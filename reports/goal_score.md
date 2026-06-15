# Aegis-Swarm v2 DAH Readiness Score

Target score: 92.0
Total score: 100.0
Hard gates passed: True

## Rubric

| Category | Score |
| --- | ---: |
| Attack Scenario Design | 30.00 |
| Defense Strategy | 25.00 |
| AI Agent Architecture | 25.00 |
| Team Capability | 10.00 |
| Document Completeness | 10.00 |

## Checks

| Check | Passed | Details |
| --- | --- | --- |
| C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest | True | tests\test_red_readiness.py ....                                         [ 75%]<br>tests\test_rolling_metrics.py ..                                         [ 78%]<br>tests\test_scenario_stats.py ....                                        [ 84%]<br>tests\test_scoring.py ......                                             [ 92%]<br>tests\test_sla.py ..                                                     [ 95%]<br>tests\test_stress_scenarios.py ...                                       [100%]<br><br>============================= 69 passed in 14.59s ============================= |
| C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe scripts/run_experiments.py --rounds 100 --seed 42 | True | average recovery delta: 3.0<br>average utility: 71.05<br>false positive rate: 0.0<br>recovery success rate: 1.0<br>scenario entropy: 99.98<br>coverage score: 100.0<br>round metrics CSV: reports\round_metrics.csv<br>scenario summary CSV: reports\scenario_summary.csv |
| C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe scripts/run_balanced_evaluation.py --rounds-per-scenario 20 --seed 42 | True | seed: 42<br>total rounds: 120<br>average SLA: 100.0<br>average utility: 69.9<br>false positive rate: 0.0<br>recovery success rate: 1.0<br>balanced round metrics CSV: reports\balanced_round_metrics.csv<br>balanced scenario summary CSV: reports\balanced_scenario_summary.csv |
| C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe scripts/run_hard_mode.py --rounds 100 --seed 42 | True | average recovery delta: 1.0<br>recovery failure rate: 0.71<br>blue success rate: 1.0<br>red success rate: 0.72<br>false positive rate: 0.0<br>average utility: 40.23<br>hard mode round metrics CSV: reports\hard_mode_round_metrics.csv<br>hard mode summary CSV: reports\hard_mode_summary.csv |
| required_reports | True | all 6 present |
| required_docs | True | all 12 present |
| hard_mode_non_perfect | True | rows=100, non_perfect=True |
| red_readiness | True | {"plan": {"red_objective": "COVERAGE", "event_type": "TELEMETRY_INCONSISTENCY", "intensity": 0.5, "strategy_reason": "Prefer under-sampled safe scenarios to avoid overfitting the self-play loop.", "expected_effect": "Improve scenario coverage across the complete safe event set."}, "objective_names": ["BLUE_MISMATCH", "CONFUSION", "COVERAGE", "RECOVERY_PRESSURE", "SLA_DROP"], "objective_events": ["AUTH_ANOMALY", "LOG_NOISE", "MISSION_COMMAND_ANOMALY", "SERVICE_DEGRADATION", "TELEMETRY_INCONSISTENCY", "TRAFFIC_SPIKE"], "stats_status": 200, "stats_keys": ["average_recent_red_success_score", "coverage_score", "external_access", "local_only", "most_effective_objective", "red_objectives", "red_strategy_stats", "safe_event_types", "scenario_entropy", "scenario_stats", "total_attempts", "total_objective_attempts"]} |
| blue_readiness | True | blue evidence present |
| ai_architecture | True | architecture evidence present |
| docs_completeness | True | docs complete |
| safety_boundaries | True | {"private_adapter_forbidden_hits": [], "source_hits": [], "default_adapter_local": true} |

## Limitations

- This is a local simulation readiness score, not official DAH runtime validation.
- Official integration still requires a private adapter and competition environment access.
