"""Базовый контракт парсеров usage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True)
class ParsedUsage:
    """Нормализованные поля usage, извлечённые из пейлоада провайдера."""

    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0


class UsageParser(Protocol):
    """Парсер usage-пейлоада конкретного провайдера."""

    provider: str

    def parse(self, payload: Mapping) -> ParsedUsage: ...
