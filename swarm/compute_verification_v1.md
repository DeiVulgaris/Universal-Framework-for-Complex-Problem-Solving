UFCPS Compute Verification v1

1. Purpose

Compute Economy requires a reliable distinction between:

claimed compute
        !=
verified compute

A resource provider should receive compensation only for computational contribution that satisfies the verification rules of the network.

This protocol defines the verification layer between resource execution and economic accounting.

The resource provider is not responsible for guaranteeing that the research question will be solved.

The role of provided computational capacity is to make the required process execution possible and to preserve its continuity.

2. Core Principle

Verified compute compensates the provision of process continuity, not the production of new meaning.

Verification must establish, with an explicitly stated confidence level, that:

the registered resource existed;

the resource had the declared capability;

the resource was allocated to a UFCPS process;

the claimed workload was actually executed;

the claimed quantity is consistent with observed execution;

the same execution is not credited twice;

the resulting accounting event can be independently audited;

the resource was capable of supporting the required continuation state for the declared operation.

The network must not require a successful scientific or semantic outcome from the resource provider as a condition for compute compensation.

3. Verification Object

A verified compute event should contain at least:

verification_event_id
resource_id
provider_id
process_id
task_id
workload_id
compute_unit_id
claimed_quantity
verified_quantity
verification_method
verification_confidence
evidence_refs
execution_start
execution_end
status
provenance

The event becomes eligible for economic settlement only after the required verification state is reached.

4. Verification Lifecycle

CLAIMED
   |
REGISTERED
   |
RESOURCE CHECK
   |
EXECUTION CHECK
   |
WORK QUANTITY CHECK
   |
INTEGRITY CHECK
   |
ANTI-DUPLICATION CHECK
   |
VALIDATED
   |
ACCOUNTING ELIGIBLE

Possible terminal states:

VERIFIED
PARTIALLY_VERIFIED
REJECTED
DISPUTED
EXPIRED

5. Resource Identity Verification

Before compute is credited, the network should establish that the claimed resource corresponds to a registered resource.

Possible evidence:

registry record;

cryptographic identity;

public key;

provider signature;

hardware attestation;

trusted execution attestation where available;

benchmark record;

historical resource evidence.

The protocol should distinguish:

resource identity
resource capability
resource availability
resource utilization

These are separate claims.

6. Capability Verification

A resource may claim:

GPU
16 GB memory
X throughput

but the network should not assume that the claim is correct.

Capability verification may include:

Benchmark

Run a standardized workload and compare the observed result with the declared capability.

Challenge Task

Submit a task whose expected characteristics are independently known.

Replicated Execution

Run the same computation on another trusted or independently verified resource and compare results.

Attestation

Use cryptographic or hardware-backed evidence where available.

No single verification method is mandatory for all resource classes.

7. Execution Verification

The network must determine whether the claimed resource actually performed the requested computation.

A provider may submit:

execution claim
=
"I executed workload W for quantity Q."

The network should obtain evidence sufficient to distinguish:

performed
not performed
partially performed
duplicated
unverifiable

Possible evidence:

signed execution records;

job identifiers;

scheduler records;

challenge responses;

intermediate checkpoints;

verifiable computation proofs;

replicated outputs;

trusted hardware evidence.

8. Quantity Verification

The system must distinguish between:

time allocated
time available
time reserved
time active
time performing the declared process operation

Compensation should be based on the resource quantity defined by the Compute Unit specification.

For example:

reserved = 100 GPU-hours
active = 80 GPU-hours
verified = 72 GPU-hours

The accounting layer may credit only:

72 verified GPU-hours

unless the economic protocol explicitly defines another compensation rule.

The verification target is the continuity-relevant execution of the declared process operation, not whether that operation generated a successful answer.

9. Normalized Compute Verification

When normalized compute units are used:

raw resource execution
        |
benchmark / calibration
        |
conversion
        |
normalized compute
        |
verification

A conversion factor must be tied to:

a defined benchmark;

a version;

a calibration period;

a workload definition.

The system should avoid permanent hardware equivalence assumptions when hardware performance changes materially.

10. Challenge-Based Verification

A challenge may be generated to test whether a resource is genuinely capable of performing the declared work.

Example:

Provider claims:
    10 NCU/s

Network challenge:
    workload C

Observed:
    9.7 NCU/s

Result:
    capability claim accepted within tolerance

Challenges may be:

random;

periodic;

triggered by anomalies;

triggered by high-value claims;

selected by validators.

Challenge frequency should balance:

security
vs.
verification cost

11. Sampling

Not every computation necessarily needs full independent replication.

The network may use risk-based sampling.

Example:

low-risk / low-value:
    periodic spot checks

high-value:
    stronger verification

anomalous provider:
    increased verification

new provider:
    onboarding verification

Verification policy may therefore be adaptive.

12. Redundant Verification

High-value or difficult-to-verify workloads may be executed independently by multiple resources.

Provider A
     |
     +---- result A
                             compare
              /
     +---- result B
     |
Provider B

Possible outcomes:

AGREEMENT
DISAGREEMENT
INCONCLUSIVE

Disagreement should create a structured verification event rather than silently selecting one result.

13. Verifiable Computation

For workloads supporting cryptographic proofs, the network may use verifiable-computation techniques.

Examples may include:

succinct proofs;

validity proofs;

proof-carrying computation;

trusted execution evidence.

The protocol does not require one specific cryptographic technology.

The requirement is:

the verification cost must be economically and operationally compatible with the value of the computation being verified.

14. Evidence Chain

A verified compute event should point to evidence.

Resource
   |
Capability Evidence
   |
Allocation
   |
Execution Evidence
   |
Quantity Evidence
   |
Verification
   |
Accounting Event

The chain should be independently reconstructible where the relevant data is available.

Large artifacts may remain outside the ledger.

The ledger may store:

hash
pointer
timestamp
event identifier
signature
provenance

15. Anti-Duplication

The same computational contribution must not generate multiple rewards.

A verification record should therefore contain a uniqueness identity derived from relevant fields, such as:

resource_id
process_id
workload_id
execution_interval
execution_nonce

A second economic claim referring to the same execution should be rejected or linked to the original event.

16. Partial Verification

A claim does not have to be all-or-nothing.

Example:

claimed:   1,000 GPU-hours
verified:    840 GPU-hours
unverified: 160 GPU-hours

The accounting system may therefore create:

verified_quantity = 840

and separately preserve the discrepancy.

This is preferable to silently accepting or silently deleting the complete claim.

17. Failed or Inconclusive Computation

A computation may fail to produce a solution, a new semantic result, or a resolution of the research question while still representing valid resource contribution.

The protocol therefore separates:

process continuity
        from
research resolution

Example:

100 verified GPU-hours
        |
experiment cannot resolve the question
        |
continuation state preserved
        |
provider compensated for verified compute

The resource provider is responsible for supplying the agreed computational capability and executing the declared operation.

The provider is not responsible for proving that the current state of technology is sufficient to solve the underlying question.

The research outcome is recorded separately as:

resolved
partial
negative
inconclusive
blocked

No outcome class, by itself, retroactively invalidates verified resource consumption.

17A. Technological Limit Boundary

A UFCPS process may reach a point at which the currently available technology cannot resolve the question.

This does not by itself constitute a failure of the resource layer.

The process may legitimately end a current procedural unit in a state such as:

TECHNOLOGICALLY_UNRESOLVED

while preserving:

current state;

attempted operations;

evidence;

negative results;

required capabilities;

resource history;

continuation conditions.

The next procedural unit may become possible only after a new capability or technology appears.

Therefore:

The obligation of the resource layer is to preserve the conditions for continuation, not to guarantee resolution.

18. Provider Reliability

Verification history may contribute to a resource/provider reliability record.

Possible metrics:

verification pass rate;

discrepancy rate;

failure rate;

response to challenges;

consistency of benchmark performance;

uptime;

dispute history.

Reliability should be contextual.

A provider may be reliable for one workload class and unsuitable for another.

19. Validator Network

Validators independently evaluate verification evidence.

A validator may return:

VALID
INVALID
PARTIAL
DISPUTED
INCONCLUSIVE

The protocol should define how validator disagreement is handled.

Possible mechanisms:

quorum;

weighted quorum;

random validator assignment;

escalation;

re-execution;

arbitration process.

Validator selection and weighting remain open research questions.

20. Economic Boundary

The verification layer must terminate before irreversible economic settlement.

DECLARED PROCESS OPERATION
    |
EXECUTION
    |
CONTINUITY VERIFICATION
    |
ACCOUNTING ELIGIBILITY
    |
ECONOMIC SETTLEMENT

A disputed claim should therefore be able to remain outside final settlement.

The economic layer pays for verified resource provision according to the protocol.

It does not make payment contingent on semantic success of the research process.

21. Fraud Resistance

The verification system must consider:

fake execution
fake hardware
fake benchmarks
replayed evidence
duplicate claims
colluding validators
Sybil providers
tampered logs
fabricated output
time manipulation
resource spoofing

Each threat should have:

attack
detection
mitigation
residual risk

22. Privacy

Verification should expose only what is required for independent checking.

Potentially sensitive data may include:

provider identity;

hardware details;

location;

workload data;

proprietary algorithms;

research data.

Therefore:

public proof
    !=
complete private execution trace

The system should investigate zero-knowledge proofs, selective disclosure, hashed evidence, and permissioned evidence stores where necessary.

23. Verification Cost

Verification itself consumes resources.

Therefore the economic model must account for:

primary compute
+
verification compute
+
storage
+
network traffic
+
validator work

The network should avoid a design in which:

cost of proving compute
>
value of compute

for small tasks.

This is especially important for micro-providers.

24. Micro-Provider Verification

Small providers should be able to participate economically.

Possible strategies:

pooled verification;

probabilistic sampling;

batched claims;

reputation-based verification frequency;

low-cost challenges;

shared validators.

The protocol must preserve individual attribution while reducing per-transaction overhead.

25. Verification State and Process Continuity

Verification is itself a procedural process.

Therefore:

Verification Agent A
        |
failure
        |
Verification Agent B
        |
continued verification

The evidence state must survive carrier replacement.

This reuses the Level 1 invariant:

Local Failure != Process Termination

A failed validator must not destroy a valid verification process.

26. Dispute Lifecycle

VERIFIED
    |
challenge
    |
DISPUTED
    |
+---------+---------+
|                   |
CONFIRMED        REJECTED
|                   |
SETTLE           INVALIDATE

A dispute should preserve the evidence and reasoning that produced it.

27. Required Interfaces

The verification layer should expose at least:

register_claim()
verify_resource()
verify_capability()
verify_execution()
verify_quantity()
check_duplicate()
submit_evidence()
challenge_claim()
resolve_dispute()
finalize_verification()

These interfaces should be independent of any particular blockchain implementation.

28. Output to Compute Accounting

The verification layer should produce a deterministic result:

verification_status
verified_quantity
compute_unit
confidence
evidence_refs
validator_refs
dispute_status

The Compute Accounting layer consumes this result.

Example:

verified_quantity = 72
compute_unit = GPU-hour
status = VERIFIED
confidence = 0.99

Only then may the economic protocol calculate compensation.

29. Experimental Program

Level 2 should implement verification benchmarks such as:

V01 valid resource claim
V02 invalid resource claim
V03 false capability claim
V04 genuine execution
V05 fabricated execution
V06 partial execution
V07 duplicate claim
V08 replayed evidence
V09 validator disagreement
V10 challenge failure
V11 high-value replicated execution
V12 micro-provider batch
V13 provider failure during verification
V14 validator failure during verification
V15 disputed claim recovery
V16 privacy-preserving verification
V17 normalized compute calibration
V18 hardware substitution
V19 malicious provider
V20 malicious validator

Each benchmark should report:

detection;

verification cost;

false acceptance;

false rejection;

settlement impact;

recovery behavior.

30. Acceptance Criteria

A candidate verification mechanism should demonstrate:

resource identity can be checked;

capability claims can be challenged;

execution claims can be verified;

quantity can be measured;

duplicate claims are rejected;

partial verification is preserved;

failed research does not invalidate real compute;

disputes preserve evidence;

validator failure does not terminate verification;

verification cost remains economically viable;

verified compute compensation is independent of whether the underlying question is resolved;

technological inability to resolve a question does not invalidate valid resource contribution.

31. Architectural Principle

Compute becomes economically compensable when the network can verify that a resource performed the declared process-supporting work.

The sequence is therefore:

Process Requirement
      |
Resource Provision
      |
Evidence
      |
Verification
      |
Verified Continuity-Supporting Compute
      |
Accounting
      |
Compensation

The verification layer is the bridge between the physical resource economy and the cryptographic economy of UFCPS.

The bridge does not assert that the supplied compute produced a new meaning, solved the question, or advanced the frontier.

Those are properties of the pr
