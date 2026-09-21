"""Carrier-selection policies for the UFCPS simulator.

Selection policy is deliberately separated from process continuity. A policy
chooses a compatible carrier; the core runtime remains responsible for state
preservation, handoff, and procedural continuity.

The included policies are intentionally simple reference implementations.
They are not ranked against one another.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

from ..core.models import Carrier, CarrierStatus, ProceduralState


class CarrierSelectionError(RuntimeError):
    """Raised when no compatible carrier can be selected."""


class CarrierSelectionPolicy(ABC):
    """Interface for selecting a carrier for a procedural state."""

    @abstractmethod
    def select(
        self,
        state: ProceduralState,
        carriers: Iterable[Carrier],
        *,
        required_capability: str | None = None,
    ) -> Carrier:
        """Select and return a compatible carrier."""
        raise NotImplementedError


@dataclass(frozen=True)
class Candidate:
    """A carrier candidate with its selection rationale."""

    carrier: Carrier
    reason: str


def available_carriers(
    carriers: Iterable[Carrier],
    *,
    required_capability: str | None = None,
) -> list[Carrier]:
    """Return carriers currently eligible for activation."""
    candidates: list[Carrier] = []

    for carrier in carriers:
        if carrier.status not in {
            CarrierStatus.AVAILABLE,
            CarrierStatus.RELEASED,
            CarrierStatus.COMPLETED,
        }:
            continue

        if required_capability is not None:
            if carrier.capabilities is None:
                continue
            if not carrier.capabilities.supports(required_capability):
                continue

        candidates.append(carrier)

    return candidates


class FirstCompatiblePolicy(CarrierSelectionPolicy):
    """Select the first eligible carrier in deterministic input order."""

    def select(
        self,
        state: ProceduralState,
        carriers: Iterable[Carrier],
        *,
        required_capability: str | None = None,
    ) -> Carrier:
        """Return the first eligible carrier."""
        del state

        candidates = available_carriers(
            carriers,
            required_capability=required_capability,
        )

        if not candidates:
            raise CarrierSelectionError(
                "No compatible carrier is available."
            )

        return candidates[0]


class CapabilityMatchedPolicy(CarrierSelectionPolicy):
    """Prefer the carrier with the strongest declared capability overlap."""

    def select(
        self,
        state: ProceduralState,
        carriers: Iterable[Carrier],
        *,
        required_capability: str | None = None,
    ) -> Carrier:
        """Return the candidate with the highest capability overlap."""

        candidates = available_carriers(
            carriers,
            required_capability=required_capability,
        )

        if not candidates:
            raise CarrierSelectionError(
                "No compatible carrier is available."
            )

        required = set()

        raw_required = state.metadata.get("required_capabilities", [])
        if isinstance(raw_required, str):
            required.add(raw_required)
        elif isinstance(raw_required, (list, tuple, set, frozenset)):
            required.update(
                item
                for item in raw_required
                if isinstance(item, str)
            )

        if required_capability:
            required.add(required_capability)

        if not required:
            # Deterministic fallback: smallest declared execution cost,
            # then stable carrier ID.
            return min(
                candidates,
                key=lambda carrier: (
                    carrier.execution_cost,
                    carrier.carrier_id,
                ),
            )

        def score(carrier: Carrier) -> tuple[int, float, str]:
            declared = (
                carrier.capabilities.capabilities
                if carrier.capabilities is not None
                else frozenset()
            )
            overlap = len(required.intersection(declared))
            return (
                overlap,
                -carrier.execution_cost,
                carrier.carrier_id,
            )

        return max(candidates, key=score)


class LeastLoadedPolicy(CarrierSelectionPolicy):
    """Prefer the carrier with the lowest accumulated execution cost."""

    def select(
        self,
        state: ProceduralState,
        carriers: Iterable[Carrier],
        *,
        required_capability: str | None = None,
    ) -> Carrier:
        """Return the least-loaded eligible carrier."""
        del state

        candidates = available_carriers(
            carriers,
            required_capability=required_capability,
        )

        if not candidates:
            raise CarrierSelectionError(
                "No compatible carrier is available."
            )

        return min(
            candidates,
            key=lambda carrier: (
                carrier.execution_cost,
                carrier.carrier_id,
            ),
        )


class ExplicitOrderPolicy(CarrierSelectionPolicy):
    """Select carriers according to an explicit deterministic ID order."""

    def __init__(self, carrier_ids: list[str]) -> None:
        if not carrier_ids:
            raise ValueError(
                "carrier_ids must contain at least one carrier ID."
            )

        self._order = tuple(carrier_ids)

    def select(
        self,
        state: ProceduralState,
        carriers: Iterable[Carrier],
        *,
        required_capability: str | None = None,
    ) -> Carrier:
        """Return the first eligible carrier appearing in the configured order."""
        del state

        by_id = {
            carrier.carrier_id: carrier
            for carrier in carriers
        }

        for carrier_id in self._order:
            carrier = by_id.get(carrier_id)
            if carrier is None:
                continue

            eligible = available_carriers(
                [carrier],
                required_capability=required_capability,
            )

            if eligible:
                return eligible[0]

        raise CarrierSelectionError(
            "No carrier from the explicit order is currently compatible."
        )


def selection_candidates(
    state: ProceduralState,
    carriers: Iterable[Carrier],
    *,
    required_capability: str | None = None,
) -> list[Candidate]:
    """
    Return all currently eligible candidates with an explicit rationale.

    This helper is useful for simulation logging and for experiments that
    need to compare carrier-selection policies.
    """
    candidates = available_carriers(
        carriers,
        required_capability=required_capability,
    )

    required: set[str] = set()

    raw_required = state.metadata.get("required_capabilities", [])
    if isinstance(raw_required, str):
        required.add(raw_required)
    elif isinstance(raw_required, (list, tuple, set, frozenset)):
        required.update(
            item
            for item in raw_required
            if isinstance(item, str)
        )

    if required_capability:
        required.add(required_capability)

    result: list[Candidate] = []

    for carrier in candidates:
        declared = (
            carrier.capabilities.capabilities
            if carrier.capabilities is not None
            else frozenset()
        )

        overlap = required.intersection(declared)

        if required and not overlap:
            reason = "eligible carrier without matching optional capability."
        elif required:
            reason = (
                "eligible carrier matching "
                f"{len(overlap)} required capability item(s)."
            )
        else:
            reason = "eligible carrier; no explicit capability requirement."

        result.append(
            Candidate(
                carrier=carrier,
                reason=reason,
            )
        )

    return result


__all__ = [
    "Candidate",
    "CapabilityMatchedPolicy",
    "CarrierSelectionError",
    "CarrierSelectionPolicy",
    "ExplicitOrderPolicy",
    "FirstCompatiblePolicy",
    "LeastLoadedPolicy",
    "available_carriers",
    "selection_candidates",
]
