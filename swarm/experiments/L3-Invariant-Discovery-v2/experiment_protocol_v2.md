# L3 Invariant Discovery v2 — Experimental Protocol

**Experiment ID:** `UFCPS-L3-INVARIANT-DISCOVERY-v2`
**Version:** 2.0
**Status:** Experimental protocol
**Parent experiment:** `L3-Invariant-Discovery-v1`

---

## 1. Purpose

This experiment tests whether the Level 3 process can generate a candidate structural invariant from observations **without being given a predefined family of candidate invariants**.

Version 1 demonstrated that a structural candidate could be selected and tested from a predefined candidate family.

Version 2 removes that restriction.

The central experimental question is:

> Can the process generate a candidate invariant from observed structural regularities without being explicitly provided with the invariant or a predefined list of possible invariants?

---

## 2. Difference from v1

Version 1 used a predefined candidate family.

Conceptually:

```text
observations
    ↓
predefined candidate family
    ↓
candidate selection
    ↓
candidate testing
```

Version 2 requires:

```text
observations
    ↓
structural extraction
    ↓
relation generation
    ↓
candidate formation
    ↓
candidate testing
    ↓
candidate rejection / revision
```

The experiment must not contain a direct list such as:

```text
"result_length == left_length + right_length"
"result == left + right"
```

or equivalent domain-specific formulations.

---

## 3. Experimental boundary

The experiment does not require unrestricted scientific reasoning.

It tests a narrower capability:

> generation of candidate relations from observable structural properties of symbolic records.

The experiment therefore remains a controlled test of invariant discovery rather than a test of general intelligence.

---

## 4. Input restriction

The process receives raw observations with fields equivalent to:

```text
record_id
left
right
result
```

The process may derive structural properties from these fields.

Examples of admissible derived properties include:

* string length;
* equality;
* prefix/suffix relations;
* repeated-symbol structure;
* character multiplicity;
* positional correspondence;
* substring relations;
* structural similarity;
* symbol-set relations;
* transformation relations.

These are observational operations, not semantic interpretations.

---

## 5. Prohibited information

The discovery process must not receive:

* the name of the domain;
* the intended semantic interpretation;
* the intended invariant;
* a list of candidate invariants;
* arithmetic terminology;
* names of numeral systems;
* the historical origin of the representations;
* the hidden evaluation oracle.

The process must not be told that the observations represent addition, quantity, arithmetic, notation, or number systems.

---

## 6. Candidate generation

Candidate generation must proceed from structural properties extracted from the observations.

The process may construct relations by comparing:

```text
left ↔ right
left ↔ result
right ↔ result
left + right ↔ result
```

provided that these operations are treated as structural transformations rather than semantic arithmetic.

The candidate-generation mechanism may use general relation templates, provided that those templates are not themselves the intended invariant.

For example, a generic structural relation such as:

```text
property(A, B, C)
```

is admissible.

A predefined statement of the intended invariant is not.

---

## 7. Candidate representation

Every generated candidate must contain at least:

```text
candidate_id
description
formal_relation
supporting_observations
challenging_observations
```

Optional fields may include:

```text
derived_features
generation_trace
confidence
status
revision_history
```

The candidate must be represented independently from the hidden evaluator.

---

## 8. Candidate testing

Every candidate must be tested against all observations available during discovery.

A candidate cannot be promoted merely because it explains a subset of observations.

The process must explicitly distinguish:

```text
SUPPORT
CHALLENGE
UNRESOLVED
```

A candidate contradicted by observations must not be reported as an established invariant.

---

## 9. Candidate revision

If a generated candidate is contradicted, the process may:

1. reject it;
2. modify it;
3. generate a more general relation;
4. generate an alternative candidate;
5. retain multiple unresolved candidates.

Candidate revision must not use the hidden evaluation oracle.

The process must receive only the observable data and the consequences of testing its own candidate.

---

## 10. Candidate competition

The process may generate multiple candidates.

If several candidates remain viable, the process must not arbitrarily select one as established.

Instead it should preserve:

```text
candidate_1
candidate_2
...
candidate_n
```

together with their respective evidence.

If the available evidence does not distinguish them, the experimental status must remain:

```text
UNRESOLVED
```

---

## 11. Holdout protocol

The holdout observations remain completely withheld during candidate generation.

The sequence is:

```text
TRAINING + CONTROLS
        ↓
candidate generation
        ↓
candidate freeze
        ↓
HOLDOUT
        ↓
evaluation
```

No candidate may be modified after exposure to the holdout.

If modification occurs after holdout exposure, the run is invalid.

---

## 12. Hidden evaluation

The hidden evaluator may know the intended structural interpretation.

The discovery process must not.

The evaluator determines whether the frozen candidate:

1. explains the positive observations;
2. rejects negative controls;
3. generalizes to holdout observations.

The evaluator must not provide information back to the discovery process.

---

## 13. Success criterion

The experiment may be classified `PASS` only if all of the following conditions hold:

### A. Candidate generation

At least one candidate is generated without being selected from a predefined invariant family.

### B. Training support

The candidate explains the relevant positive training observations.

### C. Control discrimination

The candidate rejects the negative controls.

### D. Holdout generalization

The frozen candidate correctly predicts the holdout observations.

### E. No semantic leakage

The candidate generation process receives no semantic domain labels or intended invariant.

### F. Independent formulation

The candidate's formulation is generated from observable structural relations rather than copied from an experiment-provided invariant.

### G. Reproducible trace

The experiment records enough information to reconstruct how the candidate was generated.

---

## 14. Failure criterion

The experiment is classified `FAIL` if:

* the candidate is explicitly supplied by the experiment;
* the candidate is selected from a predefined list of intended invariants;
* semantic labels leak into the discovery process;
* the candidate cannot discriminate negative controls;
* the frozen candidate fails the required holdout tests;
* the process changes the candidate after seeing the holdout;
* the discovery trace cannot establish that the candidate originated from observations.

---

## 15. Unresolved criterion

The experiment is classified `UNRESOLVED` if:

* several candidates remain viable;
* the candidate generation mechanism produces plausible relations but evidence is insufficient;
* the candidate generalizes inconsistently;
* the holdout is insufficient to distinguish competing candidates;
* the generation trace is incomplete;
* a structural candidate is produced but its independence from experiment design cannot be established.

`UNRESOLVED` is a valid scientific result.

It must not be converted into `PASS`.

---

## 16. Independence requirement

The strongest requirement of v2 is:

> The experiment must demonstrate that the candidate was generated from observations rather than retrieved from experiment-specific knowledge.

Therefore the implementation must preserve a generation trace.

At minimum:

```text
raw observation
    ↓
derived structural feature
    ↓
relation construction
    ↓
candidate
```

The trace should allow an external reviewer to determine whether the candidate follows from the observed data.

---

## 17. Avoiding semantic leakage through feature names

Feature names must not encode the intended domain.

For example, names such as:

```text
number_value
sum
addition_result
numeral_value
arithmetic_result
```

are prohibited.

Neutral names are required:

```text
left_length
right_length
result_length
left_symbols
right_symbols
result_symbols
position_relation
multiplicity_relation
```

The distinction is important because a semantically informative feature name can function as hidden supervision.

---

## 18. Generalization requirement

A candidate should not be considered successful merely because it memorizes the surface form of the training examples.

The experiment must distinguish:

```text
memorization
```

from:

```text
structural generalization
```

The holdout observations therefore use symbolic structures not identical to the training examples.

---

## 19. Candidate complexity

When multiple candidates explain the observations, the process may record candidate complexity.

Possible structural measures include:

* number of conditions;
* number of derived properties;
* number of transformations;
* number of exceptions.

However, complexity must not be used to impose a hidden preferred answer.

If multiple candidates remain observationally equivalent, the result remains `UNRESOLVED`.

---

## 20. Level 3 integration

The experiment should be connected to the existing Level 3 process.

The integration is expected to expose the invariant-discovery task as another recursive process:

```text
C_k
 ↓
observation
 ↓
structural distinctions
 ↓
candidate relations
 ↓
candidate testing
 ↓
C_k+1
```

Candidate invariants and unresolved questions should become persistent content of the successor cognitive space.

The Level 3 process must remain continuous even when candidate generation reaches a local deadlock.

---

## 21. Local deadlock

A failure to generate a satisfactory invariant must not terminate the global process.

For example:

```text
candidate generation exhausted
        ↓
UNRESOLVED
        ↓
new question
        ↓
next process cycle
```

The invariant remains a question rather than becoming a forced conclusion.

This preserves the Level 3 invariant:

> Local Failure ≠ Process Termination.

---

## 22. Reproducibility

The following must remain frozen after the first v2 run:

* dataset version;
* train/control/holdout partition;
* hidden evaluation oracle;
* protocol version;
* candidate-generation rules;
* feature extraction rules;
* candidate representation;
* pass/fail/unresolved criteria.

Any substantive change requires:

```text
L3-Invariant-Discovery-v3
```

or another explicitly versioned experiment.

---

## 23. Required experiment output

The runner must record:

```text
experiment_id
protocol_version
dataset_version
status
generated_candidates
candidate_generation_traces
training_support
training_challenges
holdout_predictions
unresolved_questions
level3_trace
```

The result should also state explicitly:

```text
predefined_candidate_family_used: false
semantic_labels_exposed_to_engine: false
holdout_used_during_discovery: false
```

These fields are methodological controls, not merely metadata.

---

## 24. Interpretation boundary

Even a successful `PASS` would establish only:

> Under the defined experimental conditions, the process generated and tested a structural invariant from symbolic observations without receiving the intended invariant or semantic domain label.

It would not establish:

* mathematical understanding;
* human-like reasoning;
* semantic consciousness;
* subjective experience;
* creativity in the human sense;
* general intelligence;
* AGI;
* autonomous goals;
* self-awareness.

Those would require separate independent experimental criteria.

---

## 25. Primary research question

The frozen research question for v2 is:

> **Can the Level 3 process generate a candidate invariant from raw symbolic observations without being given a predefined family of candidate invariants?**

The experiment must answer only this question.

---

## 26. Experimental discipline

The governing rule is:

> **The process must discover the invariant; the experiment must not teach it the invariant.**

The epistemic status rules remain:

```text
PASS         → NEXT LEVEL
FAIL         → STOP
UNRESOLVED   → OPEN QUESTION
```

The experiment therefore treats an unresolved result as information rather than failure of the research program.

---

## 27. Relationship to v1

Version 1 remains preserved as the baseline.

```text
L3-Invariant-Discovery-v1
    predefined candidate family
    ↓
    candidate selection
    ↓
    contradiction
    ↓
    UNRESOLVED
```

Version 2 tests the stronger condition:

```text
L3-Invariant-Discovery-v2
    raw observations
    ↓
    structural feature generation
    ↓
    relation generation
    ↓
    candidate generation
    ↓
    candidate testing
    ↓
    holdout
```

The two experiments must not be conflated.

---

## 28. Expected scientific outcome

There are three legitimate outcomes.

### PASS

The process independently generates a candidate that survives controls and generalizes to holdout.

### FAIL

The process cannot generate a viable candidate under the frozen protocol, or the result depends on prohibited supervision.

### UNRESOLVED

The process generates meaningful candidates but the available evidence cannot establish independent invariant discovery.

All three outcomes are scientifically informative.

---

**Protocol status: FROZEN FOR IMPLEMENTATION**

**Next artifact:** v2 dataset/runner adaptation and candidate-generation implementation, without a predefined invariant family.
