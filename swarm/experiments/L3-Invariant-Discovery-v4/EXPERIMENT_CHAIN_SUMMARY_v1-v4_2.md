# UFCPS — Level 3 Invariant Discovery

## Experimental Chain Summary v1–v4.2

**Experiment family:** `L3-Invariant-Discovery`
**Level:** 3 — Reflection
**Research question:** Can the Level 3 process discover and generalize a structural/compositional invariant from opaque symbolic observations without being given its semantic interpretation?

---

# 1. Purpose of the Experimental Chain

The experimental chain was designed to progressively test a stronger form of Level 3 behavior.

The initial question was whether a Level 3 process could identify a regularity in raw symbolic observations.

The experiment was deliberately constrained so that the discovery process would not be told that the observations represented:

* numbers;
* arithmetic;
* addition;
* counting;
* numeral systems;
* cardinality.

The experimental progression was:

```text
v1
Candidate evaluation
        ↓
v2
Candidate generation without predefined target family
        ↓
v3
Structural candidate generation + counterexamples
        ↓
v4
Executable compositional transformations
        ↓
v4.1
Methodological control failure identified
        ↓
v4.2
Discriminating controls + holdout generalization
```

The chain therefore moved from detecting structural regularity toward testing executable hypothesis selection.

---

# 2. v1 — Initial Invariant Discovery

## Research question

Can Level 3 identify a candidate invariant from raw symbolic observations?

The initial experiment used opaque symbolic examples such as:

```text
2      2      → 4
10     10     → 100
II     II     → IV
||||   ||||   → ||||||||
••     ••     → ••••
aa     aa     → aaaa
```

The system generated the candidate:

```text
RESULT_LENGTH_EQUALS_OPERAND_LENGTH_SUM
```

The candidate received support but also encountered challenges.

The experiment produced unresolved questions.

## Result

```text
STATUS: UNRESOLVED
```

## Interpretation

v1 demonstrated that a structural candidate could be formulated, but it did not establish that the process had independently discovered a productive invariant.

A major limitation was that the candidate family was effectively predefined.

---

# 3. v2 — Removal of the Predefined Candidate Family

## Methodological change

v2 removed the predefined target-invariant family.

The process was allowed to generate candidates from generic structural properties such as:

* length;
* equality;
* prefix/suffix;
* repeated-symbol structure;
* character multiplicity;
* positional correspondence;
* structural similarity;
* symbol-set relations;
* transformation relations.

The purpose was to test whether candidate generation could occur without being told what kind of invariant to search for.

## Technical result

The v2 benchmark infrastructure passed.

The actual discovery process generated:

```text
generated_candidate_count: 103
selection_status: MULTIPLE_VIABLE_CANDIDATES
```

## Result

```text
STATUS: UNRESOLVED
```

## Interpretation

The experiment demonstrated that removal of the predefined target family produced a large hypothesis space.

However:

> structural regularity did not uniquely identify a productive invariant.

Many candidates could explain the available observations.

This established an important methodological problem:

```text
structural regularity
        ≠
productive invariant
```

---

# 4. v3 — Candidate Selection and Counterexamples

## Methodological change

v3 introduced a more explicit discovery/selection structure.

The system generated executable structural candidates and subjected them to counterexample evaluation.

The actual run produced:

```text
discovery observations: 6
selection observations: 4
controls: 4
counterexamples: 4
holdout observations: 5

generated candidates: 36
viable candidates after counterexamples: 10
frozen candidate: NONE

STATUS: UNRESOLVED
```

Ten candidates survived the available counterexamples.

Examples included structural relations such as:

```text
length_difference == 0
left_equals_result == False
right_equals_result == False
result_matches_combined_counts == True
result_set_matches_combined_set == True
result_length_matches_combined_length == True
...
```

## Interpretation

v3 demonstrated that the process could:

1. generate multiple structural hypotheses;
2. evaluate them;
3. eliminate some using counterexamples;
4. retain provenance and candidate structure.

However, ten candidates remained viable.

No unique candidate could be frozen.

The key finding was:

> **Generating structural candidates and eliminating contradictions is insufficient when several hypotheses remain observationally compatible.**

This motivated a transition from descriptive structural properties to executable compositional relations.

---

# 5. v4 — Executable Compositional Relations

## Methodological change

v4 changed the candidate ontology.

Instead of:

```text
feature == value
```

the candidate became:

```text
T(left, right) → predicted_result
```

A candidate therefore had to:

* use both inputs;
* produce an output;
* be executable;
* make predictions on unseen input pairs.

The initial candidate space contained eight transformations:

```text
CONCAT_LEFT_RIGHT
CONCAT_RIGHT_LEFT
SORT_COMBINED_SYMBOLS
REVERSE_COMBINED_SYMBOLS
INTERLEAVE_LEFT_RIGHT
INTERLEAVE_RIGHT_LEFT
COMBINED_SYMBOL_COUNTS_CANONICAL
UNIQUE_COMBINED_SYMBOLS
```

The evaluator itself did not contain the intended target relation.

---

# 6. v4.1 — First Run and Methodological Failure

The first v4 dataset contained:

```text
discovery: 6
selection: 4
control: 4
counterexample: 4
holdout: 5
```

Four candidates survived selection:

```text
CAND_V4_0001  CONCAT_LEFT_RIGHT
CAND_V4_0003  SORT_COMBINED_SYMBOLS
CAND_V4_0007  COMBINED_SYMBOL_COUNTS_CANONICAL
CAND_V4_0008  UNIQUE_COMBINED_SYMBOLS
```

All four had perfect selection accuracy.

However, every control observation had been deliberately constructed as a violation of the hidden relation.

For example, a candidate could predict:

```text
ab + cd → abcd
```

while the control observation supplied:

```text
ab + cd → cdab
```

The candidate therefore necessarily failed.

## Result

```text
STATUS: UNRESOLVED
```

## Methodological diagnosis

This was not a failure of the executable candidate mechanism.

It was a failure in control design.

The experiment revealed:

> **A control that intentionally violates the hidden relation does not discriminate between competing hypotheses. It merely forces a correct hypothesis to fail.**

Therefore:

```text
Control ≠ negative example
```

A useful control must instead be:

```text
Control = valid observation on which competing hypotheses make different predictions
```

This became the central methodological correction of v4.2.

---

# 7. v4.2 — Discriminating Controls

## Methodological correction

v4.2 preserved the v4 candidate ontology:

```text
T(left, right) → predicted_result
```

and preserved the semantic isolation of the discovery process.

The control partition was redesigned.

All control observations are now valid observations of the same hidden relation.

Their purpose is to create **informative disagreement** between surviving hypotheses.

The experimental sequence became:

```text
Discovery
   ↓
Candidate Generation
   ↓
Selection
   ↓
Discriminating Controls
   ↓
Counterexamples
   ↓
Candidate Freeze
   ↓
Holdout
```

---

# 8. v4.2 Actual Result

The experiment was executed successfully.

```text
discovery observations: 6
selection observations: 4
controls: 4
counterexamples: 4
holdout observations: 5

generated candidates: 8
selection viable candidates: 7
control viable candidates: 1
discriminating controls: 4/4
viable candidates after counterexamples: 1
frozen candidate: CAND_V4_0001

STATUS: PASS
```

The frozen candidate was:

```text
CAND_V4_0001
CONCAT_LEFT_RIGHT
left + right
```

Thus:

```text
8 candidates
      ↓
7 survive selection
      ↓
4/4 controls discriminate
      ↓
1 survives control
      ↓
1 survives counterexamples
      ↓
candidate frozen
      ↓
holdout passed
      ↓
PASS
```

---

# 9. What v4.2 Actually Demonstrates

The result supports the following narrow statement:

> **Under the tested experimental conditions, the Level 3 process successfully selected a unique executable compositional relation from a predefined but semantically opaque hypothesis space, using discriminating observations, counterexample evaluation, candidate freezing, and unseen holdout data.**

The important elements are:

### 9.1 Semantic opacity

The discovery process was not given the semantic interpretation of the symbolic data.

### 9.2 Executability

Candidates were executable transformations rather than merely descriptive properties.

### 9.3 Compositionality

The candidate operated on both inputs:

```text
left + right
```

### 9.4 Hypothesis competition

Seven candidates initially survived selection.

### 9.5 Discrimination

All four control observations were discriminating.

```text
discriminating controls: 4/4
```

### 9.6 Unique selection

Only one candidate survived the control stage.

### 9.7 Falsification

The surviving candidate was evaluated against counterexamples.

### 9.8 Freeze-before-holdout

The candidate was frozen before holdout evaluation.

### 9.9 Generalization

The frozen candidate passed the holdout partition.

---

# 10. What v4.2 Does Not Demonstrate

The result does **not** establish:

* unrestricted invariant discovery;
* arbitrary hypothesis generation;
* semantic understanding;
* arithmetic understanding;
* consciousness;
* subjectivity;
* general intelligence;
* AGI;
* autonomous goals;
* independence from benchmark design;
* discovery outside the predefined transformation language.

The most important limitation is:

> **The eight executable transformation operations were specified in advance.**

Therefore the experiment tests:

```text
selection within a predefined executable hypothesis space
```

rather than:

```text
unrestricted construction of the hypothesis space itself
```

---

# 11. Methodological Progression

The experimental chain can therefore be represented as:

```text
v1
Structural candidate
        │
        │ limitation:
        │ predefined candidate family
        ▼
v2
Open structural candidate generation
        │
        │ limitation:
        │ many viable candidates
        ▼
v3
Candidate generation
+
counterexample elimination
        │
        │ limitation:
        │ multiple candidates remain
        ▼
v4
Executable compositional hypotheses
        │
        │ limitation:
        │ controls were invalid violations
        ▼
v4.1
Methodological failure identified
        │
        │ correction:
        │ controls become valid
        │ discriminating observations
        ▼
v4.2
Executable hypothesis selection
+
discriminating controls
+
counterexamples
+
holdout
        │
        ▼
PASS
```

---

# 12. Main Scientific Finding of the Chain

The most valuable result of the entire sequence is not simply the `PASS` of v4.2.

It is the progressive identification of what is required to turn a structural regularity into a meaningful hypothesis test.

The chain shows:

```text
regularity
    ↓
candidate
    ↓
multiple candidates
    ↓
executable candidates
    ↓
hypothesis competition
    ↓
discriminating observations
    ↓
falsification
    ↓
freeze
    ↓
holdout generalization
```

Each stage removes a different source of ambiguity.

---

# 13. Current Epistemic Status

The current result should therefore be recorded as:

```text
L3-INVARIANT-DISCOVERY-v1
UNRESOLVED

L3-INVARIANT-DISCOVERY-v2
UNRESOLVED

L3-INVARIANT-DISCOVERY-v3
UNRESOLVED

L3-INVARIANT-DISCOVERY-v4
UNRESOLVED
(methodological control flaw identified)

L3-INVARIANT-DISCOVERY-v4.1
HISTORICAL / SUPERSEDED
(control design flaw)

L3-INVARIANT-DISCOVERY-v4.2
PASS
```

But `PASS` applies specifically to the **v4.2 experimental claim**, not to unrestricted Level 3 invariant discovery.

---

# 14. The Boundary Reached by v4.2

The current architecture has crossed an important methodological boundary.

It can now perform:

```text
opaque observations
        ↓
predefined executable hypothesis space
        ↓
candidate generation
        ↓
selection
        ↓
discriminating evidence
        ↓
falsification
        ↓
unique candidate
        ↓
holdout generalization
```

The unresolved next question is therefore no longer:

> Can Level 3 distinguish competing executable hypotheses?

v4.2 provides evidence that it can within the tested hypothesis space.

The next question is stronger:

> **Can Level 3 construct the hypothesis space itself from lower-level structural primitives, rather than receiving the candidate transformations in advance?**

That is the methodological frontier beyond v4.2.

---

# 15. Final Chain Summary

The experimental chain has moved from:

```text
"What regularity is present?"
```

to:

```text
"Which executable hypothesis explains the observations?"
```

and v4.2 has demonstrated:

```text
multiple hypotheses
        ↓
informative disagreement
        ↓
hypothesis elimination
        ↓
unique executable candidate
        ↓
unseen-data validation
```

This is a substantially stronger experimental object than the original v1 test.

The next level should therefore not merely add more data.

It should attack the remaining dependency:

```text
PREDEFINED TRANSFORMATION CATALOG
```

The critical next experiment is to replace the fixed eight-operation catalogue with a compositional construction mechanism whose primitive vocabulary is itself structurally neutral.

That would test whether the process can move from:

```text
hypothesis selection
```

to:

```text
hypothesis construction
```

without semantic leakage.
