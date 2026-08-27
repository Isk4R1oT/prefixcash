"""Генератор демо-лога: support-агент с типовыми поломками префикс-кеша.

Четыре сессии — три сломанные разными способами и одна собранная правильно:

    s1-timestamp   текущее время в начале system-промпта
    s2-session-id  идентификатор сессии в начале system-промпта
    s3-kb-reorder  статьи базы знаний переставляются между вызовами
    s4-fixed       весь статический блок первым, динамика — в конец

    python -m examples.make_support_log --out examples/support_agent.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

POLICY = """You are Nimbus Support, the assistant for Nimbus Cloud.

## Scope
Answer questions about billing, quotas, regions, and incident status. Never
promise refunds above $500 without a human approver. Never disclose another
tenant's data. If a question needs account changes, hand off to a human.

## Tone
Answer in at most six sentences. Lead with the resolution, then the reason.
Never apologise twice in one message. Do not speculate about incident causes
before the status page confirms them.

## Tools
- `lookup_invoice(invoice_id)` — returns line items and payment state.
- `check_quota(project_id, resource)` — returns limit, usage, and reset time.
- `region_status(region)` — returns the live status-page entry.
- `escalate(summary, severity)` — opens a ticket for a human operator.

## Rules for tools
Call `lookup_invoice` before any statement about a charge. Never quote a
quota from memory — always call `check_quota`. If `region_status` reports a
degradation, say so before answering the user's original question.

## Refund policy
Prorated refunds are automatic for outages above 30 minutes in a single
billing period. Anything else needs `escalate` with severity `billing`.
Credits expire twelve months after issue and never convert to cash.
"""

KB = [
    "KB-118: Quota resets occur at 00:00 UTC on the first of the month.",
    "KB-204: Egress in the eu-central region is billed at $0.09/GB after 10TB.",
    "KB-311: Support-plan upgrades take effect on the next billing cycle.",
    "KB-402: Reserved instances cannot be transferred between projects.",
    "KB-509: Status-page incidents are authoritative over agent statements.",
]

QUESTIONS = [
    "Why is my invoice higher than last month?",
    "What is my current egress quota for eu-central?",
    "Is there an incident in us-east right now?",
]


def _call(session: str, system: str, question: str, prompt_tokens: int, cached: int) -> dict:
    return {
        "model": "gpt-4o",
        "session_id": session,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": 180,
            "prompt_tokens_details": {"cached_tokens": cached},
        },
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
    }


def build() -> list[dict]:
    kb_block = "\n".join(KB)
    static = f"{POLICY}\n## Knowledge base\n{kb_block}"
    size = 4200
    records: list[dict] = []

    # s1 — время в начале: префикс рвётся на каждом вызове, кеш не читается
    for i, q in enumerate(QUESTIONS):
        head = f"Current time: 2026-08-27 09:0{i}:11 UTC.\n"
        records.append(_call("s1-timestamp", head + static, q, size, 0))

    # s2 — идентификатор сессии в начале: то же самое, другой источник динамики
    for i, q in enumerate(QUESTIONS):
        head = f"Session: 4f9c21{i}a-7d3e-4b18-9a02-{i}c5e8871f0d2\n"
        records.append(_call("s2-session-id", head + static, q, size, 0))

    # s3 — база знаний переставляется: статика есть, но порядок плавает
    for i, q in enumerate(QUESTIONS):
        rotated = "\n".join(KB[i:] + KB[:i])
        system = f"{POLICY}\n## Knowledge base\n{rotated}"
        records.append(_call("s3-kb-reorder", system, q, size, 0 if i else 0))

    # s4 — собрано правильно: статика первой, динамика в конце
    for i, q in enumerate(QUESTIONS):
        tail = f"\n\n## Request context\nCurrent time: 2026-08-27 09:0{i}:11 UTC."
        cached = 0 if i == 0 else 4096  # первый вызов холодный, дальше — попадания
        records.append(_call("s4-fixed", static + tail, q, size, cached))

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("examples/support_agent.jsonl"))
    args = parser.parse_args()
    records = build()
    with args.out.open("w", encoding="utf-8") as sink:
        for record in records:
            sink.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"{len(records)} calls -> {args.out}")


if __name__ == "__main__":
    main()
