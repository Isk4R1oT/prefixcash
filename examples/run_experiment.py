"""Запуск experiment.py на реальном DeepSeek: broken vs fixed системный промпт.

    export DEEPSEEK_API_KEY=sk-...   # или .env рядом
    uv run python examples/run_experiment.py

Что происходит: реплей 2 сессий x 2 хода в двух вариантах (broken/fixed),
замер hit rate по usage DeepSeek, LLM-as-judge качества, вердикт APPLY/DON'T.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

from examples.sales_prompts import STAGING_SESSIONS, build_system_prompt
from prefixcash.optimize.experiment import SessionCase, run_experiment


def load_api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("DEEPSEEK_API_KEY не задан: export DEEPSEEK_API_KEY=sk-... или .env")


class DeepSeekClient:
    """Минимальный OpenAI-совместимый клиент (urllib, без зависимостей)."""

    def __init__(self, api_key: str, model: str = "deepseek-chat") -> None:
        self._key = api_key
        self._model = model

    def complete(self, messages: list[dict]) -> tuple[str, dict]:
        body = json.dumps({"model": self._model, "messages": messages, "max_tokens": 120, "temperature": 0.2}).encode()
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=body,
            headers={"Authorization": "Bearer " + self._key, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
        text = data["choices"][0]["message"]["content"] or ""
        return text, data.get("usage", {})


def prompt_for(variant: str, session_id: str) -> str:
    """Вариант сборки system-промпта: baseline=broken, fixed=исправленный."""
    if variant == "baseline":
        return build_system_prompt("broken")
    if variant == "fixed":
        return build_system_prompt("fixed")
    raise ValueError(variant)


def main() -> None:
    key = load_api_key()
    client = DeepSeekClient(key)
    cases = [
        SessionCase(
            session_id=s["session_id"],
            system_prompt=build_system_prompt("broken"),
            turns=s["turns"],
            provider="deepseek",
            model="deepseek-chat",
        )
        for s in STAGING_SESSIONS
    ]
    report = run_experiment(cases, client, judge=client, prompt_for=prompt_for)
    print(report.render_md())


if __name__ == "__main__":
    main()
