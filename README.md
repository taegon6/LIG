# Aegis-Swarm

**Aegis-Swarm**은 DAH 2026 예선 제출을 목표로 한 안전한 Red-Blue Self-Play AI 에이전트 MVP입니다. 방산 임무 서비스에서 발생할 수 있는 이상 징후를 로컬 이벤트로 시뮬레이션하고, Blue Agent가 SLA를 고려해 방어 액션을 선택하며, Commander Agent가 보안 대응과 임무 가용성의 균형을 조정합니다.

## 1. 문제 정의

방산 임무 시스템은 사이버 이상 징후를 빠르게 탐지해야 하지만, 과도한 차단은 임무 지속성과 SLA를 해칠 수 있습니다. Aegis-Swarm은 이 trade-off를 다룹니다.

- Red Agent: 안전한 로컬 이상 이벤트 생성
- Blue Agent: 로그와 SLA 기반 위험도 산출 및 방어 액션 선택
- Commander Agent: SLA, 최근 점수, 방어 성과를 보고 운영 모드 조정
- Dashboard: DAH 평가축인 공격 점수, 방어 점수, SLA, 총 효용 표시

## 2. 솔루션 개요

Aegis-Swarm은 실제 공격 도구가 아니라 **방어 의사결정 실험 프레임워크**입니다. 모든 공격 행동은 SQLite에 기록되는 시뮬레이션 이벤트이며, 외부 시스템을 스캔하거나 공격하지 않습니다.

Self-play 라운드는 다음 순서로 진행됩니다.

1. Commander Agent가 현재 SLA와 최근 점수를 보고 모드를 선택합니다.
2. Red Agent가 안전한 시뮬레이션 이벤트를 생성합니다.
3. 이벤트가 SQLite에 저장됩니다.
4. Blue Agent가 최근 로그를 관찰하고 risk score를 계산합니다.
5. Blue Agent가 SLA-aware policy로 방어 액션을 선택합니다.
6. Action Registry가 로컬 미션 상태만 전이합니다.
7. Scoring 모듈이 attack, defense, SLA, recovery, utility를 계산합니다.

## 3. 아키텍처

```text
FastAPI Mission Service
  ├─ Red Agent
  ├─ Blue Agent
  ├─ Commander Agent
  ├─ SQLite logs/scores/actions
  ├─ Competition Adapter
  │   ├─ LocalSimulatorAdapter
  │   └─ CompetitionStubAdapter
  └─ Streamlit Dashboard
```

주요 디렉터리:

- `mission_service/`: FastAPI API와 SQLite 연결
- `agents/`: Red, Blue, Commander 에이전트
- `core/`: 이벤트 스키마, SLA, 정책, scoring, action registry
- `simulator/`: 안전한 로컬 이벤트 생성기
- `adapters/`: 로컬 시뮬레이터와 향후 대회 환경 연결 인터페이스
- `dashboard/`: Streamlit DAH 점수판
- `docs/report.md`: DAH 예선 제출 보고서 초안
- `docs/submission_checklist.md`: 공식 일정/제출물 기반 체크리스트
- `docs/demo_script.md`: 3분/5분 시연 스크립트

## 4. 안전성 선언

이 프로젝트는 다음 기능을 구현하지 않습니다.

- 실제 해킹 또는 취약점 악용
- 포트 스캔, 네트워크 스캔
- 브루트포스, credential attack, credential theft
- malware, persistence, lateral movement
- 외부 시스템에 대한 공격 또는 침투 행위

Red Agent는 `TRAFFIC_SPIKE`, `AUTH_ANOMALY`, `TELEMETRY_INCONSISTENCY`, `SERVICE_DEGRADATION`, `MISSION_COMMAND_ANOMALY`, `LOG_NOISE` 같은 안전한 로컬 이벤트만 생성합니다.

## 5. 실행 방법

Python 3.11 이상을 권장합니다.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

API 서버:

```bash
uvicorn mission_service.app:app --reload --port 8000
```

대시보드:

```bash
streamlit run dashboard/streamlit_app.py
```

접속:

- API: `http://localhost:8000`
- Dashboard: `http://localhost:8501`

Docker Compose:

```bash
docker compose up --build
```

## 6. 주요 API

- `GET /health`: 서비스 상태, SLA, 미션 상태
- `GET /adapter/status`: 현재 adapter 모드와 외부 접근 여부
- `GET /mission/status`: Commander 모드와 미션 상태
- `GET /vehicle/state`: UGV 상태
- `POST /vehicle/command`: 안전한 시뮬레이션 명령 기록
- `GET /telemetry`: 텔레메트리 상태
- `GET /logs/recent?limit=50`: 이벤트, 액션, 점수 로그
- `POST /simulate/event`: 안전한 시나리오 이벤트 삽입
- `POST /agent/blue/decide`: Blue Agent 판단 실행
- `POST /selfplay/round`: Red-Blue-Commander self-play 1라운드 실행

## 7. 데모 시나리오

1. `docker compose up --build` 또는 로컬 API/대시보드를 실행합니다.
2. Dashboard에서 `Traffic Spike`, `Auth Anomaly`, `Telemetry Inconsistency`, `Service Degradation`을 실행합니다.
3. `Run Self-Play Round`로 Commander mode, Red event, Blue decision, DAH score summary를 확인합니다.
4. `/selfplay/round` 응답의 `strategy_notes`에서 각 에이전트의 판단 근거를 확인합니다.

예시:

```bash
curl -X POST http://localhost:8000/selfplay/round
```

## 8. 테스트

```bash
pytest
```

검증 항목:

- Blue Agent 정책
- SLA 계산
- scoring utility 공식
- `/health`, `/adapter/status`, `/selfplay/round` API smoke
- LocalSimulatorAdapter와 CompetitionStubAdapter 동작

## 9. 본선 확장 계획

본선 환경이 공개되면 `CompetitionStubAdapter`를 실제 DAH runtime adapter로 교체합니다. 에이전트 판단 루프는 유지하고, 이벤트 수집/방어 액션 제출/점수 조회만 adapter에서 연결합니다. 이렇게 하면 로컬 시뮬레이션과 대회 환경을 같은 인터페이스로 운영할 수 있습니다.

## 10. 제출 준비 문서

- [예선 제출 보고서 초안](docs/report.md)
- [제출 준비 체크리스트](docs/submission_checklist.md)
- [데모 스크립트](docs/demo_script.md)
- [제출 패키징 안내](docs/submission_package.md)
