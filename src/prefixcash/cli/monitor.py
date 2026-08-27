"""Static rich snapshot of metrics (live Textual TUI — `tui` command)."""

from __future__ import annotations

from rich.table import Table

from prefixcash.core.metrics import CacheMetrics, aggregate
from prefixcash.core.pricing import cost


def _saved_by_key(metrics: list[CacheMetrics]) -> dict[tuple[str, str], float]:
    """Экономия, просуммированная ОТДЕЛЬНО по каждой паре (provider, model)."""
    saved: dict[tuple[str, str], float] = {}
    for m in metrics:
        breakdown = cost(m)
        if not breakdown.priced:
            continue
        key = (m.provider, m.model)
        saved[key] = saved.get(key, 0.0) + breakdown.saved_usd
    return saved


def metrics_table(metrics: list[CacheMetrics]) -> Table:
    table = Table(title="prefixcash — cache hit rate")
    table.add_column("provider")
    table.add_column("model")
    table.add_column("calls")
    table.add_column("input")
    table.add_column("cache read")
    table.add_column("hit %")
    table.add_column("saved $")

    saved_by_key = _saved_by_key(metrics)
    keys = sorted({(m.provider, m.model) for m in metrics})
    for provider, model in keys:
        agg = aggregate(metrics, provider=provider, model=model)
        table.add_row(
            provider,
            model,
            f"{agg.calls:,}",
            f"{agg.input_tokens:,}",
            f"{agg.cache_read_tokens:,}",
            f"{agg.hit_rate:.1%}",
            f"${saved_by_key.get((provider, model), 0.0):,.2f}",
        )
    return table
