

The scenario distinguishes a valid process-level termination condition from
local carrier failure.

Condition A is represented by a local carrier failure with a valid successor.
Condition B reaches an explicit global termination condition.

The architectural distinction under test is:

    Local Failure != Process Termination
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
from ..policies import FailureEvent, FailureInjector, FailureType


@dataclass(frozen=True)
class GlobalTerminationResult:
    """Serializable summary of the global-termination test."""

    process_id: str
    local_failure_process_terminated: bool
    local_failure_successor_created: bool
    explicit_termination_process_terminated: bool
    termination_reason_recorded: bool
    local_failure_distinct_from_global_termination: bool
    continuity_valid: bool
    metrics: dict[str, Any]
    event_log: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "process_id": self.process_id,
            "local_failure_process_terminated": (
                self.local_failure_process_terminated
            ),
            "local_failure_successor_created": (
                self.local_failure_successor_created
            ),
            "explicit_termination_process_terminated": (
                self.explicit_termination_process_terminated
            ),
            "termination_reason_recorded": (
                self.termination_reason_recorded
            ),
            "local_failure_distinct_from_global_termination": (
                self.local_failure_distinct_from_global_termination
            ),
            "continuity_valid": self.continuity_valid,
            "metrics": dict(self.metrics),
            "event_log": list(self.event_log),
        }


def _partial_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Produce a partial result before controlled carrier failure."""
    del carrier

    return ExecutionResult(
        completed=True,
        current_state=(
            "A valid partial procedural state exists before carrier failure."
        ),
        local_result=(
            "Partial computation completed; the process still has remaining "
            "work."
        ),
        difference=(
            "A successor carrier can continue the remaining work."
        ),
        next_operation=Operation.DISS,
    )


def run_global_termination(
    *,
    process_id: str = "global-termination-simulation",
) -> GlobalTerminationResult:
    """Run both control conditions."""
    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=30,
            strict_state_sync=True,
        )
    )

    for carrier_id, carrier_type in (
        ("carrier_A", "source_reasoner"),
        ("carrier_B", "successor_reasoner"),
        ("carrier_C", "termination_test_reasoner"),
    ):
        runtime.add_carrier(
            Carrier(
                carrier_id=carrier_id,
                carrier_type=carrier_type,
                capabilities=CapabilityProfile(
                    name=carrier_type,
                    capabilities=frozenset(
                        {
                            "general_reasoning",
                            "continuation",
                        }
                    ),
                ),
            )
        )

    # Condition A: local carrier failure with valid continuation.
    state_a = ProceduralState(
        unit_id="A0",
        step_index=0,
        task="Test local carrier failure with an available successor.",
        current_state="Condition A initial state.",
        unresolved_difference=(
            "Remaining work can be continued by another carrier."
        ),
        next_required_operation=Operation.DIFF,
        continuation_relevant={
            "successor_available": True,
        },
    )

    runtime.add_state(state_a)
    runtime.activate("carrier_A", "A0")

    source_result = runtime.execute(
        "A0",
        "carrier_A",
        _partial_executor,
    )

    if not source_result.completed:
        raise RuntimeError(
            "Condition A source executor unexpectedly failed."
        )

    runtime.preserve("A0")

    # Inject local carrier termination. This is a carrier event, not a process
    # termination request.
    injector = FailureInjector(
        [
            FailureEvent(
                tick=runtime.snapshot.tick,
                failure_type=FailureType.CARRIER_TERMINATION,
                carrier_id="carrier_A",
                unit_id="A0",
            )
        ]
    )

    injector.apply_due(
        runtime.snapshot,
        tick=runtime.snapshot.tick,
    )

    local_failure_process_terminated = runtime.terminated

    successor = runtime.delegate(
        "A0",
        "carrier_A",
        "carrier_B",
        reason=(
            "Condition A: local carrier failed while a valid continuation "
            "remained available."
        ),
        next_unit_id="A1",
    )

    local_failure_successor_created = (
        successor.unit_id == "A1"
        and successor.step_index == 1
        and not runtime.terminated
    )

    # Condition B: explicit process-level termination.
    state_b = ProceduralState(
        unit_id="B0",
        step_index=0,
        task="Test explicit global process termination.",
        current_state="Condition B termination state.",
        unresolved_difference="",
        next_required_operation=Operation.TERMINATE,
        continuation_relevant={
            "global_termination_test": True,
        },
    )

    runtime.add_state(state_b)
    runtime.activate("carrier_C", "B0")

    explicit_reason = (
        "Condition B reached an explicit global termination criterion."
    )

    runtime.terminate(explicit_reason)

    explicit_termination_process_terminated = runtime.terminated

    termination_reason_recorded = (
        runtime.snapshot.termination_reason == explicit_reason
    )

    local_failure_distinct_from_global_termination = (
        not local_failure_process_terminated
        and local_failure_successor_created
        and explicit_termination_process_terminated
        and termination_reason_recorded
    )

    continuity_valid = (
        local_failure_successor_created
        and local_failure_distinct_from_global_termination
    )

    runtime.assert_continuity()

    return GlobalTerminationResult(
        process_id=process_id,
        local_failure_process_terminated=(
            local_failure_process_terminated
        ),
        local_failure_successor_created=(
            local_failure_successor_created
        ),
        explicit_termination_process_terminated=(
            explicit_termination_process_terminated
        ),
        termination_reason_recorded=termination_reason_recorded,
        local_failure_distinct_from_global_termination=(
            local_failure_distinct_from_global_termination
        ),
        continuity_valid=continuity_valid,
        metrics=runtime.metrics(),
        event_log=runtime.event_log(),
    )


def main() -> int:
    """Run the scenario and emit JSON."""
    import json

    result = run_global_termination()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if result.local_failure_process_terminated:
        return 1

    if not result.local_failure_successor_created:
        return 1

    if not result.explicit_termination_process_terminated:
        return 1

    if not result.termination_reason_recorded:
        return 1

    if not result.local_failure_distinct_from_global_termination:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
