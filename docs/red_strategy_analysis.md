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
- Hard-mode failure cases: repeated pressure can expose recovery limits even when Blue action selection is correct.

## Why This Helps DAH Readiness

The v2 Red side now has explicit objectives rather than random scenario labels
only. This improves the Attack Scenario Design portion of the preliminary
rubric while staying public-safe. It also makes the demo easier to explain:
judges can see not just what event happened, but why Red selected it and what
effect the simulator expected.

## Next Improvements

- Add more sequence-level objective selection for hard mode.
- Track objective-level success rates separately from event-type stats.
- Tune Commander mode transitions based on objective-specific failures.
- Connect an official runtime through a private adapter when allowed.
