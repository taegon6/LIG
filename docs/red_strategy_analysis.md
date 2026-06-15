# Red Strategy Analysis

Red strategy in Aegis-Swarm v2 is an explainable local simulation policy. It is
not an offensive automation system. The goal is to produce safe scenario
pressure that helps judges inspect whether Blue defense and Commander recovery
logic are robust.

## Current Strategy Loop

1. Commander selects `BALANCED`, `RECOVERY_FIRST`, `DEFENSE_HARDENING`, or `RED_EXPLORATION`.
2. Red selects one safe objective: `SLA_DROP`, `BLUE_MISMATCH`, `CONFUSION`, `RECOVERY_PRESSURE`, or `COVERAGE`.
3. Red generates one approved local event with bounded intensity.
4. Blue responds with a simulated defensive action.
5. Scoring records Red success, Blue defense, SLA preservation, recovery, false positives, and utility.

## Evidence Signals

- `red_success_score`: round-level pressure score from the v2 scoring model.
- `avg_sla_drop`: scenario memory signal for availability pressure.
- `false_positive_count`: confusion signal for benign or noisy events.
- `coverage_score`: whether all safe event types have been exercised.
- `red_strategy_stats`: objective-level memory for Red success, SLA pressure, mismatch rate, recovery, and utility impact.
- Hard-mode failure cases: repeated pressure can expose recovery limits even when Blue action selection is correct.

## What Red Does

Red selects a safe objective, chooses one approved local event type, assigns a
bounded intensity, and emits strategy metadata. The event is local data only.
The latest self-play API returns `red_objective`, `red_strategy_reason`,
`expected_effect`, `red_strategy_stat`, and `red_success_score`.

## What Red Does Not Do

Red does not run exploits, probes, credential behavior, malware, persistence,
lateral movement, shell behavior, or outside target interaction. It is an
evaluation agent for local defense strategy, not an attack tool.

## Why This Helps DAH Readiness

The v2 Red side now has explicit objectives rather than random scenario labels
only. This improves the Attack Scenario Design portion of the preliminary
rubric while staying public-safe. It also makes the demo easier to explain:
judges can see not just what event happened, but why Red selected it and what
effect the simulator expected.

## Most Effective Objectives

The current evidence is generated locally. In normal self-play, objective-level
memory is available from `GET /stats/red` and `reports/round_metrics.csv`. In
hard mode, repeated `SERVICE_DEGRADATION`, `TELEMETRY_INCONSISTENCY`, and
`TRAFFIC_SPIKE` pressure tends to produce the strongest Red-side evidence because
it can reduce rolling SLA or cause partial recovery. This is documented in
`docs/failure_analysis.md`.

## How Red Trains And Evaluates Blue

Red creates pressure across five objective families. Blue is then evaluated on
whether it chooses the correct action, avoids false positives, restores SLA, and
keeps total utility high. This makes Red useful for both curriculum generation
and final evidence generation.

## Official Competition Integration

Official attack-side integration must use a private adapter only. The public
repository keeps the adapter example inert so no private runtime detail or real
action logic is published.

## Next Improvements

- Add more sequence-level objective selection for hard mode.
- Track objective-level success rates separately from event-type stats.
- Tune Commander mode transitions based on objective-specific failures.
- Connect an official runtime through a private adapter when allowed.
