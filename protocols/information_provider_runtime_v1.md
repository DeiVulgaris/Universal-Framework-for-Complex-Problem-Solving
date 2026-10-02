# Information Provider Runtime v1

## Purpose

The Information Provider Runtime closes the executable gap between the
Stage 58 query plan and the UFCPS information-space bridge.

It performs:

1. query-plan preparation;
2. provider resolution by source class;
3. provider invocation;
4. result normalization;
5. retrieval identity/provenance construction;
6. handoff to the existing retrieval-ingestion boundary.

## Runtime path

Semantic Core query plan
  -> prepare_requests
  -> ProviderRegistry
  -> InformationProvider.search
  -> normalize retrievals
  -> ingest_retrievals
  -> UQL frontier/history

## Built-in adapters

### Local corpus

swarm/local_corpus_provider_v1.py searches text-bearing files under a
configured local path. It is deterministic and requires no external service.

### HTTP JSON

swarm/http_json_provider_v1.py calls a configurable HTTP GET endpoint and
expects either a JSON array or an object containing a results array. It is
intentionally vendor-neutral.

The adapter can therefore connect a deployed UFCPS instance to a web,
literature, repository, dataset, or domain API without changing the semantic
contract.

### In-memory provider

The runtime module contains a deterministic in-memory provider for tests and
demonstrations.

## Provider registry

InformationProviderRegistry maps source classes to provider adapters.

Missing coverage is explicit: an unregistered source class becomes an ERROR
retrieval with provider provenance instead of silently disappearing.

## Preflight

run_preflight() performs the full information-before-action cycle:

query plan
  -> provider dispatch
  -> retrieval envelopes
  -> UQL ingestion

No task is automatically created from retrieval. The resulting UQL frontier
remains available to Task Discovery and later semantic validation.

## Deduplication

Retrieval identities are deterministic for a query/provider/source-class/locator
combination. This allows repeated preflight runs to be recognized without
altering the semantic meaning of the retrieved source.

## Status

v1 — experimental executable runtime.
