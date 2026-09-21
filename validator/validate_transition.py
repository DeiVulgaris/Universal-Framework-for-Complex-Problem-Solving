#!/usr/bin/env python3

"""
UFCPS transition validator v1.

This validator performs:

1. JSON Schema validation of a transition object.
2. Cross-field validation of UFCPS transition invariants.

The validator does not establish:
- task correctness;
- scientific truth;
- optimality;
- empirical validity;
- convergence;
- general intelligence.

Usage:

    python validator/validate_transition.py path/to/transition.json

Optional:

    python validator/validate_transition.py path/to/transition.json \
        --schema schemas/transition_v1.json

Exit codes:
    0  valid
    1  invalid transition
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

VALID_TRANSITION_TYPES = {
    "local",
    "continuation",
    "delegation",
    "branch",
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

VALID_STATUSES = {
    "active",
    "stuck",
    "dissipating",
    "delegated",
    "unfolded",
}

TERMINAL_DESTINATION_STATUSES = {
    "unfolded",
}

DELEGATION_TYPES = {
    "delegation",
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


def validate_schema(
    instance: Any,
    schema: dict[str, Any],
) -> list[ValidationErrorRecord]:
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


def semantic_validate(instance: Any) -> list[ValidationErrorRecord]:
    """Validate UFCPS transition invariants."""
    findings: list[ValidationErrorRecord] = []

    if not isinstance(instance, dict):
        return findings

    transition_type = instance.get("transition_type")
    source = instance.get("source_procedural_unit", {})
    operation = instance.get("operation", {})
    destination = instance.get("destination_procedural_unit", {})
    carrier_transition = instance.get("carrier_transition", {})
    continuation = instance.get("continuation_state", {})
    validation = instance.get("validation", {})

    source_step = source.get("step_index")
    destination_step = destination.get("step_index")

    source_carrier_id = source.get("carrier_id")
    destination_carrier_id = destination.get("carrier_id")
    source_carrier_type = source.get("carrier_type")
    destination_carrier_type = destination.get("carrier_type")

    source_status = source.get("session_status")
    destination_status = destination.get("session_status")

    current_operation = operation.get("name")
    operation_flow = operation.get("flow")

    source_state_reference = source.get("state_reference")
    destination_state_reference = destination.get("state_reference")

    # Basic enum-level semantic checks.
    if transition_type not in VALID_TRANSITION_TYPES:
        findings.append(
            ValidationErrorRecord(
                "transition_type",
                "must be a recognized UFCPS transition type",
            )
        )

    if current_operation not in VALID_OPERATIONS:
        findings.append(
            ValidationErrorRecord(
                "operation.name",
                "must be a recognized UFCPS operation",
            )
        )

    if source_status not in VALID_STATUSES:
        findings.append(
            ValidationErrorRecord(
                "source_procedural_unit.session_status",
                "must be a recognized UFCPS session status",
            )
        )

    if destination_status not in VALID_STATUSES:
        findings.append(
            ValidationErrorRecord(
                "destination_procedural_unit.session_status",
                "must be a recognized UFCPS session status",
            )
        )

    # Canonical operator flow.
    if operation_flow != CANONICAL_FLOW:
        findings.append(
            ValidationErrorRecord(
                "operation.flow",
                f"must equal {CANONICAL_FLOW!r}",
            )
        )

    # A successor procedural unit normally advances by one step.
    if isinstance(source_step, int) and isinstance(destination_step, int):
        if destination_step != source_step + 1:
            findings.append(
                ValidationErrorRecord(
                    "destination_procedural_unit.step_index",
                    f"must equal source step_index + 1 ({source_step + 1})",
                )
            )

    # A transition cannot point to exactly the same procedural unit.
    if (
        source_state_reference
        and destination_state_reference
        and source_state_reference == destination_state_reference
        and transition_type != "local"
    ):
        findings.append(
            ValidationErrorRecord(
                "destination_procedural_unit.state_reference",
                "must identify a distinct successor state for non-local transitions",
            )
        )

    # Carrier transition consistency.
    changed = carrier_transition.get("changed")
    declared_source_id = carrier_transition.get("source_carrier")
    declared_destination_id = carrier_transition.get("destination_carrier")

    actual_carrier_changed = (
        source_carrier_id is not None
        and destination_carrier_id is not None
        and source_carrier_id != destination_carrier_id
    )

    if changed is True and not actual_carrier_changed:
        findings.append(
            ValidationErrorRecord(
                "carrier_transition.changed",
                "cannot be true when source and destination carrier IDs are identical",
            )
        )

    if changed is False and actual_carrier_changed:
        findings.append(
            ValidationErrorRecord(
                "carrier_transition.changed",
                "must be true when source and destination carrier IDs differ",
            )
        )

    if declared_source_id and source_carrier_id:
        if declared_source_id != source_carrier_id:
            findings.append(
                ValidationErrorRecord(
                    "carrier_transition.source_carrier",
                    "must match source_procedural_unit.carrier_id",
                )
            )

    if declared_destination_id and destination_carrier_id:
        if declared_destination_id != destination_carrier_id:
            findings.append(
                ValidationErrorRecord(
                    "carrier_transition.destination_carrier",
                    "must match destination_procedural_unit.carrier_id",
                )
            )

    # Delegation requires carrier change by protocol semantics.
    if transition_type == "delegation":
        if changed is not True:
            findings.append(
                ValidationErrorRecord(
                    "carrier_transition.changed",
                    "delegation requires a carrier transition",
                )
            )

        if current_operation != "delegate":
            findings.append(
                ValidationErrorRecord(
                    "operation.name",
                    "delegation transition_type requires operation.name = 'delegate'",
                )
            )

    if transition_type == "continuation" and current_operation == "delegate":
        findings.append(
            ValidationErrorRecord(
                "transition_type",
                "a delegate operation should use transition_type = 'delegation'",
            )
        )

    # Branch transitions must preserve their source state while changing the
    # destination procedural reference.
    if transition_type == "branch":
        if not continuation.get("state_preserved"):
            findings.append(
                ValidationErrorRecord(
                    "continuation_state.state_preserved",
                    "branch transitions require preserved continuation state",
                )
            )

    # Local transitions must retain the same carrier.
    if transition_type == "local":
        if changed is True or actual_carrier_changed:
            findings.append(
                ValidationErrorRecord(
                    "carrier_transition",
                    "local transitions must retain the same carrier",
                )
            )

    # Continuation state is mandatory when changing carriers.
    if changed is True:
        if continuation.get("state_preserved") is not True:
            findings.append(
                ValidationErrorRecord(
                    "continuation_state.state_preserved",
                    "carrier replacement requires continuation-relevant state preservation",
                )
            )

        if not continuation.get("state_reference"):
            findings.append(
                ValidationErrorRecord(
                    "continuation_state.state_reference",
                    "carrier replacement requires a continuation state reference",
                )
            )

    # Source deadlock handling.
    if source_status == "stuck":
        if current_operation == "terminate":
            findings.append(
                ValidationErrorRecord(
                    "operation.name",
                    "a stuck source unit must not automatically terminate the process",
                )
            )

        if transition_type not in {"delegation", "continuation", "branch"}:
            findings.append(
                ValidationErrorRecord(
                    "transition_type",
                    "a stuck source should transition through continuation, delegation, or branching",
                )
            )

    # Dissipation semantics.
    if current_operation == "diss":
        if not continuation.get("state_preserved"):
            findings.append(
                ValidationErrorRecord(
                    "continuation_state.state_preserved",
                    "diss must preserve continuation-relevant state",
                )
            )

    # Unfold must instantiate a successor unit.
    if current_operation == "unfold":
        if destination_status not in {"active", "unfolded"}:
            findings.append(
                ValidationErrorRecord(
                    "destination_procedural_unit.session_status",
                    "unfold must create an active or unfolded destination unit",
                )
            )

    # Termination must not masquerade as continuation.
    if current_operation == "terminate":
        if continuation.get("continuation_required") is True:
            findings.append(
                ValidationErrorRecord(
                    "continuation_state.continuation_required",
                    "must be false or absent for an explicit termination transition",
                )
            )

    # Continuation-required transitions must preserve an unresolved difference
    # or an explicit reason for continuing.
    continuation_required = continuation.get("continuation_required") is True
    unresolved_difference = continuation.get("unresolved_difference")
    next_operation = continuation.get("next_required_operation")

    if continuation_required:
        if not unresolved_difference and not next_operation:
            findings.append(
                ValidationErrorRecord(
                    "continuation_state",
                    "continuation requires an unresolved difference or next required operation",
                )
            )

    if next_operation and next_operation not in VALID_OPERATIONS:
        findings.append(
            ValidationErrorRecord(
                "continuation_state.next_required_operation",
                "must be a recognized UFCPS operation",
            )
        )

    # The transition's validation flags describe checks; they do not create
    # truth on their own. They should, however, not contradict the fact that
    # this validator was reached only after schema validation.
    if validation.get("schema_valid") is False:
        findings.append(
            ValidationErrorRecord(
                "validation.schema_valid",
                "cannot be false for a transition that passes schema validation",
            )
        )

    if validation.get("continuation_valid") is False and continuation_required:
        findings.append(
            ValidationErrorRecord(
                "validation.continuation_valid",
                "cannot be false when continuation_required is true without an explicit blocked-state rationale",
            )
        )

    # Carrier type changes must be explained when they occur.
    if (
        source_carrier_type
        and destination_carrier_type
        and source_carrier_type != destination_carrier_type
    ):
        reason = carrier_transition.get("reason")
        if not reason:
            findings.append(
                ValidationErrorRecord(
                    "carrier_transition.reason",
                    "must explain a carrier-type change",
                )
            )

    return findings


def format_findings(findings: list[ValidationErrorRecord]) -> str:
    """Format validation findings for CLI output."""
    if not findings:
        return "VALID"

    lines = [f"INVALID: {len(findings)} finding(s)"]
    lines.extend(f"  - {finding}" for finding in findings)
    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Validate a UFCPS transition against schema and process invariants.",
    )
    parser.add_argument(
        "transition",
        type=Path,
        help="Path to the transition JSON instance.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/transition_v1.json"),
        help="Path to transition_v1.json (default: schemas/transition_v1.json).",
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
        instance = load_json(args.transition)
        schema = load_json(args.schema)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    schema_findings = validate_schema(instance, schema)

    if args.schema_only:
        findings = schema_findings
    else:
        semantic_findings: list[ValidationErrorRecord] = []
        if not schema_findings:
            semantic_findings = semantic_validate(instance)
        findings = schema_findings + semantic_findings

    print(format_findings(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
