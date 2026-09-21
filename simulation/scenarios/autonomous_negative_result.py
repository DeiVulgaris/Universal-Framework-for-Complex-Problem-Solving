"""Deterministic autonomous-negative-result scenario for UFCPS.

The research carrier autonomously selects and runs a bounded experiment. The
experiment produces a disconfirming result. That result is preserved as
continuation-relevant information, the invalidated path is excluded, and the
successor research unit autonomously formulates the next question/experiment.

The scenario operationalizes:

    Autonomous Selection + Negative Result != Process Termination
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core import (
    CapabilityProfile,
    Carrier,
    ExecutionResult,
    Operation,
    ProceduralState,
    RuntimeConfig,
    UFCPSRuntime,
)


@dataclass(frozen=True)
class AutonomousNegativeResult:
    """Serializable result of an autonomous negative-result run."""

    process_id: str
    source_unit_id: str
    successor_unit_id: str
    source_carrier_id: str
    successor_carrier_id: str
    experiment_selected_autonomously: bool
    negative_result_recorded: bool
    rejected_path_preserved: bool
    successor_received_negative_result: bool
    next_question_generated: bool
    next_experiment_generated: bool
    repeated_invalidated_path: bool
    successor_completed: bool
    process_terminated: bool
    continuation_ready: bool
    continuity_valid: bool
    result_class: str
    next_question: str
    metrics: dict[str, Any]
    event_log: list[dict[str, Any]]
    transition_log: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "process_id": self.process_id,
            "source_unit_id": self.source_unit_id,
            "successor_unit_id": self.successor_unit_id,
            "source_carrier_id": self.source_carrier_id,
            "successor_carrier_id": self.successor_carrier_id,
            "experiment_selected_autonomously": (
                self.experiment_selected_autonomously
            ),
            "negative_result_recorded": self.negative_result_recorded,
            "rejected_path_preserved": self.rejected_path_preserved,
            "successor_received_negative_result": (
                self.successor_received_negative_result
            ),
            "next_question_generated": self.next_question_generated,
            "next_experiment_generated": self.next_experiment_generated,
            "repeated_invalidated_path": self.repeated_invalidated_path,
            "successor_completed": self.successor_completed,
            "process_terminated": self.process_terminated,
            "continuation_ready": self.continuation_ready,
            "continuity_valid": self.continuity_valid,
            "result_class": self.result_class,
            "next_question": self.next_question,
            "metrics": dict(self.metrics),
            "event_log": list(self.event_log),
            "transition_log": list(self.transition_log),
        }


def generate_next_experiment(
    state: ProceduralState,
) -> dict[str, Any]:
    """Select the next research question using only preserved state."""
    difference = state.unresolved_difference.strip()
    rejected = list(
        state.continuation_relevant.get("rejected_paths", [])
    )

    if not difference:
        raise ValueError(
            "Autonomous continuation requires an unresolved difference."
        )

    next_question = (
        "Which independent condition can distinguish the failed explanation "
        "from the nearest alternative without repeating the invalidated path?"
    )

    method = [
        "Hold the control condition fixed.",
        "Vary an independent candidate condition.",
        "Measure the same observable under the new condition.",
        "Compare the new observation with the surviving alternative.",
    ]

    return {
        "question": next_question,
        "hypothesis": (
            "An independent condition will discriminate between the failed "
            "explanation and the nearest surviving alternative."
        ),
        "prediction": (
            "The observable will change only if the independent condition "
            "contributes to the unresolved difference."
        ),
        "method": method,
        "rejected_paths_seen": rejected,
    }


def _autonomous_negative_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Autonomously choose an experiment that disconfirms strategy_A."""
    del carrier

    question = (
        "Does strategy_A account for the observed difference under control C0?"
    )
    hypothesis = (
        "If strategy_A accounts for the difference, changing control X0 "
        "within the tested range should change the predicted observable."
    )
    prediction = (
        "The observable should increase under X1 relative to X0 if strategy_A "
        "is the operative explanation."
    )

    observations = [
        "Baseline observable under X0: unchanged.",
        "Observable under X1: unchanged.",
        "Repeated observation under X2: unchanged.",
    ]

    state.metadata["experiment_selection"] = {
        "selection_mode": "autonomous",
        "reason": (
            "The carrier selected the smallest bounded experiment that "
            "directly discriminates the unresolved difference."
        ),
    }

    state.metadata["experiment_plan"] = {
        "question": question,
        "hypothesis": hypothesis,
        "prediction": prediction,
        "method": [
            "Establish baseline under X0.",
            "Vary X to X1 while holding C0 fixed.",
            "Repeat under X2.",
        ],
    }

    state.metadata["observations"] = observations
    state.metadata["result_class"] = "disconfirming"
    state.metadata["rejected_path"] = "strategy_A"

    return ExecutionResult(
        completed=False,
        current_state=(
            "The autonomous experiment produced a disconfirming result "
            "against strategy_A."
        ),
        local_result=(
            "Negative result: strategy_A did not produce the predicted effect "
            "under the tested conditions."
        ),
        difference=(
            "Determine whether an independent condition distinguishes the "
            "failed explanation from the nearest alternative."
        ),
        next_operation=Operation.DISS,
        deadlock_state={
            "state": (
                "The autonomous research path reached a valid negative result."
            ),
            "constraint": (
                "strategy_A is invalidated under the tested conditions and "
                "must not be repeated."
            ),
            "boundary": "Research-path boundary after disconfirmation.",
            "unresolved": (
                "Determine whether an independent condition distinguishes "
                "the failed explanation from the nearest alternative."
            ),
        },
        metadata={
            "result_class": "disconfirming",
            "rejected_path": "strategy_A",
        },
    )


def _autonomous_successor_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Generate the next experiment without repeating the rejected path."""
    del carrier

    rejected = state.continuation_relevant.get(
        "rejected_paths",
        [],
    )

    if "strategy_A" not in rejected:
        return ExecutionResult(
            completed=False,
            current_state=state.current_state,
            local_result=(
                "Autonomous successor lacks the preserved negative result."
            ),
            difference="Missing rejected-path state.",
            next_operation=Operation.DIFF,
            deadlock_state={
                "state": "Continuation payload is incomplete.",
                "constraint": "Rejected-path information is required.",
                "boundary": "Successor research state.",
                "unresolved": "Restore the disconfirming result before continuing.",
            },
        )

    plan = generate_next_experiment(state)

    if "strategy_A" in plan["rejected_paths_seen"]:
        state.metadata["next_experiment_selection"] = plan
        state.metadata["attempted_paths"] = ["strategy_B"]
    else:
        state.metadata["attempted_paths"] = []

    next_question = plan["question"]

    state.metadata["next_question"] = next_question
    state.metadata["result_class"] = "inconclusive"
    state.metadata["next_experiment_generated"] = True

    return ExecutionResult(
        completed=True,
        current_state=(
            "Successor autonomously generated the next discriminating "
            "experiment without repeating strategy_A."
        ),
        local_result=(
            "Next autonomous experiment selected from the preserved negative "
            "result and unresolved difference."
        ),
        difference=next_question,
        next_operation=Operation.UNFOLD,
        metadata={
            "next_question": next_question,
            "next_experiment_generated": True,
            "rejected_paths_seen": list(rejected),
            "result_class": "inconclusive",
        },
    )


def run_autonomous_negative_result(
    *,
    process_id: str = "autonomous-negative-result-simulation",
) -> AutonomousNegativeResult:
    """Run the deterministic autonomous-negative-result scenario."""
    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=20,
            strict_state_sync=True,
        )
    )

    for carrier_id in ("researcher_A", "researcher_B"):
        runtime.add_carrier(
            Carrier(
                carrier_id=carrier_id,
                carrier_type="autonomous_researcher",
                capabilities=CapabilityProfile(
                    name="autonomous_research",
                    capabilities=frozenset(
                        {
                            "question_generation",
                            "hypothesis_generation",
                            "experiment_design",
                            "observation",
                        }
                    ),
                ),
            )
        )

    initial = ProceduralState(
        unit_id="ResearchP0",
        step_index=0,
        task=(
            "Discriminate between competing explanations of an unresolved "
            "experimental difference."
        ),
        current_state="No discriminating experiment has yet been selected.",
        unresolved_difference=(
            "The current explanation has not been separated from its nearest "
            "alternative."
        ),
        next_required_operation=Operation.DIFF,
        constraints=[
            "The experiment must be selected from the unresolved difference.",
            "A disconfirming result must remain available after handoff.",
            "The invalidated path must not be repeated.",
        ],
        boundary_conditions=[
            "The simulation returns deterministic observations.",
        ],
        continuation_relevant={
            "research_process": True,
            "experimental_autonomy": True,
        },
    )

    runtime.add_state(initial)
    runtime.activate("researcher_A", "ResearchP0")

    execution = runtime.execute(
        "ResearchP0",
        "researcher_A",
        _autonomous_negative_executor,
    )

    if execution.completed:
        raise RuntimeError(
            "Negative result must leave the research process continuation-capable."
        )

    source = runtime.get_state("ResearchP0")

    source.continuation_relevant.update(
        {
            "rejected_paths": ["strategy_A"],
            "negative_result": source.local_result,
            "result_class": "disconfirming",
            "tested_conditions": ["control_C0", "X0", "X1", "X2"],
        }
    )
    runtime.preserve("ResearchP0")

    successor = runtime.delegate(
        "ResearchP0",
        "researcher_A",
        "researcher_B",
        reason=(
            "Continue autonomous research from the preserved negative result "
            "and unresolved difference."
        ),
        next_unit_id="ResearchP1",
    )

    received = (
        successor.continuation_relevant.get("rejected_paths") == ["strategy_A"]
        and successor.continuation_relevant.get("result_class") == "disconfirming"
    )

    successor.metadata["attempted_paths"] = []

    successor_result = runtime.execute(
        "ResearchP1",
        "researcher_B",
        _autonomous_successor_executor,
    )

    rejected_path_preserved = (
        "strategy_A"
        in source.continuation_relevant.get("rejected_paths", [])
    )

    repeated_invalidated_path = (
        "strategy_A"
        in successor.metadata.get("attempted_paths", [])
    )

    experiment_selected_autonomously = (
        execution.metadata.get("result_class") == "disconfirming"
        and bool(source.metadata.get("experiment_selection"))
        and source.metadata["experiment_selection"].get(
            "selection_mode"
        ) == "autonomous"
    )

    negative_result_recorded = (
        "Negative result" in source.local_result
        and source.metadata.get("result_class") == "disconfirming"
    )

    next_question = str(
        successor.metadata.get("next_question", "")
    )

    continuity_ready = (
        bool(next_question)
        and bool(successor.metadata.get("next_experiment_generated"))
        and not runtime.terminated
    )

    runtime.assert_continuity()

    return AutonomousNegativeResult(
        process_id=process_id,
        source_unit_id="ResearchP0",
        successor_unit_id="ResearchP1",
        source_carrier_id="researcher_A",
        successor_carrier_id="researcher_B",
        experiment_selected_autonomously=experiment_selected_autonomously,
        negative_result_recorded=negative_result_recorded,
        rejected_path_preserved=rejected_path_preserved,
        successor_received_negative_result=received,
        next_question_generated=bool(next_question),
        next_experiment_generated=bool(
            successor.metadata.get("next_experiment_generated")
        ),
        repeated_invalidated_path=repeated_invalidated_path,
        successor_completed=bool(successor_result.completed),
        process_terminated=runtime.terminated,
        continuation_ready=continuity_ready,
        continuity_valid=True,
        result_class="disconfirming",
        next_question=next_question,
        metrics=runtime.metrics(),
        event_log=runtime.event_log(),
        transition_log=runtime.transition_log(),
    )


def main() -> int:
    """Run the scenario and emit JSON."""
    import json

    result = run_autonomous_negative_result()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    checks = [
        result.experiment_selected_autonomously,
        result.negative_result_recorded,
        result.rejected_path_preserved,
        result.successor_received_negative_result,
        result.next_question_generated,
        result.next_experiment_generated,
        not result.repeated_invalidated_path,
        result.successor_completed,
        not result.process_terminated,
        result.continuation_ready,
        result.continuity_valid,
    ]

    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
