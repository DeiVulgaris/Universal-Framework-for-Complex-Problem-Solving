"""Runtime facade for the UFCPS simulator.

This module provides the narrow orchestration layer between:

- core process models
- the execution engine
- the shared continuation-state store

The runtime is intentionally small. Scenario code should use this facade
instead of manipulating the simulator's internal collections directly.

The central architectural property remains:

    carrier lifetime != process-state lifetime
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .engine import ExecutionResult, LocalExecutor, UFCPSExecutionEngine
from .models import (
    Carrier,
    EventType,
    Operation,
    ProceduralState,
    ProcessSnapshot,
)
from .state_store import SharedStateStore, StateRecord


@dataclass
class RuntimeConfig:
    """Configuration for one simulation runtime."""

    process_id: str
    max_steps: int = 100
    strict_state_sync: bool = True


class RuntimeInvariantError(RuntimeError):
    """Raised when runtime synchronization or continuity is violated."""


class UFCPSRuntime:
    """High-level runtime facade for a single simulated process."""

    def __init__(
        self,
        config: RuntimeConfig,
        *,
        state_store: SharedStateStore | None = None,
    ) -> None:
        if not config.process_id.strip():
            raise ValueError("process_id must not be empty.")

        if config.max_steps < 1:
            raise ValueError("max_steps must be at least 1.")

        self.config = config
        self.snapshot = ProcessSnapshot(process_id=config.process_id)
        self.state_store = state_store or SharedStateStore()
        self.engine = UFCPSExecutionEngine(self.snapshot)

        self._step_count = 0

    @property
    def process_id(self) -> str:
        """Return the process identifier."""
        return self.config.process_id

    @property
    def terminated(self) -> bool:
        """Return whether the process has reached global termination."""
        return self.snapshot.terminated

    @property
    def step_count(self) -> int:
        """Return the number of executed runtime steps."""
        return self._step_count

    def add_carrier(self, carrier: Carrier) -> None:
        """Register a carrier."""
        self.engine.register_carrier(carrier)

    def add_state(self, state: ProceduralState) -> str:
        """Register a procedural state and persist its continuation state."""
        reference = self.engine.register_state(state)
        self._sync_state(reference)
        return reference

    def activate(self, carrier_id: str, unit_id: str) -> None:
        """Assign a carrier to a procedural unit."""
        self.engine.activate_carrier(carrier_id, unit_id)

    def execute(
        self,
        unit_id: str,
        carrier_id: str,
        executor: LocalExecutor,
    ) -> ExecutionResult:
        """Execute one local procedural step and synchronize its state."""
        self._ensure_step_budget()
        result = self.engine.execute(unit_id, carrier_id, executor)

        state = self.engine.get_state(unit_id)
        reference = self.snapshot.store_state(state)
        self._sync_state(reference)

        self._step_count += 1
        return result

    def identify_difference(
        self,
        unit_id: str,
        difference: str,
        *,
        source: str = "runtime",
    ) -> str:
        """Record and persist a structural difference."""
        self.engine.identify_difference(
            unit_id,
            difference,
            source=source,
        )
        reference = self.snapshot.store_state(
            self.engine.get_state(unit_id)
        )
        self._sync_state(reference)
        return reference

    def preserve(self, unit_id: str) -> str:
        """Fix continuation-relevant state."""
        reference = self.engine.fix_state(unit_id)
        self._sync_state(reference)
        return reference

    def dissipate(self, unit_id: str, carrier_id: str) -> str:
        """Release carrier dependence while preserving state."""
        reference = self.engine.dissipate(
            unit_id,
            carrier_id,
        )
        self._sync_state(reference)
        return reference

    def delegate(
        self,
        unit_id: str,
        source_carrier_id: str,
        destination_carrier_id: str,
        *,
        reason: str,
        next_unit_id: str | None = None,
    ) -> ProceduralState:
        """
        Perform carrier-independent continuation.

        The sequence is:

            request handoff
            -> preserve shared state
            -> dissipate source carrier
            -> unfold successor on destination carrier
        """
        self._ensure_step_budget()

        successor = self.engine.delegate(
            unit_id,
            source_carrier_id,
            destination_carrier_id,
            reason=reason,
            next_unit_id=next_unit_id,
        )

        source = self.engine.get_state(unit_id)
        self._sync_state(self.snapshot.store_state(source))
        self._sync_state(self.snapshot.store_state(successor))

        self._step_count += 1
        return successor

    def branch(
        self,
        source_unit_id: str,
        source_carrier_id: str,
        branches: list[tuple[str, str, str]],
    ) -> list[ProceduralState]:
        """Create parallel successor procedural units."""
        self._ensure_step_budget()

        successors = self.engine.branch(
            source_unit_id,
            source_carrier_id,
            branches,
        )

        source = self.engine.get_state(source_unit_id)
        self._sync_state(self.snapshot.store_state(source))

        for successor in successors:
            self._sync_state(
                self.snapshot.store_state(successor)
            )

        self._step_count += 1
        return successors

    def load_state(self, reference: str) -> StateRecord:
        """Load a state from the process-level shared state store."""
        return self.state_store.get(reference)

    def state_exists(self, reference: str) -> bool:
        """Return whether a state is available for continuation."""
        return self.state_store.exists(reference)

    def terminate(self, reason: str) -> None:
        """Perform explicit global process termination."""
        self.engine.terminate(reason)

    def event_log(self) -> list[dict[str, Any]]:
        """Return an exportable event log."""
        return [
            {
                "tick": event.tick,
                "event_type": event.event_type.value,
                "process_id": event.process_id,
                "unit_id": event.unit_id,
                "carrier_id": event.carrier_id,
                "transition_id": event.transition_id,
                "details": dict(event.details),
            }
            for event in self.snapshot.events
        ]

    def transition_log(self) -> list[dict[str, Any]]:
        """Return an exportable transition log."""
        rows: list[dict[str, Any]] = []

        for transition in self.snapshot.transitions:
            continuation = transition.continuation

            rows.append(
                {
                    "transition_id": transition.transition_id,
                    "transition_type": transition.transition_type.value,
                    "source_unit_id": transition.source_unit_id,
                    "source_step_index": transition.source_step_index,
                    "source_carrier_id": transition.source_carrier_id,
                    "destination_unit_id": transition.destination_unit_id,
                    "destination_step_index": (
                        transition.destination_step_index
                    ),
                    "destination_carrier_id": (
                        transition.destination_carrier_id
                    ),
                    "operation": transition.operation.value,
                    "carrier_changed": transition.carrier_changed(),
                    "continuation": (
                        {
                            "state_reference": (
                                continuation.state_reference
                            ),
                            "source_unit_id": (
                                continuation.source_unit_id
                            ),
                            "source_step_index": (
                                continuation.source_step_index
                            ),
                            "unresolved_difference": (
                                continuation.unresolved_difference
                            ),
                            "next_required_operation": (
                                continuation.next_required_operation.value
                                if continuation.next_required_operation
                                is not None
                                else None
                            ),
                            "reason": continuation.reason,
                        }
                        if continuation is not None
                        else None
                    ),
                    "reason": transition.reason,
                }
            )

        return rows

    def metrics(self) -> dict[str, Any]:
        """Return basic runtime measurements."""
        handoffs = sum(
            1
            for transition in self.snapshot.transitions
            if transition.carrier_changed()
        )

        valid_step_transitions = sum(
            1
            for transition in self.snapshot.transitions
            if transition.validate_step_continuity()
        )

        deadlocks = sum(
            1
            for event in self.snapshot.events
            if event.event_type == EventType.DEADLOCK_CREATED
        )

        failures = sum(
            1
            for event in self.snapshot.events
            if event.event_type == EventType.VALIDATION_FAILED
        )

        return {
            "process_id": self.process_id,
            "terminated": self.terminated,
            "termination_reason": self.snapshot.termination_reason,
            "runtime_steps": self._step_count,
            "procedural_units": len(self.snapshot.active_units),
            "registered_carriers": len(self.snapshot.carriers),
            "transitions": len(self.snapshot.transitions),
            "carrier_handoffs": handoffs,
            "valid_step_transitions": valid_step_transitions,
            "deadlocks": deadlocks,
            "validation_failures": failures,
            "stored_states": self.state_store.count(),
            "event_count": len(self.snapshot.events),
        }

    def assert_continuity(self) -> None:
        """
        Check runtime-level continuation invariants.

        This method deliberately checks structural process continuity only.
        It does not evaluate the truth or quality of task-specific results.
        """
        for transition in self.snapshot.transitions:
            if not transition.validate_step_continuity():
                raise RuntimeInvariantError(
                    f"Invalid step continuity in {transition.transition_id}: "
                    f"{transition.source_step_index} -> "
                    f"{transition.destination_step_index}"
                )

            if transition.carrier_changed():
                if transition.continuation is None:
                    raise RuntimeInvariantError(
                        f"Transition {transition.transition_id} changes carrier "
                        "without continuation state."
                    )

                if not transition.continuation.has_required_information():
                    raise RuntimeInvariantError(
                        f"Transition {transition.transition_id} has incomplete "
                        "continuation state."
                    )

        if self.terminated:
            return

        if self._step_count > self.config.max_steps:
            raise RuntimeInvariantError(
                f"Runtime step budget exceeded: {self._step_count} > "
                f"{self.config.max_steps}"
            )

    def export_state_store(self) -> list[dict[str, Any]]:
        """Return the complete shared-state snapshot."""
        return self.state_store.export_jsonable()

    def _sync_state(self, snapshot_reference: str) -> None:
        """Copy the engine's state snapshot into the shared state store."""
        try:
            payload = self.snapshot.load_state(snapshot_reference)
        except KeyError as exc:
            if self.config.strict_state_sync:
                raise RuntimeInvariantError(
                    f"Engine state reference disappeared: "
                    f"{snapshot_reference}"
                ) from exc
            return

        unit_id = payload.get("unit_id")
        step_index = payload.get("step_index")

        if not isinstance(unit_id, str) or not unit_id:
            raise RuntimeInvariantError(
                f"Persisted state {snapshot_reference!r} has no valid unit_id."
            )

        if not isinstance(step_index, int) or step_index < 0:
            raise RuntimeInvariantError(
                f"Persisted state {snapshot_reference!r} has invalid "
                "step_index."
            )

        parent_reference = None
        parent_unit_id = payload.get("parent_unit_id")
        if isinstance(parent_unit_id, str) and parent_unit_id:
            parent_reference = (
                f"state://{self.process_id}/{parent_unit_id}"
            )

        self.state_store.put(
            reference=snapshot_reference,
            process_id=self.process_id,
            unit_id=unit_id,
            step_index=step_index,
            payload=payload,
            parent_reference=parent_reference,
            metadata={
                "runtime_sync": True,
                "operation_flow": (
                    "diff -> fix -> diss -> unfold"
                ),
            },
            overwrite=True,
        )

    def _ensure_step_budget(self) -> None:
        """Enforce the runtime-level execution budget."""
        self.snapshot.assert_not_terminated()

        if self._step_count >= self.config.max_steps:
            raise RuntimeInvariantError(
                "Maximum simulation step count reached."
            )


__all__ = [
    "RuntimeConfig",
    "RuntimeInvariantError",
    "UFCPSRuntime",
]
