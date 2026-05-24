# Aegis-Swarm v2 Submission Checklist

## Evidence Status

- [x] `pytest` passed locally: 40 tests passed.
- [x] Adaptive self-play report generated: `reports/round_metrics.csv`.
- [x] Adaptive scenario summary generated: `reports/scenario_summary.csv`.
- [x] Balanced evaluation report generated: `reports/balanced_round_metrics.csv`.
- [x] Balanced scenario summary generated: `reports/balanced_scenario_summary.csv`.
- [x] Docker was verified locally for API port 8000 and Streamlit port 8501.
- [ ] Dashboard screenshots available for final submission package.
- [ ] Final public repository review confirms no secrets, credentials, NDA data, or private competition endpoints.

## Required Final Artifacts

- [x] `README.md`
- [x] `docs/report.md`
- [x] `docs/experiment_results.md`
- [x] `docs/presentation_script.md`
- [x] `scripts/run_experiments.py`
- [x] `scripts/run_balanced_evaluation.py`
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
- [ ] Before publishing, inspect environment files and Git history for accidental secrets.

## Demo Readiness

- [x] `POST /selfplay/round` returns Red event, Blue decision, Commander mode, DAH scores, strategy notes, recovery event, and knowledge mapping.
- [x] Adaptive 100-round experiment completed with seed 42.
- [x] Balanced 120-round evaluation completed with seed 42 and 20 rounds per scenario.
- [ ] Capture dashboard screenshots showing SLA, Commander mode, DAH scoring view, recent events, and Blue decisions.
- [ ] Export final report to PDF and check file size.

## Commands

```bash
pytest
python scripts/run_experiments.py --rounds 100 --seed 42
python scripts/run_balanced_evaluation.py --rounds-per-scenario 20 --seed 42
docker compose up --build
```
