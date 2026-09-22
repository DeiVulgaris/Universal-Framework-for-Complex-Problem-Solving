# L3 Invariant Discovery v3 — Experiment Results

**Experiment:** UFCPS-L3-INVARIANT-DISCOVERY-v3
**Protocol:** v3.0
**Dataset:** UFCPS-L3-INVARIANT-DISCOVERY-v3
**Status:** `UNRESOLVED`

---

## 1. Research Question

The experiment asks:

> Can the Level 3 process generate a candidate invariant from raw symbolic observations without being given a predefined family of candidate invariants, and distinguish a productive relation through prediction and counterexample resistance?

The experiment is intended to move beyond simple structural regularity and test whether candidate relations can survive a progressively stronger selection process.

---

## 2. Experimental Status

The final result is:

```text
UNRESOLVED
```

This is an epistemically valid result.

The experiment did not establish a unique productive invariant before holdout evaluation.

The experiment therefore does not pass the Level 3 invariant-discovery criterion.

It also does not constitute a failure of the experimental pipeline itself.

---

## 3. Execution Summary

The experiment was executed with the following configuration:

```text
predefined_candidate_family_used: False
semantic_labels_exposed_to_engine: False
holdout_used_during_discovery: False
```

Observed partitions:

| Partition              | Count |
| ---------------------- | ----: |
| Discovery observations |     6 |
| Selection observations |     4 |
| Controls               |     4 |
| Counterexamples        |     4 |
| Holdout observations   |     5 |

Candidate generation produced:

```text
generated candidates: 36
```

After selection and counterexample testing:

```text
viable candidates: 10
frozen candidate: NONE
```

Because more than one candidate remained viable, the freeze criterion was not satisfied.

Holdout evaluation was therefore not performed.

---

## 4. Candidate Generation

The v3 process generated 36 structural candidates from the available observations.

Unlike v1, no predefined invariant family was supplied.

Unlike v2, the experiment introduced a selection stage and explicit counterexample testing intended to eliminate candidates that failed to remain predictive under additional observations.

The resulting candidates were nevertheless largely expressed as structural feature regularities.

Examples include relations of the form:

```text
length_difference == 0
left_equals_result == False
right_equals_result == False
result_matches_combined_counts == True
result_set_matches_combined_set == True
result_length_matches_combined_length == True
```

This distinction is important.

A statement such as:

```text
length_difference == 0
```

describes a regularity of the observations.

It does not, by itself, specify how the result is generated from the two inputs.

---

## 5. Viable Candidates

Ten candidates survived both the selection stage and the counterexample stage.

### CAND_V3_0008

```text
relation_type:
OBSERVATION_FEATURE_EQUALS

feature:
length_difference

value:
0
```

Interpretation:

```text
The two input strings have equal length.
```

---

### CAND_V3_0010

```text
relation_type:
OBSERVATION_FEATURE_EQUALS

feature:
left_equals_result

value:
False
```

Interpretation:

```text
The left input is not identical to the result.
```

---

### CAND_V3_0011

```text
relation_type:
OBSERVATION_FEATURE_EQUALS

feature:
right_equals_result

value:
False
```

Interpretation:

```text
The right input is not identical to the result.
```

---

### CAND_V3_0025

```text
relation_type:
OBSERVATION_FEATURE_EQUALS

feature:
result_matches_combined_counts

value:
True
```

This candidate is structurally more informative because it relates the symbol multiplicities of the result to the combined multiplicities present in the two inputs.

It is nevertheless still represented as a predefined structural feature assertion rather than as an independently generated compositional transformation.

---

### CAND_V3_0026

```text
relation_type:
OBSERVATION_FEATURE_EQUALS

feature:
result_set_matches_combined_set

value:
True
```

Interpretation:

```text
The set of symbols occurring in the result
matches the combined symbol set of the inputs.
```

---

### CAND_V3_0027

```text
relation_type:
OBSERVATION_FEATURE_EQUALS

feature:
result_length_matches_combined_length

value:
True
```

Interpretation:

```text
The result length equals the combined lengths of the two inputs.
```

---

### CAND_V3_0029

```text
relation_type:
OBSERVATION_FEATURE_EQUALS

feature:
result_matches_right_left_concat

value:
False
```

---

### CAND_V3_0031

```text
relation_type:
OBSERVATION_FEATURE_EQUALS

feature:
right_prefix_of_result

value:
False
```

---

### CAND_V3_0032

```text
relation_type:
OBSERVATION_FEATURE_EQUALS

feature:
left_suffix_of_result

value:
False
```

---

### CAND_V3_0036

```text
relation_type:
OBSERVATION_FEATURE_EQUALS

feature:
result_equals_reverse_sorted_operands

value:
False
```

---

## 6. Counterexample Result

All ten surviving candidates remained supported after the counterexample stage.

For the viable candidates:

```text
support:
C01, C02, C03, C04

challenges:
none
```

Therefore:

```text
counterexamples did not discriminate between the remaining candidates.
```

This is the central result of v3.

The counterexample set was sufficient to eliminate some generated relations, but insufficient to isolate a unique productive relation.

---

## 7. Why the Experiment Remained UNRESOLVED

The experiment requires a unique candidate to be frozen before holdout evaluation.

The actual result was:

```text
36 generated candidates
        ↓
10 viable candidates
        ↓
no unique candidate
        ↓
no candidate freeze
        ↓
no holdout evaluation
        ↓
UNRESOLVED
```

This prevents the experiment from claiming that one discovered relation generalizes to previously unseen observations.

The unresolved state is therefore not caused by a technical execution failure.

It reflects insufficient discrimination between competing hypotheses.

---

## 8. Methodological Finding

The most important finding of v3 is that **counterexample resistance alone is not sufficient when the candidate space contains many structural regularities**.

Several candidates can simultaneously describe the observed data without explaining the transformation that connects the inputs to the output.

For example:

```text
result_length_matches_combined_length == True
```

and

```text
result_matches_combined_counts == True
```

may both hold for the same observations.

The first describes a quantitative structural property.

The second describes a stronger relation involving symbol multiplicities.

Neither statement, however, is yet represented as a general transformation:

```text
(left, right) → result
```

This distinction becomes important for the next experimental stage.

---

## 9. Feature Regularity vs. Productive Relation

The current v3 candidate space is dominated by relations of the form:

```text
feature(observation) == value
```

A productive invariant requires a stronger representation:

```text
left
  +
right
  ↓
structural transformation
  ↓
result
```

The research problem therefore changes from:

> Which property remains true across the observations?

to:

> Which relation between the inputs and the output generates a prediction that survives counterexamples and previously unseen observations?

This is a substantially stronger criterion.

---

## 10. What v3 Demonstrates

The v3 experiment demonstrates that the Level 3 experimental pipeline can:

1. operate without a predefined candidate family;
2. generate multiple structural candidate relations from raw observations;
3. separate discovery, selection, counterexample, and holdout partitions;
4. evaluate candidates against additional observations;
5. reject candidates that fail available tests;
6. retain multiple surviving hypotheses when the evidence does not discriminate them;
7. prevent holdout evaluation before candidate freeze;
8. preserve the unresolved state rather than forcing a conclusion.

These are methodological capabilities of the experimental architecture.

---

## 11. What v3 Does Not Demonstrate

The experiment does **not** demonstrate:

* independent discovery of a unique invariant;
* semantic understanding of the hidden relation;
* general arithmetic understanding;
* autonomous hypothesis selection;
* general intelligence;
* consciousness or subjectivity;
* that the surviving candidate `CAND_V3_0025` is the discovered invariant;
* successful holdout generalization.

In particular, `CAND_V3_0025` should not be promoted to a discovered invariant merely because it is structurally more informative than some competing candidates.

---

## 12. Relation to Previous Experiments

The experimental progression is:

### v1

A predefined candidate family was supplied.

Result:

```text
UNRESOLVED
```

The experiment showed that the pipeline could evaluate a candidate family, but did not establish independent invariant discovery.

### v2

The predefined candidate family was removed.

The system generated:

```text
103 candidates
```

Multiple viable candidates remained.

Result:

```text
UNRESOLVED
```

This established open structural candidate generation, but not unique invariant discovery.

### v3

The process was extended with selection and counterexample testing.

The system generated:

```text
36 candidates
```

After counterexample testing:

```text
10 viable candidates
```

No unique candidate could be frozen.

Result:

```text
UNRESOLVED
```

Thus v3 represents a methodological progression rather than a failed repetition.

---

## 13. Current Epistemic Position

The current evidence supports the following statement:

> The Level 3 experimental pipeline can generate structural hypotheses from raw symbolic observations and test their persistence against selection and counterexample partitions. In the v3 experiment, this process reduced 36 generated candidates to 10 viable candidates, but did not establish a unique productive invariant before holdout evaluation. Independent invariant discovery therefore remains unresolved.

This is the strongest conclusion supported by the current experiment.

---

## 14. Next Experimental Problem

The next experiment should not simply add more counterexamples.

The central unresolved problem is the representation of the candidate itself.

The next stage should investigate whether the system can generate and compare **compositional relations** between inputs and output rather than only feature regularities.

Conceptually:

```text
CURRENT:

observation
    ↓
structural feature
    ↓
feature == value


NEXT:

left ─────┐
          ├──→ structural transformation ──→ result
right ────┘
```

The key question becomes:

> Can a candidate structural relation demonstrate productivity through prediction and counterexample resistance without the process being given the semantic interpretation of the target relation?

A successful experiment would require a candidate to do more than describe already observed regularities.

It would need to generate predictions about previously unseen input-output configurations.

---

## 15. Epistemic Status

```text
v1  → UNRESOLVED
v2  → UNRESOLVED
v3  → UNRESOLVED
```

The sequence nevertheless shows methodological progression:

```text
predefined candidate family
        ↓
open structural candidate generation
        ↓
candidate selection
        ↓
counterexample testing
        ↓
productive relation requirement
```

The invariant-discovery problem remains open.

No claim of successful independent invariant discovery is made at this stage.

---

## 16. Reproducibility Record

Experiment:

```text
UFCPS-L3-INVARIANT-DISCOVERY-v3
```

Protocol:

```text
3.0
```

Dataset:

```text
UFCPS-L3-INVARIANT-DISCOVERY-v3
```

Final status:

```text
UNRESOLVED
```

Generated candidates:

```text
36
```

Viable candidates:

```text
10
```

Frozen candidate:

```text
NONE
```

Holdout evaluation:

```text
NOT PERFORMED
```

Reason:

```text
Unique productive candidate was not established before holdout access.
```

---

## 17. Final Conclusion

v3 does not solve invariant discovery.

It does something more useful for the research program: it identifies the next precise methodological bottleneck.

The problem is no longer simply generating candidates or exposing them to counterexamples.

The next challenge is to distinguish:

```text
a property that happens to remain true
```

from

```text
a relation that can generate a correct prediction.
```

That distinction defines the next experimental step.
