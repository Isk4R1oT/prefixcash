"""experiment.py — проверка фикс-вариантов на выборке в staging (D24/D25).

Протокол (advisory, D18):
1. Берём выборку сессий (staging-трафик): system_prompt + последовательности user-сообщений.
2. Для каждого варианта сборки промпта прогоняем реплей через реального провайдера
   и собираем usage -> hit rate и saved USD (через ценовые таблицы prefixcash).
3. Вердикт по экономике кеша: улучшился ли hit rate и сколько $ экономии на выборке.

Качество фиксов НЕ оцениваем (D25): у пользователя свой eval. Наша задача —
показать, ГДЕ ломается кеш и СКОЛЬКО будет сэкономлено при правильной сборке.

Клиент-агностично: нужен любой объект с `complete(messages) -> (text, usage)`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from prefixcash.core.metrics import CacheMetrics
from prefixcash.core.parsers import parse_usage
from prefixcash.core.pricing import cost

DEFAULT_VARIANTS = ("baseline", "fixed")
HIT_IMPROVEMENT_THRESHOLD = 0.05


class LLMClient(Protocol):
    """Минимальный контракт LLM-клиента: (messages) -> (text, usage-пейлоад)."""

    def complete(self, messages: list[dict]) -> tuple[str, dict]: ...


@dataclass
class SessionCase:
    """Один сценарий сессии (staging-трафик)."""

    session_id: str
    system_prompt: str
    turns: list[str]
    provider: str = "deepseek"
    model: str = "deepseek-chat"


@dataclass
class CallResult:
    """Результат одного хода реплея."""

    session_id: str
    turn: int
    output: str
    input_tokens: int
    cache_hit_tokens: int

    @property
    def hit_rate(self) -> float:
        return self.cache_hit_tokens / self.input_tokens if self.input_tokens else 0.0


@dataclass
class VariantResult:
    """Агрегат по варианту: hit rate и деньги."""

    name: str
    calls: list[CallResult]
    provider: str = "deepseek"
    model: str = "deepseek-chat"

    @property
    def inputs(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def hits(self) -> int:
        return sum(c.cache_hit_tokens for c in self.calls)

    @property
    def hit_rate(self) -> float:
        return self.hits / self.inputs if self.inputs else 0.0

    def _cost_of(self, call: CallResult):
        m = CacheMetrics(
            provider=self.provider,
            model=self.model,
            input_tokens=call.input_tokens,
            cache_read_tokens=call.cache_hit_tokens,
        )
        return cost(m)

    @property
    def base_input_cost(self) -> float:
        return sum(self._cost_of(c).base_input_cost for c in self.calls)

    @property
    def actual_input_cost(self) -> float:
        return sum(self._cost_of(c).actual_input_cost for c in self.calls)

    @property
    def saved_usd(self) -> float:
        return self.base_input_cost - self.actual_input_cost


@dataclass
class ExperimentReport:
    """Итог эксперимента: hit rate и экономия по вариантам (D25: без оценки качества)."""

    session_count: int
    baseline: VariantResult
    variants: list[VariantResult]
    verdict: str

    @property
    def best_variant(self) -> VariantResult:
        return max(self.variants, key=lambda v: v.hit_rate) if self.variants else self.baseline

    @property
    def hit_rate_delta(self) -> float:
        return self.best_variant.hit_rate - self.baseline.hit_rate

    @property
    def saved_delta_usd(self) -> float:
        return self.best_variant.saved_usd - self.baseline.saved_usd

    def render_md(self) -> str:
        header = "| variant | calls | input | hits | hit % | base $ | actual $ | saved $ |"
        sep = "|---|---:|---:|---:|---:|---:|---:|---:|"
        lines = ["# prefixcash experiment", "", header, sep]
        for v in [self.baseline, *self.variants]:
            lines.append(
                f"| {v.name} | {len(v.calls)} | {v.inputs:,} | {v.hits:,} | {v.hit_rate:.1%} "
                f"| {v.base_input_cost:.4f} | {v.actual_input_cost:.4f} | {v.saved_usd:.4f} |"
            )
        lines.append("")
        lines.append(f"Экономия на выборке при применении фикса: ${self.saved_delta_usd:.4f}")
        lines.append("")
        lines.append(f"**Вердикт: {self.verdict}**")
        return "\n".join(lines)


def _replay(
    cases: Sequence[SessionCase],
    prompt_for: Callable[[str, str], str],
    variant: str,
    client: LLMClient,
    max_turns: int | None,
) -> list[CallResult]:
    """Реплей сессий с данным вариантом системного промпта."""
    results: list[CallResult] = []
    for case in cases:
        system = prompt_for(variant, case.session_id)
        messages: list[dict] = [{"role": "system", "content": system}]
        for turn, user_text in enumerate(case.turns, start=1):
            messages.append({"role": "user", "content": user_text})
            text, usage = client.complete(messages)
            messages.append({"role": "assistant", "content": text})
            parsed = parse_usage(case.provider, usage)
            results.append(
                CallResult(
                    session_id=case.session_id,
                    turn=turn,
                    output=text,
                    input_tokens=parsed.input_tokens,
                    cache_hit_tokens=parsed.cache_read_tokens,
                )
            )
            if max_turns is not None and turn >= max_turns:
                break
    return results


def run_experiment(
    cases: Sequence[SessionCase],
    client: LLMClient,
    *,
    prompt_for: Callable[[str, str], str],
    variants: Sequence[str] = DEFAULT_VARIANTS,
    max_turns: int | None = None,
) -> ExperimentReport:
    """Прогоняет эксперимент: реплей по вариантам + вердикт по экономике кеша.

    Качество фиксов оценивает пользователь своим eval'ом (D25) — здесь только
    кеш-экономика: где ломается и сколько $ сэкономит правильная сборка.
    """
    results: dict[str, VariantResult] = {}
    for variant in variants:
        calls = _replay(cases, prompt_for, variant, client, max_turns)
        results[variant] = VariantResult(
            variant,
            calls,
            provider=cases[0].provider if cases else "deepseek",
            model=cases[0].model if cases else "deepseek-chat",
        )

    baseline = results[variants[0]]
    rest = [results[v] for v in variants[1:]]
    best = max(rest, key=lambda v: v.hit_rate) if rest else baseline
    delta = best.hit_rate - baseline.hit_rate
    saved_delta = best.saved_usd - baseline.saved_usd
    if delta > HIT_IMPROVEMENT_THRESHOLD:
        verdict = (
            f"ФИКС ЭФФЕКТИВЕН: hit rate {baseline.hit_rate:.0%} -> {best.hit_rate:.0%} "
            f"(+{delta:.0%}), экономия на выборке ${saved_delta:.4f}. "
            f"Качество — проверьте вашим eval'ом перед применением (D18)."
        )
    else:
        verdict = (
            f"ФИКС НЕ ДАЁТ ВЫИГРЫША: hit rate {baseline.hit_rate:.0%} -> {best.hit_rate:.0%} "
            f"({delta:+.0%}). Причина может быть вне кеша."
        )
    return ExperimentReport(session_count=len(cases), baseline=baseline, variants=rest, verdict=verdict)
