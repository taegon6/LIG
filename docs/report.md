# Aegis-Swarm DAH 2026 예선 제출 보고서 초안

## 1. 문제 정의

방산 임무 시스템은 사이버 위협을 탐지하고 대응하는 동시에 임무 지속성과 가용성을 유지해야 한다. 단순히 모든 이상 징후를 강하게 차단하면 서비스 SLA가 무너질 수 있고, 반대로 가용성만 중시하면 침해 징후를 놓칠 수 있다.

Aegis-Swarm은 이 균형 문제를 다루기 위한 안전한 Red-Blue Self-Play 에이전트 프레임워크다. Red Agent는 실제 공격을 수행하지 않고 로컬 시뮬레이션 이벤트만 생성한다. Blue Agent는 최근 이벤트와 SLA를 관찰해 위험도를 계산하고, Commander Agent는 보안 대응과 임무 가용성 사이의 우선순위를 조정한다.

## 2. DAH 평가축 대응

DAH 2026의 핵심 평가 관점은 공격 점수, 방어 점수, 가용성/SLA의 균형으로 해석된다. Aegis-Swarm은 이를 다음처럼 모델링한다.

- Attack Score: Red Agent가 생성한 안전한 이상 이벤트의 강도와 시나리오 다양성
- Defense Score: Blue Agent가 이벤트 유형과 위험도에 맞는 대응을 선택했는지
- SLA Score: latency, status code, mission status, sla_ok 기반 가용성 지표
- Total Utility: 방어, 공격, SLA, 복구, false positive penalty를 결합한 통합 효용

이 구조는 본선 환경에서 실제 대회 API가 제공될 경우 Competition Adapter를 통해 동일한 에이전트 판단 루프에 연결할 수 있도록 설계했다.

## 3. 에이전트 설계

### Red Agent

Red Agent는 안전한 로컬 이벤트만 생성한다. 지원 이벤트는 `TRAFFIC_SPIKE`, `AUTH_ANOMALY`, `TELEMETRY_INCONSISTENCY`, `SERVICE_DEGRADATION`, `MISSION_COMMAND_ANOMALY`, `LOG_NOISE`다. 외부 시스템 스캔, 취약점 악용, 자격증명 공격, 악성코드 동작은 구현하지 않는다.

### Blue Agent

Blue Agent는 최근 로그에서 인증 이상, 트래픽 급증, 지연 시간, 텔레메트리 불일치, 오류율 점수를 계산한다. 이 점수를 SLA-aware policy에 입력해 `OBSERVE_ONLY`, `APPLY_RATE_LIMIT`, `ISOLATE_TELEMETRY_STREAM`, `RESTART_SERVICE` 같은 방어 액션을 선택한다.

### Commander Agent

Commander Agent는 SLA와 최근 점수를 보고 `BALANCED`, `RECOVERY_FIRST`, `DEFENSE_HARDENING`, `RED_EXPLORATION` 모드를 선택한다. 이를 통해 self-play가 단순 이벤트 생성이 아니라 임무 상태와 성과에 따라 전략을 바꾸는 구조를 갖는다.

## 4. SLA-aware 방어 전략

Aegis-Swarm의 핵심 차별점은 방어 행동을 SLA와 함께 평가한다는 점이다. 예를 들어 위험이 중간 수준이고 SLA가 안정적이면 rate limit처럼 낮은 영향의 대응을 우선 선택한다. SLA가 낮아지면 차단보다 재시작 또는 롤백 같은 복구 중심 행동을 우선한다.

이 접근은 방산 임무 환경에서 "보안 강화"와 "임무 지속"을 동시에 고려해야 하는 요구에 맞춘 것이다.

## 5. 안전성 선언

본 프로젝트는 안전한 로컬 시뮬레이션 MVP다.

- 실제 해킹 기능 없음
- 포트 스캔, 네트워크 스캔 없음
- 취약점 악용 payload 없음
- 브루트포스 또는 자격증명 탈취 없음
- 악성코드, persistence, lateral movement 없음
- 모든 Red behavior는 SQLite에 기록되는 시뮬레이션 이벤트

Competition Adapter도 현재는 stub만 제공하며 외부 호출을 수행하지 않는다.

## 6. 본선 연동 계획

본선 환경이 공개되면 `CompetitionStubAdapter`를 실제 대회 API adapter로 교체한다. 교체 대상은 이벤트 수집, 미션 상태 조회, 방어 액션 제출, 점수 조회로 제한한다. 에이전트 정책과 scoring view는 유지해 로컬 시뮬레이션과 대회 런타임을 같은 인터페이스로 운영한다.

향후 개선 방향은 다음과 같다.

- 로그 feature extraction 고도화
- 라운드별 전략 메모리 강화
- DAH 공식 점수 API 연동
- 본선 데모용 replay와 report export
- 안전성 검증 체크리스트 자동화
