#!/usr/bin/env python3
"""Tests for the UFCPS Stage 59 information provider runtime."""

from pathlib import Path
import tempfile

from http_json_provider_v1 import HttpJsonProvider
from information_provider_runtime_v1 import (
    InformationProviderRegistry,
    InMemoryInformationProvider,
    dispatch_requests,
    run_preflight,
)
from local_corpus_provider_v1 import LocalCorpusProvider
from uql_store_v1 import UQLStore


def _plan() -> dict:
    return {
        "query_plan_id": "QPLAN-TEST-59",
        "frontier_id": "FR-TEST-59",
        "question_id": "Q-TEST-59",
        "intents": ["SOLUTION_DISCOVERY", "INFORMATION_GAP"],
        "queries": [
            {
                "query_id": "QRY-TEST-59-01",
                "intent": "SOLUTION_DISCOVERY",
                "text": "Find the existing solution.",
                "target_difference": "candidate solution unknown",
            },
            {
                "query_id": "QRY-TEST-59-02",
                "intent": "INFORMATION_GAP",
                "text": "Find missing information.",
                "target_difference": "information gap unknown",
            },
        ],
        "constraints": ["preserve invariant"],
        "source_classes": ["web"],
        "provenance": {"source": "semantic-core", "stage": "59"},
    }


def main() -> None:
    provider = InMemoryInformationProvider([
        {
            "query_id": "QRY-TEST-59-01",
            "locator": "demo://web/solution",
            "content": "documented solution candidate",
            "relevance": "HIGH",
            "source": {"name": "fixture-web", "type": "web"},
        }
    ])
    registry = InformationProviderRegistry()
    registry.register(provider, source_classes=["web"])

    envelopes = dispatch_requests(
        [
            {
                "query_id": "QRY-X",
                "query_plan_id": "QPLAN-X",
                "question_id": "Q-X",
                "intent": "SOLUTION_DISCOVERY",
                "text": "find",
                "source_classes": ["web", "literature"],
                "constraints": [],
                "exclusions": [],
                "provenance": {"stage": "59"},
            }
        ],
        registry,
    )
    assert {item["retrieval_status"] for item in envelopes} == {"ERROR", "NOT_FOUND"}

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "source.md").write_text(
            "Orthogonal resolution preserves an invariant and changes the "
            "continuation mode.\n",
            encoding="utf-8",
        )
        local = LocalCorpusProvider(root)
        local_results = local.search({
            "text": "orthogonal resolution",
            "target_difference": "continuation mode",
        })
        assert local_results
        assert local_results[0]["locator"].startswith("file:")

        fake_payload = {
            "results": [{
                "locator": "https://example.test/result",
                "title": "Fixture",
                "snippet": "Fixture result",
                "relevance": "MEDIUM",
            }]
        }

        def fake_transport(url, headers, timeout):
            assert "q=Find" in url
            assert headers["Accept"] == "application/json"
            assert timeout == 7
            return fake_payload

        http = HttpJsonProvider(
            "https://example.test/search",
            source_class="web",
            timeout_seconds=7,
            transport=fake_transport,
        )
        http_results = http.search({"text": "Find", "intent": "EVIDENCE_DISCOVERY"})
        assert len(http_results) == 1
        assert http_results[0]["locator"].startswith("https://")

        store = UQLStore(root / "uql")
        store.create_question(
            question_id="Q-TEST-59",
            process_id="P-TEST-59",
            formulation="Test information preflight.",
        )
        result = run_preflight(
            store,
            question_id="Q-TEST-59",
            plan=_plan(),
            registry=registry,
        )
        assert result["status"] == "COMPLETED"
        assert result["ingestion"]["status"] == "UPDATED"
        state = store.get_frontier("Q-TEST-59")
        assert state.evidence_references
        assert state.evidence_references[0].startswith("retrieval:")

        completed = [
            event for event in store.events_for_question("Q-TEST-59")
            if event.event_type == "information_preflight_completed"
        ]
        assert len(completed) == 1


if __name__ == "__main__":
    main()
