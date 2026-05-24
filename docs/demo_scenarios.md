# Aegis-Swarm v2 Demo Scenarios

## Demo Goal

Show the judging chain:

```text
Attack event -> Blue decision -> Action -> SLA recovery -> Score update
```

## Scenario 1: Traffic Spike

- Red event: `TRAFFIC_SPIKE`
- Expected Blue action: `APPLY_RATE_LIMIT`
- What to show: SLA remains stable or recovers after rate limiting.
- Dashboard areas: latest round summary, before/after SLA delta, SLA history.

## Scenario 2: Auth Anomaly

- Red event: `AUTH_ANOMALY`
- Expected Blue action: `BLOCK_SUSPICIOUS_TOKEN`
- What to show: Blue containment choice and D3FEND mapping.
- Dashboard areas: latest Blue reasoning, D3FEND action mapping.

## Scenario 3: Telemetry Inconsistency

- Red event: `TELEMETRY_INCONSISTENCY`
- Expected Blue action: `ISOLATE_TELEMETRY_STREAM`
- What to show: mission stays active while telemetry stream is contained.
- Dashboard areas: mission/adapter card, event logs, Blue decision logs.

## Scenario 4: Service Degradation

- Red event: `SERVICE_DEGRADATION`
- Expected Blue action: `RESTART_SERVICE` or `ROLLBACK_VERSION`
- What to show: recovery-first behavior and measurable `recovery_delta`.
- Dashboard areas: before/after SLA delta, recovery score, Commander mode.

## Scenario 5: Adaptive Memory

Run several self-play rounds, then open scenario memory:

- total attempts
- entropy
- coverage score
- red success rate
- blue success rate
- most effective Blue action

This demonstrates that the agents are not only reacting to a single event, but also learning from local scenario outcomes.
