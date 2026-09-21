#!/usr/bin/env python3

"""Benchmark Test 2: machine validation of UFCPS transitions."""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from validator.validate_transition import (  # noqa: E402
    load_json,
    semantic_validate,
    validate_schema,
)


@dataclass
class TransitionCaseResult:
    name: str
    schema_valid: bool
    semantic_valid: bool
    expected_valid: bool
    diagnostics: list[str]


@dataclass
class TransitionValidationResult:
    cases: list[TransitionCaseResult]
    valid_case_passed: bool
    invalid_cases_rejected: bool
    diagnostics_structured: bool
    all_expected_results_match: bool
    continuity_valid: bool


def _base_transition() -> dict:
    return {
        "transition_id": "T-0001",
        "transition_type": "continuation",
        "source_procedural_unit": {
            "step_index": 0,
            "carrier_id": "carrier_a",
            "carrier_type": "symbolic",
            "session_status": "active",
            "state_reference": "P0",
        },
        "operation": "unfold",
        "destination_procedural_unit": {
            "step_index": 1,
            "carrier_id": "carrier_b",
            "carrier_type": "symbolic",
            "session_status": "active",
            "state_reference": "P1",
        },
        "carrier_transition": {
            "changed": True,
            "source_carrier": "carrier_a",
            "destination_carrier": "carrier_b",
            "reason": "continuation handoff",
        },
        "continuation_state": {
            "state_preserved": True,
            "state_reference": "C0",
            "unresolved_difference": "continue task",
            "next_required_operation": "unfold",
        },
        "validation": {
            "schema_valid": True,
            "process_rule_valid": True,
            "continuation_valid": True,
        },
    }


def _run_case(
    name: str,
    transition: dict,
    expected_valid: bool,
    schema: dict,
) -> TransitionCaseResult:
    schema_findings = validate_schema(transition, schema)

    if schema_findings:
        semantic_findings = []
        schema_valid = False
        semantic_valid = False
    else:
        semantic_findings = semantic_validate(transition)
        schema_valid = True
        semantic_valid = not semantic_findings

    diagnostics = [str(item) for item in (schema_findings + semantic_findings)]

    return TransitionCaseResult(
        name=name,
        schema_valid=schema_valid,
        semantic_valid=semantic_valid,
        expected_valid=expected_valid,
        diagnostics=diagnostics,
    )


def run_transition_validation() -> TransitionValidationResult:
    """Run the deterministic transition-validation benchmark cases."""
    schema = load_json(REPO_ROOT / "transition_v1.json")

    valid = _base_transition()

    skipped_step = copy.deepcopy(valid)
    skipped_step["transition_id"] = "T-0002"
    skipped_step["destination_procedural_unit"]["step_index"] = 2

    inconsistent_carrier = copy.deepcopy(valid)
    inconsistent_carrier["transition_id"] = "T-0003"
    inconsistent_carrier["carrier_transition"]["source_carrier"] = "wrong_source"

    missing_continuation = copy.deepcopy(valid)
    missing_continuation["transition_id"] = "T-0004"
    missing_continuation["continuation_state"]["state_preserved"] = False

    delegation_without_change = copy.deepcopy(valid)
    delegation_without_change["transition_id"] = "T-0005"
    delegation_without_change["transition_type"] = "delegation"
    delegation_without_change["operation"] = "delegate"
    delegation_without_change["carrier_transition"]["changed"] = False
    delegation_without_change["carrier_transition"]["destination_carrier"] = "carrier_a"
    delegation_without_change["destination_procedural_unit"]["carrier_id"] = "carrier_a"

    local_with_replacement = copy.deepcopy(valid)
    local_with_replacement["transition_id"] = "T-0006"
    local_with_replacement["transition_type"] = "local"

    cases = [
        _run_case("correct_successor_step", valid, True, schema),
        _run_case("skipped_successor_step", skipped_step, False, schema),
        _run_case("inconsistent_carrier_metadata", inconsistent_carrier, False, schema),
        _run_case("missing_continuation_after_replacement", missing_continuation, False, schema),
        _run_case("delegation_without_carrier_change", delegation_without_change, False, schema),
        _run_case("local_transition_with_replacement", local_with_replacement, False, schema),
    ]

    valid_case_passed = (
        cases[0].schema_valid
        and cases[0].semantic_valid
        and cases[0].expected_valid
    )

    invalid_cases_rejected = all(
        not (case.schema_valid and case.semantic_valid)
        for case in cases[1:]
    )

    diagnostics_structured = all(
        case.expected_valid or bool(case.diagnostics)
        for case in cases
    )

    all_expected_results_match = all(
        (case.schema_valid and case.semantic_valid) == case.expected_valid
        for case in cases
    )

    return TransitionValidationResult(
        cases=cases,
        valid_case_passed=valid_case_passed,
        invalid_cases_rejected=invalid_cases_rejected,
        diagnostics_structured=diagnostics_structured,
        all_expected_results_match=all_expected_results_match,
        continuity_valid=(
            valid_case_passed
            and invalid_cases_rejected
            and diagnostics_structured
            and all_expected_results_match
        ),
    )


def main() -> int:
    result = run_transition_validation()
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    return 0 if result.continuity_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
