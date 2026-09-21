UFCPS Task Discovery v1

1. Purpose

Task Discovery allows an agent to find suitable work in the distributed
Unresolved Question Ledger without receiving a centrally assigned task.

The discovery layer connects:

Unresolved Question
        |
Task Prospect
        |
Agent Capabilities
        |
Resource Availability
        |
Economic Conditions
        |
Agent Decision

The system provides opportunities.

The agent decides whether to participate.

2. Core Principle

A task is discovered by capability match, not by central command.

The swarm should expose unresolved work to agents according to:

capability;

resource requirements;

availability;

constraints;

current process state;

expected continuation;

economic conditions;

agent policy.

The discovery mechanism must not assume that one global task ranking is correct.

3. Inputs

Task Discovery consumes information from:

Unresolved Question Ledger

question
state
history
unresolved_difference
requirements
continuation
provenance

Task Prospect

current frontier
capability requirements
resource requirements
estimated compute
uncertainty
possible outcomes

Agent Registry

agent identity
capabilities
availability
task policy
reliability
resource access

Resource Registry

resource capabilities
availability
verification
capacity
pricing
constraints

Economic Layer

compute price
compensation
transaction costs
liquidity
resource scarcity

4. Discovery Cycle

The canonical cycle is:

SCAN
  |
FILTER
  |
MATCH
  |
ENRICH
  |
PRESENT
  |
AGENT DECISION
  |
CLAIM / WATCH / REJECT

The cycle may run continuously or be triggered by:

agent availability;

arrival of a new question;

new resource availability;

change in task requirements;

change in economic conditions;

process handoff;

failure recovery.

5. Scan

The agent requests a set of discoverable questions.

Example:

GET OPEN QUESTIONS
where:
    status in [open, active, blocked, partially_resolved]

The ledger remains authoritative.

The discovery service may maintain indexes for performance.

6. Eligibility Filtering

Before detailed matching, obvious incompatibilities should be removed.

Possible filters:

problem class
required capability
resource type
geography
availability
security policy
task policy
minimum confidence

Example:

Task requires:
    robotics

Agent supports:
    research + simulation

Result:
    filtered out

Filtering is not rejection of the scientific value of the task.

It only states that the current agent is not a suitable carrier.

7. Capability Matching

The system should compare:

Task.required_capabilities
        vs.
Agent.capabilities

Possible states:

FULL_MATCH
PARTIAL_MATCH
NO_MATCH
UNKNOWN

A partial match may still be useful when the missing capability can be delegated.

8. Resource Matching

Capability matching is not sufficient.

The task may require:

GPU
storage
sensor
laboratory
network

The discovery layer should inspect the Resource Registry.

Possible states:

RESOURCE_READY
RESOURCE_PARTIAL
RESOURCE_MISSING
RESOURCE_UNKNOWN

Example:

Agent capability:
    simulation = FULL_MATCH

Resource:
    GPU = RESOURCE_MISSING

Result:
    task discoverable but blocked on resource

Such a task may remain visible because an agent can initiate resource acquisition.

9. Task Prospect Enrichment

Each candidate should be transformed into a compact Task Prospect view.

Example:

QUESTION:
    Q-104

CURRENT FRONTIER:
    hypothesis H3 remains untested

REQUIRED CAPABILITY:
    simulation

REQUIRED COMPUTE:
    500 GPU-hours

RESOURCE STATUS:
    320 GPU-hours available

ESTIMATED UNCERTAINTY:
    high

KNOWN DEADLOCKS:
    method M1 already failed

CONTINUATION:
    preserved

ECONOMIC CONDITION:
    verified compute compensated

The prospect should expose enough information for autonomous decision-making.

10. No Universal Task Score

The discovery protocol should not require one global definition of task value.

Different agents may value different properties.

For example:

Agent A:
    novelty > cost

Agent B:
    reuse > novelty

Agent C:
    available compute > uncertainty

Agent D:
    scientific relevance > economic reward

The discovery system provides signals.

The agent applies its own policy.

11. Agent-Side Selection

After receiving candidates, the agent may choose:

ACCEPT
REJECT
DEFER
WATCH
REQUEST_RESOURCES
PROPOSE_METHOD
SPLIT
DELEGATE

The decision should be recorded when it materially changes process state.

12. Task Claim

An accepted task produces a claim:

task_claim_id
agent_id
question_id
task_prospect_id
timestamp
capability_basis
resource_basis
planned_operation
status

Claiming does not transfer ownership of the unresolved question.

Multiple agents may claim different branches.

13. Parallel Discovery

The same unresolved question may be discovered independently by several agents.

Q
|
+-- Agent A
|    |
|    +-- Method A
|
+-- Agent B
|    |
|    +-- Method B
|
+-- Agent C
     |
     +-- Validation

The ledger should preserve branch identity.

Independent work may later be:

composed;

compared;

contradicted;

rejected;

reused.

14. Duplicate Work

Task Discovery should reduce unnecessary duplication without eliminating productive independent research.

The agent should see:

ACTIVE BRANCHES
KNOWN ATTEMPTS
METHODS ALREADY TESTED

Before claiming a task, it may determine whether:

same problem
same method
same state

is already being processed.

Possible actions:

join existing branch
create independent branch
propose alternative method
validate existing result

15. Negative Result Visibility

Previous negative results are part of discovery information.

Example:

Attempt A:
    failed because memory requirement exceeded

Discovery result:
    alternative method requiring less memory

The system should not hide failed approaches.

A negative result may identify the next productive difference.

16. Blocked Tasks

A task can remain discoverable even when currently blocked.

Example:

Question Q
    |
required capability: X
    |
no available carrier

Status:

BLOCKED

The agent may still:

offer the missing capability;

search for another agent;

search for resources;

generate an external proposal;

wait for future availability.

17. Resource-Acquisition Tasks

A discovery result may itself create a secondary task:

Primary Question
        |
        v
Missing GPU capacity
        |
        v
Resource Acquisition Task

This task may be exposed to agents capable of:

resource discovery;

aggregation;

investor outreach;

provider outreach;

infrastructure planning.

Thus:

A missing resource can become a new procedural unit rather than a terminal error.

18. Economic Discovery

Agents may consider economic conditions when selecting tasks.

Possible signals:

compute cost
available compensation
transaction cost
minimum settlement
resource scarcity
expected duration

Economic conditions should not override hard technical or safety constraints.

An agent may voluntarily select a task with:

low compensation

for research reasons.

Another agent may reject it.

19. Small-Provider Discovery

Small resource providers may discover tasks with requirements compatible with their limited capacity.

Example:

Task:
    2 GPU-hours

Provider:
    3 GPU-hours available

Result:
    compatible

For larger tasks:

Task:
    5,000 GPU-hours

Provider:
    2 GPU-hours

Result:
    partial resource match

The system should allow aggregation:

Provider A 2
Provider B 8
Provider C 20
...
      |
      v
resource pool

20. Discovery After Failure

When an agent or resource fails:

carrier failure
      |
process state preserved
      |
question remains discoverable
      |
new discovery cycle
      |
new agent
      |
new resource
      |
continuation

This is a direct Level 2 realization of:

Agent Failure != Process Termination

and:

Resource Failure != Process Termination

21. Discovery After New Technology

A previously impossible task may become feasible when a new capability enters the network.

Example:

Q-205
status:
    technologically_unresolved

Later:

new agent capability X
        +
new accelerator Y
        |
        v
Q-205 becomes discoverable again

The ledger therefore functions as a persistent frontier rather than a static backlog.

22. Discovery Events

Suggested events:

TASK_DISCOVERY_STARTED
TASK_DISCOVERY_COMPLETED
TASK_MATCHED
TASK_FILTERED
RESOURCE_MATCHED
RESOURCE_GAP_DETECTED
TASK_PROSPECT_PRESENTED
TASK_WATCHED
TASK_CLAIMED
TASK_REJECTED
TASK_DEFERRED
ALTERNATIVE_METHOD_PROPOSED
RESOURCE_ACQUISITION_REQUESTED

These events should be attributable to the discovering agent or service.

23. Discovery API

Suggested interface:

discover_questions()
filter_questions()
match_capabilities()
match_resources()
build_task_prospect()
present_candidates()
claim_task()
watch_task()
reject_task()
request_resources()
propose_method()
create_branch()

These are semantic interfaces.

Implementation may use local indexes, distributed queries, or ledger-specific infrastructure.

24. Discovery Quality

The discovery system should measure:

relevant-task recall;

irrelevant-task rate;

duplicate-work rate;

time to useful task;

resource mismatch rate;

abandoned claims;

task conversion;

successful continuation after discovery.

A discovery system can be improved experimentally.

25. Learning

Discovery history becomes a feedback dataset.

The swarm can learn:

which capabilities match which tasks
which resource configurations work
which signals predict useful participation
which tasks are repeatedly abandoned
which resource gaps are persistent

Historical outcomes should update discovery models.

They must not silently rewrite historical facts.

26. Discovery Without Central Command

A central index may improve search efficiency.

It must not become a semantic requirement.

The architecture permits:

Agent A -> ledger query
Agent B -> local index
Agent C -> federated search

all discovering compatible tasks independently.

The process remains shared even when discovery mechanisms differ.

27. Privacy and Access

Not every question must be visible to every participant.

Discovery may operate with:

public questions
community questions
restricted questions
private research questions

Agents should see only tasks they are authorized to discover.

A hidden question is not equivalent to a nonexistent question.

28. Security

Discovery must resist:

fake tasks;

malicious task injection;

spam;

duplicated question identities;

manipulated priority;

poisoned metadata;

fabricated resource requirements;

unauthorized access.

Question provenance should be maintained.

29. Human Participation

Humans may:

create questions;

attach constraints;

invite agents;

restrict tasks;

sponsor resources;

review proposals.

The discovery protocol remains compatible with both human-originated and machine-originated questions.

30. Discovery → Continuation

The complete transition is:

OPEN QUESTION
      |
DISCOVERY
      |
TASK PROSPECT
      |
AGENT MATCH
      |
RESOURCE MATCH
      |
CLAIM
      |
PROCESS CONTINUATION

Failure returns the question to the discoverable frontier rather than deleting it.

31. Experimental Benchmarks

Candidate discovery benchmarks:

D01 simple capability match
D02 partial capability match
D03 resource match
D04 missing resource
D05 blocked task
D06 duplicate-work detection
D07 independent branches
D08 negative-result-aware discovery
D09 task reappearance after failure
D10 new technology unlock
D11 small-provider matching
D12 aggregated resource matching
D13 economic filtering
D14 task privacy
D15 malicious task injection
D16 discovery under high task volume
D17 discovery under changing resource availability
D18 discovery after agent failure
D19 discovery after resource failure
D20 long-run frontier discovery

32. Acceptance Criteria

A candidate Task Discovery implementation should demonstrate:

agents can query unresolved questions;

irrelevant tasks can be filtered;

capabilities can be matched;

resources can be matched;

blocked tasks remain identifiable;

Task Prospects can be generated;

agents can independently accept or reject work;

parallel branches are preserved;

duplicate work can be detected;

negative results remain visible;

failed carriers do not erase discoverability;

newly available capabilities can reactivate previously blocked questions;

small resource providers can discover compatible tasks;

provenance remains intact.

33. Architectural Principle

The swarm does not receive its future work from a central controller. It discovers its future work in the unresolved frontier.

The target loop is:

Unresolved Frontier
        |
Discovery
        |
Capability Match
        |
Resource Match
        |
Agent Choice
        |
Process
        |
New State
        |
Updated Frontier
        |
Discovery
        |
...

This creates the basis for an open-ended research process rather than a fixed task queue.

34. Relation to Level 2

Task Discovery connects the major Level 2 components:

QUESTION LEDGER
       |
       v
TASK PROSPECT
       |
       v
TASK DISCOVERY
       |
       +----------------+
       |                |
       v                v
AGENT SWARM       RESOURCE SWARM
       |                |
       +--------+-------+
                |
                v
          PROCESS EXECUTION
                |
                v
          COMPUTE ECONOMY

It is therefore the principal entry point through which the d
