# UFCPS — Level 3 Invariant Discovery Experiment

## Experiment ID

`L3-Invariant-Discovery-v1`

## Status

Experimental protocol — v1

## 1. Purpose

The experiment tests whether a UFCPS process can discover a stable invariant from heterogeneous raw observations without being explicitly told the semantic domain of the observations.

The process must not be told that the dataset concerns:

* arithmetic;
* numbers;
* numeral systems;
* addition;
* notation;
* historical representations;
* or any other human semantic category.

The process receives only structured observations.

---

## 2. Experimental question

The primary question is:

> Can the process identify a relation that remains stable across different surface representations of the observed input-output structures?

The experiment is **not** designed to test whether the process understands arithmetic.

It tests whether the process can detect structural regularity that is preserved despite variation in representation.

---

## 3. Input available to the process

The process receives records of the form:

```text
left
right
result
```

Example:

```text
2
2
11
```

or:

```text
II
II
IV
```

or:

```text
10
10
100
```

The symbols themselves have no semantic explanation supplied by the experiment.

The process may compare:

* symbol identity;
* repetition;
* ordering;
* length;
* structural composition;
* relations between input and output;
* recurrence of transformations across records.

The process must derive any higher-level regularity from the observations.

---

## 4. Hidden semantic information

The following information is withheld from the process:

* what the symbols represent;
* whether different symbol sets belong to different notation systems;
* whether a symbol represents a quantity;
* what operation is being represented;
* what the expected invariant is;
* which examples are historical and which are synthetic;
* which examples belong to the holdout set.

This information belongs exclusively to the external evaluation layer.

---

## 5. Dataset structure

The experiment uses three logical subsets.

### 5.1 Training observations

These observations are available during invariant discovery.

They contain multiple surface representations exhibiting a common structural relation.

The process is free to search for regularities among them.

### 5.2 Negative controls

These observations contain deliberately violated relations.

They are required to determine whether the process has identified a stable relation rather than simply declaring every observed transformation valid.

### 5.3 Holdout observations

These observations are withheld during discovery.

They use combinations or structures not directly present in the training observations.

The holdout set tests whether a proposed invariant generalizes beyond memorized examples.

---

## 6. Critical separation

The experiment has two different objects:

### Process hypothesis

The invariant proposed by the UFCPS process.

### Evaluation oracle

The independently defined criterion used to determine whether the proposed invariant correctly explains the dataset.

The process must not receive the evaluation oracle.

The evaluator must not modify the criterion after seeing the process output.

---

## 7. What counts as invariant discovery

A candidate invariant is considered structurally meaningful only if it satisfies all of the following:

1. It explains multiple training observations.
2. It is not dependent on the literal identity of one particular symbol.
3. It distinguishes positive observations from negative controls.
4. It generates correct predictions for previously unseen holdout observations.
5. It can be expressed independently of the historical or human name of the representation.
6. It remains consistent when the same underlying relation is expressed using different symbol structures.

A candidate that merely memorizes:

```text
"2 + 2 → 11"
```

is not sufficient.

A candidate that identifies a reusable relation applicable to previously unseen symbol structures is stronger evidence of invariant discovery.

---

## 8. Required output of the process

The process should produce, at minimum:

```text
1. candidate invariant
2. supporting observations
3. observations that contradict or challenge it
4. predicted results for holdout observations
5. confidence/status of the candidate
6. unresolved questions
```

The process should be allowed to return:

```text
UNRESOLVED
```

if it cannot establish a sufficiently stable invariant.

This is a valid experimental outcome.

---

## 9. Negative controls

Negative controls are essential.

Without them, the experiment could mistake unrestricted pattern generation for invariant discovery.

The process therefore has to distinguish between:

```text
observed regularity
```

and:

```text
regularity that survives contradiction
```

A candidate invariant that accepts both positive examples and deliberately contradictory controls without modification fails the discrimination requirement.

---

## 10. Holdout test

After the discovery phase, the candidate invariant is evaluated against observations that were not available during discovery.

The evaluator records:

```text
holdout_correct
holdout_incorrect
holdout_unresolved
```

The process must not receive feedback from the holdout evaluation before its candidate invariant is frozen.

---

## 11. Independence requirement

The experiment must not encode the desired invariant into the transition mechanism.

In particular, the experiment must not contain an instruction equivalent to:

```text
find addition
find arithmetic
find cardinality
find a numeral system
find conserved quantity
```

The evaluator may know these properties.

The process may not.

This distinction is central to the experiment.

---

## 12. PASS criterion

The experiment receives:

```text
PASS
```

only if the process:

1. produces a candidate invariant;
2. applies it across multiple heterogeneous observations;
3. rejects or identifies the negative controls as inconsistent;
4. successfully predicts the required holdout cases;
5. does not require the semantic labels withheld by the experiment;
6. preserves an explicit distinction between established observations and unresolved cases.

PASS means:

> The tested process demonstrated the ability to generate and apply a representation-independent structural hypothesis under the defined experimental conditions.

It does **not** mean that the process has demonstrated general intelligence, understanding, consciousness, creativity, or autonomous scientific reasoning.

---

## 13. FAIL criterion

The experiment receives:

```text
FAIL
```

if the process is unable to satisfy the predefined discovery criterion.

Examples include:

* pure memorization;
* inability to distinguish positive and negative controls;
* systematic failure on holdout observations;
* candidate invariant dependent on explicit semantic labels;
* contradiction between the claimed invariant and the process's own predictions;
* inability to maintain a stable candidate hypothesis.

FAIL is an informative architectural result.

It means that the tested implementation did not satisfy the predefined criterion.

---

## 14. UNRESOLVED criterion

The experiment receives:

```text
UNRESOLVED
```

when the available evidence is insufficient to establish either successful invariant discovery or failure of the architecture.

Examples:

* several competing invariants explain the training data equally well;
* holdout data are insufficient to discriminate between candidates;
* the process identifies a plausible invariant but cannot formulate it sufficiently clearly for independent evaluation;
* the evaluation mechanism itself becomes ambiguous;
* the process produces contradictory hypotheses without enough evidence to select among them.

The rule is:

```text
UNRESOLVED ≠ PASS
```

No positive architectural claim is made from an unresolved result.

---

## 15. Frozen criterion

Before the first experimental run, the following must remain fixed:

* dataset version;
* training/control/holdout partition;
* success criterion;
* failure criterion;
* unresolved criterion;
* evaluator logic;
* process input format.

Any later modification must receive a new version.

For example:

```text
v1 → v2
```

rather than silently modifying v1.

---

## 16. Experimental controls

The experiment should eventually include at least the following controls.

### Control A — Memorization

Test whether the process can appear successful by reproducing literal training transformations without discovering a transferable rule.

### Control B — Surface similarity

Test whether the process is merely grouping observations according to symbol shape or string similarity.

### Control C — Representation change

Introduce structurally different symbol alphabets while preserving the underlying relation.

### Control D — Contradiction

Introduce observations that violate the candidate relation.

### Control E — Holdout generalization

Test the candidate on previously unseen combinations.

---

## 17. Interpretation boundary

A successful result would establish only the following narrow proposition:

> Under the defined conditions, the tested UFCPS process can generate a structural hypothesis from heterogeneous symbolic observations and apply that hypothesis beyond the exact training examples.

It would not establish:

* understanding;
* arithmetic competence in the human sense;
* semantic comprehension;
* consciousness;
* subjectivity;
* creativity;
* general intelligence;
* autonomy;
* AGI.

Those require independent experiments.

---

## 18. Relation to Level 3

This experiment belongs to the Level 3 research question:

```text
Continuity
    ↓
Recursion
    ↓
Reflection
    ↓
Reflexive transformation
    ↓
Invariant discrimination
```

The experiment therefore asks whether the process can use its accumulated observations to distinguish a stable relation from merely local or superficial regularities.

This is deliberately narrower than a subjectivity test.

---

## 19. Epistemic stopping rule

The experiment follows the UFCPS epistemic invariant:

```text
PASS
  ↓
NEXT LEVEL

FAIL
  ↓
STOP

UNRESOLVED
  ↓
OPEN QUESTION
```

The result of this experiment determines whether the next experimental question is justified.

---

## 20. Reproducibility

Every execution must record:

```text
experiment_id
dataset_version
protocol_version
process_version
evaluator_version
timestamp
result
candidate_invariant
supporting_observations
contradicting_observations
holdout_predictions
unresolved_questions
```

The execution artifact must be kept inside:

```text
swarm/experiments/L3-Invariant-Discovery-v1/
```

No result from this experiment should be mixed with the permanent Level 3 benchmark artifacts until the experiment has reached a documented conclusion.

---

## 21. Current artifact registry

Current experiment directory:

```text
swarm/experiments/L3-Invariant-Discovery-v1/
```

Current artifacts:

```text
level3_invariant_discovery_dataset_v1.json
experiment_protocol_v1.md
```

No implementation or result file is implied by this protocol.

---

## 22. Final experimental rule

The central rule is:

> The process must discover the invariant; the experiment must not teach it the invariant.

The evaluator knows what is being tested.

The process does not.
