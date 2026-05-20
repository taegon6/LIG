# DAH 2026 제출 준비 체크리스트

확인 기준: `https://dah.ai.kr/guide`, `https://dah.ai.kr/schedule`  
확인일: 2026-05-20

## 1. 공식 일정

| 항목 | 일정 |
| --- | --- |
| 참가 접수 마감 | 2026-06-14 23:59 |
| 예선 보고서 제출 시작 | 2026-06-15 00:00 |
| 예선 보고서 제출 마감 | 2026-07-10 23:59 |
| 본선 진출팀 발표 | 2026-07-31 |
| 본선 · 시상식 · VIP 투어 | 2026-08-21 |

## 2. 계정/접수 정보

- [ ] 팀명 확정
- [ ] 참가 부문 확정: 중·고등 / 대학 / 대학원생 / 혼합팀
- [ ] 팀장 이름, 이메일, 연락처 확정
- [ ] 팀원 정보 정리
- [ ] 접수번호와 비밀번호 보관
- [ ] 접수 확인/수정 페이지 접근 확인

## 3. 필수 제출물

- [ ] 예선 보고서 통합 PDF 1부
- [ ] PDF 파일 크기 50MB 이하 확인
- [ ] 부가자료 링크 준비
- [ ] 부가자료 링크가 운영팀 접근 가능 상태인지 확인
- [ ] 학생 부문이면 재학증명서 또는 교수추천서 준비
- [ ] 학생 증빙은 팀원 전원 통합 PDF 1부로 준비
- [ ] 학생 증빙 PDF 50MB 이하 확인

## 4. Aegis-Swarm 제출 패키지

- [ ] `README.md`: 프로젝트 개요, 안전성, 실행법, API, demo flow
- [ ] `docs/report.md`: 예선 보고서 원고
- [ ] `docs/demo_script.md`: 3분/5분 데모 시나리오
- [ ] `docker-compose.yml`: API 8000, Dashboard 8501 실행
- [ ] `tests/`: pytest 통과
- [ ] `adapters/`: 본선 연동용 Competition Adapter 구조
- [ ] 실행 검증 로그: pytest, Docker Compose, `/health`, `/selfplay/round`
- [ ] 대시보드 스크린샷
- [ ] self-play round JSON 응답 예시

## 5. 보고서 구성 권장안

1. 문제 정의
2. 프로젝트 개요
3. DAH 평가축 대응: attack, defense, SLA
4. 시스템 아키텍처
5. Red/Blue/Commander Agent 설계
6. SLA-aware policy
7. Competition Adapter와 본선 확장 계획
8. 안전성 선언
9. 데모 시나리오
10. 검증 결과

## 6. 제출 전 최종 검증

```bash
python -m pytest
docker compose up --build -d
curl http://localhost:8000/health
curl -X POST http://localhost:8000/selfplay/round
curl -I http://localhost:8501
docker compose down
```

합격 기준:

- [ ] pytest 통과
- [ ] Docker build 성공
- [ ] API 컨테이너가 8000 포트로 뜸
- [ ] Dashboard 컨테이너가 8501 포트로 뜸
- [ ] `/health` 정상 응답
- [ ] `/selfplay/round`에 `dah_scores`, `strategy_notes` 포함
- [ ] Dashboard에서 DAH Scoring View 표시

## 7. 제출 리스크

- [ ] 부가자료 링크 권한 비공개 상태 방지
- [ ] PDF 50MB 초과 방지
- [ ] 보고서에 실제 공격 기능처럼 보이는 표현 제거
- [ ] 안전성 선언 명확히 표기
- [ ] 제출 마감일 전 최종 업로드 확인
