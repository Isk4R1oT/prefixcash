"""Textual TUI: монитор + тепловая карта префиксов (D16, D23).

Управление: j/k — переключение сессий. Тепловая карта показывает, где в промпте
кеш стабилен (зелёный), колеблется (жёлтый) и где теряется (красный), плюс
конкретные фикс-предложения (assembly-lint, advisory D18).
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from prefixcash.core.metrics import aggregate
from prefixcash.core.pricing import cost
from prefixcash.diagnose.assembly import AssemblySuggestion, lint
from prefixcash.diagnose.calls import CallRecord
from prefixcash.diagnose.engine import group_by_session
from prefixcash.diagnose.heatmap import PromptHeatmap, build_heatmap

_COLORS = {"hot": "green", "warm": "yellow", "cold": "red"}


def render_heatmap_markup(hm: PromptHeatmap, limit: int | None = None) -> str:
    """Тепловая карта как rich-разметка (цвет по стабильности)."""
    if not hm.cells:
        return "(нет промптов в сессии)"
    cells = hm.cells[:limit] if limit else hm.cells
    parts = [f"[{_COLORS[c.kind]}]{c.word}[/]" for c in cells]
    text = " ".join(parts)
    if limit and len(hm.cells) > limit:
        text += f" … ещё {len(hm.cells) - limit} слов"
    return text


class PrefixCashTui(App):
    """Интерактивный монитор prefixcash."""

    TITLE = "prefixcash — cache heatmap"
    CSS = """
    #stats, #routing { height: auto; margin: 0 1; }
    #heatmap { height: auto; margin: 0 1; border: round $primary; padding: 0 1; }
    #fixes { height: auto; margin: 0 1; }
    """

    def __init__(self, calls: list[CallRecord]) -> None:
        super().__init__()
        self._calls = calls
        self._sessions = group_by_session(calls)
        self._session_ids = sorted(self._sessions)
        self._idx = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical():
                yield Static(id="stats")
                yield Static(id="routing")
            with Vertical():
                yield Static(id="heatmap")
                yield Static(id="fixes")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_all()

    # --- рендер ---
    def refresh_all(self) -> None:
        self.query_one("#stats", Static).update(self._stats_text())
        self.query_one("#routing", Static).update(self._routing_text())
        sid = self._session_ids[self._idx] if self._session_ids else None
        if sid is None:
            self.query_one("#heatmap", Static).update("(нет сессий с промптами)")
            self.query_one("#fixes", Static).update("")
            return
        hm = build_heatmap(sid, self._sessions[sid])
        self.query_one("#heatmap", Static).update(render_heatmap_markup(hm))
        self.query_one("#fixes", Static).update(self._fixes_text(lint(hm)))

    def _stats_text(self) -> str:
        if not self._calls:
            return "(нет данных)"
        agg = aggregate([c.metrics for c in self._calls])
        saved = 0.0
        for c in self._calls:
            cb = cost(c.metrics)
            if cb.priced:
                saved += cb.saved_usd
        idx = self._idx if self._session_ids else 0
        total = len(self._session_ids)
        return (
            f"calls: {agg.calls} | hit rate: {agg.hit_rate:.1%} | saved: ${saved:.2f}\n"
            f"сессия {idx + 1}/{total}: {self._session_ids[idx] if self._session_ids else '-'} (j/k — переключение)"
        )

    def _routing_text(self) -> str:
        from prefixcash.optimize.routing import recommend

        return f"маршрутизация (advisory): {recommend()}"

    def _fixes_text(self, fixes: list[AssemblySuggestion]) -> str:
        if not fixes:
            return "фикс-предложения: стабильный префикс, поломок нет"
        lines = [f"фикс-предложения ({len(fixes)}):"]
        for f in fixes[:6]:
            lines.append(f"  [{_COLORS['cold']}]{f.position}: {f.word}[/] — {f.suggestion}")
        return "\n".join(lines)

    # --- управление ---
    def key_j(self) -> None:
        if self._session_ids:
            self._idx = (self._idx + 1) % len(self._session_ids)
            self.refresh_all()

    def key_k(self) -> None:
        if self._session_ids:
            self._idx = (self._idx - 1) % len(self._session_ids)
            self.refresh_all()
