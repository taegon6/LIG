# Aegis-Swarm v2 Architecture

## 개요

Aegis-Swarm v2는 안전한 로컬 self-play 환경에서 Red anomaly, Blue defense, Commander operation mode, SLA recovery, scoring evidence를 연결한다. 모든 이벤트는 SQLite에 저장되는 simulated event이며 외부 target과 상호작용하지 않는다.

## Runtime Flow

```text
Dashboard or API
  -> POST /selfplay/round
  -> Commander Agent selects mode
  -> Red Agent selects safe local scenario
  -> event inserted into SQLite
  -> Blue Agent calculates risk and selects action
  -> Action Registry applies local state transition
  -> RECOVERY_HEALTH_CHECK inserted
  -> SLA and v2 scores recalculated
  -> scenario_stats updated
```

## Agents

### Red Agent

Red Agent uses safe local event types only. It uses epsilon-greedy scenario selection over `scenario_stats`: mostly exploit scenarios with higher red success rate, sometimes explore other safe scenarios. If SLA is low or Commander mode is `RECOVERY_FIRST`, intensity is lowered.

### Blue Agent

Blue Agent is split into modular policies:

- triage policy: component score and risk level
- containment policy: rate limit, token block, telemetry isolation
- recovery policy: restart or rollback
- deception policy: decoy or escalation
- SLA governor: SLA-aware guardrails and recent failure awareness

### Commander Agent

Commander Agent balances operational safety:

- `BALANCED`
- `RECOVERY_FIRST`
- `DEFENSE_HARDENING`
- `RED_EXPLORATION`

## Persistence

SQLite tables:

- `events`
- `actions`
- `scores`
- `scenario_stats`

`scenario_stats` is the adaptive memory layer used by both Red and Blue.

## Adapter Boundary

Competition integration must happen through a private adapter. The public repository must not contain NDA data, private API URLs, credentials, tokens, or competition-only logs.
