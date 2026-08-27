"""prefixcash CLI: report / monitor / diagnose / providers / import / tui."""

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
    """prefixcash — prefix-cache economics for LLM applications."""


@cli.command()
@click.option("--file", "path", type=click.Path(exists=True, dir_okay=False), required=True, help="call log (JSONL)")
@click.option("--format", "fmt", type=click.Choice(["md", "json"]), default="md", show_default=True)
def report(path: str, fmt: str) -> None:
    """Report «$ saved» vs cold baseline (the artifact for whoever pays the bill)."""
    metrics = list(iter_jsonl(path))
    if not metrics:
        raise click.ClickException("no usage records in the log")
    rep = build_report(metrics)
    if fmt == "json":
        console.print_json(json.dumps(report_to_dict(rep), ensure_ascii=False))
    else:
        # Дословно: rich перенёс бы длинные строки по ширине терминала и
        # разрезал markdown-таблицу — `report > report.md` перестал бы
        # быть валидным markdown на узком экране.
        click.echo(render_md(rep))


@cli.command()
@click.option("--file", "path", type=click.Path(exists=True, dir_okay=False), required=True, help="call log (JSONL)")
def monitor(path: str) -> None:
    """Snapshot of hit rate by provider/model (see `tui` for the live dashboard)."""
    metrics = list(iter_jsonl(path))
    if not metrics:
        raise click.ClickException("no usage records in the log")
    console.print(metrics_table(metrics))


@cli.command()
@click.option(
    "--file",
    "path",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="call log (JSONL) — needs prompt/messages",
)
@click.option("--session", "session", default=None, help="filter by session_id")
@click.option("--json", "as_json", is_flag=True, help="output as JSON")
def diagnose(path: str, session: str | None, as_json: bool) -> None:
    """What breaks the prefix cache inside sessions: findings + heatmap + fixes (advisory, D18)."""
    calls = [c for c in iter_calls(path) if session is None or c.metrics.session_id == session]
    sessions = group_by_session(calls)
    if as_json:
        console.print_json(json.dumps(_findings_to_dict(analyze_calls(calls)), ensure_ascii=False))
        return
    if not sessions:
        console.print("No usage records in the log.")
        return
    total = 0
    for sid, group in sorted(sessions.items()):
        fs = analyze_session(sid, group)
        total += len(fs)
        hm = build_heatmap(sid, group)
        noun = "finding" if len(fs) == 1 else "findings"
        console.print(
            f"[bold]{sid}[/bold] — {len(fs)} {noun}, cacheable prefix {hm.cached_ratio:.0%}"
        )
        for f in fs:
            prev = f.prev_call_index if f.prev_call_index is not None else "?"
            console.print(f"  call {prev} -> {f.call_index}: shared prefix {f.shared_prefix_words} words")
            if f.break_words:
                console.print(f"    words after the break: {' '.join(f.break_words)}")
            for c in f.causes:
                console.print(f"    • [red]{c.kind}[/red]: {c.detail}")
            for v in f.fix_variants:
                console.print(f"    → fix: {v}")
        if hm.cells:
            console.print(
                "  heatmap — [green]cached[/] · [bold red]breaks the cache[/] · "
                "[dark_orange]lost after the break[/]:"
            )
            console.print("  " + render_heatmap_markup(hm, limit=24))
            for s in lint(hm)[:4]:
                console.print(f"    [red]{s.position}: {s.word}[/] — {s.suggestion}")
    console.print(f"\nTotal: {total} breakages in {len(sessions)} sessions")


@cli.command()
def providers() -> None:
    """Provider cache-semantics table (prices, TTL)."""
    table = Table(title="prefixcash — cache pricing (check `verified` against your own contract)")
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
@click.option("--file", "path", type=click.Path(exists=True, dir_okay=False), required=True, help="call log (JSONL)")
def tui(path: str) -> None:
    """Interactive TUI: stats + prefix heatmap (j/k — sessions)."""
    from prefixcash.cli.tui import PrefixCashTui

    calls = list(iter_calls(path))
    if not calls:
        raise click.ClickException("no usage records in the log")
    PrefixCashTui(calls).run()


@cli.command("import")
@click.option(
    "--litellm",
    "path",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="source JSONL (LiteLLM/OpenRouter/raw records)",
)
@click.option("--out", "out", type=click.Path(dir_okay=False), default="prefixcash.jsonl", show_default=True)
def import_cmd(path: str, out: str) -> None:
    """Normalize a log into prefixcash JSONL."""
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
    """Serialize diagnose findings to JSON."""
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
