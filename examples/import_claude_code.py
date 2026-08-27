"""Адаптер: логи сессий Claude Code -> JSONL для prefixcash.

Claude Code пишет каждую сессию в ~/.claude/projects/<project>/<session>.jsonl.
Записи ассистента несут сырой Anthropic-usage, где уже есть настоящие
cache_read_input_tokens / cache_creation_input_tokens — то есть реальный
hit rate живого агента можно померить, ничего не инструментируя.

Claude Code пишет НЕСКОЛЬКО записей на один запрос к API (блоки контента
одного ответа несут один и тот же usage), поэтому вызовы дедуплицируются
по `requestId` — без этого инпут и экономия завышаются примерно вдвое.

Тексты промптов НЕ переносятся: в них лежит рабочий код. Для `report`
и `monitor` нужен только usage.

    python -m examples.import_claude_code --out claude-code.jsonl
    prefixcash report --file claude-code.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

SOURCE = Path.home() / ".claude" / "projects"


def _anonymize(name: str) -> str:
    """Имя проекта -> устойчивый безымянный ярлык (в логах бывают клиенты)."""
    return "proj-" + hashlib.sha256(name.encode()).hexdigest()[:8]


def _records(session_file: Path, project: str, seen: set[str]) -> Iterator[dict]:
    for line in session_file.open(encoding="utf-8", errors="ignore"):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        model = message.get("model")
        if not isinstance(usage, dict) or not model or model.startswith("<"):
            continue
        request_id = entry.get("requestId")
        if request_id:
            if request_id in seen:
                continue
            seen.add(request_id)
        yield {
            "provider": "anthropic",
            "model": model,
            "usage": {
                "input_tokens": int(usage.get("input_tokens") or 0),
                "cache_read_input_tokens": int(usage.get("cache_read_input_tokens") or 0),
                "cache_creation_input_tokens": int(usage.get("cache_creation_input_tokens") or 0),
                "output_tokens": int(usage.get("output_tokens") or 0),
            },
            "session_id": entry.get("sessionId") or session_file.stem,
            "project": project,
            "agent": "claude-code",
            "ts": entry.get("timestamp"),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=Path("claude-code.jsonl"))
    parser.add_argument("--model", default=None, help="оставить только эту модель")
    args = parser.parse_args()

    written = 0
    seen: set[str] = set()
    with args.out.open("w", encoding="utf-8") as sink:
        for session_file in sorted(args.source.rglob("*.jsonl")):
            project = _anonymize(session_file.parent.name)
            for record in _records(session_file, project, seen):
                if args.model and record["model"] != args.model:
                    continue
                sink.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
    print(f"{written} calls -> {args.out}")


if __name__ == "__main__":
    main()
