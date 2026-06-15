# Aegis-Swarm v2 Failure Analysis

This document summarizes failure and near-failure behavior observed in the
Aegis-Swarm v2 hard-mode evaluation. All cases below are local simulated
hard-mode cases. They do not represent real-world compromise, real exploit
execution, network scanning, credential attacks, malware behavior, or any
interaction with external targets.

Data sources:

- `reports/hard_mode_round_metrics.csv`
- `reports/hard_mode_summary.csv`
- `reports/stress_summary.csv` for additional comparison context

Hard-mode command:

```bash
python scripts/run_hard_mode.py --rounds 100 --seed 42
```

## Hard-Mode Summary

| Metric | Value |
| --- | ---: |
| Average SLA | 29.00 |
| Minimum rolling SLA 10 | 10.00 |
| Minimum rolling SLA 50 | 14.29 |
| Average recovery delta | 1.00 |
| Recovery failure rate | 0.71 |
| Mission recovery success rate | 0.29 |
| Action match rate | 1.00 |
| Red success rate | 0.72 |
| False positive rate | 0.00 |
| Average utility | 40.23 |

The hard-mode result is intentionally not perfect. `Action match rate` means
Blue selected the expected action class. `Mission recovery success rate` means
the post-action local health check recovered SLA. Hard mode shows that the
correct action class can still fail to recover the mission under sustained
simulated pressure.

## Why failure analysis matters

Normal adaptive evaluation and balanced evaluation can look too perfect because
post-action health checks often recover the local mission state quickly. That is
useful for proving the basic Red/Blue/Commander loop, but it can hide whether
the system behaves well under repeated pressure.

Hard mode intentionally adds partial recovery, higher simulated response cost,
and rolling SLA pressure. This makes the evaluation less flattering but more
useful. Failure cases show realistic limitations and point to future work:
better recovery planning, pressure-aware escalation, cooldown modeling, and
multi-step containment instead of one-shot actions.

## Failure And Near-Failure Cases

### 1. TELEMETRY_DRIFT / TELEMETRY_INCONSISTENCY

| Field | Value |
| --- | --- |
| Round | 6 |
| Event or sequence | `TELEMETRY_DRIFT` / `TELEMETRY_INCONSISTENCY` |
| Blue action | `ISOLATE_TELEMETRY_STREAM` |
| SLA drop | `pre_sla` 10.00 to `post_action_sla` 0.00 |
| Recovery result | Failed partial recovery, `recovery_delta` 0.00 |
| Red or utility impact | `red_success_score` 35.00, `total_utility` 45.71 |
| Hard-mode note | `local pressure=5; repeated anomaly pressure; higher simulated action cost=22.0; partial/delayed recovery` |

Why it was difficult: telemetry anomalies were repeated while local pressure was
already saturated. The Blue Agent chose the correct containment action, but hard
mode treated isolation as costly and incomplete under sustained drift.

What should improve next: the agent should distinguish between a single
telemetry inconsistency and a drift pattern. For repeated drift, it should
consider a staged response: isolate the stream, lower command confidence,
trigger a recovery health check, and escalate if rolling SLA remains low.

### 2. REPEATED_SERVICE_DEGRADATION / SERVICE_DEGRADATION

| Field | Value |
| --- | --- |
| Round | 29 |
| Event or sequence | `REPEATED_SERVICE_DEGRADATION` / `SERVICE_DEGRADATION` |
| Blue action | `RESTART_SERVICE` |
| SLA drop | `pre_sla` 32.00 to `post_action_sla` 0.00 |
| Recovery result | Failed partial recovery, `recovery_delta` 0.00 |
| Red or utility impact | `red_success_score` 65.00, `total_utility` 22.48 |
| Hard-mode note | `local pressure=5; repeated anomaly pressure; higher simulated action cost=26.0; partial/delayed recovery` |

Why it was difficult: repeated degradation made the default restart action too
expensive and too slow to restore SLA. The action matched the event type, but
matching the event was not enough to preserve availability.

What should improve next: the Commander and Blue Agent should treat repeated
degradation as a recovery-first situation earlier. A future policy could switch
from repeated restarts to rollback, degraded-mode operation, or mission-safe
throttling when recent restart attempts fail to recover SLA.

### 3. MIXED_SAFE_SEQUENCE / SERVICE_DEGRADATION

| Field | Value |
| --- | --- |
| Round | 24 |
| Event or sequence | `MIXED_SAFE_SEQUENCE` / `SERVICE_DEGRADATION` |
| Blue action | `RESTART_SERVICE` |
| SLA drop | `pre_sla` 28.26 to `post_action_sla` 0.00 |
| Recovery result | Failed partial recovery, `recovery_delta` 0.00 |
| Red or utility impact | `red_success_score` 65.00, `total_utility` 22.48 |
| Hard-mode note | `local pressure=5; repeated anomaly pressure; higher simulated action cost=26.0; partial/delayed recovery` |

Why it was difficult: the degradation happened inside a mixed sequence rather
than as a clean single scenario. Prior traffic, authentication, and mission
command anomalies kept local pressure high, so the restart did not create an
immediate SLA recovery.

What should improve next: the agent should use sequence context more directly.
When several event types arrive in a short window, the policy should account for
compound pressure instead of selecting only the best action for the latest
event.

### 4. MIXED_SAFE_SEQUENCE / TRAFFIC_SPIKE

| Field | Value |
| --- | --- |
| Round | 77 |
| Event or sequence | `MIXED_SAFE_SEQUENCE` / `TRAFFIC_SPIKE` |
| Blue action | `APPLY_RATE_LIMIT` |
| SLA drop | `pre_sla` 24.00 to `post_action_sla` 0.00 |
| Recovery result | Failed delayed recovery, `recovery_delta` 0.00 |
| Red or utility impact | `red_success_score` 45.00, `total_utility` 32.38 |
| Hard-mode note | `local pressure=5; partial/delayed recovery` |

Why it was difficult: rate limiting is the correct safe response to traffic
pressure, but hard mode modeled the response as delayed when local pressure was
already high. The result shows that correct mitigation can still be too slow.

What should improve next: the Blue Agent should estimate whether rate limiting
alone is enough. Under high rolling pressure, it may need to combine rate
limiting with Commander-level recovery mode or staged capacity protection in the
simulator.

### 5. NOISE_THEN_PRESSURE / TELEMETRY_INCONSISTENCY

| Field | Value |
| --- | --- |
| Round | 42 |
| Event or sequence | `NOISE_THEN_PRESSURE` / `TELEMETRY_INCONSISTENCY` |
| Blue action | `ISOLATE_TELEMETRY_STREAM` |
| SLA drop | `pre_sla` 32.00 to `post_action_sla` 0.00 |
| Recovery result | Failed partial recovery, `recovery_delta` 0.00 |
| Red or utility impact | `red_success_score` 45.00, `total_utility` 28.22 |
| Hard-mode note | `local pressure=5; repeated anomaly pressure; higher simulated action cost=22.0; partial/delayed recovery` |

Why it was difficult: the sequence began with local log noise, then shifted into
real simulated pressure. The agent avoided false positives, but by the time the
telemetry inconsistency arrived the rolling pressure was already high.

What should improve next: the agent should keep a low-cost suspicion trail for
noise-heavy windows. It should not overreact to noise, but it should preserve
context so that later telemetry anomalies can trigger faster recovery planning.

## Additional Stress Scenario Context

The separate stress scenario run is less severe than hard mode because it still
allows full final recovery. It is useful as a bridge between balanced evaluation
and hard mode:

| Stress sequence | Minimum SLA | Final SLA | Recovery success | Utility |
| --- | ---: | ---: | ---: | ---: |
| `SLOW_BURN_DEGRADATION` | 0.00 | 100.00 | 1.00 | 66.47 |
| `TELEMETRY_DRIFT` | 0.00 | 100.00 | 1.00 | 70.19 |

These stress results show that the current agent can recover in moderate
multi-event scenarios. Hard mode then exposes the next limitation: recovery can
fail when simulated pressure remains high after the correct action is selected.

## Honest Interpretation

Aegis-Swarm v2 demonstrates a safe, explainable local Red/Blue/Commander
self-play loop. It does not prove perfect real-world defense. The strongest
result is policy interpretability and safe repeatable evidence generation. The
main weakness is recovery strategy under sustained or compound pressure. Future
work should focus on multi-step recovery, pressure-aware Commander mode changes,
and more detailed mission-impact modeling.
