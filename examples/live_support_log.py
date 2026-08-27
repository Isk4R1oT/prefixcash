"""Живой прогон support-агента через DeepSeek -> реальный лог для prefixcash.

Две сессии с ОДИНАКОВЫМ содержимым и разной сборкой промпта:

    live-broken  текущее время в НАЧАЛЕ системного промпта — префикс рвётся
    live-fixed   тот же блок статики первым, время уехало в хвост

Системный блок намеренно длиннее ~1024 токенов: ниже этого порога DeepSeek
кеш вообще не включает, и разница между сборками не проявилась бы.

    export DEEPSEEK_API_KEY=sk-...
    python -m examples.live_support_log --out examples/live_support.jsonl
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from examples.run_experiment import DeepSeekClient, load_api_key

POLICY = """You are Nimbus Support, the assistant for Nimbus Cloud.

## Scope
Answer questions about billing, quotas, regions, incident status, and plan
limits. Never promise refunds above $500 without a human approver. Never
disclose another tenant's data. If a question requires account changes,
hand off to a human operator instead of guessing.

## Tone
Answer in at most six sentences. Lead with the resolution, then the reason.
Never apologise twice in one message. Do not speculate about incident causes
before the status page confirms them. Prefer concrete numbers over adjectives.

## Tools
- `lookup_invoice(invoice_id)` — returns line items and payment state.
- `check_quota(project_id, resource)` — returns limit, usage, reset time.
- `region_status(region)` — returns the live status-page entry.
- `escalate(summary, severity)` — opens a ticket for a human operator.
- `list_reservations(project_id)` — returns reserved capacity and terms.

## Rules for tools
Call `lookup_invoice` before any statement about a charge. Never quote a quota
from memory — always call `check_quota`. If `region_status` reports a
degradation, say so before answering the original question. Use `escalate`
whenever the resolution needs a human decision, and tell the user you did.

## Refund policy
Prorated refunds are automatic for outages above 30 minutes within a single
billing period. Anything else requires `escalate` with severity `billing`.
Credits expire twelve months after issue and never convert to cash. Refunds
are issued to the original payment method only.

## Knowledge base
KB-118: Quota resets occur at 00:00 UTC on the first day of the month.
KB-204: Egress in eu-central is billed at $0.09/GB after the first 10TB.
KB-311: Support-plan upgrades take effect on the next billing cycle.
KB-402: Reserved instances cannot be transferred between projects.
KB-509: Status-page incidents are authoritative over agent statements.
KB-517: Snapshot storage is billed separately from volume storage.
KB-623: A project suspended for non-payment retains data for 30 days.
KB-701: Rate limits are per-project, not per-API-key.
KB-744: Cross-region replication doubles storage cost and is opt-in.
KB-802: Trial accounts cannot open severity-1 tickets.
KB-815: Invoices are finalised on the 3rd; disputes must be filed by the 10th.
KB-901: Deleted volumes are unrecoverable after 24 hours.
KB-933: Autoscaling events are not billed as separate instance launches.
KB-948: A region in `degraded` state still bills at full rate.
KB-970: Committed-use discounts apply before promotional credits.
KB-988: API keys revoked by an admin stop working within 60 seconds.

## Escalation matrix
Severity 1 — production down, paying customer, no workaround.
Severity 2 — major feature broken, workaround exists, revenue impact.
Severity 3 — degraded experience, no revenue impact, scheduled fix.
Severity 4 — question, documentation gap, or feature request.
Always state the severity you chose and why, in one clause.

## Prohibited
Do not quote prices for regions not listed in the knowledge base. Do not
estimate incident resolution times. Do not compare Nimbus to competitors.
Do not offer credits as a negotiating tactic. Do not acknowledge internal
tooling by name.

## Regions and billing notes
us-east-1 — primary, full service catalogue, standard egress tiering.
us-west-2 — full catalogue, snapshot storage billed at the us-east rate.
eu-central-1 — GDPR residency guarantees, egress tiering per KB-204.
eu-north-1 — reduced catalogue, no GPU instances, lowest storage rate.
ap-south-1 — full catalogue, cross-region replication to eu is not offered.
ap-northeast-2 — full catalogue, reserved capacity sold in 6-month terms only.
sa-east-1 — reduced catalogue, invoices issued in USD regardless of locale.
Regions in `maintenance` state accept no new reservations but bill normally.

## Common resolutions
Invoice higher than expected — almost always egress above the 10TB tier or a
snapshot series nobody deleted. Check both before escalating.
Quota appears wrong — the console caches for five minutes; `check_quota` is
authoritative and should be quoted instead.
Sudden 429s — confirm whether the limit is per-project (KB-701) before
suggesting a key rotation, which does not help.
Data missing after volume deletion — recovery is impossible after 24 hours
(KB-901); say so plainly rather than opening a hopeful ticket.
Suspended project — data is retained 30 days (KB-623); restoring requires
settling the invoice first, and that is a human step.

## Response format
Open with the answer. Follow with the single most relevant KB reference by
its identifier. If a tool was called, state which one and what it returned.
Close with the next action and who owns it — the user, or Nimbus.
"""

QUESTIONS = [
    "Why is my invoice higher than last month?",
    "What is my egress quota for eu-central right now?",
    "Is there an incident in us-east affecting my project?",
    "Can I move a reserved instance to another project?",
]

STAMPS = [f"2026-08-27 09:{m:02d}:11 UTC" for m in range(len(QUESTIONS))]


def _static_block(run_id: str) -> str:
    """Статический блок прогона.

    `run_id` одинаков для ВСЕХ вызовов прогона, поэтому внутри прогона он
    префикс не ломает. Но он делает промпт отличным от промптов прошлых
    прогонов — иначе кеш провайдера остаётся тёплым с прошлого запуска и
    «сломанная» сессия тоже получает попадания (см. METHODOLOGY.md про
    зависимость от порядка прогонов).

    Стоит ПЕРВОЙ строкой обоих вариантов: соль обязана попасть в префикс
    до любой динамики, иначе холодный старт не гарантирован — хвост промпта
    совпадёт с прогонами прошлого часа.
    """
    return f"## Build\nnimbus-support {run_id}"


def broken_prompt(run_id: str, stamp: str) -> str:
    """Динамика перед большим статическим блоком — префикс рвётся на времени."""
    return f"{_static_block(run_id)}\nCurrent time: {stamp}.\n{POLICY}"


def fixed_prompt(run_id: str, stamp: str) -> str:
    """Статика впереди, динамика в хвосте — префикс общий для всех вызовов."""
    return f"{_static_block(run_id)}\n{POLICY}\n\n## Request context\nCurrent time: {stamp}."


def run_session(client: DeepSeekClient, session: str, build, run_id: str) -> list[dict]:
    records: list[dict] = []
    for stamp, question in zip(STAMPS, QUESTIONS, strict=True):
        system = build(run_id, stamp)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
        _, usage = client.complete(messages)
        records.append(
            {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "session_id": session,
                "usage": usage,
                "messages": messages,
            }
        )
        hit = usage.get("prompt_cache_hit_tokens", 0)
        total = usage.get("prompt_tokens", 0)
        print(f"  {session:14} prompt={total:5} cache_hit={hit:5}")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("examples/live_support.jsonl"))
    args = parser.parse_args()

    client = DeepSeekClient(load_api_key())
    # Разные run_id для двух сессий: иначе вторая унаследует тёплый кеш первой
    # и разница между сборками смажется.
    print("live DeepSeek run:")
    records = run_session(client, "live-broken", broken_prompt, uuid.uuid4().hex)
    records += run_session(client, "live-fixed", fixed_prompt, uuid.uuid4().hex)

    with args.out.open("w", encoding="utf-8") as sink:
        for record in records:
            sink.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"{len(records)} live calls -> {args.out}")


if __name__ == "__main__":
    main()
