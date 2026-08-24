"""Оптимизация: кеш-осведомлённая маршрутизация и батч-порядок (P2, D22/D23).

Advisory-first (D18): всё — рекомендации; ничего не применяется автоматически.
"""

from prefixcash.optimize.batch import PrefixGroup, group_by_prefix, suggest_order
from prefixcash.optimize.routing import ProviderScore, cache_friendliness, recommend

__all__ = ["PrefixGroup", "ProviderScore", "cache_friendliness", "group_by_prefix", "recommend", "suggest_order"]
