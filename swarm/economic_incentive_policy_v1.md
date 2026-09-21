UFCPS Level 2 — Economic Incentive Policy v1

Status

Document role: economic integration specification

Status: recommended for simulation

Scope: swarm/

Depends on:

swarm/compute_economy_model_v1.json

swarm/points_economy_v1.json

swarm/compute_accounting_v1.json

swarm/resource_registry_v1.json

swarm/swarm_scheduler_v1.py

schemas/deadlock_v1.json

swarm/proposal_engine_v1.py

swarm/economic_simulator_v1.py

1. Architectural principle

The economic layer is an enabling layer for process continuity.

It must not redefine:

the meaning of a problem;

the correctness of a research result;

the Level 1 process identity;

C1-C5 semantic criteria;

the rule Local Failure != Process Termination.

Economic mechanisms answer a different question:

How can scarce computational and physical resources remain available long enough for the process to continue?

Therefore economic reward is attached to verified contribution and useful process continuity, not to the claim that a research question has been solved.

2. Mechanism A — Recursion Cost Control

2.1 Motivation

Unlimited recursive delegation can consume resources even when the new transition contributes little or no new information.

The economic layer therefore assigns a cost to repeated delegation.

This is not a penalty on recursion itself. It is a control on resource consumption by low-information recursion.

2.2 Inputs

For a transition P_n -> P_n+1, collect:

recursion_depth;

verified_compute_requested;

verified_compute_consumed;

new_information_score;

unresolved_information_delta;

deadlock_information_score;

repeated_state_signal;

C5 recursion status.

2.3 Recommended cost function

Define:

effective_step_cost = base_step_cost × recursion_multiplier × redundancy_multiplier

where:

recursion_multiplier = 1 + alpha × depth

and:

redundancy_multiplier = 1 + beta × repetition

Recommended initial status:

alpha is a simulation parameter;

beta is a simulation parameter;

both are bounded;

no mandatory exponential function in v1.

The controller may later test exponential policies, but they should remain experiments rather than core semantics.

2.4 Information relief

A recursion step that produces verified new information should reduce its economic penalty.

Define:

information_relief = clamp(new_information_score + unresolved_information_delta, 0, 1)

and:

effective_penalty = raw_penalty × (1 - gamma × information_relief)

Thus:

deep recursion with no new information becomes progressively more expensive;

deep recursion producing meaningful new information remains economically viable;

a valid unresolved result can still create information and therefore justify the next transition.

2.5 C5 interaction

C5 remains the semantic recursion-control mechanism.

The economic controller does not replace C5.

Recommended rule:

C5 violation -> no new discretionary economic budget

while:

C5 valid + verified contribution -> normal economic evaluation

3. Mechanism B — Deadlock Information Pricing

3.1 Principle

A deadlock is not merely an error object.

A structured deadlock can become a reusable information resource for the next process.

Therefore the economic layer should distinguish between:

low-information failure;

verified unresolved result;

richly structured deadlock.

3.2 Information density

Define a normalized deadlock_information_score from 0 to 1.

Recommended components:

boundary_completeness;

constraint_completeness;

attempt_trace_completeness;

negative_result_quality;

evidence_quality;

substitution_guidance;

reproducibility.

Illustrative weighted score:

DIS = 0.20*boundary + 0.20*constraint + 0.15*attempt_trace + 0.15*negative_result + 0.10*evidence + 0.10*substitution + 0.10*reproducibility

Weights are experimental and must be calibrated.

3.3 Reward rule

A carrier receives a bonus for a verified structured deadlock:

deadlock_bonus = deadlock_budget × DIS

The bonus is not payment for failure.

It is compensation for producing a reusable information object that reduces uncertainty for subsequent process steps.

3.4 Anti-gaming controls

The bonus requires:

schema-valid deadlock;

provenance;

verification;

non-duplicate content;

reproducibility or independent confirmation where applicable.

Repeated copies of the same deadlock must not generate unlimited rewards.

3.5 Priority interaction

DIS may be used as one scheduler signal, but it must not override:

task correctness constraints;

capability compatibility;

verification requirements;

C5;

core process continuity rules.

4. Mechanism C — External Resource Ingestion

4.1 Principle

External resource inflow changes the available physical basis of the swarm.

Relevant inflows include:

participant GPUs;

participant CPUs;

storage;

network capacity;

dedicated nodes;

verified external compute contracts;

investment capital.

The economic layer should react to these changes, but should not automatically create arbitrary inflation.

4.2 Resource inflow signal

Define:

resource_inflow_index = verified_new_capacity / target_capacity

The index is computed separately for:

compute;

storage;

network;

other resource classes.

4.3 Compute-unit pricing

The price of a compute unit should be recalculated from:

verified resource cost;

utilization;

energy cost;

maintenance;

depreciation;

network cost;

supply/demand;

available reserve capacity.

External resource inflow should therefore first affect capacity and marginal cost, not simply increase token/credit issuance.

4.4 Capital inflow

Capital may finance:

hardware;

energy;

network;

verification infrastructure;

research operations.

Capital must not by itself create an unlimited reward entitlement.

The cost-anchored annual model remains:

C_next = projected verified annual cost

maximum_profit = 10 × C_next

maximum_total_compensation = 11 × C_next

4.5 Proposal engine interaction

proposal_engine_v1.py may include:

requested compute;

required capacity;

expected duration;

expected Resource Credit budget;

optional crypto budget;

capital requirement;

resource gap.

A proposal must not be interpreted as proof that the proposed resources exist.

Actual issuance and compensation require later verification.

5. Combined economic flow

Recommended flow:

unresolved question
→ task prospect
→ resource requirement
→ market discovery
→ scheduler assignment
→ verified execution
→ result / negative result / deadlock
→ information valuation
→ economic accounting
→ next process step

For recursion:

P_n -> P_n+1

the controller evaluates both:

semantic validity under C5;

economic resource consumption.

For a deadlock:

Deadlock_n

the controller evaluates both:

semantic completeness;

information density.

6. Relationship to existing accounting

The mechanisms must remain layered.

Existing layer

resource_registry_v1
→ identifies resources.

compute_accounting_v1
→ verifies delivered compute and records compensation.

points_economy_v1
→ defines the optional non-cash participant incentive.

payment_router_v1
→ routes RC / crypto / fiat funding.

resource_market_v1
→ discovers and matches resource offers.

swarm_scheduler_v1
→ assigns agents and resources to process tasks.

New economic policy

economic_incentive_policy_v1
→ calculates:

recursion economic pressure;

deadlock information value;

resource-inflow effects.

It must not duplicate the underlying resource or compute ledgers.

7. Stress-test requirements

The economic simulator should test at minimum:

Recursion

shallow valid recursion;

deep valid recursion with new information;

deep recursion with repeated state;

recursion approaching C5 boundary;

recursion after C5 rejection.

Expected property:

low-information recursion cost >= high-information recursion cost

for otherwise comparable resource demand.

Deadlock

empty/poorly structured deadlock;

schema-valid deadlock;

high-density deadlock;

duplicate deadlock;

independently reproduced deadlock.

Expected property:

reward(high-DIS) > reward(low-DIS)

only when verification conditions are equivalent.

External resource ingestion

no new resources;

small participant-GPU influx;

large participant-GPU influx;

energy-price shock;

hardware-cost shock;

capital influx without compute influx;

compute influx without capital influx.

Expected property:

resource influx changes capacity and unit economics before any unrestricted reward expansion.

Economic safety

early-participant concentration;

mass participant onboarding;

demand collapse;

demand surge;

liquidity stress;

repeated micro-transactions;

malicious recursive delegation.

8. Core invariants

The following invariants are required for the simulation layer:

Local Failure != Process Termination

Unverified Compute -> No Verified Compute Reward

Unverified Deadlock -> No Deadlock Information Bonus

Duplicate Deadlock -> No Unlimited Repeated Bonus

C5 Invalid -> No New Discretionary Recursive Budget

Resource Inflow != Automatic Unlimited Issuance

maximum_profit <= 10 × projected_annual_cost

maximum_total_compensation <= 11 × projected_annual_cost

Annual Cost Anchor = current_year_actuals -> next_year_projection

Author Royalty = 0.001% of every transaction

Internal Crypto <-> RC protocol fee = 0

Internal Crypto <-> RC spread = 0

Resource Credits are non-cash service credits

Crypto remains optional

Research outcome is not required for compensation for verified process continuity

9. Parameters explicitly marked experimental

The following must not be treated as settled constants:

recursion coefficients alpha, beta, gamma;

deadlock information-density weights;

deadlock reward budget;

exact conversion of verified compute to points/credits;

resource-inflow response coefficients;

dynamic service prices;

rate of release within a year.

They belong in the economic experiment runner and should be calibrated against measured system behavior.

10. Recommended next implementation

First implement a pure calculation layer that has no authority over payments.

Recommended component:

swarm/economic_incentive_engine_v1.py

Inputs:

transition/delegation metadata;

deadlock object;

verified accounting events;

current resource-market state;

current annual cost projection.

Outputs:

recursion economic multiplier;

deadlock information score;

deadlock bonus;

resource-inflow index;

recommended budget/price adjustments;

invariant-check results.

Only after this calculation layer passes stress tests should it be connected to actual issuance, payment routing, or production scheduling.
