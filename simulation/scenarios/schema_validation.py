"""UFCPS schema validation scenario.

This module exercises the machine-readable UFCPS state schemas with
representative valid and deliberately invalid payloads.

The scenario validates structural conformance only. Passing validation does
not establish scientific truth, task solvability, semantic correctness, or
convergence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas"


@dataclass(frozen=True)
class SchemaCase:
    """One schema-validation case."""

    name: str
    schema_file: str
    payload: dict[str, Any]
    expected_valid: bool


@dataclass
class SchemaValidationResult:
    """Aggregate result for the schema-validation scenario."""

    cases: list[dict[str, Any]] = field(default_factory=list)
    passed: bool = False
    valid_cases: int = 0
    invalid_cases: int = 0
    expected_failures_confirmed: int = 0
    errors: list[str] = field(default_factory=list)


def _load_schema(filename: str) -> dict[str, Any]:
    path = SCHEMA_DIR / filename
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _procedural_state_valid() -> dict[str, Any]:
    """Return a minimal payload satisfying procedural_state_v1.json."""
    return {
        "procedural_unit": {
            "step_index": 0,
            "unit_id": "P0",
            "carrier": {
                "carrier_id": "agent_00",
                "carrier_type": "solver",
            },
            "session_status": "active",
        },
        "task_state": {
            "task": "Resolve structural difference",
            "current_state": "initial",
            "local_result": "",
            "result_status": "none",
        },
        "structural_difference": {
            "identified": True,
            "description": "A relevant difference has been identified.",
            "source": "task",
            "relevance": "continuation",
        },
        "operation": {
            "current": "diff",
            "flow": "diff -> fix -> diss -> unfold",
            "completed": ["diff"],
        },
        "continuation": {
            "required": True,
            "state_preserved": True,
            "successor_exists": False,
            "next_step_index": 1,
            "next_unit_reference": "P1",
            "next_carrier_id": "agent_01",
            "next_carrier_type": "solver",
            "reason": "Continue the process with preserved state.",
        },
        "semantic_beacons": {
            "mandatory_tokens": ["metamonism", "Ex uno omnia"],
            "operator_flow": "diff -> fix -> diss -> unfold",
        },
    }


def _experimental_state_valid() -> dict[str, Any]:
    """Return a minimal payload satisfying experimental_state_v1.json."""
    return {
        "experiment_id": "EXP-001",
        "procedural_unit": {
            "step_index": 0,
            "carrier_id": "agent_lab_00",
            "carrier_type": "experimenter",
            "session_status": "active",
        },
        "research_question": "Does preserving continuation state retain task progress?",
        "hypothesis": "Preserved continuation state is sufficient for process handoff.",
        "testable_prediction": "A successor can continue from the preserved state.",
        "method": {
            "description": "Handoff the state to a compatible successor carrier.",
            "procedure": [
                "Preserve continuation-relevant state.",
                "Construct a successor procedural unit.",
                "Validate the reconstructed state.",
            ],
            "controls": ["Use the same task state before and after handoff."],
        },
        "input_conditions": ["Continuation state is explicitly preserved."],
        "expected_observation": "Successor resumes from the preserved state.",
        "stop_condition": "Successor state is reconstructed and validated.",
        "observations": [
            {
                "observation_id": "OBS-001",
                "description": "State reference remained available.",
                "source_type": "simulation",
            }
        ],
        "result": "Successor reconstructed the continuation state.",
        "result_class": "confirming",
        "interpretation": "The observation is consistent with the hypothesis for this test.",
        "uncertainty": {
            "present": True,
            "description": "The result is limited to the simulated conditions.",
            "level": "moderate",
        },
        "limitations": ["Single simulated handoff."],
        "constraints": ["Schema validation is structural only."],
        "unresolved_difference": "",
        "next_question": "Can the same state survive repeated carrier replacement?",
        "next_required_operation": "unfold",
        "continuation": {
            "state_preserved": True,
            "continuation_required": True,
            "state_reference": "state://EXP-001/P0",
            "handoff_reason": "Continue the experiment.",
            "next_carrier_type": "experimenter",
            "branch_count": 0,
        },
    }


def _cases() -> list[SchemaCase]:
    procedural = _procedural_state_valid()
    procedural_missing_required = dict(procedural)
    procedural_missing_required.pop("continuation")

    experimental = _experimental_state_valid()
    experimental_bad_enum = dict(experimental)
    experimental_bad_enum["result_class"] = "made_up_result"

    return [
        SchemaCase(
            name="procedural_valid",
            schema_file="procedural_state_v1.json",
            payload=procedural,
            expected_valid=True,
        ),
        SchemaCase(
            name="procedural_missing_required",
            schema_file="procedural_state_v1.json",
            payload=procedural_missing_required,
            expected_valid=False,
        ),
        SchemaCase(
            name="experimental_valid",
            schema_file="experimental_state_v1.json",
            payload=experimental,
            expected_valid=True,
        ),
        SchemaCase(
            name="experimental_invalid_result_class",
            schema_file="experimental_state_v1.json",
            payload=experimental_bad_enum,
            expected_valid=False,
        ),
    ]


def validate_case(case: SchemaCase) -> tuple[bool, list[str]]:
    """Validate one payload and return (is_valid, error_messages)."""
    schema = _load_schema(case.schema_file)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(case.payload), key=lambda error: list(error.path))
    return not errors, [error.message for error in errors]


def run_schema_validation() -> SchemaValidationResult:
    """Execute all schema-validation cases."""
    result = SchemaValidationResult()

    for case in _cases():
        try:
            actual_valid, errors = validate_case(case)
        except Exception as exc:  # pragma: no cover - defensive diagnostic path
            result.errors.append(f"{case.name}: validator error: {exc}")
            continue

        outcome_matches = actual_valid == case.expected_valid
        if case.expected_valid and actual_valid:
            result.valid_cases += 1
        elif not case.expected_valid and not actual_valid:
            result.invalid_cases += 1
            result.expected_failures_confirmed += 1

        result.cases.append(
            {
                "name": case.name,
                "schema_file": case.schema_file,
                "expected_valid": case.expected_valid,
                "actual_valid": actual_valid,
                "outcome_matches": outcome_matches,
                "errors": errors,
            }
        )

        if not outcome_matches:
            result.errors.append(
                f"{case.name}: expected valid={case.expected_valid}, "
                f"got valid={actual_valid}"
            )

    result.passed = not result.errors and len(result.cases) == len(_cases())
    return result


if __name__ == "__main__":
    outcome = run_schema_validation()
    print(json.dumps({
        "passed": outcome.passed,
        "valid_cases": outcome.valid_cases,
        "invalid_cases": outcome.invalid_cases,
        "expected_failures_confirmed": outcome.expected_failures_confirmed,
        "cases": outcome.cases,
        "errors": outcome.errors,
    }, indent=2, ensure_ascii=False))
    raise SystemExit(0 if outcome.passed else 1)
