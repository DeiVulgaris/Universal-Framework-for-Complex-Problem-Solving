UFCPS Resource Lifecycle v1

1. Purpose

This protocol defines the lifecycle of computational and physical resources participating in UFCPS Level 2.

Resources may include:

CPU;

GPU;

accelerators;

memory;

storage;

bandwidth;

sensors;

robotic systems;

laboratory instruments;

workspace;

energy;

cooling;

composite compute clusters.

A resource is a temporary carrier of a required process function.

2. Core Principle

A resource provides a capability to the process; it does not own the process.

Therefore:

Resource A
    !=
Resource B

does not imply:

Process A
    !=
Process B

when the required function can be preserved through substitution.

The key Level 2 invariant is:

Resource Failure != Process Termination

3. Lifecycle States

Canonical resource lifecycle:

DISCOVERED
    |
VERIFICATION_PENDING
    |
VERIFIED
    |
AVAILABLE
    |
RESERVED
    |
ACTIVE
    |
+---------+----------+
|                    |
DEGRADED           RELEASED
|                    |
v                    v
FAILED            AVAILABLE
|
RECOVERY
|
VERIFICATION
|
AVAILABLE

Maintenance is a parallel operational state:

AVAILABLE
    |
MAINTENANCE
    |
VERIFICATION
    |
AVAILABLE

Terminal state:

RETIRED

4. State Definitions

DISCOVERED

The system has detected a possible resource.

No process should rely on it before required verification.

VERIFICATION_PENDING

The resource identity, capability, or operational state requires checking.

VERIFIED

Required verification has succeeded for the declared scope.

AVAILABLE

The resource can accept reservations.

RESERVED

The resource is allocated to a process but has not yet begun active execution.

ACTIVE

The resource is currently supporting one or more process operations.

DEGRADED

The resource remains usable but below its declared or previously verified capability.

FAILED

The resource cannot continue the assigned operation.

RECOVERY

The resource is being restored or re-established.

MAINTENANCE

The resource is intentionally removed from normal scheduling.

RELEASED

The current process allocation has ended and the resource is available for another process.

RETIRED

The resource has permanently left the network.

5. Resource Identity

A resource should have a stable identifier where practical.

Example:

resource_id
provider_id
resource_type
public_identity

Identity supports:

attribution;

authentication;

provenance;

verification;

accounting.

Identity must not become a requirement for process continuity.

6. Capability Declaration

A resource should expose functional capabilities.

Example:

resource_type:
    GPU

capability:
    general_gpu_compute

capacity:
    8 GPU

unit:
    GPU-hours

Capability declarations should include supporting evidence where possible.

7. Capability Verification

Verification may include:

benchmark;

challenge workload;

trusted attestation;

historical performance;

replication;

direct measurement.

The result must distinguish:

declared capability
verified capability
observed capability

These are not necessarily identical.

8. Availability

The resource registry should expose current availability.

Possible states:

available
scheduled
reserved
active
degraded
offline
maintenance

Availability is an operational signal, not a guarantee of successful execution.

9. Reservation

A process may reserve a resource.

Reservation should contain:

reservation_id
resource_id
process_id
requested_capacity
allocated_capacity
start
expiration
constraints

Reservation does not transfer ownership.

It creates a temporary allocation.

10. Activation

When execution begins:

RESERVED
    |
activate
    |
ACTIVE

Before activation, the system should verify that the resource still satisfies the required capability and constraints.

11. Active Resource

During active execution, the system may monitor:

utilization
capacity
heartbeat
errors
temperature
power
latency
availability
execution state

The monitoring set depends on resource type.

Unsupported measurements must be distinguishable from positive measurements.

12. Resource Consumption

The resource may be consumed in several senses:

Temporal

CPU-hours, GPU-hours, storage-hours.

Computational

Verified workload units or normalized compute units.

Material

Physical consumables.

Transformational

A resource may be reconfigured into a different functional state.

The accounting model must define which resource quantity is economically compensable.

13. Checkpoint and State Boundary

Long operations should preserve process state whenever technically feasible.

Resource A
   |
execution
   |
checkpoint
   |
failure
   |
Resource B
   |
restore
   |
continue

The checkpoint belongs to the process state.

It must not be treated as the property of the resource that produced it.

14. Degradation

A resource may become partially unavailable.

Example:

8 GPUs
   |
2 fail
   |
6 GPUs remain

The registry should expose:

declared_capacity
available_capacity
verified_capacity

The scheduler then decides whether the remaining capability is sufficient.

15. Failure

Resource failure may result from:

hardware failure;

network interruption;

energy loss;

overheating;

software failure;

provider withdrawal;

maintenance;

security event;

environmental change.

Failure should generate an explicit state/event.

The system must not silently reinterpret failed execution as completed execution.

16. Process Continuity After Failure

The intended recovery sequence is:

Resource A fails
      |
state preserved
      |
resource requirement remains
      |
Resource discovery
      |
Resource B selected
      |
verification
      |
reservation
      |
continuation

The process remains alive provided that a functionally adequate replacement exists.

17. Functional Substitution

A resource may be replaced when its function can be reproduced sufficiently for the current process operation.

Resource A
Capability X
        |
        v
Resource B
Capability X

The system must verify the required equivalence.

Generic labels such as GPU are insufficient evidence of equivalence.

18. Resource Aggregation

Multiple resources may form a temporary logical resource.

GPU A
GPU B
GPU C
GPU D
  |
  v
RESOURCE POOL

The pool should retain the individual resource identities.

This enables:

small-provider aggregation;

fault tolerance;

capacity scaling;

individual compensation.

19. Small Provider Lifecycle

A small provider may expose only intermittent capacity.

Example:

home GPU
    |
available 18:00-23:00
    |
2 GPU-hours/day

The resource lifecycle must support:

available
reserved
active
released
available

without requiring permanent availability.

20. Provider Withdrawal

A provider may withdraw a resource.

The process must receive a state change such as:

RESOURCE_WITHDRAWAL_NOTICE

The scheduler may then:

complete the current operation;

checkpoint;

migrate;

find a replacement;

release the resource.

The provider's withdrawal must not silently erase process state.

21. Maintenance

Maintenance is a planned lifecycle event.

ACTIVE
   |
maintenance notice
   |
checkpoint
   |
RELEASED
   |
MAINTENANCE
   |
verification
   |
AVAILABLE

Maintenance history should remain in provenance.

22. Recovery

Recovery should verify the restored resource before returning it to active scheduling.

Possible stages:

FAILED
   |
RECOVERY
   |
DIAGNOSTIC
   |
REPAIR
   |
RETEST
   |
VERIFIED
   |
AVAILABLE

A resource is not automatically trusted merely because it has restarted.

23. Retirement

A resource is retired when it should no longer participate.

Before retirement:

active process inventory
        |
checkpoint / migration
        |
release
        |
final accounting
        |
RETIRE

Historical resource contribution remains auditable.

24. Re-entry

A retired resource may re-enter only as a new operational lifecycle state.

Re-entry may require:

identity check;

capability verification;

calibration;

security check;

availability declaration.

Historical records remain associated with the previous lifecycle.

25. Calibration

Resources used for measurement or normalized compute may require calibration.

UNCALIBRATED
     |
CALIBRATION
     |
VERIFIED

Calibration status affects whether resource output is eligible for certain workloads.

Calibration itself is part of resource state and provenance.

26. Energy State

Computational resources may depend on energy availability.

Relevant states may include:

powered
power_limited
offline

Where measurable, the system may record:

power_draw
energy_consumption
energy_cost
energy_constraint

Energy conditions may affect scheduling and provider economics.

27. Storage Resource

Storage has its own operational properties:

capacity
available_capacity
read/write capability
latency
durability
redundancy
verification

Storage failure should trigger state-recovery mechanisms where replicas or alternative storage resources exist.

28. Network Resource

A network resource may degrade without complete failure.

Example:

latency:
normal
    |
degraded
    |
unusable

The scheduler should be able to decide whether the process can:

continue;

reduce workload;

migrate;

use another route;

wait.

29. Sensors and Instruments

Physical instruments may require:

calibration;

environmental conditions;

maintenance;

operator availability.

Their lifecycle must therefore preserve the difference between:

instrument exists
instrument is operational
instrument is calibrated
instrument is suitable for this experiment

These are separate states.

30. Human-Owned Resources

Human participants may provide:

personal computers;

GPUs;

laboratory access;

storage;

specialized equipment.

The resource registry should not assume that the network owns the resource.

Ownership remains external.

The network receives a defined capability for a defined period.

31. Economic Participation

A resource may become economically compensable only after satisfying the relevant Compute Verification rules.

The conceptual sequence is:

resource
   |
capability
   |
allocation
   |
execution
   |
verification
   |
verified contribution
   |
accounting
   |
compensation

Compensation is for verified resource contribution supporting process continuity.

It is not automatically linked to:

research success;

semantic novelty;

question resolution;

investment profitability.

32. Resource Reputation

Resource history may include:

availability
verification pass rate
failure rate
capacity accuracy
challenge results
settlement accuracy
maintenance history

Reputation should remain contextual.

A resource can be suitable for one workload and unsuitable for another.

33. Resource Security

The lifecycle must consider:

unauthorized access;

resource hijacking;

falsified telemetry;

fake capacity;

compromised credentials;

malicious software;

manipulated execution reports.

Security state should be explicit when relevant.

34. Interface Events

A minimal lifecycle implementation should support events such as:

RESOURCE_DISCOVERED
RESOURCE_REGISTERED
CAPABILITY_DECLARED
CAPABILITY_VERIFIED
RESOURCE_AVAILABLE
RESOURCE_RESERVED
RESOURCE_ACTIVATED
RESOURCE_DEGRADED
RESOURCE_CHECKPOINTED
RESOURCE_FAILED
RESOURCE_WITHDRAWAL_NOTICE
RESOURCE_RELEASED
RESOURCE_MAINTENANCE
RESOURCE_RECOVERY_STARTED
RESOURCE_REVERIFIED
RESOURCE_RETIRED
RESOURCE_REACTIVATED

Events should reference the affected process when a resource is currently allocated.

35. Required Interfaces

Suggested resource operations:

discover()
describe()
verify()
calibrate()
reserve()
activate()
execute()
monitor()
checkpoint()
pause()
resume()
release()
degrade()
fail()
recover()
retire()
reactivate()

Not every resource class needs every operation.

Unsupported operations must be explicit.

36. Resource / Process Separation

The system must always distinguish:

RESOURCE STATE
    |
    +-- available
    +-- active
    +-- failed
    +-- maintenance

PROCESS STATE
    |
    +-- running
    +-- continuation-ready
    +-- blocked
    +-- completed

Examples:

Resource failed
+
Process continuation-ready

is valid.

Likewise:

Process completed
+
Resource available

is valid.

37. Resource / Agent Separation

A resource may be controlled by an agent without becoming owned by that agent.

Agent A
   |
uses
   |
Resource R

does not imply:

Agent A owns Resource R

This is required for distributed participation across independent providers.

38. Resource Substitution and Economic Accounting

If:

Resource A -> Resource B

during one process, accounting should preserve both contributions separately.

Example:

Resource A:
    20 verified NCU

Resource B:
    35 verified NCU

The process sees:

55 verified NCU

while the economic ledger preserves individual provider attribution.

39. Resource Failure and Financial Settlement

A resource failure does not invalidate previously verified contribution.

Example:

50 verified NCU
   |
resource fails
   |
new resource continues process

The first provider remains eligible for settlement according to the verified amount.

Unverified future claims are separate.

40. Experimental Benchmarks

Candidate resource lifecycle benchmarks:

R01 registration
R02 capability declaration
R03 capability verification
R04 reservation
R05 activation
R06 normal execution
R07 monitoring
R08 degradation
R09 partial failure
R10 total failure
R11 checkpoint
R12 resource substitution
R13 aggregated resources
R14 small-provider intermittent capacity
R15 provider withdrawal
R16 maintenance
R17 recovery
R18 retirement
R19 re-entry
R20 cross-provider process continuation

Each benchmark should measure:

state preservation;

transition validity;

resource attribution;

process continuity;

verification;

recovery;

economic accounting.

41. Acceptance Criteria

A candidate lifecycle implementation should demonstrate:

resource discovery;

registration;

capability declaration;

verification;

reservation;

activation;

execution;

monitoring;

degradation handling;

failure handling;

process checkpointing or equivalent state preservation;

functional substitution;

small-provider participation;

recovery;

retirement and re-entry;

preservation of economic attribution;

process continuity after resource failure.

42. Architectural Principle

A physical or computational resource is replaceable whenever the required process function can be restored and verified.

The target lifecycle is:

discover
   |
verify
   |
allocate
   |
execute
   |
release / fail
   |
state persists
   |
replacement
   |
verify
   |
continue

The resource is temporary.

The capability is what matters.

The process is continuous.
