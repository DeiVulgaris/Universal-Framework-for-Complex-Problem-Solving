#!/usr/bin/env python3
"""UFCPS information-space adapter.

Consumes provider-neutral query plans produced by the Semantic Core and
records retrieval envelopes into the UFCPS UQL.

The module does not perform network access. A provider adapter can submit the
returned request objects to web, literature, repository, dataset, or other
information systems.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Iterable, Mapping, Sequence

from uql_store_v1 import UQLStore

VALID_INTENTS = {
    "SOLUTION_DISCOVERY",
    "METHOD_DISCOVERY",
    "EVIDENCE_DISCOVERY",
    "CONTRADICTION_CHECK",
    "INFORMATION_GAP",
    "PRECEDENT_DISCOVERY",
    "SOURCE_VALIDATION",
}
VALID_RETRIEVAL = {"FOUND", "NOT_FOUND", "PARTIAL", "ERROR"}
VALID_RELEVANCE = {"UNKNOWN", "LOW", "MEDIUM", "HIGH"}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [_text(value)] if _text(value) else []
    if not isinstance(value, list):
        return []
    return [_text(x) for x in value if _text(x)]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def validate_query_plan(plan: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("query_plan_id", "frontier_id", "question_id"):
        if not _text(plan.get(key)):
            errors.append(f"{key}_missing")

    queries = plan.get("queries")
    if not isinstance(queries, list) or not queries:
        errors.append("queries_missing")

    intents = plan.get("intents")
    if not isinstance(intents, list) or not intents:
        errors.append("intents_missing")
    else:
        for intent in intents:
            if _text(intent).upper() not in VALID_INTENTS:
                errors.append(f"invalid_intent:{_text(intent)}")

    provenance = _mapping(plan.get("provenance"))
    if not provenance:
        errors.append("provenance_missing")

    return sorted(set(errors))


def prepare_requests(plan: Mapping[str, Any]) -> dict[str, Any]:
    errors = validate_query_plan(plan)
    if errors:
        return {
            "status": "INVALID",
            "requests": [],
            "errors": errors,
            "query_plan_id": _text(plan.get("query_plan_id")),
        }

    requests: list[dict[str, Any]] = []
    for query in plan["queries"]:
        if not isinstance(query, Mapping):
            continue
        intent = _text(query.get("intent")).upper()
        query_id = _text(query.get("query_id"))
        query_text = _text(query.get("text"))
        if intent not in VALID_INTENTS or not query_id or not query_text:
            continue
        requests.append({
            "query_id": query_id,
            "query_plan_id": _text(plan["query_plan_id"]),
            "question_id": _text(plan["question_id"]),
            "intent": intent,
            "text": query_text,
            "target_difference": _text(query.get("target_difference")),
            "source_classes": _strings(plan.get("source_classes")),
            "constraints": _strings(plan.get("constraints")),
            "exclusions": _strings(query.get("exclusions")),
            "provenance": dict(_mapping(plan.get("provenance"))),
        })

    return {
        "status": "READY",
        "requests": requests,
        "errors": [],
    }


def validate_retrieval_envelope(envelope: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in (
        "retrieval_id", "query_id", "locator",
        "content_reference", "retrieval_status",
    ):
        if not _text(envelope.get(key)):
            errors.append(f"{key}_missing")

    status = _text(envelope.get("retrieval_status")).upper()
    if status not in VALID_RETRIEVAL:
        errors.append("invalid_retrieval_status")

    relevance = _text(envelope.get("relevance")).upper()
    if relevance and relevance not in VALID_RELEVANCE:
        errors.append("invalid_relevance")

    if not _mapping(envelope.get("source")):
        errors.append("source_missing")

    if not _mapping(envelope.get("provenance")):
        errors.append("provenance_missing")

    return sorted(set(errors))


def ingest_retrievals(
    store: UQLStore,
    *,
    question_id: str,
    envelopes: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    accepted: list[str] = []
    errors: list[str] = []
    evidence_refs: list[str] = []
    observations: list[str] = []

    for envelope in envelopes:
        validation = validate_retrieval_envelope(envelope)
        if validation:
            errors.extend(validation)
            continue

        retrieval_id = _text(envelope["retrieval_id"])
        query_id = _text(envelope["query_id"])
        status = _text(envelope["retrieval_status"]).upper()
        relevance = _text(envelope.get("relevance", "UNKNOWN")).upper()
        source = _mapping(envelope["source"])
        locator = _text(envelope["locator"])
        content_reference = _text(envelope["content_reference"])

        store.append_history(
            question_id=question_id,
            event_type="information_retrieved",
            payload={
                "retrieval_id": retrieval_id,
                "query_id": query_id,
                "retrieval_status": status,
                "relevance": relevance,
                "source": dict(source),
                "locator": locator,
                "content_reference": content_reference,
                "provenance": dict(_mapping(envelope["provenance"])),
            },
        )

        if status in {"FOUND", "PARTIAL"}:
            evidence_ref = f"retrieval:{retrieval_id}"
            evidence_refs.append(evidence_ref)
        observations.append(
            f"{query_id}: {status} ({relevance}) from {locator}"
        )
        accepted.append(retrieval_id)

    if accepted:
        current = store.get_frontier(question_id).to_dict()
        merged_evidence = list(dict.fromkeys(
            list(current.get("evidence_references", [])) + evidence_refs
        ))
        merged_observations = list(dict.fromkeys(
            list(current.get("observations", [])) + observations
        ))
        store.update_frontier(
            question_id=question_id,
            event_type="information_space_frontier_update",
            patch={
                "evidence_references": merged_evidence,
                "observations": merged_observations,
                "metadata": {
                    **dict(current.get("metadata", {})),
                    "information_space": {
                        "retrieval_count": len(accepted),
                        "last_retrieval_ids": accepted,
                    },
                },
            },
        )

    return {
        "status": "UPDATED" if accepted else "NO_VALID_RETRIEVALS",
        "question_id": question_id,
        "accepted_retrieval_ids": accepted,
        "errors": errors,
    }


def information_state(store: UQLStore, question_id: str) -> dict[str, Any]:
    frontier = store.get_frontier(question_id).to_dict()
    metadata = _mapping(frontier.get("metadata"))
    info = _mapping(metadata.get("information_space"))
    return {
        "question_id": question_id,
        "evidence_references": list(frontier.get("evidence_references", [])),
        "observations": list(frontier.get("observations", [])),
        "information_space": dict(info),
        "next_required_operation": _text(frontier.get("next_required_operation")),
        "unresolved_difference": _text(frontier.get("unresolved_difference")),
    }


def demo() -> dict[str, Any]:
    import tempfile
    from pathlib import Path

    plan = {
        "query_plan_id": "QPLAN-DEMO",
        "frontier_id": "FR-DEMO",
        "question_id": "Q-DEMO",
        "intents": ["SOLUTION_DISCOVERY", "INFORMATION_GAP"],
        "queries": [
            {
                "query_id": "QRY-DEMO-01",
                "intent": "SOLUTION_DISCOVERY",
                "text": "Existing solutions for the unresolved problem.",
                "target_difference": "candidate solution unknown",
            },
            {
                "query_id": "QRY-DEMO-02",
                "intent": "INFORMATION_GAP",
                "text": "What additional information discriminates the alternatives?",
                "target_difference": "discriminating information unknown",
            },
        ],
        "constraints": ["preserve invariant"],
        "source_classes": ["web", "literature", "code_repository"],
        "provenance": {
            "source_repository": "metamonism-semantic-core",
            "source_reference": "stage58",
            "derivation_mode": "FORMALIZATION",
        },
    }

    with tempfile.TemporaryDirectory() as directory:
        store = UQLStore(Path(directory) / "uql")
        store.create_question(
            question_id="Q-DEMO",
            process_id="P-DEMO",
            formulation="Investigate unresolved problem.",
        )
        prepared = prepare_requests(plan)
        ingested = ingest_retrievals(
            store,
            question_id="Q-DEMO",
            envelopes=[
                {
                    "retrieval_id": "RET-001",
                    "query_id": "QRY-DEMO-01",
                    "source": {"type": "literature", "name": "demo-source"},
                    "locator": "demo://source/1",
                    "content_reference": "demo-content-1",
                    "retrieval_status": "FOUND",
                    "relevance": "HIGH",
                    "provenance": {"provider": "demo"},
                },
                {
                    "retrieval_id": "RET-002",
                    "query_id": "QRY-DEMO-02",
                    "source": {"type": "web", "name": "demo-source"},
                    "locator": "demo://source/2",
                    "content_reference": "demo-content-2",
                    "retrieval_status": "NOT_FOUND",
                    "relevance": "UNKNOWN",
                    "provenance": {"provider": "demo"},
                },
            ],
        )
        state = information_state(store, "Q-DEMO")
        assert prepared["status"] == "READY"
        assert len(prepared["requests"]) == 2
        assert ingested["status"] == "UPDATED"
        assert len(state["evidence_references"]) == 2
        return {"prepared": prepared, "ingested": ingested, "state": state}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    if args.demo:
        data = demo()
        print(json.dumps(data, ensure_ascii=False, indent=2) if args.as_json else
              f"requests={len(data['prepared']['requests'])} accepted={len(data['ingested']['accepted_retrieval_ids'])}")
