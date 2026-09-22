# L3 Invariant Discovery — Experimental Results v1

**Experiment:** L3-Invariant-Discovery-v1
**Version:** 1.0
**Status:** UNRESOLVED
**Experiment folder:** `swarm/experiments/L3-Invariant-Discovery-v1/`

---

## 1. Purpose

This experiment tests whether the Level 3 architecture can identify a structural invariant from observations presented without semantic domain labels.

The experiment deliberately separates:

1. raw observations;
2. candidate invariant generation;
3. contradiction/control testing;
4. holdout evaluation;
5. Level 3 recursive processing.

The central question is:

> Can the process identify a relation that remains meaningful across different symbolic representations rather than merely reproducing a surface pattern?

The experiment does **not** attempt to establish arithmetic understanding, semantic understanding, consciousness, creativity, general intelligence, or AGI.

---

## 2. Experimental principle

The process receives observations in raw symbolic form.

Semantic names such as:

* arithmetic;
* numbers;
* addition;
* numeral systems;
* Roman numerals;
* binary;
* ternary;
* unary;
* Mayan notation;

are not exposed to the discovery process.

The experiment therefore operates on structural properties of the supplied observations.

The protocol distinguishes:

```text
OBSERVATION
    ↓
CANDIDATE RELATION
    ↓
SUPPORT / CONTRADICTION
    ↓
HOLDOUT TEST
    ↓
PASS / FAIL / UNRESOLVED
```

The important epistemic rule is:

> `UNRESOLVED ≠ PASS`

A candidate that explains only part of the observations must not be promoted to an established invariant.

---

## 3. Experiment artifacts

The experiment is isolated in:

```text
swarm/experiments/L3-Invariant-Discovery-v1/
```

Current artifacts:

```text
level3_invariant_discovery_dataset_v1.json
experiment_protocol_v1.md
invariant_discovery_runner_v1.py
invariant_discovery_adapter_v1.py
EXPERIMENT_RESULTS_v1.md
```

The experiment uses a dedicated directory so that the complete experimental state can be removed without affecting the main Level 3 architecture if the experiment is later rejected or replaced.

---

## 4. Dataset structure

The dataset contains three logical groups:

### Training observations

The training set contains multiple symbolic representations exhibiting regularities.

Examples include:

```text
2      + 2      → 4
2      + 2      → 11
10     + 10     → 100
II     + II     → IV
||||   + ||||   → ||||||||
••     + ••     → ••••
XX     + XX     → XXXX
aa     + aa     → aaaa
```

The discovery process receives the symbolic structures rather than their semantic interpretation.

### Negative controls

The control observations deliberately violate candidate structural relations.

Examples include:

```text
2      + 2      → 5
10     + 10     → 101
II     + II     → V
||||   + ||||   → |||||||
```

The purpose of the controls is to distinguish a genuine explanatory relation from a trivial rule that accepts everything.

### Holdout observations

The holdout set is withheld from candidate discovery and is intended to test whether a frozen candidate generalizes beyond the observations used to generate it.

The holdout therefore provides an independent test of the candidate rather than additional discovery material.

---

## 5. Technical execution

The GitHub Actions Level 3 workflow completed successfully.

Environment:

```text
Python 3.11.16
```

The repository environment check reported:

```text
Python environment: READY
UFCPS files: READY
Module discovery: READY
Imports: READY
```

The existing Level 3 benchmarks also passed.

### Full-cycle benchmark

```text
all_passed: True
```

All checks passed, including:

* exhaustion detection;
* frustration activation;
* reflection activation;
* self/world differentiation;
* orthogonal-transition preparation;
* multiple transition branches;
* branch interaction;
* new distinction detection;
* candidate invariant detection;
* question persistence;
* successor-space creation;
* process continuity;
* non-termination after local failure.

### Recursive-space benchmark

```text
all_passed: True
```

The recursive sequence remained:

```text
C_0 → C_1 → C_2
```

with:

```text
c0_distinctions: 2
c1_distinctions: 4
c2_distinctions: 6
```

The benchmark confirmed persistence of previous content, addition of new content, provenance preservation, question accumulation, and continuation after local deadlock.

### Emergent integration

```text
all_passed: True
```

The integration produced:

```text
exploration_branch_count: 3
interaction_status: BOTH
emergent_record_count: 5
question_count: 9
event_count: 6
next_space_version: 2
process_terminated: False
```

These results establish that the invariant-discovery experiment was executed on top of a functioning Level 3 recursive process rather than an isolated mock implementation.

---

## 6. Invariant Discovery Adapter Result

The dedicated adapter completed execution successfully.

Reported status:

```text
status: CANDIDATE
```

The selected candidate was:

```text
RESULT_LENGTH_EQUALS_OPERAND_LENGTH_SUM
```

with the structural formulation:

```text
result_length == left_length + right_length
```

The candidate received:

```text
training_support:
    S01
    S02

training_challenges:
    S03
    S04
```

Thus the candidate explains part of the observations but is contradicted by other training observations.

This is the critical result of the current stage.

The adapter therefore did **not** report an established invariant.

---

## 7. Interpretation of the candidate

The candidate captures a surface structural regularity.

For example:

```text
aa + aa → aaaa
```

has:

```text
2 + 2 = 4
```

in terms of symbol-string lengths.

Likewise:

```text
•• + •• → ••••
```

has the same length relation.

However:

```text
II + II → IV
```

does not satisfy the proposed string-length relation, because:

```text
length(IV) = 2
```

while:

```text
length(II) + length(II) = 4
```

Similarly:

```text
xx + xx → xxxxx
```

does not satisfy the candidate.

Therefore the candidate cannot yet serve as a general invariant for the dataset.

---

## 8. What the experiment established

The current stage establishes the following:

### 8.1 The experimental pipeline executes

The dataset, protocol, adapter, Level 3 components, and GitHub Actions environment operate together without runtime failure in the main workflow.

### 8.2 A structural candidate can be generated

The adapter can identify a nontrivial structural regularity from raw symbolic observations.

### 8.3 Controls can challenge the candidate

The candidate is not automatically accepted when contradictory observations are present.

### 8.4 Unresolved state is preserved

The process retains unresolved questions instead of converting an incomplete candidate into a confirmed result.

### 8.5 Level 3 recursive continuity remains intact

The invariant-discovery experiment does not terminate the Level 3 process.

The system continues to generate successor cognitive spaces and questions.

The system diagnostic recorded:

```text
cycle_1: C_k → C_k+1
cycle_2: C_k+1 → C_k+1+1
```

with:

```text
cycle_1_continuation: True
cycle_2_continuation: True
process_terminated: False
```

The diagnostic also recorded:

```text
uql_event_count: 12
uql_question_count: 18
runtime_error_count: 0
```

---

## 9. What the experiment did NOT establish

The current result does **not** establish that Level 3 independently discovers arbitrary invariants.

In particular, the current adapter contains a predefined candidate family.

The experiment therefore currently tests:

> whether the process can evaluate and select a structural relation from a predefined candidate space.

It does not yet fully test:

> whether the process can construct the candidate space itself from observations.

This distinction is essential.

---

## 10. Methodological limitation

The current adapter contains candidate relations including:

```text
RESULT_LENGTH_EQUALS_OPERAND_LENGTH_SUM
RESULT_EQUALS_LITERAL_CONCATENATION
```

Therefore the candidate search space is constrained by the experiment designer.

This introduces an experimental dependency:

```text
observations
      ↓
predefined candidate family
      ↓
candidate selection
```

rather than the stronger architecture:

```text
observations
      ↓
generated relation space
      ↓
candidate generation
      ↓
candidate testing
      ↓
candidate revision/rejection
```

Consequently, the present experiment must not be described as a demonstration of fully endogenous invariant discovery.

---

## 11. Level 3 bridge issue

The adapter reported:

```text
level3_bridge:
    available: False
    error: "No module named 'level3_emergent_integration_v1'"
```

This is a technical integration issue in the standalone execution of the adapter.

It does not correspond to a failure of the Level 3 integration benchmark itself.

The repository environment check successfully imported:

```text
swarm.level3_emergent_integration_v1
```

and the dedicated Level 3 emergent integration benchmark passed.

Therefore the current interpretation is:

```text
Level 3 implementation: operational
Invariant-discovery adapter: operational
Standalone adapter → Level 3 bridge import: unresolved technical issue
```

The bridge problem must be corrected before treating the adapter as fully integrated with the Level 3 runtime.

---

## 12. Epistemic status

The experiment is classified:

```text
UNRESOLVED
```

not:

```text
PASS
```

and not:

```text
FAIL
```

The reason is that the experimental mechanism successfully produced and challenged a candidate, but the candidate was not sufficient to explain the observations and the candidate-generation space remains partially predefined.

The result therefore provides useful evidence about the architecture without satisfying the stronger discovery criterion.

---

## 13. Current scientific boundary

The strongest justified statement from this stage is:

> **The current Level 3 experimental pipeline can generate a structural candidate from raw symbolic observations, test that candidate against contradictory observations, retain unresolved questions, and continue the recursive process without terminating. However, independent invariant discovery has not yet been demonstrated because the current adapter searches within a predefined candidate family.**

This is the current boundary of the evidence.

---

## 14. Next experimental question

The next experiment should remove the predefined candidate family as far as technically possible.

The intended architecture is:

```text
RAW OBSERVATIONS
        ↓
STRUCTURAL EXTRACTION
        ↓
RELATION GENERATION
        ↓
CANDIDATE SPACE
        ↓
CANDIDATE TESTING
        ↓
CONTRADICTION
        ↓
REVISION / REJECTION
        ↓
HOLDOUT
```

The central question becomes:

> **Can the Level 3 process generate a candidate invariant without being given a predefined list of candidate relations?**

A successful result would require more than finding a relation.

The process would need to:

1. generate a candidate relation from observations;
2. expose the relation in an explicit form;
3. test it against positive observations;
4. reject or modify it when contradicted;
5. preserve unresolved alternatives;
6. apply a frozen candidate to withheld observations;
7. avoid using semantic domain labels;
8. avoid receiving the intended invariant directly from the experiment.

---

## 15. Experimental discipline

The following rule remains fixed:

> **The process must discover the invariant; the experiment must not teach it the invariant.**

The experiment also retains the general UFCPS epistemic invariant:

```text
PASS         → NEXT LEVEL
FAIL         → STOP
UNRESOLVED   → OPEN QUESTION
```

Therefore the current result opens the next experimental question rather than being converted into a success claim.

---

## 16. Conclusion

The first invariant-discovery stage was technically successful but scientifically unresolved.

The important outcome is not that the adapter produced a candidate. The important outcome is that the candidate was **not accepted merely because it matched some observations**.

A structural hypothesis was produced:

```text
RESULT_LENGTH_EQUALS_OPERAND_LENGTH_SUM
```

and immediately exposed to contradictory observations.

The process therefore demonstrated a preliminary cycle of:

```text
observation
    ↓
structural candidate
    ↓
support
    ↓
contradiction
    ↓
unresolved state
```

The next stage must move the experimental boundary from **candidate selection** toward **candidate generation**.

Only then can the stronger question of endogenous invariant discovery be tested.

---

**Experimental status: `UNRESOLVED`**

**Next target: candidate generation without a predefined invariant family.**
