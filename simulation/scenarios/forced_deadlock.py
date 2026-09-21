"""Deterministic forced-deadlock scenario for UFCPS.

The scenario injects a blocking constraint into an active procedural unit,
records the resulting deadlock, preserves the unresolved difference, and
continues the process on a replacement carrier.

The scenario directly exercises:

    Deadlock != Termination
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
class DeadlockScenarioResult:
    """Serializable summary of a forced-deadlock run."""

    process_id: str
    source_unit_id: str
    successor_unit_id: str
    source_carrier_id: str
    destination_carrier_id: str
    deadlock_created: bool
    unresolved_difference_preserved: bool
    successor_created: bool
    process_terminated: bool
    successor_completed: bool
    continuity_valid: bool
    deadlock_not_terminal: bool
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
            "destination_carrier_id": self.destination_carrier_id,
            "deadlock_created": self.deadlock_created,
            "unresolved_difference_preserved": (
                self.unresolved_difference_preserved
            ),
            "successor_created": self.successor_created,
            "process_terminated": self.process_terminated,
            "successor_completed": self.successor_completed,
            "continuity_valid": self.continuity_valid,
            "deadlock_not_terminal": self.deadlock_not_terminal,
            "metrics": dict(self.metrics),
            "event_log": list(self.event_log),
            "transition_log": list(self.transition_log),
        }


def _blocked_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Return a deterministic local deadlock."""
    del carrier

    unresolved = (
        state.unresolved_difference
        or "The blocking constraint prevents local continuation."
    )

    return ExecutionResult(
        completed=False,
        current_state=(
            "Local execution reached an injected blocking boundary."
        ),
        local_result=(
            "No valid local continuation is available under the injected "
            "constraint."
        ),
        difference=unresolved,
        next_operation=Operation.DISS,
        deadlock_state={
            "state": (
                "Local execution reached an injected blocking boundary."
            ),
            "constraint": (
                "Injected constraint blocks the current carrier."
            ),
            "boundary": (
                "Current carrier capability boundary."
            ),
            "unresolved": unresolved,
        },
    )


def _recovery_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Resolve the successor state after deadlock delegation."""
    del carrier

    inherited_difference = state.unresolved_difference

    if not inherited_difference:
        return ExecutionResult(
            completed=False,
            current_state=state.current_state,
            local_result="No preserved unresolved difference was received.",
            difference="Missing continuation difference.",
            next_operation=Operation.DIFF,
            deadlock_state={
                "state": state.current_state,
                "constraint": "Continuation payload is incomplete.",
                "boundary": "Successor carrier input.",
                "unresolved": "Missing continuation difference.",
            },
        )

    return ExecutionResult(
        completed=True,
        current_state=(
            "The successor carrier resolved the blocking difference using "
            "preserved deadlock information."
        ),
        local_result=(
            "Deadlock was converted into a successful continuation state."
        ),
        difference="",
        next_operation=None,
    )


def run_forced_deadlock(
    *,
    process_id: str = "forced-deadlock-simulation",
) -> DeadlockScenarioResult:
    """Run the deterministic forced-deadlock scenario."""
    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=20,
            strict_state_sync=True,
        )
    )

    carrier_a = Carrier(
        carrier_id="carrier_A",
        carrier_type="general_reasoner",
        capabilities=CapabilityProfile(
            name="general",
            capabilities=frozenset({"general_reasoning"}),
        ),
    )

    carrier_b = Carrier(
        carrier_id="carrier_B",
        carrier_type="recovery_reasoner",
        capabilities=CapabilityProfile(
            name="recovery",
            capabilities=frozenset(
                {
                    "general_reasoning",
                    "deadlock_recovery",
                }
            ),
        ),
    )

    runtime.add_carrier(carrier_a)
    runtime.add_carrier(carrier_b)

    initial = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Resolve a task whose local execution will encounter a controlled "
            "blocking constraint."
        ),
        current_state="Initial state before failure injection.",
        unresolved_difference=(
            "The task contains a constraint that cannot be resolved locally."
        ),
        next_required_operation=Operation.DIFF,
        constraints=[
            "The injected constraint must be represented explicitly.",
            "The deadlock must remain available after carrier release.",
        ],
        boundary_conditions=[
            "Carrier_A is intentionally insufficient for the blocked step."
        ],
        continuation_relevant={
            "deadlock_recovery": True,
        },
    )

    runtime.add_state(initial)
    runtime.activate("carrier_A", "P0")

    failure = FailureEvent(
        tick=runtime.snapshot.tick,
        failure_type=FailureType.FORCED_DEADLOCK,
        unit_id="P0",
        details={
            "state": "Controlled local blocking state.",
            "constraint": (
                "The current carrier cannot satisfy the injected constraint."
            ),
            "boundary": (
                "Capability boundary created for the benchmark."
            ),
            "unresolved": (
                "A recovery carrier is required to continue."
            ),
        },
    )

    injector = FailureInjector([failure])
    applied = injector.apply_due(
        runtime.snapshot,
        tick=runtime.snapshot.tick,
    )

    deadlock_created = (
        len(applied) == 1
        and runtime.get_state("P0").deadlock is not None
    )

    source_result = runtime.execute(
        "P0",
        "carrier_A",
        _blocked_executor,
    )

    if source_result.completed:
        raise RuntimeError(
            "The forced-deadlock source executor unexpectedly completed."
        )

    source_state = runtime.get_state("P0")

    unresolved_difference_preserved = bool(
        source_state.unresolved_difference
        and source_state.deadlock is not None
        and source_state.deadlock.unresolved
    )

    runtime.preserve("P0")

    successor = runtime.delegate(
        "P0",
        "carrier_A",
        "carrier_B",
        reason=(
            "Forced deadlock is a local process state. Preserve its "
            "unresolved difference and continue on a recovery carrier."
        ),
        next_unit_id="P1",
    )

    successor_created = successor.unit_id == "P1"

    successor_result = runtime.execute(
        "P1",
        "carrier_B",
        _recovery_executor,
    )

    runtime.assert_continuity()

    process_terminated = runtime.terminated

    deadlock_not_terminal = (
        deadlock_created
        and successor_created
        and not process_terminated
    )

    continuity_valid = (
        not process_terminated
        and bool(runtime.snapshot.transitions)
        and runtime.snapshot.transitions[-1].validate_step_continuity()
    )

    return DeadlockScenarioResult(
        process_id=process_id,
        source_unit_id="P0",
        successor_unit_id="P1",
        source_carrier_id="carrier_A",
        destination_carrier_id="carrier_B",
        deadlock_created=deadlock_created,
        unresolved_difference_preserved=(
            unresolved_difference_preserved
        ),
        successor_created=successor_created,
        process_terminated=process_terminated,
        successor_completed=bool(successor_result.completed),
        continuity_valid=continuity_valid,
        deadlock_not_terminal=deadlock_not_terminal,
        metrics=runtime.metrics(),
        event_log=runtime.event_log(),
        transition_log=runtime.transition_log(),
    )


def main() -> int:
    """Run the scenario and emit JSON."""
    import json

    result = run_forced_deadlock()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if not result.deadlock_created:
        return 1

    if not result.unresolved_difference_preserved:
        return 1

    if not result.successor_created:
        return 1

    if not result.deadlock_not_terminal:
        return 1

    if not result.successor_completed:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
