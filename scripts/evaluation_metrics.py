from __future__ import annotations

from statistics import mean
from typing import Any


ROLLING_COLUMNS = [
    "instant_sla",
    "rolling_sla_10",
    "rolling_sla_50",
    "rolling_recovery_delta",
]


def add_rolling_metrics(
    rows: list[dict[str, Any]],
    *,
    sla_key: str = "post_action_sla",
    recovery_key: str = "recovery_delta",
    recovery_window: int = 10,
) -> list[dict[str, Any]]:
    """Add rolling SLA evidence columns in round order.

    `instant_sla` is the final SLA for the current evaluated round. The rolling
    values include the current round and all available prior rounds in the
    requested window.
    """

    enriched: list[dict[str, Any]] = []
    sla_history: list[float] = []
    recovery_history: list[float] = []
    for row in rows:
        enriched_row = dict(row)
        instant_sla = float(row.get(sla_key, 0.0))
        recovery_delta = float(row.get(recovery_key, 0.0))
        sla_history.append(instant_sla)
        recovery_history.append(recovery_delta)

        enriched_row["instant_sla"] = round(instant_sla, 2)
        enriched_row["rolling_sla_10"] = round(mean(sla_history[-10:]), 2)
        enriched_row["rolling_sla_50"] = round(mean(sla_history[-50:]), 2)
        enriched_row["rolling_recovery_delta"] = round(mean(recovery_history[-recovery_window:]), 2)
        enriched.append(enriched_row)
    return enriched
