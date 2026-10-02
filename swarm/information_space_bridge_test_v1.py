#!/usr/bin/env python3
"""Smoke tests for the UFCPS information-space bridge."""

from pathlib import Path
import tempfile

from information_space_bridge_v1 import (
    ingest_retrievals,
    information_state,
    prepare_requests,
)
from uql_store_v1 import UQLStore


def main() -> None:
    plan = {
        "query_plan_id": "QPLAN-TEST",
        "frontier_id": "FR-TEST",
        "question_id": "Q-TEST",
        "intents": ["SOLUTION_DISCOVERY"],
        "queries": [{
            "query_id": "QRY-TEST-01",
            "intent": "SOLUTION_DISCOVERY",
            "text": "Find existing solutions.",
        }],
        "constraints": [],
        "source_classes": ["web"],
        "provenance": {"source": "semantic-core", "stage": "58"},
    }

    with tempfile.TemporaryDirectory() as directory:
        store = UQLStore(Path(directory) / "uql")
        store.create_question(
            question_id="Q-TEST",
            process_id="P-TEST",
            formulation="Test information lookup.",
        )

        prepared = prepare_requests(plan)
        assert prepared["status"] == "READY"
        assert len(prepared["requests"]) == 1

        ingested = ingest_retrievals(
            store,
            question_id="Q-TEST",
            envelopes=[{
                "retrieval_id": "RET-TEST-01",
                "query_id": "QRY-TEST-01",
                "source": {"type": "web", "name": "test"},
                "locator": "https://example.invalid/result",
                "content_reference": "test-content",
                "retrieval_status": "FOUND",
                "relevance": "HIGH",
                "provenance": {"provider": "test"},
            }],
        )
        assert ingested["status"] == "UPDATED"
        state = information_state(store, "Q-TEST")
        assert "retrieval:RET-TEST-01" in state["evidence_references"]


if __name__ == "__main__":
    main()
