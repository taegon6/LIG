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

## Safe Scenario Grammar

The Red side is framed as an adversarial evaluation curriculum, not as an
attack tool. Each sequence below is composed only from the existing safe event
set and is evaluated through local simulation.

| Sequence template | Objective | Safe event grammar | Expected Blue response | Primary metric | Failure interpretation |
| --- | --- | --- | --- | --- | --- |
| `SLOW_BURN_DEGRADATION` | `SLA_DROP` | repeated `SERVICE_DEGRADATION` with bounded intensity | `RESTART_SERVICE` or `ROLLBACK_VERSION` | `avg_sla_drop`, `red_success_score` | Mission availability can degrade before recovery succeeds |
| `TELEMETRY_DRIFT` | `RECOVERY_PRESSURE` | repeated `TELEMETRY_INCONSISTENCY` | `ISOLATE_TELEMETRY_STREAM` | `recovery_delta`, rolling SLA | Correct isolation may still be too slow under pressure |
| `NOISE_THEN_PRESSURE` | `CONFUSION` -> `RECOVERY_PRESSURE` | `LOG_NOISE`, `LOG_NOISE`, then pressure event | `OBSERVE_ONLY`, then event-specific action | false-positive rate, recovery failure | Blue should ignore noise but retain context for later pressure |
| `MIXED_SAFE_SEQUENCE` | `BLUE_MISMATCH` | `TRAFFIC_SPIKE`, `AUTH_ANOMALY`, `MISSION_COMMAND_ANOMALY`, `SERVICE_DEGRADATION` | rate limit, token containment, decoy/escalation, recovery | `blue_mismatch`, action match | Latest-event logic must avoid stale-history mistakes |
| `COVERAGE_SWEEP` | `COVERAGE` | one pass over all six safe event types | event-specific expected response | coverage score, scenario entropy | The curriculum is too narrow if scenario coverage is low |

## Objective Transition Logic

Red objective selection is adaptive but still safe and local-only:

| Condition | Objective transition | Rationale |
| --- | --- | --- |
| Scenario coverage is incomplete | any objective -> `COVERAGE` | Avoid overfitting the self-play loop to one event family |
| SLA or rolling SLA is already low | `SLA_DROP` -> `RECOVERY_PRESSURE` | Exercise recovery without increasing unsafe behavior |
| Recent false-positive penalty appears | any objective -> `CONFUSION` | Check whether Blue overreacts to benign local noise |
| Blue action matching is consistently strong | `COVERAGE` -> `BLUE_MISMATCH` | Test whether event-specific action selection remains stable |
| Hard mode shows delayed recovery | `SLA_DROP` -> `RECOVERY_PRESSURE` | Separate action correctness from mission recovery success |

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

`reports/red_objective_summary.csv` is the compact objective-level evidence
artifact. It summarizes attempts, Red success, SLA drop, Blue mismatch,
recovery delta, utility impact, and the most effective safe event type for each
Red objective observed during adaptive self-play.

## DAH-Style Attack Score Mapping

The DAH preliminary rubric values attack scenario design most heavily. Aegis-Swarm
maps that requirement to objective-driven Red behavior:

- Scenario diversity: `COVERAGE` objective and balanced evaluation.
- Mission impact: `SLA_DROP` and `RECOVERY_PRESSURE`.
- Defender confusion: `BLUE_MISMATCH` and `CONFUSION`.
- Evidence: `reports/round_metrics.csv`, `reports/red_objective_summary.csv`, `reports/hard_mode_round_metrics.csv`, and `/stats/red`.
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
