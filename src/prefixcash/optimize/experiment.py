"""experiment.py — проверка фикс-вариантов на выборке в staging (D24).

Протокол (advisory, D18):
1. Берём выборку сессий (staging-трафик): system_prompt + последовательности user-сообщений.
2. Для каждого варианта сборки промпта прогоняем реплей через реального провайдера
   и собираем usage -> hit rate и saved USD (через ценовые таблицы prefixcash).
3. Качество: LLM-as-judge попарно (baseline vs variant ответы) на тех же вопросах.
4. Вердикт: APPLY / DON'T APPLY — применяет человек.

Клиент-агностично: нужен любой объект с `complete(messages) -> (text, usage)`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from prefixcash.core.metrics import CacheMetrics
from prefixcash.core.parsers import parse_usage
from prefixcash.core.pricing import cost

DEFAULT_VARIANTS = ("baseline", "fixed")


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
class QualityVerdict:
    """Результат LLM-as-judge по парам (baseline, variant)."""

    original_better: int = 0
    variant_better: int = 0
    ties: int = 0

    @property
    def total(self) -> int:
        return self.original_better + self.variant_better + self.ties

    @property
    def variant_not_worse(self) -> bool:
        """Качество варианта не хуже: вариант лучше или равен чаще, чем хуже."""
        return self.variant_better + self.ties >= self.original_better


@dataclass
class ExperimentReport:
    """Итог эксперимента: hit rate, деньги и качество по вариантам."""

    session_count: int
    baseline: VariantResult
    variants: list[VariantResult]
    quality: QualityVerdict
    verdict: str

    def render_md(self) -> str:
        header = "| variant | calls | input | hits | hit % | base $ | actual $ | saved $ |"
        sep = "|---|---:|---:|---:|---:|---:|---:|---:|"
        lines = ["# prefixcash experiment", "", header, sep]
        for v in [self.baseline, *self.variants]:
            lines.append(
                f"| {v.name} | {len(v.calls)} | {v.inputs:,} | {v.hits:,} | {v.hit_rate:.1%} "
                f"| {v.base_input_cost:.4f} | {v.actual_input_cost:.4f} | {v.saved_usd:.4f} |"
            )
        q = self.quality
        lines.append("")
        lines.append(
            f"Качество (LLM-as-judge, {q.total} пар): оригинал лучше {q.original_better}, "
            f"вариант лучше {q.variant_better}, равны {q.ties}"
        )
        lines.append("")
        lines.append(f"**Вердикт: {self.verdict}**")
        return "\n".join(lines)


_JUDGE_PROMPT = (
    "Ты — судья качества ответов ассистента. Тебе дадут вопрос и два ответа. "
    "Оцени, какой ответ лучше (точнее, полезнее, корректнее) или они равнозначны.\n"
    'Ответь строго одним JSON: {"choice": "first" | "second" | "tie"}'
)


def judge_pairwise(judge: LLMClient, query: str, first: str, second: str) -> str:
    """Попарное сравнение: 'first' | 'second' | 'tie'."""
    messages = [
        {"role": "system", "content": _JUDGE_PROMPT},
        {"role": "user", "content": f"Вопрос: {query}\n\nОтвет 1: {first}\n\nОтвет 2: {second}"},
    ]
    text, _ = judge.complete(messages)
    m = re.search(r'"(first|second|tie)"', text)
    return m.group(1) if m else "tie"


def _replay(
    cases: Sequence[SessionCase],
    prompt_for: Callable[[str, str], str],
    variant: str,
    client: LLMClient,
    max_turns: int | None,
) -> tuple[list[CallResult], dict[tuple[str, int], str], dict[tuple[str, int], str]]:
    """Реплей сессий с данным вариантом системного промпта.

    Возвращает (вызовы, ответы по ключу (session, turn), вопросы по ключу).
    """
    results: list[CallResult] = []
    outputs: dict[tuple[str, int], str] = {}
    queries: dict[tuple[str, int], str] = {}
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
            outputs[(case.session_id, turn)] = text
            queries[(case.session_id, turn)] = user_text
            if max_turns is not None and turn >= max_turns:
                break
    return results, outputs, queries


def run_experiment(
    cases: Sequence[SessionCase],
    client: LLMClient,
    *,
    prompt_for: Callable[[str, str], str],
    variants: Sequence[str] = DEFAULT_VARIANTS,
    max_turns: int | None = None,
    judge: LLMClient | None = None,
) -> ExperimentReport:
    """Прогоняет эксперимент: реплей по вариантам + LLM-as-judge + вердикт (advisory)."""
    variant_results: dict[str, VariantResult] = {}
    outputs: dict[str, dict[tuple[str, int], str]] = {}
    queries: dict[str, dict[tuple[str, int], str]] = {}
    for variant in variants:
        calls, outs, ques = _replay(cases, prompt_for, variant, client, max_turns)
        variant_results[variant] = VariantResult(
            variant,
            calls,
            provider=cases[0].provider if cases else "deepseek",
            model=cases[0].model if cases else "deepseek-chat",
        )
        outputs[variant] = outs
        queries[variant] = ques

    quality = QualityVerdict()
    if judge is not None and len(variants) >= 2:
        base, alt = variants[0], variants[1]
        for key in outputs[base]:
            if key not in outputs[alt]:
                continue
            choice = judge_pairwise(judge, queries[base][key], outputs[base][key], outputs[alt][key])
            if choice == "first":
                quality.original_better += 1
            elif choice == "second":
                quality.variant_better += 1
            else:
                quality.ties += 1

    baseline = variant_results[variants[0]]
    rest = [variant_results[v] for v in variants[1:]]
    best = max(rest, key=lambda v: v.hit_rate) if rest else baseline
    hit_improved = best.hit_rate > baseline.hit_rate + 0.05
    if hit_improved and quality.variant_not_worse:
        verdict = (
            f"APPLY: {best.name} (hit rate {baseline.hit_rate:.0%} -> {best.hit_rate:.0%}, "
            f"качество не хуже: {quality.variant_better + quality.ties}/{quality.total})"
        )
    elif hit_improved:
        verdict = "ПРОВЕРИТЬ ВРУЧНУЮ: hit rate вырос, но качество требует ручной оценки"
    else:
        verdict = "DON'T APPLY: улучшения hit rate не достигнуто"
    return ExperimentReport(
        session_count=len(cases),
        baseline=baseline,
        variants=rest,
        quality=quality,
        verdict=verdict,
    )
