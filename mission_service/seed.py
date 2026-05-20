from __future__ import annotations

from core.event_schema import SimulatedEvent
from mission_service.db import init_db, insert_event, recent_events


def seed_if_empty() -> None:
    init_db()
    if recent_events(1):
        return
    insert_event(SimulatedEvent(description="Initial healthy mission heartbeat").model_dump())


if __name__ == "__main__":
    seed_if_empty()
