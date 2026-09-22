# L3 Invariant Discovery — Experimental Results v2

## 1. Experiment

**Experiment ID:** `UFCPS-L3-INVARIANT-DISCOVERY-v2`

**Version:** `2.0`

**Purpose:**

Determine whether the Level 3 process can generate candidate invariant relations from raw symbolic observations without being supplied with a predefined family of intended invariants.

The experiment is designed to separate:

1. structural observation,
2. relation generation,
3. candidate generation,
4. candidate evaluation,
5. candidate freezing,
6. holdout evaluation.

---

## 2. Experimental Status

**Overall status: `UNRESOLVED`**

The experiment did not produce a unique candidate invariant.

This is an experimental result, not a technical failure.

The process correctly returned `UNRESOLVED` because multiple candidates remained viable after training/control evaluation.

---

## 3. Technical Components

The following components were implemented and tested:

* `experiment_protocol_v2.md`
* `invariant_relation_generator_v2.py`
* `invariant_relation_generator_benchmark_v2.py`
* `invariant_candidate_evaluator_v2.py`
* `invariant_discovery_runner_v2.py`
* `level3_invariant_discovery_dataset_v2.json`

The complete experiment is contained in:

`swarm/experiments/L3-Invariant-Discovery-v2/`

---

## 4. Generator Benchmark

The structural relation generator passed all technical checks.

### Result

```text
UFCPS — L3 Invariant Relation Generator Benchmark v2

predefined_candidate_family_used: False
semantic_labels_exposed_to_engine: False

Checks:

PASS: raw_observations_available
PASS: structural_features_available
PASS: relations_are_data_derived
PASS: candidate_generation_available
PASS: candidate_provenance_available
PASS: no_semantic_labels_exposed
PASS: changed_symbols_produce_structural_output
PASS: changed_structure_is_observable
PASS: empty_input_handled

all_passed: True
RESULT: READY
```

### Interpretation

The generator can:

* receive raw symbolic observations;
* extract neutral structural properties;
* generate structural relations;
* construct candidate relations from recurring observations;
* preserve candidate provenance;
* operate without semantic domain labels;
* detect changes in symbol and structural configuration.

This establishes the technical readiness of the v2 relation-generation component.

It does **not** by itself establish invariant discovery.

---

## 5. Candidate Evaluator

The candidate evaluator also passed its technical test.

### Result

```text
UFCPS — L3 Candidate Evaluator v2

experiment: UFCPS-L3-INVARIANT-DISCOVERY-v2
version: 2.0
candidate_id: CAND_TEST

training_support: ['T01', 'T02']
training_challenges: ['T03', 'C01']

holdout_prediction_count: 3
frozen: True
status: READY

RESULT: READY
```

The evaluator demonstrated that a candidate can be:

1. evaluated against training observations;
2. challenged by control observations;
3. frozen;
4. evaluated against a separate holdout set.

---

## 6. Full v2 Experiment Run

The integrated runner produced:

```text
UFCPS — L3 Invariant Discovery Runner v2

experiment: UFCPS-L3-INVARIANT-DISCOVERY-v2
dataset: UFCPS-L3-INVARIANT-DISCOVERY-v2
dataset_version: 2.0

predefined_candidate_family_used: False
semantic_labels_exposed_to_engine: False
holdout_used_during_discovery: False

generated_candidate_count: 103
selection_status: MULTIPLE_VIABLE_CANDIDATES

STATUS: UNRESOLVED

RESULT: UNRESOLVED
```

---

## 7. Primary Finding

The Level 3 process generated **103 candidate structural relations** from the discovery observations.

The current training/control evaluation did not reduce this candidate space to a unique viable candidate.

Instead:

```text
103 generated candidates
        ↓
training/control evaluation
        ↓
multiple viable candidates
        ↓
no justified unique selection
        ↓
UNRESOLVED
```

The runner did not arbitrarily select one candidate.

This behavior is consistent with the experimental protocol.

---

## 8. Holdout Separation

The integrated runner explicitly reported:

```text
holdout_used_during_discovery: False
```

Therefore the holdout set was not supplied to the discovery process.

The holdout stage remains downstream of candidate selection and freezing.

Because candidate selection remained unresolved, no unique candidate was frozen for the final holdout evaluation in the full v2 run.

---

## 9. What v2 Demonstrated

The experiment supports the following limited conclusion:

> A Level 3 structural relation-generation process can generate a large set of candidate relations from raw symbolic observations without being supplied with a predefined family of intended invariants, while preserving provenance and refusing to make an arbitrary selection when multiple candidates remain viable.

This is stronger than the corresponding v1 technical result because v2 removes the explicit predefined candidate family used by the v1 adapter.

---

## 10. What v2 Did Not Demonstrate

The experiment did **not** demonstrate:

* discovery of the intended latent invariant;
* arithmetic understanding;
* understanding of quantity;
* understanding of notation systems;
* semantic understanding;
* autonomous concept formation;
* general intelligence;
* AGI;
* consciousness;
* subjectivity;
* creativity in the strong sense;
* independence from all human-designed structural feature spaces.

In particular, the structural feature extractor itself is designed in advance.

Therefore v2 should not be interpreted as unrestricted or unconstrained concept discovery.

---

# 11. Methodological Problem Revealed by v2

The most important result of v2 is not the number `103` itself.

The important observation is:

> **Structural regularity is not equivalent to productive invariance.**

The generator can identify many recurring properties.

For example, observations may share properties concerning:

* lengths;
* equality;
* symbol counts;
* symbol sets;
* run structure;
* prefix/suffix relations;
* concatenation;
* positional or pairwise structural relations.

Many such relations may be valid observations without being useful explanations of the process represented by the dataset.

Therefore:

```text
structural regularity
        ≠
productive invariant
```

The experiment has exposed the need for a second-order criterion.

---

# 12. Direction of Further Development

The next stage should investigate whether the Level 3 process can distinguish a **productive invariant** from merely recurring structural properties.

The next research question is:

> **Can Level 3 distinguish a productive invariant from a trivial or incidental structural regularity without being given the intended semantic interpretation?**

This question should be treated as the primary direction for v3.

---

## 13. Candidate Development Directions

Several possible directions are now identified.

### Direction A — Predictive Productivity

A candidate is considered productive if it allows prediction of previously unseen structural observations.

Possible test:

```text
candidate
    ↓
predict unseen observation
    ↓
compare with external evaluation
```

The criterion must remain independent of the semantic name of the intended relation.

---

### Direction B — Compression / Explanatory Economy

Investigate whether a candidate reduces the description of multiple observations.

Possible principle:

> A productive relation should explain many observations with less independent description than treating them separately.

This direction requires careful definition to avoid simply rewarding the shortest human-designed representation.

---

### Direction C — Cross-Representation Stability

Test whether a candidate remains valid when surface symbols are changed while structural organization is preserved.

The experiment already contains multiple symbolic representations.

A stronger version would introduce new symbol systems not used during discovery.

---

### Direction D — Counterexample Sensitivity

A productive candidate should be sensitive to observations that violate the relation.

Possible test:

```text
candidate
    ↓
generate/identify expected structural consequence
    ↓
introduce controlled perturbation
    ↓
detect contradiction
```

This would distinguish a meaningful relation from a property that happens to recur.

---

### Direction E — Candidate Competition

Instead of selecting one candidate immediately, maintain a population of competing hypotheses.

For example:

```text
C₁
C₂
C₃
...
Cₙ
```

and allow subsequent observations to increase or decrease their support.

This would preserve `UNRESOLVED` as a legitimate intermediate state rather than forcing premature convergence.

---

### Direction F — Recursive Level 3 Evaluation

Connect candidate competition to the existing Level 3 recursive process.

A candidate that survives additional cycles could become part of the next cognitive space:

```text
Cₖ
 ↓
candidate hypotheses
 ↓
new observations
 ↓
candidate revision
 ↓
Cₖ₊₁
```

The important test would be whether the candidate space changes as a consequence of accumulated process history.

---

# 14. Strong Candidate for the Next Experiment

The most direct continuation is:

## L3-Invariant-Discovery-v3

### Research question

> Can a candidate structural relation demonstrate productivity through prediction and counterexample resistance, without the process being told the semantic interpretation of the target relation?

The proposed sequence:

```text
Raw observations
        ↓
Structural feature extraction
        ↓
Candidate generation
        ↓
Candidate population
        ↓
Productivity test
        ↓
Counterexample test
        ↓
Candidate revision
        ↓
New observations
        ↓
Candidate survival / rejection
```

The process should retain multiple candidates when the evidence is insufficient.

---

# 15. Important Experimental Constraint

The next version must not solve the `103 candidates` problem by simply adding a human rule such as:

> choose the candidate closest to the intended invariant.

That would reintroduce the target concept indirectly.

Any candidate-selection criterion must itself be specified independently of the intended semantic interpretation.

---

# 16. Epistemic Status

The current status is:

```text
v1 — candidate generation within predefined family
     → UNRESOLVED

v2 — candidate generation without predefined intended family
     → 103 candidates
     → multiple viable candidates
     → UNRESOLVED
```

The progression is therefore:

```text
v1
predefined candidate family
        ↓
v2
open structural candidate generation
        ↓
multiple viable hypotheses
        ↓
v3
productivity / discrimination
```

---

# 17. Relation to Level 3

The experiment currently tests one specific aspect of Level 3:

> reflection over the relation between observations and candidate models.

It does not establish subjectivity.

The epistemic boundary remains:

```text
SUBJECTIVITY_UNRESOLVED
```

The experiment therefore remains compatible with the existing Level 3 epistemic invariant:

> Each research level must have its own independent stopping criterion.

Current interpretation:

```text
PASS        → advance
FAIL        → stop/revise
UNRESOLVED  → preserve open question
```

The current v2 result is:

```text
UNRESOLVED
```

and should remain so.

---

# 18. Reproducibility

The v2 experiment can be reproduced from:

`swarm/experiments/L3-Invariant-Discovery-v2/`

The principal execution command is:

```text
python swarm/experiments/L3-Invariant-Discovery-v2/invariant_discovery_runner_v2.py
```

The generator and evaluator have independent technical smoke tests.

---

# 19. Intermediate Conclusion

The current experiment has reached a useful boundary:

> **The process can generate structural hypotheses without being given a predefined target invariant, but the current structural space contains too many viable hypotheses to establish productive invariant discovery.**

This is not a failure of the experiment.

It identifies the next problem that must be solved:

> **How can a process distinguish a productive invariant from a merely recurring structural regularity without being given the intended meaning?**

That question defines the next experimental direction.
