from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st


API_URL = os.getenv("AEGIS_API_URL", "http://localhost:8000").rstrip("/")
REPORTS_DIR = Path(os.getenv("AEGIS_REPORTS_DIR", "reports"))


EVENT_LABELS = {
    "NORMAL": ("Normal", "정상 운영"),
    "TRAFFIC_SPIKE": ("Traffic Spike", "요청 폭주"),
    "AUTH_ANOMALY": ("Auth Anomaly", "인증 이상"),
    "TELEMETRY_INCONSISTENCY": ("Telemetry Issue", "센서/위치 데이터 불일치"),
    "SERVICE_DEGRADATION": ("Service Slowdown", "서비스 저하"),
    "MISSION_COMMAND_ANOMALY": ("Command Anomaly", "임무 명령 이상"),
    "LOG_NOISE": ("Log Noise", "로그 노이즈"),
    "RECOVERY_HEALTH_CHECK": ("Recovery Check", "방어 후 상태 점검"),
}

ACTION_LABELS = {
    "OBSERVE_ONLY": ("Observe", "모니터링만 수행"),
    "APPLY_RATE_LIMIT": ("Rate Limit", "요청량 제한"),
    "BLOCK_SUSPICIOUS_TOKEN": ("Block Token", "의심 세션 차단"),
    "ISOLATE_TELEMETRY_STREAM": ("Isolate Telemetry", "텔레메트리 격리"),
    "RESTART_SERVICE": ("Restart", "서비스 재시작"),
    "ROLLBACK_VERSION": ("Rollback", "안정 버전 복구"),
    "DEPLOY_DECOY": ("Deploy Decoy", "기만 환경 배치"),
    "ESCALATE_ALERT": ("Escalate", "사람에게 경고"),
}

MODE_LABELS = {
    "BALANCED": ("Balanced", "보안과 임무 지속성 균형"),
    "RECOVERY_FIRST": ("Recovery First", "복구 우선"),
    "DEFENSE_HARDENING": ("Defense Hardening", "방어 강화"),
    "RED_EXPLORATION": ("Red Exploration", "안전 시나리오 탐색"),
}


def api_get(path: str) -> dict[str, Any]:
    response = requests.get(f"{API_URL}{path}", timeout=5)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.post(f"{API_URL}{path}", json=payload or {}, timeout=10)
    response.raise_for_status()
    return response.json()


def fmt_score(value: Any, suffix: str = "") -> str:
    if value in (None, ""):
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:.1f}{suffix}"
    return str(value)


def event_name(event_type: str | None) -> str:
    label, description = EVENT_LABELS.get(str(event_type), (str(event_type), str(event_type)))
    return f"{label} - {description}"


def action_name(action_type: str | None) -> str:
    label, description = ACTION_LABELS.get(str(action_type), (str(action_type), str(action_type)))
    return f"{label} - {description}"


def health_badge(sla_score: float, mission_status: str, comm_status: str) -> tuple[str, str]:
    if mission_status != "ACTIVE":
        return "주의 필요", "임무 상태가 ACTIVE가 아닙니다."
    if sla_score < 85:
        return "복구 우선", "서비스 품질이 낮아 복구 액션이 우선입니다."
    if sla_score < 95 or comm_status not in {"NORMAL", "DEGRADED_BUT_CONTAINED"}:
        return "관찰 필요", "임무는 진행 중이지만 통신이나 품질 변화가 있습니다."
    return "안정", "임무와 서비스 품질이 안정적으로 유지되고 있습니다."


def trigger_scenario(name: str, intensity: float) -> None:
    st.session_state["last_result"] = api_post("/simulate/event", {"scenario": name, "intensity": intensity})


def run_selfplay_round() -> None:
    result = api_post("/selfplay/round")
    st.session_state["last_result"] = result
    st.session_state.setdefault("round_history", []).append(
        {
            "round": len(st.session_state.get("round_history", [])) + 1,
            "commander_mode": result.get("commander_mode"),
            "event_type": result.get("red_event", {}).get("event_type"),
            "blue_action": result.get("blue_decision", {}).get("selected_action"),
            "pre_sla": result.get("pre_sla"),
            "post_event_sla": result.get("post_event_sla"),
            "post_action_sla": result.get("post_action_sla"),
            "total_utility": result.get("score", {}).get("total_utility"),
        }
    )


def events_frame(events: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "time": str(event.get("timestamp", ""))[11:19],
                "event": event_name(event.get("event_type")),
                "severity": event.get("severity"),
                "latency_ms": event.get("latency_ms"),
                "mission": event.get("mission_status"),
                "sla_ok": event.get("sla_ok"),
                "description": event.get("description"),
            }
            for event in events
        ]
    )


def actions_frame(actions: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "time": str(action.get("timestamp", ""))[11:19],
                "blue_action": action_name(action.get("action_type")),
                "risk": action.get("risk_level"),
                "confidence": action.get("confidence"),
                "sla_impact": action.get("expected_sla_impact"),
                "reason": action.get("reason"),
            }
            for action in actions
        ]
    )


def score_frame(scores: list[dict[str, Any]]) -> pd.DataFrame:
    rows = list(reversed(scores))
    return pd.DataFrame(
        [
            {
                "round": index + 1,
                "sla_score": row.get("sla_score"),
                "red_success": row.get("red_success_score", row.get("attack_score")),
                "blue_defense": row.get("blue_defense_score", row.get("defense_score")),
                "utility": row.get("total_utility"),
            }
            for index, row in enumerate(rows)
        ]
    )


def scenario_frame(stats: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for row in stats.get("scenario_stats", []):
        attempts = max(1, int(row.get("attempts", 0)))
        rows.append(
            {
                "scenario": EVENT_LABELS.get(row.get("event_type"), (row.get("event_type"), ""))[0],
                "attempts": row.get("attempts"),
                "red_success_rate": round(int(row.get("red_success_count", 0)) / attempts, 3),
                "blue_success_rate": round(int(row.get("blue_success_count", 0)) / attempts, 3),
                "avg_sla_drop": row.get("avg_sla_drop"),
                "avg_recovery_delta": row.get("avg_recovery_delta"),
                "false_positives": row.get("false_positive_count"),
                "best_blue_action": row.get("most_effective_blue_action") or "-",
            }
        )
    return pd.DataFrame(rows)


def stress_summary_frame() -> pd.DataFrame:
    path = REPORTS_DIR / "stress_summary.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def latest_round_summary(result: dict[str, Any]) -> None:
    red_event = result.get("red_event", {})
    blue = result.get("blue_decision", {})
    score = result.get("score", {})
    mapping = result.get("knowledge_mapping", {})

    st.subheader("Latest Self-Play Round Summary")
    st.caption("Attack event -> Blue decision -> Action -> SLA recovery -> Score update")
    chain = st.columns(5)
    chain[0].metric("Attack Event", EVENT_LABELS.get(red_event.get("event_type"), ("-", ""))[0])
    chain[0].caption(f"severity {fmt_score(red_event.get('severity'))}")
    chain[1].metric("Blue Decision", blue.get("risk_level", "-"))
    chain[1].caption(f"risk {fmt_score(blue.get('risk_score'))}")
    chain[2].metric("Action", ACTION_LABELS.get(blue.get("selected_action"), ("-", ""))[0])
    chain[2].caption(mapping.get("blue_action", {}).get("category", "-"))
    chain[3].metric("SLA Recovery", fmt_score(result.get("recovery_delta"), " pts"))
    chain[3].caption(f"{fmt_score(result.get('pre_sla'))} -> {fmt_score(result.get('post_action_sla'))}")
    chain[4].metric("Utility", fmt_score(score.get("total_utility")))
    chain[4].caption(f"Red success {fmt_score(score.get('red_success_score'))}")

    reasoning = result.get("strategy_notes", {})
    st.info(
        "\n\n".join(
            [
                f"Commander: {reasoning.get('commander', '-')}",
                f"Red: {reasoning.get('red', '-')}",
                f"Blue: {reasoning.get('blue', '-')}",
            ]
        )
    )
    if mapping:
        map_cols = st.columns(2)
        map_cols[0].markdown("**ATT&CK-style event mapping**")
        map_cols[0].json(mapping.get("red_event", {}))
        map_cols[1].markdown("**D3FEND-style action mapping**")
        map_cols[1].json(mapping.get("blue_action", {}))


st.set_page_config(page_title="Aegis-Swarm v2", page_icon="A", layout="wide")
st.title("Aegis-Swarm v2 Judging Dashboard")
st.caption("안전한 로컬 Red-Blue self-play로 SLA 회복, 방어 판단, scenario memory, scoring evidence를 보여줍니다.")

try:
    health = api_get("/health")
    mission = api_get("/mission/status")
    vehicle = api_get("/vehicle/state")
    adapter = api_get("/adapter/status")
    logs = api_get("/logs/recent?limit=100")
    scenario_stats = api_get("/stats/scenarios")
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

overview = st.columns(6)
overview[0].metric("Current State", status_label)
overview[0].caption(status_text)
overview[1].metric("SLA", f"{sla_score:.1f}%")
overview[1].caption("임무 서비스 가용성")
overview[2].metric("Commander", MODE_LABELS.get(commander_mode, (commander_mode, ""))[0])
overview[2].caption(MODE_LABELS.get(commander_mode, ("", ""))[1])
overview[3].metric("Red Success", fmt_score(latest_score.get("red_success_score", latest_score.get("attack_score"))))
overview[3].caption("낮을수록 방어 우수")
overview[4].metric("Blue Defense", fmt_score(latest_score.get("blue_defense_score", latest_score.get("defense_score"))))
overview[4].caption("높을수록 대응 적합")
overview[5].metric("Utility", fmt_score(latest_score.get("total_utility")))
overview[5].caption("종합 점수")

st.divider()

button_cols = st.columns(5)
with button_cols[0]:
    if st.button("요청 폭주", use_container_width=True):
        trigger_scenario("TRAFFIC_SPIKE", 0.7)
with button_cols[1]:
    if st.button("인증 이상", use_container_width=True):
        trigger_scenario("AUTH_ANOMALY", 0.7)
with button_cols[2]:
    if st.button("센서 불일치", use_container_width=True):
        trigger_scenario("TELEMETRY_INCONSISTENCY", 0.8)
with button_cols[3]:
    if st.button("서비스 저하", use_container_width=True):
        trigger_scenario("SERVICE_DEGRADATION", 0.8)
with button_cols[4]:
    if st.button("AI Self-Play 1 Round", use_container_width=True, type="primary"):
        run_selfplay_round()

if "last_result" in st.session_state and "blue_decision" in st.session_state["last_result"]:
    latest_round_summary(st.session_state["last_result"])
elif latest_event or latest_action:
    st.subheader("Latest Observed State")
    state_cols = st.columns(3)
    state_cols[0].markdown(f"**Attack event:** {event_name(latest_event.get('event_type'))}")
    state_cols[1].markdown(f"**Blue action:** {action_name(latest_action.get('action_type'))}")
    state_cols[2].markdown(f"**Score update:** utility {fmt_score(latest_score.get('total_utility'))}")

st.divider()

score_history = score_frame(scores)
chart_cols = st.columns([1.2, 1])
with chart_cols[0]:
    st.subheader("SLA History")
    if not score_history.empty:
        st.line_chart(score_history.set_index("round")[["sla_score", "utility"]])
    else:
        st.info("아직 score history가 없습니다. Self-play round를 실행하세요.")

with chart_cols[1]:
    st.subheader("Before/After SLA Delta")
    result = st.session_state.get("last_result", {})
    if result and "post_action_sla" in result:
        delta_cols = st.columns(3)
        delta_cols[0].metric("Pre SLA", fmt_score(result.get("pre_sla"), "%"))
        delta_cols[1].metric("After Event", fmt_score(result.get("post_event_sla"), "%"))
        delta_cols[2].metric("After Action", fmt_score(result.get("post_action_sla"), "%"), fmt_score(result.get("recovery_delta")))
    else:
        st.caption("Self-play round 실행 후 pre -> event -> action SLA 변화가 표시됩니다.")

st.subheader("Commander Mode Timeline")
round_history = pd.DataFrame(st.session_state.get("round_history", []))
if not round_history.empty:
    st.dataframe(round_history[["round", "commander_mode", "event_type", "blue_action", "post_action_sla", "total_utility"]], use_container_width=True, hide_index=True)
else:
    st.caption(f"현재 Commander mode: {MODE_LABELS.get(commander_mode, (commander_mode, ''))[0]}. 새 round를 실행하면 timeline이 쌓입니다.")

st.divider()

scenario_df = scenario_frame(scenario_stats)
memory_cols = st.columns([1.2, 1])
with memory_cols[0]:
    st.subheader("Scenario Memory")
    stat_cols = st.columns(3)
    stat_cols[0].metric("Total Attempts", scenario_stats.get("total_attempts", 0))
    stat_cols[1].metric("Entropy", fmt_score(scenario_stats.get("scenario_entropy")))
    stat_cols[2].metric("Coverage", fmt_score(scenario_stats.get("coverage_score"), "%"))
    st.dataframe(scenario_df, use_container_width=True, hide_index=True)

with memory_cols[1]:
    st.subheader("Per-Scenario Success")
    if not scenario_df.empty:
        st.bar_chart(scenario_df.set_index("scenario")[["red_success_rate", "blue_success_rate"]])
    else:
        st.info("아직 scenario stats가 없습니다.")

st.divider()

st.subheader("Stress Scenario Evaluation")
stress_df = stress_summary_frame()
if not stress_df.empty:
    st.caption("Safe local event sequences only. No external target interaction.")
    st.dataframe(stress_df, use_container_width=True, hide_index=True)
else:
    st.caption("Run `python scripts/run_stress_scenarios.py` to generate stress scenario evidence.")

st.divider()

reason_cols = st.columns([1, 1])
with reason_cols[0]:
    st.subheader("Latest Blue Reasoning")
    if latest_action:
        st.markdown(f"**Action:** {action_name(latest_action.get('action_type'))}")
        st.write(latest_action.get("reason", "-"))
        st.caption(f"Risk: {latest_action.get('risk_level')} | Confidence: {fmt_score(latest_action.get('confidence'))} | SLA impact: {latest_action.get('expected_sla_impact')}")
    else:
        st.info("Blue decision이 아직 없습니다.")

with reason_cols[1]:
    st.subheader("Mission / Adapter")
    mission_cols = st.columns(3)
    mission_cols[0].metric("Vehicle", vehicle.get("vehicle_type", "-"))
    mission_cols[1].metric("Battery", f"{vehicle.get('battery', '-')}%")
    mission_cols[2].metric("Adapter", adapter.get("adapter_mode", "-"))
    st.caption(f"External access: {adapter.get('external_access')} | {adapter.get('description', '')}")

tab_events, tab_actions, tab_scores = st.tabs(["Event Logs", "Blue Decisions", "Scores"])
with tab_events:
    st.dataframe(events_frame(events), use_container_width=True, hide_index=True)
with tab_actions:
    st.dataframe(actions_frame(actions), use_container_width=True, hide_index=True)
with tab_scores:
    st.dataframe(scores, use_container_width=True, hide_index=True)
