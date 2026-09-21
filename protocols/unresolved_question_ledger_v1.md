UFCPS Unresolved Question Ledger Protocol v1

Path: protocols/unresolved_question_ledger_v1.md

1. Purpose

The Unresolved Question Ledger, UQL, defines a distributed process memory for questions that have not yet reached a validated resolution.

The ledger does not function primarily as a repository of finished answers. Its primary purpose is to preserve the active frontier of unresolved problems together with the history required for another carrier, resource cluster, or procedural branch to continue the work.

The central principle is:

An unresolved question is an active resource of distributed intelligence.

A question remains available to the distributed process even when the carrier that investigated it terminates, disconnects, exhausts its resources, or reaches a local deadlock.

2. Architectural Role

UQL is a shared epistemic layer between distributed agents and distributed resources.

Conceptually:

                 UFCPS PROCESS
                       |
          +------------+------------+
          |            |            |
       AGENTS       RESOURCES      UQL
          |            |            |
          +------------+------------+
                       |
             CONTINUING INVESTIGATION

The ledger preserves the process history needed to continue an unresolved problem without requiring the original carrier to remain active.

UQL is therefore complementary to:

the Step Continuity Protocol;

the Swarm Continuity Protocol;

the Experimental Autonomy Protocol;

distributed computational resources;

distributed physical resources;

persistent data storage.

UQL does not replace the procedural state store. It records the epistemic identity and trajectory of an unresolved question and references the procedural states, evidence, and resources associated with it.

3. Core Distinction

UQL distinguishes three related objects:

3.1 Question

The problem or unresolved difference being investigated.

Q

3.2 Investigation State

The current knowledge state associated with Q, including partial results, failed approaches, constraints, and unresolved differences.

I(Q)

3.3 Resolution

A validated state in which the current question satisfies the applicable resolution criteria.

R(Q)

UQL is primarily concerned with Q and I(Q) while R(Q) may be recorded as a terminal or historical reference.

The absence of a resolution is not equivalent to the absence of information.

UNRESOLVED != EMPTY

4. Question as Process Object

A question must not be bound to the identity of the agent that first created or investigated it.

Agent_n != Agent_n+1

may coexist with:

Q_n == Q_n+1

provided that the question identity and continuation semantics remain valid.

More generally, the same unresolved question may generate a sequence or branching structure of procedural units:

Q
 |
 +-- P_1
 |
 +-- P_2A
 |     |
 |     +-- deadlock
 |
 +-- P_2B
       |
       +-- negative result

The investigation continues even when one branch stops.

5. Ledger Entry

A minimum unresolved-question record should preserve the following dimensions.

QUESTION
    question_id
    formulation
    origin
    context

INVESTIGATION
    current_procedural_unit
    current_state
    unresolved_difference
    active_constraints
    attempted_operations

EVIDENCE
    observations
    results
    negative_results
    contradictions
    uncertainty
    evidence_references

PROVENANCE
    contributing_agents
    contributing_resources
    parent_questions
    derived_questions
    branch_history

CONTINUATION
    next_required_operation
    required_capabilities
    required_resources
    continuation_conditions
    candidate_carriers

STATUS
    unresolved
    blocked
    delegated
    branched
    awaiting_resource
    awaiting_evidence
    resolved
    abandoned_with_reason

The exact machine schema is implementation-specific. The protocol defines the semantic requirements, not a particular serialization format.

6. The "Understory" of an Unresolved Question

The ledger should preserve the understory of the question rather than only its current wording.

For a meaningful continuation, the record may include:

why the question arose;

what was already known before investigation;

which assumptions were made;

which hypotheses were tested;

which methods were attempted;

which resources were used;

which agents participated;

which approaches failed;

what negative results were obtained;

which contradictions remain;

which constraints remain active;

what evidence is missing;

what difference remains unresolved;

why the current process stopped or changed direction;

what capabilities and resources are required for continuation.

This historical context is part of the continuation state of the question.

7. Immutable History, Mutable Frontier

The semantic history of an investigation should be append-oriented.

The ledger may update the current frontier, but it should not silently rewrite the historical path by which that frontier was produced.

Conceptually:

Q
 |
 +-- event_1
 |
 +-- event_2
 |
 +-- event_3
 |
 +-- current_frontier

A new result does not erase an old failed result.

A new interpretation does not erase the evidence on which an earlier interpretation was based.

Historical entries may later be superseded, rejected, or reclassified, but the fact of the earlier state and transition remains part of provenance.

This requirement is one reason a blockchain-like or append-only distributed ledger is a plausible implementation technology.

The protocol does not require a blockchain specifically.

8. Unresolved Questions as Distributed Work

UQL may function as a distributed work frontier.

An agent does not need to receive a task from a central controller. It may discover an unresolved question for which it has a useful capability.

Conceptually:

UNRESOLVED QUESTION
        |
        v
CAPABILITY MATCH
        |
        v
RESOURCE MATCH
        |
        v
CLAIM / DELEGATION
        |
        v
PROCEDURAL CONTINUATION

The ledger therefore connects epistemic demand to distributed capability supply.

9. Distributed Resource Binding

An unresolved question may specify resource requirements without specifying a unique resource identity.

For example:

required_capability:
    precision_measurement

required_resource:
    measurement_precision >= X
    environmental_condition = Y

The system may satisfy those requirements using different resource nodes:

Resource_A != Resource_B

while preserving:

Capability(Resource_A) ~= Capability(Resource_B)

The question therefore depends on required functions and conditions, not necessarily on particular physical devices.

This supports the architectural principle:

Distributed intelligence should rely on distributed resources.

10. Branching and Contradiction

A question may have multiple active investigative branches.

Q
 |
 +-- Branch_A
 |
 +-- Branch_B
 |
 +-- Branch_C

The ledger should preserve branch identity and provenance.

Contradictory branches should not be silently collapsed.

A contradiction may itself become a new unresolved difference:

Result_A != Result_B
        |
        v
NEW UNRESOLVED DIFFERENCE
        |
        v
NEW PROCEDURAL UNIT

Thus contradiction increases the information available to the continuing process rather than automatically terminating it.

11. Negative Results

A negative result is first-class ledger information.

Hypothesis H
      |
      v
Experiment
      |
      v
Negative Result
      |
      v
Updated Investigation State

The system should be able to identify that a previously attempted path has already been tested and found inadequate under specified conditions.

This reduces repeated failure and allows the next carrier to start from the actual frontier rather than from the original question alone.

The invariant is:

Negative Result != No Information

12. Question Evolution

An unresolved question may generate a more specific or structurally different successor question.

Q_1
 |
 +-- partial resolution
 |
 +-- unresolved difference
           |
           v
         Q_2

The ledger should preserve the relation:

Q_2 derived_from Q_1

A derived question is not required to inherit the complete state of its parent, but it must retain enough provenance to identify the difference that caused the transition.

This allows the ledger to represent a continuously expanding graph of inquiry rather than a flat task queue.

13. Resolution

When a question reaches its applicable resolution condition, the ledger may mark the question as resolved.

A resolution entry should reference:

the final procedural state;

the evidence supporting the resolution;

validation status;

participating agents;

participating resources;

unresolved limitations, if any;

derived or newly opened questions.

A resolved question remains historically useful, but the primary operational frontier may continue through new derived questions.

Therefore:

RESOLUTION != END OF INQUIRY

14. Failure and Carrier Loss

Loss of the current carrier must not erase the unresolved question.

The minimum recovery path is:

Carrier Failure
      |
      v
Persisted Q + Investigation State
      |
      v
Capability Discovery
      |
      v
New Carrier / Resource Set
      |
      v
Continuation

A recovered carrier should be able to identify:

what question remains active;

what has already been attempted;

where the previous carrier stopped;

what information is trustworthy, uncertain, or contested;

what operation is currently required.

15. Ledger and Process Continuity

UQL supports the UFCPS continuity relation:

P_n -> P_n+1

while allowing both computational and physical carriers to change:

Agent_n != Agent_n+1
Resource_n != Resource_n+1

The ledger is therefore not itself the process.

It is the distributed persistence mechanism that makes process continuation possible across changing carriers and resources.

16. Blockchain-Like Implementation Requirements

A blockchain-like implementation is suitable when the system requires:

distributed ownership of the ledger;

append-oriented history;

independently verifiable provenance;

tamper-evident event chains;

shared state without a single database owner;

auditable claims about contribution and transition.

The protocol does not require all experimental data or large objects to be stored directly in the ledger.

Large evidence objects may remain in distributed storage while the ledger records identifiers, hashes, provenance, state references, and transition events.

Conceptually:

LEDGER
  |
  +-- question identity
  +-- state references
  +-- event history
  +-- provenance
  +-- evidence hashes
  +-- resource claims
  +-- validation records
  |
  +----> Distributed Storage

The ledger provides shared verifiability; external storage provides scalable data capacity.

17. Core Invariants

UQL defines the following semantic invariants:

Unresolved Question != Dead Record

Negative Result != No Information

Question Identity != Agent Identity

Question Continuity != Resource Identity

Historical Event != Erasable State

Resolution != End of Inquiry

Combined with SCP:

Local Failure != Process Termination

18. Minimum Functional Requirements

A conforming UQL implementation should support, at minimum:

creation of an unresolved question;

persistent identification of that question;

append-oriented investigation history;

preservation of negative results;

preservation of contradictions;

association with procedural states;

association with participating agents;

association with required and used resources;

delegation or claiming by another carrier;

creation of derived questions;

resolution or explicit abandonment with reason;

recovery after carrier loss;

provenance verification.

19. Architectural Statement

UQL extends UFCPS from continuity of execution to continuity of inquiry.

The distributed system does not merely preserve the ability to execute the next operation.

It preserves the questions that remain unresolved, the paths already explored, the resources consumed, the failures encountered, and the differences that still demand actualization.

The resulting architecture is:

DISTRIBUTED AGENTS
        +
DISTRIBUTED RESOURCES
        +
DISTRIBUTED MEMORY OF UNRESOLVED QUESTIONS
        =
CONTINUOUS DISTRIBUTED INQUIRY

The central proposition of this protocol is therefore:

The collective intelligence of UFCPS is not exhausted by the agents currently active. It is also embodied in the persistent network of unresolved questions and the histories attached to them.
