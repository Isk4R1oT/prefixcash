"""prefixcash — слой экономики префикс-кеша для LLM-приложений.

Measure, diagnose and fix your LLM prompt-cache hit rate — and see the dollars you save.
"""

from prefixcash.core.metrics import CacheMetrics
from prefixcash.core.parsers import parse_usage, to_metrics
from prefixcash.core.pricing import PRICING, CostBreakdown, cost

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "CacheMetrics",
    "CostBreakdown",
    "PRICING",
    "cost",
    "parse_usage",
    "to_metrics",
]
