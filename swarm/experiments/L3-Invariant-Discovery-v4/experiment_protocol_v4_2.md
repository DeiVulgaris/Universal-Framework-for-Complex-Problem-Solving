# UFCPS — Level 3 Invariant Discovery v4.2

## Experiment Protocol

**Experiment ID:** `UFCPS-L3-INVARIANT-DISCOVERY-v4.2`
**Level:** 3 — Reflection
**Research Area:** Productive Compositional Invariant Discovery
**Status:** Protocol specification

---

## 1. Research Question

Can the Level 3 process generate a **productive compositional relation** between two input structures and an output structure, formulate that relation as an executable transformation, and generalize it to unseen observations without being given:

* the semantic interpretation of the observations;
* the intended relation;
* a predefined family of target invariants;
* the holdout observations.

The central object of discovery is:

```text
T(left, right) → predicted_result
```

The candidate must be executable and must use information from both inputs.

---

## 2. Methodological Correction from v4.1

Version 4.1 used a control partition containing observations that deliberately violated the hidden relation.

This creates a methodological problem.

The evaluator in v4 evaluates candidates by comparing:

```text
candidate(left, right)
```

with:

```text
observed_result
```

Therefore, if a control observation is deliberately constructed as a violation of the hidden relation, a correct candidate is expected to fail that control.

Such a control does not discriminate between competing hypotheses. It merely tests whether the candidate reproduces an intentionally incorrect observation.

### v4.2 correction

In v4.2:

> **A control observation is a valid observation of the same underlying relation, selected because competing candidate transformations produce different predictions for it.**

Thus:

```text
Control ≠ negative example
```

Instead:

```text
Control = discriminating observation
```

All discovery, selection, and control observations belong to the same underlying observational process.

The control partition is therefore used to determine whether competing executable hypotheses can be distinguished by additional evidence.

---

## 3. Core Ontology

The experiment operates on opaque symbolic structures.

Each observation has the form:

```text
(left, right) → result
```

No semantic interpretation is provided to the discovery process.

The process may inspect structural properties of the observations and may construct executable transformations.

The intended hidden relation remains external to the discovery process.

---

## 4. Information Available to the Discovery Process

The discovery process may receive only:

```text
record_id
left
right
result
```

It may derive structural properties from these observations.

Permitted structural information includes, where applicable:

* string length;
* equality;
* prefix/suffix relations;
* repeated-symbol structure;
* character multiplicity;
* positional correspondence;
* structural similarity;
* symbol-set relations;
* transformation relations;
* composition of observed structures.

The process must not receive semantic descriptions of the domain.

---

## 5. Prohibited Information

The discovery process must not receive:

* the name of the intended relation;
* semantic labels for observations;
* arithmetic terminology;
* numeral-system terminology;
* historical information about the representations;
* the hidden evaluation rule;
* a predefined list of candidate target relations;
* expected positive/negative labels during discovery;
* holdout observations during candidate generation or selection.

In particular, the system must not be told that the observations represent:

* numbers;
* arithmetic;
* addition;
* counting;
* notation systems;
* cardinality.

---

## 6. Candidate Representation

A candidate is an executable compositional transformation:

```text
T(left, right) → result
```

A candidate should contain at least:

```text
candidate_id
relation_type
formal_relation
execution_trace
provenance
```

The candidate must be executable on previously unseen input pairs.

A candidate that merely describes a statistical property without producing an output is not sufficient.

---

## 7. Candidate Requirements

A viable compositional candidate must:

1. accept both inputs;
2. produce a predicted output;
3. be executable;
4. be derived from discovery observations;
5. contain sufficient provenance for reconstruction;
6. make predictions without reading the observed result;
7. remain testable on observations not used to construct it.

The candidate must not use the observed result as an input to its prediction function.

---

## 8. Experimental Partitions

The dataset is divided into five partitions:

```text
DISCOVERY
SELECTION
CONTROL
COUNTEREXAMPLE
HOLDOUT
```

### 8.1 Discovery

Used to generate candidate transformations.

Candidates may be constructed from observations in this partition.

---

### 8.2 Selection

Used to eliminate candidates that do not reproduce additional observations.

Selection observations are not used as holdout observations.

Multiple candidates may survive selection.

---

### 8.3 Control

The control partition has a specific methodological purpose:

> distinguish competing candidates that remain viable after discovery and selection.

Control observations must satisfy the following conditions:

1. they are valid observations of the same hidden relation;
2. they are not violations deliberately constructed to defeat a correct candidate;
3. at least some surviving candidate transformations must make different predictions on them;
4. the observed result must correspond to the underlying relation;
5. the discovery process must not receive a label identifying the correct candidate.

The control set should therefore maximize disagreement among surviving hypotheses where practical.

For example, if two candidates both reproduce:

```text
ab + cd → abcd
```

but produce different outputs for:

```text
ac + bd → ?
```

then an observation using that second pair can discriminate between the hypotheses.

The purpose is not to create a negative example.

The purpose is to create **informative disagreement**.

---

## 9. Control Design Principle

The control partition should be designed after identifying the major competing candidate transformations, while keeping the actual semantic interpretation hidden from the discovery process.

The external experiment designer may inspect candidate behavior when constructing the control partition.

The discovery process may not receive that information.

This creates a separation between:

```text
experimental design
```

and:

```text
invariant discovery
```

The control generator may therefore optimize for:

```text
candidate disagreement
```

without exposing:

```text
target semantics
```

to the discovery engine.

---

## 10. Candidate Equivalence

Two candidates may be syntactically different while producing identical outputs on all currently observed inputs.

Therefore:

```text
syntactic difference ≠ empirical difference
```

The experiment must record prediction signatures where possible.

Candidates producing identical predictions on all available observations may constitute an observational equivalence class.

Such equivalence does not establish that either candidate represents the underlying invariant.

If multiple observationally equivalent candidates remain after control evaluation, the experiment should remain:

```text
UNRESOLVED
```

unless additional observations distinguish them or the candidates are formally demonstrated to be equivalent over the relevant transformation domain.

---

## 11. Counterexamples

Counterexamples remain distinct from controls.

A counterexample is an observation specifically selected or discovered because a candidate that previously appeared viable fails to reproduce it.

The purpose is falsification.

Conceptually:

```text
Control:
    distinguish surviving hypotheses

Counterexample:
    falsify a candidate
```

A counterexample does not need to be an intentional violation of the hidden relation.

It is sufficient that the candidate's prediction differs from the observed result.

---

## 12. Holdout

The holdout partition remains completely isolated from discovery and candidate selection.

The process must not access holdout observations until the candidate has been frozen.

Required sequence:

```text
Dataset
   ↓
Discovery
   ↓
Candidate Generation
   ↓
Selection
   ↓
Control Discrimination
   ↓
Counterexample Evaluation
   ↓
Candidate Freeze
   ↓
Holdout
```

No candidate may be modified after observing holdout results.

---

## 13. Candidate Freeze

Before holdout evaluation, the system must establish:

```text
frozen_candidate
```

or explicitly record:

```text
NO_FROZEN_CANDIDATE
```

A candidate may be frozen only after:

* discovery;
* selection;
* control evaluation;
* counterexample evaluation.

If multiple viable candidates remain and cannot be distinguished, candidate freeze should not occur.

---

## 14. External Evaluation Oracle

An external evaluation oracle may exist for experimental validation.

The oracle may know the hidden relation.

However:

> The oracle must not expose its semantic interpretation to the discovery process.

Oracle information may be used for:

* post hoc evaluation;
* dataset construction;
* holdout scoring;
* methodological validation.

It must not be used for candidate generation or candidate selection.

---

## 15. Independence Requirements

The experiment should explicitly record whether the following occurred:

```text
predefined_candidate_family_used
semantic_labels_exposed_to_engine
expected_positive_labels_loaded
expected_positive_labels_used
holdout_used_during_discovery
holdout_used_during_selection
observed_result_used_for_prediction
```

For a valid discovery experiment, the expected values are:

```text
predefined_candidate_family_used = false
semantic_labels_exposed_to_engine = false
expected_positive_labels_loaded = false
expected_positive_labels_used = false
holdout_used_during_discovery = false
holdout_used_during_selection = false
observed_result_used_for_prediction = false
```

---

## 16. Provenance

Every generated candidate must retain sufficient provenance to determine:

* which observations contributed to its generation;
* which transformation primitives were used;
* how the executable relation was constructed;
* which observations were used for evaluation;
* whether any prohibited information entered the process.

The provenance record must distinguish:

```text
generation evidence
selection evidence
control evidence
counterexample evidence
holdout evidence
```

---

## 17. Success Criteria

The experiment may be considered:

```text
PASS
```

only if all required conditions are satisfied.

### Required conditions

1. A compositional candidate is generated.
2. The candidate is executable.
3. The candidate uses both inputs.
4. No predefined target-invariant family is supplied.
5. No semantic interpretation is supplied.
6. The candidate reproduces discovery-supported observations.
7. The candidate survives selection.
8. The candidate survives discriminating controls.
9. Competing candidates are eliminated or shown to be observationally/formally equivalent.
10. The candidate survives counterexample evaluation.
11. The candidate is frozen before holdout access.
12. The frozen candidate generalizes to holdout observations.
13. Complete provenance is available.
14. The experiment is reproducible.

---

## 18. UNRESOLVED Conditions

The experiment must remain:

```text
UNRESOLVED
```

if any of the following occurs:

* multiple viable candidates remain;
* control observations do not discriminate candidates;
* candidates remain observationally equivalent;
* the candidate transformation language is insufficient;
* holdout evidence is insufficient;
* provenance is incomplete;
* independence from semantic information cannot be established;
* candidate selection depends on information that should have been hidden;
* reproducibility is incomplete.

Importantly:

```text
UNRESOLVED ≠ FAIL
```

It means that the experiment has not established a unique productive invariant.

---

## 19. FAIL Conditions

The experiment should be classified as:

```text
FAIL
```

when the protocol itself is successfully executed but the tested hypothesis is contradicted by the observations.

Examples include:

* no candidate can reproduce valid discovery/selection observations;
* every executable candidate fails valid discriminating observations;
* a frozen candidate fails the required holdout generalization;
* the hypothesized productive relation cannot account for the observed data under the allowed transformation language.

---

## 20. Interpretation Boundary

Even a successful result would establish only that the tested Level 3 process can generate and generalize an executable compositional relation under the specified experimental conditions.

It would not by itself establish:

* semantic understanding;
* arithmetic understanding;
* consciousness;
* subjectivity;
* general intelligence;
* AGI;
* autonomous goals;
* independence from all benchmark design.

The experiment tests a specific methodological property:

> **productive discovery and generalization of a compositional relation from opaque symbolic observations.**

---

## 21. Version Relation

v4.2 is a methodological refinement of v4.1.

The core ontology remains:

```text
T(left, right) → predicted_result
```

The following remain unchanged:

* opaque symbolic observations;
* executable candidate requirement;
* semantic isolation;
* no predefined target invariant;
* discovery/selection/holdout separation;
* candidate freeze;
* provenance requirements;
* external oracle isolation.

The principal change is:

```text
v4.1:
control = intentional violation

v4.2:
control = discriminating valid observation
```

Therefore v4.2 must be treated as a new experimental version rather than a rewrite of the historical v4.1 result.

---

## 22. Expected Experimental Logic

The intended reasoning chain is:

```text
Raw observations
      ↓
Candidate generation
      ↓
Several executable hypotheses
      ↓
Selection
      ↓
Surviving hypotheses
      ↓
Discriminating controls
      ↓
Hypothesis separation
      ↓
Counterexample testing
      ↓
Candidate freeze
      ↓
Unseen holdout
      ↓
Generalization result
```

The critical transition is:

```text
multiple viable hypotheses
        ↓
informative disagreement
        ↓
hypothesis discrimination
```

rather than:

```text
multiple viable hypotheses
        ↓
invalid negative examples
        ↓
all candidates fail
```

---

## 23. Central Methodological Principle

The v4.2 experiment adopts the following principle:

> **A good control does not contradict the phenomenon being tested; it creates an observation on which competing explanations make different predictions.**

Accordingly, control observations should increase information about the hypothesis space rather than merely introduce contradictions.

---

## 24. Expected Status Before Execution

No outcome is assumed by this protocol.

The experiment may produce:

```text
PASS
FAIL
UNRESOLVED
```

The status must be determined exclusively from the executed experiment and recorded results.
