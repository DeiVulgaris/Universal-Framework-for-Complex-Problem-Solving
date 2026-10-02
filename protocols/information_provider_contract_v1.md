# Information Provider Contract v1

## Purpose

An information provider is an external or local mechanism capable of
answering a provider-neutral UFCPS information request.

The provider is an adapter, not a semantic judge.

Canonical boundary:

QUERY REQUEST
  ↓
PROVIDER ADAPTER
  ↓
RAW INFORMATION
  ↓
NORMALIZED RETRIEVAL
  ↓
UQL / SEMANTIC VALIDATION

## Provider interface

A provider exposes:

- a stable provider name;
- one or more supported source classes;
- a search operation accepting one prepared query request;
- zero or more raw result records.

Supported source classes in the current contract include:

- web
- literature
- code_repository
- dataset
- internal_corpus

Providers may support additional source classes when registered locally. The
query contract remains unchanged.

## Raw result minimum

A provider result should expose:

- locator, URL, path, or another source identifier;
- optional content reference;
- optional title/snippet/content;
- optional relevance;
- optional source metadata.

The runtime supplies missing retrieval identity and provenance.

## Provider failures

The provider runtime normalizes failures into retrieval status:

FOUND
PARTIAL
NOT_FOUND
ERROR

A provider exception therefore records an information failure rather than
terminating the unresolved question.

An empty successful response becomes NOT_FOUND.

## Semantic boundary

Provider results are not claims.

The runtime must not:

- declare a source correct;
- rank sources as authoritative in semantic terms;
- close a question because a search returned nothing;
- assign an agent;
- claim a task;
- infer a solution from a single retrieval.

These decisions belong to subsequent UFCPS and Semantic Core processes.

## Reusability

A concrete provider may be:

- a local corpus index;
- an HTTP JSON API adapter;
- a scholarly search service;
- a repository search service;
- a domain database adapter.

The same prepared request and normalized retrieval contract is used for all.
