

"""
UFCPS state validator v1.

This validator performs two layers of checks:

1. JSON Schema validation for structural correctness.
2. Cross-field semantic checks for UFCPS state invariants that are not
   adequately expressed by the schema alone.

The validator does not determine:
- whether a task is solvable;
- whether a result is scientifically true;
- whether an interpretation is correct;
- whether a strategy is optimal;
- whether convergence will occur.

Usage:

    python validator/validate_state.py path/to/state.json

Optional:

    python validator/validate_state.py path/to/state.json \
        --schema schemas/procedural_state_v1.json

Exit codes:
    0  valid
    1  invalid state
    2  usage or runtime error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import SchemaError
except ImportError as exc:
    raise SystemExit(
        "jsonschema is required. Install it with: pip install jsonschema"
    ) from exc


CANONICAL_FLOW = "diff -> fix -> diss -> unfold"
VALID_STATUSES = {
    "active",
    "stuck",
    "dissipating",
    "delegated",
    "unfolded",
}
VALID_OPERATIONS = {
    "diff",
    "fix",
    "diss",
    "unfold",
    "delegate",
    "compose",
    "terminate",
}


class ValidationErrorRecord:
    """A structured validation finding."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message

    def __str__(self) -> str:
        if self.path:
            return f"{self.path}: {self.message}"
        return self.message


def load_json(path: Path) -> Any:
    """Load a UTF-8 JSON file."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise RuntimeError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"Cannot read {path}: {exc}") from exc


def validate_schema(instance: Any, schema: dict[str, Any]) -> list[ValidationErrorRecord]:
    """Validate instance against JSON Schema Draft 2020-12."""
    try:
        validator = Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        )
        validator.check_schema(schema)
    except SchemaError as exc:
        return [
            ValidationErrorRecord(
                "$schema",
                f"Schema itself is invalid: {exc.message}",
            )
        ]

    findings: list[ValidationErrorRecord] = []

    for error in sorted(
        validator.iter_errors(instance),
        key=lambda item: list(item.absolute_path),
    ):
        path = ".".join(str(part) for part in error.absolute_path)
        findings.append(ValidationErrorRecord(path, error.message))

    return findings


def get_nested(
    instance: dict[str, Any],
    *keys: str,
) -> Any:
    """Safely retrieve a nested value."""
    current: Any = instance
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def semantic_validate(instance: Any) -> list[ValidationErrorRecord]:
    """
    Validate UFCPS cross-field invariants.

    These checks assume that schema validation has already succeeded enough
    for the expected fields to be present.
    """
    findings: list[ValidationErrorRecord] = []

    if not isinstance(instance, dict):
        return findings

    procedural_unit = instance.get("procedural_unit", {})
    task_state = instance.get("task_state", {})
    structural_difference = instance.get("structural_difference", {})
    operation = instance.get("operation", {})
    deadlock = instance.get("deadlock")
    delegation = instance.get("delegation")
    continuation = instance.get("continuation")
    recursion = instance.get("c5_recursion_control")
    preserved_state = instance.get("preserved_state")

    status = procedural_unit.get("session_status")
    step_index = procedural_unit.get("step_index")
    current_operation = operation.get("current")

    # Canonical operator flow.
    if operation.get("flow") != CANONICAL_FLOW:
        findings.append(
            ValidationErrorRecord(
                "operation.flow",
                f"must equal {CANONICAL_FLOW!r}",
            )
        )

    if current_operation not in VALID_OPERATIONS:
        findings.append(
            ValidationErrorRecord(
                "operation.current",
                "must be one of the canonical UFCPS operations",
            )
        )

    # A structural difference is required before a resolution operation.
    resolution_operations = {"fix", "diss", "unfold"}
    if current_operation in resolution_operations:
        if structural_difference.get("identified") is not True:
            findings.append(
                ValidationErrorRecord(
                    "structural_difference.identified",
                    f"must be true when operation.current is {current_operation!r}",
                )
            )

    # Deadlock invariant.
    deadlock_present = (
        isinstance(deadlock, dict) and deadlock.get("present") is True
    )

    if status == "stuck" and not deadlock_present:
        findings.append(
            ValidationErrorRecord(
                "deadlock.present",
                "must be true when procedural_unit.session_status is 'stuck'",
            )
        )

    if deadlock_present and status not in {"stuck", "dissipating", "delegated", "unfolded"}:
        findings.append(
            ValidationErrorRecord(
                "procedural_unit.session_status",
                "deadlock state requires a continuation-oriented status",
            )
        )

    # A stuck state must not silently terminate the process.
    if status == "stuck" and current_operation == "terminate":
        findings.append(
            ValidationErrorRecord(
                "operation.current",
                "a local stuck state must not automatically terminate the process",
            )
        )

    # Delegation consistency.
    delegation_requested = (
        isinstance(delegation, dict) and delegation.get("requested") is True
    )

    if delegation_requested:
        if status not in {"dissipating", "delegated"}:
            findings.append(
                ValidationErrorRecord(
                    "procedural_unit.session_status",
                    "delegation requires 'dissipating' or 'delegated' status",
                )
            )

        if not delegation.get("target_carrier_type"):
            findings.append(
                ValidationErrorRecord(
                    "delegation.target_carrier_type",
                    "must be specified when delegation is requested",
                )
            )

        if not delegation.get("reason"):
            findings.append(
                ValidationErrorRecord(
                    "delegation.reason",
                    "must explain why delegation is required",
                )
            )

    if status == "delegated" and not delegation_requested:
        findings.append(
            ValidationErrorRecord(
                "delegation.requested",
                "must be true when procedural_unit.session_status is 'delegated'",
            )
        )

    # Continuation consistency.
    continuation_required = (
        isinstance(continuation, dict)
        and continuation.get("required") is True
    )
    state_preserved = (
        isinstance(continuation, dict)
        and continuation.get("state_preserved") is True
    )

    if continuation_required and not state_preserved:
        findings.append(
            ValidationErrorRecord(
                "continuation.state_preserved",
                "must be true when continuation.required is true",
            )
        )

    if continuation_required and continuation.get("successor_exists") is True:
        next_step = continuation.get("next_step_index")
        if isinstance(step_index, int) and isinstance(next_step, int):
            if next_step != step_index + 1:
                findings.append(
                    ValidationErrorRecord(
                        "continuation.next_step_index",
                        f"must equal current step_index + 1 ({step_index + 1})",
                    )
                )

    if status == "unfolded" and not continuation_required:
        findings.append(
            ValidationErrorRecord(
                "continuation.required",
                "should be true when procedural_unit.session_status is 'unfolded'",
            )
        )

    # Preservation consistency.
    if isinstance(preserved_state, dict):
        preserved = preserved_state.get("preserved")
        if continuation_required and preserved is not True:
            findings.append(
                ValidationErrorRecord(
                    "preserved_state.preserved",
                    "must be true when continuation is required",
                )
            )

    # C5 recursion control.
    if isinstance(recursion, dict):
        current_depth = recursion.get("current_depth")
        max_depth = recursion.get("max_depth_limit")
        action = recursion.get("action_on_overflow")

        if (
            isinstance(current_depth, int)
            and isinstance(max_depth, int)
            and current_depth > max_depth
            and action not in {"delegate", "branch", "pause", "terminate"}
        ):
            findings.append(
                ValidationErrorRecord(
                    "c5_recursion_control.action_on_overflow",
                    "must define a valid overflow action when depth exceeds the configured limit",
                )
            )

        # A depth overflow with no explicit continuation action is invalid.
        if (
            isinstance(current_depth, int)
            and isinstance(max_depth, int)
            and current_depth > max_depth
        ):
            if current_operation not in {"delegate", "compose", "terminate"}:
                findings.append(
                    ValidationErrorRecord(
                        "operation.current",
                        "must use an explicit recursion-control operation when C5 depth is exceeded",
                    )
                )

    # Result status consistency.
    result_status = task_state.get("result_status")
    local_result = task_state.get("local_result", "")

    if result_status == "none" and local_result:
        findings.append(
            ValidationErrorRecord(
                "task_state.result_status",
                "cannot be 'none' when task_state.local_result contains a result",
            )
        )

    if result_status in {"complete", "failed", "inconclusive"} and not local_result:
        findings.append(
            ValidationErrorRecord(
                "task_state.local_result",
                "must contain a local result for a terminally classified local result state",
            )
        )

    # Difference source should be explicit when a difference is identified.
    if structural_difference.get("identified") is True:
        if not structural_difference.get("description"):
            findings.append(
                ValidationErrorRecord(
                    "structural_difference.description",
                    "must describe the identified difference",
                )
            )

    # Termination is a global/process-level action, not an automatic local state.
    if current_operation == "terminate":
        unresolved = instance.get("unresolved_difference", "")
        continuation_flag = get_nested(instance, "continuation", "required")
        if unresolved and continuation_flag is True:
            findings.append(
                ValidationErrorRecord(
                    "operation.current",
                    "cannot terminate while an unresolved difference is explicitly marked for continuation",
                )
            )

    return findings


def format_findings(findings: list[ValidationErrorRecord]) -> str:
    """Format findings for CLI output."""
    if not findings:
        return "VALID"

    lines = [f"INVALID: {len(findings)} finding(s)"]
    lines.extend(f"  - {finding}" for finding in findings)
    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Validate a UFCPS procedural state against schema and semantic invariants.",
    )
    parser.add_argument(
        "state",
        type=Path,
        help="Path to the state JSON instance.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/procedural_state_v1.json"),
        help="Path to the JSON Schema (default: schemas/procedural_state_v1.json).",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Run only JSON Schema validation.",
    )
    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_argument_parser()
    args = parser.parse_args()

    try:
        state = load_json(args.state)
        schema = load_json(args.schema)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    schema_findings = validate_schema(state, schema)

    if args.schema_only:
        findings = schema_findings
    else:
        semantic_findings = []
        if not schema_findings:
            semantic_findings = semantic_validate(state)
        findings = schema_findings + semantic_findings

    print(format_findings(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
