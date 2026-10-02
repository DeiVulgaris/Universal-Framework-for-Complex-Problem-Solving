# Information Space Bridge v1

## Purpose

The Information Space Bridge is the pre-execution information layer of UFCPS.

It allows an existing unresolved question or task to be checked against
accessible information before new computation, experimentation, or
delegation is started.

Canonical flow:

QUESTION
  ↓
INFORMATION NEED
  ↓
QUERY PLAN
  ↓
INFORMATION SPACE
  ↓
RETRIEVAL
  ↓
EVIDENCE CANDIDATES
  ↓
FRONTIER UPDATE
  ↓
DISCOVERY / CLAIM / EXECUTION

## Information space

The information space is provider-neutral. It may include:

- web search;
- scientific literature;
- books and archives;
- code repositories;
- datasets;
- standards and technical documentation;
- internal corpora;
- domain-specific databases.

UFCPS does not assume that one provider or source class is authoritative.

## Query intents

Supported intents:

- SOLUTION_DISCOVERY
- METHOD_DISCOVERY
- EVIDENCE_DISCOVERY
- CONTRADICTION_CHECK
- INFORMATION_GAP
- PRECEDENT_DISCOVERY
- SOURCE_VALIDATION

A query intent describes what information the process is seeking. It does not
decide the truth of retrieved material.

## Preflight principle

Before executing a newly formed task, the process may run an information
preflight:

1. search for existing solutions;
2. search for existing methods;
3. search for evidence;
4. search for counterevidence or limitations;
5. identify remaining information gaps.

The result may change the next procedural step.

Examples:

existing solution found
  -> validate/adapt existing solution

method found
  -> evaluate method instead of inventing another

contradictory evidence found
  -> create reconciliation task

no adequate information found
  -> perform experiment, computation, or other information-producing action

## Retrieval is not truth

A retrieval result is process information.

It may be:

FOUND
PARTIAL
NOT_FOUND
ERROR

and may carry relevance:

UNKNOWN
LOW
MEDIUM
HIGH

These values do not establish scientific validity.

## Evidence ingestion

A retrieved result is stored with:

- retrieval identity;
- query identity;
- source identity;
- locator;
- content reference;
- retrieval status;
- provenance.

The bridge then records it in UQL as continuation-relevant information.

## No hidden assignment

The information bridge does not:

- assign an agent;
- claim a task;
- select a winning source;
- declare a solution correct;
- terminate the question because search failed.

## Integration

The native implementation is:

swarm/information_space_bridge_v1.py

The Semantic Core supplies query plans. UFCPS dispatches them to an external
provider and stores the returned retrieval envelopes.

The provider itself is intentionally outside the core protocol.

## Status

v1 — experimental information retrieval integration layer.
