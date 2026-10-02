#!/usr/bin/env python3
"""Tests for the Semantic Core Stage 61 localized-frontier bridge."""

from pathlib import Path
import tempfile

from invariant_replay_frontier_bridge_v1 import apply_localized_frontier
from uql_store_v1 import UQLStore


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = UQLStore(Path(directory) / "uql")
        store.create_question(
            question_id="Q-61-TEST",
            process_id="P-61-TEST",
            formulation="Test replay localization.",
        )

        localized = {
            "frontier_id": "FR61-TEST",
            "question_id": "Q-61-TEST",
            "root_invariant_id": "ROOT",
            "trace_id": "TRACE-61-TEST",
            "anchor_step_id": "S2",
            "impact_mode": "EXPLICIT_STEP_REFERENCE",
            "reasoning_prefix": ["S1", "S2"],
            "affected_step": {"step_id": "S2"},
            "downstream_steps": [{"step_id": "S3", "replay_status": "REQUIRES_REPLAY"}],
            "information_result": {"result_class": "EVIDENCE_FOUND"},
            "next_required_operation": "validate_evidence_against_registered_chain",
            "provenance": {"stage": "61"},
        }

        result = apply_localized_frontier(
            store,
            localized,
            unresolved_difference="Validate the affected derivation step.",
        )
        assert result["status"] == "FRONTIER_REOPENED"
        frontier = store.get_frontier("Q-61-TEST")
        assert frontier.current_procedural_unit == "S2"
        assert frontier.next_required_operation == "validate_evidence_against_registered_chain"
        assert frontier.unresolved_difference == "Validate the affected derivation step."
        assert frontier.metadata["semantic_replay"]["root_invariant_id"] == "ROOT"

        events = store.events_for_question("Q-61-TEST")
        assert any(
            event.event_type == "semantic_core_reasoning_replay"
            for event in events
        )

        invalid = apply_localized_frontier(
            store,
            {**localized, "question_id": "UNKNOWN"},
        )
        assert invalid["status"] == "BLOCKED"
        assert "unknown_question_id:UNKNOWN" in invalid["errors"]

        print("Stage 61 UFCPS bridge tests: PASS")


if __name__ == "__main__":
    main()
