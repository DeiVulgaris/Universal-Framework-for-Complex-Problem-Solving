#!/usr/bin/env python3
"""Native UFCPS adapter for a structured Semantic Core task tree.

The adapter is intentionally conservative:
- task-tree nodes become unresolved UQL questions;
- parent/child identity is preserved;
- no agent is assigned;
- no task is claimed;
- no scientific truth is established;
- execution results update UQL as candidate process information.

The module depends only on existing UFCPS UQL and Task Discovery primitives.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Iterable, Mapping, Optional, Sequence

from task_discovery_engine_v1 import discover
from uql_store_v1 import UQLStore


RESULT_CLASSES = {
    "solution",
    "partial",
    "negative",
    "contradiction",
    "inconclusive",
    "anomaly",
    "deadlock",
}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _task_nodes(task_tree: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = task_tree.get("tasks", [])
    if not isinstance(raw, list):
        raise ValueError("task_tree.tasks must be a list")
    return [node for node in raw if isinstance(node, Mapping)]


def validate_task_tree(task_tree: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    root_id = _text(task_tree.get("root_task_id"))
    nodes = _task_nodes(task_tree)
    by_task_id = {
        _text(node.get("task_id")): node
        for node in nodes
        if _text(node.get("task_id"))
    }

    if not root_id:
        errors.append("root_task_id_missing")
    elif root_id not in by_task_id:
        errors.append("root_task_not_found")

    if not nodes:
        errors.append("tasks_empty")

    for node in nodes:
        task_id = _text(node.get("task_id")) or "<missing>"
        for key in ("question_id", "formulation", "unresolved_difference", "next_required_operation"):
            if not _text(node.get(key)):
                errors.append(f"{task_id}:{key}_missing")

        if task_id != root_id and not _text(node.get("parent_task_id")):
            errors.append(f"{task_id}:parent_task_id_missing")

        if task_id != root_id and _text(node.get("parent_task_id")) not in by_task_id:
            errors.append(f"{task_id}:parent_task_not_found")

        if not _text(node.get("source_basis")):
            errors.append(f"{task_id}:source_basis_missing")

        provenance = _mapping(node.get("provenance"))
        if not provenance:
            errors.append(f"{task_id}:provenance_missing")

    return sorted(set(errors))


def _question_from_node(
    node: Mapping[str, Any],
    *,
    process_id: str,
) -> dict[str, Any]:
    required_resources = node.get("required_resources", [])
    if not isinstance(required_resources, list):
        required_resources = []

    metadata = {
        "bridge": "semantic_core_ufcps_v1",
        "task_id": _text(node.get("task_id")),
        "task_type": _text(node.get("task_type")),
        "parent_task_id": _text(node.get("parent_task_id")),
        "source_basis": _text(node.get("source_basis")),
        "provenance": dict(_mapping(node.get("provenance"))),
        "evidence_refs": _strings(node.get("evidence_refs")),
        "constraints": _strings(node.get("constraints")),
        "next_required_operation": _text(node.get("next_required_operation")).lower(),
        "required_capabilities": _strings(node.get("required_capabilities")),
    }

    return {
        "question_id": _text(node.get("question_id")),
        "process_id": process_id,
        "formulation": _text(node.get("formulation")),
        "unresolved_difference": _text(node.get("unresolved_difference")),
        "required_capabilities": _strings(node.get("required_capabilities")),
        "required_resources": [dict(item) for item in required_resources if isinstance(item, Mapping)],
        "metadata": metadata,
    }


def _patch_from_result(result: Mapping[str, Any]) -> dict[str, Any]:
    kind = _text(result.get("result_class")).lower()
    if kind not in RESULT_CLASSES:
        raise ValueError(f"unsupported result class: {kind}")

    content = _text(result.get("result_content"))
    unresolved = _text(result.get("unresolved_difference"))
    evidence = _strings(result.get("evidence_refs"))
    failed_paths = _strings(result.get("failed_paths"))
    operation = _text(result.get("next_required_operation")).lower() or "investigate"
    method = _text(result.get("method"))

    patch: dict[str, Any] = {
        "evidence_references": evidence,
        "next_required_operation": operation,
        "metadata": {
            "last_result_class": kind,
            "last_result_content": content,
            "result_provenance": dict(_mapping(result.get("provenance"))),
        },
    }

    if kind == "solution":
        patch["status"] = "unresolved"
        patch["results"] = [content] if content else []
        patch["uncertainty"] = "resolution candidate requires semantic validation"
    elif kind == "partial":
        patch["status"] = "unresolved"
        patch["results"] = [content] if content else []
        patch["unresolved_difference"] = unresolved
    elif kind == "negative":
        patch["status"] = "unresolved"
        patch["negative_results"] = [content] if content else []
        patch["unresolved_difference"] = unresolved
        patch["attempted_operations"] = list(dict.fromkeys(
            failed_paths + ([method] if method else [])
        ))
    elif kind == "contradiction":
        patch["status"] = "unresolved"
        patch["contradictions"] = [content] if content else []
        patch["unresolved_difference"] = unresolved or "branch results are incompatible"
    elif kind == "inconclusive":
        patch["status"] = "unresolved"
        patch["uncertainty"] = content
        patch["unresolved_difference"] = unresolved or "additional discriminating information is required"
    elif kind == "anomaly":
        patch["status"] = "unresolved"
        patch["observations"] = [content] if content else []
        patch["unresolved_difference"] = unresolved or "anomaly requires differentiation"
    elif kind == "deadlock":
        patch["status"] = "active"
        patch["unresolved_difference"] = unresolved or "current method cannot continue"
        patch["metadata"]["deadlock"] = content

    return patch


def import_task_tree(
    store: UQLStore,
    task_tree: Mapping[str, Any],
    *,
    process_id: str,
) -> dict[str, Any]:
    errors = validate_task_tree(task_tree)
    if errors:
        return {"status": "INVALID", "errors": errors, "created": [], "derived": []}

    nodes = _task_nodes(task_tree)
    root_task_id = _text(task_tree.get("root_task_id"))
    root_node = next(node for node in nodes if _text(node.get("task_id")) == root_task_id)
    created: list[str] = []
    derived: list[str] = []

    root_question_id = _text(root_node.get("question_id"))
    if root_question_id not in store.frontier:
        store.create_question(
            question_id=root_question_id,
            process_id=process_id,
            formulation=_text(root_node.get("formulation")),
            metadata={
                "bridge": "semantic_core_ufcps_v1",
                "task_id": root_task_id,
                "provenance": dict(_mapping(root_node.get("provenance"))),
                "source_basis": _text(root_node.get("source_basis")),
            },
            required_capabilities=_strings(root_node.get("required_capabilities")),
            required_resources=root_node.get("required_resources", [])
                if isinstance(root_node.get("required_resources", []), list) else [],
        )
        store.update_frontier(
            question_id=root_question_id,
            event_type="semantic_core_frontier_imported",
            patch={
                "unresolved_difference": _text(root_node.get("unresolved_difference")),
                "active_constraints": _strings(root_node.get("constraints")),
                "evidence_references": _strings(root_node.get("evidence_refs")),
                "next_required_operation": _text(root_node.get("next_required_operation")).lower(),
                "metadata": dict(_mapping(root_node.get("provenance"))),
            },
            process_id=process_id,
        )
        created.append(root_question_id)

    pending = [node for node in nodes if _text(node.get("task_id")) != root_task_id]
    while pending:
        progressed = False
        remaining: list[Mapping[str, Any]] = []
        for node in pending:
            parent_task_id = _text(node.get("parent_task_id"))
            parent = next(
                (candidate for candidate in nodes
                 if _text(candidate.get("task_id")) == parent_task_id),
                None,
            )
            if parent is None:
                remaining.append(node)
                continue

            parent_question_id = _text(parent.get("question_id"))
            question_id = _text(node.get("question_id"))

            if question_id not in store.frontier:
                store.derive_question(
                    parent_question_id=parent_question_id,
                    child_question_id=question_id,
                    formulation=_text(node.get("formulation")),
                    process_id=process_id,
                    unresolved_difference=_text(node.get("unresolved_difference")),
                    metadata={
                        "bridge": "semantic_core_ufcps_v1",
                        "task_id": _text(node.get("task_id")),
                        "task_type": _text(node.get("task_type")),
                        "source_basis": _text(node.get("source_basis")),
                        "constraints": _strings(node.get("constraints")),
                        "evidence_refs": _strings(node.get("evidence_refs")),
                        "required_capabilities": _strings(node.get("required_capabilities")),
                        "required_resources": node.get("required_resources", [])
                            if isinstance(node.get("required_resources", []), list) else [],
                        "next_required_operation": _text(node.get("next_required_operation")).lower(),
                        "provenance": dict(_mapping(node.get("provenance"))),
                        "depends_on": _strings(node.get("depends_on")),
                    },
                )
                store.update_frontier(
                    question_id=question_id,
                    event_type="semantic_core_task_imported",
                    patch={
                        "active_constraints": _strings(node.get("constraints")),
                        "evidence_references": _strings(node.get("evidence_refs")),
                        "required_capabilities": _strings(node.get("required_capabilities")),
                        "required_resources": node.get("required_resources", [])
                            if isinstance(node.get("required_resources", []), list) else [],
                        "next_required_operation": _text(node.get("next_required_operation")).lower(),
                        "metadata": {
                            **dict(_mapping(node.get("provenance"))),
                            "bridge_task_type": _text(node.get("task_type")),
                            "depends_on": _strings(node.get("depends_on")),
                        },
                    },
                    process_id=process_id,
                )
                derived.append(question_id)
            progressed = True

        if not progressed:
            unresolved_ids = sorted(_text(node.get("task_id")) for node in remaining)
            return {
                "status": "BLOCKED",
                "errors": [f"unmaterialized_tasks:{','.join(unresolved_ids)}"],
                "created": created,
                "derived": derived,
            }
        pending = remaining

    return {
        "status": "READY",
        "errors": [],
        "created": created,
        "derived": derived,
        "question_ids": created + derived,
    }


def _discovery_question(frontier: Mapping[str, Any]) -> dict[str, Any]:
    """Map UQL frontier field names to Task Discovery Engine vocabulary."""
    metadata = _mapping(frontier.get("metadata"))
    return {
        "question_id": _text(frontier.get("question_id")),
        "formulation": _text(frontier.get("formulation")),
        "status": _text(frontier.get("status", "unresolved")).lower() or "unresolved",
        "current_state": json.dumps(
            _mapping(frontier.get("current_state")), ensure_ascii=False, sort_keys=True
        ) if isinstance(frontier.get("current_state"), Mapping) else _text(frontier.get("current_state")),
        "current_frontier": _text(frontier.get("current_state")),
        "unresolved_difference": _text(frontier.get("unresolved_difference")),
        "known_constraints": list(frontier.get("active_constraints", [])),
        "previous_attempts": list(frontier.get("attempted_operations", [])),
        "evidence_references": list(frontier.get("evidence_references", [])),
        "required_capabilities": list(frontier.get("required_capabilities", [])),
        "requirements": {"resources": list(frontier.get("required_resources", []))},
        "next_required_operation": _text(frontier.get("next_required_operation")),
        "prospect_signals": metadata.get("prospect_signals", {}),
        "continuation": {
            "required": True,
            "unresolved_difference": _text(frontier.get("unresolved_difference")),
            "next_required_operation": _text(frontier.get("next_required_operation")),
        },
        "provenance": metadata.get("provenance", {}),
        "task_id": metadata.get("task_id"),
    }


def discover_imported_tasks(
    store: UQLStore,
    *,
    agents: Iterable[Mapping[str, Any]],
    resources: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    questions = [_discovery_question(frontier) for frontier in store.list_active()]
    prospects = discover(questions, agents, resources)
    return [prospect.to_dict() for prospect in prospects]


def apply_execution_result(
    store: UQLStore,
    *,
    question_id: str,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    patch = _patch_from_result(result)

    # Keep the result itself as an append-only event even where the frontier
    # fields already capture a summary.
    store.append_history(
        question_id=question_id,
        event_type="semantic_core_execution_result",
        payload={
            "result_class": _text(result.get("result_class")).lower(),
            "result_content": _text(result.get("result_content")),
            "evidence_refs": _strings(result.get("evidence_refs")),
            "provenance": dict(_mapping(result.get("provenance"))),
        },
    )

    # Only apply patch fields that are authoritative UFCPS frontier fields.
    allowed = {
        "status", "unresolved_difference", "active_constraints",
        "attempted_operations", "observations", "results", "negative_results",
        "contradictions", "uncertainty", "evidence_references",
        "next_required_operation", "metadata",
    }
    current = store.get_frontier(question_id).to_dict()
    filtered = {key: value for key, value in patch.items() if key in allowed}

    if "attempted_operations" in filtered:
        filtered["attempted_operations"] = list(dict.fromkeys(
            list(current.get("attempted_operations", [])) + list(filtered["attempted_operations"])
        ))
    for field in ("evidence_references", "results", "negative_results", "contradictions", "observations"):
        if field in filtered:
            filtered[field] = list(dict.fromkeys(
                list(current.get(field, [])) + list(filtered[field])
            ))
    if "metadata" in filtered:
        filtered["metadata"] = {
            **dict(current.get("metadata", {})),
            **dict(filtered["metadata"]),
        }

    store.update_frontier(
        question_id=question_id,
        event_type="execution_result_frontier_update",
        patch=filtered,
    )

    return {
        "status": "FRONTIER_UPDATED",
        "question_id": question_id,
        "result_class": _text(result.get("result_class")).lower(),
        "patch": filtered,
        "semantic_validation_required": True,
    }


def demo() -> dict[str, Any]:
    """Demonstrate import, discovery shaping and result preservation."""
    import tempfile
    from pathlib import Path

    task_tree = {
        "root_task_id": "TASK-Q-DEMO-ROOT",
        "tasks": [
            {
                "task_id": "TASK-Q-DEMO-ROOT",
                "question_id": "Q-DEMO",
                "parent_task_id": None,
                "formulation": "Investigate an unresolved process boundary.",
                "unresolved_difference": "Current method does not yield a successor.",
                "next_required_operation": "investigate",
                "task_type": "primary",
                "source_basis": "unresolved_difference",
                "constraints": ["preserve invariant"],
                "evidence_refs": ["core:frontier-demo"],
                "required_capabilities": ["analysis"],
                "required_resources": [],
                "provenance": {"source_repository": "metamonism-semantic-core", "derivation_mode": "FORMALIZATION"},
            },
            {
                "task_id": "TASK-Q-DEMO-BOUNDARY",
                "question_id": "Q-DEMO:BOUNDARY",
                "parent_task_id": "TASK-Q-DEMO-ROOT",
                "formulation": "Identify missing boundary information.",
                "unresolved_difference": "Boundary information is insufficient.",
                "next_required_operation": "investigate",
                "task_type": "investigation",
                "source_basis": "evidence_gap",
                "constraints": ["preserve invariant"],
                "evidence_refs": ["core:frontier-demo"],
                "required_capabilities": ["analysis"],
                "required_resources": [],
                "provenance": {"source_repository": "metamonism-semantic-core", "derivation_mode": "FORMALIZATION"},
            },
        ],
    }

    with tempfile.TemporaryDirectory() as directory:
        store = UQLStore(Path(directory) / "uql")
        imported = import_task_tree(store, task_tree, process_id="P-DEMO")
        prospects = discover_imported_tasks(
            store,
            agents=[{"agent_id": "A-DEMO", "capabilities": ["analysis"]}],
            resources=[],
        )
        result = apply_execution_result(
            store,
            question_id="Q-DEMO:BOUNDARY",
            result={
                "result_class": "negative",
                "result_content": "Current method did not distinguish the boundary.",
                "method": "boundary_probe_v1",
                "unresolved_difference": "Which new observation discriminates the boundary?",
                "evidence_refs": ["run-demo-negative"],
                "provenance": {"source": "ufcps-demo", "status": "PROCESS_INFORMATION"},
            },
        )
        frontier = store.get_frontier("Q-DEMO:BOUNDARY").to_dict()
        assert imported["status"] == "READY"
        assert len(imported["derived"]) == 1
        assert prospects
        assert result["semantic_validation_required"] is True
        assert "boundary_probe_v1" in frontier["attempted_operations"]
        assert frontier["status"] == "unresolved"

        return {
            "imported": imported,
            "prospects": prospects,
            "result_update": result,
            "frontier_after_result": frontier,
        }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    if not args.demo:
        parser.print_help()
        return 0
    data = demo()
    print(json.dumps(data, ensure_ascii=False, indent=2) if args.as_json else
          f"import={data['imported']['status']} prospects={len(data['prospects'])} result={data['result_update']['result_class']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
