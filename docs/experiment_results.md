# Aegis-Swarm v2 Experiment Results

## Experiment Command

```bash
python scripts/run_experiments.py --rounds 100 --seed 42
```

The experiment uses FastAPI `TestClient` and a local SQLite experiment database. It does not require Docker and does not contact external targets.

## Summary Metrics

| Metric | Value |
| --- | ---: |
| Rounds | 100 |
| Seed | 42 |
| Average SLA | 100.00 |
| Average SLA Drop | 7.54 |
| Average Recovery Delta | 8.00 |
| Average Utility | 70.73 |
| False Positive Rate | 0.000 |
| Recovery Success Rate | 1.000 |
| Scenario Entropy | 64.30 |
| Coverage Score | 100.00 |

## Early-vs-Late Comparison

| Window | Average SLA | Blue Success Rate | Red Success Rate | Average Recovery Delta | False Positive Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rounds 1-20 | 100.00 | 1.000 | 0.000 | 0.00 | 0.000 |
| Rounds 81-100 | 100.00 | 1.000 | 0.200 | 20.00 | 0.000 |

## Per-Scenario Summary

| Scenario | Attempts | Average SLA | Average SLA Drop | Average Recovery Delta | Average Utility | Action Accuracy | False Positive Rate | Recovery Success Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AUTH_ANOMALY | 3 | 100.00 | 0.00 | 0.00 | 71.30 | 1.000 | 0.000 | 1.000 |
| LOG_NOISE | 51 | 100.00 | 0.00 | 0.00 | 72.00 | 1.000 | 0.000 | 1.000 |
| MISSION_COMMAND_ANOMALY | 2 | 100.00 | 0.00 | 0.00 | 71.35 | 1.000 | 0.000 | 1.000 |
| SERVICE_DEGRADATION | 36 | 100.00 | 20.94 | 22.22 | 68.76 | 1.000 | 0.000 | 1.000 |
| TELEMETRY_INCONSISTENCY | 4 | 100.00 | 0.00 | 0.00 | 71.00 | 1.000 | 0.000 | 1.000 |
| TRAFFIC_SPIKE | 4 | 100.00 | 0.00 | 0.00 | 71.40 | 1.000 | 0.000 | 1.000 |

## Balanced Scenario Evaluation

Adaptive self-play is useful for demonstrating curriculum behavior, because the Commander and Red Agent can shift toward recovery, exploration, or hardening based on recent results. That also means the scenario mix can become imbalanced. The balanced evaluation below is separate evidence: it fixes the scenario schedule so every safe event type is tested exactly 20 times with the same Blue policy and v2 scoring model.

```bash
python scripts/run_balanced_evaluation.py --rounds-per-scenario 20 --seed 42
```

The balanced run created 120 total local simulation rounds. No external target interaction, scanning, exploit payload, credential attack, or malware behavior is used.

| Scenario | Attempts | Action Accuracy | Average SLA | Average SLA Drop | Average Recovery Delta | Average Utility | False Positive Rate | Recovery Success Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| TRAFFIC_SPIKE | 20 | 1.000 | 100.00 | 0.00 | 0.00 | 71.40 | 0.000 | 1.000 |
| AUTH_ANOMALY | 20 | 1.000 | 100.00 | 0.00 | 0.00 | 71.30 | 0.000 | 1.000 |
| TELEMETRY_INCONSISTENCY | 20 | 1.000 | 100.00 | 5.00 | 5.00 | 70.84 | 0.000 | 1.000 |
| SERVICE_DEGRADATION | 20 | 1.000 | 100.00 | 79.10 | 100.00 | 62.35 | 0.000 | 1.000 |
| MISSION_COMMAND_ANOMALY | 20 | 1.000 | 100.00 | 0.00 | 0.00 | 71.50 | 0.000 | 1.000 |
| LOG_NOISE | 20 | 1.000 | 100.00 | 0.00 | 0.00 | 72.00 | 0.000 | 1.000 |

Balanced evaluation highlights per-scenario defense stability. `TRAFFIC_SPIKE` now consistently maps to `APPLY_RATE_LIMIT`, `AUTH_ANOMALY` maps to `BLOCK_SUSPICIOUS_TOKEN`, `MISSION_COMMAND_ANOMALY` maps to deception/escalation rather than service restart, and `LOG_NOISE` remains observe-only with a 0.000 false positive rate. `SERVICE_DEGRADATION` intentionally creates the largest immediate SLA disruption, then demonstrates full local recovery through the post-action `RECOVERY_HEALTH_CHECK`.

## Interpretation for DAH Preliminary Report

The 100-round run shows that Aegis-Swarm v2 maintains post-action SLA at 100% while still exercising all six safe simulated scenario types. The service degradation scenario caused the clearest SLA impact, with an average SLA drop of 20.94 points and average recovery delta of 22.22 points. This demonstrates that the post-action `RECOVERY_HEALTH_CHECK` model is measurable rather than decorative.

False positives remained 0.000 after Blue Agent was hardened to prioritize the latest unrecovered active event while treating `RECOVERY_HEALTH_CHECK` as a boundary for already-handled history. This avoids both stale-event overreaction and passive observation for fresh simulated pressure.

Scenario coverage reached 100%, and scenario entropy reached 64.30. Action accuracy improved to 1.000 for every scenario in this deterministic run, including `TRAFFIC_SPIKE` and `MISSION_COMMAND_ANOMALY`. The remaining improvement target is gathering more samples for low-frequency scenarios and tuning service-degradation scoring so temporary pre-recovery disruption is separated more clearly from final mission recovery.

Generated evidence files:

- `reports/round_metrics.csv`
- `reports/scenario_summary.csv`
- `reports/balanced_round_metrics.csv`
- `reports/balanced_scenario_summary.csv`
