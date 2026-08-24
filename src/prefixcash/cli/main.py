"""CLI prefixcash (P0): report / monitor / providers / import."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from prefixcash import __version__
from prefixcash.cli.monitor import metrics_table
from prefixcash.cli.report import build_report, render_md, report_to_dict
from prefixcash.core.pricing import PRICING
from prefixcash.integrations.importers import iter_jsonl

console = Console()


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """prefixcash — экономика префикс-кеша для LLM-приложений."""


@cli.command()
@click.option("--file", "path", type=click.Path(exists=True, dir_okay=False), required=True, help="JSONL-лог вызовов")
@click.option("--format", "fmt", type=click.Choice(["md", "json"]), default="md", show_default=True)
def report(path: str, fmt: str) -> None:
    """Отчёт «$ сэкономлено» vs холодный бейзлайн (артефакт для тех, кто платит)."""
    metrics = list(iter_jsonl(path))
    if not metrics:
        raise click.ClickException("в логе нет записей с usage")
    rep = build_report(metrics)
    if fmt == "json":
        console.print_json(json.dumps(report_to_dict(rep), ensure_ascii=False))
    else:
        console.print(render_md(rep))


@cli.command()
@click.option("--file", "path", type=click.Path(exists=True, dir_okay=False), required=True, help="JSONL-лог вызовов")
def monitor(path: str) -> None:
    """Снимок hit rate по провайдерам/моделям (live TUI на Textual — P1)."""
    metrics = list(iter_jsonl(path))
    if not metrics:
        raise click.ClickException("в логе нет записей с usage")
    console.print(metrics_table(metrics))


@cli.command()
def providers() -> None:
    """Таблица кеш-семантики провайдеров (цены, TTL)."""
    table = Table(title="prefixcash — pricing (PRELIMINARY: проверить перед релизом)")
    table.add_column("provider")
    table.add_column("model")
    table.add_column("base $/1M")
    table.add_column("cached $/1M")
    table.add_column("ttl")
    table.add_column("updated")
    table.add_column("verified")
    for (provider, model), entry in sorted(PRICING.items()):
        table.add_row(
            provider,
            model,
            f"{entry.base_input_per_mtok:.4f}",
            f"{entry.cached_input_per_mtok:.4f}",
            entry.ttl_hint,
            entry.updated,
            "yes" if entry.verified else "no",
        )
    console.print(table)


@cli.command("import")
@click.option("--litellm", "path", type=click.Path(exists=True, dir_okay=False), required=True, help="исходный JSONL (LiteLLM/OpenRouter/сырые записи)")
@click.option("--out", "out", type=click.Path(dir_okay=False), default="prefixcash.jsonl", show_default=True)
def import_cmd(path: str, out: str) -> None:
    """Нормализует лог в JSONL prefixcash."""
    count = 0
    with open(out, "w", encoding="utf-8") as fh:
        for m in iter_jsonl(path):
            fh.write(json.dumps(_record(m), ensure_ascii=False) + "\n")
            count += 1
    console.print(f"normalized {count} records -> {out}")


def _record(m) -> dict:
    return {
        "provider": m.provider,
        "model": m.model,
        "usage": {
            "input_tokens": m.input_tokens,
            "cache_read_tokens": m.cache_read_tokens,
            "cache_write_tokens": m.cache_write_tokens,
            "output_tokens": m.output_tokens,
        },
        "session_id": m.session_id,
        "agent": m.agent,
        "project": m.project,
        "ts": m.ts.isoformat(),
    }
