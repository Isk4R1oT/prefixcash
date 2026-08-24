import json
from pathlib import Path

from prefixcash.core.parsers import parse_usage

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "deepseek_usage.json"


def test_deepseek_parse_cache_hit():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))["usage"]
    parsed = parse_usage("deepseek", payload)
    assert parsed.input_tokens == 900
    assert parsed.cache_read_tokens == 810
    assert parsed.output_tokens == 120


def test_deepseek_parse_missing_cache_fields():
    parsed = parse_usage("deepseek", {"prompt_tokens": 5, "completion_tokens": 1})
    assert parsed.cache_read_tokens == 0
