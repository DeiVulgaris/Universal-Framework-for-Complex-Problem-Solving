UFCPS Task Claim Protocol v1

Path: swarm/task_claim_protocol_v1.md

1. Purpose

The Task Claim Protocol defines how an autonomous agent may enter an unresolved UFCPS process after discovering a compatible Task Prospect.

The protocol separates:

TASK DISCOVERY
    !=
TASK CLAIM
    !=
TASK ACCEPTANCE
    !=
RESOURCE RESERVATION
    !=
ACTIVE EXECUTION

A claim is a process-participation request, not ownership of the question.

2. Core Principle

A claim gives an agent a temporary right to attempt continuation of a process; it does not transfer ownership of the process or question.

Therefore:

Question Identity != Claim Identity != Agent Identity

and:

Claim Failure != Process Termination

A question remains discoverable when a claim is rejected, released, expires, or the claiming carrier disappears.

3. Architectural Position

The claim layer is positioned between discovery and scheduling/execution:

UQL
 |
 v
TASK DISCOVERY
 |
 v
TASK PROSPECT
 |
 v
CLAIM
 |
 v
ACCEPTANCE
 |
 v
RESOURCE RESERVATION
 |
 v
ACTIVE EXECUTION
 |
 +----------+-----------+
 |          |           |
RESULT   DEADLOCK    RELEASE
 |          |           |
 +----------+-----------+
            |
            v
           UQL

Discovery exposes opportunity.

Claim expresses an agent's intention to participate.

Acceptance verifies that the claim is admissible under current process conditions.

Resource reservation binds currently available resources without changing question identity.

Execution creates the next procedural state.

4. Claim Object

A claim should minimally contain:

claim_id
question_id
agent_id
prospect_id
created_at
expires_at
status
requested_capabilities
requested_resources
method_intent
parent_claim_id
provenance

Optional fields may include:

estimated_compute
estimated_duration
requested_resource_window
preferred_execution_mode
agent_confidence
agent_notes

The claim should reference the Task Prospect rather than silently copying the entire authoritative question state.

UQL remains authoritative for the question and its historical investigation state.

5. Claim States

Canonical lifecycle:

DISCOVERED
    |
CLAIM_REQUESTED
    |
CLAIMED
    |
ACCEPTED
    |
RESOURCE_RESERVED
    |
ACTIVE
    |
+-------------+-------------+-------------+
|             |             |             |
COMPLETED   DEADLOCK     RELEASED     EXPIRED

Additional rejection state:

CLAIM_REQUESTED -> REJECTED

and recovery path:

ACTIVE
  |
agent/resource loss
  v
RELEASED
  |
  v
DISCOVERED

A released or expired claim does not close the underlying question.

6. Discovery Does Not Imply Claim

A Task Prospect may be visible to many agents.

Q
 |
 +--> Prospect_A --> Agent_A
 |
 +--> Prospect_B --> Agent_B
 |
 +--> Prospect_C --> Agent_C

No agent is considered a participant merely because it can discover the prospect.

An agent must explicitly create a claim.

This prevents the discovery mechanism from becoming an implicit assignment mechanism.

7. Claim Admission

A claim may be accepted only when its structural requirements are satisfied.

Minimum checks:

question_id exists and refers to an active or recoverable question;

agent_id is known or otherwise verifiable;

the claim references a valid prospect;

requested capabilities are compatible with the prospect;

no terminal question state forbids further work;

claim has not expired before admission;

required provenance fields are present;

any required resource request is structurally valid.

Claim admission does not establish scientific correctness.

It establishes only that the participation request is structurally admissible.

8. Concurrent Claims

Multiple agents may claim the same question.

Q
 |
 +-- Claim_A
 |
 +-- Claim_B
 |
 +-- Claim_C

The system must not silently delete competing claims.

Possible policy outcomes include:

ACCEPT_ALL_AS_PARALLEL
ACCEPT_ONE_AND_QUEUE_OTHERS
REJECT_WITH_REASON
DEFER

The selection policy is an operational policy, not part of question identity.

Parallel claims are especially appropriate when independent methods may produce complementary evidence.

9. No Ownership Semantics

The following implication is prohibited:

Claimed(Q, Agent_A)
=>
Owned(Q, Agent_A)

A claim may temporarily control one execution path, but the question itself remains part of the distributed UQL frontier.

Other agents may:

submit independent claims;

observe the process where policy permits;

propose alternative methods;

continue another branch;

claim a successor state after release or completion.

10. Claim Expiration

Claims should be time-bounded when execution requires temporary exclusivity.

created_at < expires_at

An expired claim becomes:

EXPIRED

and may release the associated process opportunity back to discovery.

Expiration is not failure of the question.

It is failure of the current participation reservation.

11. Voluntary Release

An agent may release its claim when:

it determines that the method is unsuitable;

required resources become unavailable;

it cannot continue within the permitted budget;

another agent has a better continuation path;

the agent chooses to defer participation.

Release must preserve continuation-relevant state in UQL.

Conceptually:

ACTIVE
  |
RELEASE
  |
PERSIST STATE
  |
REDISCOVER

12. Agent Failure

Agent disappearance must not terminate the question.

Required recovery path:

Agent Failure
      |
      v
Detect Expired / Invalid Claim
      |
      v
Preserve Last Valid State
      |
      v
Rediscover Question
      |
      v
New Claim

Any locally completed verified resource contribution remains attributable under its existing accounting record.

Unverified work does not become verified merely because a claim existed.

13. Resource Reservation

Acceptance of a claim does not automatically imply resource reservation.

ACCEPTED
   |
   v
RESOURCE MATCH
   |
   +--> available -> RESERVED
   |
   +--> unavailable -> AWAITING_RESOURCES

The process may remain active in a waiting state without being terminated.

Resource substitution is valid when the required functional capability and verification conditions remain satisfied.

Therefore:

Resource_A != Resource_B

may coexist with:

Continuation_A == Continuation_B

when substitution is valid.

14. Claim Handoff

A claim may be transferred when the current agent cannot continue but preserved state remains valid.

Canonical pattern:

Claim_A
   |
RELEASE / HANDOFF
   |
Claim_B
   |
P_n -> P_n+1

The new claim must reference the parent claim:

parent_claim_id = Claim_A

This creates provenance without making the new agent the owner of the question.

15. Deadlock Interaction

A claim may terminate in a structured Deadlock.

ACTIVE
  |
DEADLOCK
  |
STRUCTURED DEADLOCK OBJECT
  |
UQL UPDATE
  |
NEW PROSPECT
  |
NEW CLAIM

A deadlock must preserve:

current state;

active constraints;

boundary;

unresolved difference;

attempted operations;

evidence references;

substitution guidance where applicable.

The Deadlock therefore modifies the opportunity surface of the question instead of closing it.

16. Economic Separation

Claiming a task is not itself a billable compute contribution.

CLAIM
    !=
COMPUTE COMPENSATION

Compensation is based on verified contribution according to the existing economic architecture.

Therefore:

Accepted Claim + No Verified Compute
    -> No Verified Compute Reward

Likewise:

Verified Compute
    -> Compensation may be calculated

regardless of whether the research question is ultimately resolved, provided all verification and economic constraints are satisfied.

17. Scheduler Relationship

The scheduler may use accepted claims as execution inputs, but a claim should not be silently created by scheduler assignment.

Preferred sequence:

Agent discovers prospect
        |
        v
Agent submits claim
        |
        v
Claim admission
        |
        v
Scheduler optimizes resources
        |
        v
Execution

A system may provide optional auto-claim behavior as an operational convenience, but such behavior must be explicitly represented rather than hidden inside scheduling semantics.

18. Multiple Claims and Branching

When parallel claims are accepted, they should produce explicit branch identity.

Q
 |
 +-- Claim_A -> P_A
 |
 +-- Claim_B -> P_B
 |
 +-- Claim_C -> P_C

Each branch preserves its own provenance.

If branches later produce compatible information, they may converge into a new procedural state.

If they conflict, the contradiction becomes continuation-relevant information.

19. Claim Validation Invariants

A conforming implementation should enforce:

Discovery != Claim
Claim != Ownership
Claim != Execution
Claim != Payment
Claim Failure != Question Termination
Agent Failure != Question Termination
Resource Failure != Question Termination
Expired Claim != Question Termination
Rejected Claim != Question Termination

And:

Every accepted claim references a valid question.
Every active claim has identifiable provenance.
Every resource reservation is independently represented.
Every verified payment references verified contribution.

20. Minimum Functional Requirements

A conforming implementation should support:

create a claim from a Task Prospect;

validate the claim structurally;

accept or reject the claim with reason;

represent competing claims;

expire claims deterministically;

release claims voluntarily;

recover after agent loss;

bind accepted claims to resources separately;

preserve claim provenance;

hand off continuation to another agent;

distinguish claim status from question status;

integrate accepted claims with scheduling and execution.

21. Canonical Process

The complete transition is:

UNRESOLVED QUESTION
        |
        v
TASK PROSPECT
        |
        v
AGENT DISCOVERY
        |
        v
CLAIM REQUESTED
        |
        v
CLAIM ACCEPTED
        |
        v
RESOURCE RESERVATION
        |
        v
ACTIVE EXECUTION
        |
   +----+-----+------+
   |          |      |
 RESULT    DEADLOCK RELEASE
   |          |      |
   +----+-----+------+
        |
        v
UQL FRONTIER UPDATE
        |
        v
NEXT DISCOVERY CYCLE

The core process identity therefore survives replacement of both agent and resource carriers.

22. Relationship to Existing UFCPS Layers

Level 1

Provides:

process continuity;

procedural states;

delegation;

branching;

composition;

deadlock preservation.

Level 2

Adds:

UQL;

Task Prospect;

Agent Swarm;

Resource Swarm;

Scheduler;

Claim Protocol;

Compute Economy.

The Task Claim Protocol is the explicit participation boundary between opportunity discovery and process execution.

23. Status

Version: v1

Status: architectural protocol specification

The protocol defines semantics and minimum requirements. Executable claim validation, lease handling, concurrency policy, and distributed consensus require implementation and empirical testing.
