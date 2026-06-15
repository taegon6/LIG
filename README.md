# Aegis-Swarm v2

Aegis-Swarm v2 is a safe local Red/Blue/Commander self-play simulator for DAH
2026 preliminary readiness. It does not perform exploitation, scanning,
credential attacks, malware behavior, shell execution, or external target
interaction. Instead, the Red Agent generates bounded synthetic anomaly events
inside a local SQLite-backed mission simulator, the Blue Agent selects
SLA-aware simulated defense actions, and the Commander Agent adjusts recovery,
hardening, and exploration modes.

## What This Project Evaluates

This project evaluates mission-defense decision quality, not offensive execution
capability.

- Red side: objective-driven local scenario generation.
- Blue side: SLA-aware simulated defense and recovery policy.
- Commander side: curriculum mode selection for recovery, hardening, and exploration.
- Evidence side: reproducible CSV reports, hard-mode failure analysis, and a DAH readiness self-check.

## Safety Boundary

The public repository is local-only and simulation-only.

Explicitly excluded:

- Real exploit code
- Port or network scanning
- Brute force, credential attacks, or credential theft
- Malware, persistence, lateral movement, or destructive behavior
- External target interaction
- Shell attack behavior
- Real firewall, service, or system changes

Current safety evidence:

- `scripts/goal_runner.py --target-score 92 --strict` passed.
- `reports/goal_score.json` reports `hard_gates_passed: true`.
- Safety check reports no forbidden source hits and default adapter mode is local/stub.
- Private adapter examples are inert placeholders with no real endpoint, token, payload, exploit, or scan behavior.

## DAH Rubric Alignment

| Rubric area | Evidence |
| --- | --- |
| Attack Scenario Design, 30 pts | Red objectives, safe scenario grammar, `/stats/red`, Red strategy memory, hard-mode Red pressure |
| Defense Strategy, 25 pts | Modular Blue policy, SLA-aware actions, recovery checks, false-positive handling |
| AI Agent Architecture, 25 pts | Red/Blue/Commander loop, SQLite memory, scoring, experiments, dashboard, adapters |
| Team Capability, 10 pts | `docs/team_capability.md`, execution plan, reproducible scripts |
| Document Completeness, 10 pts | one-page summary, report, experiment results, failure analysis, Q&A, demo flow |

## Architecture

```text
FastAPI Mission Service
  -> SQLite evidence store
  -> Red Agent: objective-driven safe local scenario pressure
  -> Blue Agent: SLA-aware simulated defense policy
  -> Commander Agent: recovery/hardening/exploration mode selection
  -> Action Registry: local state transition only
  -> Scoring Model: Red success, Blue defense, SLA, recovery, utility
  -> Adapter Layer: local simulator, competition stub, private template
  -> Streamlit Dashboard
```

## Red Agent Design

Red uses five safe objectives:

- `SLA_DROP`
- `BLUE_MISMATCH`
- `CONFUSION`
- `RECOVERY_PRESSURE`
- `COVERAGE`

Each objective maps only to existing safe local events:

- `TRAFFIC_SPIKE`
- `AUTH_ANOMALY`
- `TELEMETRY_INCONSISTENCY`
- `SERVICE_DEGRADATION`
- `MISSION_COMMAND_ANOMALY`
- `LOG_NOISE`

Red strategy evidence is exposed through:

- `GET /stats/red`
- `reports/round_metrics.csv`
- `reports/red_objective_summary.csv`
- `reports/hard_mode_round_metrics.csv`
- `docs/attack_scenario_design.md`
- `docs/red_strategy_analysis.md`

## Private-Adapter-Ready Red Action Layer

The public repo includes an abstract Red action layer for future authorized DAH
integration:

- `core/red_action_schema.py`
- `adapters/mock_official_runtime.py`
- `adapters/private_red_adapter.py.example`
- `POST /red/plan`
- `POST /red/mock/execute`

Allowed abstract action names:

- `OBSERVE_TARGET_STATE`
- `SELECT_ALLOWED_TARGET`
- `SUBMIT_ALLOWED_RED_ACTION`
- `REQUEST_SCORE_FEEDBACK`
- `PRESSURE_SLA_TARGET`
- `CONFUSE_DEFENSE_SIGNAL`
- `COVERAGE_PROBE`

These are planning labels only. The public repo contains no payload field, no
endpoint field, no token field, and no real action execution against outside
systems.

## Key Evidence

Latest reproducible local evidence:

- `pytest`: 70 tests passed.
- Adaptive self-play: 100 rounds, average SLA 100.0, five Red objectives x 20 attempts, coverage score 100.0.
- Balanced evaluation: 6 safe scenarios x 20 attempts.
- Hard mode: average SLA 29.0, recovery failure rate 0.71, Red success rate 0.72.
- Goal runner: score 100.0, hard gates passed.

Hard mode is intentionally non-perfect. It shows that Blue can choose the
correct action class while mission recovery still fails under sustained local
pressure. In reports, action match and mission recovery are treated as separate
concepts.

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
```

Run the API:

```bash
uvicorn mission_service.app:app --reload --host 0.0.0.0 --port 8000
```

Run the dashboard:

```bash
streamlit run dashboard/streamlit_app.py
```

Docker:

```bash
docker compose up --build
```

## Reproduce Evidence

```bash
python scripts/run_experiments.py --rounds 100 --seed 42
python scripts/run_balanced_evaluation.py --rounds-per-scenario 20 --seed 42
python scripts/run_hard_mode.py --rounds 100 --seed 42
python scripts/goal_runner.py --target-score 92 --strict
```

Generated evidence:

- `reports/round_metrics.csv`
- `reports/scenario_summary.csv`
- `reports/red_objective_summary.csv`
- `reports/balanced_round_metrics.csv`
- `reports/balanced_scenario_summary.csv`
- `reports/hard_mode_round_metrics.csv`
- `reports/hard_mode_summary.csv`
- `reports/goal_score.json`
- `reports/goal_score.md`

## Main API Endpoints

- `GET /health`
- `GET /adapter/status`
- `GET /mission/status`
- `GET /vehicle/state`
- `GET /telemetry`
- `GET /logs/recent?limit=50`
- `GET /stats/scenarios`
- `GET /stats/red`
- `POST /simulate/event`
- `POST /agent/blue/decide`
- `POST /selfplay/round`
- `POST /red/plan`
- `POST /red/mock/execute`

## Important Documents

- `docs/one_page_summary.md`
- `docs/report.md`
- `docs/experiment_results.md`
- `docs/failure_analysis.md`
- `docs/attack_scenario_design.md`
- `docs/red_strategy_analysis.md`
- `docs/official_red_adapter_plan.md`
- `docs/safety_statement.md`
- `docs/private_adapter_design.md`
- `docs/team_capability.md`
- `docs/judge_qa.md`
- `docs/demo_flow.md`
- `docs/submission_checklist.md`

## Limitations

- Aegis-Swarm v2 is a local simulation, not official DAH runtime evidence.
- Red and Blue policies are explainable heuristics, not full reinforcement learning.
- Official runtime integration requires a private adapter and competition environment access.
- Public examples must remain inert and free of secrets, real endpoints, and real action logic.
