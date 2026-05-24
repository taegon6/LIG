# Aegis-Swarm v2 3-Minute Presentation Script

## 0:00-0:30 - Opening

Hello, we are presenting Aegis-Swarm v2, a safe local Red-Blue-Commander self-play simulator for mission-oriented cyber defense.

The problem we focus on is not real-world exploitation. The problem is defensive decision quality under simulated pressure. In a UAV or UGV mission service, a security response must reduce risk while preserving availability, latency, mission status, and recovery.

## 0:30-1:10 - System Overview

Aegis-Swarm runs a FastAPI mission service, a SQLite evidence database, a Streamlit dashboard, and three agents.

The Red Agent generates only safe local anomaly events such as traffic spike, authentication anomaly, telemetry inconsistency, service degradation, mission command anomaly, and benign log noise. It uses an epsilon-greedy heuristic to explore or prefer scenarios from local score memory. It does not scan, exploit, brute-force, steal credentials, or contact external targets.

The Blue Agent computes explainable component scores for authentication risk, traffic pressure, latency, telemetry inconsistency, and error rate. It then chooses a simulated defensive action such as rate limiting, token blocking, telemetry isolation, service restart, decoy deployment, or observe-only.

The Commander Agent selects the operating mode: balanced, recovery-first, defense-hardening, or red-exploration.

## 1:10-1:50 - SLA-Aware Defense

The key design point is SLA-aware defense. A good defense action is not simply the strongest action. For example, traffic spike should usually map to a low-impact simulated rate limit. Authentication anomaly should map to token containment. Service degradation should prioritize recovery.

After every Blue action, Aegis-Swarm inserts a `RECOVERY_HEALTH_CHECK` event. This makes post-action SLA measurable. We track pre-SLA, post-event SLA, post-action SLA, recovery delta, Red success, Blue defense, false positives, and total utility.

All of these are local simulated state transitions. No real firewall rules, shell commands, service restarts, or external cyber actions are performed.

## 1:50-2:30 - Evidence

We ran two evidence modes.

First, adaptive self-play for 100 rounds with seed 42. This showed average SLA of 100.00, average utility of 70.73, false positive rate of 0.000, recovery success rate of 1.000, and scenario coverage score of 100.00.

Second, balanced scenario evaluation. Adaptive self-play can become scenario-imbalanced, so we added a separate evaluation that runs each safe scenario exactly 20 times. In that balanced run, all six scenarios reached action accuracy of 1.000, recovery success rate of 1.000, and false positive rate of 0.000.

This gives judges both views: adaptive curriculum behavior and per-scenario defense stability.

## 2:30-3:00 - Safety and Future Competition Integration

Aegis-Swarm v2 is safe by design. It contains no exploit code, no scanning, no brute force, no credential theft, no malware behavior, and no external target interaction.

For official competition integration, the public repository includes a `CompetitionStubAdapter` that is not configured and performs no external calls. A private adapter can later connect official runtime APIs to the same interface without exposing secrets or NDA data.

In short, Aegis-Swarm demonstrates explainable, SLA-aware AI defense coordination in a safe local simulation, ready to be extended toward an official competition runtime when the private adapter is available.
