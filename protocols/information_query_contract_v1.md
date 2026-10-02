# Information Query Contract v1

A query is an operation for reducing uncertainty or discovering existing
knowledge before or during task execution.

Canonical object:

QUERY =
  target question
  + query intent
  + unresolved difference
  + query text
  + constraints
  + source classes
  + exclusions
  + provenance

The query is not itself a solution and not itself a task completion.

## Query modes

SOLUTION_DISCOVERY asks whether an existing solution or close solution is
already documented.

METHOD_DISCOVERY asks which known methods can address the unresolved
difference.

EVIDENCE_DISCOVERY searches for observations, measurements, results, or
documented evidence relevant to the difference.

CONTRADICTION_CHECK searches for counterexamples, limitations, failures,
negative results, or conflicting evidence.

INFORMATION_GAP asks what information is missing to discriminate between
remaining alternatives.

PRECEDENT_DISCOVERY searches for prior cases with relevant structure.

SOURCE_VALIDATION seeks primary or authoritative source material.

## Query-to-action rule

The information result may change the planned action:

information found
  -> validate / adapt / compose / reuse

information missing
  -> experiment / investigate / request data

information contradictory
  -> reconcile / test / split

information insufficient
  -> identify discriminating observation

This mapping is procedural guidance, not an automatic truth judgment.

## Result object

A retrieval result must retain query identity and source provenance.

A provider adapter may return snippets, full documents, datasets, or references.
The UFCPS bridge stores references and metadata and leaves semantic validation
to the consuming layer.

## Status

v1 experimental contract.
