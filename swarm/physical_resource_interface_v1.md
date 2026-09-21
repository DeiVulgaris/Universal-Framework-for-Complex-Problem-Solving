UFCPS Physical Resource Interface v1

1. Purpose

The Physical Resource Interface connects UFCPS Level 2 with real computational and physical resources.

The interface may expose:

CPUs;

GPUs;

accelerators;

storage;

network capacity;

sensors;

robotic systems;

laboratory instruments;

physical workspaces;

energy and cooling services.

The interface does not make the physical resource part of the semantic identity of the process.

Its purpose is to expose a verified capability that can temporarily support a procedural unit.

2. Core Principle

The physical resource is a carrier of a process function, not the owner of the process.

Therefore:

Process
   |
required capability
   |
physical resource
   |
verified operation
   |
continuation state

A resource may disappear while the process remains alive.

Resource A
    |
failure
    |
state preserved
    |
Resource B
    |
continuation

This preserves the Level 1 invariant:

Local Failure != Process Termination

3. Interface Boundary

The interface separates UFCPS from device-specific implementation.

UFCPS
  |
  | abstract capability request
  v
Physical Resource Interface
  |
  +---- device adapter
  |
  +---- scheduler
  |
  +---- verification
  |
  v
Physical Resource

UFCPS should not need to know the vendor-specific details of every device.

The interface should expose stable semantic operations.

4. Resource Capability Contract

Every connected resource should expose:

resource_id
resource_type
capabilities
capacity
availability
constraints
verification_state
location_class
ownership_class
pricing
lifecycle_state

Example:

resource_id:
    GPU-NODE-104

resource_type:
    gpu

capability:
    distributed_compute

capacity:
    8 GPU

availability:
    available

verification:
    verified

lifecycle:
    active

The exact physical implementation remains below the interface boundary.

5. Capability Request

A process should request a capability rather than a specific device.

Example:

required capability:
    GPU compute

minimum:
    4 GPU-hours

constraints:
    memory >= 16 GB
    reliability >= threshold

The scheduler can then identify an appropriate physical resource.

This allows:

GPU A -> unavailable
        |
        v
GPU B -> selected

without changing the semantic identity of the process.

6. Resource Lifecycle

The interface should expose a common resource lifecycle:

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
DEGRADED
    |
FAILED
    |
MAINTENANCE
    |
RELEASED

A resource may return from maintenance to verification before becoming available again.

7. Reservation

Before an operation begins, the process may reserve a resource.

request
   |
capability match
   |
resource selection
   |
reservation
   |
execution

A reservation should include:

reservation_id
resource_id
process_id
requested_capacity
allocated_capacity
start
expiration
constraints

Reservation is not ownership.

It is temporary process allocation.

8. Activation

After successful reservation:

RESERVED
   |
activate
   |
ACTIVE

Activation should verify that the resource still satisfies the required capability.

A resource that changed state between reservation and activation must be re-evaluated.

9. Execution

The interface should expose an abstract execution operation:

execute(
    process_id,
    workload_id,
    resource_id,
    requested_quantity
)

The adapter translates this into a device-specific operation.

The interface should return at least:

execution_id
started_at
resource_id
process_id
workload_id
declared_quantity
status

Large execution outputs should not necessarily pass through the interface.

They may be stored in an external storage system with references recorded in process state.

10. Monitoring

Active resources should expose monitoring information such as:

heartbeat
availability
utilization
errors
temperature
power state
capacity remaining
execution state

Not every physical resource will expose every field.

The interface should distinguish:

unknown
not supported
unavailable
verified

rather than interpreting absent data as success.

11. Verification Hook

The interface must connect directly to Compute Verification.

Resource
    |
execution
    |
evidence
    |
verification
    |
verified compute

The resource adapter should make evidence available where possible:

execution_id
attestation
benchmark_ref
scheduler_record
checkpoint_ref
usage_record

The interface itself does not decide economic compensation.

12. Checkpointing

Long-running operations should support checkpoints whenever technically possible.

Process P
    |
checkpoint 1
    |
checkpoint 2
    |
resource failure
    |
load checkpoint 2
    |
new resource
    |
continue

Checkpointing reduces dependence on a particular physical carrier.

A checkpoint should be linked to:

process_id
procedural_unit
state_id
workload_id
resource_id
timestamp
integrity_hash

13. Resource Failure

Failure should be represented explicitly.

ACTIVE
  |
failure
  |
FAILED
  |
evidence preserved
  |
resource released
  |
new resource requested
  |
continuation

The interface must not silently report failed execution as completed.

14. Partial Resource Failure

A resource may degrade without becoming completely unusable.

Examples:

8 GPUs
    |
2 fail
    |
6 remain active

The interface should expose:

declared_capacity = 8
available_capacity = 6
verified_capacity = 6

The scheduler can determine whether the remaining capability is sufficient for continuation.

15. Functional Substitution

A process may substitute resources when their required capabilities are compatible.

Resource A
capability X

        replaced by

Resource B
capability X

The substitution must be validated against the task requirements.

The protocol should not assume that physically different resources are equivalent merely because they share a generic label.

16. Aggregated Resources

The interface may expose a resource pool as a logical resource.

Example:

GPU-01
GPU-02
GPU-03
GPU-04
     |
     v
COMPUTE POOL
     |
     v
logical capability

The pool should retain references to its underlying resources.

This supports the Resource Aggregation Layer.

17. Small Provider Integration

A small resource provider should be able to expose only a limited amount of capacity.

Example:

home workstation
   |
2 GPU-hours/day

The interface should make this capacity visible without requiring the provider to operate a large cluster.

Small contributions may later be aggregated into pools.

18. Provider Privacy

The public interface does not need to reveal every physical detail.

Possible disclosure levels:

public capability
provider-visible details
restricted hardware details
private operational data

The protocol should expose enough information for:

matching;

verification;

accounting;

without unnecessarily exposing proprietary or personal data.

19. Physical Location

Physical resources may have geographic or environmental constraints.

Examples:

country
region
network zone
laboratory
mobile
remote

Exact coordinates should only be exposed when operationally necessary and authorized.

The scheduler may match on location class or region without receiving a precise physical address.

20. Human Safety Boundary

Physical resources may cause physical effects.

Therefore the interface must distinguish between:

digital execution
physical execution
high-risk physical execution

Actions affecting physical equipment may require additional authorization.

Examples:

read sensor -> autonomous

start compute job -> autonomous

move robotic actuator -> policy dependent

change laboratory conditions -> explicit authorization

destructive physical operation -> explicit authorization

The exact boundary is resource-specific.

21. Human-in-the-Loop

The interface should support explicit human approval states.

REQUESTED
    |
HUMAN_REVIEW
    |
APPROVED
    |
EXECUTE

or:

REQUESTED
    |
REJECTED

Human intervention becomes part of process state rather than an undocumented external interruption.

22. Power and Energy

Physical computation requires energy.

Where measurable, the resource interface may expose:

energy_source
power_draw
energy_cost
energy_constraint
availability

This information can later feed:

provider economics;

resource selection;

compute pricing;

infrastructure investment analysis.

Energy data must be treated as an input to the economic model, not assumed to have a fixed global value.

23. Storage Interface

Storage is a persistent physical resource and should be represented separately from process memory.

The interface may expose:

storage_capacity
available_capacity
read/write capability
redundancy
latency
durability
verification
location class

The process should be able to move stored state between storage resources.

24. Network Interface

The process may require:

bandwidth
latency
availability
routing
privacy

Network resources should therefore be schedulable and replaceable like compute resources.

A network interruption should generate a process event rather than silently terminating the process.

25. Sensors and Instruments

For physical experimentation, the interface should distinguish:

instrument identity
measurement capability
calibration state
measurement range
precision
environmental constraints

A measurement result should reference:

instrument
calibration state
experiment
measurement event
timestamp

This creates a chain from physical observation to procedural state.

26. Calibration

A resource requiring calibration should expose its calibration status.

UNCALIBRATED
    |
CALIBRATION
    |
VERIFIED

A resource that fails calibration should not be treated as equivalent to a verified resource.

Calibration history should become part of provenance.

27. Adapter Architecture

Each physical resource class may have an adapter:

UFCPS Interface
     |
     +---- CUDA / GPU adapter
     +---- CPU adapter
     +---- cloud adapter
     +---- storage adapter
     +---- sensor adapter
     +---- robotics adapter
     +---- laboratory adapter

Adapters translate implementation-specific APIs into common UFCPS operations.

The semantic layer should remain independent of the adapter implementation.

28. API Operations

A minimal physical resource interface should provide:

discover()
describe()
verify()
reserve()
activate()
execute()
monitor()
checkpoint()
pause()
resume()
release()
fail()
recover()

Not every resource must implement every operation.

Unsupported operations should be explicit.

29. Resource State vs Process State

The interface must preserve a strict distinction:

RESOURCE STATE
    |
    +-- available
    +-- active
    +-- failed
    +-- maintenance

PROCESS STATE
    |
    +-- running
    +-- blocked
    +-- continuation-ready
    +-- completed

A resource may fail while the process remains continuation-ready.

Likewise, a process may terminate while a resource remains available.

30. Economic Integration

A completed resource execution should produce a record consumable by Compute Verification and Accounting.

Physical Resource
      |
Execution
      |
Usage Evidence
      |
Verification
      |
Verified Compute
      |
Accounting
      |
Compensation

The interface does not determine the final currency amount.

That remains the responsibility of the economic protocol.

31. Process Continuity Across Physical Infrastructure

The target behavior is:

Question Q
    |
Process P
    |
GPU Cluster A
    |
checkpoint
    |
Cluster A unavailable
    |
Resource discovery
    |
GPU Cluster B
    |
restore state
    |
continue P

The physical infrastructure has changed.

The process has not been terminated.

This is one of the core experimental claims of Level 2.

32. Security Requirements

Physical interfaces must defend against:

fake resource identity;

forged telemetry;

unauthorized execution;

malicious firmware or adapters;

compromised credentials;

false capacity;

manipulated measurements;

replayed evidence;

resource hijacking.

The interface should expose security state where relevant.

33. Experimental Integration

Initial experimental implementations should start with reversible digital resources:

local CPU
local GPU
cloud compute
distributed storage

Later stages may include:

sensors
robotics
laboratory equipment
manufacturing systems

Higher physical autonomy should be introduced progressively.

34. Acceptance Criteria

A candidate physical resource interface should demonstrate:

resource discovery;

capability declaration;

verification;

reservation;

execution;

monitoring;

failure reporting;

checkpoint or equivalent state preservation where supported;

resource substitution;

integration with compute verification;

integration with compute accounting;

preservation of process continuity after resource failure.

35. Architectural Principle

The physical world becomes part of UFCPS through capabilities and verifiable state, not through permanent ownership of the process by any device.

The intended chain is:

Process Requirement
      |
Capability Request
      |
Resource Discovery
      |
Resource Verification
      |
Reservation
      |
Execution
      |
Evidence
      |
Verified Resource Contribution
      |
Economic Accounting

If the physical carrier disappears:

carrier failure
      |
state preserved
      |
functional substitute
      |
process continuation

The ultimate objective is not to make one machine indispensable.

It is to make the process capable of finding another machine, resource, or physical configuration capable of continuing the required function.
