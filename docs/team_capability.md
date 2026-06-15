# Team Capability

This document maps the work needed for DAH preliminary and final-round
readiness into clear roles. One person can cover multiple roles, but the project
plan assumes these responsibilities are visible.

## Roles

| Role | Responsibility | Current evidence |
| --- | --- | --- |
| Attack scenario design | Safe Red objectives, scenario coverage, hard-mode pressure | `agents/red_objectives.py`, `docs/attack_scenario_design.md` |
| Defense strategy | SLA-aware Blue policy, recovery, false-positive control | `agents/blue_agent.py`, `agents/blue/*`, `docs/failure_analysis.md` |
| AI agent architecture | Red/Blue/Commander loop, memory, scoring, experiments | `/selfplay/round`, scenario stats, v2 reports |
| Full-stack / infrastructure | FastAPI, Streamlit, SQLite, Docker Compose | API, dashboard, Docker validation |
| Execution lead | Reproducible runs, reports, submission packaging | `scripts/goal_runner.py`, report CSVs, docs |

## Execution Plan

1. Keep public repo local-only and safe.
2. Use `goal_runner.py` before every submission update.
3. Maintain normal, balanced, multi-seed, stress, and hard-mode evidence.
4. Prepare a private adapter only when official runtime rules are available.
5. Package final Markdown/PDF evidence and dashboard screenshots for submission.

## Risk Management

- Safety risk: public repo excludes real offensive behavior and private runtime material.
- Evidence risk: hard mode and failure analysis prevent overly optimistic claims.
- Integration risk: official DAH runtime requires a private adapter and separate validation.
