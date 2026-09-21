#!/usr/bin/env python3

"""Unified runner for the initial UFCPS simulation scenarios.

The runner executes deterministic reference scenarios and normalizes their
outputs into one machine-readable report.

Scenarios currently included:

- basic_handoff
- parallel_resolution
- autonomous_experiment

The runner does not assign quality rankings to scenarios. It reports whether
each scenario completed its own structural acceptance checks.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable

from .scenarios import (
    run_autonomous_experiment,
    run_basic_handoff,
    run_parallel_resolution,
)


ScenarioCallable = Callable[[], Any]


SCENARIOS: dict[str, ScenarioCallable] = {
    "basic_handoff": run_basic_handoff,
    "parallel_resolution": run_parallel_resolution,
    "autonomous_experiment": run_autonomous_experiment,
}


def normalize_result(result: Any) -> dict[str, Any]:
    """Convert a scenario result into plain JSON-compatible data."""
    if is_dataclass(result):
        value = asdict(result)
    elif hasattr(result, "to_dict") and callable(result.to_dict):
        value = result.to_dict()
    elif isinstance(result, dict):
        value = dict(result)
    else:
        raise TypeError(
            f"Unsupported scenario result type: {type(result).__name__}"
        )

    return _json_safe(value)


def _json_safe(value: Any) -> Any:
    """Recursively normalize enums and nested dataclass values."""
    if is_dataclass(value):
        return _json_safe(asdict(value))

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]

    if hasattr(value, "value") and isinstance(
        getattr(value, "value", None),
        str,
    ):
        return value.value

    return value


def scenario_passed(result: dict[str, Any]) -> bool:
    """Evaluate the scenario's own explicit acceptance fields."""
    continuity = result.get("continuity_valid", False)
    terminated = result.get("process_terminated", False)

    if continuity is not True:
        return False

    if terminated is True:
        return False

    # Scenario-specific structural acceptance checks.
    if "handoff_performed" in result:
        if result.get("handoff_performed") is not True:
            return False

    if "continuation_preserved" in result:
        if result.get("continuation_preserved") is not True:
            return False

    if "destination_completed" in result:
        if result.get("destination_completed") is not True:
            return False

    if "branch_count" in result:
        if result.get("branch_count") != 2:
            return False

    if "branch_state_isolated" in result:
        if result.get("branch_state_isolated") is not True:
            return False

    if "provenance_preserved" in result:
        if result.get("provenance_preserved") is not True:
            return False

    if "composition_inputs_ready" in result:
        if result.get("composition_inputs_ready") is not True:
            return False

    if "continuation_ready" in result:
        if result.get("continuation_ready") is not True:
            return False

    return True


def run_scenario(
    name: str,
    function: ScenarioCallable,
) -> dict[str, Any]:
    """Run one scenario and capture success or an execution error."""
    try:
        raw_result = function()
        result = normalize_result(raw_result)

        return {
            "scenario": name,
            "status": "passed"
            if scenario_passed(result)
            else "failed",
            "result": result,
            "error": None,
        }

    except Exception as exc:  # pragma: no cover - defensive runtime boundary
        return {
            "scenario": name,
            "status": "error",
            "result": None,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }


def run_selected(
    names: list[str] | None = None,
) -> dict[str, Any]:
    """Run selected scenarios or all registered scenarios."""
    selected = names or list(SCENARIOS)

    unknown = [
        name
        for name in selected
        if name not in SCENARIOS
    ]

    if unknown:
        raise ValueError(
            "Unknown scenario(s): " + ", ".join(sorted(unknown))
        )

    results = [
        run_scenario(name, SCENARIOS[name])
        for name in selected
    ]

    passed = sum(
        1
        for item in results
        if item["status"] == "passed"
    )

    failed = sum(
        1
        for item in results
        if item["status"] == "failed"
    )

    errors = sum(
        1
        for item in results
        if item["status"] == "error"
    )

    return {
        "runner_version": "v1",
        "scenarios_requested": len(selected),
        "scenarios_passed": passed,
        "scenarios_failed": failed,
        "scenarios_with_errors": errors,
        "all_passed": (
            len(selected) > 0
            and passed == len(selected)
        ),
        "scenarios": results,
    }


def write_report(
    report: dict[str, Any],
    output: Path,
) -> None:
    """Write the report as UTF-8 JSON."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Run UFCPS simulation scenarios.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        choices=sorted(SCENARIOS),
        help=(
            "Scenario to run. Repeat the option to select multiple "
            "scenarios. Without this option, all scenarios run."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the JSON report.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the report to stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report = run_selected(args.scenarios)
    except ValueError as exc:
        parser.error(str(exc))

    serialized = json.dumps(
        report,
        ensure_ascii=False,
        indent=2 if args.pretty or args.output else None,
    )

    if args.output:
        write_report(report, args.output)

    print(serialized)

    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
