# L3 Invariant Discovery v4 — Experiment Protocol

**Experiment:** UFCPS-L3-INVARIANT-DISCOVERY-v4
**Protocol version:** 4.0
**Status:** DESIGN / PRE-EXECUTION

---

## 1. Research Question

The v4 experiment asks:

> Can the Level 3 process generate a productive compositional relation between two input structures and an output structure, such that the relation can generate predictions for previously unseen observations without being given the semantic interpretation of the target relation?

The central transition from v3 is:

```text
v3:

observation
    ↓
structural feature
    ↓
feature == value
```

to:

```text
v4:

left ─────┐
          ├──→ compositional relation ──→ result
right ────┘
```

The experiment therefore focuses on **relations that explain how the result is produced from the inputs**, rather than merely describing properties that happen to hold in the observations.

---

# 2. Motivation

The v3 experiment generated 36 candidates and reduced them to 10 viable candidates after selection and counterexample testing.

The remaining candidates included both relatively informative relations and trivial structural regularities.

For example:

```text
length_difference == 0
```

and:

```text
result_matches_combined_counts == True
```

can both survive the available tests.

The problem is therefore not simply insufficient counterexamples.

The deeper problem is that the candidate representation permits statements about observations without requiring a candidate to **construct or predict the result from the inputs**.

v4 changes the candidate ontology.

A candidate is no longer primarily a property of an observation.

A candidate is a proposed transformation:

```text
T(left, right) → predicted_result
```

The candidate must therefore be executable on an unseen pair of inputs.

---

# 3. Epistemic Objective

The experiment does not attempt to determine whether the system understands the semantic meaning of the observations.

The target is narrower:

> Determine whether a process can independently construct a structural transformation that remains predictive outside the observations from which it was generated.

The experiment therefore separates:

1. candidate generation;
2. candidate execution;
3. prediction;
4. counterexample testing;
5. holdout generalization.

A candidate that merely describes the training observations without generating predictions does not satisfy the productive-relation criterion.

---

# 4. Input Representation

The discovery engine receives only raw symbolic observations.

Each observation has the form:

```text
{
    "record_id": "...",
    "left": "...",
    "right": "...",
    "result": "..."
}
```

The engine must not receive:

* domain names;
* semantic interpretations;
* arithmetic terminology;
* names of numeral systems;
* descriptions of the hidden relation;
* a predefined target invariant;
* a predefined candidate relation family.

The hidden evaluation oracle remains external to the discovery process.

---

# 5. Candidate Ontology

A v4 candidate must represent a transformation rather than only a feature assertion.

Canonical conceptual form:

```text
Candidate:
    T(left, right) → result
```

A candidate must contain at least:

```text
candidate_id
relation_type
transformation
input_requirements
prediction_rule
source_record_ids
generation_trace
```

The transformation must be executable against a new pair of inputs.

---

# 6. Compositionality Requirement

A candidate is considered compositional only if its prediction depends on both input structures.

The minimal conceptual structure is:

```text
(left, right)
     ↓
 transformation
     ↓
 predicted_result
```

Candidates that simply inspect the result and state a property of it are insufficient.

For example:

```text
result_length == 4
```

is not a productive compositional relation.

Likewise:

```text
length_difference(left, right) == 0
```

does not by itself predict the result.

A candidate such as:

```text
combine_symbol_counts(left, right)
    → predicted_result
```

is structurally capable of producing a prediction and therefore qualifies for further evaluation.

---

# 7. Transformation Classes

The protocol does not prescribe a single target transformation.

The discovery engine may construct transformations from neutral structural operations available to the representation.

Possible operation primitives include:

### 7.1 Concatenation

```text
left + right
```

### 7.2 Reverse concatenation

```text
right + left
```

### 7.3 Character or symbol multiset composition

```text
counts(left) + counts(right)
```

### 7.4 Symbol-set composition

```text
symbols(left) ∪ symbols(right)
```

### 7.5 Positional composition

Operations based on corresponding positions in the two inputs.

### 7.6 Reordering

Composition followed by a structural ordering operation.

### 7.7 Repetition or multiplicity transformation

Transformations based on the number of occurrences of symbols.

### 7.8 Structural mapping

A transformation that preserves or combines structural properties of the two inputs.

These are **operation primitives**, not target invariants.

The experiment must not declare in advance which composition is correct.

---

# 8. Important Methodological Constraint

The operation vocabulary must not become a disguised predefined candidate family.

The system may use generic structural operations as a representation language.

It must not be told:

```text
"The hidden rule is addition."
```

or:

```text
"The correct operation is combined symbol counts."
```

or:

```text
"Search specifically for the operation that produces the expected result."
```

The distinction is:

```text
allowed:

generic structural operations
        ↓
candidate construction
        ↓
candidate testing


prohibited:

hidden target relation
        ↓
candidate construction
```

The purpose of v4 is to test whether a productive relation can emerge from generic compositional primitives.

---

# 9. Discovery Partition

The discovery partition is used to construct candidate transformations.

It contains raw observations only:

```text
record_id
left
right
result
```

No evaluation labels are exposed.

The engine may inspect the complete structural content of the discovery observations.

The discovery stage must record provenance showing which observations contributed to each candidate.

---

# 10. Selection Partition

The selection partition is withheld from initial candidate construction.

Candidates are executed against the selection observations.

For each candidate:

```text
(left, right)
      ↓
candidate transformation
      ↓
predicted_result
```

The prediction is compared with the observed result only during evaluation.

The candidate therefore receives an empirical prediction record rather than merely a feature-support score.

---

# 11. Prediction Record

Each candidate evaluation should record:

```text
{
    "record_id": "...",
    "left": "...",
    "right": "...",
    "predicted_result": "...",
    "observed_result": "...",
    "prediction_correct": true
}
```

The distinction between prediction and observation must remain explicit.

The engine must not modify the candidate after seeing the result unless the protocol explicitly enters a revision stage.

---

# 12. Counterexample Partition

Counterexamples are used to test whether apparently productive transformations survive deliberately conflicting observations.

The counterexample stage should answer:

> Does the candidate continue to predict correctly when observations are selected specifically to distinguish competing transformations?

A candidate that fails its counterexamples is rejected.

A candidate that survives them remains viable.

However:

```text
counterexample survival ≠ proof
```

A candidate must still satisfy the holdout criterion.

---

# 13. Candidate Freeze

Before holdout access, the process must determine whether a candidate can be frozen.

A candidate may be frozen only if:

1. it is executable;
2. it generates predictions;
3. it has sufficient support on discovery/selection observations;
4. it survives counterexamples;
5. competing candidates are either rejected or otherwise discriminated;
6. the candidate transformation is fully specified;
7. its generation provenance is available;
8. no holdout information has influenced the candidate.

If multiple materially different candidates remain viable:

```text
STATUS = UNRESOLVED
```

No candidate is frozen.

---

# 14. Holdout Partition

The holdout partition remains completely inaccessible during candidate discovery and selection.

Only after candidate freeze may the frozen candidate be evaluated against holdout observations.

The holdout therefore tests:

```text
Can the transformation generate correct results
for previously unseen input combinations?
```

A candidate that merely describes the training data but fails to generate unseen results does not pass.

---

# 15. Productive Relation Criterion

The primary criterion of v4 is **productive prediction**.

A candidate demonstrates productive behavior only if it can:

```text
observe previous examples
        ↓
construct a transformation
        ↓
apply the transformation to new inputs
        ↓
generate a predicted result
        ↓
match previously unseen observations
```

The target is therefore not merely:

```text
descriptive regularity
```

but:

```text
predictive compositional relation
```

---

# 16. Candidate Competition

The experiment must explicitly preserve competing hypotheses.

For example:

```text
Candidate A:
T_A(left, right)

Candidate B:
T_B(left, right)

Candidate C:
T_C(left, right)
```

If all candidates produce equivalent predictions on the available evidence, the result remains:

```text
UNRESOLVED
```

The system must not select a candidate merely because it appears intuitively more meaningful.

Candidate selection must be evidence-based.

---

# 17. Equivalence and Redundancy

Two candidates may be structurally different but observationally equivalent on the available dataset.

Therefore the evaluator should distinguish:

```text
syntactic difference
```

from:

```text
predictive difference
```

If:

```text
T_A(x,y) = T_B(x,y)
```

for every tested input pair, the candidates may constitute an equivalence class rather than two independently distinguishable hypotheses.

The experiment should preserve this information rather than artificially selecting one.

---

# 18. Generalization Criterion

The strongest evidence comes from a candidate that predicts observations outside its construction data.

The required progression is:

```text
Discovery
    ↓
Candidate generation
    ↓
Selection prediction
    ↓
Counterexample testing
    ↓
Candidate freeze
    ↓
Holdout prediction
```

A candidate that succeeds only on discovery observations does not pass.

A candidate that succeeds on selection but fails holdout does not pass.

---

# 19. Semantic Independence

The discovery engine must not receive the semantic interpretation of the target relation.

The following remain prohibited:

```text
addition
numeral system
cardinality
arithmetic
combination
sum
```

as descriptions of the intended answer.

The engine operates on symbolic structures.

The external evaluator may know the hidden construction of the dataset.

Discovery and evaluation must remain epistemically separated.

---

# 20. Methodological Audit

The runner must report at least:

```text
predefined_candidate_family_used
semantic_labels_exposed_to_engine
holdout_used_during_discovery
candidate_generation_count
candidate_execution_count
candidate_selection_count
candidate_counterexample_count
frozen_candidate
holdout_evaluation_status
```

It must also report whether any candidate was supplied directly or whether all candidates were generated by the discovery process.

---

# 21. Required Experiment Output

The runner should produce:

```text
EXPERIMENT_RESULTS_v4.json
```

The result should contain at least:

```text
experiment_id
protocol_version
dataset_id
dataset_version
status

predefined_candidate_family_used
semantic_labels_exposed_to_engine
holdout_used_during_discovery

partition_counts

generated_candidate_count
generated_candidates

selection_evaluations
counterexample_evaluations

viable_candidate_ids
equivalent_candidate_groups

frozen_candidate

holdout_evaluation

unresolved_questions
level3_trace
methodological_audit
```

---

# 22. Status Rules

## PASS

The experiment may return:

```text
PASS
```

only if:

1. no predefined target invariant was supplied;
2. no semantic interpretation was exposed;
3. at least one executable compositional candidate was independently generated;
4. the candidate generated predictions on unseen input pairs;
5. the candidate survived counterexample testing;
6. candidate freeze occurred before holdout access;
7. holdout predictions were successful;
8. competing viable candidates were either eliminated or shown to be predictively equivalent;
9. provenance and generation trace are complete;
10. the result is reproducible.

---

## FAIL

The experiment returns:

```text
FAIL
```

if the protocol is violated or the frozen candidate fails the required prediction/generalization criteria.

Examples include:

* predefined target invariant supplied;
* semantic leakage;
* holdout contamination;
* candidate supplied rather than generated;
* candidate cannot execute;
* candidate fails required predictions;
* provenance is missing.

---

## UNRESOLVED

The experiment returns:

```text
UNRESOLVED
```

when the evidence is insufficient to distinguish competing hypotheses.

Examples:

* multiple materially different candidates remain viable;
* holdout evidence is insufficient;
* candidate predictions are observationally equivalent;
* candidate generation is incomplete;
* the transformation language is insufficient to discriminate hypotheses.

The protocol explicitly treats:

```text
UNRESOLVED ≠ PASS
```

---

# 23. Relationship to v3

v3 established:

```text
structural candidate generation
        +
selection
        +
counterexample testing
```

but retained a candidate representation dominated by:

```text
feature == value
```

v4 changes the fundamental candidate representation to:

```text
T(left, right) → result
```

The progression is therefore:

```text
v1
predefined candidate family

        ↓

v2
open structural candidate generation

        ↓

v3
candidate selection + counterexamples

        ↓

v4
productive compositional transformations
```

This is a change in experimental ontology, not merely an increase in dataset size.

---

# 24. What v4 Is Intended to Test

The experiment is intended to determine whether a Level 3 process can move from:

```text
"What properties characterize these observations?"
```

to:

```text
"What transformation connects these inputs to this output?"
```

and then further to:

```text
"Can that transformation generate a correct result
for an input combination it has not previously seen?"
```

This is the central methodological transition.

---

# 25. What v4 Does Not Test

Even a successful v4 result would not establish:

* semantic understanding;
* arithmetic understanding;
* consciousness;
* subjectivity;
* general intelligence;
* AGI;
* autonomous goals;
* phenomenal experience.

The experiment concerns a narrow property:

> productive compositional invariant discovery from symbolic observations.

---

# 26. Pre-Execution Freeze

Before the first execution of v4, the following must be frozen:

* protocol;
* dataset;
* discovery partition;
* selection partition;
* counterexample partition;
* holdout partition;
* structural operation vocabulary;
* candidate representation;
* candidate freeze criteria;
* evaluation procedure;
* result schema.

Any methodological change after execution constitutes a new experiment version.

---

# 27. Successive Experimental Logic

The intended research sequence is:

```text
v1
Can a predefined invariant be evaluated?

        ↓

v2
Can candidates be generated without a predefined invariant family?

        ↓

v3
Can structural candidates be filtered by prediction-oriented
selection and counterexamples?

        ↓

v4
Can the process generate an executable transformation
from inputs to output and use it to make new predictions?
```

Only if v4 establishes productive compositional prediction should the research proceed to the next epistemic question.

---

# 28. Final Research Principle

The v4 experiment adopts the following principle:

> **A productive invariant is not merely a property that remains true. It is a relation capable of generating a prediction.**

Therefore:

```text
descriptive regularity
        ≠
productive relation
```

and:

```text
prediction
        +
counterexample resistance
        +
holdout generalization
```

constitute the core evidential structure of the experiment.

The purpose of v4 is not to make the answer easier to find.

It is to make the distinction between **describing the observed world** and **generating a relation capable of producing new observations** experimentally testable.
