# Aegis-Swarm v2 Experiment Guide

## 목적

`scripts/run_experiments.py`는 self-play를 반복 실행하고 제출 보고서에 사용할 CSV evidence를 생성한다. Docker 없이 Python 환경에서 실행된다.

## 실행

```bash
python scripts/run_experiments.py --rounds 100 --seed 42
```

옵션:

- `--rounds`: 실행할 self-play round 수
- `--seed`: deterministic 실험 seed
- `--reports-dir`: CSV 저장 경로, 기본값 `reports`
- `--db-path`: 실험용 SQLite DB 경로

## 출력 파일

### reports/round_metrics.csv

Round 단위 기록:

- event_type
- severity
- commander_mode
- blue_action
- pre_sla
- post_event_sla
- post_action_sla
- recovery_delta
- red_success_score
- blue_defense_score
- total_utility

### reports/scenario_summary.csv

Scenario별 요약:

- attempts
- average_sla
- average_sla_drop
- average_recovery_delta
- average_utility
- action_accuracy
- false_positive_rate
- recovery_success_rate

## 콘솔 요약

Runner는 다음 값을 출력한다.

- average SLA
- average SLA drop
- average recovery delta
- average utility
- false positive rate
- recovery success rate
- scenario entropy
- coverage score

## 재현성

Seed가 제공되면 runner는 실험용 DB를 초기화하고 같은 seed 기반으로 Red scenario selection을 수행한다. 기존 운영 DB와 섞이지 않도록 기본적으로 `reports/experiment_state.db`를 사용한다.

## 안전성

Runner는 FastAPI `TestClient`로 로컬 self-play endpoint를 호출한다. 외부 target, network scanning, exploit, credential attack은 수행하지 않는다.
