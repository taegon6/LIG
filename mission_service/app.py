from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Query

from adapters import get_adapter
from agents.blue_agent import BlueAgent
from agents.commander_agent import CommanderAgent
from agents.red_agent import RedAgent
from core.action_registry import apply_action_to_state, build_action_record
from core.event_schema import BlueDecision, SimulateEventRequest, SimulatedEvent, VehicleCommandRequest, now_iso
from core.knowledge_mapping import round_knowledge_mapping
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
        "red_success_score": latest.get("red_success_score", latest.get("attack_score", 0.0)),
        "blue_defense_score": latest.get("blue_defense_score", latest.get("defense_score", 0.0)),
        "sla_preservation_score": latest.get("sla_preservation_score", latest.get("sla_score", current_sla())),
        "attack_score": latest.get("attack_score", latest.get("red_success_score", 0.0)),
        "defense_score": latest.get("defense_score", latest.get("blue_defense_score", 0.0)),
        "sla_score": latest.get("sla_score", current_sla()),
        "recovery_score": latest.get("recovery_score", 0.0),
        "action_cost": latest.get("action_cost", 0.0),
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


def build_post_action_health_event(
    event: dict[str, Any],
    decision: BlueDecision,
    mission_state: MissionState,
    action_result: dict[str, Any],
) -> SimulatedEvent:
    effect = action_result.get("effect", {})
    latency_delta = int(effect.get("latency_delta", 0))
    latency_ms = max(90, min(900, int(event.get("latency_ms", 120)) + latency_delta))
    status_code = 200 if mission_state.mission_status == "ACTIVE" else 503
    sla_ok = (
        mission_state.mission_status == "ACTIVE"
        and status_code < 500
        and latency_ms < 500
        and bool(mission_state.sla_ok)
    )
    return SimulatedEvent(
        source="action_registry",
        event_type="RECOVERY_HEALTH_CHECK",
        severity=0.0,
        latency_ms=latency_ms,
        status_code=status_code,
        mission_status=mission_state.mission_status,
        sla_ok=sla_ok,
        description=(
            "Post-action simulated health check after "
            f"{decision.selected_action}: {'SLA preserved' if sla_ok else 'recovery incomplete'}."
        ),
    )


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


@app.get("/stats/scenarios")
def stats_scenarios() -> dict[str, Any]:
    return db.scenario_stats_summary()


@app.post("/simulate/event")
def simulate_event(request: SimulateEventRequest) -> dict[str, Any]:
    event = generate_event(request.scenario, request.intensity)
    update_mission_state_from_event(event.model_dump())
    saved = db.insert_event(event.model_dump())
    return {"event": saved, "sla_score": current_sla(), "mission_state": MISSION_STATE.model_dump()}


@app.post("/agent/blue/decide", response_model=BlueDecision)
def blue_decide() -> BlueDecision:
    events = db.recent_events(50)
    decision = BlueAgent(db.scenario_stats()).decide(events, current_sla())
    action_record = build_action_record(decision)
    db.insert_action(action_record.model_dump())
    return decision


@app.post("/selfplay/round")
def selfplay_round() -> dict[str, Any]:
    global MISSION_STATE, COMMANDER_MODE
    adapter = active_adapter()
    pre_sla = current_sla()
    recent_scores = db.recent_scores(10)
    recent_actions = db.recent_actions(10)

    commander = CommanderAgent()
    COMMANDER_MODE = commander.decide_mode(pre_sla, recent_scores, recent_actions)

    scenario_stats_before = db.scenario_stats()
    red_event = RedAgent().generate(COMMANDER_MODE, recent_scores, pre_sla, scenario_stats_before)
    update_mission_state_from_event(red_event.model_dump())
    saved_event = db.insert_event(red_event.model_dump())

    events = db.recent_events(50)
    post_event_sla = current_sla()
    blue_decision = BlueAgent(db.scenario_stats()).decide(events, post_event_sla)
    action_record = db.insert_action(build_action_record(blue_decision).model_dump())
    adapter_action_result = adapter.submit_blue_action(blue_decision.model_dump())
    action_result = apply_action_to_state(blue_decision, MISSION_STATE.model_dump())
    MISSION_STATE = MissionState(**action_result["mission_state"])

    recovery_event = build_post_action_health_event(saved_event, blue_decision, MISSION_STATE, action_result)
    saved_recovery_event = db.insert_event(recovery_event.model_dump())
    post_action_sla = current_sla()
    sla_delta = round(post_action_sla - pre_sla, 2)
    recovery_delta = round(post_action_sla - post_event_sla, 2)

    score = score_round(
        saved_event,
        blue_decision.model_dump(),
        post_action_sla,
        previous_sla_score=pre_sla,
        post_event_sla=post_event_sla,
        post_action_sla=post_action_sla,
    )
    saved_score = db.insert_score({"timestamp": now_iso(), **score})
    scenario_stat = db.update_scenario_stats(
        event_type=saved_event["event_type"],
        blue_action=blue_decision.selected_action,
        score=saved_score,
        sla_drop=round(pre_sla - post_event_sla, 2),
        recovery_delta=recovery_delta,
    )
    dah_scores = build_dah_scores(saved_score)
    strategy_notes = {
        "commander": commander_strategy_note(COMMANDER_MODE, pre_sla),
        "red": red_strategy_note(COMMANDER_MODE, pre_sla, saved_event["event_type"]),
        "blue": blue_strategy_note(blue_decision, post_event_sla),
        "adapter": adapter_action_result["description"],
    }
    knowledge_mapping = round_knowledge_mapping(saved_event["event_type"], blue_decision.selected_action)

    return {
        "adapter_mode": adapter.adapter_status()["adapter_mode"],
        "commander_mode": COMMANDER_MODE,
        "pre_sla": pre_sla,
        "post_event_sla": post_event_sla,
        "post_action_sla": post_action_sla,
        "sla_delta": sla_delta,
        "recovery_delta": recovery_delta,
        "red_event": saved_event,
        "recovery_event": saved_recovery_event,
        "blue_decision": blue_decision.model_dump(),
        "action_result": action_result,
        "adapter_action_result": adapter_action_result,
        "action_log": action_record,
        "sla_score": saved_score["sla_score"],
        "dah_scores": dah_scores,
        "strategy_notes": strategy_notes,
        "knowledge_mapping": knowledge_mapping,
        "score": saved_score,
        "scenario_stat": scenario_stat,
        "mission_state": MISSION_STATE.model_dump(),
    }
