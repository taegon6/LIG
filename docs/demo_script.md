# Aegis-Swarm 데모 스크립트

목표: DAH 예선 심사자가 3~5분 안에 프로젝트 의도, 안전성, 실행 가능성, DAH 평가축 대응을 이해하도록 한다.

## 1. 데모 준비

```bash
docker compose up --build -d
```

확인:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/selfplay/round
```

브라우저:

```text
http://localhost:8501
```

## 2. 3분 데모 흐름

### 0:00 - 0:30 문제 정의

설명:

> 방산 임무 환경에서는 보안 대응과 임무 지속성 사이의 균형이 중요합니다. Aegis-Swarm은 Red-Blue Self-Play를 통해 공격 이상 이벤트, 방어 판단, SLA 영향을 한 라운드 안에서 설명 가능하게 보여줍니다.

보여줄 화면:

- Dashboard 상단 DAH Scoring View
- SLA Score, Attack Score, Defense Score, Total Utility

### 0:30 - 1:10 안전한 Red event

버튼:

- `Traffic Spike`
- `Telemetry Inconsistency`

설명:

> Red Agent는 실제 공격을 수행하지 않습니다. 모든 이벤트는 SQLite에 기록되는 안전한 로컬 시뮬레이션입니다.

보여줄 화면:

- Recent Events 테이블
- event_type, severity, latency_ms, mission_status

### 1:10 - 2:10 Self-play round

버튼:

- `Run Self-Play Round`

설명:

> Commander가 현재 SLA와 최근 점수를 보고 운영 모드를 선택합니다. Red는 안전 이벤트를 생성하고, Blue는 risk score와 SLA-aware policy를 기반으로 방어 액션을 선택합니다.

보여줄 화면:

- Latest Result
- `blue_decision`
- `dah_scores`
- `strategy_notes`

### 2:10 - 3:00 본선 확장성

설명:

> 현재는 LocalSimulatorAdapter를 사용하지만, 본선 환경에서는 CompetitionStubAdapter 자리에 실제 대회 API adapter를 연결하면 됩니다. 에이전트 판단 루프는 유지하고 이벤트 수집, 방어 액션 제출, 점수 조회만 교체합니다.

보여줄 화면:

- Adapter: local
- External Access: NO
- `/adapter/status` 응답

## 3. 5분 데모 확장

3분 데모에 아래를 추가한다.

### 시나리오 A: Traffic Spike

명령:

```bash
curl -X POST http://localhost:8000/simulate/event ^
  -H "Content-Type: application/json" ^
  -d "{\"scenario\":\"TRAFFIC_SPIKE\",\"intensity\":0.7}"
curl -X POST http://localhost:8000/agent/blue/decide
```

기대 설명:

- Traffic spike와 latency가 올라간다.
- SLA가 충분히 안정적이면 `APPLY_RATE_LIMIT`가 선택된다.
- 과도한 restart 대신 낮은 SLA 영향의 대응을 선택한다.

### 시나리오 B: Telemetry Inconsistency

명령:

```bash
curl -X POST http://localhost:8000/simulate/event ^
  -H "Content-Type: application/json" ^
  -d "{\"scenario\":\"TELEMETRY_INCONSISTENCY\",\"intensity\":0.8}"
curl -X POST http://localhost:8000/agent/blue/decide
```

기대 설명:

- Telemetry integrity risk가 올라간다.
- Blue는 `ISOLATE_TELEMETRY_STREAM` 또는 SLA 상황에 맞는 containment action을 선택한다.

### 시나리오 C: Service Degradation

명령:

```bash
curl -X POST http://localhost:8000/simulate/event ^
  -H "Content-Type: application/json" ^
  -d "{\"scenario\":\"SERVICE_DEGRADATION\",\"intensity\":0.85}"
curl -X POST http://localhost:8000/selfplay/round
```

기대 설명:

- SLA가 흔들리면 Commander는 recovery-first 판단을 하게 된다.
- Blue는 blocking보다 service recovery 계열 action을 우선한다.

## 4. 데모에서 강조할 문장

- "실제 공격 기능이 아니라 안전한 로컬 self-play 시뮬레이션입니다."
- "DAH 평가축인 attack, defense, SLA를 각각 점수로 분리해 보여줍니다."
- "방산 임무 환경에서는 보안 조치와 임무 지속성의 trade-off가 핵심입니다."
- "본선 API가 공개되면 Competition Adapter만 교체해 연결할 수 있습니다."

## 5. 녹화 체크리스트

- [ ] Docker Compose 실행 장면
- [ ] Dashboard 첫 화면
- [ ] Traffic Spike 버튼
- [ ] Run Self-Play Round 버튼
- [ ] `dah_scores` JSON
- [ ] `strategy_notes` JSON
- [ ] `/adapter/status` 결과
- [ ] 안전성 설명 화면 또는 README 안전성 섹션
