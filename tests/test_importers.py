import json

from prefixcash.integrations.importers import iter_jsonl


def test_import_litellm_style(tmp_path):
    log = tmp_path / "log.jsonl"
    log.write_text(
        json.dumps(
            {
                "model": "gpt-4o",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 10,
                    "prompt_tokens_details": {"cached_tokens": 60},
                },
                "metadata": {"session_id": "s1", "agent": "sales"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    ms = list(iter_jsonl(log))
    assert len(ms) == 1
    assert ms[0].provider == "openai"
    assert ms[0].session_id == "s1"
    assert ms[0].agent == "sales"
    assert ms[0].cache_read_tokens == 60


def test_import_normalized_format(tmp_path):
    log = tmp_path / "n.jsonl"
    log.write_text(
        json.dumps(
            {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "usage": {"input_tokens": 500, "cache_read_tokens": 450, "cache_write_tokens": 0, "output_tokens": 20},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    ms = list(iter_jsonl(log))
    assert len(ms) == 1
    assert ms[0].provider == "deepseek"
    assert ms[0].hit_rate == 0.9


def test_import_infers_provider_from_model(tmp_path):
    log = tmp_path / "m.jsonl"
    deepseek = {
        "model": "deepseek-chat",
        "usage": {"prompt_tokens": 100, "completion_tokens": 5, "prompt_cache_hit_tokens": 90},
    }
    claude = {
        "model": "claude-sonnet-4-5",
        "usage": {"prompt_tokens": 50, "completion_tokens": 3, "prompt_tokens_details": {"cached_tokens": 40}},
    }
    log.write_text("\n".join(json.dumps(r) for r in [deepseek, claude]) + "\n", encoding="utf-8")
    ms = list(iter_jsonl(log))
    assert ms[0].provider == "deepseek"
    assert ms[0].hit_rate == 0.9
    assert ms[1].provider == "anthropic"
    assert ms[1].cache_read_tokens == 40


def test_import_raw_anthropic_usage_keeps_cache_tokens(tmp_path):
    """Сырой Anthropic-usage несёт и `input_tokens`, и свои cache-поля.

    Регресс: он уходил в ветку нормализованного формата и терял
    cache_read/cache_write — тихий 0% hit rate у провайдера с самой
    большой скидкой на кеш.
    """
    log = tmp_path / "anthropic_raw.jsonl"
    log.write_text(
        json.dumps(
            {
                "provider": "anthropic",
                "model": "claude-opus-4-8",
                "usage": {
                    "input_tokens": 2,
                    "cache_creation_input_tokens": 35223,
                    "cache_read_input_tokens": 20262,
                    "output_tokens": 283,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (metrics,) = list(iter_jsonl(log))
    assert metrics.cache_read_tokens == 20262
    assert metrics.cache_write_tokens == 35223
    # весь промпт = 2 (некешированный остаток) + 20262 (read) + 35223 (write)
    assert metrics.input_tokens == 55487
    assert 0.0 < metrics.hit_rate < 1.0


def test_import_normalized_usage_still_parsed(tmp_path):
    """Формат после `prefixcash import` не должен пострадать от фикса выше."""
    log = tmp_path / "normalized.jsonl"
    log.write_text(
        json.dumps(
            {
                "provider": "anthropic",
                "model": "claude-opus-4-8",
                "usage": {
                    "input_tokens": 2,
                    "cache_write_tokens": 35223,
                    "cache_read_tokens": 20262,
                    "output_tokens": 283,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (metrics,) = list(iter_jsonl(log))
    assert metrics.cache_read_tokens == 20262
    assert metrics.cache_write_tokens == 35223
