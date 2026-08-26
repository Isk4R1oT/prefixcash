"""Diagnosis rules: intra-session prefix breakage -> causes and fix variants.

Advisory-first (D18): findings propose fix VARIANTS; nothing is applied
automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prefixcash.diagnose.calls import CallRecord
from prefixcash.diagnose.diff import first_divergence, snippet
from prefixcash.diagnose.dynamics import classify
from prefixcash.diagnose.lcp import common_prefix_len
from prefixcash.diagnose.tokens import tokenize


@dataclass
class BreakCause:
    """Cause of a prefix break."""

    kind: str
    detail: str


@dataclass
class Finding:
    """One finding: where the prefix diverged, why, and fix variants."""

    session_id: str
    call_index: int
    prev_call_index: int | None
    shared_prefix_words: int
    break_words: list[str] = field(default_factory=list)
    causes: list[BreakCause] = field(default_factory=list)
    fix_variants: list[str] = field(default_factory=list)
    note: str = ""


_FIX_BY_CAUSE: dict[str, str] = {
    "dynamic_iso_datetime": "move the dynamic timestamp to the END of the prompt (after the static block)",
    "dynamic_datetime": "move the dynamic timestamp to the END of the prompt (after the static block)",
    "dynamic_time": "move the dynamic time/timestamp to the END of the prompt (after the static block)",
    "dynamic_date": "move the date out of the prefix — to the end or into session metadata",
    "dynamic_uuid": "remove the session/request id from the prefix — put it in metadata/tags, not in the text",
    "dynamic_hex_token": "stabilize the prefix: generated tokens go to the end",
    "dynamic_number": "check that the counter/number is not in the prefix position",
    "dynamic_email": "personal data — move to the end/metadata (also safer)",
    "dynamic_url_query": "stabilize the URL or move it to the end",
    "dynamic_placeholder": "render the placeholder at the END of the prompt",
    "high_entropy": "high-entropy segment (UUID/hash/generation) — move it out of the prefix",
    "content_change": "content before the shared prefix changes between calls — stabilize prompt assembly order",
    "cache_miss_despite_shared_prefix": (
        "prefix matches but usage shows no cache hit — likely TTL expiry or a non-caching "
        "provider/upstream; for shared prefixes — keep-alive warm-up (P2) or pin a cache-friendly provider"
    ),
}


def _fix_for(cause_kind: str) -> str:
    return _FIX_BY_CAUSE.get(cause_kind, "check prompt assembly manually")


def analyze_session(session_id: str, calls: list[CallRecord]) -> list[Finding]:
    """Analyzes the call sequence of ONE session (D21): finds prefix breakage between
    neighboring messages and classifies what exactly breaks it."""
    findings: list[Finding] = []
    for i in range(1, len(calls)):
        cur = calls[i]
        prev = calls[i - 1]
        if cur.prompt is None or prev.prompt is None:
            continue
        a = tokenize(prev.prompt)
        b = tokenize(cur.prompt)
        lcp = common_prefix_len(a, b)
        div = first_divergence(a, b)
        causes: list[BreakCause] = []
        break_words: list[str] = []
        if div < len(b) and div < len(a):
            break_words = b[div : div + 6]
            seen: set[str] = set()
            for w in break_words:
                for kind in classify(w):
                    if kind not in seen:
                        seen.add(kind)
                        causes.append(BreakCause(kind=f"dynamic_{kind}", detail=f"word after the break: {w!r}"))
            if not causes:
                causes.append(BreakCause("content_change", detail=f"break at word {div}: «{snippet(b, div)}»"))
        # usage-уровень: общий префикс есть, а кеш-хита нет
        if cur.metrics.cache_read_tokens == 0 and lcp > 0:
            causes.append(
                BreakCause(
                    "cache_miss_despite_shared_prefix",
                    detail=f"shared prefix {lcp} words, but usage.cache_read_tokens == 0",
                )
            )
        if causes:
            findings.append(
                Finding(
                    session_id=session_id,
                    call_index=i,
                    prev_call_index=i - 1,
                    shared_prefix_words=lcp,
                    break_words=break_words,
                    causes=causes,
                    fix_variants=[_fix_for(c.kind) for c in causes],
                )
            )
    return findings
