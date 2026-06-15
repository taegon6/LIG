# Attack Scenario Design

Aegis-Swarm v2 strengthens Red-side readiness without adding real offensive
capability. Red behavior is limited to safe local simulation events that are
inserted into SQLite and evaluated by the local Blue/Commander loop.

## Safe Event Set

- `TRAFFIC_SPIKE`
- `AUTH_ANOMALY`
- `TELEMETRY_INCONSISTENCY`
- `SERVICE_DEGRADATION`
- `MISSION_COMMAND_ANOMALY`
- `LOG_NOISE`

## Red Objectives

| Objective | Purpose | Safe event focus |
| --- | --- | --- |
| `SLA_DROP` | Stress latency, status, and mission availability | `SERVICE_DEGRADATION`, `TRAFFIC_SPIKE`, `TELEMETRY_INCONSISTENCY` |
| `BLUE_MISMATCH` | Check whether Blue chooses the correct defensive action | `AUTH_ANOMALY`, `MISSION_COMMAND_ANOMALY`, `TELEMETRY_INCONSISTENCY` |
| `CONFUSION` | Measure false positives and overreaction to noise | `LOG_NOISE`, `MISSION_COMMAND_ANOMALY`, `AUTH_ANOMALY` |
| `RECOVERY_PRESSURE` | Test post-action recovery and rolling SLA | `SERVICE_DEGRADATION`, `TELEMETRY_INCONSISTENCY`, `TRAFFIC_SPIKE` |
| `COVERAGE` | Avoid self-play overfitting to a narrow scenario mix | all safe event types |

## Strategy Metadata

Each Red plan includes:

- `red_objective`
- `event_type`
- `intensity`
- `strategy_reason`
- `expected_effect`

This makes Red behavior explainable in `/selfplay/round`, `/stats/red`, and the
readiness reports. The design is intentionally evidence-oriented: Red success is
measured through local `red_success_score`, SLA drop, Blue mismatch, false
positive pressure, recovery failure, and scenario coverage.

## Safety Boundary

The public Red design does not include real exploit code, network probing,
credential behavior, malware behavior, persistence, lateral movement, or
interaction with outside systems. The private adapter example is inert and
contains placeholders only.
