# Aegis-Swarm v2 One-Page Summary

## Problem

Mission defense agents must protect a UAV/UGV-style service without harming
availability. A response that blocks a simulated anomaly but drops mission SLA
is not acceptable in a defense competition setting.

## Proposed Solution

Aegis-Swarm v2 is a safe local Red/Blue/Commander self-play simulator. Red
generates only synthetic local anomaly events, Blue selects SLA-aware defensive
actions, and Commander balances recovery, hardening, and exploration.

## 5-Line Architecture Summary

1. FastAPI mission service exposes health, mission state, telemetry, logs, and self-play APIs.
2. SQLite stores simulated events, Blue actions, scores, and scenario memory.
3. Red Agent creates safe local scenarios such as `TRAFFIC_SPIKE` and `SERVICE_DEGRADATION`.
4. Blue Agent calculates risk, chooses a simulated defensive action, and records rationale.
5. Streamlit dashboard and Markdown reports present DAH-style SLA, score, and failure evidence.

## Key Evidence Metrics

| Evidence Run | Main Result |
| --- | --- |
| Normal self-play | 100 rounds, average SLA 100.00, false positive rate 0.000, recovery success 1.000 |
| Balanced evaluation | 6 safe scenarios x 20 attempts, action accuracy 1.000 for every scenario |
| Multi-seed evaluation | 5 seeds x 100 rounds, mean average SLA 100.000, mean false positive rate 0.000 |
| Hard mode | 100 rounds, average SLA 29.00, recovery failure rate 0.71, red success rate 0.72 |

## Normal Self-Play Result

Adaptive self-play demonstrates the working Red/Blue/Commander loop. It keeps
post-action SLA at 100.00 in the seed-42 100-round run, but the scenario mix is
adaptive and imbalanced, so it is not enough by itself.

## Balanced Evaluation Result

Balanced evaluation tests every safe event type exactly 20 times. It shows that
the Blue policy consistently maps scenarios to the expected action, including
`TRAFFIC_SPIKE -> APPLY_RATE_LIMIT`, `AUTH_ANOMALY -> BLOCK_SUSPICIOUS_TOKEN`,
and `LOG_NOISE -> OBSERVE_ONLY`.

## Multi-Seed Result

Five 100-round runs across seeds 1-5 keep average SLA at 100.000 and false
positive rate at 0.000. Scenario entropy varies, confirming that adaptive
self-play changes scenario pressure and should be paired with balanced evidence.

## Hard Mode Result

Hard mode was added to avoid optimistic-only evaluation. It intentionally adds
partial recovery, higher simulated response cost, and rolling SLA pressure. The
result is honest: Blue often selects the correct action, but recovery can still
fail under sustained local pressure. See `docs/failure_analysis.md`.

## Safety Boundaries

Aegis-Swarm v2 does not implement real offensive cyber behavior. It performs no
exploit execution, scanning, brute force, credential theft, malware behavior,
real service restart, firewall change, or interaction with external targets.
All Red behavior is a local synthetic event inserted into SQLite.

## Official Competition / Private Adapter Plan

The public repository includes a local simulator adapter and a non-networked
competition stub. Official runtime integration should be done through a private
adapter that maps competition APIs to the same interface without publishing
private endpoints, credentials, or competition secrets.

## Limitations

Aegis-Swarm v2 is still a local simulation. Red adaptation is heuristic rather
than full RL, Blue policy is explainable and rule-based, and hard-mode pressure
is simulated rather than measured from an official DAH runtime. Real competition
validation requires the private adapter and official environment access.
