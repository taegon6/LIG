# Official Red Adapter Plan

Aegis-Swarm v2 prepares for DAH authorized attack-side integration without
adding real attack code to the public repository. The public codebase contains
only safe local planning, local mock execution, and inert adapter templates.

## Public Repository Boundary

The public repository has no real attack code. It does not include exploit
logic, probing logic, brute force behavior, credential behavior, malware
behavior, persistence behavior, shell attack behavior, or outside target
interaction.

## Private Adapter Requirement

Real DAH integration must use a private adapter maintained outside the public
repository. That adapter must follow competition rules and submit only official
allowed actions. Secrets, runtime addresses, credentials, and competition
configuration must never be committed.

## Reused Red Objective Layer

The same Red objective layer can be reused in an official runtime:

- `SLA_DROP`
- `BLUE_MISMATCH`
- `CONFUSION`
- `RECOVERY_PRESSURE`
- `COVERAGE`

These objectives map to abstract allowed action names in `core/red_action_schema.py`.
The public `RedActionPlan` contains no field for executable instructions or
private runtime details.

## Public Mock Runtime

`adapters/mock_official_runtime.py` is local-only. It simulates allowed action
submission and feedback with in-memory data so the team can test planning flow
without contacting any outside system.

## Review Checklist

- Use only official allowed actions.
- Keep secrets and runtime addresses outside Git.
- Review logs before submission packaging.
- Keep public examples inert.
- Validate with `pytest` and `scripts/goal_runner.py`.
