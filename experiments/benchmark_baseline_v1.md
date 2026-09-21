UFCPS Benchmark Baseline v1

Status

Baseline status: PASS

Unified runner result:

scenarios requested: 20

scenarios passed: 20

scenarios failed: 0

scenarios with errors: 0

all passed: true

This document records the current simulation baseline for the UFCPS v1
architecture. It is a reference point for later changes to the runtime,
schemas, protocols, policies, and scenarios.

Reproduction

From the repository root:

python -m simulation.runner

The unified runner executes all scenarios registered in
simulation.runner.SCENARIOS and evaluates their explicit acceptance
conditions.

A single scenario can be run with:

python -m simulation.runner --scenario <scenario_name>

Benchmark Suite

The current benchmark contains the following 20 tests.

#

Scenario

Purpose

Result

1

schema_validation

Validate procedural and experimental state payloads against schemas

PASS

2

transition_validation

Validate correct and intentionally invalid procedural transitions

PASS

3

basic_handoff

Demonstrate basic continuation across a carrier handoff

PASS

4

forced_deadlock

Demonstrate deadlock as a local non-terminal state

PASS

5

carrier_substitution

Continue on a carrier selected for a missing capability

PASS

6

stateless_delegation_control

Compare continuation with and without preserved state

PASS

7

parallel_resolution

Create isolated parallel branches with preserved provenance

PASS

8

contradictory_branches

Preserve contradictory branch results as a new unresolved difference

PASS

9

composition

Compose partial branch results while preserving provenance

PASS

10

negative_result

Preserve a negative result and avoid repeating an invalidated path

PASS

11

autonomous_experiment

Generate and execute an experiment from an unresolved difference

PASS

12

autonomous_negative_result

Preserve an autonomous disconfirming result and generate the next experiment

PASS

13

repeated_carrier_replacement

Test repeated carrier substitution across a procedural chain

PASS

14

communication_interruption

Recover continuation from shared state after communication loss

PASS

15

recursion_stress

Enforce C5 recursion control without confusing pause with termination

PASS

16

global_termination

Distinguish local carrier failure from explicit process termination

PASS

17

long_run_continuity

Test continuity across a longer chain with controlled interruptions

PASS

18

swarm_scaling

Exercise isolated branch execution at multiple carrier counts

PASS

19

continuity_vs_centralization

Record architectural behavior under distributed and centralized conditions

PASS

20

process_identity

Test continuity under repeated carrier identity changes

PASS

Architectural Properties Covered

The baseline exercises the following UFCPS properties represented in the
current simulation layer:

procedural state persists independently of a single carrier

local failure does not imply global process termination

continuation state can survive carrier substitution

unresolved differences remain available as future process input

negative results can exclude previously invalidated paths

branches can remain isolated while retaining provenance

contradictory results can be preserved rather than silently discarded

partial states can be composed into a successor state

autonomous research can generate its own next question and method

recursion can be stopped at a control boundary

communication loss can be recovered through shared state

process continuity can survive repeated carrier replacement

carrier identity and process identity are treated as distinct

global termination remains an explicit process-level condition

Baseline Invariants

The current passing suite establishes the following operational invariants
within the implemented simulation model:

Local Failure != Process Termination

Carrier Identity != Process Identity

Negative Result != No Information

P_n -> P_n+1

For carrier-changing transitions, continuation-relevant state is preserved and
the procedural step index advances by one.

Validation Boundary

This baseline is a software architecture and simulation benchmark. A
passing result means that the implemented scenarios satisfy their explicit
acceptance conditions in the current repository state.

It does not by itself establish:

scientific validity of UFCPS as a theory of intelligence

empirical validity in physical or social systems

convergence or correctness for arbitrary problems

performance superiority over alternative architectures

robustness under all possible adversarial or stochastic conditions

Those questions require additional benchmarks, implementations, and empirical
evidence.

Change Control

This file should remain a historical baseline.

When runtime or scenario behavior changes:

rerun the complete benchmark;

record the new aggregate result;

identify any newly passing, failing, or modified tests;

create a new baseline version rather than silently rewriting this one.

Recommended next baseline names:

benchmark_baseline_v2.md

benchmark_baseline_v3.md

Current Baseline

The current reference point is:

UFCPS v1 — 20/20 benchmark scenarios passing.
