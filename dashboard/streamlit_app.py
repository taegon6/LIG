from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
import streamlit as st


API_URL = os.getenv("AEGIS_API_URL", "http://localhost:8000").rstrip("/")


EVENT_LABELS = {
    "NORMAL": ("Normal", "정상 운영 로그"),
    "TRAFFIC_SPIKE": ("Traffic Spike", "요청이 갑자기 몰리는 상황"),
    "AUTH_ANOMALY": ("Auth Anomaly", "이상한 인증 시도가 늘어난 상황"),
    "TELEMETRY_INCONSISTENCY": ("Telemetry Issue", "차량 센서/위치 데이터가 흔들리는 상황"),
    "SERVICE_DEGRADATION": ("Service Slowdown", "서비스가 느려지거나 오류가 늘어난 상황"),
    "MISSION_COMMAND_ANOMALY": ("Command Anomaly", "평소와 다른 임무 명령이 들어온 상황"),
    "LOG_NOISE": ("Log Noise", "큰 위험은 아니지만 로그가 지저분해진 상황"),
}

ACTION_LABELS = {
    "OBSERVE_ONLY": ("Observe", "지켜보기"),
    "APPLY_RATE_LIMIT": ("Rate Limit", "요청량을 줄여 서비스 안정화"),
    "BLOCK_SUSPICIOUS_TOKEN": ("Block Token", "의심 인증 토큰 차단"),
    "ISOLATE_TELEMETRY_STREAM": ("Isolate Telemetry", "센서/통신 흐름 격리"),
    "RESTART_SERVICE": ("Restart", "서비스 재시작으로 복구 우선"),
    "ROLLBACK_VERSION": ("Rollback", "안정 버전으로 되돌리기"),
    "DEPLOY_DECOY": ("Deploy Decoy", "가짜 표적 배치"),
    "ESCALATE_ALERT": ("Escalate", "사람 담당자에게 경고"),
}

MODE_LABELS = {
    "BALANCED": ("Balanced", "보안 대응과 임무 지속성을 균형 있게 유지"),
    "RECOVERY_FIRST": ("Recovery First", "SLA가 낮아 복구를 최우선"),
    "DEFENSE_HARDENING": ("Defense Hardening", "방어 실패가 누적되어 보안 강화"),
    "RED_EXPLORATION": ("Red Exploration", "다양한 안전 시나리오 탐색"),
}


def api_get(path: str) -> dict[str, Any]:
    response = requests.get(f"{API_URL}{path}", timeout=5)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.post(f"{API_URL}{path}", json=payload or {}, timeout=10)
    response.raise_for_status()
    return response.json()


def trigger_scenario(name: str, intensity: float) -> None:
    result = api_post("/simulate/event", {"scenario": name, "intensity": intensity})
    st.session_state["last_result"] = result


def fmt_score(value: Any, suffix: str = "") -> str:
    if value in (None, ""):
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:.1f}{suffix}"
    return str(value)


def event_name(event_type: str | None) -> str:
    if not event_type:
        return "-"
    label, description = EVENT_LABELS.get(event_type, (event_type, event_type))
    return f"{label} - {description}"


def action_name(action_type: str | None) -> str:
    if not action_type:
        return "-"
    label, description = ACTION_LABELS.get(action_type, (action_type, action_type))
    return f"{label} - {description}"


def mode_name(mode: str) -> str:
    label, description = MODE_LABELS.get(mode, (mode, mode))
    return f"{label}: {description}"


def health_badge(sla_score: float, mission_status: str, comm_status: str) -> tuple[str, str]:
    if mission_status != "ACTIVE":
        return "주의 필요", "임무 상태가 ACTIVE가 아닙니다."
    if sla_score < 85:
        return "복구 우선", "서비스 품질이 낮아 복구 액션이 우선입니다."
    if sla_score < 95 or comm_status not in {"NORMAL", "DEGRADED_BUT_CONTAINED"}:
        return "관찰 필요", "임무는 진행 중이지만 통신이나 품질 변화가 있습니다."
    return "안정", "임무와 서비스 품질이 안정적으로 유지되고 있습니다."


def simple_events(events: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for event in events:
        rows.append(
            {
                "시간": str(event.get("timestamp", ""))[11:19],
                "상황": event_name(event.get("event_type")),
                "강도": fmt_score(event.get("severity")),
                "지연(ms)": event.get("latency_ms"),
                "임무": event.get("mission_status"),
                "설명": event.get("description"),
            }
        )
    return pd.DataFrame(rows)


def simple_actions(actions: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for action in actions:
        rows.append(
            {
                "시간": str(action.get("timestamp", ""))[11:19],
                "AI 판단": action_name(action.get("action_type")),
                "위험도": action.get("risk_level"),
                "확신도": fmt_score(action.get("confidence")),
                "SLA 영향": action.get("expected_sla_impact"),
                "이유": action.get("reason"),
            }
        )
    return pd.DataFrame(rows)


def explain_last_result(result: dict[str, Any]) -> None:
    red_event = result.get("red_event") or result.get("event") or {}
    blue_decision = result.get("blue_decision") or {}
    score = result.get("dah_scores") or result.get("score") or {}
    notes = result.get("strategy_notes") or {}

    st.markdown("#### 이번 라운드 요약")
    cols = st.columns(4)
    cols[0].metric("발생한 상황", EVENT_LABELS.get(red_event.get("event_type"), ("-", ""))[0])
    cols[1].metric("AI 위험 판단", blue_decision.get("risk_level", "-"))
    cols[2].metric("선택한 대응", ACTION_LABELS.get(blue_decision.get("selected_action"), ("-", ""))[0])
    cols[3].metric("총 효용", fmt_score(score.get("total_utility")))

    if notes:
        st.info(
            "\n\n".join(
                [
                    f"Commander: {notes.get('commander', '-')}",
                    f"Red: {notes.get('red', '-')}",
                    f"Blue: {notes.get('blue', '-')}",
                ]
            )
        )

    with st.expander("개발자용 JSON 보기"):
        st.json(result)


st.set_page_config(page_title="Aegis-Swarm", page_icon="A", layout="wide")

st.title("Aegis-Swarm 상황판")
st.caption("방산 임무 서비스에서 AI가 이상 상황을 감지하고, 임무를 멈추지 않도록 방어 결정을 내리는 안전한 로컬 시뮬레이션")

try:
    health = api_get("/health")
    mission = api_get("/mission/status")
    vehicle = api_get("/vehicle/state")
    adapter = api_get("/adapter/status")
    logs = api_get("/logs/recent?limit=25")
except requests.RequestException as exc:
    st.error(f"API 서버에 연결할 수 없습니다: {exc}")
    st.stop()

events = logs.get("events", [])
actions = logs.get("actions", [])
scores = logs.get("scores", [])
latest_event = events[0] if events else {}
latest_action = actions[0] if actions else {}
latest_score = scores[0] if scores else {}

mission_status = mission.get("mission_status", "UNKNOWN")
comm_status = mission.get("comm_status", "UNKNOWN")
sla_score = float(health.get("sla_score", 0.0))
status_label, status_text = health_badge(sla_score, mission_status, comm_status)
commander_mode = mission.get("commander_mode", "BALANCED")

overview = st.columns([1.2, 1, 1, 1])
overview[0].metric("현재 상태", status_label)
overview[0].caption(status_text)
overview[1].metric("임무 상태", mission_status)
overview[1].caption(f"통신 상태: {comm_status}")
overview[2].metric("서비스 품질", f"{sla_score:.1f}%")
overview[2].caption("95% 이상이면 안정권")
overview[3].metric("Commander", MODE_LABELS.get(commander_mode, (commander_mode, ""))[0])
overview[3].caption(MODE_LABELS.get(commander_mode, ("", ""))[1])

st.divider()

left, right = st.columns([1.1, 0.9])
with left:
    st.subheader("지금 무슨 일이 일어났나")
    if latest_event:
        st.markdown(f"**최근 상황:** {event_name(latest_event.get('event_type'))}")
        st.write(latest_event.get("description", "설명이 없습니다."))
        event_cols = st.columns(4)
        event_cols[0].metric("상황 강도", fmt_score(latest_event.get("severity")))
        event_cols[1].metric("응답 지연", f"{latest_event.get('latency_ms', '-')} ms")
        event_cols[2].metric("상태 코드", latest_event.get("status_code", "-"))
        event_cols[3].metric("SLA 만족", "YES" if latest_event.get("sla_ok") else "NO")
    else:
        st.info("아직 이벤트가 없습니다. 아래 버튼으로 안전한 시뮬레이션을 시작해보세요.")

with right:
    st.subheader("AI가 내린 판단")
    if latest_action:
        st.markdown(f"**선택한 대응:** {action_name(latest_action.get('action_type'))}")
        st.write(latest_action.get("reason", "판단 이유가 없습니다."))
        action_cols = st.columns(3)
        action_cols[0].metric("위험도", latest_action.get("risk_level", "-"))
        action_cols[1].metric("확신도", fmt_score(latest_action.get("confidence")))
        action_cols[2].metric("SLA 영향", latest_action.get("expected_sla_impact", "-"))
    else:
        st.info("아직 Blue Agent 판단이 없습니다. Self-play 라운드를 실행하면 판단이 표시됩니다.")

st.subheader("버튼으로 보는 안전 시뮬레이션")
st.caption("아래 버튼은 실제 공격이 아니라 로컬 SQLite에 안전한 상황 이벤트를 기록합니다.")
scenario_cols = st.columns(5)
with scenario_cols[0]:
    if st.button("요청 폭주", use_container_width=True, help="TRAFFIC_SPIKE 이벤트 생성"):
        trigger_scenario("TRAFFIC_SPIKE", 0.7)
with scenario_cols[1]:
    if st.button("인증 이상", use_container_width=True, help="AUTH_ANOMALY 이벤트 생성"):
        trigger_scenario("AUTH_ANOMALY", 0.7)
with scenario_cols[2]:
    if st.button("센서 불일치", use_container_width=True, help="TELEMETRY_INCONSISTENCY 이벤트 생성"):
        trigger_scenario("TELEMETRY_INCONSISTENCY", 0.8)
with scenario_cols[3]:
    if st.button("서비스 저하", use_container_width=True, help="SERVICE_DEGRADATION 이벤트 생성"):
        trigger_scenario("SERVICE_DEGRADATION", 0.8)
with scenario_cols[4]:
    if st.button("AI 한 판 실행", use_container_width=True, type="primary", help="Red-Blue-Commander 전체 라운드 실행"):
        st.session_state["last_result"] = api_post("/selfplay/round")

if "last_result" in st.session_state:
    explain_last_result(st.session_state["last_result"])

st.divider()

score_cols = st.columns(4)
score_cols[0].metric("Attack Score", fmt_score(latest_score.get("attack_score")))
score_cols[0].caption("Red가 만든 이상 상황의 강도")
score_cols[1].metric("Defense Score", fmt_score(latest_score.get("defense_score")))
score_cols[1].caption("Blue 대응이 상황에 맞았는지")
score_cols[2].metric("SLA Score", f"{sla_score:.1f}%")
score_cols[2].caption("임무 서비스가 안정적으로 유지되는지")
score_cols[3].metric("Total Utility", fmt_score(latest_score.get("total_utility")))
score_cols[3].caption("방어와 가용성을 합친 종합 점수")

with st.expander("차량/임무 상태 자세히 보기"):
    vehicle_cols = st.columns(4)
    position = vehicle.get("position", {})
    vehicle_cols[0].metric("차량", vehicle.get("vehicle_type", "-"))
    vehicle_cols[1].metric("배터리", f"{vehicle.get('battery', '-')}%")
    vehicle_cols[2].metric("위치 X", position.get("x", "-"))
    vehicle_cols[3].metric("위치 Y", position.get("y", "-"))
    st.json(vehicle)

with st.expander("대회 연동 준비 상태"):
    adapter_cols = st.columns(3)
    adapter_cols[0].metric("Adapter", adapter.get("adapter_mode", "-"))
    adapter_cols[1].metric("Ready", "YES" if adapter.get("ready") else "NO")
    adapter_cols[2].metric("외부 접속", "YES" if adapter.get("external_access") else "NO")
    st.caption(adapter.get("description", ""))

tab_events, tab_actions, tab_scores = st.tabs(["상황 로그", "AI 대응 기록", "점수 기록"])
with tab_events:
    st.dataframe(simple_events(events), use_container_width=True, hide_index=True)
with tab_actions:
    st.dataframe(simple_actions(actions), use_container_width=True, hide_index=True)
with tab_scores:
    st.dataframe(scores, use_container_width=True, hide_index=True)
