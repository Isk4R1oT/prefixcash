"""Сценарии бенчмарка prefixcash: сложные кейсы поломки префикс-кеша.

Каждый сценарий = набор сессий + сборщик system-промпта в двух вариантах:
- baseline — «сломанная» сборка (динамика в начале / нестабильный порядок);
- fixed — исправленная сборка (статический префикс, динамика в конце).

`expected_causes` — какие причины должна найти диагностика в baseline (офлайн).
"""

from __future__ import annotations

import random
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from prefixcash.optimize.experiment import SessionCase

KB_WORDS = (
    ["каталог", "товар", "описание", "цена", "скидка", "артикул", "наличие", "поставщик", "гарантия", "доставка"]
    * 160
)
KB = " ".join(KB_WORDS)

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "claude_quant_l2_prompt.txt"


@dataclass
class Scenario:
    """Один сценарий бенчмарка."""

    name: str
    description: str
    expected_causes: list[str]  # причины, которые должна найти диагностика в baseline
    sessions: list[dict]  # [{"session_id": ..., "turns": [...]}]
    build_system: Callable[[str, str], str]  # (version, session_id) -> system_prompt
    max_turns: int = 3


def _kb_system(version: str, sid: str, head: str, dyn: str) -> str:
    persona = "Ты AI-продавец. Отвечай коротко и по делу."
    if version == "baseline":
        return f"{head}: {dyn}. {persona}\n\nБаза знаний:\n{KB}"
    return f"{persona}\n\nБаза знаний:\n{KB}\n[{head}: {dyn}]"


def build_timestamp(version: str, sid: str) -> str:
    return _kb_system(version, sid, "Сейчас", datetime.now().isoformat(timespec="microseconds"))


def build_uuid(version: str, sid: str) -> str:
    return _kb_system(version, sid, "Session", str(uuid.uuid4()))


def build_kb_reorder(version: str, sid: str) -> str:
    persona = "Ты AI-продавец. Отвечай коротко и по делу."
    if version == "baseline":
        rng = random.Random(datetime.now().isoformat(timespec="microseconds") + sid)
        words = KB.split()
        rng.shuffle(words)
        return f"{persona}\n\nБаза знаний:\n{' '.join(words)}"
    return f"{persona}\n\nБаза знаний:\n{KB}"


def build_short(version: str, sid: str) -> str:
    # Короткий промпт (<1024 токенов): кеш провайдера не включается — обе версии одинаковы.
    return "Ты короткий ассистент. Отвечай кратко."


def build_real(version: str, sid: str) -> str:
    # Реальный системный промпт (claude-quant, L2 summariser): статичный по природе.
    base = _FIXTURE.read_text(encoding="utf-8").strip()
    ts = datetime.now().isoformat(timespec="microseconds")
    if version == "baseline":
        return f"Сейчас: {ts}.\n{base}"
    return f"{base}\n[метаданные: {ts}]"


SCENARIOS: list[Scenario] = [
    Scenario(
        name="sales-timestamp",
        description="Динамический timestamp в начале system-промпта ломает кеш; фикс — динамика в конец.",
        expected_causes=["dynamic_iso_datetime"],
        sessions=[
            {"session_id": f"chat-{i}", "turns": ["Сколько стоит SKU-001?", "А есть скидки?", "Как оплатить?"]}
            for i in range(3)
        ],
        build_system=build_timestamp,
    ),
    Scenario(
        name="sales-uuid",
        description="session-id/uuid в начале префикса; фикс — в метаданные/конец.",
        expected_causes=["dynamic_uuid"],
        sessions=[
            {"session_id": f"chat-{i}", "turns": ["Что в наличии?", "Цена SKU-002?", "Гарантия?"]}
            for i in range(3)
        ],
        build_system=build_uuid,
    ),
    Scenario(
        name="kb-reorder",
        description="Случайный порядок базы знаний каждый вызов ломает токен-совпадение; фикс — стабильный порядок.",
        expected_causes=["content_change"],
        sessions=[{"session_id": f"chat-{i}", "turns": ["Сколько стоит?", "Доставка?"]} for i in range(3)],
        build_system=build_kb_reorder,
    ),
    Scenario(
        name="short-prompt",
        description=(
            "Короткий промпт (<1024 токенов): кеш не включается — диагност молчит, "
            "эксперимент честно показывает отсутствие выигрыша."
        ),
        expected_causes=[],
        sessions=[{"session_id": f"chat-{i}", "turns": ["Привет", "Пока"]} for i in range(2)],
        build_system=build_short,
        max_turns=2,
    ),
    Scenario(
        name="real-framework",
        description=(
            "Реальный системный промпт (claude-quant, L2 summariser, ~3.9K токенов): "
            "статичен; baseline вставляет timestamp в начало."
        ),
        expected_causes=["dynamic_iso_datetime"],
        sessions=[
            {"session_id": f"l2-{i}", "turns": ["Спроецируй L2", "Обнови watchlist"]}
            for i in range(2)
        ],
        build_system=build_real,
        max_turns=2,
    ),
]


def to_cases(scenario: Scenario) -> list[SessionCase]:
    """Строит выборку SessionCase для эксперимента (provider/model по умолчанию DeepSeek)."""
    return [
        SessionCase(
            session_id=s["session_id"],
            system_prompt=scenario.build_system("baseline", s["session_id"]),
            turns=s["turns"],
            provider="deepseek",
            model="deepseek-chat",
        )
        for s in scenario.sessions
    ]
