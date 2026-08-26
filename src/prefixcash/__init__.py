"""prefixcash — prefix-cache economics for LLM applications.

A small, focused library that closes one problem: finding and fixing the money
your LLM app leaks through a broken prompt prefix cache.

Four verbs:

- **measure** — hit rate + $ saved vs a cold baseline, from a log or a callback;
- **diagnose** — where in the prompt the prefix breaks between calls, and why;
- **fix (advisory)** — heatmap, assembly suggestions, routing, batch ordering;
- **prove** — replay fix variants on a staging sample and get a verdict.

Typical use:

    import litellm
    from prefixcash import PrefixCashCallback, measure_log, diagnose_log

    litellm.callbacks = [PrefixCashCallback(file="metrics.jsonl")]  # drop-in

    report = measure_log("metrics.jsonl")       # $ saved vs cold baseline
    findings = diagnose_log("metrics.jsonl")    # leaks inside sessions
"""

from prefixcash.cli.report import Report, build_report
from prefixcash.core.metrics import CacheMetrics
from prefixcash.core.parsers import parse_usage, to_metrics
from prefixcash.core.pricing import PRICING, CostBreakdown, cost
from prefixcash.diagnose.assembly import AssemblySuggestion, lint
from prefixcash.diagnose.calls import CallRecord
from prefixcash.diagnose.engine import analyze_calls, group_by_session
from prefixcash.diagnose.heatmap import PromptHeatmap, build_heatmap
from prefixcash.diagnose.rules import BreakCause, Finding, analyze_session
from prefixcash.integrations.importers import iter_calls, iter_jsonl
from prefixcash.integrations.litellm_plugin import PrefixCashCallback
from prefixcash.optimize.batch import PrefixGroup, group_by_prefix, suggest_order
from prefixcash.optimize.experiment import (
    CallResult,
    ExperimentReport,
    SessionCase,
    VariantResult,
    run_experiment,
)
from prefixcash.optimize.routing import ProviderScore, cache_friendliness, recommend

__version__ = "0.2.1"0.2.0"


def measure_log(path: str) -> Report:
    """Measure hit rate and $ saved from a JSONL log (the report artifact).

    Accepts raw provider usage, LiteLLM-normalized usage, or prefixcash's own
    normalized format (see `prefixcash.integrations.importers`).
    """
    return build_report(list(iter_jsonl(path)))


def diagnose_log(path: str) -> dict[str, list[Finding]]:
    """Diagnose prefix breakage inside sessions from a JSONL log (D21).

    Returns {session_id: [Finding]} — where the prefix diverged, the cause, and
    advisory fix variants (D18).
    """
    return analyze_calls(list(iter_calls(path)))


__all__ = [
    "__version__",
    # measure
    "CacheMetrics",
    "CostBreakdown",
    "PRICING",
    "Report",
    "build_report",
    "cost",
    "measure_log",
    "parse_usage",
    "to_metrics",
    # diagnose
    "AssemblySuggestion",
    "BreakCause",
    "CallRecord",
    "Finding",
    "PromptHeatmap",
    "analyze_calls",
    "analyze_session",
    "build_heatmap",
    "diagnose_log",
    "group_by_session",
    "lint",
    # fix
    "PrefixGroup",
    "ProviderScore",
    "cache_friendliness",
    "group_by_prefix",
    "recommend",
    "suggest_order",
    # prove
    "CallResult",
    "ExperimentReport",
    "SessionCase",
    "VariantResult",
    "run_experiment",
    # integrations
    "PrefixCashCallback",
    "iter_calls",
    "iter_jsonl",
]
