# DAH Preliminary Report Outline

## 1. Problem Definition

- Defense mission services need cyber resilience and availability.
- Over-blocking can harm SLA and mission continuity.
- Aegis-Swarm evaluates response quality through safe local self-play.

## 2. Safety Statement

- All Red behavior is simulated locally.
- No exploit, scanning, brute force, malware, credential theft, or external target interaction.
- Public repo contains no NDA/private competition data.

## 3. System Architecture

- FastAPI Mission Service
- Red Agent
- Modular Blue Agent
- Commander Agent
- SQLite memory and scoring
- Competition Adapter
- Streamlit Judging Dashboard

## 4. Agent Design

- Red Agent: epsilon-greedy safe scenario selection
- Blue Agent: triage, containment, recovery, deception, SLA governor
- Commander Agent: balanced, recovery-first, defense-hardening, red-exploration modes

## 5. Measurable SLA Recovery

Explain:

- `pre_sla`
- `post_event_sla`
- `post_action_sla`
- `sla_delta`
- `recovery_delta`
- `RECOVERY_HEALTH_CHECK`

## 6. Realistic Scoring

Explain:

- red_success_score
- blue_defense_score
- sla_preservation_score
- recovery_score
- false_positive_penalty
- action_cost
- total_utility

## 7. Scenario Memory

Explain `scenario_stats`, entropy, coverage, Red exploit/explore behavior, and Blue recent failure awareness.

## 8. Knowledge Mapping

Show ATT&CK-style event labels and D3FEND-style action labels as interpretation aids, not as claims of real attack execution.

## 9. Experiments

Use `reports/round_metrics.csv` and `reports/scenario_summary.csv` as evidence tables. Include average SLA, recovery success rate, false positive rate, entropy, and coverage.

## 10. Competition Integration Plan

Private adapter only:

- event ingestion
- mission state query
- Blue action submission
- official score query

Do not publish private endpoints, tokens, logs, or NDA material.
