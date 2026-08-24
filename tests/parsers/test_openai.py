import json
from pathlib import Path

from prefixcash.core.parsers import parse_usage

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "openai_usage.json"


def test_openai_parse_cached_tokens():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))["usage"]
    parsed = parse_usage("openai", payload)
    assert parsed.input_tokens == 1000
    assert parsed.cache_read_tokens == 640
    assert parsed.output_tokens == 150


def test_openai_parse_missing_details():
    parsed = parse_usage("openai", {"prompt_tokens": 10, "completion_tokens": 2})
    assert parsed.cache_read_tokens == 0
