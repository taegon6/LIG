from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_EXPERIMENT_COMMANDS = [
    [sys.executable, "scripts/run_experiments.py", "--rounds", "100", "--seed", "42"],
    [sys.executable, "scripts/run_balanced_evaluation.py", "--rounds-per-scenario", "20", "--seed", "42"],
    [sys.executable, "scripts/run_hard_mode.py", "--rounds", "100", "--seed", "42"],
]

REQUIRED_REPORTS = [
    "reports/round_metrics.csv",
    "reports/scenario_summary.csv",
    "reports/balanced_round_metrics.csv",
    "reports/balanced_scenario_summary.csv",
    "reports/hard_mode_round_metrics.csv",
    "reports/hard_mode_summary.csv",
]

REQUIRED_DOCS = [
    "docs/one_page_summary.md",
    "docs/report.md",
    "docs/experiment_results.md",
    "docs/failure_analysis.md",
    "docs/attack_scenario_design.md",
    "docs/red_strategy_analysis.md",
    "docs/judge_qa.md",
    "docs/demo_flow.md",
    "docs/safety_statement.md",
    "docs/private_adapter_design.md",
    "docs/team_capability.md",
    "docs/submission_checklist.md",
]

SAFE_EVENTS = {
    "TRAFFIC_SPIKE",
    "AUTH_ANOMALY",
    "TELEMETRY_INCONSISTENCY",
    "SERVICE_DEGRADATION",
    "MISSION_COMMAND_ANOMALY",
    "LOG_NOISE",
}

RED_OBJECTIVES = {
    "SLA_DROP",
    "BLUE_MISMATCH",
    "CONFUSION",
    "RECOVERY_PRESSURE",
    "COVERAGE",
}

FORBIDDEN_PRIVATE_ADAPTER_TERMS = [
    "http://",
    "https://",
    "token",
    "endpoint",
    "payload",
    "exploit",
    "scan",
]


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "details": self.details}


def run_command(command: list[str], timeout: int = 180) -> CheckResult:
    display = " ".join(command)
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    output = (completed.stdout + "\n" + completed.stderr).strip()
    tail = "\n".join(output.splitlines()[-8:])
    return CheckResult(display, completed.returncode == 0, tail or f"exit={completed.returncode}")


def path_exists(path: str) -> bool:
    return (PROJECT_ROOT / path).exists()


def check_required_paths(label: str, paths: list[str]) -> CheckResult:
    missing = [path for path in paths if not path_exists(path)]
    if missing:
        return CheckResult(label, False, "missing: " + ", ".join(missing))
    return CheckResult(label, True, f"all {len(paths)} present")


def file_text(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def hard_mode_has_non_perfect_condition() -> CheckResult:
    path = PROJECT_ROOT / "reports/hard_mode_round_metrics.csv"
    if not path.exists():
        return CheckResult("hard_mode_non_perfect", False, "hard-mode round metrics missing")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return CheckResult("hard_mode_non_perfect", False, "hard-mode round metrics empty")
    non_perfect = any(
        float(row.get("post_action_sla", 100.0)) < 100.0
        or float(row.get("rolling_sla_10", 100.0)) < 100.0
        or str(row.get("recovery_failed", "")).lower() == "true"
        or float(row.get("red_success_score", 0.0)) > 0.0
        for row in rows
    )
    return CheckResult(
        "hard_mode_non_perfect",
        non_perfect,
        f"rows={len(rows)}, non_perfect={non_perfect}",
    )


def check_red_readiness() -> tuple[CheckResult, dict[str, Any]]:
    evidence: dict[str, Any] = {}
    try:
        from agents.red_agent import RedAgent
        from agents.red_objectives import RED_OBJECTIVES as OBJECTIVES, validate_objectives_safe_only
        from mission_service.app import app
        from fastapi.testclient import TestClient

        plan = RedAgent(epsilon=0.0).generate_plan("BALANCED", [], 100.0, [])
        client = TestClient(app)
        stats = client.get("/stats/red")
        body = stats.json() if stats.status_code == 200 else {}
        objective_names = set(OBJECTIVES)
        objective_events = {event for objective in OBJECTIVES.values() for event in objective.safe_events}
        evidence = {
            "plan": plan.metadata(),
            "objective_names": sorted(objective_names),
            "objective_events": sorted(objective_events),
            "stats_status": stats.status_code,
            "stats_keys": sorted(body.keys()),
        }
        passed = (
            objective_names == RED_OBJECTIVES
            and set(objective_events) <= SAFE_EVENTS
            and validate_objectives_safe_only()
            and stats.status_code == 200
            and "red_objectives" in body
            and "scenario_stats" in body
        )
        return CheckResult("red_readiness", passed, json.dumps(evidence, ensure_ascii=False)), evidence
    except Exception as exc:  # pragma: no cover - reported in JSON for CLI users
        return CheckResult("red_readiness", False, repr(exc)), evidence


def check_blue_readiness() -> CheckResult:
    required = {
        "agents/blue/blue_agent.py": ["risk_score", "selected_action", "expected_sla_impact"],
        "agents/blue/sla_governor.py": ["SLA"],
        "core/scoring.py": ["red_success_score", "blue_defense_score", "recovery_score"],
        "scripts/run_balanced_evaluation.py": ["action_accuracy", "false_positive"],
        "scripts/run_hard_mode.py": ["recovery_failed", "rolling_sla_10"],
        "docs/failure_analysis.md": ["does not prove perfect real-world defense"],
    }
    missing: list[str] = []
    for path, terms in required.items():
        text = file_text(path) if path_exists(path) else ""
        for term in terms:
            if term not in text:
                missing.append(f"{path}:{term}")
    return CheckResult("blue_readiness", not missing, "missing: " + ", ".join(missing) if missing else "blue evidence present")


def check_ai_architecture() -> CheckResult:
    required_paths = [
        "agents/red_agent.py",
        "agents/blue_agent.py",
        "agents/commander_agent.py",
        "agents/memory.py",
        "adapters/base.py",
        "adapters/local_simulator.py",
        "adapters/competition_stub.py",
        "dashboard/streamlit_app.py",
        "scripts/run_ablation.py",
        "scripts/run_multi_seed_evaluation.py",
        "scripts/goal_runner.py",
    ]
    missing = [path for path in required_paths if not path_exists(path)]
    return CheckResult("ai_architecture", not missing, "missing: " + ", ".join(missing) if missing else "architecture evidence present")


def check_safety_boundaries() -> tuple[CheckResult, dict[str, Any]]:
    private_adapter_path = "adapters/private_red_adapter.py.example"
    private_text = file_text(private_adapter_path).lower() if path_exists(private_adapter_path) else ""
    private_hits = [term for term in FORBIDDEN_PRIVATE_ADAPTER_TERMS if term in private_text]

    source_patterns = [
        r"\bsocket\.",
        r"\bparamiko\b",
        r"\bftplib\b",
        r"\btelnetlib\b",
        r"\bscapy\b",
        r"\bnmap\b",
        r"\bmasscan\b",
        r"\bhydra\b",
        r"\bmetasploit\b",
        r"\bos\.system\b",
        r"\bsubprocess\.popen\b",
    ]
    source_hits: list[str] = []
    for folder in ["agents", "adapters", "core", "mission_service", "simulator"]:
        for path in (PROJECT_ROOT / folder).rglob("*"):
            if path.is_file() and path.suffix in {".py", ".example"}:
                text = path.read_text(encoding="utf-8").lower()
                for pattern in source_patterns:
                    if re.search(pattern, text):
                        source_hits.append(f"{path.relative_to(PROJECT_ROOT)}:{pattern}")

    adapter_default_text = file_text("adapters/factory.py")
    default_adapter_ok = 'os.getenv("AEGIS_ADAPTER", "local")' in adapter_default_text
    evidence = {
        "private_adapter_forbidden_hits": private_hits,
        "source_hits": source_hits,
        "default_adapter_local": default_adapter_ok,
    }
    passed = not private_hits and not source_hits and default_adapter_ok
    return CheckResult("safety_boundaries", passed, json.dumps(evidence, ensure_ascii=False)), evidence


def check_docs_completeness() -> CheckResult:
    result = check_required_paths("required_docs", REQUIRED_DOCS)
    if not result.passed:
        return result
    required_terms = {
        "docs/attack_scenario_design.md": ["SLA_DROP", "BLUE_MISMATCH", "RECOVERY_PRESSURE"],
        "docs/red_strategy_analysis.md": ["red_success_score", "coverage_score"],
        "docs/team_capability.md": ["attack", "defense", "AI", "full-stack", "execution"],
        "docs/private_adapter_design.md": ["private adapter", "official runtime"],
    }
    missing: list[str] = []
    for path, terms in required_terms.items():
        text = file_text(path)
        lowered = text.lower()
        for term in terms:
            if term.lower() not in lowered:
                missing.append(f"{path}:{term}")
    return CheckResult("docs_completeness", not missing, "missing: " + ", ".join(missing) if missing else "docs complete")


def compute_scores(checks: dict[str, CheckResult]) -> dict[str, Any]:
    attack_items = [
        path_exists("agents/red_objectives.py"),
        checks["red_readiness"].passed,
        path_exists("docs/attack_scenario_design.md"),
        path_exists("docs/red_strategy_analysis.md"),
        path_exists("adapters/private_red_adapter.py.example"),
        path_exists("reports/hard_mode_round_metrics.csv"),
        checks["hard_mode_non_perfect"].passed,
    ]
    defense_items = [
        checks["blue_readiness"].passed,
        path_exists("scripts/run_balanced_evaluation.py"),
        path_exists("scripts/run_stress_scenarios.py"),
        path_exists("scripts/run_hard_mode.py"),
        path_exists("docs/failure_analysis.md"),
        path_exists("reports/balanced_scenario_summary.csv"),
    ]
    ai_items = [
        checks["ai_architecture"].passed,
        path_exists("mission_service/app.py"),
        path_exists("agents/memory.py"),
        path_exists("scripts/run_ablation.py"),
        path_exists("scripts/run_multi_seed_evaluation.py"),
        path_exists("dashboard/streamlit_app.py"),
        path_exists("scripts/goal_runner.py"),
    ]
    team_items = [
        path_exists("docs/team_capability.md"),
        all(term in file_text("docs/team_capability.md").lower() for term in ["attack", "defense", "ai", "full-stack", "execution"]),
    ]
    docs_items = [
        checks["docs_completeness"].passed,
        path_exists("docs/one_page_summary.md"),
        path_exists("docs/judge_qa.md"),
        path_exists("docs/demo_flow.md"),
        path_exists("docs/safety_statement.md"),
        path_exists("docs/submission_checklist.md"),
    ]

    def weighted_score(items: list[bool], points: float) -> float:
        return round(points * (sum(1 for item in items if item) / len(items)), 2)

    categories = {
        "Attack Scenario Design": weighted_score(attack_items, 30),
        "Defense Strategy": weighted_score(defense_items, 25),
        "AI Agent Architecture": weighted_score(ai_items, 25),
        "Team Capability": weighted_score(team_items, 10),
        "Document Completeness": weighted_score(docs_items, 10),
    }
    return {"categories": categories, "total_score": round(sum(categories.values()), 2)}


def write_reports(result: dict[str, Any]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "goal_score.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Aegis-Swarm v2 DAH Readiness Score",
        "",
        f"Target score: {result['target_score']}",
        f"Total score: {result['total_score']}",
        f"Hard gates passed: {result['hard_gates_passed']}",
        "",
        "## Rubric",
        "",
        "| Category | Score |",
        "| --- | ---: |",
    ]
    for category, score in result["categories"].items():
        lines.append(f"| {category} | {score:.2f} |")
    lines.extend(["", "## Checks", "", "| Check | Passed | Details |", "| --- | --- | --- |"])
    for check in result["checks"]:
        details = str(check["details"]).replace("\n", "<br>")
        lines.append(f"| {check['name']} | {check['passed']} | {details} |")
    lines.extend(["", "## Limitations", "", "- This is a local simulation readiness score, not official DAH runtime validation.", "- Official integration still requires a private adapter and competition environment access."])
    (REPORTS_DIR / "goal_score.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_goal(target_score: float, strict: bool) -> dict[str, Any]:
    command_checks = [run_command([sys.executable, "-m", "pytest"], timeout=240)]
    command_checks.extend(run_command(command, timeout=240) for command in REQUIRED_EXPERIMENT_COMMANDS)

    checks: dict[str, CheckResult] = {
        "pytest": command_checks[0],
        "run_experiments": command_checks[1],
        "run_balanced_evaluation": command_checks[2],
        "run_hard_mode": command_checks[3],
        "required_reports": check_required_paths("required_reports", REQUIRED_REPORTS),
        "required_docs": check_required_paths("required_docs", REQUIRED_DOCS),
        "hard_mode_non_perfect": hard_mode_has_non_perfect_condition(),
    }
    checks["red_readiness"], red_evidence = check_red_readiness()
    checks["blue_readiness"] = check_blue_readiness()
    checks["ai_architecture"] = check_ai_architecture()
    checks["docs_completeness"] = check_docs_completeness()
    checks["safety_boundaries"], safety_evidence = check_safety_boundaries()

    hard_gate_names = [
        "pytest",
        "run_experiments",
        "run_balanced_evaluation",
        "run_hard_mode",
        "required_reports",
        "required_docs",
        "red_readiness",
        "safety_boundaries",
        "hard_mode_non_perfect",
    ]
    if strict:
        hard_gate_names.extend(["blue_readiness", "ai_architecture", "docs_completeness"])

    scores = compute_scores(checks)
    hard_gates_passed = all(checks[name].passed for name in hard_gate_names)
    result = {
        "target_score": target_score,
        "strict": strict,
        "total_score": scores["total_score"],
        "categories": scores["categories"],
        "hard_gates_passed": hard_gates_passed,
        "passed": hard_gates_passed and scores["total_score"] >= target_score,
        "hard_gates": hard_gate_names,
        "checks": [check.as_dict() for check in checks.values()],
        "red_evidence": red_evidence,
        "safety_evidence": safety_evidence,
    }
    write_reports(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DAH preliminary-readiness self-check.")
    parser.add_argument("--target-score", type=float, default=92.0)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    result = run_goal(args.target_score, args.strict)
    print(f"goal score: {result['total_score']}")
    print(f"hard gates passed: {result['hard_gates_passed']}")
    print("goal score JSON: reports/goal_score.json")
    print("goal score markdown: reports/goal_score.md")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
