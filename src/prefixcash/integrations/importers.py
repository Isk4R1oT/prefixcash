"""Импорт логов в CacheMetrics: JSONL (LiteLLM / OpenRouter / сырые записи / формат prefixcash)."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from datetime import datetime
from pathlib import Path

from prefixcash.core.metrics import CacheMetrics
from prefixcash.core.parsers import to_metrics
from prefixcash.diagnose.calls import CallRecord, prompt_from_messages

_MODEL_PREFIX_PROVIDERS = (
    ("deepseek", "deepseek"),
    ("gpt", "openai"),
    ("o1", "openai"),
    ("o3", "openai"),
    ("o4", "openai"),
    ("claude", "anthropic"),
    ("gemini", "gemini"),
)


def _provider_from_model(model: str) -> str | None:
    low = model.lower()
    for prefix, provider in _MODEL_PREFIX_PROVIDERS:
        if low.startswith(prefix):
            return provider
    return None


def _provider_of_record(record: Mapping) -> str:
    p = record.get("provider")
    if p:
        return str(p)
    llm_params = record.get("litellm_params") or {}
    p = llm_params.get("custom_llm_provider")
    if p:
        return str(p)
    model = str(record.get("model") or "")
    if "/" in model:
        return model.split("/", 1)[0]
    inferred = _provider_from_model(model)
    if inferred is not None:
        return inferred
    return "openai"


def _model_of_record(record: Mapping) -> str:
    model = str(record.get("model") or "")
    return model.split("/", 1)[1] if "/" in model else model


def _ts_of_record(record: Mapping) -> datetime | None:
    ts = record.get("ts")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts))
    except ValueError:
        return None


def _iter_records(path: str | Path) -> Iterator[dict]:
    """Читает JSONL: по строке — словарь записи."""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _metrics_from_record(record: Mapping) -> CacheMetrics | None:
    """Строит CacheMetrics из записи (провайдерский ИЛИ нормализованный usage)."""
    usage = record.get("usage")
    if not usage:
        return None
    if "input_tokens" in usage:
        # наш нормализованный формат (после `prefixcash import`)
        kw: dict = {
            "provider": str(record.get("provider") or "unknown"),
            "model": str(record.get("model") or ""),
            "input_tokens": int(usage.get("input_tokens", 0) or 0),
            "cache_read_tokens": int(usage.get("cache_read_tokens", 0) or 0),
            "cache_write_tokens": int(usage.get("cache_write_tokens", 0) or 0),
            "output_tokens": int(usage.get("output_tokens", 0) or 0),
            "session_id": record.get("session_id"),
            "agent": record.get("agent"),
            "project": record.get("project"),
        }
        ts = _ts_of_record(record)
        if ts is not None:
            kw["ts"] = ts
        return CacheMetrics(**kw)
    meta = record.get("metadata") or {}
    return to_metrics(
        _provider_of_record(record),
        _model_of_record(record),
        usage,
        session_id=meta.get("session_id") or record.get("session_id"),
        agent=meta.get("agent") or record.get("agent"),
        project=meta.get("project") or record.get("project"),
    )


def iter_jsonl(path: str | Path) -> Iterator[CacheMetrics]:
    """Читает JSONL: метрики вызовов (для report/monitor)."""
    for record in _iter_records(path):
        metrics = _metrics_from_record(record)
        if metrics is not None:
            yield metrics


def iter_calls(path: str | Path) -> Iterator[CallRecord]:
    """Читает JSONL: вызовы с промптами (для diagnose, D21)."""
    for record in _iter_records(path):
        metrics = _metrics_from_record(record)
        if metrics is None:
            continue
        prompt = record.get("prompt")
        if not prompt and record.get("messages"):
            prompt = prompt_from_messages(record.get("messages"))
        yield CallRecord(metrics=metrics, prompt=str(prompt) if prompt else None)
