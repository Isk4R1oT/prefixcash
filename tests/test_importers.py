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
