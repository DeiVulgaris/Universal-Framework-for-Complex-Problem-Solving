"""Controlled failure-injection policies for the UFCPS simulator.

Failure injection is kept outside the execution engine so that benchmark
scenarios can reproduce interruptions without changing the continuity logic.

A failure is represented as a planned runtime event. The injector itself does
not decide how the process should recover. Recovery remains the responsibility
of the runtime and protocol layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from ..core.models import CarrierStatus, EventType, ProcessSnapshot


class FailureType(str, Enum):
    """Supported controlled failure modes."""

    CARRIER_TERMINATION = "carrier_termination"
    CARRIER_TIMEOUT = "carrier_timeout"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    COMMUNICATION_LOSS = "communication_loss"
    FORCED_DEADLOCK = "forced_deadlock"
    STATE_CORRUPTION = "state_corruption"


class FailureInjectionError(RuntimeError):
    """Raised when a failure cannot be injected safely."""


@dataclass(frozen=True)
class FailureEvent:
    """A scheduled failure injection."""

    tick: int
    failure_type: FailureType
    carrier_id: str | None = None
    unit_id: str | None = None
    details: dict[str, str] = field(default_factory=dict)


class FailureInjector:
    """Apply deterministic failures to a UFCPS simulation snapshot."""

    def __init__(
        self,
        failures: Iterable[FailureEvent] = (),
    ) -> None:
        self._failures = sorted(
            list(failures),
            key=lambda event: event.tick,
        )
        self._applied: set[tuple[int, FailureType, str | None, str | None]] = set()

    @property
    def failures(self) -> tuple[FailureEvent, ...]:
        """Return the configured failure schedule."""
        return tuple(self._failures)

    @property
    def applied_count(self) -> int:
        """Return the number of failure events already applied."""
        return len(self._applied)

    def pending(self) -> list[FailureEvent]:
        """Return currently unsatisfied failure events."""
        return [
            failure
            for failure in self._failures
            if self._key(failure) not in self._applied
        ]

    def apply_due(
        self,
        snapshot: ProcessSnapshot,
        *,
        tick: int | None = None,
    ) -> list[FailureEvent]:
        """
        Apply all failures scheduled for the current or earlier tick.

        Each failure is applied at most once.
        """
        current_tick = snapshot.tick if tick is None else tick
        applied: list[FailureEvent] = []

        for failure in self._failures:
            if failure.tick > current_tick:
                break

            key = self._key(failure)

            if key in self._applied:
                continue

            self._apply(snapshot, failure)
            self._applied.add(key)
            applied.append(failure)

        return applied

    def reset(self) -> None:
        """Reset the injector so the schedule can be replayed."""
        self._applied.clear()

    def add(self, failure: FailureEvent) -> None:
        """Add a failure to the deterministic schedule."""
        self._failures.append(failure)
        self._failures.sort(key=lambda event: event.tick)

    def _apply(
        self,
        snapshot: ProcessSnapshot,
        failure: FailureEvent,
    ) -> None:
        """Apply one failure event."""
        if snapshot.terminated:
            raise FailureInjectionError(
                "Cannot inject a failure after global process termination."
            )

        if failure.failure_type in {
            FailureType.CARRIER_TERMINATION,
            FailureType.CARRIER_TIMEOUT,
            FailureType.CAPABILITY_UNAVAILABLE,
            FailureType.COMMUNICATION_LOSS,
        }:
            if not failure.carrier_id:
                raise FailureInjectionError(
                    f"{failure.failure_type.value} requires carrier_id."
                )

            try:
                carrier = snapshot.carriers[failure.carrier_id]
            except KeyError as exc:
                raise FailureInjectionError(
                    f"Unknown carrier: {failure.carrier_id!r}"
                ) from exc

            unit_id = failure.unit_id or carrier.current_unit_id

            if failure.failure_type == FailureType.CARRIER_TERMINATION:
                self._terminate_carrier(
                    snapshot,
                    failure.carrier_id,
                    unit_id,
                    failure,
                )
                return

            if failure.failure_type == FailureType.CARRIER_TIMEOUT:
                self._timeout_carrier(
                    snapshot,
                    failure.carrier_id,
                    unit_id,
                    failure,
                )
                return

            if failure.failure_type == FailureType.CAPABILITY_UNAVAILABLE:
                self._disable_capability(
                    snapshot,
                    failure.carrier_id,
                    unit_id,
                    failure,
                )
                return

            if failure.failure_type == FailureType.COMMUNICATION_LOSS:
                self._communication_loss(
                    snapshot,
                    failure.carrier_id,
                    unit_id,
                    failure,
                )
                return

        if failure.failure_type == FailureType.FORCED_DEADLOCK:
            self._force_deadlock(snapshot, failure)
            return

        if failure.failure_type == FailureType.STATE_CORRUPTION:
            self._corrupt_state(snapshot, failure)
            return

        raise FailureInjectionError(
            f"Unsupported failure type: {failure.failure_type.value}"
        )

    def _terminate_carrier(
        self,
        snapshot: ProcessSnapshot,
        carrier_id: str,
        unit_id: str | None,
        failure: FailureEvent,
    ) -> None:
        """Terminate one carrier without terminating the process."""
        carrier = snapshot.carriers[carrier_id]

        carrier.status = CarrierStatus.RELEASED
        carrier.current_unit_id = None

        snapshot.record_event(
            EventType.CARRIER_REPLACED,
            unit_id=unit_id,
            carrier_id=carrier_id,
            details={
                "failure_type": failure.failure_type.value,
                "action": "carrier_terminated",
                **failure.details,
            },
        )

    def _timeout_carrier(
        self,
        snapshot: ProcessSnapshot,
        carrier_id: str,
        unit_id: str | None,
        failure: FailureEvent,
    ) -> None:
        """Represent a carrier timeout as a releasable local failure."""
        carrier = snapshot.carriers[carrier_id]

        carrier.status = CarrierStatus.RELEASED
        carrier.current_unit_id = None

        snapshot.record_event(
            EventType.CARRIER_REPLACED,
            unit_id=unit_id,
            carrier_id=carrier_id,
            details={
                "failure_type": failure.failure_type.value,
                "action": "carrier_timeout",
                **failure.details,
            },
        )

    def _disable_capability(
        self,
        snapshot: ProcessSnapshot,
        carrier_id: str,
        unit_id: str | None,
        failure: FailureEvent,
    ) -> None:
        """Temporarily mark a carrier's required capability unavailable."""
        carrier = snapshot.carriers[carrier_id]

        capability = failure.details.get("capability")
        disabled = set(
            carrier.metadata.get("disabled_capabilities", [])
        )

        if capability:
            disabled.add(capability)

        carrier.metadata["disabled_capabilities"] = sorted(disabled)

        if carrier.status == CarrierStatus.ACTIVE:
            carrier.status = CarrierStatus.STUCK

        snapshot.record_event(
            EventType.DEADLOCK_CREATED,
            unit_id=unit_id,
            carrier_id=carrier_id,
            details={
                "failure_type": failure.failure_type.value,
                "action": "capability_unavailable",
                "capability": capability or "",
                **failure.details,
            },
        )

    def _communication_loss(
        self,
        snapshot: ProcessSnapshot,
        carrier_id: str,
        unit_id: str | None,
        failure: FailureEvent,
    ) -> None:
        """Mark communication with the carrier as unavailable."""
        carrier = snapshot.carriers[carrier_id]

        carrier.metadata["communication_available"] = False

        if carrier.status == CarrierStatus.ACTIVE:
            carrier.status = CarrierStatus.STUCK

        snapshot.record_event(
            EventType.HANDOFF_REQUESTED,
            unit_id=unit_id,
            carrier_id=carrier_id,
            details={
                "failure_type": failure.failure_type.value,
                "action": "communication_loss",
                **failure.details,
            },
        )

    def _force_deadlock(
        self,
        snapshot: ProcessSnapshot,
        failure: FailureEvent,
    ) -> None:
        """Create a deterministic deadlock object for a procedural unit."""
        if not failure.unit_id:
            raise FailureInjectionError(
                "forced_deadlock requires unit_id."
            )

        try:
            state = snapshot.active_units[failure.unit_id]
        except KeyError as exc:
            raise FailureInjectionError(
                f"Unknown procedural unit: {failure.unit_id!r}"
            ) from exc

        state.deadlock = self._deadlock_from_details(state, failure)
        state.unresolved_difference = (
            state.deadlock.unresolved
        )

        carrier_id = None
        for carrier in snapshot.carriers.values():
            if carrier.current_unit_id == failure.unit_id:
                carrier_id = carrier.carrier_id
                if carrier.status == CarrierStatus.ACTIVE:
                    carrier.status = CarrierStatus.STUCK
                break

        snapshot.record_event(
            EventType.DEADLOCK_CREATED,
            unit_id=failure.unit_id,
            carrier_id=carrier_id,
            details={
                "failure_type": failure.failure_type.value,
                "action": "forced_deadlock",
                "state": state.deadlock.state,
                "constraint": state.deadlock.constraint,
                "boundary": state.deadlock.boundary,
                "unresolved": state.deadlock.unresolved,
            },
        )

        snapshot.store_state(state)

    def _corrupt_state(
        self,
        snapshot: ProcessSnapshot,
        failure: FailureEvent,
    ) -> None:
        """Inject controlled corruption into one stored state for testing."""
        if not failure.unit_id:
            raise FailureInjectionError(
                "state_corruption requires unit_id."
            )

        state = snapshot.active_units.get(failure.unit_id)
        if state is None:
            raise FailureInjectionError(
                f"Unknown procedural unit: {failure.unit_id!r}"
            )

        reference = snapshot.store_state(state)

        field_name = failure.details.get("field", "local_result")
        payload = snapshot.load_state(reference)

        if field_name not in payload:
            raise FailureInjectionError(
                f"Cannot corrupt missing stored field: {field_name!r}"
            )

        payload[field_name] = failure.details.get(
            "replacement",
            "__CORRUPTED__",
        )
        snapshot.shared_state[reference] = payload

        snapshot.record_event(
            EventType.VALIDATION_FAILED,
            unit_id=failure.unit_id,
            details={
                "failure_type": failure.failure_type.value,
                "action": "state_corruption",
                "state_reference": reference,
                "field": field_name,
            },
        )

    @staticmethod
    def _deadlock_from_details(
        state: object,
        failure: FailureEvent,
    ):
        """Build a DeadlockState without importing the model at module load."""
        from ..core.models import DeadlockState

        current_state = getattr(state, "current_state", "")

        return DeadlockState(
            state=failure.details.get(
                "state",
                str(current_state),
            ),
            constraint=failure.details.get(
                "constraint",
                "Injected blocking constraint.",
            ),
            boundary=failure.details.get(
                "boundary",
                "Current carrier capability boundary.",
            ),
            unresolved=failure.details.get(
                "unresolved",
                "Injected unresolved difference.",
            ),
        )

    @staticmethod
    def _key(
        failure: FailureEvent,
    ) -> tuple[int, FailureType, str | None, str | None]:
        """Create a deterministic identity for one scheduled failure."""
        return (
            failure.tick,
            failure.failure_type,
            failure.carrier_id,
            failure.unit_id,
        )


def single_carrier_failure(
    *,
    tick: int,
    carrier_id: str,
    unit_id: str | None = None,
    failure_type: FailureType = FailureType.CARRIER_TERMINATION,
) -> FailureEvent:
    """Convenience constructor for a carrier-level failure."""
    return FailureEvent(
        tick=tick,
        failure_type=failure_type,
        carrier_id=carrier_id,
        unit_id=unit_id,
    )


def forced_deadlock(
    *,
    tick: int,
    unit_id: str,
    unresolved: str,
    constraint: str = "Injected blocking constraint.",
    boundary: str = "Current local capability boundary.",
) -> FailureEvent:
    """Convenience constructor for a deterministic deadlock."""
    return FailureEvent(
        tick=tick,
        failure_type=FailureType.FORCED_DEADLOCK,
        unit_id=unit_id,
        details={
            "unresolved": unresolved,
            "constraint": constraint,
            "boundary": boundary,
        },
    )


__all__ = [
    "FailureEvent",
    "FailureInjectionError",
    "FailureInjector",
    "FailureType",
    "forced_deadlock",
    "single_carrier_failure",
]
