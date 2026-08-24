"""CLI prefixcash: report / monitor / diagnose / providers / import (P0+P1)."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from prefixcash import __version__
from prefixcash.cli.monitor import metrics_table
from prefixcash.cli.report import build_report, render_md, report_to_dict
from prefixcash.core.pricing import PRICING
from prefixcash.diagnose.assembly import lint
from prefixcash.diagnose.engine import analyze_calls, group_by_session
from prefixcash.diagnose.heatmap import build_heatmap, render_heatmap_markup
from prefixcash.diagnose.rules import analyze_session
from prefixcash.integrations.importers import iter_calls, iter_jsonl

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
@click.option(
    "--file",
    "path",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="JSONL-лог вызовов (нужны prompt/messages)",
)
@click.option("--session", "session", default=None, help="фильтр по session_id")
@click.option("--json", "as_json", is_flag=True, help="вывод в JSON")
def diagnose(path: str, session: str | None, as_json: bool) -> None:
    """Что ломает префикс-кеш внутри сессий: находки + тепловая карта + фиксы (advisory, D18)."""
    calls = [c for c in iter_calls(path) if session is None or c.metrics.session_id == session]
    sessions = group_by_session(calls)
    if as_json:
        console.print_json(json.dumps(_findings_to_dict(analyze_calls(calls)), ensure_ascii=False))
        return
    if not sessions:
        console.print("В логе нет записей с usage.")
        return
    total = 0
    for sid, group in sorted(sessions.items()):
        fs = analyze_session(sid, group)
        total += len(fs)
        hm = build_heatmap(sid, group)
        console.print(f"[bold]{sid}[/bold] — {len(fs)} находок, стабильность префикса {hm.hot_ratio:.0%}")
        for f in fs:
            prev = f.prev_call_index if f.prev_call_index is not None else "?"
            console.print(f"  call {prev} -> {f.call_index}: общий префикс {f.shared_prefix_words} слов")
            if f.break_words:
                console.print(f"    слова после разрыва: {' '.join(f.break_words)}")
            for c in f.causes:
                console.print(f"    • [red]{c.kind}[/red]: {c.detail}")
            for v in f.fix_variants:
                console.print(f"    → фикс: {v}")
        if hm.cells:
            console.print("  тепловая карта (цвет = стабильность префикса):")
            console.print("  " + render_heatmap_markup(hm, limit=24))
            for s in lint(hm)[:4]:
                console.print(f"    [red]{s.position}: {s.word}[/] — {s.suggestion}")
    console.print(f"\nИтого: {total} поломок в {len(sessions)} сессиях")


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


@cli.command()
@click.option("--file", "path", type=click.Path(exists=True, dir_okay=False), required=True, help="JSONL-лог вызовов")
def tui(path: str) -> None:
    """Интерактивный TUI: статистика + тепловая карта префиксов (j/k — сессии)."""
    from prefixcash.cli.tui import PrefixCashTui

    calls = list(iter_calls(path))
    if not calls:
        raise click.ClickException("в логе нет записей с usage")
    PrefixCashTui(calls).run()


@cli.command("import")
@click.option(
    "--litellm",
    "path",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="исходный JSONL (LiteLLM/OpenRouter/сырые записи)",
)
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


def _findings_to_dict(findings: dict[str, list]) -> dict:
    """Сериализует находки diagnose в JSON."""
    return {
        sid: [
            {
                "call_index": f.call_index,
                "prev_call_index": f.prev_call_index,
                "shared_prefix_words": f.shared_prefix_words,
                "break_words": f.break_words,
                "causes": [{"kind": c.kind, "detail": c.detail} for c in f.causes],
                "fix_variants": f.fix_variants,
            }
            for f in fs
        ]
        for sid, fs in findings.items()
    }
