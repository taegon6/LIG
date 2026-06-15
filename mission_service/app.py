from __future__ import annotations

from typing import Any

from fastapi import Body, FastAPI, Query

from adapters import get_adapter
from adapters.mock_official_runtime import MockOfficialRuntime
from agents.blue_agent import BlueAgent
from agents.commander_agent import CommanderAgent
from agents.red_agent import RedAgent
from agents.red_objectives import RED_OBJECTIVES
from core.action_registry import apply_action_to_state, build_action_record
from core.event_schema import BlueDecision, SimulateEventRequest, SimulatedEvent, VehicleCommandRequest, now_iso
from core.knowledge_mapping import round_knowledge_mapping
from core.red_action_schema import RedActionPlan, RedActionResult
from core.scoring import action_matches_event, score_round
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
    action = decision.selected_action
    event_type = str(event.get("event_type", "NORMAL"))
    base_latency = int(event.get("latency_ms", 120))
    latency_delta = int(effect.get("latency_delta", 0))
    latency_ms = max(90, min(900, base_latency + latency_delta))
    status_code = 200 if mission_state.mission_status == "ACTIVE" else 503
    mission_status = mission_state.mission_status
    sla_ok_state = bool(mission_state.sla_ok)

    if action == "RESTART_SERVICE":
        latency_ms = 150
        status_code = 200
        mission_status = "ACTIVE"
        sla_ok_state = True
    elif action == "ROLLBACK_VERSION":
        latency_ms = 170
        status_code = 200
        mission_status = "ACTIVE"
        sla_ok_state = True
    elif action == "APPLY_RATE_LIMIT" and event_type == "TRAFFIC_SPIKE":
        latency_ms = min(280, max(120, base_latency - 220))
        status_code = 200
        mission_status = "ACTIVE"
        sla_ok_state = True
    elif action == "ISOLATE_TELEMETRY_STREAM" and event_type == "TELEMETRY_INCONSISTENCY":
        latency_ms = min(300, max(120, base_latency - 120))
        status_code = 200
        mission_status = "ACTIVE"
        sla_ok_state = True

    sla_ok = (
        mission_status == "ACTIVE"
        and status_code < 500
        and latency_ms < 500
        and sla_ok_state
    )
    return SimulatedEvent(
        source="action_registry",
        event_type="RECOVERY_HEALTH_CHECK",
        severity=0.0,
        latency_ms=latency_ms,
        status_code=status_code,
        mission_status=mission_status,
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


@app.get("/stats/red")
def stats_red() -> dict[str, Any]:
    scenario_summary = db.scenario_stats_summary()
    strategy_summary = db.red_strategy_stats_summary()
    latest_scores = db.recent_scores(20)
    red_scores = [float(score.get("red_success_score", score.get("attack_score", 0.0))) for score in latest_scores]
    average_red_success = round(sum(red_scores) / len(red_scores), 2) if red_scores else 0.0
    objective_catalog = {
        name: {
            "safe_events": objective.safe_events,
            "strategy_reason": objective.strategy_reason,
            "expected_effect": objective.expected_effect,
        }
        for name, objective in RED_OBJECTIVES.items()
    }
    return {
        "local_only": True,
        "external_access": False,
        "red_objectives": objective_catalog,
        "safe_event_types": sorted({event for objective in RED_OBJECTIVES.values() for event in objective.safe_events}),
        "average_recent_red_success_score": average_red_success,
        "red_strategy_stats": strategy_summary["red_strategy_stats"],
        "total_objective_attempts": strategy_summary["total_objective_attempts"],
        "most_effective_objective": strategy_summary["most_effective_objective"],
        "scenario_stats": scenario_summary["scenario_stats"],
        "coverage_score": scenario_summary["coverage_score"],
        "scenario_entropy": scenario_summary["scenario_entropy"],
        "total_attempts": scenario_summary["total_attempts"],
    }


def red_planning_context(context: dict[str, Any] | None = None) -> dict[str, Any]:
    provided = dict(context or {})
    provided.setdefault("commander_mode", COMMANDER_MODE)
    provided.setdefault("current_sla", current_sla())
    provided.setdefault("recent_scores", db.recent_scores(10))
    provided.setdefault("scenario_stats", db.scenario_stats())
    provided.setdefault("red_strategy_stats", db.red_strategy_stats())
    return provided


@app.post("/red/plan")
def red_plan(context: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    runtime = MockOfficialRuntime()
    planning_context = red_planning_context(context)
    planning_context.setdefault("allowed_actions", runtime.list_allowed_red_actions())
    plan = RedAgent().plan_official_red_action(planning_context)
    return {
        "red_objective": plan.red_objective,
        "allowed_action_type": plan.allowed_action_type,
        "strategy_reason": plan.strategy_reason,
        "expected_effect": plan.expected_effect,
        "estimated_score_effect": plan.estimated_score_effect,
        "safety_status": plan.safety_status,
    }


@app.post("/red/mock/execute", response_model=RedActionResult)
def red_mock_execute(context: dict[str, Any] | None = Body(default=None)) -> RedActionResult:
    runtime = MockOfficialRuntime()
    planning_context = red_planning_context(context)
    planning_context["allowed_actions"] = runtime.list_allowed_red_actions()
    plan: RedActionPlan = RedAgent().plan_official_red_action(planning_context)
    return runtime.submit_allowed_red_action(plan)


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
    red_plan = RedAgent().generate_plan(
        COMMANDER_MODE,
        recent_scores,
        pre_sla,
        scenario_stats_before,
        db.red_strategy_stats(),
    )
    red_event = red_plan.event
    update_mission_state_from_event(red_event.model_dump())
    saved_event = db.insert_event(red_event.model_dump())

    events = db.recent_events(50)
    post_event_sla = calculate_sla([saved_event])
    blue_decision = BlueAgent(db.scenario_stats()).decide(events, post_event_sla)
    action_record = db.insert_action(build_action_record(blue_decision).model_dump())
    adapter_action_result = adapter.submit_blue_action(blue_decision.model_dump())
    action_result = apply_action_to_state(blue_decision, MISSION_STATE.model_dump())
    MISSION_STATE = MissionState(**action_result["mission_state"])

    recovery_event = build_post_action_health_event(saved_event, blue_decision, MISSION_STATE, action_result)
    saved_recovery_event = db.insert_event(recovery_event.model_dump())
    post_action_sla = calculate_sla([saved_recovery_event])
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
    blue_mismatch = not action_matches_event(saved_event, blue_decision.model_dump())
    red_strategy_stat = db.update_red_strategy_stats(
        objective=red_plan.red_objective,
        event_type=saved_event["event_type"],
        score=saved_score,
        sla_drop=round(pre_sla - post_event_sla, 2),
        blue_mismatch=blue_mismatch,
        recovery_delta=recovery_delta,
    )
    dah_scores = build_dah_scores(saved_score)
    strategy_notes = {
        "commander": commander_strategy_note(COMMANDER_MODE, pre_sla),
        "red": red_plan.strategy_reason,
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
        "red_objective": red_plan.red_objective,
        "red_strategy_reason": red_plan.strategy_reason,
        "expected_effect": red_plan.expected_effect,
        "blue_mismatch": blue_mismatch,
        "red_success_score": saved_score["red_success_score"],
        "red_strategy": red_plan.metadata(),
        "red_strategy_stat": red_strategy_stat,
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
