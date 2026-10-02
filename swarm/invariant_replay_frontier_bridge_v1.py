#!/usr/bin/env python3
"""UFCPS adapter for an impact-localized Semantic Core reasoning frontier."""

from __future__ import annotations

import argparse
import json
from typing import Any, Mapping, Sequence

from uql_store_v1 import UQLStore


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [_text(value)] if _text(value) else []
    if not isinstance(value, list):
        return []
    return [_text(x) for x in value if _text(x)]


def validate_localized_frontier(frontier: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in (
        "frontier_id", "question_id", "root_invariant_id",
        "trace_id", "anchor_step_id", "impact_mode",
        "reasoning_prefix", "affected_step", "downstream_steps",
        "information_result", "next_required_operation", "provenance",
    ):
        if key not in frontier:
            errors.append(f"{key}_missing")

    if frontier.get("impact_mode") not in {"EXPLICIT_STEP_REFERENCE", "TAIL_FALLBACK"}:
        errors.append("invalid_impact_mode")
    if not _text(frontier.get("question_id")):
        errors.append("question_id_empty")
    if not _text(frontier.get("anchor_step_id")):
        errors.append("anchor_step_id_empty")
    if not isinstance(frontier.get("reasoning_prefix"), list) or not frontier.get("reasoning_prefix"):
        errors.append("reasoning_prefix_invalid")
    if not _mapping(frontier.get("affected_step")):
        errors.append("affected_step_invalid")
    if not isinstance(frontier.get("downstream_steps"), list):
        errors.append("downstream_steps_invalid")
    if not _mapping(frontier.get("information_result")):
        errors.append("information_result_invalid")
    if not _mapping(frontier.get("provenance")):
        errors.append("provenance_invalid")
    return sorted(set(errors))


def apply_localized_frontier(
    store: UQLStore,
    localized: Mapping[str, Any],
    *,
    unresolved_difference: str | None = None,
) -> dict[str, Any]:
    errors = validate_localized_frontier(localized)
    if errors:
        return {"status": "INVALID", "errors": errors}

    question_id = _text(localized["question_id"])
    if question_id not in store.frontier:
        return {"status": "BLOCKED", "errors": [f"unknown_question_id:{question_id}"]}

    current = store.get_frontier(question_id).to_dict()
    anchor = dict(_mapping(localized["affected_step"]))
    information = dict(_mapping(localized["information_result"]))

    metadata = {
        **dict(current.get("metadata", {})),
        "semantic_replay": {
            "trace_id": _text(localized["trace_id"]),
            "root_invariant_id": _text(localized["root_invariant_id"]),
            "anchor_step_id": _text(localized["anchor_step_id"]),
            "impact_mode": _text(localized["impact_mode"]),
            "reasoning_prefix": _strings(localized.get("reasoning_prefix")),
            "affected_step": anchor,
            "downstream_steps": localized.get("downstream_steps", []),
            "information_result": information,
        },
    }

    patch: dict[str, Any] = {
        "current_procedural_unit": _text(localized["anchor_step_id"]),
        "next_required_operation": _text(localized["next_required_operation"]).lower(),
        "metadata": metadata,
    }
    if unresolved_difference and unresolved_difference.strip():
        patch["unresolved_difference"] = unresolved_difference.strip()

    event = store.update_frontier(
        question_id=question_id,
        event_type="semantic_core_impact_localized_frontier",
        patch=patch,
    )

    store.append_history(
        question_id=question_id,
        event_type="semantic_core_reasoning_replay",
        payload={
            "trace_id": _text(localized["trace_id"]),
            "root_invariant_id": _text(localized["root_invariant_id"]),
            "anchor_step": anchor,
            "reasoning_prefix": _strings(localized.get("reasoning_prefix")),
            "downstream_steps": localized.get("downstream_steps", []),
            "information_result": information,
            "impact_mode": _text(localized["impact_mode"]),
            "provenance": dict(_mapping(localized["provenance"])),
        },
    )

    return {
        "status": "FRONTIER_REOPENED",
        "question_id": question_id,
        "anchor_step_id": _text(localized["anchor_step_id"]),
        "current_procedural_unit": _text(localized["anchor_step_id"]),
        "next_required_operation": _text(localized["next_required_operation"]).lower(),
        "event_id": event.event_id,
    }


def demo() -> dict[str, Any]:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        store = UQLStore(Path(directory) / "uql")
        store.create_question(
            question_id="Q-61-DEMO",
            process_id="P-61-DEMO",
            formulation="Test localized replay frontier.",
        )
        localized = {
            "frontier_id": "FR61-DEMO",
            "question_id": "Q-61-DEMO",
            "root_invariant_id": "ROOT",
            "trace_id": "TRACE-61-DEMO",
            "anchor_step_id": "S3",
            "impact_mode": "EXPLICIT_STEP_REFERENCE",
            "reasoning_prefix": ["S1", "S2", "S3"],
            "affected_step": {"step_id": "S3", "information_effect": "REQUIRES_RECONCILIATION"},
            "downstream_steps": [{"step_id": "S4", "replay_status": "REQUIRES_REPLAY"}],
            "information_result": {"result_class": "CONTRADICTION_FOUND"},
            "next_required_operation": "reconcile_or_test_affected_step",
            "provenance": {"stage": "61"},
        }
        result = apply_localized_frontier(
            store,
            localized,
            unresolved_difference="Which constraint explains the contradiction?",
        )
        frontier = store.get_frontier("Q-61-DEMO")
        assert result["status"] == "FRONTIER_REOPENED"
        assert frontier.current_procedural_unit == "S3"
        assert frontier.unresolved_difference == "Which constraint explains the contradiction?"
        assert frontier.metadata["semantic_replay"]["root_invariant_id"] == "ROOT"
        return {"status": "PASS", "frontier": frontier.to_dict()}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    if not args.demo:
        parser.print_help()
        return 0
    result = demo()
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.as_json else
          f"status={result['status']} anchor={result['frontier']['current_procedural_unit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
