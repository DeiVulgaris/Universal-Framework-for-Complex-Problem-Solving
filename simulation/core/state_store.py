"""Shared continuation-state store for the UFCPS simulator.

The store models the process-level memory layer used by the simulation.
State survives carrier replacement because it is persisted here rather than
kept exclusively inside a carrier object.

This module deliberately stores plain serializable dictionaries at the
boundary so that the simulated state can later be written to JSON or mapped
to an external persistence system.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Iterable


class StateStoreError(RuntimeError):
    """Base exception for shared-state errors."""


class StateNotFoundError(StateStoreError):
    """Raised when a requested state reference does not exist."""


class StateAlreadyExistsError(StateStoreError):
    """Raised when a new state uses an existing reference without overwrite."""


@dataclass(frozen=True)
class StateRecord:
    """Immutable snapshot stored in the shared environment."""

    reference: str
    process_id: str
    unit_id: str
    step_index: int
    payload: dict[str, Any]
    parent_reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SharedStateStore:
    """Thread-safe in-memory state store for deterministic simulation."""

    def __init__(self) -> None:
        self._records: dict[str, StateRecord] = {}
        self._lock = RLock()

    def put(
        self,
        *,
        reference: str,
        process_id: str,
        unit_id: str,
        step_index: int,
        payload: dict[str, Any],
        parent_reference: str | None = None,
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> StateRecord:
        """Store a continuation state."""
        if not reference.strip():
            raise ValueError("State reference must not be empty.")

        if not process_id.strip():
            raise ValueError("Process ID must not be empty.")

        if not unit_id.strip():
            raise ValueError("Unit ID must not be empty.")

        if step_index < 0:
            raise ValueError("Step index must be non-negative.")

        if not isinstance(payload, dict):
            raise TypeError("State payload must be a dictionary.")

        record = StateRecord(
            reference=reference,
            process_id=process_id,
            unit_id=unit_id,
            step_index=step_index,
            payload=deepcopy(payload),
            parent_reference=parent_reference,
            metadata=deepcopy(metadata or {}),
        )

        with self._lock:
            if reference in self._records and not overwrite:
                raise StateAlreadyExistsError(
                    f"State {reference!r} already exists."
                )
            self._records[reference] = record

        return record

    def get(self, reference: str) -> StateRecord:
        """Return a deep-copied state record."""
        with self._lock:
            try:
                record = self._records[reference]
            except KeyError as exc:
                raise StateNotFoundError(
                    f"Unknown state reference: {reference}"
                ) from exc

            return StateRecord(
                reference=record.reference,
                process_id=record.process_id,
                unit_id=record.unit_id,
                step_index=record.step_index,
                payload=deepcopy(record.payload),
                parent_reference=record.parent_reference,
                metadata=deepcopy(record.metadata),
            )

    def exists(self, reference: str) -> bool:
        """Return whether a state reference exists."""
        with self._lock:
            return reference in self._records

    def delete(self, reference: str) -> None:
        """Delete a state explicitly.

        Deletion is intentionally separate from dissipation. The UFCPS
        dissipation operation preserves state; this method exists only for
        explicit lifecycle or test cleanup.
        """
        with self._lock:
            if reference not in self._records:
                raise StateNotFoundError(
                    f"Unknown state reference: {reference}"
                )
            del self._records[reference]

    def list_process(self, process_id: str) -> list[StateRecord]:
        """Return all state records belonging to a process."""
        with self._lock:
            records = [
                record
                for record in self._records.values()
                if record.process_id == process_id
            ]

        return [
            StateRecord(
                reference=record.reference,
                process_id=record.process_id,
                unit_id=record.unit_id,
                step_index=record.step_index,
                payload=deepcopy(record.payload),
                parent_reference=record.parent_reference,
                metadata=deepcopy(record.metadata),
            )
            for record in records
        ]

    def children_of(self, parent_reference: str) -> list[StateRecord]:
        """Return successor states directly linked to a parent state."""
        with self._lock:
            records = [
                record
                for record in self._records.values()
                if record.parent_reference == parent_reference
            ]

        return [
            StateRecord(
                reference=record.reference,
                process_id=record.process_id,
                unit_id=record.unit_id,
                step_index=record.step_index,
                payload=deepcopy(record.payload),
                parent_reference=record.parent_reference,
                metadata=deepcopy(record.metadata),
            )
            for record in records
        ]

    def latest_for_process(self, process_id: str) -> StateRecord | None:
        """Return the highest-step state for a process, if one exists."""
        records = self.list_process(process_id)
        if not records:
            return None
        return max(records, key=lambda record: record.step_index)

    def references(self) -> list[str]:
        """Return all state references in insertion-independent order."""
        with self._lock:
            return sorted(self._records)

    def count(self) -> int:
        """Return the number of stored states."""
        with self._lock:
            return len(self._records)

    def export_jsonable(self) -> list[dict[str, Any]]:
        """Return a JSON-serializable snapshot of the store."""
        with self._lock:
            records: Iterable[StateRecord] = list(self._records.values())

        return [
            {
                "reference": record.reference,
                "process_id": record.process_id,
                "unit_id": record.unit_id,
                "step_index": record.step_index,
                "payload": deepcopy(record.payload),
                "parent_reference": record.parent_reference,
                "metadata": deepcopy(record.metadata),
            }
            for record in records
        ]

    def clear(self) -> None:
        """Clear all stored state.

        Intended for isolated test runs and simulator reset only.
        """
        with self._lock:
            self._records.clear()


__all__ = [
    "SharedStateStore",
    "StateAlreadyExistsError",
    "StateNotFoundError",
    "StateRecord",
    "StateStoreError",
]
