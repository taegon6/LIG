from __future__ import annotations

from scripts.evaluation_metrics import add_rolling_metrics


def test_add_rolling_metrics_uses_current_round_as_instant_sla() -> None:
    rows = [
        {"post_action_sla": 100.0, "recovery_delta": 0.0},
        {"post_action_sla": 80.0, "recovery_delta": 20.0},
    ]

    enriched = add_rolling_metrics(rows)

    assert enriched[0]["instant_sla"] == 100.0
    assert enriched[1]["instant_sla"] == 80.0


def test_add_rolling_metrics_calculates_windowed_means() -> None:
    rows = [
        {"post_action_sla": float(index), "recovery_delta": 1.0}
        for index in range(1, 12)
    ]

    enriched = add_rolling_metrics(rows)

    assert enriched[-1]["rolling_sla_10"] == 6.5
    assert enriched[-1]["rolling_sla_50"] == 6.0
    assert enriched[-1]["rolling_recovery_delta"] == 1.0
