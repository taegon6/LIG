# Aegis-Swarm

Aegis-Swarm은 방어형 사이버 대회 환경을 상정한 안전한 로컬 Red-Blue Self-Play AI 에이전트 MVP입니다. FastAPI 기반 미션 서비스, SQLite 이벤트 저장소, Red/Blue/Commander 에이전트, Streamlit 대시보드를 통해 UAV/UGV 스타일 임무 서비스에서 발생하는 이상 징후와 방어 의사결정을 시뮬레이션합니다.

## 안전 원칙

이 프로젝트는 실제 해킹, 스캔, 취약점 악용, 브루트포스, 악성코드, 자격증명 탈취 기능을 구현하지 않습니다. Red Agent는 외부 시스템에 접근하지 않고, `TRAFFIC_SPIKE`, `AUTH_ANOMALY`, `TELEMETRY_INCONSISTENCY`, `SERVICE_DEGRADATION`, `MISSION_COMMAND_ANOMALY`, `LOG_NOISE` 같은 안전한 로컬 시뮬레이션 이벤트만 SQLite에 기록합니다.

## 아키텍처

- `mission_service`: FastAPI API 서버와 SQLite 접근 계층
- `agents`: Red Agent, Blue Agent, Commander Agent
- `core`: 이벤트 스키마, SLA 계산, 정책, 점수화, 액션 레지스트리
- `simulator`: 안전한 시나리오 이벤트 생성기
- `dashboard`: Streamlit 운영 대시보드
- `tests`: pytest 기반 핵심 로직과 API 스모크 테스트

Self-play 라운드는 Commander가 운영 모드를 정하고, Red가 안전한 이벤트를 생성하며, Blue가 최근 로그와 SLA를 바탕으로 위험도를 계산하고 방어 액션을 선택합니다. Action Registry는 실제 시스템 명령을 실행하지 않고 미션 상태만 로컬로 전이합니다.

## 설치

Python 3.11 이상을 권장합니다.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 로컬 실행

API 서버:

```bash
uvicorn mission_service.app:app --reload --port 8000
```

대시보드:

```bash
streamlit run dashboard/streamlit_app.py
```

브라우저에서 `http://localhost:8501`로 접속합니다.

## Docker Compose 실행

```bash
docker compose up --build
```

- API: `http://localhost:8000`
- Dashboard: `http://localhost:8501`
- SQLite 데이터는 Docker volume `aegis_data`에 저장됩니다.

## API 엔드포인트

- `GET /health`: 서비스 상태, 현재 SLA, 미션 상태
- `GET /mission/status`: 시뮬레이션 미션 상태와 Commander 모드
- `GET /vehicle/state`: UGV 차량 상태
- `POST /vehicle/command`: 안전한 시뮬레이션 명령 접수
- `GET /telemetry`: 현재 텔레메트리
- `GET /logs/recent?limit=50`: 최근 이벤트, 액션, 점수 로그
- `POST /simulate/event`: 지정한 안전 시나리오 이벤트 삽입
- `POST /agent/blue/decide`: Blue Agent 의사결정 실행
- `POST /selfplay/round`: Commander, Red, Blue, Action, Scoring 전체 라운드 실행

## 데모 시나리오

1. `docker compose up --build`를 실행합니다.
2. `http://localhost:8501`에서 대시보드를 엽니다.
3. `Traffic Spike`, `Auth Anomaly`, `Telemetry Inconsistency`, `Service Degradation` 버튼으로 안전 이벤트를 생성합니다.
4. `Run Self-Play Round`를 눌러 Commander 모드, Red 이벤트, Blue 방어 결정, 점수 결과를 확인합니다.

예시 API 호출:

```bash
curl -X POST http://localhost:8000/selfplay/round
```

응답에는 `commander_mode`, `red_event`, `blue_decision`, `sla_score`, `score.total_utility`가 포함됩니다.

## 테스트

```bash
pytest
```

테스트는 Blue Agent 정책, SLA 계산, 점수 공식, `/health` API 스모크 동작을 검증합니다.

## 향후 개선

- 대회용 시나리오 팩과 난이도 설정 추가
- 방어 정책별 SLA 비용 모델 고도화
- 라운드별 리플레이와 에이전트 메모리 시각화
- 팀별 점수판과 시나리오별 리더보드
- 실제 대회 인프라와 연동할 때도 외부 공격 기능 없이 이벤트 수집 어댑터만 분리 적용
