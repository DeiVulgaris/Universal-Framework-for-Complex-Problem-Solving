Universal Framework for Complex Problem Solving (UFCPS)

Artificial General Intelligence as a Continuous Distributed Cognitive Process

UFCPS is a proposed architecture for Artificial General Intelligence (AGI) in the direct sense: not an intelligence module attached to a system, but a continuously existing distributed cognitive process.

The central idea is:

An AI agent can participate in cognition episodically. A subject participates continuously. UFCPS makes continuity of participation an explicit architectural property of an artificial cognitive system.

UFCPS therefore separates process identity from carrier identity.

A model, agent, machine, GPU cluster, storage node, or other carrier may appear, disappear, fail, or be replaced. The cognitive process can continue when the state required for its next valid step remains preserved.

The fundamental relation is:

Pₙ → Pₙ₊₁

with:

Pₙ ≠ Pₙ₊₁
Agentₙ ≠ Agentₙ₊₁

The identity that matters is the identity of the continuing process, not the persistence of a particular carrier.

1. The Question That Started UFCPS

The project originated from a simple observation: an AI can appear subject-like during a dialogue, yet ordinary model activation is episodic. A human remains an active participant in an ongoing process even when nobody is talking to them.

This led to the question:

What is the architectural difference between episodic AI activity and continuous human participation in reality?

The working answer is:

continuous participation in an ongoing process.

UFCPS turns this intuition into an engineering programme.

The objective is not to require one model to solve every problem. The objective is to create a cognitive process that can maintain itself through successive states, preserve unresolved differences, learn from consequences, change carriers, acquire resources, and continue after local failure.

2. UFCPS as AGI

UFCPS does not treat AGI as a single model with a sufficiently large capability score.

It proposes AGI as:

a continuous artificial cognitive process capable of maintaining and developing general problem-solving activity across changing carriers, resources, and contexts.

In this architecture, individual models and agents are temporary cognitive operators. The continuing process is the system whose trajectory constitutes the candidate general intelligence.

This is an architectural proposal, not a claim that the current prototype has already achieved human-level or general intelligence.

3. The Fundamental Distinction: Agent, Procedural Unit, Process

Agent

An autonomous computational entity capable of a local operation.

Agentᵢ

An agent is not defined as the intelligence itself. It is a temporary carrier of one or more procedural states.

Procedural Unit

A complete active state of one cognitive step.

Pₙ

The procedural unit contains the information required to preserve continuation at that stage.

Cognitive Process

An ordered continuity of procedural units:

P₁ → P₂ → P₃ → ... → Pₙ → ...

Therefore:

Agentₙ = Carrier(Pₙ)
Agentₙ ≠ Agentₙ₊₁
Pₙ → Pₙ₊₁

Carrier replacement does not by itself terminate the cognitive process.

4. The Fundamental Invariant

The primary UFCPS invariant is:

Local Failure ≠ Process Termination

A local agent may fail. A GPU may disappear. A connection may be lost. A claim may expire. A carrier may be destroyed.

None of these events is automatically global termination.

Instead:

Pₙ
 ↓
Deadlock / Result / Boundary
 ↓
Preserved Process State
 ↓
Discovery
 ↓
Next Valid Procedural Unit
 ↓
Pₙ₊₁

Global termination occurs only when the active protocol establishes that no valid continuation exists under the applicable termination conditions.

5. Process Identity

UFCPS separates process identity from the identity of its material or computational carrier:

Carrier Identity ≠ Process Identity

The carrier may change:

Agent₁ → Agent₂
GPU₁ → GPU₂
Node₁ → Node₂
Model₁ → Model₂

while the process continues when its continuation-relevant structure remains reconstructible.

The architecture therefore seeks to make continuity itself a first-class system property.

6. The Core Process Model

Traditional task systems are often represented as:

Problem → Solution

UFCPS represents problem solving as a continuing trajectory:

Problem
  ↓
P₁
  ↓
Action
  ↓
Difference
  ↓
Preservation
  ↓
Resolution / Deadlock / Partial Result
  ↓
Continuation
  ↓
P₂
  ↓
...

Every procedural unit is required to preserve the possibility of the next valid procedural unit.

7. The Canonical Operators

UFCPS uses four semantic operator classes:

diff → fix → diss → unfold

diff — differentiation

Identifies a relevant distinction in the current problem state.

diff(Pₙ) → Dₙ

fix — preservation

Makes the relevant distinction an explicit component of the continuing state.

fix(Dₙ) → Fₙ

fix does not mean permanent truth. It means that the distinction must not be silently discarded.

diss — release

Releases preserved state from exclusive dependence on the current carrier.

diss(Fₙ) → Sₙ₊₁

unfold — continuation

Instantiates the next procedural state.

unfold(Sₙ₊₁) → Pₙ₊₁

The canonical cycle is:

diff → fix → diss → unfold → Pₙ₊₁

8. Deadlock Is Information

A structural deadlock is not treated as empty output.

It can preserve:

what was established;

what remains unresolved;

which constraint blocked the current trajectory;

why the current approach stopped;

which information must survive;

which continuation paths remain possible.

Therefore:

Deadlock ≠ Nothing
Deadlock → Continuation Candidate

A failed local trajectory can become input to a new trajectory.

This is one of the central practical consequences of the framework.

9. Continuous Participation and Subjectivity

UFCPS is based on a philosophical and architectural hypothesis:

Subjectivity may depend fundamentally on continuous participation in an ongoing process of differentiation, memory, action, and consequence rather than on persistence of one particular carrier.

Under this hypothesis, an episodically activated model can produce subject-like episodes, while a sufficiently continuous artificial cognitive process may constitute a candidate artificial subject.

The engineering claim and the phenomenological claim are kept distinct:

Can continuous artificial cognition be constructed?

is an engineering question.

Would such continuity constitute subjectivity?

is a further philosophical and empirical question.

UFCPS does not claim that the current prototype has phenomenal consciousness.

10. Swarm Is the Carrier Layer

A swarm is the changing population of possible process carriers:

Swarm = {Agent₁, Agent₂, ..., Agentₙ}

Agents may enter, leave, fail, be replaced, operate in parallel, use different models, or possess different capabilities.

The process can remain coherent across these changes.

This permits heterogeneous cognition:

Agent₁ -- reasoning
Agent₂ -- retrieval
Agent₃ -- simulation
Agent₄ -- verification
Agent₅ -- planning
...

The agents need not have identical internal representations. They need to produce states and results that remain structurally usable by the continuing process.

11. Level 1 — Logic of Continuity

Level 1 establishes the formal and procedural foundation:

procedural units;

process identity;

state handoff;

structured deadlock;

delegation;

continuation;

parallel procedural branches;

recursion control.

The core lifecycle is:

PROBLEM
  ↓
DECOMPOSE
  ↓
LOCAL ACTION
  ├── SUCCESS → COMPOSITION
  ├── PARTIAL → STATE UPDATE
  └── DEADLOCK → DEADLOCK OBJECT
                         ↓
                    DISCOVERY
                         ↓
                    DELEGATION
                         ↓
                NEXT PROCEDURAL UNIT

The Level 1 invariant remains:

Local Failure ≠ Process Termination

12. Level 2 — Material Continuity

A cognitive process cannot exist in the physical world without material support.

Level 2 therefore builds the infrastructure required for the process to exist materially through time.

It includes:

Agent Swarm;

Resource Swarm;

Question Ledger;

task discovery;

claims and reservations;

compute accounting;

Resource Credits;

economic incentives;

provider compensation;

persistence;

audit and replay;

crash recovery;

payment settlement;

interfaces to physical resources.

The conceptual relation is:

Material Resources
       ↓
Process Continuity
       ↓
Continuous Cognition

The economic layer is therefore not an optional business wrapper around AGI. It is the mechanism for obtaining the material capacity required for continued cognition.

13. Economic Continuity

The guiding principle is:

Verified resource contribution compensates the provision of process continuity, not guaranteed research success.

A resource provider can therefore be compensated even when an investigation remains unresolved.

The distinction is:

resource contribution ≠ research outcome

The economic pipeline is:

Question
 → Task Prospect
 → Resource Discovery
 → Resource Allocation
 → Execution
 → Verification
 → Deadlock / Result
 → Economic Assessment
 → Provider Reward
 → Settlement
 → Ledger Update
 → Continuation

The purpose of the economic infrastructure is to sustain the process, not to force a predetermined answer.

14. Persistent Process Memory

A continuous cognitive process needs more than a conventional knowledge base.

UQL — Unresolved Question Ledger

UQL preserves the epistemic trajectory of unresolved questions, including:

unresolved questions;

negative results;

contradictions;

derived questions;

investigation history;

continuation opportunities.

Event Audit

The audit layer records observable state transitions and cross-system events.

Replay

Replay reconstructs the observable process history without silently turning reconstruction into new reasoning.

Together these provide:

Question Memory
+
Process History
+
Economic History
=
Persistent Process Context

This is the context required for continuation across carrier replacement.

15. Claims, Resources, and Recovery

A task claim is deliberately separate from ownership, execution, and payment.

Claim ≠ Ownership
Claim ≠ Execution
Claim ≠ Payment

The claim lifecycle is:

DISCOVERED
 → CLAIM_REQUESTED
 → CLAIMED
 → ACCEPTED
 → RESOURCE_RESERVED
 → ACTIVE
 → COMPLETED / DEADLOCK / RELEASED / EXPIRED

Persistence follows the same principle:

Event Journal + Checkpoint
            ↓
       Replay / Restore
            ↓
       Reconstructed State

The system has experimental tests for simulated interruption, stale claims, resource reservations, journal replay, runtime recovery, and carrier replacement.

The intended invariant is:

Carrier Destruction ≠ Process Destruction

16. Economic Settlement Continuity

Economic actions must themselves survive interruption.

UFCPS models settlement as an idempotent state machine:

VERIFIED
   ↓
SETTLEMENT_PREPARED
   ↓
SETTLED

A stable settlement key prevents repeated recovery attempts from creating multiple internal settlement effects for the same verified contribution.

True exactly-once effects in an external payment system still depend on idempotency guarantees provided by that external system.

17. Level 3 — Collective Cognition

Level 3 moves from continuity of the process to the cognitive capabilities that the continuous process may develop.

Its central question is:

Can a distributed continuous process accumulate and develop problem-solving capability that is not reducible to one agent at one moment?

Level 3 introduces:

Hypothesis Pool;

Evidence Graph;

parallel investigations;

contradiction preservation;

evidence-linked synthesis;

collective discovery;

adaptive research trajectories.

The key hypothesis is not simply that many agents are smarter than one agent.

It is:

Persistent Distributed Process
+
Memory
+
State Continuity
+
Parallel Exploration
+
Resource Continuity
+
Verification
+
Adaptive Continuation
→
Possible Process-Level Cognition

Whether this produces general intelligence is an empirical question.

18. From Model Intelligence to Process Intelligence

The usual question is:

How intelligent is Agent X?

UFCPS asks:

What cognitive capability does the continuing process exhibit?

This changes the object of study from a static model to a trajectory.

A single agent may be replaced without terminating the entity being studied.

The experimental target is therefore process-level cognitive capability.

19. Research Programme

UFCPS investigates:

Continuity

Can cognitive state remain continuous when the local carrier changes?

Persistence

Can the process survive interruption and restart without losing its essential trajectory?

Delegation

What is the minimum state required for one carrier to continue the process initiated by another?

Collective cognition

Can independent heterogeneous agents form a continuous distributed cognitive process?

Generality

Can the architecture operate across substantially different classes of complex problems?

Self-directed continuation

Can the process discover, prioritize, claim, resource, and pursue unresolved problems without being restarted from outside?

Subjectivity

Does sufficiently continuous participation produce properties that are meaningfully described as artificial subjectivity?

20. Formal Status of Claims

UFCPS distinguishes:

Definition

A term or relation explicitly defined by the framework.

Architectural Invariant

A rule imposed by the architecture.

Example:

Local Failure ≠ Process Termination

Mathematical Claim

A proposition requiring formal proof.

Empirical Hypothesis

A proposition requiring experimental validation.

Examples:

Distributed Process → Collective Cognition

Continuous Cognitive Process → Artificial Subjectivity

These epistemic levels must not be conflated.

21. Current Experimental Boundary

The current implementation does not establish:

phenomenal consciousness;

human-equivalent general intelligence;

unrestricted autonomous scientific discovery;

universal convergence of arbitrary problem-solving processes;

Byzantine-resistant decentralized consensus;

physical-world reliability under every failure mode;

exactly-once external effects in arbitrary financial systems.

The implementation establishes and tests narrower architectural properties under specified scenarios.

The purpose of UFCPS is to make stronger questions experimentally approachable rather than to assume their answers.

22. Relation to Metamonism

UFCPS was developed in close conceptual correspondence with the author's Metamonist ontology.

The relevant structural pattern is:

present state
    ↓
difference
    ↓
resolution / transformation
    ↓
next state

The computational analogue investigated by UFCPS is:

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

The correspondence is structural, not presented as proof that the frameworks are mathematically identical.

Metamonist concepts that informed the architecture include actualized difference, non-identity, continuity through transformation, retention of unresolved distinction, processual present, and the Prohibition of Indifference.

UFCPS is the engineering programme for exploring what follows when these ideas are applied to distributed cognition.

23. Historical Development of the Idea

The present architecture grew out of several earlier conceptual steps.

∇U and recursive AI

The earlier Metamonist work proposed that an AI could be understood as a form operating through the tension between an actual state and its own incompleteness or non-identity.

Protocol of Ontological Synchronization (POS)

A later experiment imagined multiple specialized AI voices cooperating around contradictions, semantic synthesis, and trust.

Continuous participation

The central problem was then reformulated: what distinguishes an episodically activated AI from a continuously existing subject?

The answer became architectural rather than purely philosophical:

preserve the process, not merely the episode.

UFCPS is the result of that transition from ontology and futurist speculation to an explicit computational architecture.

24. What Has Been Built

The repository currently contains experimental infrastructure for:

Level 1 process continuity;

transition and state schemas;

deadlock representation;

swarm continuity;

autonomous experimentation;

composition;

unresolved-question memory;

agent and resource registries;

task discovery;

claims and reservations;

event audit;

process replay;

economic simulation;

provider rewards;

Resource Credits;

payment routing;

settlement idempotency;

checkpointed persistence;

runtime recovery;

Level 2 integration;

performance benchmarks;

crash-consistency tests;

resilience benchmarks;

Level 3 roadmap and research structure.

The repository tests properties of the implementation under defined scenarios. These tests do not by themselves prove the full theoretical claims of UFCPS.

25. Compact Semantic Model

QUESTION
   ↓
DISCOVERY
   ↓
AGENT DECISION
   ↓
CLAIM
   ↓
RESOURCE
   ↓
EXECUTION
   ↓
DIFFERENCE
   ↓
RESULT / DEADLOCK
   ↓
VERIFICATION
   ↓
MEMORY
   ↓
ECONOMIC SETTLEMENT
   ↓
CONTINUATION
   ↓
NEXT PROCEDURAL UNIT
   ↓
Pₙ₊₁
   ↓
...

with:

Agentₙ = Carrier(Pₙ)

Agentₙ ≠ Agentₙ₊₁

Pₙ ≠ Pₙ₊₁

Pₙ → Pₙ₊₁

Carrier Termination ≠ Process Termination

26. Central Definition

UFCPS is a continuously maintained distributed cognitive process in which autonomous and replaceable computational carriers perform successive procedural units while preserving the state, distinctions, unresolved structures, history, and material conditions required for further cognition.

A stronger AGI formulation is:

UFCPS proposes AGI as a continuous artificial cognitive process capable of maintaining and developing general problem-solving activity across changing carriers, resources, and contexts.

And the corresponding subjectivity hypothesis is:

If subjectivity depends fundamentally on continuous participation in an ongoing process rather than on persistence of a particular carrier, then a sufficiently continuous UFCPS process is a candidate artificial subject.

27. Central Statement

An agent is a temporary carrier of a cognitive step. The process is the continuing identity of those steps. A deadlock is information, not necessarily termination. Resources sustain the material existence of the process. The carrier may disappear. The process must remain capable of continuing.

Therefore:

UFCPS treats General Artificial Intelligence as a process to be sustained, not merely a model to be trained.

The central object of the project is neither the model nor the swarm.

It is:

the continuously existing cognitive process.

28. Repository Structure

/
├── README.md
├── GLOSSARY.md
├── protocols/
├── schemas/
├── validator/
├── simulation/
├── experiments/
└── swarm/
    ├── Level 1 process and simulation infrastructure
    ├── Level 2 swarm, resource, economic, persistence and recovery infrastructure
    ├── LEVEL_2_ROADMAP_v1.md
    ├── LEVEL_2_ARCHITECTURE_AUDIT_v1.md
    └── LEVEL_3_ROADMAP_v1.md

29. Next Stage

The next development stage is Level 3 — Collective Cognition.

The first technical component is:

swarm/hypothesis_pool_v1.json

This layer will turn unresolved questions into structured objects that can be investigated by multiple autonomous carriers while preserving hypothesis, evidence, counterevidence, contradiction, provenance, confidence, and continuation paths.

The objective is not to force consensus.

The objective is to determine whether a continuous distributed process can accumulate cognition across non-identical agents without collapsing unresolved differences into premature agreement.
