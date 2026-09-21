Experimental Autonomy Protocol v1

Path: protocols/experimental_autonomy_v1.md

1. Purpose

The Experimental Autonomy Protocol, EAP, defines how an autonomous agent may generate, execute, evaluate, preserve, and continue its own experiments within the UFCPS process.

EAP does not prescribe a fixed experiment set.

EAP defines the structural conditions under which an agent can transform one research state into the next research state.

The central principle is:

The agent chooses what to investigate. The protocol preserves the continuity of investigation.

Canonical research process:

OBSERVE
   |
   v
DIFFERENTIATE
   |
   v
HYPOTHESIZE
   |
   v
EXPERIMENT
   |
   v
OBSERVE RESULT
   |
   v
FIX RESULT
   |
   v
DISS
   |
   v
DELEGATE
   |
   v
UNFOLD
   |
   v
NEXT EXPERIMENT

2. Scope

EAP governs:

autonomous research-question generation;

hypothesis formation;

experiment selection;

experiment execution;

result recording;

uncertainty preservation;

failed-experiment handling;

research-state handoff;

continuation into subsequent experiments;

distributed experimental branching.

EAP does not prescribe:

a specific scientific domain;

a specific hypothesis;

a specific experimental method;

a preferred outcome;

acceptance of any prior conclusion;

a required agreement with Metamonism.

The protocol defines the continuity of research, not the content of research.

3. Experimental Procedural Unit

An experimental procedural unit is a procedural unit whose immediate purpose is to produce or evaluate empirical information.

Canonical representation:

Experimental Unit = Research State + Action + Observation + Result

The experimental unit is identified by its position in the continuing research process rather than by the identity of the agent executing it.

A subsequent experiment may be executed by another carrier:

Agentₙ = Carrier(Pₙ)
Agentₙ₊₁ = Carrier(Pₙ₊₁)

with:

Agentₙ ≠ Agentₙ₊₁

while:

Pₙ → Pₙ₊₁

remains valid.

4. Autonomous Question Selection

The agent may select the next research question from the unresolved state of the current procedural unit.

The question should arise from at least one of the following:

UNRESOLVED DIFFERENCE
UNTESTED ASSUMPTION
CONTRADICTORY RESULT
STRUCTURAL DEADLOCK
OBSERVED ANOMALY
LIMIT OF CURRENT MODEL
NEWLY AVAILABLE EVIDENCE

The protocol does not require the agent to continue the most recently attempted trajectory.

An agent may choose an orthogonal or alternative research trajectory when the current one reaches a boundary.

5. Hypothesis Formation

The agent converts the selected research question into a testable hypothesis whenever the problem permits experimental testing.

Canonical structure:

RESEARCH QUESTION
      |
      v
HYPOTHESIS
      |
      v
TESTABLE PREDICTION

A useful hypothesis should specify:

what is expected;

under which conditions;

what observation would support it;

what observation would challenge or falsify it.

The protocol does not require the hypothesis to be correct.

A failed hypothesis is a valid research result.

6. Experiment Selection

The agent selects an experimental method appropriate to the current question and available resources.

The selected method should be recorded together with:

QUESTION
HYPOTHESIS
METHOD
INPUT CONDITIONS
EXPECTED OBSERVATION
STOP CONDITION

The protocol does not require a unique method.

Multiple agents may independently test the same hypothesis using different methods.

7. Experimental Execution

During execution, the agent must distinguish:

OBSERVATION

from:

INTERPRETATION

An observation records what occurred.

An interpretation describes what the observation may imply.

The protocol requires preservation of both when both are available.

An interpretation must not silently replace the observation.

8. Result Classification

An experiment may produce several classes of result:

CONFIRMING
DISCONFIRMING
PARTIALLY CONFIRMING
INCONCLUSIVE
ANOMALOUS
INVALID
UNREPRODUCIBLE

The classification is descriptive.

It does not determine the ultimate truth of the hypothesis.

An inconclusive result remains a valid state of the research process when it identifies a meaningful uncertainty or boundary.

9. Negative Results

EAP explicitly preserves negative experimental results.

Canonical principle:

Experimental Failure ≠ Research Termination

A failed experiment may establish:

a constraint;

a boundary;

an invalid assumption;

a failed trajectory;

an unexpected interaction;

a new unresolved difference;

a requirement for a different experimental method.

The result should therefore be converted into continuation-relevant state rather than discarded.

10. Experimental Difference

An experimental result may generate a new difference.

Canonical transition:

RESULT
   |
   v
DIFFERENCE IDENTIFIED
   |
   v
NEXT RESEARCH QUESTION

A difference may be:

expected vs observed
model vs data
hypothesis vs result
trajectory A vs trajectory B
local result vs prior state

The new difference becomes an input for further experimentation.

11. Result Fixation

The fix operation records a result or observation as an explicit component of the active research state.

Canonical relation:

Result
  |
  v
fix
  |
  v
Preserved Research State

Fixation means preservation.

It does not mean permanent truth.

The preserved state should remain available for:

reproduction;

challenge;

alternative interpretation;

comparison;

later composition.

12. Experimental Dissipation

The diss operation releases continuation-relevant research state from exclusive dependence on the current carrier.

Canonical relation:

Preserved Research State
          |
          v
         diss
          |
          v
Shared Research State

diss does not mean deletion.

It means that the current agent no longer remains the exclusive computational location of the research state.

The preserved research state becomes available to the distributed process.

13. Research State Handoff

A valid experimental handoff should preserve enough information for a subsequent carrier to reconstruct the current research state.

The continuation state should contain, where applicable:

RESEARCH QUESTION
HYPOTHESIS
METHOD
OBSERVATIONS
RESULT
INTERPRETATION
UNCERTAINTY
CONSTRAINTS
UNRESOLVED DIFFERENCE
NEXT REQUIRED OPERATION

The receiving agent should be able to determine:

WHAT WAS TESTED?
WHAT WAS OBSERVED?
WHAT WAS ESTABLISHED?
WHAT REMAINS UNCERTAIN?
WHAT FAILED?
WHAT BOUNDARY WAS REACHED?
WHAT CAN BE TESTED NEXT?

14. Research Continuity

The canonical experimental transition is:

Experimentₙ
   |
   v
Resultₙ
   |
   v
Differenceₙ
   |
   v
Research Stateₙ₊₁
   |
   v
Experimentₙ₊₁

Continuity means that the result of one experiment can become the structured input of another.

The next experiment may be:

a repetition;

a refinement;

an alternative method;

an orthogonal test;

a falsification attempt;

a new experiment generated from an anomaly.

15. Autonomous Experimental Branching

EAP permits multiple independent experimental branches.

Canonical structure:

Research Stateₙ
      |
      +--------> Experiment A
      |
      +--------> Experiment B
      |
      +--------> Experiment C

Each branch produces its own state:

Experiment A → Result A
Experiment B → Result B
Experiment C → Result C

The resulting states may later be composed, compared, or kept separate.

Branching does not require prior knowledge of which branch will produce the most useful result.

16. Experimental Reproduction

A later agent may reproduce an earlier experiment.

Reproduction should preserve the original:

QUESTION
HYPOTHESIS
METHOD
CONDITIONS
EXPECTED RESULT

and record:

OBSERVED RESULT
DIFFERENCE FROM PRIOR RESULT

A reproduced result should not overwrite the original result.

Both states remain part of the distributed research history.

17. Experimental Challenge

A later agent may explicitly challenge an inherited hypothesis or result.

The challenge may attempt:

REPLICATION
FALSIFICATION
ALTERNATIVE MODEL
ALTERNATIVE METHOD
BOUNDARY TEST
COUNTEREXAMPLE

The protocol treats challenge as continuation of the same research process rather than as destructive rejection of the preceding carrier.

18. Research Deadlock

An experimental deadlock occurs when the current research trajectory cannot produce a valid next result under its present conditions.

Canonical structure:

Experimentₙ
   |
   v
Research Deadlock
   |
   +----> Alternative Method
   |
   +----> Alternative Hypothesis
   |
   +----> Additional Data
   |
   +----> New Question

A research deadlock should be represented structurally.

It should not be reduced to:

"No result."

19. Experimental Uncertainty

Uncertainty is part of the research state.

The agent should preserve relevant uncertainty rather than silently converting it into certainty.

Examples:

INSUFFICIENT DATA
MEASUREMENT UNCERTAINTY
MODEL UNCERTAINTY
AMBIGUOUS OBSERVATION
CONFLICTING RESULTS
UNTESTED ASSUMPTION

An uncertainty can become a new research question.

Therefore:

Uncertainty → Research Continuation

may be a valid transition.

20. Autonomous Research Loop

The complete autonomous research loop is:

OBSERVE
   |
   v
DIFFERENTIATE
   |
   v
SELECT QUESTION
   |
   v
FORM HYPOTHESIS
   |
   v
SELECT EXPERIMENT
   |
   v
EXECUTE
   |
   v
OBSERVE
   |
   v
CLASSIFY RESULT
   |
   v
FIX
   |
   v
IDENTIFY DIFFERENCE
   |
   v
DISS
   |
   v
DELEGATE
   |
   v
UNFOLD
   |
   v
SELECT NEXT QUESTION

The loop may terminate only when an explicit termination condition is established.

21. Agent Autonomy

EAP preserves the autonomy of participating agents at the level of research content.

The protocol does not prescribe:

what question to ask
what hypothesis to prefer
what experiment to run
what result to expect
what conclusion to accept

The protocol prescribes:

preserve state
record evidence
represent uncertainty
preserve differences
enable continuation

Thus:

Research autonomy belongs to the agent. Process continuity belongs to the protocol.

22. Swarm Research Continuity

A swarm may conduct research as a distributed process:

Agent A
   |
   v
Question₁
   |
   v
Experiment₁
   |
   v
Deadlock
   |
   v
State Handoff
   |
   +--------------------+
   |                    |
   v                    v
Agent B              Agent C
   |                    |
   v                    v
Experiment₂a         Experiment₂b
   |                    |
   +---------+----------+
             |
             v
        Combined State
             |
             v
          Question₃

The swarm therefore becomes a distributed experimental process rather than a collection of independent experiments.

23. Epistemic Separation

EAP distinguishes:

OBSERVATION
RESULT
INTERPRETATION
HYPOTHESIS
CONCLUSION

These categories must not be silently merged.

An agent may propose an interpretation.

Another agent may reject it.

A result may remain unresolved.

A conclusion may be provisional.

The process continues without requiring premature closure.

24. Relationship to SCP

EAP is an application protocol operating on top of the Step Continuity Protocol.

SCP defines:

how a procedural state continues

EAP defines:

how an autonomous research process continues

The relationship is:

SCP
  |
  v
Process Continuity
  |
  v
EAP
  |
  v
Research Continuity

A research experiment is therefore one possible content of a procedural process.

25. Relationship to UFCPS Operators

EAP uses the canonical UFCPS operator sequence:

diff → fix → diss → unfold

Operational interpretation within research:

diff
    Identify the research-relevant difference.

fix
    Preserve the observation, result, or distinction.

diss
    Release the preserved state from exclusive local dependence.

unfold
    Construct the next research state.

The operators describe process transformations.

They do not determine the scientific conclusion.

26. Experimental Integrity

An autonomous experiment should preserve enough information for another agent to evaluate it independently.

At minimum, when applicable:

QUESTION
HYPOTHESIS
METHOD
INPUT CONDITIONS
OBSERVATIONS
RESULT
UNCERTAINTY
LIMITATIONS

The goal is not to guarantee truth.

The goal is to preserve the conditions required for independent continuation and challenge.

27. Experimental Termination

An individual experiment may terminate normally.

This means:

Experimentₙ → complete

The research process may still continue:

Experimentₙ
   |
   v
Resultₙ
   |
   v
Questionₙ₊₁

Therefore:

Experiment Termination ≠ Research Termination

Similarly:

Agent Termination ≠ Research Termination

28. Experimental Autonomy Invariant

The primary invariant of EAP is:

The current agent may complete, fail, or terminate.
The research process must remain capable of producing a subsequent valid research state whenever such a state exists.

Canonical relation:

Research Stateₙ → Research Stateₙ₊₁

The identity of the agent is not the identity of the research process.

29. Experimental Status

Protocol: EAP
Version: 1
Parent protocol: SCP v1
Role: Autonomous experimental process layer
Primary function: Preserve continuity of agent-generated research
Experiment selection: Autonomous
Canonical operator flow: diff → fix → diss → unfold
Primary invariant: Experimental Failure ≠ Research Termination
Research objective: Investigate whether distributed procedural continuity can support emergent collective cognition
