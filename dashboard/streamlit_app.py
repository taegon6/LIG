from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


API_URL = os.getenv("AEGIS_API_URL", "http://localhost:8000").rstrip("/")


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


st.set_page_config(page_title="Aegis-Swarm", page_icon="A", layout="wide")
st.title("Aegis-Swarm")
st.caption("Safe local Red-Blue self-play simulation for defense-style mission operations")

try:
    health = api_get("/health")
    mission = api_get("/mission/status")
    vehicle = api_get("/vehicle/state")
    logs = api_get("/logs/recent?limit=25")
except requests.RequestException as exc:
    st.error(f"API 연결 실패: {exc}")
    st.stop()

latest_score = logs["scores"][0] if logs["scores"] else {}
commander_mode = mission.get("commander_mode", "BALANCED")

cols = st.columns(5)
cols[0].metric("Current SLA", f"{health['sla_score']:.2f}%")
cols[1].metric("Commander Mode", commander_mode)
cols[2].metric("Attack Score", latest_score.get("attack_score", "-"))
cols[3].metric("Defense Score", latest_score.get("defense_score", "-"))
cols[4].metric("Utility", latest_score.get("total_utility", "-"))

left, right = st.columns([1, 1])
with left:
    st.subheader("Mission Status")
    st.json(health["mission_status"])

with right:
    st.subheader("Vehicle State")
    st.json(vehicle)

st.subheader("Simulated Scenarios")
scenario_cols = st.columns(5)
with scenario_cols[0]:
    if st.button("Traffic Spike", use_container_width=True):
        trigger_scenario("TRAFFIC_SPIKE", 0.7)
with scenario_cols[1]:
    if st.button("Auth Anomaly", use_container_width=True):
        trigger_scenario("AUTH_ANOMALY", 0.7)
with scenario_cols[2]:
    if st.button("Telemetry Inconsistency", use_container_width=True):
        trigger_scenario("TELEMETRY_INCONSISTENCY", 0.8)
with scenario_cols[3]:
    if st.button("Service Degradation", use_container_width=True):
        trigger_scenario("SERVICE_DEGRADATION", 0.8)
with scenario_cols[4]:
    if st.button("Run Self-Play Round", use_container_width=True):
        st.session_state["last_result"] = api_post("/selfplay/round")

if "last_result" in st.session_state:
    st.subheader("Latest Result")
    st.json(st.session_state["last_result"])

tab_events, tab_actions, tab_scores = st.tabs(["Recent Events", "Blue Decisions", "Scores"])
with tab_events:
    st.dataframe(logs["events"], use_container_width=True, hide_index=True)
with tab_actions:
    st.dataframe(logs["actions"], use_container_width=True, hide_index=True)
with tab_scores:
    st.dataframe(logs["scores"], use_container_width=True, hide_index=True)
