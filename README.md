# Aegis-Swarm v2

**Aegis-Swarm**은 DAH 2026 예선 제출을 목표로 만든 안전한 Red-Blue-Commander self-play AI 시뮬레이션입니다. UAV/UGV 임무 서비스를 로컬로 흉내 내고, Red Agent가 안전한 이상 이벤트를 만들며, Blue Agent가 SLA를 고려해 방어 액션을 선택합니다. Commander Agent는 보안 대응과 임무 가용성의 균형을 조정합니다.

이 프로젝트는 실제 공격 도구가 아닙니다. 모든 Red behavior는 SQLite에 기록되는 로컬 시뮬레이션 이벤트입니다.

## 1. 문제 정의

방산 임무 서비스에서는 공격 징후를 강하게 차단하는 것만으로는 충분하지 않습니다. 잘못된 차단은 임무 지연, telemetry 단절, 서비스 재시작을 만들 수 있고, 이는 SLA와 임무 지속성 손실로 이어집니다.

Aegis-Swarm v2는 다음 질문에 답합니다.

- Red anomaly가 발생했을 때 Blue Agent는 어떤 근거로 위험도를 계산하는가?
- 방어 액션 이후 SLA가 실제로 회복되거나 보존되는가?
- 특정 scenario에서 Blue가 반복 실패하면 다음 판단이 적응하는가?
- scoring이 단순 severity가 아니라 방어 적합성, 회복성, 오탐 비용까지 반영하는가?
- 실험 결과를 CSV로 남겨 제출 보고서의 근거로 사용할 수 있는가?

## 2. 안전성 경계

구현하지 않는 것:

- 실제 해킹 또는 취약점 악용
- 포트 스캔, 네트워크 스캔
- 브루트포스, credential attack, credential theft
- malware, persistence, lateral movement
- 외부 시스템 공격 또는 침투 행위
- 외부 target interaction

Red Agent는 다음 안전한 로컬 이벤트만 생성합니다.

- `TRAFFIC_SPIKE`
- `AUTH_ANOMALY`
- `TELEMETRY_INCONSISTENCY`
- `SERVICE_DEGRADATION`
- `MISSION_COMMAND_ANOMALY`
- `LOG_NOISE`

## 3. v2 아키텍처

```text
FastAPI Mission Service
  ├─ Red Agent
  │   └─ epsilon-greedy safe scenario selection
  ├─ Blue Agent
  │   ├─ triage policy
  │   ├─ containment policy
  │   ├─ recovery policy
  │   ├─ deception policy
  │   └─ SLA governor
  ├─ Commander Agent
  ├─ SQLite
  │   ├─ events
  │   ├─ actions
  │   ├─ scores
  │   └─ scenario_stats
  ├─ Competition Adapter
  │   ├─ LocalSimulatorAdapter
  │   └─ CompetitionStubAdapter
  └─ Streamlit Judging Dashboard
```

주요 디렉터리:

- `mission_service/`: FastAPI API와 SQLite persistence
- `agents/blue/`: Blue Agent 모듈형 정책
- `agents/red_agent.py`: 안전한 Red scenario generator
- `agents/commander_agent.py`: 운영 모드 결정
- `core/`: SLA, scoring, action registry, knowledge mapping
- `adapters/`: 로컬/대회 adapter 인터페이스
- `dashboard/`: Streamlit judging dashboard
- `scripts/run_experiments.py`: 반복 실험 및 CSV evidence 생성
- `reports/`: 실험 결과 CSV

## 4. Blue Agent 모듈형 정책

Blue Agent public interface는 그대로 유지됩니다.

```python
from agents.blue_agent import BlueAgent

decision = BlueAgent().decide(events, sla_score=None)
```

내부 정책:

- `triage_policy`: component score와 risk level 계산
- `containment_policy`: traffic/auth/telemetry containment 선택
- `recovery_policy`: service degradation과 낮은 SLA 복구 우선
- `deception_policy`: mission command anomaly, decoy, escalation 처리
- `sla_governor`: SLA threshold와 recent failure awareness 적용

Scenario memory에서 Blue 실패가 누적되면 해당 event type의 올바른 response class 우선순위가 올라갑니다.

## 5. Commander Agent 역할

Commander Agent는 최근 SLA와 score history를 보고 운영 모드를 선택합니다.

- `BALANCED`: 보안 대응과 임무 지속성 균형
- `RECOVERY_FIRST`: SLA가 낮아 복구 우선
- `DEFENSE_HARDENING`: Blue 실패가 누적되어 방어 강화
- `RED_EXPLORATION`: Red scenario coverage 확대

## 6. Scenario Memory

`scenario_stats` 테이블은 scenario별 self-play memory를 저장합니다.

- attempts
- red_success_count
- blue_success_count
- avg_sla_drop
- avg_recovery_delta
- false_positive_count
- most_effective_blue_action
- last_seen_at

`GET /stats/scenarios`는 scenario stats, entropy, coverage score, total attempts를 반환합니다.

## 7. 현실적인 Scoring Model

v2 scoring은 severity만으로 Red 성공을 계산하지 않습니다.

주요 지표:

- `red_success_score`: mismatched action, SLA drop, degraded mission, recovery failure를 반영
- `blue_defense_score`: action match, SLA preservation, recovery success, false positive avoidance를 반영
- `sla_preservation_score`: 방어 후 SLA 보존 정도
- `recovery_score`: Red 이벤트 이후 Blue action이 SLA를 얼마나 회복했는지
- `false_positive_penalty`: 정상/노이즈 이벤트에 과잉 대응한 비용
- `action_cost`: 재시작, 롤백, 격리 같은 액션의 운영 비용
- `total_utility`: Red 성공을 감점하고 Blue/SLA/recovery를 가산하는 종합 점수

## 8. 측정 가능한 SLA Recovery

`POST /selfplay/round`는 Blue action 이후 `RECOVERY_HEALTH_CHECK` 이벤트를 추가로 기록합니다.

반환 필드:

- `pre_sla`
- `post_event_sla`
- `post_action_sla`
- `sla_delta`
- `recovery_delta`

따라서 보고서와 dashboard에서 "공격 이벤트 전 - 이벤트 직후 - 방어 후"의 SLA 변화를 정량적으로 보여줄 수 있습니다.

## 9. Dashboard 사용

API와 dashboard 실행:

```bash
uvicorn mission_service.app:app --reload --port 8000
streamlit run dashboard/streamlit_app.py
```

접속:

- API: `http://localhost:8000`
- Dashboard: `http://localhost:8501`

Dashboard가 보여주는 항목:

- SLA history line chart
- latest Blue reasoning card
- before/after SLA delta
- scenario stats table
- per-scenario success chart
- Commander mode timeline
- D3FEND action mapping
- latest self-play round summary

Dashboard의 핵심 흐름:

```text
Attack event -> Blue decision -> Action -> SLA recovery -> Score update
```

## 10. Experiment Runner

반복 실험 실행:

```bash
python scripts/run_experiments.py --rounds 100 --seed 42
```

생성 파일:

- `reports/round_metrics.csv`
- `reports/scenario_summary.csv`

콘솔 출력:

- average SLA
- average SLA drop
- average recovery delta
- average utility
- false positive rate
- recovery success rate
- scenario entropy
- coverage score

Docker는 필요하지 않습니다. `seed`가 주어지면 실험용 SQLite DB를 초기화하고 deterministic하게 실행합니다.

## 11. 주요 API

- `GET /health`
- `GET /adapter/status`
- `GET /mission/status`
- `GET /vehicle/state`
- `GET /telemetry`
- `GET /logs/recent?limit=50`
- `GET /stats/scenarios`
- `POST /simulate/event`
- `POST /agent/blue/decide`
- `POST /selfplay/round`

## 12. Adapter Layer와 대회 연동

현재 기본 adapter는 `LocalSimulatorAdapter`입니다. 실제 대회 API가 공개되면 public repo의 로직을 바꾸기보다 private adapter를 별도로 구현해 연결해야 합니다.

중요 원칙:

- 공식 대회 연동은 private adapter에서만 수행합니다.
- public repository에는 NDA 자료, private API endpoint, token, 운영 로그, 비공개 scoring detail을 포함하지 않습니다.
- 공개 repo에는 안전한 local simulator와 interface만 유지합니다.

환경변수:

```bash
AEGIS_ADAPTER=local
AEGIS_ADAPTER=competition_stub
```

`competition_stub`는 외부 호출을 하지 않고 "not configured" 상태만 반환합니다.

## 13. 테스트

```bash
pytest
```

검증 범위:

- Blue Agent modular policy
- recent failure awareness
- SLA 계산
- measurable recovery
- realistic scoring
- scenario stats
- knowledge mapping
- experiment runner CSV generation
- API smoke tests

## 14. Docker 실행

```bash
docker compose up --build
```

포트:

- API: `8000`
- Dashboard: `8501`

## 15. 제출 준비 문서

- [아키텍처 설명](docs/architecture.md)
- [데모 시나리오](docs/demo_scenarios.md)
- [실험 가이드](docs/experiment_guide.md)
- [보고서 아웃라인](docs/report_outline.md)
- [예선 제출 보고서 초안](docs/report.md)
- [제출 준비 체크리스트](docs/submission_checklist.md)
- [데모 스크립트](docs/demo_script.md)
- [제출 패키징 안내](docs/submission_package.md)
