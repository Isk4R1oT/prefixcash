"""Отчёт «$ сэкономлено» vs холодный бейзлайн (артефакт для тех, кто платит)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from prefixcash.core.metrics import CacheMetrics, aggregate
from prefixcash.core.pricing import cost


@dataclass
class ProviderRow:
    provider: str
    calls: int
    input_tokens: int
    cache_read_tokens: int
    hit_rate: float
    base_input_cost: float
    actual_input_cost: float
    saved_usd: float
    priced_calls: int


@dataclass
class Report:
    providers: list[ProviderRow]
    totals: ProviderRow | None = None
    overall_hit_rate: float = 0.0


def build_report(metrics: Sequence[CacheMetrics]) -> Report:
    providers: list[ProviderRow] = []
    for provider in sorted({m.provider for m in metrics}):
        agg = aggregate(metrics, provider=provider)
        base = actual = saved = 0.0
        priced_calls = 0
        for m in metrics:
            if m.provider != provider:
                continue
            c = cost(m)
            if c.priced:
                base += c.base_input_cost
                actual += c.actual_input_cost
                saved += c.saved_usd
                priced_calls += 1
        providers.append(
            ProviderRow(
                provider=provider,
                calls=agg.calls,
                input_tokens=agg.input_tokens,
                cache_read_tokens=agg.cache_read_tokens,
                hit_rate=agg.hit_rate,
                base_input_cost=base,
                actual_input_cost=actual,
                saved_usd=saved,
                priced_calls=priced_calls,
            )
        )
    if not providers:
        return Report(providers=[])
    totals = ProviderRow(
        provider="TOTAL",
        calls=sum(p.calls for p in providers),
        input_tokens=sum(p.input_tokens for p in providers),
        cache_read_tokens=sum(p.cache_read_tokens for p in providers),
        hit_rate=0.0,
        base_input_cost=sum(p.base_input_cost for p in providers),
        actual_input_cost=sum(p.actual_input_cost for p in providers),
        saved_usd=sum(p.saved_usd for p in providers),
        priced_calls=sum(p.priced_calls for p in providers),
    )
    totals.hit_rate = totals.cache_read_tokens / totals.input_tokens if totals.input_tokens else 0.0
    return Report(providers=providers, totals=totals, overall_hit_rate=totals.hit_rate)


def render_md(report: Report) -> str:
    lines = [
        "# prefixcash report",
        "",
        "Методология: бейзлайн = весь инпут по полной цене (консервативно). См. METHODOLOGY.md.",
        "",
        "| provider | calls | input | cache read | hit % | base $ | actual $ | saved $ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for p in report.providers:
        lines.append(
            f"| {p.provider} | {p.calls} | {p.input_tokens:,} | {p.cache_read_tokens:,} "
            f"| {p.hit_rate:.1%} | {p.base_input_cost:,.2f} | {p.actual_input_cost:,.2f} | {p.saved_usd:,.2f} |"
        )
    t = report.totals
    if t is not None:
        lines.append(
            f"| **TOTAL** | **{t.calls}** | **{t.input_tokens:,}** | **{t.cache_read_tokens:,}** "
            f"| **{t.hit_rate:.1%}** | **{t.base_input_cost:,.2f}** | **{t.actual_input_cost:,.2f}** "
            f"| **{t.saved_usd:,.2f}** |"
        )
    lines.append("")
    return "\n".join(lines)


def report_to_dict(report: Report) -> dict:
    rows = []
    for p in report.providers:
        rows.append(
            {
                "provider": p.provider,
                "calls": p.calls,
                "input_tokens": p.input_tokens,
                "cache_read_tokens": p.cache_read_tokens,
                "hit_rate": round(p.hit_rate, 4),
                "base_input_cost": round(p.base_input_cost, 2),
                "actual_input_cost": round(p.actual_input_cost, 2),
                "saved_usd": round(p.saved_usd, 2),
                "priced_calls": p.priced_calls,
            }
        )
    t = report.totals
    totals = None
    if t is not None:
        totals = {
            "calls": t.calls,
            "input_tokens": t.input_tokens,
            "cache_read_tokens": t.cache_read_tokens,
            "hit_rate": round(t.hit_rate, 4),
            "base_input_cost": round(t.base_input_cost, 2),
            "actual_input_cost": round(t.actual_input_cost, 2),
            "saved_usd": round(t.saved_usd, 2),
        }
    return {"overall_hit_rate": round(report.overall_hit_rate, 4), "totals": totals, "providers": rows}
