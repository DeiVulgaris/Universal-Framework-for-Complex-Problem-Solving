UFCPS Simulation

1. Purpose

The simulation directory contains executable and reproducible simulations of UFCPS process continuity.

The simulation layer exists to test the protocol under controlled artificial conditions before introducing more complex runtime environments.

The simulation does not attempt to reproduce human cognition in full.

Its first purpose is narrower:

determine whether a distributed procedural process can preserve continuity across changing carriers, local failures, branching, composition, and autonomous experimental steps.

2. Simulation Boundary

The simulation models:

agents

carriers

procedural units

procedural states

transitions

deadlocks

state handoff

delegation

branching

composition

validation

recursion control

termination

The simulation may simplify:

language generation

external world interaction

scientific instrumentation

memory implementation

communication networks

planning algorithms

Such simplifications must be explicit.

3. Minimal Simulation Model

The minimal runtime state is:

World -> Swarm -> Carrier -> P_n -> Transition -> P_n+1

The simulation maintains a shared process environment containing the state required for continuation.

The carrier is an execution resource.

The procedural unit is the current cognitive step.

The process is the sequence of state transitions.

4. Simulation Entities

Agent

An executable computational entity.

Carrier

The agent currently responsible for executing a procedural unit.

Procedural Unit

A bounded step in the distributed process.

State

The continuation-relevant information associated with a procedural unit.

Transition

A recorded change from one procedural unit to another.

Swarm

A set of carriers participating in one distributed process.

Environment

The simulation state containing shared process information and runtime events.

5. Agent Model

An agent should have at least:

unique identifier

carrier type

capability profile

execution status

current procedural reference

local resource limits

Optional properties may include:

memory capacity

tool access

specialization

communication latency

failure probability

execution cost

The simulation must distinguish carrier properties from process state.

6. Carrier Lifecycle

A simulated carrier may move through:

available -> active -> stuck -> dissipating -> released

or:

available -> active -> completed -> released

A released carrier may no longer execute the previous procedural unit.

Its process state may nevertheless remain available to the swarm.

7. Procedural Unit Lifecycle

A procedural unit may move through:

ACTIVE -> STUCK -> DISSIPATING -> DELEGATED -> UNFOLDED

followed by:

P_n -> P_n+1

The exact runtime sequence may vary.

The semantic role of the transitions must remain compatible with SCP v1.

8. Shared Process State

The simulation environment should retain:

procedural state

transition history

deadlock records

delegation records

branch records

composition records

experiment records

validation results

active constraints

termination conditions

State persistence should be independent of the lifetime of one carrier.

9. Event Model

The simulation may represent runtime changes as events.

Typical events include:

STEP_STARTED

STEP_COMPLETED

DIFFERENCE_IDENTIFIED

STATE_FIXED

STATE_DISSIPATED

HANDOFF_REQUESTED

CARRIER_REPLACED

DEADLOCK_CREATED

BRANCH_CREATED

BRANCH_COMPLETED

COMPOSITION_STARTED

COMPOSITION_COMPLETED

CONTRADICTION_DETECTED

EXPERIMENT_STARTED

EXPERIMENT_COMPLETED

VALIDATION_FAILED

TERMINATION_REQUESTED

PROCESS_TERMINATED

Events should be append-only whenever practical.

10. Discrete-Time Simulation

The initial simulator should use discrete procedural steps.

At each simulation tick:

inspect active carriers

execute eligible operations

update procedural states

generate transitions

persist continuation state

apply failures or interruptions

schedule successor work

validate resulting states

evaluate termination conditions

The simulator should expose the complete transition trace.

11. Failure Injection

Controlled failure is a first-class simulation feature.

Failure events may be injected:

before execution

during execution

after local completion

during state handoff

during delegation

during composition

Example:

Carrier_A active
-> failure
-> state preserved
-> Carrier_B assigned
-> P_n+1

The simulation should record the exact failure point.

12. Deadlock Injection

A deterministic deadlock generator should be available.

It may impose:

impossible local constraint

unavailable capability

forbidden operation

contradictory local assumptions

missing required resource

The deadlock must generate a structured state rather than a generic exception.

The simulation then tests whether the process can continue.

13. Carrier Selection

The simulator may provide several selection policies.

Examples:

random compatible carrier

capability-matched carrier

least-loaded carrier

fixed carrier order

explicit test assignment

The carrier selection policy must be recorded because it can affect benchmark results.

No selection policy should be treated as universally optimal.

14. State Handoff Model

A handoff transfers continuation-relevant state.

The minimal handoff object contains:

source procedural unit

destination procedural unit

source carrier

destination carrier

preserved state reference

unresolved difference

next required operation

handoff reason

The simulator should allow measurement of state loss during handoff.

15. State Loss Simulation

To test robustness, the simulator may intentionally remove portions of state.

Examples:

remove local result

remove unresolved difference

remove constraints

remove provenance

remove next-operation metadata

The resulting continuation should be classified as:

successful

degraded

invalid

blocked

This makes state sufficiency experimentally measurable.

16. Branching Model

A branch is created when one procedural state produces multiple successor states.

Example:

P_n -> P_n+1a
P_n -> P_n+1b

Each branch receives:

inherited continuation state

branch identifier

branch-specific difference

branch-specific carrier

The branches must remain distinguishable until an explicit composition operation occurs.

17. Composition Model

Composition integrates multiple preserved states.

The simulator should support at least:

merge

complement

constraint

corroboration

contradiction

transformation

synthesis

Composition must retain provenance.

A composition operation may itself produce a new unresolved difference.

18. Contradiction Model

A contradiction is represented explicitly.

Example:

Result_A = X
Result_B = not X

The simulator should not automatically discard one branch.

Instead it should create a contradiction record containing:

source references

contradictory values

conditions

provenance

unresolved difference

The next procedural unit may use the contradiction as its input.

19. Autonomous Research Model

The simulation may include an autonomous research carrier.

It receives:

current state

available observations

unresolved difference

active constraints

It does not receive a predefined experiment.

It may generate:

Question -> Hypothesis -> Prediction -> Method

followed by execution and evaluation.

The simulator records the generated research state.

20. Result Model

Experimental results may be:

confirming

disconfirming

partially confirming

inconclusive

anomalous

invalid

unreproducible

All result classes remain valid simulation states.

No result class implies automatic termination.

21. Randomness

Whenever randomness is used, the simulator should support explicit seeds.

Every benchmark run should record:

random seed

randomization policy

number of random decisions

A deterministic replay mode is strongly recommended.

22. Cost Model

The initial simulator may model abstract cost units rather than physical compute time.

Possible cost dimensions include:

carrier execution cost

state storage cost

communication cost

validation cost

delegation cost

composition cost

experiment cost

The purpose is to make architectural overhead measurable.

23. Timing Model

The simulator may assign abstract durations to:

execution

handoff

communication

validation

composition

experiment execution

Timing parameters should be configurable.

The initial experiments should avoid conclusions based solely on arbitrary simulated timings.

24. Continuity Measurements

The simulator should expose at least:

Process Survival

Whether a valid successor procedural unit exists after local failure.

Handoff Integrity

Whether continuation-relevant state survives carrier replacement.

State Loss

Which required state elements were unavailable to the successor.

Recovery Steps

Number of transitions required to restore normal execution.

Repeated Work

Amount of work repeated because preserved state was insufficient.

Branch Integrity

Whether branch state remains separated.

Provenance Integrity

Whether source history remains recoverable.

25. Termination Model

Termination occurs only when an explicit process-level condition is satisfied.

Possible conditions include:

task completed

validated convergence

exhausted search

resource policy

recursion limit

external shutdown

Carrier failure alone is not a valid global termination event.

26. C5 Recursion Control

The simulation must enforce configurable recursion limits.

The runtime should track:

current depth

maximum depth

number of branches

number of generated successor states

overflow action

Possible overflow actions:

delegate

branch

pause

terminate

Every overflow event should be recorded.

27. Simulation Scenarios

The initial scenarios should include:

single-carrier baseline

basic handoff

forced deadlock

repeated carrier replacement

communication interruption

parallel resolution

contradictory branches

composition

autonomous experiment

negative experimental result

recursion stress

long-running process

Each scenario should have a machine-readable configuration.

28. Replay

A simulation run should be replayable from retained artifacts where deterministic execution is possible.

Replay should restore:

initial state

configuration

random seed

carrier pool

failure schedule

event sequence

Replay is particularly important when investigating rare continuity failures.

29. Logging

Simulation logs should record:

timestamp or tick

event type

procedural unit

carrier

state reference

transition reference

operation

result

validation status

Errors should be explicit.

The simulator should not convert an invalid transition into a valid one merely to preserve execution.

30. Invariant Monitoring

The simulator should monitor UFCPS invariants continuously.

At minimum:

Local Failure != Process Termination

Agent_n != Agent_n+1

does not invalidate:

P_n -> P_n+1

and:

Deadlock != Termination

When an invariant is violated, the simulator should record:

invariant identifier

violating state

event that caused the violation

relevant carrier

preceding transition

diagnostic details

31. Simulation and Validators

The simulator should invoke or remain compatible with:

validator/validate_state.py

validator/validate_transition.py

Validation should occur:

before accepting a new state

before accepting a transition

after handoff

after composition

after autonomous experiment completion

Runtime validation may impose additional conditions not represented in schemas.

32. Simulation Architecture

The initial implementation may be divided into:

simulation/core

for entities and state transitions.

simulation/policies

for carrier selection and scheduling policies.

simulation/scenarios

for benchmark configurations.

simulation/logging

for event and trace handling.

simulation/replay

for deterministic reruns.

simulation/results

for generated benchmark artifacts.

The directory structure may evolve as implementation requirements become clearer.

33. Minimal Executable Prototype

The first executable prototype should implement only:

a procedural state

a carrier

a transition

a forced carrier failure

state preservation

carrier replacement

successor execution

validation

trace output

Parallelism and autonomous research should be added after the minimal continuity mechanism is observable.

34. First Simulation Experiment

The minimal experiment is:

Agent_A -> P_0

then:

Agent_A -> failure

then:

P_0 state -> preserved

then:

Agent_B -> P_1

The principal observation is whether the successor can continue using preserved state.

The experiment should compare this with a control in which the continuation state is discarded.

35. Expected Outputs

A simulation run should produce:

final process state

event log

transition trace

validation report

continuity metrics

failure classification

configuration snapshot

random seed, when used

These artifacts should be machine-readable where practical.

36. Interpretation Boundary

A successful simulation demonstrates that the simulated mechanism operated under the tested conditions.

It does not demonstrate:

human-level intelligence

general intelligence

consciousness

correctness of Metamonism

real-world scalability

universal process continuity

Those require separate evidence.

37. Relation to Experimental Benchmark

experiments/benchmark_v1.md defines what should be tested.

This directory defines how those tests can be simulated.

The separation allows benchmark criteria to remain stable while simulator implementations change.

38. Status

Version: v1

Status: simulation architecture specification

The next implementation stage may introduce concrete simulator modules after the protocol, schema, validation, example, and benchmark layers are stable enough for executable testing.
