"""Тесты experiment.py на фейковом клиенте (без сети)."""

from prefixcash.optimize.experiment import SessionCase, run_experiment


class FakeClient:
    """Имитация DeepSeek: cache hit = длина общего префикса с предыдущим вызовом.

    baseline-промпт меняется на каждый вызов -> hits ~0;
    fixed-промпт имеет длинный стабильный префикс -> hits большие.
    """

    def __init__(self) -> None:
        self._prev_words: list[str] | None = None
        self.calls = 0

    def complete(self, messages: list[dict]) -> tuple[str, dict]:
        self.calls += 1
        prompt = "\n".join(str(m.get("content", "")) for m in messages)
        words = prompt.split()
        hit = 0
        if self._prev_words is not None:
            n = 0
            for a, b in zip(self._prev_words, words, strict=False):
                if a != b:
                    break
                n += 1
            hit = n * 2
        self._prev_words = words
        usage = {
            "prompt_tokens": len(words) * 2,
            "completion_tokens": 10,
            "prompt_cache_hit_tokens": hit,
            "prompt_cache_miss_tokens": len(words) * 2 - hit,
        }
        return "Ответ.", usage


STATIC = "static base " + "x" * 120
_counter = {"n": 0}


def _prompt_for(variant: str, session_id: str) -> str:
    if variant == "baseline":
        _counter["n"] += 1
        return f"время: {_counter['n']:020d}. {STATIC}"  # меняется каждый вызов
    return f"{STATIC} [метаданные: {session_id}]"


def _cases():
    return [
        SessionCase("chat-1", STATIC, ["вопрос 1", "вопрос 2"]),
        SessionCase("chat-2", STATIC, ["вопрос 3", "вопрос 4"]),
    ]


def test_fixed_beats_baseline_on_hit_rate():
    client = FakeClient()
    report = run_experiment(_cases(), client, prompt_for=_prompt_for)
    assert report.baseline.hit_rate < report.variants[0].hit_rate
    assert report.variants[0].hit_rate > 0.5
    assert "FIX WORKS" in report.verdict


def test_report_md_contains_economics():
    client = FakeClient()
    report = run_experiment(_cases(), client, prompt_for=_prompt_for)
    md = report.render_md()
    assert "Sample savings" in md
    assert "hit %" in md
    assert report.saved_delta_usd > 0


def test_verdict_no_gain_when_variant_worse():
    def worse_prompt(variant: str, session_id: str) -> str:
        if variant == "baseline":
            return STATIC
        _counter["n"] += 1
        return f"ломалка: {_counter['n']:020d}. {STATIC}"  # ломает префикс в начале

    client = FakeClient()
    report = run_experiment(_cases(), client, prompt_for=worse_prompt)
    assert report.variants[0].hit_rate < report.baseline.hit_rate
    assert "NO GAIN" in report.verdict
