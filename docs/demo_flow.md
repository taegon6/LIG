# Demo Flow

## 1. Start Locally

```bash
docker compose up --build
```

Open:

- API: `localhost:8000`
- Dashboard: `localhost:8501`

## 2. Show Mission Health

Call `GET /health` and show SLA, mission status, and local-only service state.

## 3. Run One Self-Play Round

Call `POST /selfplay/round`. Highlight:

- Commander mode
- Red objective and safe event
- Blue decision and reason
- post-event SLA and post-action SLA
- Red success score and total utility

## 4. Show Red Readiness Stats

Call `GET /stats/red`. Explain the five Red objectives, safe event coverage,
scenario memory, and recent Red success score.

## 5. Show Dashboard

Use scenario buttons for Traffic Spike, Auth Anomaly, Telemetry Inconsistency,
Service Degradation, and Self-Play Round. Explain that all behavior is local
simulation.

## 6. Show Evidence Reports

Open:

- `docs/one_page_summary.md`
- `docs/experiment_results.md`
- `docs/failure_analysis.md`
- `reports/goal_score.md`

## 7. Close With Limitations

State clearly that Aegis-Swarm v2 is not official DAH runtime evidence yet.
Official integration requires a private adapter and competition environment.
