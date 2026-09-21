"""Core data models for the UFCPS simulator.

The models in this module intentionally keep process state separate from
carrier identity. A carrier executes a procedural unit, but continuation
state belongs to the process and can survive carrier replacement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CarrierStatus(str, Enum):
    """Runtime status of a carrier."""

    AVAILABLE = "available"
    ACTIVE = "active"
    STUCK = "stuck"
    DISSIPATING = "dissipating"
    COMPLETED = "completed"
    RELEASED = "released"


class SessionStatus(str, Enum):
    """Status of a procedural unit session."""

    ACTIVE = "active"
    STUCK = "stuck"
    DISSIPATING = "dissipating"
    DELEGATED = "delegated"
    UNFOLDED = "unfolded"


class Operation(str, Enum):
    """Canonical UFCPS operations plus process-level operations."""

    DIFF = "diff"
    FIX = "fix"
    DISS = "diss"
    UNFOLD = "unfold"
    DELEGATE = "delegate"
    COMPOSE = "compose"
    TERMINATE = "terminate"


class TransitionType(str, Enum):
    """Supported transition classes."""

    LOCAL = "local"
    CONTINUATION = "continuation"
    DELEGATION = "delegation"
    BRANCH = "branch"


class EventType(str, Enum):
    """Simulation event types."""

    STEP_STARTED = "STEP_STARTED"
    STEP_COMPLETED = "STEP_COMPLETED"
    DIFFERENCE_IDENTIFIED = "DIFFERENCE_IDENTIFIED"
    STATE_FIXED = "STATE_FIXED"
    STATE_DISSIPATED = "STATE_DISSIPATED"
    HANDOFF_REQUESTED = "HANDOFF_REQUESTED"
    CARRIER_REPLACED = "CARRIER_REPLACED"
    DEADLOCK_CREATED = "DEADLOCK_CREATED"
    BRANCH_CREATED = "BRANCH_CREATED"
    BRANCH_COMPLETED = "BRANCH_COMPLETED"
    COMPOSITION_STARTED = "COMPOSITION_STARTED"
    COMPOSITION_COMPLETED = "COMPOSITION_COMPLETED"
    CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"
    EXPERIMENT_STARTED = "EXPERIMENT_STARTED"
    EXPERIMENT_COMPLETED = "EXPERIMENT_COMPLETED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    TERMINATION_REQUESTED = "TERMINATION_REQUESTED"
    PROCESS_TERMINATED = "PROCESS_TERMINATED"


@dataclass(frozen=True)
class CapabilityProfile:
    """Capabilities available to a carrier."""

    name: str
    capabilities: frozenset[str] = frozenset()

    def supports(self, capability: str) -> bool:
        """Return whether the carrier declares the requested capability."""
        return capability in self.capabilities


@dataclass
class Carrier:
    """A computational carrier for a procedural unit."""

    carrier_id: str
    carrier_type: str
    status: CarrierStatus = CarrierStatus.AVAILABLE
    capabilities: CapabilityProfile | None = None
    current_unit_id: str | None = None
    execution_cost: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def activate(self, unit_id: str) -> None:
        """Assign and activate this carrier."""
        if self.status not in {
            CarrierStatus.AVAILABLE,
            CarrierStatus.RELEASED,
            CarrierStatus.COMPLETED,
        }:
            raise ValueError(
                f"Carrier {self.carrier_id!r} cannot be activated from status "
                f"{self.status.value!r}"
            )

        self.status = CarrierStatus.ACTIVE
        self.current_unit_id = unit_id

    def mark_stuck(self) -> None:
        """Mark the carrier as locally stuck."""
        if self.status != CarrierStatus.ACTIVE:
            raise ValueError(
                f"Carrier {self.carrier_id!r} cannot become stuck from "
                f"status {self.status.value!r}"
            )
        self.status = CarrierStatus.STUCK

    def release(self) -> None:
        """Release the carrier from the current procedural unit."""
        self.status = CarrierStatus.RELEASED
        self.current_unit_id = None


@dataclass
class DeadlockState:
    """Structured representation of a local deadlock."""

    state: str
    constraint: str
    boundary: str
    unresolved: str


@dataclass
class ProceduralState:
    """Continuation-relevant state belonging to one procedural unit."""

    unit_id: str
    step_index: int
    task: str
    current_state: str
    local_result: str = ""
    unresolved_difference: str = ""
    next_required_operation: Operation | None = None
    constraints: list[str] = field(default_factory=list)
    boundary_conditions: list[str] = field(default_factory=list)
    continuation_relevant: dict[str, Any] = field(default_factory=dict)
    deadlock: DeadlockState | None = None
    parent_unit_id: str | None = None
    branch_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_stuck(self) -> bool:
        """Return whether this state currently contains a deadlock."""
        return self.deadlock is not None

    def preserve(self) -> dict[str, Any]:
        """Return the state required for continuation."""
        return {
            "unit_id": self.unit_id,
            "step_index": self.step_index,
            "task": self.task,
            "current_state": self.current_state,
            "local_result": self.local_result,
            "unresolved_difference": self.unresolved_difference,
            "next_required_operation": (
                self.next_required_operation.value
                if self.next_required_operation is not None
                else None
            ),
            "constraints": list(self.constraints),
            "boundary_conditions": list(self.boundary_conditions),
            "continuation_relevant": dict(self.continuation_relevant),
            "deadlock": (
                {
                    "state": self.deadlock.state,
                    "constraint": self.deadlock.constraint,
                    "boundary": self.deadlock.boundary,
                    "unresolved": self.deadlock.unresolved,
                }
                if self.deadlock is not None
                else None
            ),
            "parent_unit_id": self.parent_unit_id,
            "branch_id": self.branch_id,
        }


@dataclass(frozen=True)
class ContinuationState:
    """Immutable handoff payload for process continuation."""

    state_reference: str
    source_unit_id: str
    source_step_index: int
    unresolved_difference: str
    next_required_operation: Operation | None
    preserved_state: dict[str, Any]
    reason: str

    def has_required_information(self) -> bool:
        """Check the minimum information required for a handoff."""
        return bool(
            self.state_reference
            and self.source_unit_id
            and self.unresolved_difference
            and self.preserved_state
        )


@dataclass(frozen=True)
class Transition:
    """A recorded procedural transition."""

    transition_id: str
    transition_type: TransitionType
    source_unit_id: str
    source_step_index: int
    source_carrier_id: str
    destination_unit_id: str
    destination_step_index: int
    destination_carrier_id: str
    operation: Operation
    continuation: ContinuationState | None = None
    reason: str = ""

    def validate_step_continuity(self) -> bool:
        """Check the canonical successor relation."""
        return self.destination_step_index == self.source_step_index + 1

    def carrier_changed(self) -> bool:
        """Return whether carrier identity changed."""
        return self.source_carrier_id != self.destination_carrier_id


@dataclass(frozen=True)
class SimulationEvent:
    """Append-only event emitted by the simulator."""

    tick: int
    event_type: EventType
    process_id: str
    unit_id: str | None = None
    carrier_id: str | None = None
    transition_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessSnapshot:
    """Current process-level simulation snapshot."""

    process_id: str
    active_units: dict[str, ProceduralState] = field(default_factory=dict)
    carriers: dict[str, Carrier] = field(default_factory=dict)
    transitions: list[Transition] = field(default_factory=list)
    events: list[SimulationEvent] = field(default_factory=list)
    shared_state: dict[str, dict[str, Any]] = field(default_factory=dict)
    terminated: bool = False
    termination_reason: str | None = None
    tick: int = 0

    def record_event(
        self,
        event_type: EventType,
        *,
        unit_id: str | None = None,
        carrier_id: str | None = None,
        transition_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> SimulationEvent:
        """Append an event and advance the simulation clock."""
        event = SimulationEvent(
            tick=self.tick,
            event_type=event_type,
            process_id=self.process_id,
            unit_id=unit_id,
            carrier_id=carrier_id,
            transition_id=transition_id,
            details=details or {},
        )
        self.events.append(event)
        self.tick += 1
        return event

    def store_state(self, state: ProceduralState) -> str:
        """Persist continuation-relevant state in the shared environment."""
        reference = f"state://{self.process_id}/{state.unit_id}"
        self.shared_state[reference] = state.preserve()
        return reference

    def load_state(self, reference: str) -> dict[str, Any]:
        """Load a previously preserved state."""
        try:
            return dict(self.shared_state[reference])
        except KeyError as exc:
            raise KeyError(f"Unknown state reference: {reference}") from exc

    def assert_not_terminated(self) -> None:
        """Reject runtime operations after global termination."""
        if self.terminated:
            raise RuntimeError(
                f"Process {self.process_id!r} is already terminated: "
                f"{self.termination_reason or 'no reason recorded'}"
            )

    def terminate(self, reason: str) -> None:
        """Terminate the process explicitly at process level."""
        self.terminated = True
        self.termination_reason = reason
        self.record_event(
            EventType.PROCESS_TERMINATED,
            details={"reason": reason},
        )
