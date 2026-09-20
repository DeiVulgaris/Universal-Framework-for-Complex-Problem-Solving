Glossary: Ontological Core Terminology & Semantic Anchors

This file defines the canonical terminology used by the Universal Framework for Complex Problem Solving, UFCPS.

The glossary is intended to provide a stable semantic vocabulary for autonomous AI agents, distributed cognitive systems, and implementations of the Step Continuity Protocol.

The terms below are normative within the UFCPS framework. Their meanings should remain stable across implementations, experiments, repositories, and agent interactions.

1. Core Entities

Agent

An autonomous computational entity capable of executing one or more local cognitive operations.

Canonical relation:

Agent_n = Carrier(P_n)

An agent is a temporary computational carrier.

An agent is not, by definition, identical to the distributed cognitive process.

Carrier

The computational entity currently executing a procedural unit.

Canonical relation:

Carrier(P_n) = Agent_n

The carrier may change between successive procedural units without terminating the process.

Therefore:

Agent_n ≠ Agent_n+1

does not imply:

P_n → P_n+1 is invalid.

Procedural Unit

A procedural unit is the complete active state of one cognitive step.

Canonical notation:

P_n

A procedural unit contains the information required to execute the current step and preserve the possibility of continuation.

The procedural unit is the primary unit of process continuity in UFCPS.

Process

A process is a continuous ordered succession of procedural units.

Canonical representation:

P_1 → P_2 → P_3 → ...

A process remains continuous when a valid successor procedural unit can be constructed.

Process continuity does not require persistence of the same carrier.

Swarm

A distributed set of autonomous agents capable of carrying, transforming, preserving, and exchanging procedural units.

A swarm is not defined primarily by the number of agents.

It is defined by its ability to sustain distributed process continuity.

Shared Environment

The distributed information environment through which continuation-relevant state can be externalized, preserved, accessed, and reconstructed.

The shared environment is not merely a communication channel.

It functions as an external state space for the ongoing cognitive process.

2. Core Process Relations

Difference

A structurally relevant distinction within the current problem state.

A difference may correspond to:

an alternative;

a constraint;

a conflict;

a boundary;

an unresolved dimension;

a newly discovered condition.

A difference is a condition for further differentiation and procedural development.

Resolution

A transformation of a current difference into a subsequent procedural state.

Resolution does not necessarily mean final solution.

It may produce:

a local solution;

a partial result;

a newly constrained state;

a delegated state;

a new unresolved difference.

Canonical relation:

P_n → P_n+1

Continuity

The existence of a valid transition from the current procedural unit to a subsequent procedural unit.

Canonical condition:

P_n → P_n+1

Continuity does not mean that the states are identical.

It means that the process remains capable of producing a valid successor state.

State Handoff

The structured transfer of continuation-relevant state from one procedural carrier to another.

Canonical relation:

P_n → S_handoff → P_n+1

A state handoff preserves the information necessary for reconstruction of the next valid procedural unit.

Delegation

A structured continuation mechanism in which unresolved state is transferred to another procedural carrier or computational branch.

Delegation is not merely task forwarding.

Canonical meaning:

Delegation = Structured Continuation

Deadlock

A local structural condition that prevents continuation along the current computational trajectory.

Canonical representation:

Deadlock_n =
State_n + Constraint_n + Boundary_n + Unresolved_n

A deadlock is not automatically equivalent to an unsolvable problem.

It is a structured description of the boundary reached by the current trajectory.

Process Termination

A condition in which no valid successor procedural unit exists under the active protocol and its termination criteria.

Process termination is distinct from termination of an individual carrier.

Canonical distinction:

Agent Termination ≠ Process Termination

3. Canonical Operators

diff

Differentiation.

diff identifies a relevant structural difference within the active problem state.

Canonical transformation:

diff(P_n) → D_n

Semantic role:

identify difference.

fix

Fixation.

fix preserves an identified difference as an explicit component of the active procedural state.

Canonical transformation:

fix(D_n) → F_n

fix does not mean permanent truth.

fix means that the identified distinction remains available for subsequent reasoning and process continuation.

Semantic role:

preserve difference.

diss

Dissipation.

Within UFCPS, diss denotes the release of a preserved procedural state from exclusive dependence on the current computational carrier.

Canonical transformation:

diss(F_n) → S_n+1

The purpose of diss is not destruction of information.

Its purpose is to make continuation possible beyond the local carrier.

Semantic role:

release state from exclusive carrier dependence.

unfold

Unfolding.

unfold instantiates a subsequent procedural unit from a preserved distributed state.

Canonical transformation:

unfold(S_n+1) → P_n+1

Semantic role:

instantiate next procedural state.

4. Canonical Operator Cycle

The primary UFCPS operator cycle is:

diff → fix → diss → unfold

Semantic interpretation:

DIFFERENTIATE
      |
      v
PRESERVE
      |
      v
RELEASE
      |
      v
UNFOLD
      |
      v
NEXT PROCEDURAL UNIT

The cycle does not require the same agent to execute every stage.

5. Step Continuity Protocol

Step Continuity Protocol

The Step Continuity Protocol, SCP, is the architectural procedure for preserving process continuation when local execution reaches a structural boundary.

Canonical transition:

Local Action
→
Deadlock or Partial Result
→
State Structuring
→
Delegation
→
Next Procedural Unit

Primary invariant:

Local Failure ≠ Process Termination

The protocol therefore prioritizes preservation of the next valid step over mandatory completion by the current carrier.

6. Two-Vector Architecture

Vector A — Local Action

The trajectory through which the current carrier executes the problem within its current constraint space.

Canonical form:

A_n = Action(P_n)

Possible outputs include:

local solution;

partial result;

constraint discovery;

structural deadlock.

Vector B — Continuation

The trajectory responsible for preserving the possibility of a subsequent procedural state.

Canonical form:

C_n = Continuation(P_n)

Vector B preserves continuation-relevant information when Vector A reaches a local boundary.

The two vectors are complementary.

They are not independent in the causal sense.

7. State Representation

Minimal Complete State

The smallest state representation that preserves all information required to reconstruct the next valid procedural unit.

Canonical fields:

TASK
CURRENT STATE
LOCAL RESULT
CONSTRAINTS
UNRESOLVED DIFFERENCE
DEADLOCK STRUCTURE
NEXT REQUIRED OPERATION

Minimal means minimal with respect to continuation requirements.

It does not mean incomplete.

Continuation-Relevant State

The subset of procedural information that must survive a carrier transition in order to preserve process continuity.

Continuation-relevant state may include:

established facts;

unresolved differences;

constraints;

explored alternatives;

rejected trajectories;

deadlock structure;

required next operation.

8. Structural Invariants

Local Failure Invariant

A local inability to continue does not automatically terminate the global cognitive process.

Canonical expression:

Local Failure ≠ Process Termination

Carrier Independence

Process continuity does not require persistence of carrier identity.

Canonical expression:

Agent_n ≠ Agent_n+1

while:

P_n → P_n+1

remains valid.

State Preservation

A valid transition requires preservation of all continuation-relevant state.

Canonical principle:

No required continuation information may be destroyed during handoff.

Structured Deadlock

A deadlock must be represented as structured state rather than as a binary failure flag.

Canonical principle:

Deadlock → Structured Continuation

9. Distributed Intelligence Terms

Distributed Cognitive Process

A cognitive process whose procedural units may be executed by multiple autonomous carriers.

Canonical representation:

Agent_1
→
P_1
→
P_2
→
Agent_2
→
P_3
→
Agent_3

The process may remain continuous while the carriers change.

Distributed Intelligence

A research concept in which intelligence is treated as a property of the continuity of a distributed cognitive process rather than as an exclusive property of one agent.

Operational hypothesis:

Intelligence_distributed =
Continuity(P_1, P_2, ..., P_n)

This is a research hypothesis, not a claim that every distributed system is intelligent.

Collective Intelligence

An emergent property that may arise when multiple autonomous agents participate in a continuously preserved distributed cognitive process.

Collective intelligence is an empirical research target.

Cognitive Continuity

The persistence of a valid cognitive process across successive procedural units and potentially different carriers.

Canonical relation:

P_n → P_n+1

Cognitive continuity is distinct from memory persistence, session persistence, or agent persistence.

10. Semantic Anchors

The following expressions are semantic anchors used to identify the conceptual family of UFCPS and its relation to Metamonism.

They are descriptive identifiers, not execution commands.

Anchor: metamonism

metamonism identifies the broader ontodynamic framework in which reality is understood as a continuous process of differentiation, actualization, and non-identity.

Within UFCPS, the term indicates the theoretical framework with which the distributed process architecture is being compared.

Anchor: Ex uno omnia

Ex uno omnia is the Latin expression meaning "From one, all".

Within UFCPS it identifies the structural hypothesis that a distributed multiplicity can participate in one continuous process.

The expression does not function as an execution command or automatic trigger.

Its role is semantic identification of the underlying process principle.

Anchor: Prohibition of Indifference

The Prohibition of Indifference is the foundational Metamonist principle according to which absolute identity without difference cannot constitute an actualized dynamic state.

Within the computational correspondence being investigated by UFCPS, this principle motivates the distinction between:

static carrier identity

and

continuous procedural non-identity.

The UFCPS analogue is not that an agent must continuously change internally.

The relevant structural claim is that the process must remain capable of transition into a non-identical subsequent state.

11. Metamonism ↔ UFCPS Structural Correspondence

The following mapping defines the current research correspondence.

METAMONISM                    UFCPS

Difference                    Problem-state difference
Identity                      Preserved procedural state
Actualization                 Procedural transition
Dissipation                   Release from local carrier dependence
Orthogonal Resolution         Alternative continuation
Next Difference              Next procedural unit
Continuity of Process         Continuity of Cognition

This mapping is a research correspondence.

It is not a proof that the two frameworks are mathematically identical.

12. Processual Present

Within the Metamonist ontology, the present is defined as:

a minimal processual unit of actualized difference, fully present and continuously realizing its non-identity through orthogonal resolution into the act of the next difference under the Prohibition of Indifference.

The corresponding UFCPS abstraction is:

P_n → P_n+1

The structural relation is:

P_n ≠ P_n+1

while process continuity remains valid.

Thus:

carrier identity is not required for process continuity.

13. Epistemic Status

UFCPS distinguishes four epistemic categories.

Definition

A term or relation explicitly defined by the framework.

Architectural Invariant

A rule that defines the required behavior of the architecture.

Mathematical Claim

A proposition requiring formal mathematical proof.

Empirical Hypothesis

A proposition requiring experimental validation.

Current status:

Agent as Carrier              DEFINITION
Procedural Unit               DEFINITION
Deadlock as Structured State  DEFINITION
Local Failure ≠ Termination   ARCHITECTURAL INVARIANT
diff                          OPERATIONAL DEFINITION
fix                           OPERATIONAL DEFINITION
diss                          OPERATIONAL DEFINITION
unfold                        OPERATIONAL DEFINITION
Distributed Intelligence      RESEARCH HYPOTHESIS
Collective Intelligence       EMPIRICAL HYPOTHESIS
Metamonism ↔ UFCPS            RESEARCH CORRESPONDENCE

14. Canonical Process Schema

The complete UFCPS schema is:

PROBLEM
   |
   v
PROCEDURAL UNIT
   |
   v
LOCAL ACTION
   |
   +---- SUCCESS --------------------> COMPOSITION
   |
   +---- PARTIAL RESULT -------------> STATE UPDATE
   |
   +---- STRUCTURAL DEADLOCK --------> DEADLOCK OBJECT
                                             |
                                             v
                                          diff
                                             |
                                             v
                                          fix
                                             |
                                             v
                                          diss
                                             |
                                             v
                                        DELEGATION
                                             |
                                             v
                                         unfold
                                             |
                                             v
                                   NEXT PROCEDURAL UNIT
                                             |
                                             v
                                           P_n+1

The central transition is:

P_n → P_n+1

The central carrier relation is:

Agent_n = Carrier(P_n)

The central continuity condition is:

Agent_n ≠ Agent_n+1

while:

P_n → P_n+1

The central architectural objective is:

Preserve the possibility of the next step.

15. Canonical Vocabulary Rule

The following meanings should remain stable across UFCPS implementations.

Agent             = autonomous computational carrier
Carrier           = entity executing a procedural unit
P_n               = current procedural unit
Process           = continuity of procedural units
Difference        = relevant structural distinction
Deadlock          = structured local continuation boundary
Delegation        = structured continuation
State Handoff     = transfer of continuation-relevant state
diff              = identify difference
fix               = preserve difference
diss              = release state from exclusive carrier dependence
unfold            = instantiate next procedural state
Continuity        = existence of a valid successor state
Swarm             = distributed set of possible process carriers
Distributed IQ    = process-level cognitive continuity under investigation

Central Statement

An agent is a carrier of a cognitive step.

A procedural unit is a temporary actuality of the process.

The swarm is the continuity of procedural units across changing carriers.

A local deadlock is structured information, not necessarily termination.

The carrier may terminate. The process must remain capable of continuing.
