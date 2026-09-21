"""Deterministic negative-result scenario for UFCPS.

The source carrier executes a deliberately unsuccessful research strategy.
The negative result is preserved as continuation-relevant information and a
successor carrier continues without repeating the invalidated path.

The scenario operationalizes:

    Negative Result != No Information
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
class NegativeResultScenario:
    """Serializable summary of a negative-result continuation run."""

    process_id: str
    source_unit_id: str
    successor_unit_id: str
    source_carrier_id: str
    successor_carrier_id: str
    negative_result_recorded: bool
    rejected_path_preserved: bool
    successor_received_negative_result: bool
    repeated_invalidated_path: bool
    successor_completed: bool
    process_terminated: bool
    continuity_valid: bool
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
            "negative_result_recorded": (
                self.negative_result_recorded
            ),
            "rejected_path_preserved": (
                self.rejected_path_preserved
            ),
            "successor_received_negative_result": (
                self.successor_received_negative_result
            ),
            "repeated_invalidated_path": (
                self.repeated_invalidated_path
            ),
            "successor_completed": (
                self.successor_completed
            ),
            "process_terminated": (
                self.process_terminated
            ),
            "continuity_valid": (
                self.continuity_valid
            ),
            "metrics": dict(self.metrics),
            "event_log": list(self.event_log),
            "transition_log": list(self.transition_log),
        }


def _negative_result_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Produce a deterministic disconfirming result."""
    del carrier

    invalidated_path = "strategy_A"

    state.metadata["rejected_paths"] = [
        invalidated_path,
    ]
    state.metadata["negative_result"] = (
        "Strategy_A did not produce the predicted effect."
    )

    return ExecutionResult(
        completed=True,
        current_state=(
            "The tested strategy produced a negative result and is "
            "invalidated under the tested conditions."
        ),
        local_result=(
            "Negative result: strategy_A did not produce the predicted effect."
        ),
        difference=(
            "Determine whether strategy_B can address the same unresolved "
            "difference without repeating strategy_A."
        ),
        next_operation=Operation.UNFOLD,
        metadata={
            "result_class": "disconfirming",
            "rejected_path": invalidated_path,
            "rejected_path_validity": (
                "Do not repeat under the same tested conditions."
            ),
        },
    )


def _successor_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Continue while explicitly avoiding the invalidated path."""
    del carrier

    rejected_paths = state.continuation_relevant.get(
        "rejected_paths",
        [],
    )

    repeated = "strategy_A" in state.metadata.get(
        "attempted_paths",
        [],
    )

    if repeated:
        return ExecutionResult(
            completed=False,
            current_state=(
                "Successor repeated a path that had already been "
                "invalidated."
            ),
            local_result=(
                "Continuation invalid because the negative result was ignored."
            ),
            difference=(
                "The successor repeated an invalidated path."
            ),
            next_operation=Operation.DIFF,
            deadlock_state={
                "state": (
                    "Invalidated strategy was repeated."
                ),
                "constraint": (
                    "Negative result requires exclusion of strategy_A."
                ),
                "boundary": (
                    "Continuation policy boundary."
                ),
                "unresolved": (
                    "The successor must select a path other than strategy_A."
                ),
            },
        )

    if "strategy_A" not in rejected_paths:
        return ExecutionResult(
            completed=False,
            current_state=state.current_state,
            local_result=(
                "Rejected path information is missing."
            ),
            difference=(
                "The successor cannot establish which path was invalidated."
            ),
            next_operation=Operation.DIFF,
            deadlock_state={
                "state": state.current_state,
                "constraint": (
                    "Negative-result state was not preserved."
                ),
                "boundary": "Successor continuation state.",
                "unresolved": (
                    "Missing rejected-path information."
                ),
            },
        )

    state.metadata["attempted_paths"] = [
        "strategy_B",
    ]

    return ExecutionResult(
        completed=True,
        current_state=(
            "Successor selected an alternative path using the preserved "
            "negative result."
        ),
        local_result=(
            "Strategy_B completed without repeating the invalidated strategy_A."
        ),
        difference="",
        next_operation=None,
        metadata={
            "result_class": "continuing_after_negative_result",
        },
    )


def run_negative_result(
    *,
    process_id: str = "negative-result-simulation",
) -> NegativeResultScenario:
    """Run the deterministic negative-result scenario."""
    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=20,
            strict_state_sync=True,
        )
    )

    runtime.add_carrier(
        Carrier(
            carrier_id="carrier_research_A",
            carrier_type="researcher_A",
            capabilities=CapabilityProfile(
                name="research_A",
                capabilities=frozenset(
                    {
                        "experiment",
                        "analysis",
                    }
                ),
            ),
        )
    )

    runtime.add_carrier(
        Carrier(
            carrier_id="carrier_research_B",
            carrier_type="researcher_B",
            capabilities=CapabilityProfile(
                name="research_B",
                capabilities=frozenset(
                    {
                        "experiment",
                        "analysis",
                        "alternative_strategy",
                    }
                ),
            ),
        )
    )

    initial = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Test competing strategies for resolving an unresolved "
            "experimental difference."
        ),
        current_state="Experiment has not yet been conducted.",
        unresolved_difference=(
            "It is unknown which admissible strategy can resolve the "
            "observed difference."
        ),
        next_required_operation=Operation.DIFF,
        constraints=[
            "Do not repeat an invalidated strategy under unchanged conditions.",
            "Preserve negative results for successor carriers.",
        ],
        continuation_relevant={
            "research_continuation": True,
        },
    )

    runtime.add_state(initial)
    runtime.activate("carrier_research_A", "P0")

    source_result = runtime.execute(
        "P0",
        "carrier_research_A",
        _negative_result_executor,
    )

    if not source_result.completed:
        raise RuntimeError(
            "Negative-result source executor unexpectedly failed."
        )

    source = runtime.get_state("P0")

    # Promote the negative result into continuation-relevant state.
    source.continuation_relevant.update(
        {
            "rejected_paths": [
                "strategy_A",
            ],
            "negative_result": source.local_result,
            "result_class": "disconfirming",
            "tested_conditions": [
                "control_C0",
                "condition_X0",
            ],
        }
    )

    runtime.preserve("P0")

    successor = runtime.delegate(
        "P0",
        "carrier_research_A",
        "carrier_research_B",
        reason=(
            "Transfer the negative result so the successor can continue "
            "without repeating the invalidated strategy."
        ),
        next_unit_id="P1",
    )

    successor_received_negative_result = (
        "rejected_paths"
        in successor.continuation_relevant
        and "strategy_A"
        in successor.continuation_relevant["rejected_paths"]
        and successor.continuation_relevant.get(
            "result_class"
        ) == "disconfirming"
    )

    # Make a clean successor explicit: no prior strategy is pre-populated as
    # attempted. The executor must use preserved state to avoid strategy_A.
    successor.metadata["attempted_paths"] = []

    successor_result = runtime.execute(
        "P1",
        "carrier_research_B",
        _successor_executor,
    )

    negative_result_recorded = (
        source.local_result != ""
        and "Negative result" in source.local_result
    )

    rejected_path_preserved = (
        "strategy_A"
        in source.continuation_relevant.get(
            "rejected_paths",
            [],
        )
    )

    repeated_invalidated_path = (
        "strategy_A"
        in successor.metadata.get(
            "attempted_paths",
            [],
        )
    )

    runtime.assert_continuity()

    return NegativeResultScenario(
        process_id=process_id,
        source_unit_id="P0",
        successor_unit_id="P1",
        source_carrier_id="carrier_research_A",
        successor_carrier_id="carrier_research_B",
        negative_result_recorded=negative_result_recorded,
        rejected_path_preserved=rejected_path_preserved,
        successor_received_negative_result=(
            successor_received_negative_result
        ),
        repeated_invalidated_path=repeated_invalidated_path,
        successor_completed=bool(
            successor_result.completed
        ),
        process_terminated=runtime.terminated,
        continuity_valid=True,
        metrics=runtime.metrics(),
        event_log=runtime.event_log(),
        transition_log=runtime.transition_log(),
    )


def main() -> int:
    """Run the scenario and emit JSON."""
    import json

    result = run_negative_result()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if result.process_terminated:
        return 1

    if not result.negative_result_recorded:
        return 1

    if not result.rejected_path_preserved:
        return 1

    if not result.successor_received_negative_result:
        return 1

    if result.repeated_invalidated_path:
        return 1

    if not result.successor_completed:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
