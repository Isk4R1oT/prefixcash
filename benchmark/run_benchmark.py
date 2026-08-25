"""Живой бенчмарк prefixcash: реплей всех сценариев через DeepSeek.

Результаты пишутся в benchmark/RESULTS.md (report cards для README при публикации).

    export DEEPSEEK_API_KEY=sk-...
    uv run python -m benchmark.run_benchmark
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from examples.run_experiment import DeepSeekClient, load_api_key

from benchmark.scenarios import SCENARIOS, to_cases
from benchmark.verify_diagnose import detect_causes
from prefixcash.optimize.experiment import run_experiment

OUT = Path(__file__).resolve().parent / "RESULTS.md"


def main() -> None:
    client = DeepSeekClient(load_api_key())
    cards: list[str] = []
    for sc in SCENARIOS:
        report = run_experiment(
            to_cases(sc),
            client,
            prompt_for=sc.build_system,
            max_turns=sc.max_turns,
        )
        causes = detect_causes(sc)
        print(f"\n=== {sc.name} ===")
        print(report.render_md())
        card = (
            f"| {sc.name} | {', '.join(causes) or '—'} | "
            f"{report.baseline.hit_rate:.1%} | {report.best_variant.hit_rate:.1%} | "
            f"{report.hit_rate_delta:+.1%} | ${report.saved_delta_usd:.4f} | {report.verdict.split('.')[0]} |"
        )
        cards.append(card)

    lines = [
        "# prefixcash benchmark — report cards",
        "",
        f"Дата: {datetime.now().isoformat(timespec='minutes')} · провайдер: DeepSeek (deepseek-chat) · ",
        "порог автоматического кеша: префикс ≥ ~1024 токенов (проверено отдельно).",
        "",
        "| сценарий | диагноз (что ломает) | hit% baseline | hit% fixed | Δ | saved $ (выборка) | вердикт |",
        "|---|---:|---:|---:|---:|---:|---|",
        *cards,
        "",
        "Примечания:",
        "- Диагноз — результат офлайн-проверки диагностики (`benchmark/verify_diagnose.py`).",
        "- `short-prompt` — намеренный негативный кейс: кеш не включается на коротких промптах.",
        "- Экономия приведена на выборке бенчмарка; экстраполяция на прод — по вашей нагрузке.",
        "- Числа зависят от состояния кеша провайдера (TTL) и порядка прогонов (см. METHODOLOGY.md).",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRESULTS.md записан: {OUT}")


if __name__ == "__main__":
    main()
