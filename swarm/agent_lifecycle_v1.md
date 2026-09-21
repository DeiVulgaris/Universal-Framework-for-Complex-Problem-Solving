UFCPS Agent Lifecycle v1

1. Purpose

This protocol defines the lifecycle of an agent participating in UFCPS Level 2.

An agent is treated as a temporary carrier of capabilities within a continuous distributed process.

The lifecycle must therefore support:

registration;

capability declaration;

verification;

availability;

task discovery;

task participation;

delegation;

handoff;

temporary unavailability;

failure;

release;

reactivation;

retirement.

2. Core Principle

An agent is a carrier of capability, not the owner of process continuity.

Therefore:

Agent A
   |
   +-- process state
   |
   +-- capability
   |
   +-- task participation

does not imply:

Agent A = Process

A process may continue after the agent disappears.

3. Lifecycle States

The canonical lifecycle is:

DISCOVERED
    |
REGISTERED
    |
VERIFICATION_PENDING
    |
VERIFIED
    |
AVAILABLE
    |
BUSY
    |
+---+-------------------+
|                       |
RELEASED              HANDOFF
|                       |
v                       v
AVAILABLE <-------- CONTINUATION
    |
DEGRADED
    |
FAILED
    |
RECOVERY
    |
AVAILABLE

Additional terminal state:

RETIRED

4. State Definitions

DISCOVERED

The network has learned that an agent may exist.

No task should depend on the agent before registration and verification requirements are satisfied.

REGISTERED

The agent has a registry identity and declared capabilities.

VERIFICATION_PENDING

The declared identity or capabilities require verification.

VERIFIED

Required identity/capability checks have passed for the declared scope.

AVAILABLE

The agent can accept new process work.

BUSY

The agent is actively carrying one or more procedural units.

DEGRADED

The agent remains reachable but one or more declared capabilities are degraded.

HANDOFF

The agent is transferring process state to another carrier.

FAILED

The agent cannot continue carrying its current work.

RECOVERY

The agent is returning to operational state.

RELEASED

The agent has voluntarily or procedurally stopped carrying a process and has returned its resources/state references to the network.

RETIRED

The agent permanently leaves the network.

5. Registration

Registration should create:

agent_id
identity
agent_type
capabilities
task_policy
resource_access
availability
provenance

The registry must preserve historical versions of capability declarations.

An update to capability should not silently rewrite previous claims.

6. Identity

An agent may have:

cryptographic identity;

provider identity;

model family;

implementation version.

Identity is used for:

attribution;

authentication;

provenance;

accountability.

Identity does not determine process continuity.

7. Capability Declaration

An agent should declare capabilities rather than merely a generic label such as:

"AI agent"

Example:

capability:
    hypothesis_analysis

category:
    research

confidence:
    0.90

A capability declaration may include evidence.

8. Capability Verification

Verification may use:

benchmark tasks;

challenge tasks;

historical performance;

peer validation;

signed attestations;

controlled experiments.

Verification should be contextual.

An agent may be verified for:

simulation

without being verified for:

physical_control

9. Availability

The agent should expose availability where practical.

Possible states:

available now
scheduled availability
busy
degraded
offline

Availability is not a guarantee that a task will succeed.

It is an operational signal for scheduling.

10. Task Discovery

An available agent may query the Task Prospect layer.

Agent capabilities
        |
        v
Question discovery
        |
        v
Task Prospect
        |
        v
Agent decision

The agent may:

accept
reject
defer
watch
request resources
propose a method
split the task

11. Task Claim

When an agent accepts a task, the system should create a task participation record.

Possible fields:

participation_id
agent_id
question_id
task_prospect_id
process_id
claimed_at
expected_capabilities
resource_requirements
status

Claiming a task does not transfer ownership of the underlying unresolved question.

Other agents may continue through parallel branches unless the process explicitly prevents that.

12. Process Activation

When a task is activated:

AVAILABLE
    |
task accepted
    |
BUSY

The agent receives or reconstructs the required procedural state.

The agent should not depend on private memory when the state is available in the distributed process memory.

13. State Loading

An agent may load:

question
context
current procedural state
prior attempts
negative results
contradictions
resource requirements
continuation conditions

This allows a new agent to continue work without reproducing the complete history from scratch.

14. Execution

While active, the agent may:

reason;

call tools;

request resources;

perform experiments;

create branches;

validate results;

delegate subtasks;

update process state.

Every material process transition should remain attributable.

15. Delegation

An agent may delegate part of its work.

Agent A
   |
   +---- subtask 1 -> Agent B
   |
   +---- subtask 2 -> Agent C

Delegation must preserve:

parent process;

child process relationship;

required state;

evidence;

provenance.

A delegated subtask may become an independent continuation branch.

16. Handoff

Handoff is the controlled transfer of process carrying capacity.

Agent A
   |
   v
handoff request
   |
state fixed
   |
state persisted
   |
Agent B selected
   |
state loaded
   |
validated
   |
continue

The original agent may then release the process.

17. Handoff Conditions

Handoff may be initiated because of:

normal completion of a procedural unit;

task specialization change;

resource mismatch;

time limit;

maintenance;

expected disconnection;

degradation;

cost change;

policy boundary.

Handoff should not require the original agent to remain permanently available.

18. Failure

An agent can fail during any stage.

Examples:

reasoning interruption
communication loss
software failure
hardware failure
credential failure
resource exhaustion
unexpected termination

The system must preserve the latest valid process state.

Failure of the carrier does not imply failure of the process.

19. Failure Recovery

Recovery sequence:

Agent A fails
     |
process state remains
     |
Task Prospect refreshed
     |
candidate agents discovered
     |
Agent B selected
     |
state reconstructed
     |
continuation

The new agent may be a different implementation, organization, or physical location.

20. Degradation

An agent may lose part of its capability without disappearing.

Example:

full capability
     |
degradation
     |
reduced capability

The scheduler may:

continue with reduced scope;

delegate missing functions;

request another resource;

initiate handoff.

A degraded state must be explicit.

21. Resource Access

An agent may have access to resources it does not own.

Examples:

owned GPU
leased GPU
shared storage
remote laboratory
cloud compute

Resource ownership and agent identity must remain separate.

22. Economic Participation

An agent may participate in:

compute-consuming processes;

resource provisioning;

validation;

research;

coordination.

The agent lifecycle must therefore expose the economic role relevant to each process.

Compute compensation belongs to the verified resource contribution, not automatically to the agent itself.

An agent controlling someone else's GPU does not thereby become the economic owner of that GPU.

23. Reputation

Performance history may be accumulated over the lifecycle.

Possible evidence:

successful task transitions
validation results
handoff quality
failure recovery
resource usage accuracy
communication reliability

Reputation should remain evidence-based and contextual.

A single failure should not automatically erase all historical information.

24. Release

An agent releases a process when:

its procedural unit is complete;

handoff is complete;

the task is paused;

it loses required capability;

maintenance begins;

it chooses to stop participation.

Release should preserve the process state for continuation.

25. Retirement

Retirement removes an agent from future scheduling.

Before retirement, the system should attempt:

active process inventory
        |
handoff / checkpoint
        |
resource release
        |
final state update
        |
RETIRED

Historical provenance remains available.

26. Re-entry

A retired or previously offline agent may register again.

Re-entry should not require rebuilding its entire historical identity.

The network may retain:

previous identity
capability history
reputation history
failure history
verification history

Current capability should still be re-verified where appropriate.

27. Multi-Agent Continuity

Several agents may carry one process simultaneously.

                 Process P
                    |
          +---------+---------+
          |         |         |
       Agent A   Agent B   Agent C
       branch     branch     validation
          |         |         |
          +---------+---------+
                    |
                 Compose
                    |
                    v
                Process P'

There is no requirement for one permanent central agent.

28. Parallel Participation

An unresolved question may remain open while multiple agents investigate it.

Each branch should preserve:

agent identity
method
state
evidence
result
uncertainty

Branches may later:

continue;

compose;

contradict;

terminate;

become reusable knowledge.

29. Agent Autonomy

The lifecycle supports increasing levels of autonomy.

Level A

Agent responds to assigned tasks.

Level B

Agent discovers tasks.

Level C

Agent requests missing resources.

Level D

Agent creates proposals for researchers/providers/investors.

Level E

Agent organizes multi-agent and multi-resource work.

Level F

Agent proposes changes to the infrastructure supporting the swarm.

Autonomy does not remove governance or authorization boundaries.

30. Human Interaction

Humans may enter the lifecycle as:

task originators;

researchers;

validators;

resource providers;

investors;

reviewers;

operators.

Human interaction should be represented as explicit process events when it materially affects continuation.

31. Interface Events

A minimal implementation should support events such as:

AGENT_REGISTERED
CAPABILITY_DECLARED
CAPABILITY_VERIFIED
AGENT_AVAILABLE
TASK_CLAIMED
TASK_STARTED
HANDOFF_REQUESTED
HANDOFF_ACCEPTED
STATE_TRANSFERRED
AGENT_DEGRADED
AGENT_FAILED
PROCESS_RELEASED
AGENT_RETIRED
AGENT_REACTIVATED

These events should reference the affected process where applicable.

32. Required Interfaces

Suggested API:

register()
verify()
declare_capability()
update_capability()
set_availability()
discover_tasks()
claim_task()
start_task()
delegate()
request_handoff()
accept_handoff()
transfer_state()
release_task()
report_failure()
recover()
retire()
reactivate()

These interfaces are implementation proposals.

33. Process Continuity Invariant

The key invariant remains:

Agent Failure != Process Termination

A second Level 2 principle is:

Agent Identity != Process Identity

The process continues when an alternative carrier can reconstruct and continue the required state.

34. Experimental Benchmarks

Candidate lifecycle benchmarks:

A01 registration
A02 capability declaration
A03 capability verification
A04 task discovery
A05 task claim
A06 task execution
A07 voluntary handoff
A08 involuntary handoff
A09 agent failure
A10 state reconstruction
A11 degraded capability
A12 parallel agents
A13 duplicate task participation
A14 agent retirement
A15 agent re-entry
A16 repeated handoff
A17 communication loss
A18 mixed agent types
A19 long-run carrier replacement
A20 process continuity after multi-agent failure

Each benchmark should measure:

state preservation;

transition validity;

recovery time;

unnecessary duplication;

resource impact;

process termination state.

35. Acceptance Criteria

A candidate lifecycle implementation should demonstrate:

an agent can register;

capabilities can be declared and verified;

tasks can be discovered;

tasks can be claimed;

procedural state can be loaded;

work can be executed;

state can be handed off;

agent failure can be recovered from;

degraded agents can be replaced;

agents can leave and re-enter the swarm;

process continuity survives carrier replacement;

historical provenance remains intact.

36. Architectural Principle

The swarm should be able to lose agents without losing the process they were carrying.

The intended lifecycle is therefore:

discover
   |
register
   |
verify
   |
participate
   |
handoff / fail / release
   |
state persists
   |
new carrier
   |
continue

The agent is temporary.

The process is c
