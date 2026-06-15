# Judge Q&A

## Is this a real attack system?

No. Aegis-Swarm v2 is a local simulator. Red events are synthetic rows and
Pydantic objects inside the application.

## What is the strongest technical claim?

The project demonstrates a safe Red/Blue/Commander self-play loop with
measurable SLA-aware defense, scenario memory, hard-mode failure evidence, and
repeatable reports.

## What changed in v2?

v2 adds modular Blue policy, scenario memory, balanced evaluation, multi-seed
evidence, stress scenarios, hard mode, failure analysis, and explicit Red
objectives.

## Why does hard mode perform worse?

Hard mode intentionally applies partial recovery and rolling SLA pressure. It
prevents the submission from relying only on optimistic recovery runs.

## What still requires private work?

Official competition runtime integration. The public repository includes only a
local adapter and inert private-adapter examples. Real competition bindings
should remain private.

## How can judges reproduce the evidence?

Run:

```bash
pytest
python scripts/run_experiments.py --rounds 100 --seed 42
python scripts/run_balanced_evaluation.py --rounds-per-scenario 20 --seed 42
python scripts/run_hard_mode.py --rounds 100 --seed 42
python scripts/goal_runner.py --target-score 92 --strict
```
