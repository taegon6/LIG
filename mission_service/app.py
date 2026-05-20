from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Query

from adapters import get_adapter
from agents.blue_agent import BlueAgent
from agents.commander_agent import CommanderAgent
from agents.red_agent import RedAgent
from core.action_registry import apply_action_to_state, build_action_record
from core.event_schema import BlueDecision, SimulateEventRequest, SimulatedEvent, VehicleCommandRequest, now_iso
from core.scoring import score_round
from core.sla import calculate_sla
from mission_service import db
from mission_service.models import HealthResponse, MissionState
from simulator.event_generator import generate_event

app = FastAPI(
    title="Aegis-Swarm Mission Service",
    description="Safe local Red-Blue self-play simulation API. No real offensive cyber actions are implemented.",
    version="0.1.0",
)

db.init_db()
MISSION_STATE = MissionState()
COMMANDER_MODE = "BALANCED"


def mission_state_dict() -> dict[str, Any]:
    return MISSION_STATE.model_dump()


def active_adapter():
    return get_adapter(mission_state_dict)


def current_sla(limit: int = 50) -> float:
    return calculate_sla(db.recent_events(limit))


def build_dah_scores(score: dict[str, Any] | None = None) -> dict[str, Any]:
    latest = score or (db.recent_scores(1)[0] if db.recent_scores(1) else {})
    return {
        "attack_score": latest.get("attack_score", 0.0),
        "defense_score": latest.get("defense_score", 0.0),
        "sla_score": latest.get("sla_score", current_sla()),
        "total_utility": latest.get("total_utility", 0.0),
        "evaluation_focus": "DAH-style attack, defense, and availability/SLA balance",
    }


def commander_strategy_note(mode: str, sla_score: float) -> str:
    if mode == "RECOVERY_FIRST":
        return f"SLA is {sla_score:.2f}; commander prioritizes recovery before aggressive blocking."
    if mode == "DEFENSE_HARDENING":
        return "Recent defense quality is weak; commander asks agents to harden response."
    if mode == "RED_EXPLORATION":
        return "Recent red pressure is low; commander allows broader safe scenario exploration."
    return "SLA and score history are stable; commander keeps a balanced self-play mode."


def red_strategy_note(mode: str, sla_score: float, event_type: str) -> str:
    if mode == "RECOVERY_FIRST":
        return f"Red generated lower-intensity {event_type} because SLA recovery is the priority."
    if mode == "DEFENSE_HARDENING":
        return f"Red generated a stronger safe {event_type} to test Blue hardening."
    if mode == "RED_EXPLORATION":
        return f"Red varied the safe scenario set with {event_type} to broaden coverage."
    return f"Red generated medium-intensity safe {event_type} for balanced self-play."


def blue_strategy_note(decision: BlueDecision, sla_score: float) -> str:
    return (
        f"Blue selected {decision.selected_action} at {decision.risk_level} risk "
        f"with SLA {sla_score:.2f}; expected SLA impact is {decision.expected_sla_impact}."
    )


def update_mission_state_from_event(event: dict[str, Any]) -> None:
    global MISSION_STATE
    state = MISSION_STATE.model_copy(deep=True)
    state.mission_status = str(event.get("mission_status", state.mission_status))
    state.sla_ok = bool(event.get("sla_ok", state.sla_ok))
    state.last_updated = now_iso()
    if event.get("event_type") == "TELEMETRY_INCONSISTENCY":
        state.comm_status = "TELEMETRY_NOISY"
    elif event.get("event_type") == "SERVICE_DEGRADATION":
        state.comm_status = "DEGRADED"
    elif event.get("event_type") == "TRAFFIC_SPIKE":
        state.comm_status = "CONGESTED"
    elif event.get("event_type") == "NORMAL":
        state.comm_status = "NORMAL"
    MISSION_STATE = state


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", sla_score=current_sla(), mission_status=MISSION_STATE)


@app.get("/adapter/status")
def adapter_status() -> dict[str, Any]:
    return active_adapter().adapter_status()


@app.get("/mission/status")
def mission_status() -> dict[str, Any]:
    return {"commander_mode": COMMANDER_MODE, **MISSION_STATE.model_dump()}


@app.get("/vehicle/state")
def vehicle_state() -> dict[str, Any]:
    return MISSION_STATE.model_dump()


@app.post("/vehicle/command")
def vehicle_command(command: VehicleCommandRequest) -> dict[str, Any]:
    global MISSION_STATE
    state = MISSION_STATE.model_copy(deep=True)
    if command.target_x is not None and command.target_y is not None:
        state.position.x = command.target_x
        state.position.y = command.target_y
    state.last_updated = now_iso()
    MISSION_STATE = state
    event = SimulatedEvent(
        source="mission_service",
        event_type="MISSION_COMMAND_ANOMALY" if "unsafe" in command.command.lower() else "NORMAL",
        severity=0.45 if "unsafe" in command.command.lower() else 0.05,
        latency_ms=140,
        status_code=200,
        mission_status=state.mission_status,
        sla_ok=state.sla_ok,
        description=f"Safe simulated command accepted: {command.command}",
    )
    saved = db.insert_event(event.model_dump())
    return {"accepted": True, "executed_real_command": False, "event": saved, "vehicle_state": state.model_dump()}


@app.get("/telemetry")
def telemetry() -> dict[str, Any]:
    return {
        "mission_id": MISSION_STATE.mission_id,
        "position": MISSION_STATE.position.model_dump(),
        "battery": MISSION_STATE.battery,
        "comm_status": MISSION_STATE.comm_status,
        "latency_ms": db.recent_events(1)[0]["latency_ms"] if db.recent_events(1) else 120,
        "timestamp": now_iso(),
    }


@app.get("/logs/recent")
def logs_recent(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    return {
        "events": db.recent_events(limit),
        "actions": db.recent_actions(limit),
        "scores": db.recent_scores(limit),
    }


@app.post("/simulate/event")
def simulate_event(request: SimulateEventRequest) -> dict[str, Any]:
    event = generate_event(request.scenario, request.intensity)
    update_mission_state_from_event(event.model_dump())
    saved = db.insert_event(event.model_dump())
    return {"event": saved, "sla_score": current_sla(), "mission_state": MISSION_STATE.model_dump()}


@app.post("/agent/blue/decide", response_model=BlueDecision)
def blue_decide() -> BlueDecision:
    events = db.recent_events(50)
    decision = BlueAgent().decide(events, current_sla())
    action_record = build_action_record(decision)
    db.insert_action(action_record.model_dump())
    return decision


@app.post("/selfplay/round")
def selfplay_round() -> dict[str, Any]:
    global MISSION_STATE, COMMANDER_MODE
    adapter = active_adapter()
    previous_sla = current_sla()
    recent_scores = db.recent_scores(10)
    recent_actions = db.recent_actions(10)

    commander = CommanderAgent()
    COMMANDER_MODE = commander.decide_mode(previous_sla, recent_scores, recent_actions)

    red_event = RedAgent().generate(COMMANDER_MODE, recent_scores, previous_sla)
    update_mission_state_from_event(red_event.model_dump())
    saved_event = db.insert_event(red_event.model_dump())

    events = db.recent_events(50)
    sla_after_event = current_sla()
    blue_decision = BlueAgent().decide(events, sla_after_event)
    action_record = db.insert_action(build_action_record(blue_decision).model_dump())
    adapter_action_result = adapter.submit_blue_action(blue_decision.model_dump())
    action_result = apply_action_to_state(blue_decision, MISSION_STATE.model_dump())
    MISSION_STATE = MissionState(**action_result["mission_state"])

    score = score_round(saved_event, blue_decision.model_dump(), current_sla(), previous_sla_score=previous_sla)
    saved_score = db.insert_score({"timestamp": now_iso(), **score})
    dah_scores = build_dah_scores(saved_score)
    strategy_notes = {
        "commander": commander_strategy_note(COMMANDER_MODE, previous_sla),
        "red": red_strategy_note(COMMANDER_MODE, previous_sla, saved_event["event_type"]),
        "blue": blue_strategy_note(blue_decision, sla_after_event),
        "adapter": adapter_action_result["description"],
    }

    return {
        "adapter_mode": adapter.adapter_status()["adapter_mode"],
        "commander_mode": COMMANDER_MODE,
        "red_event": saved_event,
        "blue_decision": blue_decision.model_dump(),
        "action_result": action_result,
        "adapter_action_result": adapter_action_result,
        "action_log": action_record,
        "sla_score": saved_score["sla_score"],
        "dah_scores": dah_scores,
        "strategy_notes": strategy_notes,
        "score": saved_score,
        "mission_state": MISSION_STATE.model_dump(),
    }
