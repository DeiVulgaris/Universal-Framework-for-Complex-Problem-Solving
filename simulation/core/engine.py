"""Execution engine for the UFCPS simulator.

The engine implements the minimal executable continuity loop:

    identify difference
    -> preserve state
    -> dissipate carrier dependence
    -> handoff / unfold successor
    -> continue P_n -> P_n+1

The implementation intentionally keeps task semantics abstract. A scenario
supplies task-specific local execution behavior; the engine enforces process
continuity and records the resulting trace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .models import (
    Carrier,
    CarrierStatus,
    ContinuationState,
    EventType,
    Operation,
    ProceduralState,
    ProcessSnapshot,
    SessionStatus,
    Transition,
    TransitionType,
)


LocalExecutor = Callable[[ProceduralState, Carrier], "ExecutionResult"]


@dataclass(frozen=True)
class ExecutionResult:
    """Result returned by one local carrier execution."""

    completed: bool
    current_state: str
    local_result: str = ""
    difference: str = ""
    next_operation: Operation | None = None
    deadlock_state: dict[str, str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class UFCPSExecutionError(RuntimeError):
    """Raised when an execution operation violates process invariants."""


class UFCPSExecutionEngine:
    """Minimal process engine for deterministic UFCPS simulations."""

    def __init__(self, snapshot: ProcessSnapshot) -> None:
        self.snapshot = snapshot

    def register_carrier(self, carrier: Carrier) -> None:
        """Register a carrier in the shared process environment."""
        if carrier.carrier_id in self.snapshot.carriers:
            raise UFCPSExecutionError(
                f"Carrier {carrier.carrier_id!r} is already registered."
            )
        self.snapshot.carriers[carrier.carrier_id] = carrier

    def register_state(self, state: ProceduralState) -> str:
        """Register a procedural state as the current active state."""
        self.snapshot.assert_not_terminated()

        if state.unit_id in self.snapshot.active_units:
            raise UFCPSExecutionError(
                f"Procedural unit {state.unit_id!r} is already active."
            )

        self.snapshot.active_units[state.unit_id] = state
        reference = self.snapshot.store_state(state)

        self.snapshot.record_event(
            EventType.STEP_STARTED,
            unit_id=state.unit_id,
            details={
                "step_index": state.step_index,
                "state_reference": reference,
            },
        )
        return reference

    def activate_carrier(
        self,
        carrier_id: str,
        unit_id: str,
    ) -> None:
        """Assign a registered carrier to a registered procedural unit."""
        self.snapshot.assert_not_terminated()

        carrier = self._get_carrier(carrier_id)
        state = self._get_state(unit_id)

        if carrier.status not in {
            CarrierStatus.AVAILABLE,
            CarrierStatus.RELEASED,
            CarrierStatus.COMPLETED,
        }:
            raise UFCPSExecutionError(
                f"Carrier {carrier_id!r} cannot activate while "
                f"in status {carrier.status.value!r}."
            )

        carrier.activate(unit_id)

        self.snapshot.record_event(
            EventType.STEP_STARTED,
            unit_id=unit_id,
            carrier_id=carrier_id,
            details={
                "carrier_type": carrier.carrier_type,
                "step_index": state.step_index,
            },
        )

    def execute(
        self,
        unit_id: str,
        carrier_id: str,
        executor: LocalExecutor,
    ) -> ExecutionResult:
        """Execute one procedural unit on one carrier."""
        self.snapshot.assert_not_terminated()

        state = self._get_state(unit_id)
        carrier = self._get_carrier(carrier_id)

        if carrier.current_unit_id != unit_id:
            raise UFCPSExecutionError(
                f"Carrier {carrier_id!r} is not assigned to unit {unit_id!r}."
            )

        if carrier.status != CarrierStatus.ACTIVE:
            raise UFCPSExecutionError(
                f"Carrier {carrier_id!r} is not active."
            )

        result = executor(state, carrier)

        state.current_state = result.current_state
        state.local_result = result.local_result

        if result.difference:
            state.unresolved_difference = result.difference
            self.snapshot.record_event(
                EventType.DIFFERENCE_IDENTIFIED,
                unit_id=unit_id,
                carrier_id=carrier_id,
                details={"difference": result.difference},
            )

        state.next_required_operation = result.next_operation

        if result.completed:
            carrier.status = CarrierStatus.COMPLETED
            self.snapshot.record_event(
                EventType.STEP_COMPLETED,
                unit_id=unit_id,
                carrier_id=carrier_id,
                details={
                    "result": result.local_result,
                    "next_operation": (
                        result.next_operation.value
                        if result.next_operation is not None
                        else None
                    ),
                },
            )
        else:
            carrier.mark_stuck()
            if result.deadlock_state is not None:
                deadlock = result.deadlock_state
                from .models import DeadlockState

                state.deadlock = DeadlockState(
                    state=deadlock.get("state", state.current_state),
                    constraint=deadlock.get("constraint", ""),
                    boundary=deadlock.get("boundary", ""),
                    unresolved=deadlock.get(
                        "unresolved",
                        state.unresolved_difference,
                    ),
                )

                self.snapshot.record_event(
                    EventType.DEADLOCK_CREATED,
                    unit_id=unit_id,
                    carrier_id=carrier_id,
                    details={
                        "state": state.deadlock.state,
                        "constraint": state.deadlock.constraint,
                        "boundary": state.deadlock.boundary,
                        "unresolved": state.deadlock.unresolved,
                    },
                )

        self.snapshot.store_state(state)
        return result

    def identify_difference(
        self,
        unit_id: str,
        difference: str,
        *,
        source: str = "runtime",
    ) -> None:
        """Explicitly record the structural difference of a procedural unit."""
        self.snapshot.assert_not_terminated()

        if not difference.strip():
            raise UFCPSExecutionError(
                "A structural difference must not be empty."
            )

        state = self._get_state(unit_id)
        state.unresolved_difference = difference

        self.snapshot.store_state(state)
        self.snapshot.record_event(
            EventType.DIFFERENCE_IDENTIFIED,
            unit_id=unit_id,
            details={
                "difference": difference,
                "source": source,
            },
        )

    def fix_state(self, unit_id: str) -> str:
        """Persist continuation-relevant state for the current unit."""
        self.snapshot.assert_not_terminated()

        state = self._get_state(unit_id)

        if not state.unresolved_difference:
            raise UFCPSExecutionError(
                f"Unit {unit_id!r} has no unresolved difference to preserve."
            )

        reference = self.snapshot.store_state(state)

        self.snapshot.record_event(
            EventType.STATE_FIXED,
            unit_id=unit_id,
            details={"state_reference": reference},
        )
        return reference

    def dissipate(
        self,
        unit_id: str,
        carrier_id: str,
    ) -> str:
        """
        Release continuation state from exclusive dependence on a carrier.

        This operation does not delete state. It persists the state in the
        shared environment and releases the carrier.
        """
        self.snapshot.assert_not_terminated()

        state = self._get_state(unit_id)
        carrier = self._get_carrier(carrier_id)

        if carrier.current_unit_id != unit_id:
            raise UFCPSExecutionError(
                f"Carrier {carrier_id!r} is not carrying unit {unit_id!r}."
            )

        state_reference = self.snapshot.store_state(state)

        if carrier.status == CarrierStatus.ACTIVE:
            carrier.status = CarrierStatus.DISSIPATING
        elif carrier.status != CarrierStatus.STUCK:
            raise UFCPSExecutionError(
                f"Carrier {carrier_id!r} cannot dissipate from "
                f"status {carrier.status.value!r}."
            )

        self.snapshot.record_event(
            EventType.STATE_DISSIPATED,
            unit_id=unit_id,
            carrier_id=carrier_id,
            details={"state_reference": state_reference},
        )

        carrier.release()
        return state_reference

    def request_handoff(
        self,
        unit_id: str,
        source_carrier_id: str,
        destination_carrier_id: str,
        *,
        reason: str,
    ) -> ContinuationState:
        """Create a validated continuation payload for another carrier."""
        self.snapshot.assert_not_terminated()

        state = self._get_state(unit_id)
        source_carrier = self._get_carrier(source_carrier_id)
        destination_carrier = self._get_carrier(destination_carrier_id)

        if source_carrier.current_unit_id != unit_id:
            raise UFCPSExecutionError(
                f"Source carrier {source_carrier_id!r} is not carrying unit "
                f"{unit_id!r}."
            )

        if destination_carrier.status not in {
            CarrierStatus.AVAILABLE,
            CarrierStatus.RELEASED,
            CarrierStatus.COMPLETED,
        }:
            raise UFCPSExecutionError(
                f"Destination carrier {destination_carrier_id!r} is not available."
            )

        if not state.unresolved_difference:
            raise UFCPSExecutionError(
                f"Unit {unit_id!r} has no unresolved difference for handoff."
            )

        state_reference = self.snapshot.store_state(state)

        continuation = ContinuationState(
            state_reference=state_reference,
            source_unit_id=state.unit_id,
            source_step_index=state.step_index,
            unresolved_difference=state.unresolved_difference,
            next_required_operation=(
                state.next_required_operation
                or Operation.DIFF
            ),
            preserved_state=state.preserve(),
            reason=reason,
        )

        if not continuation.has_required_information():
            raise UFCPSExecutionError(
                "Continuation payload is incomplete."
            )

        self.snapshot.record_event(
            EventType.HANDOFF_REQUESTED,
            unit_id=unit_id,
            carrier_id=source_carrier_id,
            details={
                "destination_carrier": destination_carrier_id,
                "state_reference": state_reference,
                "reason": reason,
            },
        )

        return continuation

    def unfold(
        self,
        continuation: ContinuationState,
        destination_carrier_id: str,
        *,
        next_unit_id: str | None = None,
        task: str | None = None,
        current_state: str | None = None,
    ) -> ProceduralState:
        """Instantiate the successor procedural unit from preserved state."""
        self.snapshot.assert_not_terminated()

        destination_carrier = self._get_carrier(destination_carrier_id)

        if destination_carrier.status not in {
            CarrierStatus.AVAILABLE,
            CarrierStatus.RELEASED,
            CarrierStatus.COMPLETED,
        }:
            raise UFCPSExecutionError(
                f"Destination carrier {destination_carrier_id!r} is unavailable."
            )

        next_step = continuation.source_step_index + 1
        derived_id = next_unit_id or f"{continuation.source_unit_id}.p{next_step}"

        if derived_id in self.snapshot.active_units:
            raise UFCPSExecutionError(
                f"Successor unit {derived_id!r} already exists."
            )

        previous = continuation.preserved_state

        successor = ProceduralState(
            unit_id=derived_id,
            step_index=next_step,
            task=task or str(previous.get("task", "")),
            current_state=current_state
            or str(previous.get("current_state", "")),
            local_result="",
            unresolved_difference=continuation.unresolved_difference,
            next_required_operation=continuation.next_required_operation,
            constraints=list(previous.get("constraints", [])),
            boundary_conditions=list(
                previous.get("boundary_conditions", [])
            ),
            continuation_relevant=dict(
                previous.get("continuation_relevant", {})
            ),
            deadlock=None,
            parent_unit_id=continuation.source_unit_id,
            branch_id=None,
        )

        self.snapshot.active_units[derived_id] = successor
        destination_carrier.activate(derived_id)
        successor_ref = self.snapshot.store_state(successor)

        transition = Transition(
            transition_id=(
                f"transition-{continuation.source_unit_id}-{derived_id}"
            ),
            transition_type=TransitionType.DELEGATION,
            source_unit_id=continuation.source_unit_id,
            source_step_index=continuation.source_step_index,
            source_carrier_id=str(
                previous.get("metadata", {}).get(
                    "carrier_id",
                    "unknown",
                )
            ),
            destination_unit_id=derived_id,
            destination_step_index=next_step,
            destination_carrier_id=destination_carrier_id,
            operation=Operation.UNFOLD,
            continuation=continuation,
            reason=continuation.reason,
        )

        # If the source carrier ID was not embedded in preserved metadata,
        # replace the synthetic value with the first carrier reference found
        # in the process history.
        if transition.source_carrier_id == "unknown":
            transition = self._replace_source_carrier_from_history(
                transition,
                continuation.source_unit_id,
            )

        self._record_transition(transition)

        self.snapshot.record_event(
            EventType.CARRIER_REPLACED,
            unit_id=derived_id,
            carrier_id=destination_carrier_id,
            transition_id=transition.transition_id,
            details={
                "source_unit_id": continuation.source_unit_id,
                "source_step_index": continuation.source_step_index,
                "destination_step_index": next_step,
                "state_reference": successor_ref,
            },
        )

        self.snapshot.record_event(
            EventType.STEP_STARTED,
            unit_id=derived_id,
            carrier_id=destination_carrier_id,
            transition_id=transition.transition_id,
            details={
                "step_index": next_step,
                "parent_unit_id": continuation.source_unit_id,
            },
        )

        return successor

    def delegate(
        self,
        unit_id: str,
        source_carrier_id: str,
        destination_carrier_id: str,
        *,
        reason: str,
        next_unit_id: str | None = None,
    ) -> ProceduralState:
        """Perform the complete dissipation -> handoff -> unfold sequence."""
        self.snapshot.assert_not_terminated()

        self._get_state(unit_id)
        self._get_carrier(source_carrier_id)
        self._get_carrier(destination_carrier_id)

        continuation = self.request_handoff(
            unit_id,
            source_carrier_id,
            destination_carrier_id,
            reason=reason,
        )

        self.dissipate(unit_id, source_carrier_id)

        return self.unfold(
            continuation,
            destination_carrier_id,
            next_unit_id=next_unit_id,
        )

    def branch(
        self,
        source_unit_id: str,
        source_carrier_id: str,
        branches: list[tuple[str, str, str]],
    ) -> list[ProceduralState]:
        """
        Create parallel successor units.

        Each tuple is:

            destination_carrier_id, branch_id, unresolved_difference
        """
        self.snapshot.assert_not_terminated()

        if not branches:
            raise UFCPSExecutionError("At least one branch is required.")

        source = self._get_state(source_unit_id)
        source_carrier = self._get_carrier(source_carrier_id)

        if source_carrier.current_unit_id != source_unit_id:
            raise UFCPSExecutionError(
                f"Source carrier {source_carrier_id!r} is not carrying "
                f"{source_unit_id!r}."
            )

        source_reference = self.snapshot.store_state(source)
        successors: list[ProceduralState] = []

        for index, (
            destination_carrier_id,
            branch_id,
            difference,
        ) in enumerate(branches):
            destination_carrier = self._get_carrier(destination_carrier_id)

            if destination_carrier.status not in {
                CarrierStatus.AVAILABLE,
                CarrierStatus.RELEASED,
                CarrierStatus.COMPLETED,
            }:
                raise UFCPSExecutionError(
                    f"Branch destination carrier "
                    f"{destination_carrier_id!r} is unavailable."
                )

            if not branch_id.strip():
                raise UFCPSExecutionError(
                    "Branch ID must not be empty."
                )

            if not difference.strip():
                raise UFCPSExecutionError(
                    "Each branch must define a structural difference."
                )

            successor_id = (
                f"{source_unit_id}.b{index + 1}"
            )

            successor = ProceduralState(
                unit_id=successor_id,
                step_index=source.step_index + 1,
                task=source.task,
                current_state=source.current_state,
                unresolved_difference=difference,
                next_required_operation=Operation.DIFF,
                constraints=list(source.constraints),
                boundary_conditions=list(source.boundary_conditions),
                continuation_relevant=dict(source.continuation_relevant),
                parent_unit_id=source.unit_id,
                branch_id=branch_id,
            )

            self.snapshot.active_units[successor_id] = successor
            destination_carrier.activate(successor_id)
            successor_ref = self.snapshot.store_state(successor)

            continuation = ContinuationState(
                state_reference=source_reference,
                source_unit_id=source.unit_id,
                source_step_index=source.step_index,
                unresolved_difference=difference,
                next_required_operation=Operation.DIFF,
                preserved_state=source.preserve(),
                reason=f"Parallel branch {branch_id}.",
            )

            transition = Transition(
                transition_id=f"branch-{source_unit_id}-{branch_id}",
                transition_type=TransitionType.BRANCH,
                source_unit_id=source.unit_id,
                source_step_index=source.step_index,
                source_carrier_id=source_carrier_id,
                destination_unit_id=successor_id,
                destination_step_index=successor.step_index,
                destination_carrier_id=destination_carrier_id,
                operation=Operation.UNFOLD,
                continuation=continuation,
                reason=f"Parallel branch {branch_id}.",
            )

            self._record_transition(transition)

            self.snapshot.record_event(
                EventType.BRANCH_CREATED,
                unit_id=successor_id,
                carrier_id=destination_carrier_id,
                transition_id=transition.transition_id,
                details={
                    "branch_id": branch_id,
                    "source_unit_id": source_unit_id,
                    "state_reference": successor_ref,
                },
            )

            successors.append(successor)

        return successors

    def terminate(self, reason: str) -> None:
        """Perform explicit process-level termination."""
        self.snapshot.assert_not_terminated()
        self.snapshot.record_event(
            EventType.TERMINATION_REQUESTED,
            details={"reason": reason},
        )
        self.snapshot.terminate(reason)

        for carrier in self.snapshot.carriers.values():
            if carrier.status == CarrierStatus.ACTIVE:
                carrier.release()

    def get_state(self, unit_id: str) -> ProceduralState:
        """Return a registered procedural state."""
        return self._get_state(unit_id)

    def get_carrier(self, carrier_id: str) -> Carrier:
        """Return a registered carrier."""
        return self._get_carrier(carrier_id)

    def _get_state(self, unit_id: str) -> ProceduralState:
        try:
            return self.snapshot.active_units[unit_id]
        except KeyError as exc:
            raise UFCPSExecutionError(
                f"Unknown procedural unit: {unit_id!r}"
            ) from exc

    def _get_carrier(self, carrier_id: str) -> Carrier:
        try:
            return self.snapshot.carriers[carrier_id]
        except KeyError as exc:
            raise UFCPSExecutionError(
                f"Unknown carrier: {carrier_id!r}"
            ) from exc

    def _record_transition(self, transition: Transition) -> None:
        """Validate and append a transition."""
        if not transition.validate_step_continuity():
            raise UFCPSExecutionError(
                "Transition violates procedural step continuity: "
                f"{transition.source_step_index} -> "
                f"{transition.destination_step_index}."
            )

        if transition.carrier_changed():
            if transition.continuation is None:
                raise UFCPSExecutionError(
                    "Carrier replacement requires continuation state."
                )

            if not transition.continuation.has_required_information():
                raise UFCPSExecutionError(
                    "Carrier replacement has incomplete continuation state."
                )

        if (
            transition.transition_type == TransitionType.LOCAL
            and transition.carrier_changed()
        ):
            raise UFCPSExecutionError(
                "Local transition cannot change carrier identity."
            )

        self.snapshot.transitions.append(transition)

    def _replace_source_carrier_from_history(
        self,
        transition: Transition,
        source_unit_id: str,
    ) -> Transition:
        """Recover source carrier from the recorded process history."""
        for event in reversed(self.snapshot.events):
            if (
                event.unit_id == source_unit_id
                and event.carrier_id is not None
            ):
                return Transition(
                    transition_id=transition.transition_id,
                    transition_type=transition.transition_type,
                    source_unit_id=transition.source_unit_id,
                    source_step_index=transition.source_step_index,
                    source_carrier_id=event.carrier_id,
                    destination_unit_id=transition.destination_unit_id,
                    destination_step_index=transition.destination_step_index,
                    destination_carrier_id=transition.destination_carrier_id,
                    operation=transition.operation,
                    continuation=transition.continuation,
                    reason=transition.reason,
                )

        raise UFCPSExecutionError(
            f"Cannot recover source carrier for unit {source_unit_id!r}."
        )


__all__ = [
    "ExecutionResult",
    "LocalExecutor",
    "UFCPSExecutionEngine",
    "UFCPSExecutionError",
]
