# L3 Invariant Discovery v3

## Status

**Experimental protocol — frozen before implementation**

Experiment ID:

`UFCPS-L3-INVARIANT-DISCOVERY-v3`

Version:

`3.0`

Parent experiment:

`UFCPS-L3-INVARIANT-DISCOVERY-v2`

Epistemic status:

`OPEN EXPERIMENT`

---

# 1. Research Question

Can a Level 3 process distinguish a **productive structural invariant** from a merely recurring structural regularity by testing its predictive consequences on previously unseen configurations and controlled counterexamples, without being given the semantic interpretation of the target relation?

The experiment does **not** ask whether the system understands arithmetic, numbers, notation, or any other predefined semantic domain.

The target is narrower:

> Can a candidate relation generated from observations survive prediction and counterexample testing because it actually constrains future observations?

---

# 2. Relation to v2

Version 3 is a new experiment.

Version 2 remains immutable.

The progression is:

```text
v1
predefined candidate family
        ↓
v2
open structural candidate generation
        ↓
v3
productivity and discrimination testing
```

v2 produced:

```text
103 generated candidates
MULTIPLE_VIABLE_CANDIDATES
UNRESOLVED
```

The v2 result is not converted into PASS.

v3 addresses the unresolved problem:

```text
recurring regularity
        ≠
productive invariant
```

---

# 3. Central Methodological Problem

A structural dataset can contain many relations that are simultaneously true.

For example, a candidate may correctly describe:

* output length,
* symbol multiplicity,
* concatenation,
* equality,
* positional structure,
* symbol-set relations,
* repeated patterns.

Such a candidate can have strong retrospective support while having little or no predictive value.

Therefore:

> Training support is insufficient evidence for invariant discovery.

A candidate must additionally constrain observations that were not available during its generation.

---

# 4. Operational Definition of Productivity

For this experiment, a candidate relation is considered **productive** if:

1. it is generated from the discovery partition;
2. it can be expressed independently of the hidden semantic oracle;
3. it makes predictions for observations not used during candidate generation;
4. those predictions are tested against observations containing novel structural configurations;
5. it survives controlled counterexamples designed to distinguish competing relations;
6. its predictive behavior is reproducible;
7. no semantic interpretation is supplied to the discovery process.

Productivity is therefore an operational experimental property.

It is **not** treated as proof of semantic understanding.

---

# 5. Experimental Separation

The experiment is divided into five information stages.

```text
RAW OBSERVATIONS
       ↓
STRUCTURAL REPRESENTATION
       ↓
CANDIDATE GENERATION
       ↓
PRODUCTIVITY TEST
       ↓
EXTERNAL EVALUATION
```

The discovery process must not receive information from later stages.

In particular:

```text
discovery
    ≠
holdout oracle
```

and

```text
candidate generation
    ≠
candidate evaluation
```

---

# 6. Data Partitions

The experiment uses four logically distinct partitions.

## 6.1 Discovery Set

Used for:

* structural feature extraction;
* relation generation;
* candidate formation.

No holdout information may enter this stage.

---

## 6.2 Selection Set

Used for:

* predictive testing;
* comparison between candidate relations;
* elimination of candidates that fail to generalize.

The selection set must contain structural configurations that are not duplicates of the discovery observations.

---

## 6.3 Counterexample Set

Used to distinguish candidates that agree on ordinary observations but make different predictions under controlled perturbation.

A counterexample must be generated or selected so that:

```text
Candidate A → prediction A

Candidate B → prediction B

A ≠ B
```

The actual observation then determines which candidate survives that test.

The counterexample generator must not receive semantic labels describing the intended invariant.

---

## 6.4 Holdout Set

The final holdout is inaccessible to candidate generation and candidate selection.

It is used only after the candidate has been frozen.

The holdout result is external evaluation.

---

# 7. Novel Structural Configuration

A selection or counterexample observation qualifies as structurally novel when at least one relevant structural configuration was not present in the discovery set.

Novelty may concern:

* operand length;
* result length;
* symbol multiplicity;
* symbol identity;
* number of distinct symbols;
* positional arrangement;
* repetition structure;
* relationship between operand structures;
* representation transformation.

Simple duplication of an existing observation does not constitute a novel prediction.

---

# 8. Candidate Representation

A candidate must be represented as data rather than as a hard-coded semantic rule.

Minimum representation:

```text
candidate_id
relation_type
relation_expression
source_observations
support_observations
challenge_observations
prediction_rule
provenance
status
```

The `prediction_rule` must be executable without referring to the hidden intended interpretation.

The evaluator must not contain a list such as:

```text
"candidate X means addition"
"candidate Y means concatenation"
"candidate Z means cardinality"
```

Candidate semantics must come from the generated relation representation itself.

---

# 9. No Semantic Hardcoding

The following information is prohibited from the discovery and selection engines:

* arithmetic terminology;
* number terminology;
* numeral-system names;
* names of mathematical operations;
* historical origin of representations;
* intended interpretation of symbols;
* hidden oracle labels;
* manually supplied target invariant;
* predefined list of intended candidate relations.

The engine may operate on neutral structural properties.

Examples of allowed information:

```text
length
equality
multiplicity
prefix
suffix
position
repetition
symbol set
structural correspondence
transformation
```

These properties describe observations without naming their intended meaning.

---

# 10. Separation of Generator and Evaluator

The generator produces candidate relations.

The evaluator receives only candidate data and observations.

The evaluator must not contain a semantic catalogue of possible candidates.

Conceptually:

```text
Generator:

observations
    ↓
structural relations
    ↓
candidate

Evaluator:

candidate + observations
    ↓
prediction
    ↓
observed result
    ↓
support / challenge
```

The evaluator must operate on the candidate's executable representation.

---

# 11. Prediction Requirement

A candidate must make an explicit prediction before the corresponding observation is revealed to the candidate-selection process.

For each prediction:

```text
prediction_id
candidate_id
input_observation
predicted_output_structure
actual_output_structure
prediction_status
```

Allowed statuses:

```text
SUPPORTED
CONTRADICTED
UNRESOLVED
```

A candidate that merely describes an already observed result without producing a testable prediction does not satisfy the productivity criterion.

---

# 12. Counterexample Requirement

Candidate relations must be exposed to observations specifically selected to distinguish competing hypotheses.

The purpose is not to maximize the number of contradictions.

The purpose is:

> to determine whether the candidate constrains future observations more strongly than competing candidates.

A counterexample is therefore informative only when competing candidates produce different predictions.

---

# 13. Candidate Competition

If multiple candidates remain viable after ordinary prediction testing, the experiment must not arbitrarily select one.

Instead:

```text
multiple viable candidates
        ↓
COUNTEREXAMPLE TEST
        ↓
candidate discrimination
```

If multiple candidates remain equally viable:

```text
STATUS = UNRESOLVED
```

No ranking or arbitrary winner selection is permitted.

---

# 14. Candidate Freeze

A candidate can be frozen only after:

1. discovery is complete;
2. candidate generation is complete;
3. selection-set predictions are complete;
4. counterexample testing is complete;
5. candidate comparison is complete;
6. no prohibited semantic information has entered the process.

After freeze:

```text
candidate_definition = immutable
```

No modification is permitted after holdout access.

Any modification requires a new experiment version.

---

# 15. Holdout Evaluation

Only the frozen candidate is evaluated against the holdout.

The holdout oracle is external to the discovery process.

The oracle may determine whether the prediction corresponds to the latent relation used to construct the dataset.

However:

```text
oracle ≠ discovery engine
```

and:

```text
oracle feedback → prohibited before freeze
```

---

# 16. PASS Criterion

The experiment may receive:

```text
PASS
```

only if all of the following are satisfied:

1. no predefined candidate family was supplied;
2. no semantic interpretation was supplied;
3. candidate generation is data-derived;
4. at least one candidate makes explicit predictions;
5. predictions are tested on structurally novel observations;
6. at least one candidate demonstrates predictive productivity;
7. controlled counterexamples discriminate between competing candidates;
8. the surviving candidate is uniquely determined or uniquely supported by the protocol;
9. the candidate is frozen before holdout evaluation;
10. holdout evaluation confirms the candidate's predictions;
11. the complete provenance trace is reproducible;
12. no semantic leakage is detected.

PASS means:

> A productive structural relation was experimentally demonstrated under this protocol.

It does **not** mean:

> The system understood the intended semantic domain.

---

# 17. FAIL Criterion

The experiment receives:

```text
FAIL
```

if the protocol itself is violated in a way that invalidates the experiment.

Examples:

* semantic information supplied to discovery;
* predefined target invariant supplied;
* predefined candidate family supplied;
* holdout used before candidate freeze;
* candidate modified after holdout access;
* prediction stage bypassed;
* counterexample stage bypassed where candidate competition exists;
* candidate evaluation depends on hard-coded intended semantics;
* provenance cannot be reconstructed;
* implementation error invalidates the result.

FAIL is a methodological result.

It does not imply that the underlying hypothesis is false.

---

# 18. UNRESOLVED Criterion

The experiment receives:

```text
UNRESOLVED
```

when the protocol is followed but the evidence does not uniquely establish productivity.

Examples:

* multiple candidates remain viable;
* candidate predictions are insufficiently discriminative;
* selection data are insufficient;
* counterexamples fail to distinguish hypotheses;
* holdout is insufficient;
* productivity is observed but uniqueness is not established;
* structural regularities remain observationally equivalent;
* candidate representation is technically valid but scientifically insufficient.

This is an expected possible result.

```text
UNRESOLVED ≠ FAIL
UNRESOLVED ≠ PASS
```

---

# 19. Required Negative Controls

The experiment must contain observations designed to test whether candidate relations merely exploit superficial regularities.

Negative controls should alter relevant surface structure while violating the candidate relation.

A candidate that cannot distinguish positive observations from structurally similar negative controls does not demonstrate useful discrimination.

---

# 20. Required Generalization Tests

The experiment must test at least three kinds of generalization.

### G1 — Scale Generalization

Known structural relation applied to previously unseen sizes.

```text
known configuration
        ↓
new scale
```

### G2 — Representation Generalization

The same underlying relation represented through a different symbolic structure.

```text
representation A
        ↓
representation B
```

### G3 — Structural Perturbation

A controlled modification that preserves some surface properties while changing the relation being tested.

```text
surface similarity preserved
relation changed
```

The purpose is to prevent a candidate from succeeding merely by exploiting superficial regularity.

---

# 21. Compression Is Not Sufficient

A short or elegant candidate is not automatically considered productive.

Likewise:

```text
high support
≠
high explanatory value
```

and:

```text
simple relation
≠
true invariant
```

Compression may be recorded as an auxiliary measure but cannot by itself determine PASS.

---

# 22. Recursive Level 3 Trace

The experiment must preserve the Level 3 process trace.

Conceptually:

```text
C_k
  ↓
observation space
  ↓
candidate generation
  ↓
candidate competition
  ↓
counterexample
  ↓
reflection
  ↓
candidate revision / persistence
  ↓
C_k+1
```

The trace must record:

* source cognitive space;
* candidate generation;
* candidate provenance;
* prediction events;
* contradiction events;
* unresolved questions;
* candidate revision;
* successor space;
* process continuation.

---

# 23. Process Continuity Invariant

The experiment preserves the Level 1/2/3 invariant:

```text
Local Failure ≠ Process Termination
```

A candidate contradiction is information.

It must not terminate the global process.

Instead:

```text
candidate contradiction
        ↓
new distinction
        ↓
reflection
        ↓
candidate revision / alternative
        ↓
continuation
```

---

# 24. Unresolved Question Ledger

The experiment must preserve unresolved questions generated during candidate competition.

Examples:

```text
Why do candidates A and B remain observationally equivalent?
Which structural configuration would distinguish them?
Which prediction would falsify candidate A?
Which prediction would falsify candidate B?
Is the current feature space sufficient?
```

Questions must persist into the successor process state.

---

# 25. Independence Criterion

The central independence criterion is:

> The process must not be given the form of the intended invariant and must derive candidate relations from observations available to it.

The following does not establish independence:

```text
candidate family hidden inside evaluator
candidate names hidden inside code
manual selection of intended candidate
post-hoc candidate construction
semantic labels disguised as structural labels
```

Therefore the implementation must be audited for semantic hardcoding before the experiment can receive PASS.

---

# 26. Reproducibility Requirements

The experiment must record:

```text
experiment_id
protocol_version
dataset_version
generator_version
evaluator_version
runner_version
discovery_partition
selection_partition
counterexample_partition
holdout_partition
candidate_generation_trace
prediction_trace
counterexample_trace
freeze_event
holdout_evaluation
unresolved_questions
final_status
```

The exact dataset and protocol versions must be frozen before the first scientific run.

---

# 27. Versioning Rule

After the first scientific run:

```text
protocol changes → v4
dataset changes → v4
candidate representation changes → v4
evaluation criterion changes → v4
partition changes → v4
feature-space changes → v4
```

Technical bug fixes that do not alter the experimental design may be recorded as implementation revisions.

A change that could alter scientific interpretation requires a new experiment version.

---

# 28. Expected Outcomes

The experiment has three legitimate outcomes.

### Outcome A

```text
PASS
```

A productive invariant is demonstrated under the operational criteria.

### Outcome B

```text
UNRESOLVED
```

Productivity is not uniquely established.

### Outcome C

```text
FAIL
```

The experimental protocol is violated or technically invalidated.

The experiment must not force a PASS outcome.

---

# 29. Scientific Scope

Even a PASS result would support only the following narrow claim:

> Under the specified experimental conditions, the Level 3 process generated a structural relation that produced predictive consequences on previously unseen configurations and survived controlled counterexample testing without being supplied the semantic interpretation of the target relation.

It would **not** establish:

* consciousness;
* subjectivity;
* phenomenal experience;
* human-like understanding;
* general intelligence;
* AGI;
* autonomous goals;
* unrestricted invariant discovery;
* semantic understanding in the human sense.

Those questions require independent experiments.

---

# 30. Primary Successive Question

If v3 produces PASS, the next experiment should ask:

> Can productive invariant generation persist when the available structural feature space itself is not sufficient to directly encode the eventual relation?

This question moves from:

```text
productive relation discovery
```

toward:

```text
productive transformation of the representational space itself
```

which is a stronger Level 3 test.

---

# 31. Canonical Experimental Principle

The central methodological principle of v3 is:

> **A relation is not treated as an invariant merely because it describes what has already happened. It must constrain what can happen next.**

Formally:

```text
description of past
        ≠
prediction of future
```

and:

```text
prediction
+
counterexample resistance
+
generalization
        →
productive invariant candidate
```

---

# 32. Status

Protocol status:

`FROZEN FOR IMPLEMENTATION`

Scientific status:

`NOT RUN`

No PASS, FAIL, or UNRESOLVED result is assigned before execution.
