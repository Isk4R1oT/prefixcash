"""Тесты experiment.py на фейковом клиенте (без сети)."""

from prefixcash.optimize.experiment import SessionCase, judge_pairwise, run_experiment


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


class TieJudge:
    def complete(self, messages: list[dict]) -> tuple[str, dict]:
        return '{"choice": "tie"}', {}


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
    report = run_experiment(_cases(), client, prompt_for=_prompt_for, judge=TieJudge())
    assert report.baseline.hit_rate < report.variants[0].hit_rate
    assert report.variants[0].hit_rate > 0.5
    assert "APPLY" in report.verdict


def test_quality_pairs_counted():
    client = FakeClient()
    report = run_experiment(_cases(), client, prompt_for=_prompt_for, judge=TieJudge())
    # 2 сессии x 2 хода = 4 пары для судьи
    assert report.quality.total == 4
    assert report.quality.ties == 4
    assert report.quality.variant_not_worse


def test_report_md_contains_verdict():
    client = FakeClient()
    report = run_experiment(_cases(), client, prompt_for=_prompt_for, judge=TieJudge())
    md = report.render_md()
    assert "APPLY" in md
    assert "hit %" in md


def test_judge_pairwise_parses_choice():
    class Judge:
        def complete(self, messages: list[dict]) -> tuple[str, dict]:
            return '{"choice": "second"}', {}

    assert judge_pairwise(Judge(), "q", "a", "b") == "second"


def test_verdict_dont_apply_when_variant_worse():
    def worse_prompt(variant: str, session_id: str) -> str:
        if variant == "baseline":
            return STATIC
        _counter["n"] += 1
        return f"ломалка: {_counter['n']:020d}. {STATIC}"  # ломает префикс в начале

    client = FakeClient()
    report = run_experiment(_cases(), client, prompt_for=worse_prompt, judge=TieJudge())
    assert report.variants[0].hit_rate < report.baseline.hit_rate
    assert "DON'T APPLY" in report.verdict
