from __future__ import annotations

from core.scoring import calculate_total_utility


def test_scoring_utility_formula() -> None:
    total = calculate_total_utility(
        defense_score=80,
        attack_score=60,
        sla_score=95,
        recovery_score=70,
        false_positive_penalty=10,
    )

    assert total == 76.5
