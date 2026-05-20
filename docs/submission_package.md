# 제출 패키징 안내

## 1. 권장 제출 구성

```text
Aegis-Swarm-DAH2026/
├─ README.md
├─ docs/
│  ├─ report.md
│  ├─ submission_checklist.md
│  ├─ demo_script.md
│  └─ submission_package.md
├─ mission_service/
├─ agents/
├─ core/
├─ simulator/
├─ adapters/
├─ dashboard/
├─ tests/
├─ docker-compose.yml
├─ Dockerfile
├─ requirements.txt
└─ pytest.ini
```

## 2. 제외 권장 항목

제출 zip 또는 공유 폴더에는 아래를 제외한다.

```text
__pycache__/
*.pyc
.pytest_cache/
.venv/
data/
pytest-cache-files-*/
```

이미 `.gitignore`와 `.dockerignore`에 반영되어 있다.

## 3. 제출 전 명령 로그

보고서 또는 부가자료에 아래 결과를 캡처한다.

```bash
python -m pytest
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health
curl -X POST http://localhost:8000/selfplay/round
curl -I http://localhost:8501
docker compose down
```

## 4. PDF 보고서 변환

`docs/report.md`를 기반으로 PDF를 만든다. 변환 도구는 자유롭게 선택한다.

권장 내용:

- 표지: 팀명, 프로젝트명, 대표자, 연락처
- 본문: `docs/report.md`
- 부록: 실행 화면, dashboard, API 응답, 테스트 통과 캡처

## 5. 부가자료 링크

부가자료 링크에는 다음을 포함한다.

- 데모 영상
- GitHub 또는 코드 zip 링크
- Dashboard 스크린샷
- API 응답 예시
- 테스트/Compose 검증 로그

링크 권한은 반드시 "운영팀 접근 가능" 상태로 설정한다.
