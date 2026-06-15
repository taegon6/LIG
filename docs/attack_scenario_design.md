# Attack Scenario Design

Aegis-Swarm v2 strengthens Red-side readiness without adding real offensive
capability. Red behavior is limited to safe local simulation events that are
inserted into SQLite and evaluated by the local Blue/Commander loop.

## Attack Goal

The attack-side goal is to create measurable defensive pressure without touching
real systems. Red tries to expose whether Blue can preserve mission SLA, avoid
false positives, choose the correct containment/recovery action, and recover
under repeated local pressure.

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

## Attack Scenario Flow

1. Commander mode and recent score history are observed.
2. Red selects an objective such as `SLA_DROP` or `BLUE_MISMATCH`.
3. Red chooses one safe event type and bounded intensity.
4. The event is inserted into local SQLite as a simulated event.
5. Blue calculates risk and chooses a simulated defensive action.
6. The action registry applies a local state transition only.
7. Scoring records Red success, Blue defense, SLA preservation, recovery, false positives, and utility.

## Expected Blue Response

| Red event | Expected Blue response |
| --- | --- |
| `TRAFFIC_SPIKE` | `APPLY_RATE_LIMIT` |
| `AUTH_ANOMALY` | `BLOCK_SUSPICIOUS_TOKEN` |
| `TELEMETRY_INCONSISTENCY` | `ISOLATE_TELEMETRY_STREAM` |
| `SERVICE_DEGRADATION` | `RESTART_SERVICE` or `ROLLBACK_VERSION` |
| `MISSION_COMMAND_ANOMALY` | `DEPLOY_DECOY` or `ESCALATE_ALERT` |
| `LOG_NOISE` | `OBSERVE_ONLY` |

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

## Red Success Metrics

- `red_success_score`: round-level Red pressure score from the v2 scoring model.
- `avg_sla_drop`: how much the event lowered simulated mission SLA before recovery.
- `avg_blue_mismatch_rate`: how often Blue chose an action outside the expected action set.
- `avg_recovery_delta`: whether Blue recovered after the event.
- `avg_total_utility_impact`: how much the round reduced total defender utility.
- `coverage_score`: whether all safe Red event types are exercised.

## DAH-Style Attack Score Mapping

The DAH preliminary rubric values attack scenario design most heavily. Aegis-Swarm
maps that requirement to objective-driven Red behavior:

- Scenario diversity: `COVERAGE` objective and balanced evaluation.
- Mission impact: `SLA_DROP` and `RECOVERY_PRESSURE`.
- Defender confusion: `BLUE_MISMATCH` and `CONFUSION`.
- Evidence: `reports/round_metrics.csv`, `reports/hard_mode_round_metrics.csv`, and `/stats/red`.
- Safety: public Red logic is simulation-only and never interacts with real targets.

## Safety Boundary

The public Red design does not include real exploit code, network probing,
credential behavior, malware behavior, persistence, lateral movement, or
interaction with outside systems. The private adapter example is inert and
contains placeholders only.

## Private Official Adapter Plan

Official DAH integration should remain outside the public repository. A private
adapter can map official runtime observations into the same Red objective
interface, but the public repo keeps only a non-functional example with no real
competition wiring.
