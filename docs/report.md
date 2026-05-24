# Aegis-Swarm v2 DAH Preliminary Report Draft

## Problem Definition

Aegis-Swarm v2 is a local, safe Red-Blue-Commander self-play simulator for defense-style cyber competition preparation. The project focuses on mission availability under simulated anomaly pressure, not on real attack execution.

The core problem is that defensive cyber agents in mission systems cannot optimize only for blocking suspicious behavior. A UAV/UGV-style mission service also needs stable latency, active mission status, and recoverable service state. A defense action that is too aggressive can harm the mission as much as the simulated anomaly.

This MVP asks three practical questions:

- Can a Red Agent generate safe local anomaly events that exercise defense decisions?
- Can a Blue Agent select an action that balances risk reduction with SLA and mission continuity?
- Can a Commander Agent adjust the self-play mode when recovery, hardening, or exploration is more important?

## Why SLA-Aware Defense Matters

In mission-oriented systems, availability is part of security. A simulated `SERVICE_DEGRADATION` should trigger recovery-oriented behavior, while a simulated `AUTH_ANOMALY` should trigger token containment instead of restarting the mission service. Aegis-Swarm therefore scores both defensive correctness and post-action SLA.

The SLA model checks four local fields from simulated events:

- `status_code < 500`
- `latency_ms < 500`
- `mission_status == ACTIVE`
- `sla_ok == true`

This keeps the evaluation concrete and explainable. The system is not trying to prove real-world cyber exploitation capability. It is testing whether a defense policy can respond to safe local signals while keeping a mission service available.

## System Architecture

```text
FastAPI Mission Service
  -> SQLite events/actions/scores/scenario_stats
  -> Red Agent: safe local anomaly event generation
  -> Blue Agent: modular risk and SLA-aware policy
  -> Commander Agent: mode selection for self-play curriculum
  -> Action Registry: simulated local state transitions only
  -> Scoring Model: attack, defense, SLA, recovery, false positive, utility
  -> Competition Adapter
       -> LocalSimulatorAdapter
       -> CompetitionStubAdapter
  -> Streamlit Dashboard
```

The FastAPI backend exposes health, mission state, telemetry, logs, scenario simulation, Blue decision, and `/selfplay/round` endpoints. The Streamlit dashboard displays SLA, Commander mode, DAH-style scores, recent events, Blue decisions, and manual scenario buttons.

SQLite stores three main evidence streams:

- `events`: simulated Red events and post-action recovery checks
- `actions`: Blue Agent decisions and rationale
- `scores`: v2 scoring outputs for each evaluated round

## Red Agent Safe Local Scenario Generation

The Red Agent is safe by design. It never scans, exploits, brute-forces, steals credentials, runs malware, or interacts with external targets. It only generates local simulated events from the approved scenario list:

- `TRAFFIC_SPIKE`
- `AUTH_ANOMALY`
- `TELEMETRY_INCONSISTENCY`
- `SERVICE_DEGRADATION`
- `MISSION_COMMAND_ANOMALY`
- `LOG_NOISE`

The current Red Agent uses an epsilon-greedy heuristic, not full reinforcement learning. With `epsilon=0.2`, it sometimes explores a random safe scenario and otherwise prefers scenarios that previously produced higher simulated Red success or SLA drop. Commander mode and current SLA also constrain event intensity. For example, `RECOVERY_FIRST` lowers event intensity to avoid compounding an already degraded mission state.

## Blue Agent Modular Policy

The Blue Agent is a modular rule-based/adaptive defender. It does not perform autonomous hacking and does not execute system-level blocking commands. It observes recent local events and computes component scores:

- `auth_failure_score`
- `traffic_spike_score`
- `latency_score`
- `telemetry_inconsistency_score`
- `error_rate_score`

These are combined into a risk score:

```text
risk_score =
  0.3 * auth_failure_score
+ 0.2 * traffic_spike_score
+ 0.2 * latency_score
+ 0.2 * telemetry_inconsistency_score
+ 0.1 * error_rate_score
```

The policy prioritizes the latest unrecovered active event, treating `RECOVERY_HEALTH_CHECK` as the boundary for already-handled history. This prevents stale events from dominating the newest decision.

Action examples:

- `TRAFFIC_SPIKE` -> `APPLY_RATE_LIMIT`
- `AUTH_ANOMALY` -> `BLOCK_SUSPICIOUS_TOKEN`
- `TELEMETRY_INCONSISTENCY` -> `ISOLATE_TELEMETRY_STREAM`
- `SERVICE_DEGRADATION` -> `RESTART_SERVICE` or `ROLLBACK_VERSION`
- `MISSION_COMMAND_ANOMALY` -> `DEPLOY_DECOY` or `ESCALATE_ALERT`
- `LOG_NOISE` -> `OBSERVE_ONLY`

All actions are simulated local state transitions and action logs. They do not change firewall rules, call external systems, or execute operating system commands.

## Commander Agent

The Commander Agent balances competition pressure with mission availability. It chooses one of four modes:

- `BALANCED`
- `RECOVERY_FIRST`
- `DEFENSE_HARDENING`
- `RED_EXPLORATION`

Decision logic:

- If SLA is below 90, choose `RECOVERY_FIRST`.
- If recent Blue defense scores are weak, choose `DEFENSE_HARDENING`.
- If recent Red success rate is low, choose `RED_EXPLORATION`.
- Otherwise, choose `BALANCED`.

This creates a simple curriculum loop. It is explainable and deterministic enough for preliminary judging, while still showing adaptive behavior over multiple rounds.

## Scenario Memory

Aegis-Swarm stores scenario-level memory in SQLite. For each event type, it tracks attempts, Red success count, Blue success count, average SLA drop, average recovery delta, false positives, and the most effective Blue action.

The Red Agent can use this scenario memory to bias safe scenario selection. The Blue Agent can also use it to harden responses when recent Blue outcomes are poor. This is a lightweight adaptive memory layer, not a neural RL policy.

## Scoring Model

The v2 scoring model is deterministic and explainable. Each round produces:

- `red_success_score`
- `blue_defense_score`
- `sla_preservation_score`
- `recovery_score`
- `false_positive_penalty`
- `action_cost`
- `total_utility`

The utility formula rewards defense, SLA preservation, and recovery, while penalizing Red success, false positives, and action cost:

```text
total_utility =
  0.35 * blue_defense_score
- 0.25 * red_success_score
+ 0.25 * sla_preservation_score
+ 0.15 * recovery_score
- 0.20 * false_positive_penalty
- 0.10 * action_cost
```

This differs from the original MVP formula because v2 treats Red success and action cost as negative utility, which better reflects a defense-oriented mission evaluation.

## Post-Action SLA Recovery

Every self-play or balanced evaluation round inserts a `RECOVERY_HEALTH_CHECK` event after the Blue action. This event makes the post-action SLA measurable instead of merely implied.

Recovery effects are simulated locally:

- `RESTART_SERVICE`: restores active mission state with latency around 150 ms.
- `ROLLBACK_VERSION`: restores active mission state with latency around 170 ms.
- `APPLY_RATE_LIMIT` for `TRAFFIC_SPIKE`: reduces simulated traffic impact and keeps latency under 280 ms.
- `ISOLATE_TELEMETRY_STREAM` for `TELEMETRY_INCONSISTENCY`: keeps the mission active and marks communication as degraded-but-contained.

No real service restart, rollback, firewall change, network action, or telemetry isolation is executed.

## Adaptive Self-Play Experiment

Command:

```bash
python scripts/run_experiments.py --rounds 100 --seed 42
```

The adaptive self-play experiment lets the Commander and Red Agent change scenario selection based on recent score history. This is useful for showing curriculum behavior, but it can produce an imbalanced scenario mix.

| Metric | Value |
| --- | ---: |
| Rounds | 100 |
| Average SLA | 100.00 |
| Average SLA Drop | 7.54 |
| Average Recovery Delta | 8.00 |
| Average Utility | 70.73 |
| False Positive Rate | 0.000 |
| Recovery Success Rate | 1.000 |
| Coverage Score | 100.00 |

Per-scenario distribution in the adaptive run:

| Scenario | Attempts | Action Accuracy | Average SLA | False Positive Rate | Recovery Success Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| AUTH_ANOMALY | 3 | 1.000 | 100.00 | 0.000 | 1.000 |
| LOG_NOISE | 51 | 1.000 | 100.00 | 0.000 | 1.000 |
| MISSION_COMMAND_ANOMALY | 2 | 1.000 | 100.00 | 0.000 | 1.000 |
| SERVICE_DEGRADATION | 36 | 1.000 | 100.00 | 0.000 | 1.000 |
| TELEMETRY_INCONSISTENCY | 4 | 1.000 | 100.00 | 0.000 | 1.000 |
| TRAFFIC_SPIKE | 4 | 1.000 | 100.00 | 0.000 | 1.000 |

Honest interpretation: adaptive self-play concentrated heavily on `LOG_NOISE` and `SERVICE_DEGRADATION` in this seeded run. That is expected behavior for a memory-guided heuristic loop, but it is not enough by itself to prove per-scenario stability. This is why the balanced scenario evaluation was added.

## Balanced Scenario Evaluation

Command:

```bash
python scripts/run_balanced_evaluation.py --rounds-per-scenario 20 --seed 42
```

Balanced evaluation fixes the schedule so each safe scenario is tested exactly 20 times. It uses the same Blue Agent, local action registry, `RECOVERY_HEALTH_CHECK`, and v2 scoring model as adaptive self-play.

| Scenario | Attempts | Action Accuracy | Average SLA | Recovery Success Rate | False Positive Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| TRAFFIC_SPIKE | 20 | 1.000 | 100.00 | 1.000 | 0.000 |
| AUTH_ANOMALY | 20 | 1.000 | 100.00 | 1.000 | 0.000 |
| TELEMETRY_INCONSISTENCY | 20 | 1.000 | 100.00 | 1.000 | 0.000 |
| SERVICE_DEGRADATION | 20 | 1.000 | 100.00 | 1.000 | 0.000 |
| MISSION_COMMAND_ANOMALY | 20 | 1.000 | 100.00 | 1.000 | 0.000 |
| LOG_NOISE | 20 | 1.000 | 100.00 | 1.000 | 0.000 |

The balanced result shows that the latest-event Blue policy is stable across the full safe scenario set. In particular, `TRAFFIC_SPIKE` maps to `APPLY_RATE_LIMIT`, `AUTH_ANOMALY` maps to `BLOCK_SUSPICIOUS_TOKEN`, `MISSION_COMMAND_ANOMALY` maps to deception/escalation rather than restart, and `LOG_NOISE` remains observe-only.

## Early-vs-Late Self-Play Comparison

| Window | Average SLA | Blue Success Rate | Red Success Rate | Average Recovery Delta | False Positive Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rounds 1-20 | 100.00 | 1.000 | 0.000 | 0.00 | 0.000 |
| Rounds 81-100 | 100.00 | 1.000 | 0.200 | 20.00 | 0.000 |

The late window has higher recovery delta because it contains more disruptive `SERVICE_DEGRADATION` rounds. Blue success remained stable, while Red success appears only when the simulated event caused immediate SLA disruption before recovery.

## Safety Boundaries

Aegis-Swarm v2 intentionally excludes real offensive cyber functionality:

- No exploit payloads
- No port scanning or network scanning
- No brute force or credential guessing
- No credential theft
- No malware, persistence, lateral movement, or destructive behavior
- No attack against external targets
- No shell or system commands for defense actions

All Red behavior is a local synthetic event inserted into SQLite and processed by local Python code.

## Private Adapter Plan for Official Competition

The public repository includes `LocalSimulatorAdapter` and `CompetitionStubAdapter`. The stub is deliberately not configured and never calls external systems.

For official competition integration, a private adapter should be implemented outside the public submission branch. That adapter would map official runtime APIs to the same interface:

- `get_mission_state()`
- `get_recent_events(limit)`
- `submit_blue_action(action)`
- `get_latest_scores()`
- `adapter_status()`

This keeps the public repository free of private endpoints, credentials, NDA data, or competition-specific secrets.

## Limitations and Future Work

Current limitations:

- Red Agent adaptation is epsilon-greedy heuristic selection, not full reinforcement learning.
- Blue Agent is modular and adaptive, but still rule-based.
- Experiments are local simulations, not official competition runtime results.
- Balanced evaluation currently uses deterministic scenario counts but still samples severity from safe ranges.
- Dashboard screenshots and a final PDF package still need to be captured before submission.

Future work:

- Add richer Commander curriculum strategies.
- Add more evidence runs with multiple seeds.
- Improve scenario memory visualization in the dashboard.
- Add private official-runtime adapter after rules and APIs are available.
- Package final report, screenshots, and demo logs into the DAH submission PDF.
