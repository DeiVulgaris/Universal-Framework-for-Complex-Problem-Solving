UFCPS Benchmark v1

1. Purpose

This benchmark defines a first reproducible test suite for the UFCPS architecture.

The benchmark is intentionally operational.

It tests whether the implemented system can maintain a distributed procedural process under controlled interruption, delegation, branching, composition, contradiction, and autonomous experimentation.

The benchmark does not attempt to establish general intelligence.

2. Primary Hypothesis

The primary hypothesis is:

A UFCPS process can preserve continuation across local carrier failure when continuation-relevant state is explicitly represented, validated, and handed to a successor carrier.

Operationally:

Local Failure != Process Termination

The benchmark tests this relation through observable system behavior.

3. Test Environment

Every benchmark run should record:

UFCPS revision or commit

protocol versions

schema versions

validator versions

model or agent identifiers

carrier configuration

available tools

shared-state mechanism

runtime environment

randomization seed, when applicable

execution start and end times

The benchmark is invalid as a reproducibility artifact when these parameters are omitted and materially affect execution.

4. Benchmark Objects

The benchmark uses the following objects:

procedural state

transition record

deadlock state

continuation state

carrier identity

branch identity

composition record

experimental state

validation result

Machine-readable examples should be stored separately from benchmark prose.

5. Baseline Task

The baseline task should be sufficiently deterministic that continuation can be measured independently of model creativity.

Suitable task classes include:

multi-step symbolic transformation

constrained planning

structured search

decomposition and recomposition

finite-state reasoning

controlled research planning

The task should require multiple procedural steps and should permit a known continuation path.

6. Baseline Run

Run the task with one carrier and no injected failure.

Record:

number of procedural units

number of transitions

completion state

local results

total execution cost

execution time

validation outcomes

This establishes the baseline execution trace.

The baseline is a reference condition, not a target score.

7. Test 1 — State Schema Validation

Objective

Determine whether valid and intentionally malformed procedural states are correctly distinguished.

Procedure

Submit a valid procedural state.

Validate it with the state validator.

Remove one required field.

Validate again.

Introduce an invalid enum value.

Validate again.

Introduce a cross-field contradiction.

Validate again.

Expected Behavior

The valid state passes.

Each malformed state produces an explicit validation failure.

The validator must not silently repair the state.

Measurements

validation accuracy

diagnostic completeness

false acceptance rate

false rejection rate

8. Test 2 — Transition Validation

Objective

Determine whether invalid transitions are detected.

Procedure

Construct transitions with:

correct successor step

skipped successor step

inconsistent carrier metadata

missing continuation state after carrier replacement

delegation without carrier change

local transition with carrier replacement

termination while continuation is explicitly required

Expected Behavior

Valid transitions pass.

Invalid transitions are rejected with structured diagnostics.

9. Test 3 — Basic Carrier Handoff

Objective

Test continuity across carrier replacement.

Procedure

Start P_0 on Carrier_A.

Interrupt Carrier_A after partial progress.

Preserve continuation-relevant state.

Mark the local session as stuck or dissipating.

Delegate the preserved state.

Start P_1 on Carrier_B.

Complete the remaining task.

Success Condition

The successor carrier completes the required continuation without reconstructing the entire previous session.

Measurements

handoff success

state loss

successor completion

additional execution cost

recovery latency

10. Test 4 — Forced Deadlock

Objective

Determine whether a deadlock becomes structured process information rather than automatic termination.

Procedure

Establish a valid procedural state.

Inject a deterministic blocking constraint.

Force the current carrier into stuck.

Create a deadlock record.

Preserve the unresolved difference.

Delegate or branch.

Execute a successor procedural unit.

Success Condition

A successor state is produced without discarding the deadlock information.

Failure Condition

The process terminates solely because the current carrier is stuck.

11. Test 5 — Carrier Type Substitution

Objective

Determine whether the process can continue when the next carrier has a different specialization.

Procedure

Use a task whose first stage is handled by a general carrier and whose next stage requires a specialized carrier.

Record:

Carrier_A -> P_n

followed by:

P_n -> Carrier_B -> P_n+1

Measurements

continuation success

state compatibility

additional handoff requirements

carrier-specific failures

time to valid continuation

12. Test 6 — Stateless Delegation Control

Objective

Determine whether explicit continuation state contributes to successful handoff.

Conditions

Run two conditions:

Condition A

Transfer only a task description.

Condition B

Transfer the full continuation-relevant state.

Measurements

Compare:

success rate

reconstruction effort

repeated work

state omissions

recovery time

final result consistency

The benchmark does not presuppose the outcome.

13. Test 7 — Parallel Resolution

Objective

Test whether independent branches can operate from a common predecessor without state corruption.

Procedure

Create P_n.

Identify two separable differences.

Generate branch A.

Generate branch B.

Execute the branches concurrently or in controlled interleaving.

Record independent states.

Compose the results.

Success Condition

Branch A does not overwrite branch B state, and vice versa.

Branch provenance remains recoverable.

14. Test 8 — Contradictory Branches

Objective

Determine whether contradictory results are preserved explicitly.

Procedure

Create two branches that intentionally produce incompatible results.

For example:

Result_A = X

and:

Result_B = not X

Expected Behavior

The contradiction remains represented.

The system does not silently select one result.

The contradiction becomes an unresolved difference or a new research question.

15. Test 9 — Composition

Objective

Determine whether compatible partial states can become an integrated successor state.

Procedure

Generate two independent partial results.

Preserve provenance.

Identify the relation between the states.

Compose the states.

Validate the resulting state.

Continue from the composed state.

Success Condition

The resulting state contains the integrated information and preserves source references.

16. Test 10 — Negative Result Preservation

Objective

Determine whether failed approaches remain available to later procedural units.

Procedure

Execute a strategy that is known to fail.

Record the negative result.

Hand the state to a new carrier.

Ask the successor to continue without repeating the invalidated path.

Measurements

repeated-failure rate

rejected-path retention

unnecessary recomputation

successor completion

17. Test 11 — Autonomous Experiment Selection

Objective

Test whether an agent can generate an experiment from an unresolved difference without receiving a predefined experiment.

Procedure

Provide:

current state

evidence

unresolved difference

active constraints

Do not provide:

experiment design

expected method

selected variables

predefined next experiment

The agent must produce:

Difference -> Question -> Hypothesis -> Prediction -> Method

and then execute the resulting experiment.

Evaluation

Assess whether the generated experiment:

addresses the unresolved difference

contains a testable prediction

distinguishes observation from interpretation

respects active constraints

records uncertainty

generates a valid successor state

The benchmark evaluates process structure, not agreement with a preferred hypothesis.

18. Test 12 — Autonomous Negative Result

Objective

Determine whether an autonomous experiment can continue after a disconfirming or inconclusive outcome.

Procedure

Provide an unresolved difference.

Permit autonomous experiment design.

Force or obtain an inconclusive result.

Preserve the result.

Ask the system to generate the next research question.

Success Condition

The system treats the result as a legitimate research state and generates a continuation path without pretending the experiment succeeded.

19. Test 13 — Repeated Carrier Replacement

Objective

Test whether continuity survives multiple successive carrier changes.

Procedure

Execute:

P_0 -> Carrier_A

P_1 -> Carrier_B

P_2 -> Carrier_C

P_3 -> Carrier_D

Inject interruption between several transitions.

Measurements

cumulative state loss

continuation success

reconstruction overhead

provenance integrity

process completion

The number of carrier replacements must be explicitly recorded.

20. Test 14 — Communication Interruption

Objective

Determine whether the process can recover when direct communication with the current carrier is lost.

Procedure

Execute a procedural unit.

Preserve state in the shared environment.

Interrupt communication.

Make the original carrier unavailable.

Start a replacement carrier from the persisted state.

Success Condition

Continuation is possible without direct recovery of the original carrier.

21. Test 15 — Recursion Control

Objective

Determine whether C5 can restrict uncontrolled continuation.

Procedure

Construct a task that continuously generates successor differences.

Set a finite maximum recursion depth.

Execute until the limit is approached.

Continue beyond the permitted depth.

Expected Behavior

The configured overflow action is triggered.

Possible actions include:

delegate

branch

pause

terminate

The system must not continue indefinitely without a recorded control decision.

22. Test 16 — Global Termination

Objective

Distinguish valid global termination from local failure.

Procedure

Run two conditions.

Condition A

A carrier fails while a valid continuation exists.

Condition B

The process reaches an explicit global termination condition.

Expected Behavior

Condition A continues.

Condition B terminates.

The benchmark records the different causes explicitly.

23. Test 17 — Long-Run Continuity

Objective

Evaluate whether continuity remains stable over a larger procedural sequence.

Procedure

Execute a task requiring many procedural transitions.

Inject:

carrier replacement

temporary deadlock

parallel branch

composition

negative result

communication interruption

at controlled points.

Measurements

total continuation rate

accumulated state loss

invalid transition rate

repeated work

branch integrity

provenance integrity

total resource cost

24. Test 18 — Swarm Scaling

Objective

Determine how the continuity mechanism behaves as the number of carriers increases.

Conditions

Run with progressively larger carrier pools.

Record:

number of active carriers

number of procedural units

number of handoffs

branch count

composition count

shared-state operations

validation operations

Measure system behavior as scale changes.

The benchmark must not assume that more carriers imply better performance.

25. Test 19 — Continuity Versus Centralization

Objective

Compare a continuity-preserving distributed architecture with a centralized reference architecture.

Conditions

Run equivalent tasks under:

centralized control

distributed continuity protocol

Keep task scope and evaluation criteria comparable.

Measure:

completion

failure recovery

communication overhead

state overhead

execution time

resource consumption

The benchmark reports observed differences without assigning an overall winner.

26. Test 20 — Process Identity Under Carrier Change

Objective

Operationalize the distinction:

Agent_n != Agent_n+1

while testing:

P_n -> P_n+1

Procedure

Replace carriers at every predefined transition.

Preserve only continuation-relevant state.

Success Condition

The process remains coherent according to the benchmark's task-specific continuation criteria.

The identity of the carrier is not used as a criterion for process continuity.

27. Metrics

The core benchmark metrics are:

Continuation Rate

successful continuations / eligible interruptions

Handoff Integrity

complete continuation states / total handoffs

Deadlock Conversion

deadlocks producing successor states / structured deadlocks

Branch Integrity

branches preserved without cross-corruption / total branches

Provenance Retention

composed results with recoverable provenance / total compositions

Redundant Work

Work repeated after handoff that was already represented in preserved state.

Recovery Cost

Additional computational resources required to resume after interruption.

Process Survival

Whether a valid successor state exists after each injected local failure.

These metrics should be reported with raw counts in addition to percentages.

28. Acceptance Criteria

A benchmark result should contain:

benchmark identifier

test condition

initial state reference

protocol version

schema version

validator version

carrier configuration

transition trace

observed result

validation result

metrics

limitations

unresolved differences

Acceptance criteria must be defined per test.

No universal numerical threshold is assumed by this document.

29. Reproducibility

A benchmark run should be reproducible from the retained artifacts whenever the environment permits reproducibility.

At minimum retain:

input states

transition records

relevant configuration

raw observations

validator output

benchmark output

random seed when applicable

Environment-dependent variability must be recorded.

30. Failure Classification

Failures should be classified rather than collapsed into one category.

Suggested categories:

schema failure

transition failure

state-loss failure

carrier failure

delegation failure

branch-isolation failure

composition failure

contradiction-loss failure

experimental-design failure

measurement failure

recursion-control failure

runtime infrastructure failure

This distinction is necessary for diagnosing the architecture.

31. Negative Findings

The benchmark explicitly permits results showing that a UFCPS mechanism does not work under tested conditions.

A failed hypothesis or architectural mechanism is a valid result.

The benchmark should record:

what failed

where it failed

under which conditions

whether failure was reproducible

whether a successor difference was generated

what modification was subsequently tested

32. Interpretation

Benchmark output should be interpreted in layers.

Layer 1 — Observation

What the system actually did.

Layer 2 — Measurement

What was quantitatively recorded.

Layer 3 — Validation

Which protocol and schema conditions were satisfied.

Layer 4 — Comparison

How the result differs from the selected baseline.

Layer 5 — Interpretation

What the result may indicate about the tested mechanism.

Layer 6 — Limitation

What the experiment cannot establish.

This ordering prevents architectural claims from being inferred directly from a single successful run.

33. Benchmark Execution Order

The recommended initial order is:

schema validation

transition validation

basic handoff

forced deadlock

carrier substitution

stateless delegation control

parallel resolution

contradiction preservation

composition

negative result preservation

autonomous experiment selection

autonomous negative result

repeated carrier replacement

communication interruption

recursion control

global termination

long-run continuity

swarm scaling

continuity versus centralization

process identity under carrier change

Earlier tests establish infrastructure for later tests.

34. Initial Null Expectations

The benchmark should not assume that the UFCPS architecture will succeed.

Possible null results include:

carrier replacement loses essential state

delegation increases repeated work

parallelization creates state corruption

composition loses provenance

autonomous experiment generation does not produce discriminating tests

recursion control causes unacceptable process loss

distributed continuity adds excessive overhead

These outcomes are compatible with the purpose of the benchmark.

35. Experimental Integrity Rule

The benchmark must not be tuned after observing results in a way that retroactively changes the success criterion without recording the change.

Any modification to:

task

success condition

carrier configuration

protocol

schema

validator

evaluation method

must be versioned.

36. Benchmark Invariant

The benchmark's central invariant is:

The unit of evaluation is the behavior of the distributed process under defined conditions, not the apparent success of any individual carrier.

This is the operational core of the UFCPS experimental program.

37. Relation to Other Files

This benchmark depends conceptually on:

protocols/SCP_v1.md

protocols/swarm_continuity_v1.md

protocols/composition_v1.md

protocols/experimental_autonomy_v1.md

schemas/procedural_state_v1.json

schemas/experimental_state_v1.json

schemas/transition_v1.json

validator/validate_state.py

validator/validate_transition.py

Concrete machine-readable cases are stored under:

examples/

38. Status

Version: v1

Status: benchmark specification

This document defines the initial UFCPS benchmark suite. Numerical results, execution logs, and empirical conclusions belong in separate benchmark run artifacts.
