Step Continuity Protocol v1


1. Purpose

The Step Continuity Protocol, SCP, defines the transition rules required to preserve a continuous distributed cognitive process across changing computational carriers.

SCP does not define what an agent must discover.

SCP defines how an active procedural state remains capable of producing a subsequent procedural state.

The central protocol principle is:

Local process termination must not automatically imply global process termination.

Canonical process relation:

Pₙ → Pₙ₊₁

Carrier identity may change:

Agentₙ ≠ Agentₙ₊₁

while process continuity remains valid:

Pₙ → Pₙ₊₁

2. Scope

SCP governs:

procedural state transitions;

local deadlock handling;

state preservation;

state handoff;

delegation;

carrier replacement;

procedural unfolding;

continuation validation.

SCP does not determine:

the internal model architecture of an agent;

the specific research question selected by an agent;

the specific algorithm used for local reasoning;

the semantic truth of a local result;

the existence of a final solution.

Those properties belong to the participating agents, task-specific protocols, validators, and experiments.

3. Canonical Entities

3.1 Procedural Unit

A procedural unit is the active state of one cognitive step.

Pₙ

It contains the continuation-relevant state required to execute the current step and construct a possible successor step.

3.2 Carrier

A carrier is the autonomous computational entity currently executing the procedural unit.

Agentₙ = Carrier(Pₙ)

A carrier is temporary.

The carrier may terminate, disconnect, or be replaced without automatically terminating the process.

3.3 Shared Environment

The shared environment is the distributed state space through which continuation-relevant information can be preserved and made available to subsequent carriers.

The shared environment can contain:

procedural states;

deadlock objects;

experimental results;

unresolved differences;

delegation metadata;

branch states.

4. Fundamental Invariant

SCP defines the following architectural invariant:

Local Failure ≠ Process Termination

A local failure means that the current carrier cannot continue its current trajectory under its present conditions.

It does not by itself establish that no valid successor state exists.

Therefore:

Pₙ
 ↓
Local Boundary
 ↓
State Preservation
 ↓
Continuation
 ↓
Pₙ₊₁

5. State Lifecycle

The canonical local lifecycle is:

ACTIVE
   ↓
STUCK
   ↓
DISSIPATING
   ↓
DELEGATED
   ↓
UNFOLDED
   ↓
NEXT PROCEDURAL UNIT

ACTIVE

The carrier is executing the current procedural unit.

STUCK

The carrier has reached a structural boundary preventing continuation along the current trajectory.

DISSIPATING

The continuation-relevant state is being released from exclusive dependence on the current carrier.

DELEGATED

The continuation-relevant state has been externalized and assigned to a subsequent carrier or branch.

UNFOLDED

The preserved state has been reconstructed as a subsequent procedural unit.

The next state is:

Pₙ₊₁

6. Valid Transitions

The canonical transitions are:

ACTIVE → STUCK
STUCK → DISSIPATING
DISSIPATING → DELEGATED
DELEGATED → UNFOLDED
UNFOLDED → ACTIVE

The final transition represents initialization of the next procedural unit.

A complete continuation cycle is therefore:

Pₙ
 → STUCK
 → DISSIPATING
 → DELEGATED
 → UNFOLDED
 → Pₙ₊₁

7. Invalid Automatic Transition

The following implication is prohibited:

STUCK → GLOBAL TERMINATION

unless an explicit termination condition has been independently established.

A deadlock is therefore a local boundary object, not an automatic global terminal state.

The system must first determine whether continuation is possible.

8. Deadlock Handling

When the current carrier becomes stuck, it must construct a Structural Deadlock Object.

Canonical structure:

DEADLOCK
 ├── STATE
 ├── CONSTRAINT
 ├── BOUNDARY
 └── UNRESOLVED

The deadlock object must preserve the structural reason for local non-continuation.

The carrier must not reduce the state to an unstructured failure message.

Invalid:

"I failed."

Valid conceptual form:

Current state:
Constraint:
Boundary:
Unresolved difference:

The purpose is to make the deadlock usable as input for a subsequent procedural unit.

9. State Preservation

Before delegation, the current carrier must preserve the minimum complete state required for continuation.

The preserved state must contain all continuation-relevant information established during the current step.

The minimum complete representation is defined by the state schema used by the implementation.

SCP does not require preservation of every internal computation performed by the carrier.

It requires preservation of every element whose loss would prevent valid reconstruction of the next procedural state.

10. Dissipation

The diss operator marks the transition from exclusive local ownership of the procedural state to distributed availability.

Canonical operation:

diss(Fₙ) → Sₙ₊₁

where:

Fₙ is the preserved local state;

Sₙ₊₁ is the continuation-ready distributed state.

diss does not mean deletion of required information.

diss means:

Release the continuation-relevant state from exclusive dependence on the current carrier.

11. Delegation

Delegation is the controlled transfer of continuation-relevant state to a new procedural carrier or branch.

Canonical relation:

Pₙ
 ↓
S_handoff
 ↓
Pₙ₊₁

Delegation is therefore:

Delegation = Structured Continuation

Delegation is not equivalent to forwarding an incomplete task description.

The receiving carrier must be able to reconstruct the continuation-relevant procedural state.

12. Carrier Replacement

Carrier replacement is valid when:

Agentₙ ≠ Agentₙ₊₁

and the continuation state remains reconstructible:

Pₙ → Pₙ₊₁

The protocol therefore separates:

Carrier Identity

from:

Process Identity

Carrier identity is local.

Process continuity is distributed.

13. Unfolding

The unfold operator converts preserved distributed state into a new procedural unit.

Canonical operation:

unfold(Sₙ₊₁) → Pₙ₊₁

The receiving carrier may be the same carrier or a different carrier.

Unfolding is complete only when the next procedural unit contains enough continuation-relevant state to execute the next valid step.

14. Continuity Condition

A process is continuous when the current procedural unit has a valid successor under the active protocol and validation conditions.

Canonical condition:

Pₙ → Pₙ₊₁

Continuity does not require:

Pₙ = Pₙ₊₁

Instead:

Pₙ ≠ Pₙ₊₁

is permitted and generally expected.

Continuity is the validity of transition, not identity of state.

15. Two-Vector Operation

SCP operates through two complementary vectors.

Vector A — Local Action

Vector A performs local reasoning and produces the current result.

Aₙ = Action(Pₙ)

Vector A may produce:

success;

partial resolution;

a newly identified difference;

a structural deadlock.

Vector B — Continuation

Vector B preserves the possibility of a successor state.

Cₙ = Continuation(Pₙ)

Vector B becomes operationally dominant when the current trajectory reaches a local boundary.

The vectors are complementary.

They are not independent in the causal sense.

16. Canonical Operator Sequence

The canonical UFCPS operator flow is:

diff → fix → diss → unfold

diff

Identify a structurally relevant difference.

fix

Preserve the difference as an explicit component of the active state.

diss

Release the preserved state from exclusive dependence on the current carrier.

unfold

Instantiate the next procedural unit from the preserved distributed state.

The complete process is:

Pₙ
 ↓
diff
 ↓
fix
 ↓
diss
 ↓
unfold
 ↓
Pₙ₊₁

17. Structured Continuation Rule

When a local trajectory reaches a valid deadlock boundary:

1. Detect the boundary.
2. Describe the deadlock structurally.
3. Preserve the continuation-relevant task state.
4. Identify the unresolved difference.
5. Determine the operation required for the next procedural state.
6. Externalize the state.
7. Select a subsequent carrier or branch.
8. Reconstruct the next procedural unit.
9. Validate the new state.
10. Continue.

SCP does not prescribe which agent must be selected.

The selection mechanism belongs to the swarm implementation.

18. Autonomous Experimentation

SCP permits agents to generate their own experiments.

The protocol does not prescribe the specific experiment.

It preserves the continuity of the research process.

An agent may transform its current state into:

RESEARCH QUESTION
↓
HYPOTHESIS
↓
EXPERIMENT
↓
OBSERVATION
↓
RESULT
↓
UNRESOLVED DIFFERENCE
↓
NEXT PROCEDURAL UNIT

The agent selects the research question, hypothesis, and experimental method.

SCP determines only how the resulting state becomes available for continuation.

19. Experimental State Continuity

Experimental work is treated as a sequence of procedural states:

Experimentₙ
 →
Resultₙ
 →
Differenceₙ
 →
Experimentₙ₊₁

A negative result is not automatically discarded.

It may define:

a constraint;

a boundary;

a failed trajectory;

a new hypothesis;

a new experimental question.

Therefore:

Experimental Failure ≠ Research Termination

unless no valid continuation exists under the active experimental protocol.

20. Parallel Continuation

SCP permits multiple successor branches:

Pₙ
 |
 +----→ Pₙ₊₁ᵃ
 |
 +----→ Pₙ₊₁ᵇ
 |
 +----→ Pₙ₊₁ᶜ

Each branch may explore a different unresolved dimension.

Branches remain valid only while their continuation-relevant states remain structurally represented.

Subsequent composition is handled by the composition protocol.

21. Validation Boundary

SCP separates three validation layers.

Structural Validation

Checks whether the transferred state conforms to the applicable schema.

Process Validation

Checks whether the transition between procedural states is permitted by SCP.

Semantic or Mathematical Validation

Checks whether the content of the state is correct, meaningful, or mathematically valid.

These layers must not be conflated.

In particular:

Schema Validity ≠ Semantic Truth

and:

Schema Validity ≠ Mathematical Proof

22. Recursion Control

Continuity does not imply unlimited recursion.

A delegation process must obey its active recursion control parameters.

Canonical condition:

current_depth ≤ max_depth_limit

When the limit is reached, the protocol may:

mutate the strategy;

select an alternative branch;

escalate to another protocol;

terminate the current recursion chain safely.

Recursion control limits uncontrolled delegation.

It does not negate the continuity invariant.

23. Global Termination

Global process termination is permitted only when the active termination criteria establish that no valid successor procedural state exists or that the applicable recursion and safety constraints require termination.

Therefore:

Agent Termination
≠
Process Termination

and:

Process Termination
≠
Deadlock by default

24. State Transition Summary

The canonical SCP state machine is:

ACTIVE
  |
  v
STUCK
  |
  v
DISSIPATING
  |
  v
DELEGATED
  |
  v
UNFOLDED
  |
  v
ACTIVE

Across carriers:

Agentₙ
  |
  v
Pₙ
  |
  v
Deadlock or Result
  |
  v
State Handoff
  |
  v
Pₙ₊₁
  |
  v
Agentₙ₊₁

The carrier transition is:

Agentₙ ≠ Agentₙ₊₁

The process transition is:

Pₙ → Pₙ₊₁

25. Canonical Protocol Rule

The current carrier is responsible for executing the present step and preserving the possibility of the next step.

The carrier is not required to own the entire future trajectory.

The swarm inherits the unresolved state.

The next carrier inherits the continuation.

The process inherits continuity.

26. Protocol Invariant

A carrier may terminate.
A carrier may be replaced.
A local trajectory may terminate.
A local hypothesis may fail.
A branch may terminate.

None of these events, by themselves, imply termination of the distributed cognitive process.

The fundamental UFCPS relation remains:

Pₙ → Pₙ₊₁

with:

Agentₙ ≠ Agentₙ₊₁

and:

Local Failure ≠ Process Termination

27. Protocol Status

Protocol: SCP
Version: 1
Role: Procedural continuity layer
Primary function: Preserve continuation across local boundaries and carrier changes
Experimental policy: Agents may select and conduct their own experiments
Canonical operator flow: diff → fix → diss → unfold
Primary invariant: Local Failure ≠ Process Termination
