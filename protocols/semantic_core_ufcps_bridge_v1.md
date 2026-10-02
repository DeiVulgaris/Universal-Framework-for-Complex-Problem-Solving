# Semantic Core ↔ UFCPS Bridge v1

## Purpose

This protocol defines the native UFCPS side of the bridge to the
Meta-Monism Semantic Core.

The bridge imports no ontology. It accepts a structured task tree and turns
its nodes into UFCPS UQL questions. Execution results are recorded back into
UQL as continuation-relevant process information.

## Direction A — Core → UFCPS

```
Semantic Frontier
    ↓
Task Tree
    ↓
UFCPS UQL
    ↓
Task Discovery
    ↓
Claim
    ↓
Execution
```

A task tree node becomes an unresolved UFCPS question.

Parent/child relations are preserved as:

```
parent_question_id
    ↓
child question
```

The UQL remains authoritative after import.

## Direction B — UFCPS → Core

```
Execution Result
    ↓
UQL frontier update
    ↓
exportable frontier state
    ↓
Semantic Core validation
    ↓
next task generation
```

The UFCPS side does not decide semantic truth.

## Result policy

| UFCPS result | UQL effect |
|---|---|
| solution | candidate resolution; question may remain unresolved until validated |
| partial | preserve partial information and unresolved difference |
| negative | append failed path and keep question active |
| contradiction | preserve contradiction and create a new unresolved difference |
| inconclusive | preserve uncertainty and request discriminating information |
| anomaly | preserve anomaly as continuation-relevant information |
| deadlock | preserve a blocked frontier that remains discoverable |

Therefore:

```
RESULT != TRUTH
RESULT != AUTOMATIC TERMINATION
```

## Task-tree import rules

An import is admissible only when a node contains:

- question identity;
- formulation;
- unresolved difference;
- parent identity when it is not the root;
- next required operation;
- provenance.

Constraints, evidence, capabilities and resources are carried into the UQL
metadata/state where the current UQL schema permits them.

## Native UFCPS integration

The bridge module is:

```
swarm/semantic_core_bridge_v1.py
```

It provides:

- task-tree validation;
- root question creation;
- derived-question creation;
- discovery input generation;
- result-to-frontier update;
- import/export event records.

It does not claim tasks, assign agents, reserve resources, or execute work.

## Architectural role

The two repositories are therefore connected as:

```
SEMANTIC CORE
meaning / provenance / constraints / unresolved differences
                         ↓
                  BRIDGE ADAPTER
                         ↓
UFCPS
question / discovery / claim / execution / continuity
                         ↓
                  BRIDGE ADAPTER
                         ↓
SEMANTIC CORE
candidate frontier update
```

## Status

v1 — experimental integration protocol.
