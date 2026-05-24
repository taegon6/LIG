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
| Average Utility | 69.61 |
| False Positive Rate | 0.000 |
| Recovery Success Rate | 1.000 |
| Scenario Entropy | 64.30 |
| Coverage Score | 100.00 |

## Early-vs-Late Comparison

| Window | Average SLA | Blue Success Rate | Red Success Rate | Average Recovery Delta | False Positive Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rounds 1-20 | 100.00 | 0.950 | 0.000 | 0.00 | 0.000 |
| Rounds 81-100 | 100.00 | 0.900 | 0.000 | 20.00 | 0.000 |

## Per-Scenario Summary

| Scenario | Attempts | Average SLA | Average SLA Drop | Average Recovery Delta | Average Utility | Action Accuracy | False Positive Rate | Recovery Success Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AUTH_ANOMALY | 3 | 100.00 | 0.00 | 0.00 | 64.27 | 0.667 | 0.000 | 1.000 |
| LOG_NOISE | 51 | 100.00 | 0.00 | 0.00 | 72.00 | 1.000 | 0.000 | 1.000 |
| MISSION_COMMAND_ANOMALY | 2 | 100.00 | 0.00 | 0.00 | 60.62 | 0.500 | 0.000 | 1.000 |
| SERVICE_DEGRADATION | 36 | 100.00 | 20.94 | 22.22 | 68.44 | 0.972 | 0.000 | 1.000 |
| TELEMETRY_INCONSISTENCY | 4 | 100.00 | 0.00 | 0.00 | 71.50 | 1.000 | 0.000 | 1.000 |
| TRAFFIC_SPIKE | 4 | 100.00 | 0.00 | 0.00 | 56.25 | 0.250 | 0.000 | 1.000 |

## Interpretation for DAH Preliminary Report

The 100-round run shows that Aegis-Swarm v2 maintains post-action SLA at 100% while still exercising all six safe simulated scenario types. The service degradation scenario caused the clearest SLA impact, with an average SLA drop of 20.94 points and average recovery delta of 22.22 points. This demonstrates that the post-action `RECOVERY_HEALTH_CHECK` model is measurable rather than decorative.

False positives were reduced to 0.000 after Blue Agent was hardened to observe benign `LOG_NOISE` when SLA is stable. This is important for defense-style mission systems, where over-response can damage availability.

Scenario coverage reached 100%, and scenario entropy reached 64.30. This means the self-play loop explores the full safe scenario set while still adapting to scenario memory. The remaining improvement target is action accuracy for `TRAFFIC_SPIKE` and `MISSION_COMMAND_ANOMALY`, which can be addressed by tuning policy thresholds and Commander curriculum without adding unsafe behavior.

Generated evidence files:

- `reports/round_metrics.csv`
- `reports/scenario_summary.csv`
