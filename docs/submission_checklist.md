# Aegis-Swarm v2 Submission Checklist

## Evidence Status

- [x] `pytest` passed locally: 55+ tests pass after v2 hard-mode additions.
- [x] Adaptive self-play report generated: `reports/round_metrics.csv`.
- [x] Adaptive scenario summary generated: `reports/scenario_summary.csv`.
- [x] Balanced evaluation report generated: `reports/balanced_round_metrics.csv`.
- [x] Balanced scenario summary generated: `reports/balanced_scenario_summary.csv`.
- [x] Hard-mode reports generated: `reports/hard_mode_round_metrics.csv`, `reports/hard_mode_summary.csv`.
- [x] Failure analysis generated: `docs/failure_analysis.md`.
- [x] Red objectives and Red stats endpoint available.
- [x] Docker was verified locally for API port 8000 and Streamlit port 8501.
- [x] DAH readiness self-check available: `scripts/goal_runner.py`.
- [ ] Dashboard screenshots available for final submission package.
- [ ] Final public repository review confirms no secrets, credentials, NDA data, or private competition endpoints.

## Required Final Artifacts

- [x] `README.md`
- [x] `docs/report.md`
- [x] `docs/experiment_results.md`
- [x] `docs/one_page_summary.md`
- [x] `docs/failure_analysis.md`
- [x] `docs/attack_scenario_design.md`
- [x] `docs/red_strategy_analysis.md`
- [x] `docs/judge_qa.md`
- [x] `docs/demo_flow.md`
- [x] `docs/safety_statement.md`
- [x] `docs/private_adapter_design.md`
- [x] `docs/team_capability.md`
- [x] `docs/presentation_script.md`
- [x] `scripts/run_experiments.py`
- [x] `scripts/run_balanced_evaluation.py`
- [x] `scripts/run_hard_mode.py`
- [x] `scripts/goal_runner.py`
- [x] Docker Compose setup
- [x] FastAPI backend
- [x] Streamlit dashboard
- [x] SQLite evidence reports

## Safety Review

- [x] Red Agent behavior is limited to safe local simulated events.
- [x] No exploit payloads are implemented.
- [x] No port scanning or network scanning is implemented.
- [x] No brute force, credential theft, or credential attack behavior is implemented.
- [x] No malware, persistence, destructive behavior, or lateral movement is implemented.
- [x] `CompetitionStubAdapter` performs no external calls.
- [x] `adapters/private_red_adapter.py.example` is inert and contains no real competition wiring.
- [ ] Before publishing, inspect environment files and Git history for accidental secrets.

## Demo Readiness

- [x] `POST /selfplay/round` returns Red event, Blue decision, Commander mode, DAH scores, strategy notes, recovery event, and knowledge mapping.
- [x] Adaptive 100-round experiment completed with seed 42.
- [x] Balanced 120-round evaluation completed with seed 42 and 20 rounds per scenario.
- [x] Hard-mode 100-round evaluation completed with seed 42.
- [x] `GET /stats/red` returns Red objectives, safe event types, and scenario memory.
- [ ] Capture dashboard screenshots showing SLA, Commander mode, DAH scoring view, recent events, and Blue decisions.
- [ ] Export final report to PDF and check file size.

## Commands

```bash
pytest
python scripts/run_experiments.py --rounds 100 --seed 42
python scripts/run_balanced_evaluation.py --rounds-per-scenario 20 --seed 42
python scripts/run_hard_mode.py --rounds 100 --seed 42
python scripts/goal_runner.py --target-score 92 --strict
docker compose up --build
```
