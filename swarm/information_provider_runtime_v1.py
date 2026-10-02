#!/usr/bin/env python3
"""UFCPS Stage 59 information provider runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from information_space_bridge_v1 import ingest_retrievals, prepare_requests
from uql_store_v1 import UQLStore

VALID_RETRIEVAL = {"FOUND", "NOT_FOUND", "PARTIAL", "ERROR"}
VALID_RELEVANCE = {"UNKNOWN", "LOW", "MEDIUM", "HIGH"}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [_text(value)] if _text(value) else []
    if not isinstance(value, list):
        return []
    return [_text(v) for v in value if _text(v)]


def _retrieval_id(query_id: str, provider_name: str, source_class: str, locator: str) -> str:
    seed = "|".join([query_id, provider_name, source_class, locator])
    return "RET-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]


class InformationProviderRegistry:
    """Resolve providers by source class without hard-coding vendors."""

    def __init__(self) -> None:
        self._providers: dict[str, Any] = {}

    def register(self, provider: Any, *, source_classes: Sequence[str] | None = None) -> None:
        classes = source_classes or getattr(provider, "source_classes", ())
        if not classes:
            raise ValueError("provider must declare at least one source class")
        for source_class in classes:
            key = _text(source_class)
            if not key:
                raise ValueError("source class must not be empty")
            if key in self._providers and self._providers[key] is not provider:
                raise ValueError(f"provider already registered for source class: {key}")
            self._providers[key] = provider

    def resolve(self, source_class: str) -> Any | None:
        return self._providers.get(_text(source_class))

    def coverage(self, source_classes: Iterable[str]) -> dict[str, bool]:
        return {
            _text(source_class): self.resolve(source_class) is not None
            for source_class in source_classes
            if _text(source_class)
        }


class InMemoryInformationProvider:
    """Deterministic provider used for runtime tests and demonstrations."""

    name = "in-memory-v1"
    source_classes = ("web", "literature", "code_repository", "dataset")

    def __init__(self, records: Iterable[Mapping[str, Any]]) -> None:
        self.records = [dict(record) for record in records]

    def search(self, request: Mapping[str, Any], *, max_results: int = 5) -> list[dict[str, Any]]:
        query_id = _text(request.get("query_id"))
        matched = [
            dict(record)
            for record in self.records
            if not _text(record.get("query_id")) or record.get("query_id") == query_id
        ]
        return matched[:max_results]


def _fallback_locator(*, provider_name: str, source_class: str, query_id: str, status: str) -> str:
    return f"provider://{provider_name}/{source_class}/{query_id}/{status.lower()}"


def _normalize_result(
    request: Mapping[str, Any],
    *,
    provider: Any,
    source_class: str,
    raw: Mapping[str, Any],
    ordinal: int,
) -> dict[str, Any]:
    provider_name = _text(getattr(provider, "name", "")) or provider.__class__.__name__
    status = _text(raw.get("retrieval_status", "FOUND")).upper()
    if status not in VALID_RETRIEVAL:
        raise ValueError(f"invalid provider retrieval status: {status}")

    locator = _text(
        raw.get("locator")
        or raw.get("url")
        or raw.get("link")
        or _fallback_locator(
            provider_name=provider_name,
            source_class=source_class,
            query_id=_text(request["query_id"]),
            status=status,
        )
    )

    content_reference = _text(raw.get("content_reference"))
    if not content_reference:
        content = _text(raw.get("content"))
        if content:
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            content_reference = f"inline-sha256:{digest}"
        else:
            content_reference = locator

    relevance = _text(raw.get("relevance", "UNKNOWN")).upper()
    if relevance not in VALID_RELEVANCE:
        relevance = "UNKNOWN"

    source = dict(_mapping(raw.get("source")))
    source.setdefault("name", provider_name)
    source.setdefault("type", source_class)
    source.setdefault("provider", provider_name)

    metadata = dict(_mapping(raw.get("metadata")))
    for field in ("title", "snippet"):
        value = _text(raw.get(field))
        if value:
            metadata[field] = value
    metadata["ordinal"] = ordinal
    if metadata:
        source["metadata"] = metadata

    return {
        "retrieval_id": _retrieval_id(
            _text(request["query_id"]),
            provider_name,
            source_class,
            locator,
        ),
        "query_id": _text(request["query_id"]),
        "source": source,
        "locator": locator,
        "content_reference": content_reference,
        "retrieval_status": status,
        "relevance": relevance,
        "provenance": {
            **dict(_mapping(request.get("provenance"))),
            "runtime_stage": "59",
            "provider": provider_name,
            "source_class": source_class,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def _error_envelope(
    request: Mapping[str, Any],
    *,
    source_class: str,
    provider_name: str,
    message: str,
) -> dict[str, Any]:
    locator = _fallback_locator(
        provider_name=provider_name,
        source_class=source_class,
        query_id=_text(request["query_id"]),
        status="ERROR",
    )
    return {
        "retrieval_id": _retrieval_id(
            _text(request["query_id"]),
            provider_name,
            source_class,
            locator,
        ),
        "query_id": _text(request["query_id"]),
        "source": {
            "name": provider_name,
            "type": source_class,
            "provider": provider_name,
            "metadata": {"error": message},
        },
        "locator": locator,
        "content_reference": f"error://{_text(request['query_id'])}",
        "retrieval_status": "ERROR",
        "relevance": "UNKNOWN",
        "provenance": {
            **dict(_mapping(request.get("provenance"))),
            "runtime_stage": "59",
            "provider": provider_name,
            "source_class": source_class,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def _not_found_envelope(
    request: Mapping[str, Any],
    *,
    source_class: str,
    provider_name: str,
) -> dict[str, Any]:
    locator = _fallback_locator(
        provider_name=provider_name,
        source_class=source_class,
        query_id=_text(request["query_id"]),
        status="NOT_FOUND",
    )
    return {
        "retrieval_id": _retrieval_id(
            _text(request["query_id"]),
            provider_name,
            source_class,
            locator,
        ),
        "query_id": _text(request["query_id"]),
        "source": {
            "name": provider_name,
            "type": source_class,
            "provider": provider_name,
        },
        "locator": locator,
        "content_reference": f"not-found://{_text(request['query_id'])}",
        "retrieval_status": "NOT_FOUND",
        "relevance": "UNKNOWN",
        "provenance": {
            **dict(_mapping(request.get("provenance"))),
            "runtime_stage": "59",
            "provider": provider_name,
            "source_class": source_class,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def dispatch_requests(
    requests: Iterable[Mapping[str, Any]],
    registry: InformationProviderRegistry,
    *,
    max_results_per_provider: int = 5,
) -> list[dict[str, Any]]:
    envelopes: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for request in requests:
        source_classes = _strings(request.get("source_classes"))
        if not source_classes:
            envelopes.append(_error_envelope(
                request,
                source_class="unspecified",
                provider_name="registry",
                message="request has no source classes",
            ))
            continue

        for source_class in source_classes:
            provider = registry.resolve(source_class)
            if provider is None:
                envelope = _error_envelope(
                    request,
                    source_class=source_class,
                    provider_name="registry",
                    message=f"no provider registered for source class: {source_class}",
                )
                key = (_text(request["query_id"]), source_class, envelope["retrieval_id"])
                if key not in seen:
                    seen.add(key)
                    envelopes.append(envelope)
                continue

            provider_name = _text(getattr(provider, "name", "")) or provider.__class__.__name__
            try:
                raw_results = provider.search(request, max_results=max_results_per_provider)
                raw_results = list(raw_results or [])
                if not raw_results:
                    envelope = _not_found_envelope(
                        request,
                        source_class=source_class,
                        provider_name=provider_name,
                    )
                    key = (_text(request["query_id"]), source_class, envelope["retrieval_id"])
                    if key not in seen:
                        seen.add(key)
                        envelopes.append(envelope)
                    continue

                for ordinal, raw in enumerate(raw_results, start=1):
                    if not isinstance(raw, Mapping):
                        continue
                    envelope = _normalize_result(
                        request,
                        provider=provider,
                        source_class=source_class,
                        raw=raw,
                        ordinal=ordinal,
                    )
                    key = (
                        envelope["query_id"],
                        source_class,
                        envelope["locator"],
                    )
                    if key not in seen:
                        seen.add(key)
                        envelopes.append(envelope)
            except Exception as exc:
                envelope = _error_envelope(
                    request,
                    source_class=source_class,
                    provider_name=provider_name,
                    message=f"{type(exc).__name__}: {exc}",
                )
                key = (_text(request["query_id"]), source_class, envelope["retrieval_id"])
                if key not in seen:
                    seen.add(key)
                    envelopes.append(envelope)

    return envelopes


def run_preflight(
    store: UQLStore,
    *,
    question_id: str,
    plan: Mapping[str, Any],
    registry: InformationProviderRegistry,
    max_results_per_provider: int = 5,
) -> dict[str, Any]:
    """Execute information preflight and ingest retrievals into UQL."""
    prepared = prepare_requests(plan)
    if prepared.get("status") != "READY":
        return {
            "status": "BLOCKED",
            "question_id": question_id,
            "prepared": prepared,
            "envelopes": [],
            "ingestion": {
                "status": "NOT_RUN",
                "accepted_retrieval_ids": [],
                "errors": [],
            },
        }

    if question_id not in store.frontier:
        raise KeyError(f"unknown question_id: {question_id}")

    envelopes = dispatch_requests(
        prepared["requests"],
        registry,
        max_results_per_provider=max_results_per_provider,
    )
    ingestion = ingest_retrievals(
        store,
        question_id=question_id,
        envelopes=envelopes,
    )
    store.append_history(
        question_id=question_id,
        event_type="information_preflight_completed",
        payload={
            "query_plan_id": _text(plan["query_plan_id"]),
            "request_count": len(prepared["requests"]),
            "retrieval_count": len(envelopes),
            "accepted_retrieval_count": len(ingestion["accepted_retrieval_ids"]),
            "provider_coverage": registry.coverage(
                class_name
                for request in prepared["requests"]
                for class_name in _strings(request.get("source_classes"))
            ),
        },
    )

    return {
        "status": "COMPLETED",
        "question_id": question_id,
        "prepared": prepared,
        "envelopes": envelopes,
        "ingestion": ingestion,
    }


def demo() -> dict[str, Any]:
    import tempfile
    from pathlib import Path

    from local_corpus_provider_v1 import LocalCorpusProvider

    with tempfile.TemporaryDirectory() as directory:
        corpus = Path(directory)
        (corpus / "note.md").write_text(
            "An existing method preserves the invariant and resolves the "
            "unresolved difference without importing geometry.\n",
            encoding="utf-8",
        )
        store = UQLStore(corpus / "uql")
        store.create_question(
            question_id="Q-59-DEMO",
            process_id="P-59-DEMO",
            formulation="Determine whether an admissible continuation exists.",
        )

        plan = {
            "query_plan_id": "QPLAN-59-DEMO",
            "frontier_id": "FR-59-DEMO",
            "question_id": "Q-59-DEMO",
            "intents": ["SOLUTION_DISCOVERY", "INFORMATION_GAP"],
            "queries": [
                {
                    "query_id": "QRY-59-DEMO-01",
                    "intent": "SOLUTION_DISCOVERY",
                    "text": "Existing solutions for admissible continuation.",
                    "target_difference": "continuation candidate unknown",
                },
                {
                    "query_id": "QRY-59-DEMO-02",
                    "intent": "INFORMATION_GAP",
                    "text": "What information discriminates the alternatives?",
                    "target_difference": "discriminating information unknown",
                },
            ],
            "constraints": ["preserve invariant"],
            "source_classes": ["internal_corpus", "web"],
            "provenance": {
                "source_repository": "metamonism-semantic-core",
                "source_reference": "stage59",
                "derivation_mode": "FORMALIZATION",
            },
        }

        registry = InformationProviderRegistry()
        registry.register(LocalCorpusProvider(corpus))
        registry.register(InMemoryInformationProvider([
            {
                "query_id": "QRY-59-DEMO-01",
                "locator": "demo://web/existing-solution",
                "title": "Demo external result",
                "snippet": "A candidate method is documented.",
                "relevance": "MEDIUM",
                "source": {"name": "demo-web", "type": "web"},
            }
        ]))

        result = run_preflight(
            store,
            question_id="Q-59-DEMO",
            plan=plan,
            registry=registry,
        )
        state = store.get_frontier("Q-59-DEMO").to_dict()
        assert result["status"] == "COMPLETED"
        assert result["ingestion"]["status"] == "UPDATED"
        assert any(item["retrieval_status"] == "FOUND" for item in result["envelopes"])
        assert any(item["retrieval_status"] == "NOT_FOUND" for item in result["envelopes"])
        assert any(ref.startswith("retrieval:") for ref in state["evidence_references"])
        return {
            "status": "PASS",
            "retrievals": len(result["envelopes"]),
            "evidence_references": state["evidence_references"],
        }


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
          f"status={result['status']} retrievals={result['retrievals']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
