"""Deterministic scheduler for UFCPS simulation work.

The scheduler is intentionally separate from the execution engine and carrier
selection policy.

Its role is only to determine which eligible procedural unit should be
scheduled and which carrier should receive it. Process continuity remains the
responsibility of the core runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .core.models import Carrier, CarrierStatus, ProceduralState
from .policies.carrier_selection import (
    CarrierSelectionPolicy,
    CarrierSelectionError,
)


class SchedulingError(RuntimeError):
    """Raised when a procedural unit cannot be scheduled."""


@dataclass(frozen=True)
class ScheduleDecision:
    """Result of one scheduling decision."""

    unit_id: str
    carrier_id: str
    reason: str
    tick: int


@dataclass
class Scheduler:
    """Simple deterministic scheduler for ready procedural units."""

    carrier_policy: CarrierSelectionPolicy
    tick: int = 0
    history: list[ScheduleDecision] = field(default_factory=list)

    def ready_states(
        self,
        states: Iterable[ProceduralState],
        *,
        assigned_unit_ids: set[str] | None = None,
    ) -> list[ProceduralState]:
        """
        Return states eligible for scheduling.

        A state is ready when it is not already assigned and has not reached a
        process-level terminal condition. Local deadlock is not itself a
        terminal scheduling condition; such a state can be delegated or
        unfolded by the runtime.
        """
        assigned = assigned_unit_ids or set()

        return [
            state
            for state in states
            if state.unit_id not in assigned
            and state.deadlock is None
        ]

    def choose(
        self,
        state: ProceduralState,
        carriers: Iterable[Carrier],
        *,
        required_capability: str | None = None,
    ) -> ScheduleDecision:
        """Select an eligible carrier for one procedural state."""
        carrier_list = list(carriers)

        try:
            carrier = self.carrier_policy.select(
                state,
                carrier_list,
                required_capability=required_capability,
            )
        except CarrierSelectionError as exc:
            raise SchedulingError(
                f"Cannot schedule unit {state.unit_id!r}: {exc}"
            ) from exc

        if carrier.status not in {
            CarrierStatus.AVAILABLE,
            CarrierStatus.RELEASED,
            CarrierStatus.COMPLETED,
        }:
            raise SchedulingError(
                f"Selected carrier {carrier.carrier_id!r} is not available."
            )

        decision = ScheduleDecision(
            unit_id=state.unit_id,
            carrier_id=carrier.carrier_id,
            reason=(
                f"Carrier selected for procedural unit {state.unit_id!r} "
                f"using {type(self.carrier_policy).__name__}."
            ),
            tick=self.tick,
        )

        self.history.append(decision)
        self.tick += 1

        return decision

    def schedule_next(
        self,
        states: Iterable[ProceduralState],
        carriers: Iterable[Carrier],
        *,
        assigned_unit_ids: set[str] | None = None,
        required_capability: str | None = None,
    ) -> ScheduleDecision:
        """Select the first ready procedural unit and assign a carrier."""
        ready = self.ready_states(
            states,
            assigned_unit_ids=assigned_unit_ids,
        )

        if not ready:
            raise SchedulingError(
                "No ready procedural unit is available for scheduling."
            )

        # Deterministic order: lowest procedural step first, then unit ID.
        state = min(
            ready,
            key=lambda item: (
                item.step_index,
                item.unit_id,
            ),
        )

        return self.choose(
            state,
            carriers,
            required_capability=required_capability,
        )

    def reset(self) -> None:
        """Reset scheduler history and logical clock."""
        self.tick = 0
        self.history.clear()

    def export_history(self) -> list[dict[str, object]]:
        """Return scheduler history in JSON-compatible form."""
        return [
            {
                "unit_id": decision.unit_id,
                "carrier_id": decision.carrier_id,
                "reason": decision.reason,
                "tick": decision.tick,
            }
            for decision in self.history
        ]


__all__ = [
    "ScheduleDecision",
    "Scheduler",
    "SchedulingError",
]
