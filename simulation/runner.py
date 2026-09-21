#!/usr/bin/env python3

"""Unified runner for UFCPS simulation scenarios.

The runner executes deterministic reference scenarios and normalizes their
outputs into one machine-readable report.

The runner reports explicit scenario acceptance conditions. It does not
assign a global quality ranking to different architectural conditions.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable

from .scenarios import (
    run_autonomous_experiment,
    run_basic_handoff,
    run_carrier_substitution,
    run_communication_interruption,
    run_composition,
    run_continuity_vs_centralization,
    run_contradictory_branches,
    run_forced_deadlock,
    run_global_termination,
    run_long_run_continuity,
    run_negative_result,
    run_parallel_resolution,
    run_recursion_stress,
    run_repeated_carrier_replacement,
    run_stateless_delegation_control,
    run_swarm_scaling,
)


ScenarioCallable = Callable[[], Any]


SCENARIOS: dict[str, ScenarioCallable] = {
    "basic_handoff": run_basic_handoff,
    "forced_deadlock": run_forced_deadlock,
    "carrier_substitution": run_carrier_substitution,
    "communication_interruption": run_communication_interruption,
    "continuity_vs_centralization": run_continuity_vs_centralization,
    "stateless_delegation_control": run_stateless_delegation_control,
    "parallel_resolution": run_parallel_resolution,
    "contradictory_branches": run_contradictory_branches,
    "composition": run_composition,
    "negative_result": run_negative_result,
    "recursion_stress": run_recursion_stress,
    "global_termination": run_global_termination,
    "long_run_continuity": run_long_run_continuity,
    "repeated_carrier_replacement": run_repeated_carrier_replacement,
    "swarm_scaling": run_swarm_scaling,
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
    """Evaluate a scenario's explicit acceptance fields."""
    continuity = result.get("continuity_valid", False)

    if continuity is not True:
        return False

    # Global termination has an intentional terminal end state.
    is_global_termination_test = (
        "explicit_termination_process_terminated" in result
    )

    if (
        result.get("process_terminated") is True
        and not is_global_termination_test
    ):
        return False

    checks_true = (
        "handoff_performed",
        "continuation_preserved",
        "destination_completed",
        "branch_state_isolated",
        "provenance_preserved",
        "composition_inputs_ready",
        "composed_state_stored",
        "successor_ready",
        "deadlock_created",
        "deadlock_not_terminal",
        "unresolved_difference_preserved",
        "successor_created",
        "successor_completed",
        "capability_was_unavailable_locally",
        "carrier_type_changed",
        "stateful_completion",
        "stateless_completion",
        "continuation_state_difference_observed",
        "contradiction_detected",
        "contradiction_preserved",
        "unresolved_difference_created",
        "successor_question_ready",
        "negative_result_recorded",
        "rejected_path_preserved",
        "successor_received_negative_result",
        "continuation_ready",
        "state_persisted_before_interruption",
        "communication_lost",
        "successor_recovered_from_shared_state",
        "overflow_reached",
        "explicit_control_event_recorded",
        "unbounded_growth_prevented",
        "local_failure_successor_created",
        "explicit_termination_process_terminated",
        "termination_reason_recorded",
        "local_failure_distinct_from_global_termination",
    )

    for field_name in checks_true:
        if field_name in result and result.get(field_name) is not True:
            return False

    checks_false = (
        "repeated_invalidated_path",
        "source_channel_restored",
        "local_failure_process_terminated",
        "state_loss_detected",
        "any_process_termination",
    )

    for field_name in checks_false:
        if field_name in result and result.get(field_name) is True:
            return False

    if "branch_count" in result and result.get("branch_count") != 2:
        return False

    if "composition_relation" in result:
        if not str(result.get("composition_relation")):
            return False

    if "overflow_action" in result:
        if result.get("overflow_action") not in {
            "delegate",
            "branch",
            "pause",
            "terminate",
        }:
            return False

    if "invalid_transitions" in result:
        if result.get("invalid_transitions") != 0:
            return False

    if (
        "completed_steps" in result
        and "configured_steps" in result
    ):
        if result.get("completed_steps") != result.get(
            "configured_steps"
        ):
            return False

    if (
        "interruptions_injected" in result
        and "interruptions_recovered" in result
    ):
        if result.get("interruptions_injected") != result.get(
            "interruptions_recovered"
        ):
            return False

    if (
        "successful_replacements" in result
        and "configured_replacements" in result
    ):
        if result.get("successful_replacements") != result.get(
            "configured_replacements"
        ):
            return False

    if "all_runs_isolated" in result:
        if result.get("all_runs_isolated") is not True:
            return False

    if "all_runs_provenance_valid" in result:
        if result.get("all_runs_provenance_valid") is not True:
            return False

    if "runs" in result:
        runs = result.get("runs")
        if isinstance(runs, list):
            for run in runs:
                if not isinstance(run, dict):
                    return False
                if run.get("continuity_valid") is not True:
                    return False
                if run.get("process_terminated") is True:
                    return False

    if "distributed" in result:
        distributed = result.get("distributed")
        centralized = result.get("centralized")

        if not isinstance(distributed, dict):
            return False

        if not isinstance(centralized, dict):
            return False

        if distributed.get("continuity_valid") is not True:
            return False

        if centralized.get("continuity_valid") is not True:
            return False

        if distributed.get("completed") is not True:
            return False

        if centralized.get("completed") is not True:
            return False

    if "replacement_records" in result:
        records = result.get("replacement_records")
        if isinstance(records, list):
            for record in records:
                if not isinstance(record, dict):
                    return False
                if record.get(
                    "continuation_state_available"
                ) is not True:
                    return False
                if record.get(
                    "unresolved_difference_preserved"
                ) is not True:
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

    except Exception as exc:
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
