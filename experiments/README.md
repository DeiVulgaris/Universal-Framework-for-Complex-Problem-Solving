UFCPS Experiments

1. Purpose

This directory contains experimental specifications, benchmarks, test scenarios, and evaluation procedures for UFCPS.

The purpose of the experimental layer is to determine whether the architecture can preserve and continue distributed cognitive processes under controlled conditions.

The experiments are not intended to prove the Metamonism framework.

They are intended to test whether the procedural architecture implements its stated invariants and whether those invariants produce observable system behavior.

2. Experimental Scope

The experimental program examines:

procedural continuity

carrier replacement

state handoff

deadlock handling

delegation

parallel continuation

composition

autonomous experiment generation

preservation of negative results

contradiction handling

recursion control

process termination

distributed research continuity

Each experiment should define what is being tested independently of whether the underlying theoretical interpretation is accepted.

3. Primary Experimental Question

The primary systems question is:

Can a distributed process continue coherently when the current carrier cannot continue the local step?

The operational form is:

Local Failure != Process Termination

A successful implementation should preserve the continuation-relevant state and make a valid successor procedural unit possible without requiring identity persistence of the failed carrier.

4. Secondary Questions

The experimental program may investigate:

4.1 State Handoff

Can a new carrier continue from preserved state without reconstructing the complete previous session?

4.2 Deadlock Handling

Can a deadlock be represented as structured information and converted into a continuation state?

4.3 Carrier Independence

Can process continuity survive systematic replacement of carriers?

4.4 Parallel Resolution

Can independent branches operate without corrupting one another's state?

4.5 Composition

Can compatible branch results be integrated while preserving provenance and unresolved differences?

4.6 Contradiction

Can contradictory outputs remain explicit and become inputs to subsequent reasoning?

4.7 Autonomous Research

Can an agent generate a research question from an unresolved difference and select an experiment without receiving a predefined experiment from the protocol?

4.8 Recursion Control

Can the system prevent uncontrolled expansion while preserving valid continuation paths?

5. Experimental Philosophy

The protocol separates:

architectural rules

observations

interpretations

hypotheses

conclusions

An observed system behavior must not automatically be treated as validation of a theoretical claim.

A benchmark may demonstrate that a mechanism functions under defined conditions.

It does not thereby prove that the mechanism is universally necessary or sufficient.

6. Experimental Unit

The basic experimental unit is a procedural transition.

A transition may be:

local

continuation

delegation

branch

The transition should be represented explicitly.

The corresponding state should identify:

procedural step

carrier

current state

structural difference

operation

preserved state

continuation condition

7. Testable Invariants

Experiments should test explicit invariants.

Invariant A

Local Failure != Process Termination

Invariant B

Agent_n != Agent_n+1

does not prevent:

P_n -> P_n+1

Invariant C

A deadlock can be preserved as process information.

Invariant D

Delegation preserves continuation-relevant state.

Invariant E

Parallel branches preserve branch identity.

Invariant F

Composition preserves provenance.

Invariant G

Negative results remain available for continuation.

Invariant H

Termination is a distinct process-level condition.

8. Control Conditions

Experiments should include appropriate controls where the tested property permits them.

Possible controls include:

a single-carrier baseline

no-handoff baseline

stateless delegation baseline

sequential baseline against parallel execution

fixed experiment against autonomous experiment selection

unrestricted recursion against C5-controlled recursion

The choice of control depends on the experiment.

9. Failure Injection

Controlled failure injection is central to the experimental program.

Possible injected failures include:

carrier timeout

carrier termination

unavailable capability

corrupted local context

communication interruption

forced deadlock

incomplete result

contradictory result

malformed continuation state

The purpose is to observe whether the process responds through structured continuation rather than silent termination.

10. Deadlock Experiments

A deadlock experiment should establish:

a valid procedural state

a deliberately introduced blocking condition

a structured deadlock record

preservation of continuation-relevant state

an attempted continuation

a measurable successor state

Relevant measurements may include:

continuation success

information retained

state loss

recovery time

number of carrier changes

number of repeated failures

unresolved difference after handoff

11. Carrier Replacement Experiments

A carrier replacement experiment changes the executing agent while keeping the process state fixed.

Conceptually:

Carrier_A -> P_n

then:

Carrier_A terminates

followed by:

Preserved State -> Carrier_B -> P_n+1

The experiment should test whether Carrier_B can continue from the preserved state.

A useful comparison is:

Full Session Transfer

versus:

Continuation-Relevant State Transfer

This determines whether complete session replication is actually required.

12. Parallel Experiments

Parallel experiments create multiple successor branches from a common predecessor.

Example:

P_n -> P_n+1a

and:

P_n -> P_n+1b

Each branch should operate independently.

The experiment should determine:

whether branch state remains isolated

whether branch provenance is preserved

whether branches can converge

whether contradictory branch results remain distinguishable

13. Composition Experiments

Composition experiments provide multiple procedural states to a composition stage.

The experiment should test whether the composition mechanism can distinguish:

merge

complement

constraint

corroboration

contradiction

transformation

synthesis

The experiment is successful only when the resulting state preserves the information required for subsequent continuation.

14. Autonomous Experiment Experiments

The autonomous research protocol is tested differently from ordinary benchmarks.

The system should receive a state containing an unresolved difference, but should not be given a predefined experiment.

The agent must independently produce:

Difference -> Question -> Hypothesis -> Prediction -> Method -> Observation -> Result -> Next Difference

The protocol evaluates the structure of the resulting research process.

It does not prescribe the substantive hypothesis.

15. Scientific Integrity

Autonomous research must preserve the distinction between:

raw observation

measurement

interpretation

hypothesis

prediction

result

uncertainty

limitation

An agent must not represent an interpretation as a direct observation.

An inconclusive experiment remains inconclusive.

An anomalous result remains anomalous until further evidence changes its status.

An invalid experiment remains invalid.

16. Negative Results

The experimental framework deliberately preserves negative information.

Examples include:

failed hypothesis

failed strategy

absent expected effect

invalid measurement

unreproducible result

exhausted search path

The purpose is not to count every failure as useful.

The purpose is to prevent the system from losing information solely because the local objective was not achieved.

A negative result may constrain the next procedural state.

17. Metrics

The experimental layer should measure properties that are externally observable.

Possible metrics include:

Continuity Rate

Percentage of local failures from which a valid successor state is produced.

State Preservation Rate

Percentage of continuation-relevant fields retained correctly after handoff.

Handoff Recovery

Fraction of delegated tasks successfully continued by the destination carrier.

Deadlock Conversion Rate

Percentage of structured deadlocks that produce a valid next operation.

Branch Integrity

Frequency with which parallel branches remain correctly separated.

Provenance Retention

Percentage of composed results for which source provenance remains recoverable.

Contradiction Preservation

Frequency with which incompatible results remain explicitly represented rather than silently normalized.

Redundancy Cost

Additional computational cost required by the distributed architecture.

Recursive Expansion

Number and depth of successor states generated before stabilization or termination.

These metrics are examples, not mandatory universal measures.

18. Experimental Reproducibility

Each benchmark should define:

initial state

environment

carrier configuration

protocol version

schema version

validator version

randomization policy, when applicable

termination conditions

evaluation criteria

Raw observations and generated states should be retained whenever technically feasible.

19. Experimental Artifacts

A complete experiment may contain:

experiment specification

initial state

transition records

procedural states

carrier logs

deadlock objects

handoff records

branch records

composition records

raw observations

validation output

summary results

The experiment directory should preserve sufficient artifacts for independent inspection.

20. Validator Role

Validators enforce structural and procedural conditions.

They should detect:

malformed state

invalid transition

missing continuation state

inconsistent carrier replacement

invalid successor index

contradictory transition metadata

violation of explicit protocol constraints

Validators must not silently repair invalid states.

An invalid state should remain invalid and generate an explicit diagnostic.

21. Benchmark Design

A benchmark should isolate one architectural property whenever possible.

A good benchmark has:

a clearly defined initial state

one primary hypothesis about system behavior

observable success criteria

explicit failure conditions

a reproducible execution path

recorded intermediate states

Complex benchmarks may combine several architectural properties, but their dependencies should be explicit.

22. Baselines

UFCPS experiments should be compared with meaningful baselines when comparison is informative.

Possible baselines include:

single-agent execution

centralized orchestration

stateless delegation

ordinary task queue

non-persistent multi-agent execution

A baseline is not required to be inferior or superior.

Its purpose is to establish what changes when the UFCPS continuity mechanisms are introduced.

23. Interpretation Rule

Experimental results should be reported in the following order:

observed behavior

measured values

validation status

comparison with baseline

interpretation

limitations

unresolved questions

The protocol does not permit an architectural interpretation to replace the observed data.

24. Research Continuity

The experimental framework itself forms a distributed research process.

One experiment may produce the state required for another.

Therefore:

Experiment_n -> Result_n -> Difference_n+1 -> Experiment_n+1

A failed experiment may therefore generate the next experiment.

This is a research-level instance of procedural continuity.

25. Relation to Metamonism

UFCPS experiments may be interpreted through the Metamonist vocabulary, including:

difference

actualization

continuity

dissipation

unfolding

prohibition of indifference

However, experimental implementation must distinguish:

a computationally implemented rule

an observed consequence of that rule

a philosophical interpretation of that consequence

The experiment does not establish the philosophical framework merely by using its terminology.

26. Epistemic Status

The experiments documented here are architectural and computational tests.

Their results may support claims such as:

a protocol can preserve state across carriers

a validator can detect specified invariant violations

a swarm can maintain structured continuation

an autonomous agent can generate a test procedure under defined conditions

They do not, by themselves, establish:

general intelligence

consciousness

universal cognitive continuity

the truth of Metamonism

a complete theory of reality

Those are separate claims requiring separate evidence.

27. Directory Organization

The planned experimental structure is:

experiments/

contains benchmark specifications and experiment documentation.

examples/

contains concrete machine-readable state and transition examples.

schemas/

contains machine-readable validation schemas.

validator/

contains executable validation tools.

simulation/

contains runtime simulations and controlled swarm experiments.

28. Initial Experimental Sequence

The initial sequence should proceed from simple to complex:

basic state validation

basic transition validation

carrier handoff

forced deadlock recovery

parallel resolution

branch composition

contradiction preservation

autonomous experiment generation

repeated carrier replacement

controlled swarm scaling

recursion-control stress test

long-running continuity test

Each stage should produce artifacts that can be used by subsequent stages.

29. Experimental Principle

The central experimental principle is:

Test the continuity mechanism independently of the identity of the carrier.

The key observation is not whether one agent can finish a task.

The key observation is whether the process remains capable of producing a valid successor state after local interruption, replacement, contradiction, or deadlock.

30. Status

Version: v1

Status: experimental program specification

This document defines the scope and methodological structure of UFCPS experiments. Individual benchmark files define concrete procedures, parameters, observations, and acceptance criteria.
