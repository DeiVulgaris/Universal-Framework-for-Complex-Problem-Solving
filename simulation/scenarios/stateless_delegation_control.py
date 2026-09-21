"""Controlled comparison of stateless and stateful delegation.

The scenario runs the same continuation task under two conditions:

- stateless delegation: the successor receives only a task description;
- stateful delegation: the successor receives continuation-relevant state.

The scenario measures whether explicit continuation state reduces repeated
work and improves successful process continuation.

The comparison is descriptive. It does not assume in advance which condition
will perform better.
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
class DelegationConditionResult:
    """Result for one delegation condition."""

    condition: str
    successor_completed: bool
    repeated_work: int
    state_loss_fields: tuple[str, ...]
    continuation_state_available: bool
    process_terminated: bool
    unresolved_difference_after_handoff: str
    local_result_after_handoff: str


@dataclass(frozen=True)
class StatelessDelegationResult:
    """Serializable comparison of stateless and stateful delegation."""

    process_id: str
    conditions: tuple[DelegationConditionResult, ...]
    stateful_completion: bool
    stateless_completion: bool
    stateful_repeated_work: int
    stateless_repeated_work: int
    stateful_state_loss: tuple[str, ...]
    stateless_state_loss: tuple[str, ...]
    continuation_state_difference_observed: bool
    process_terminated: bool
    continuity_valid: bool
    metrics: dict[str, Any]
    event_log: list[dict[str, Any]]
    transition_log: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable comparison."""
        return {
            "process_id": self.process_id,
            "conditions": [
                {
                    "condition": item.condition,
                    "successor_completed": item.successor_completed,
                    "repeated_work": item.repeated_work,
                    "state_loss_fields": list(item.state_loss_fields),
                    "continuation_state_available": (
                        item.continuation_state_available
                    ),
                    "process_terminated": item.process_terminated,
                    "unresolved_difference_after_handoff": (
                        item.unresolved_difference_after_handoff
                    ),
                    "local_result_after_handoff": (
                        item.local_result_after_handoff
                    ),
                }
                for item in self.conditions
            ],
            "stateful_completion": self.stateful_completion,
            "stateless_completion": self.stateless_completion,
            "stateful_repeated_work": self.stateful_repeated_work,
            "stateless_repeated_work": self.stateless_repeated_work,
            "stateful_state_loss": list(self.stateful_state_loss),
            "stateless_state_loss": list(self.stateless_state_loss),
            "continuation_state_difference_observed": (
                self.continuation_state_difference_observed
            ),
            "process_terminated": self.process_terminated,
            "continuity_valid": self.continuity_valid,
            "metrics": dict(self.metrics),
            "event_log": list(self.event_log),
            "transition_log": list(self.transition_log),
        }


def _source_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Create a deterministic partial result requiring continuation."""
    del carrier

    return ExecutionResult(
        completed=False,
        current_state=(
            "Stage A completed. Stage B requires the preserved search "
            "boundary and rejected alternatives."
        ),
        local_result=(
            "Stage A completed; two candidate paths were tested and rejected."
        ),
        difference=(
            "Continue Stage B using the preserved search boundary and "
            "rejected alternatives."
        ),
        next_operation=Operation.DISS,
        deadlock_state={
            "state": (
                "Stage A completed before Stage B."
            ),
            "constraint": (
                "Stage B requires continuation-relevant search state."
            ),
            "boundary": (
                "Source carrier execution boundary."
            ),
            "unresolved": (
                "Continue Stage B using preserved search information."
            ),
        },
        metadata={
            "tested_candidates": [
                "candidate_1",
                "candidate_2",
            ],
            "search_boundary": "candidate_3 and beyond",
        },
    )


def _stateful_successor_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Continue using explicitly preserved continuation state."""
    del carrier

    candidates = state.continuation_relevant.get(
        "tested_candidates",
        [],
    )
    boundary = state.continuation_relevant.get(
        "search_boundary",
        "",
    )

    if (
        not isinstance(candidates, list)
        or not candidates
        or not boundary
    ):
        return ExecutionResult(
            completed=False,
            current_state=state.current_state,
            local_result=(
                "Required continuation-relevant state was not preserved."
            ),
            difference=(
                "Missing tested candidates or search boundary."
            ),
            next_operation=Operation.DIFF,
            deadlock_state={
                "state": state.current_state,
                "constraint": (
                    "Continuation-relevant search state is absent."
                ),
                "boundary": "Successor input boundary.",
                "unresolved": (
                    "Missing tested candidates or search boundary."
                ),
            },
        )

    state.metadata["repeated_work"] = 0

    return ExecutionResult(
        completed=True,
        current_state=(
            f"Stage B resumed from preserved boundary {boundary}."
        ),
        local_result=(
            "Successor continued without repeating the rejected candidates."
        ),
        difference="",
        next_operation=None,
    )


def _stateless_successor_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Continue from a task description without preserved local search state."""
    del carrier

    # The successor has to repeat the two known rejected candidates before it
    # can safely continue to the next boundary.
    state.metadata["repeated_work"] = 2

    return ExecutionResult(
        completed=True,
        current_state=(
            "Stage B completed after reconstructing missing search context."
        ),
        local_result=(
            "Successor completed, but two previously rejected candidates "
            "had to be evaluated again."
        ),
        difference="",
        next_operation=None,
    )


def _new_runtime(
    process_id: str,
) -> UFCPSRuntime:
    """Create a runtime containing the two carriers used by both conditions."""
    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=20,
            strict_state_sync=True,
        )
    )

    runtime.add_carrier(
        Carrier(
            carrier_id="carrier_source",
            carrier_type="general_reasoner",
            capabilities=CapabilityProfile(
                name="general",
                capabilities=frozenset(
                    {
                        "general_reasoning",
                        "search",
                    }
                ),
            ),
        )
    )

    runtime.add_carrier(
        Carrier(
            carrier_id="carrier_successor",
            carrier_type="continuation_reasoner",
            capabilities=CapabilityProfile(
                name="continuation",
                capabilities=frozenset(
                    {
                        "general_reasoning",
                        "search",
                        "continuation",
                    }
                ),
            ),
        )
    )

    return runtime


def _run_stateful_condition(
    process_id: str,
) -> tuple[DelegationConditionResult, UFCPSRuntime]:
    """Run the stateful delegation condition."""
    runtime = _new_runtime(process_id)

    state = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Complete Stage B while avoiding previously rejected candidates."
        ),
        current_state="Initial search state.",
        unresolved_difference="Stage B requires preserved search context.",
        next_required_operation=Operation.DIFF,
        constraints=[
            "Do not repeat rejected candidates when continuation state is available."
        ],
        continuation_relevant={},
    )

    runtime.add_state(state)
    runtime.activate("carrier_source", "P0")

    source_result = runtime.execute(
        "P0",
        "carrier_source",
        _source_executor,
    )

    if source_result.completed:
        raise RuntimeError(
            "Stateful source condition unexpectedly completed locally."
        )

    source_state = runtime.get_state("P0")

    # Preserve the local execution metadata as continuation-relevant state.
    source_state.continuation_relevant.update(
        {
            "tested_candidates": [
                "candidate_1",
                "candidate_2",
            ],
            "search_boundary": "candidate_3 and beyond",
        }
    )

    runtime.preserve("P0")

    successor = runtime.delegate(
        "P0",
        "carrier_source",
        "carrier_successor",
        reason=(
            "Transfer continuation-relevant search state so the successor "
            "can continue without repeating rejected work."
        ),
        next_unit_id="P1",
    )

    successor_result = runtime.execute(
        successor.unit_id,
        "carrier_successor",
        _stateful_successor_executor,
    )

    state_loss = tuple(
        field
        for field in (
            "task",
            "current_state",
            "local_result",
            "unresolved_difference",
            "continuation_relevant",
        )
        if field not in successor.preserve()
    )

    repeated_work = int(
        successor.metadata.get("repeated_work", 0)
    )

    transition = runtime.snapshot.transitions[-1]
    continuation_available = (
        transition.continuation is not None
        and transition.continuation.has_required_information()
    )

    runtime.assert_continuity()

    return (
        DelegationConditionResult(
            condition="stateful",
            successor_completed=bool(successor_result.completed),
            repeated_work=repeated_work,
            state_loss_fields=state_loss,
            continuation_state_available=continuation_available,
            process_terminated=runtime.terminated,
            unresolved_difference_after_handoff=(
                successor.unresolved_difference
            ),
            local_result_after_handoff=successor.local_result,
        ),
        runtime,
    )


def _run_stateless_condition(
    process_id: str,
) -> tuple[DelegationConditionResult, UFCPSRuntime]:
    """Run the stateless delegation condition."""
    runtime = _new_runtime(process_id)

    state = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Complete Stage B while avoiding previously rejected candidates."
        ),
        current_state="Initial search state.",
        unresolved_difference="Stage B requires preserved search context.",
        next_required_operation=Operation.DIFF,
        constraints=[
            "The successor receives only a task description."
        ],
        continuation_relevant={},
    )

    runtime.add_state(state)
    runtime.activate("carrier_source", "P0")

    source_result = runtime.execute(
        "P0",
        "carrier_source",
        _source_executor,
    )

    if source_result.completed:
        raise RuntimeError(
            "Stateless source condition unexpectedly completed locally."
        )

    source_state = runtime.get_state("P0")

    # Deliberately construct a reduced successor state with only task-level
    # information. No tested-candidate list or search boundary is transferred.
    runtime.preserve("P0")

    successor = ProceduralState(
        unit_id="P1",
        step_index=1,
        task=source_state.task,
        current_state="Task description only.",
        unresolved_difference=(
            "Continuation context must be reconstructed from the task."
        ),
        next_required_operation=Operation.DIFF,
        constraints=list(source_state.constraints),
        continuation_relevant={},
        parent_unit_id="P0",
    )

    runtime.snapshot.active_units["P1"] = successor
    runtime.get_carrier("carrier_successor").activate("P1")
    runtime.snapshot.store_state(successor)

    successor_result = runtime.execute(
        "P1",
        "carrier_successor",
        _stateless_successor_executor,
    )

    state_loss = (
        "tested_candidates",
        "search_boundary",
    )

    repeated_work = int(
        successor.metadata.get("repeated_work", 0)
    )

    runtime.assert_continuity()

    return (
        DelegationConditionResult(
            condition="stateless",
            successor_completed=bool(successor_result.completed),
            repeated_work=repeated_work,
            state_loss_fields=state_loss,
            continuation_state_available=False,
            process_terminated=runtime.terminated,
            unresolved_difference_after_handoff=(
                successor.unresolved_difference
            ),
            local_result_after_handoff=successor.local_result,
        ),
        runtime,
    )


def run_stateless_delegation_control(
    *,
    process_id: str = "stateless-delegation-control-simulation",
) -> StatelessDelegationResult:
    """Run and compare the two delegation conditions."""
    stateful_result, stateful_runtime = _run_stateful_condition(
        f"{process_id}-stateful"
    )

    stateless_result, stateless_runtime = _run_stateless_condition(
        f"{process_id}-stateless"
    )

    continuity_valid = (
        stateful_result.continuation_state_available
        and stateful_result.successor_completed
        and stateless_result.successor_completed
        and not stateful_result.process_terminated
        and not stateless_result.process_terminated
    )

    state_difference_observed = (
        stateful_result.repeated_work
        != stateless_result.repeated_work
        or stateful_result.state_loss_fields
        != stateless_result.state_loss_fields
        or (
            stateful_result.continuation_state_available
            != stateless_result.continuation_state_available
        )
    )

    # Merge only process-level accounting from both independent runs.
    metrics = {
        "stateful": stateful_runtime.metrics(),
        "stateless": stateless_runtime.metrics(),
        "repeated_work_difference": (
            stateless_result.repeated_work
            - stateful_result.repeated_work
        ),
    }

    return StatelessDelegationResult(
        process_id=process_id,
        conditions=(
            stateful_result,
            stateless_result,
        ),
        stateful_completion=(
            stateful_result.successor_completed
        ),
        stateless_completion=(
            stateless_result.successor_completed
        ),
        stateful_repeated_work=(
            stateful_result.repeated_work
        ),
        stateless_repeated_work=(
            stateless_result.repeated_work
        ),
        stateful_state_loss=(
            stateful_result.state_loss_fields
        ),
        stateless_state_loss=(
            stateless_result.state_loss_fields
        ),
        continuation_state_difference_observed=(
            state_difference_observed
        ),
        process_terminated=(
            stateful_result.process_terminated
            or stateless_result.process_terminated
        ),
        continuity_valid=continuity_valid,
        metrics=metrics,
        event_log=(
            stateful_runtime.event_log()
            + stateless_runtime.event_log()
        ),
        transition_log=(
            stateful_runtime.transition_log()
            + stateless_runtime.transition_log()
        ),
    )


def main() -> int:
    """Run the comparison and emit JSON."""
    import json

    result = run_stateless_delegation_control()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if not result.stateful_completion:
        return 1

    if not result.stateless_completion:
        return 1

    if not result.continuation_state_difference_observed:
        return 1

    if result.process_terminated:
        return 1

    # The benchmark intentionally does not require stateless delegation to
    # fail. It requires the two state-transfer conditions to remain observable.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
