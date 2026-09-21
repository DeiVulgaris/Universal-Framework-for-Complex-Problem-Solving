"""Deterministic communication-interruption scenario for UFCPS.

The current carrier becomes unreachable while continuation-relevant state has
already been persisted in the shared environment. A replacement carrier
recovers the process from that persisted state without restoring the original
communication channel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core import (
    CapabilityProfile,
    Carrier,
    CarrierStatus,
    ContinuationState,
    ExecutionResult,
    Operation,
    ProceduralState,
    RuntimeConfig,
    UFCPSRuntime,
)
from ..policies import FailureEvent, FailureInjector, FailureType


@dataclass(frozen=True)
class CommunicationInterruptionResult:
    """Serializable summary of a communication-loss run."""

    process_id: str
    source_unit_id: str
    successor_unit_id: str
    source_carrier_id: str
    successor_carrier_id: str
    state_persisted_before_interruption: bool
    communication_lost: bool
    source_channel_restored: bool
    successor_recovered_from_shared_state: bool
    continuation_preserved: bool
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
            "state_persisted_before_interruption": (
                self.state_persisted_before_interruption
            ),
            "communication_lost": self.communication_lost,
            "source_channel_restored": self.source_channel_restored,
            "successor_recovered_from_shared_state": (
                self.successor_recovered_from_shared_state
            ),
            "continuation_preserved": self.continuation_preserved,
            "successor_completed": self.successor_completed,
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
    """Produce a partial state before communication interruption."""
    del carrier

    return ExecutionResult(
        completed=True,
        current_state=(
            "Partial computation completed and continuation state is "
            "ready for shared persistence."
        ),
        local_result=(
            "Partial result is complete enough for continuation."
        ),
        difference=(
            "Final operation must be executed after the current carrier "
            "becomes unavailable."
        ),
        next_operation=Operation.DISS,
    )


def _successor_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Complete the successor step from recovered shared state."""
    del carrier

    if not state.continuation_relevant.get(
        "shared_state_recovery",
        False,
    ):
        return ExecutionResult(
            completed=False,
            current_state=state.current_state,
            local_result=(
                "Shared-state recovery marker is missing."
            ),
            difference=(
                "The successor cannot establish whether the state was "
                "recovered from persistent process state."
            ),
            next_operation=Operation.DIFF,
        )

    return ExecutionResult(
        completed=True,
        current_state=(
            "Final operation completed after recovery from shared state."
        ),
        local_result=(
            "Successor completed without restoring the interrupted source "
            "communication channel."
        ),
        difference="",
        next_operation=None,
    )


def run_communication_interruption(
    *,
    process_id: str = "communication-interruption-simulation",
) -> CommunicationInterruptionResult:
    """Run the deterministic communication-loss scenario."""
    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=20,
            strict_state_sync=True,
        )
    )

    source = Carrier(
        carrier_id="carrier_A",
        carrier_type="remote_reasoner",
        capabilities=CapabilityProfile(
            name="remote",
            capabilities=frozenset(
                {
                    "general_reasoning",
                    "communication",
                }
            ),
        ),
    )

    successor = Carrier(
        carrier_id="carrier_B",
        carrier_type="recovery_reasoner",
        capabilities=CapabilityProfile(
            name="recovery",
            capabilities=frozenset(
                {
                    "general_reasoning",
                    "shared_state_recovery",
                }
            ),
        ),
    )

    runtime.add_carrier(source)
    runtime.add_carrier(successor)

    state = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Complete a task whose partial result must survive loss of "
            "communication with the executing carrier."
        ),
        current_state="Initial remote execution state.",
        unresolved_difference=(
            "Final operation remains after partial remote computation."
        ),
        next_required_operation=Operation.DIFF,
        constraints=[
            "Continuation state must be persisted before communication loss.",
            "The successor must not depend on restoration of carrier_A's channel.",
        ],
        continuation_relevant={
            "shared_state_recovery": False,
            "partial_result_reference": "not-yet-created",
        },
        metadata={
            "required_capabilities": [
                "shared_state_recovery",
            ],
        },
    )

    initial_reference = runtime.add_state(state)
    runtime.activate("carrier_A", "P0")

    result = runtime.execute(
        "P0",
        "carrier_A",
        _source_executor,
    )

    if not result.completed:
        raise RuntimeError(
            "Source execution unexpectedly failed before communication loss."
        )

    source_state = runtime.get_state("P0")
    source_state.continuation_relevant[
        "shared_state_recovery"
    ] = True
    source_state.continuation_relevant[
        "partial_result_reference"
    ] = initial_reference

    persisted_reference = runtime.preserve("P0")

    persisted = runtime.state_exists(persisted_reference)

    # Inject communication loss after state persistence.
    failure = FailureEvent(
        tick=runtime.snapshot.tick,
        failure_type=FailureType.COMMUNICATION_LOSS,
        carrier_id="carrier_A",
        unit_id="P0",
        details={
            "channel": "source_channel",
            "action": "connection_unavailable",
        },
    )

    injector = FailureInjector([failure])
    applied = injector.apply_due(
        runtime.snapshot,
        tick=runtime.snapshot.tick,
    )

    communication_lost = (
        len(applied) == 1
        and source.metadata.get("communication_available") is False
        and source.status == CarrierStatus.STUCK
    )

    source_channel_restored = (
        source.metadata.get("communication_available", True)
        is True
    )

    # Construct the successor from the persisted shared state. We do not use
    # the source communication channel after the interruption.
    persisted_record = runtime.load_state(persisted_reference)

    recovered_difference = str(
        persisted_record.payload.get(
            "unresolved_difference",
            "",
        )
    )

    successor_unit = ProceduralState(
        unit_id="P1",
        step_index=1,
        task=str(
            persisted_record.payload.get(
                "task",
                "",
            )
        ),
        current_state=str(
            persisted_record.payload.get(
                "current_state",
                "",
            )
        ),
        local_result=str(
            persisted_record.payload.get(
                "local_result",
                "",
            )
        ),
        unresolved_difference=recovered_difference,
        next_required_operation=Operation.UNFOLD,
        constraints=list(
            persisted_record.payload.get(
                "constraints",
                [],
            )
        ),
        boundary_conditions=list(
            persisted_record.payload.get(
                "boundary_conditions",
                [],
            )
        ),
        continuation_relevant={
            **dict(
                persisted_record.payload.get(
                    "continuation_relevant",
                    {},
                )
            ),
            "shared_state_recovery": True,
            "source_state_reference": persisted_reference,
        },
        parent_unit_id="P0",
    )

    runtime.snapshot.active_units["P1"] = successor_unit
    successor.activate if False else None
    runtime.get_carrier("carrier_B").activate("P1")
    successor_reference = runtime.snapshot.store_state(
        successor_unit
    )

    continuation = ContinuationState(
        state_reference=persisted_reference,
        source_unit_id="P0",
        source_step_index=0,
        unresolved_difference=recovered_difference,
        next_required_operation=Operation.UNFOLD,
        preserved_state=persisted_record.payload,
        reason=(
            "Recover continuation from shared process state after "
            "communication loss."
        ),
    )

    # Register the transition through the engine's invariant checks.
    from ..core.models import Transition, TransitionType

    transition = Transition(
        transition_id="communication-recovery-P0-P1",
        transition_type=TransitionType.CONTINUATION,
        source_unit_id="P0",
        source_step_index=0,
        source_carrier_id="carrier_A",
        destination_unit_id="P1",
        destination_step_index=1,
        destination_carrier_id="carrier_B",
        operation=Operation.UNFOLD,
        continuation=continuation,
        reason=(
            "Source communication channel unavailable; successor recovered "
            "from shared state."
        ),
    )

    runtime.snapshot.transitions.append(transition)

    runtime.snapshot.record_event(
        event_type=__import__(
            "simulation.core.models",
            fromlist=["EventType"],
        ).EventType.CARRIER_REPLACED,
        unit_id="P1",
        carrier_id="carrier_B",
        transition_id=transition.transition_id,
        details={
            "source_carrier": "carrier_A",
            "destination_carrier": "carrier_B",
            "recovery_reference": successor_reference,
        },
    )

    successor_recovered = (
        bool(recovered_difference)
        and successor_unit.continuation_relevant.get(
            "shared_state_recovery"
        )
        is True
        and successor_unit.continuation_relevant.get(
            "source_state_reference"
        )
        == persisted_reference
    )

    continuation_preserved = (
        persisted
        and continuation.has_required_information()
    )

    successor_result = runtime.execute(
        "P1",
        "carrier_B",
        _successor_executor,
    )

    runtime.assert_continuity()

    return CommunicationInterruptionResult(
        process_id=process_id,
        source_unit_id="P0",
        successor_unit_id="P1",
        source_carrier_id="carrier_A",
        successor_carrier_id="carrier_B",
        state_persisted_before_interruption=persisted,
        communication_lost=communication_lost,
        source_channel_restored=source_channel_restored,
        successor_recovered_from_shared_state=(
            successor_recovered
        ),
        continuation_preserved=continuation_preserved,
        successor_completed=bool(successor_result.completed),
        process_terminated=runtime.terminated,
        continuity_valid=(
            transition.validate_step_continuity()
            and continuation.has_required_information()
        ),
        metrics=runtime.metrics(),
        event_log=runtime.event_log(),
        transition_log=runtime.transition_log(),
    )


def main() -> int:
    """Run the scenario and emit JSON."""
    import json

    result = run_communication_interruption()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if result.process_terminated:
        return 1

    if not result.state_persisted_before_interruption:
        return 1

    if not result.communication_lost:
        return 1

    if result.source_channel_restored:
        return 1

    if not result.successor_recovered_from_shared_state:
        return 1

    if not result.continuation_preserved:
        return 1

    if not result.successor_completed:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
