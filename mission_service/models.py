from __future__ import annotations

from pydantic import BaseModel, Field

from core.event_schema import now_iso


class Position(BaseModel):
    x: float = 12.4
    y: float = 7.8


class MissionState(BaseModel):
    mission_id: str = "M-001"
    vehicle_type: str = "UGV"
    mission_status: str = "ACTIVE"
    position: Position = Field(default_factory=Position)
    battery: int = 76
    comm_status: str = "NORMAL"
    sla_ok: bool = True
    last_updated: str = Field(default_factory=now_iso)


class HealthResponse(BaseModel):
    status: str
    sla_score: float
    mission_status: MissionState
