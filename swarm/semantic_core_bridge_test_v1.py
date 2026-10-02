#!/usr/bin/env python3
"""Smoke tests for the native Semantic Core ↔ UFCPS bridge."""

from __future__ import annotations

import tempfile
from pathlib import Path

from semantic_core_bridge_v1 import (
    apply_execution_result,
    discover_imported_tasks,
    import_task_tree,
)
from uql_store_v1 import UQLStore


def build_task_tree():
    return {
        "root_task_id": "TASK-Q-TEST-ROOT",
        "tasks": [
            {
                "task_id": "TASK-Q-TEST-ROOT",
                "question_id": "Q-TEST",
                "parent_task_id": None,
                "formulation": "Investigate an unresolved difference.",
                "unresolved_difference": "Current path does not resolve the frontier.",
                "next_required_operation": "investigate",
                "task_type": "primary",
                "source_basis": "unresolved_difference",
                "constraints": ["preserve invariant"],
                "evidence_refs": ["core:test"],
                "required_capabilities": ["analysis"],
                "required_resources": [],
                "provenance": {
                    "source_repository": "metamonism-semantic-core",
                    "source_reference": "test",
                    "derivation_mode": "FORMALIZATION",
                },
            },
            {
                "task_id": "TASK-Q-TEST-A",
                "question_id": "Q-TEST:A",
                "parent_task_id": "TASK-Q-TEST-ROOT",
                "formulation": "Identify the missing distinction.",
                "unresolved_difference": "The discriminating distinction is unknown.",
                "next_required_operation": "investigate",
                "task_type": "investigation",
                "source_basis": "evidence_gap",
                "constraints": ["preserve invariant"],
                "evidence_refs": ["core:test"],
                "required_capabilities": ["analysis"],
                "required_resources": [],
                "provenance": {
                    "source_repository": "metamonism-semantic-core",
                    "source_reference": "test",
                    "derivation_mode": "FORMALIZATION",
                },
            },
        ],
    }


def main():
    with tempfile.TemporaryDirectory() as directory:
        store = UQLStore(Path(directory) / "uql")
        imported = import_task_tree(store, build_task_tree(), process_id="P-TEST")
        assert imported["status"] == "READY"
        assert imported["created"] == ["Q-TEST"]
        assert imported["derived"] == ["Q-TEST:A"]

        prospects = discover_imported_tasks(
            store,
            agents=[{"agent_id": "A-TEST", "capabilities": ["analysis"]}],
            resources=[],
        )
        child = next(p for p in prospects if p["question_id"] == "Q-TEST:A")
        assert "preserve invariant" in child["known_constraints"]
        assert "analysis" in child["required_capabilities"]

        update = apply_execution_result(
            store,
            question_id="Q-TEST:A",
            result={
                "result_class": "negative",
                "result_content": "The attempted probe did not distinguish the alternatives.",
                "method": "probe_v1",
                "unresolved_difference": "Which observation distinguishes the alternatives?",
                "evidence_refs": ["run:test-negative"],
                "provenance": {"source": "ufcps-test", "status": "PROCESS_INFORMATION"},
            },
        )
        assert update["status"] == "FRONTIER_UPDATED"
        frontier = store.get_frontier("Q-TEST:A").to_dict()
        assert frontier["status"] == "unresolved"
        assert "probe_v1" in frontier["attempted_operations"]
        assert frontier["negative_results"]


if __name__ == "__main__":
    main()
