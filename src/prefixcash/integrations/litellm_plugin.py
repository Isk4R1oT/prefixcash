"""LiteLLM callback: сбор cache-метрик в реальном времени (P0).

Подключение (litellm — опциональная зависимость, extra "litellm"):

    import litellm
    from prefixcash.integrations.litellm_plugin import PrefixCashCallback

    litellm.callbacks = [PrefixCashCallback(file="prefixcash.jsonl")]

Модуль импортируется без установленного litellm: hooks вызываются самим LiteLLM
по соглашению имён (log_success_event / log_failure_event).
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Mapping
from typing import Any

from prefixcash.core.metrics import CacheMetrics
from prefixcash.core.parsers.base import ParsedUsage
from prefixcash.core.parsers.deepseek import DeepSeekUsageParser
from prefixcash.core.parsers.openai import OpenAIUsageParser

MetricSink = Callable[[CacheMetrics], None]


def _usage_dict(response_obj: Any) -> Mapping:
    usage = getattr(response_obj, "usage", None)
    if usage is None:
        return {}
    if isinstance(usage, Mapping):
        return usage
    details = getattr(usage, "prompt_tokens_details", None)
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        "prompt_tokens_details": {
            "cached_tokens": getattr(details, "cached_tokens", 0) or 0,
        },
    }


def _provider_of(kwargs: Mapping) -> str:
    params = kwargs.get("litellm_params") or {}
    p = params.get("custom_llm_provider")
    if p:
        return str(p)
    model = str(kwargs.get("model") or "")
    return model.split("/", 1)[0] if "/" in model else "openai"


def _model_of(kwargs: Mapping, response_obj: Any) -> str:
    model = str(kwargs.get("model") or getattr(response_obj, "model", "") or "")
    return model.split("/", 1)[1] if "/" in model else model


def _parse(provider: str, usage: Mapping) -> ParsedUsage:
    """P0: LiteLLM нормализует usage в openai-стиль; raw deepseek — провайдерским парсером."""
    if provider.lower() == "deepseek" and "prompt_cache_hit_tokens" in usage:
        return DeepSeekUsageParser().parse(usage)
    return OpenAIUsageParser().parse(usage)


def _json_record(m: CacheMetrics) -> dict:
    return {
        "provider": m.provider,
        "model": m.model,
        "usage": {
            "input_tokens": m.input_tokens,
            "cache_read_tokens": m.cache_read_tokens,
            "cache_write_tokens": m.cache_write_tokens,
            "output_tokens": m.output_tokens,
        },
        "session_id": m.session_id,
        "agent": m.agent,
        "project": m.project,
        "ts": m.ts.isoformat(),
    }


class PrefixCashCallback:
    """Минимальный LiteLLM callback для сбора cache-метрик (P0)."""

    def __init__(
        self,
        *,
        sink: MetricSink | None = None,
        file: str | None = None,
        provider_hint: str | None = None,
    ) -> None:
        self._sink = sink
        self._file = file
        self._provider_hint = provider_hint
        self._lock = threading.Lock()
        self.metrics: list[CacheMetrics] = []

    # --- hooks LiteLLM ---
    def log_success_event(self, kwargs: dict, response_obj: Any, start_time: Any, end_time: Any) -> None:
        usage = _usage_dict(response_obj)
        if not usage:
            return
        provider = self._provider_hint or _provider_of(kwargs)
        params = kwargs.get("litellm_params") or {}
        meta = params.get("metadata") or {}
        parsed = _parse(provider, usage)
        metrics = CacheMetrics(
            provider=provider.lower(),
            model=_model_of(kwargs, response_obj),
            input_tokens=parsed.input_tokens,
            cache_read_tokens=parsed.cache_read_tokens,
            cache_write_tokens=parsed.cache_write_tokens,
            output_tokens=parsed.output_tokens,
            session_id=meta.get("session_id") or kwargs.get("session_id"),
            agent=meta.get("agent") or kwargs.get("agent"),
            project=meta.get("project") or kwargs.get("project"),
        )
        with self._lock:
            self.metrics.append(metrics)
            if self._file:
                with open(self._file, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(_json_record(metrics), ensure_ascii=False) + "\n")
        if self._sink:
            self._sink(metrics)

    def log_failure_event(self, kwargs: dict, response_obj: Any, start_time: Any, end_time: Any) -> None:
        pass  # P0: учитываем только успешные вызовы (в failure нет usage)
