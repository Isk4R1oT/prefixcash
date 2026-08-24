"""Промпты продавца для демо: длинная «база знаний» (чтобы кеш работал, нужен
префикс >= ~1024 токенов) и два режима сборки system-промпта.

- broken: timestamp в НАЧАЛЕ system-промпта, перегенерируется на каждый вызов
  -> префикс ломается на каждом ходу -> hit rate ~0.
- fixed: статичная часть + динамика в КОНЦЕ -> длинный стабильный префикс
  -> кеш попадает (проверено: DeepSeek кеширует при повторе).
"""

from datetime import datetime

# «База знаний»: 1600 слов — префикс ~3.8K токенов (порог кеша DeepSeek).
KB_WORDS = (
    ["каталог", "товар", "описание", "цена", "скидка", "артикул", "наличие", "поставщик", "гарантия", "доставка"]
    * 160
)
KB = " ".join(KB_WORDS)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_price",
            "description": "Вернуть цену товара по артикулу (SKU)",
            "parameters": {
                "type": "object",
                "properties": {"sku": {"type": "string"}},
                "required": ["sku"],
            },
        },
    }
]


def now_ts() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def build_system_prompt(version: str) -> str:
    """Собирает system-промпт продавца: broken — ts в начале, fixed — в конце."""
    persona = "Ты AI-продавец. Отвечай коротко и по делу. Используй инструмент get_price для цен."
    ts = now_ts()
    if version == "broken":
        return f"Сейчас: {ts}. {persona}\n\nБаза знаний:\n{KB}"
    if version == "fixed":
        return f"{persona}\n\nБаза знаний:\n{KB}\n[метаданные: {ts}]"
    raise ValueError(f"unknown version: {version}")


STAGING_SESSIONS = [
    {
        "session_id": "chat-1",
        "turns": ["Здравствуйте, сколько стоит товар с артикулом SKU-001?", "А есть скидки?"],
    },
    {
        "session_id": "chat-2",
        "turns": ["Что из товаров сейчас в наличии?", "Как можно оплатить?"],
    },
]
