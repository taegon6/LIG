# Private Adapter Design

The public repository includes a local simulator adapter and a competition
stub. Official DAH runtime integration should be implemented as a private
adapter outside the public submission branch.

## Interface

A private adapter should map official runtime data into the same public
interface:

- `get_mission_state()`
- `get_recent_events(limit)`
- `submit_blue_action(action)`
- `get_latest_scores()`
- `adapter_status()`

## Public Repository Rule

The public repository must not contain private runtime details, credentials,
competition secrets, or real target information. The example file
`adapters/private_red_adapter.py.example` is intentionally inert.

## Expected Mapping

| Aegis-Swarm concept | Private adapter responsibility |
| --- | --- |
| Mission state | Convert official state into the local `MissionState` shape |
| Recent events | Convert official telemetry into safe internal event records |
| Blue action | Submit only competition-approved defensive actions |
| Scores | Normalize official scoring into local report fields |
| Status | Report readiness without exposing private configuration |

## Safety Review Before Use

Before official use, the private adapter should be reviewed for rule compliance,
secret handling, logging boundaries, and reproducibility. That implementation
should remain outside this public repo unless the competition explicitly allows
publication.
