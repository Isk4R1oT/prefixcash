"""P0: статический rich-снимок метрик (live TUI на Textual — P1, D16)."""

from __future__ import annotations

from rich.table import Table

from prefixcash.core.metrics import CacheMetrics, aggregate
from prefixcash.core.pricing import cost


def metrics_table(metrics: list[CacheMetrics]) -> Table:
    table = Table(title="prefixcash — cache hit rate")
    table.add_column("provider")
    table.add_column("model")
    table.add_column("calls")
    table.add_column("input")
    table.add_column("cache read")
    table.add_column("hit %")
    table.add_column("saved $")
    rows: dict[tuple[str, str], tuple] = {}
    for m in metrics:
        key = (m.provider, m.model)
        if key not in rows:
            agg = aggregate(metrics, provider=m.provider, model=m.model)
            saved = sum(c.saved_usd for c in (cost(x) for x in metrics) if c.priced)
            rows[key] = (agg, saved)
    for (provider, model), (agg, saved) in sorted(rows.items()):
        table.add_row(
            provider,
            model,
            str(agg.calls),
            f"{agg.input_tokens:,}",
            f"{agg.cache_read_tokens:,}",
            f"{agg.hit_rate:.1%}",
            f"${saved:,.2f}",
        )
    return table
