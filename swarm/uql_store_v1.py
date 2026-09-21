
"""UFCPS Level 2 — Persistent Unresolved Question Ledger Store v1.

A small local persistence layer for the UQL protocol.

Design principles
-----------------
* question history is append-oriented and never silently overwritten;
* current frontier is mutable and may be rebuilt from the event log;
* event history is hash-chained for tamper-evident local verification;
* large external evidence may be represented by references/hashes only;
* the store is a persistence mechanism, not a scheduler or research judge;
* atomic snapshot replacement is used for crash-safe frontier updates.

Storage layout for ``base_path``::

    <base_path>.events.jsonl
    <base_path>.frontier.json

The implementation is intentionally local and deterministic in v1. A later
network/distributed backend can preserve the same semantic API and event model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

SCHEMA_VERSION = "uql-store-v1"
GENESIS_HASH = "0" * 64
TERMINAL_STATUSES = {"resolved", "abandoned_with_reason", "cancelled", "invalid"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_event(prev_hash: str, event_without_hash: Mapping[str, Any]) -> str:
    payload = f"{prev_hash}|{_canonical(dict(event_without_hash))}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_safe(v) for v in value]
    return value


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


@dataclass(frozen=True)
class UQLEvent:
    event_id: str
    event_type: str
    question_id: str
    process_id: str
    sequence: int
    payload: dict[str, Any]
    prev_event_hash: str
    event_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuestionFrontier:
    question_id: str
    process_id: str
    formulation: str
    status: str = "unresolved"
    current_procedural_unit: Optional[str] = None
    current_state: dict[str, Any] = field(default_factory=dict)
    unresolved_difference: str = ""
    active_constraints: list[str] = field(default_factory=list)
    attempted_operations: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    results: list[str] = field(default_factory=list)
    negative_results: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    uncertainty: str = ""
    evidence_references: list[str] = field(default_factory=list)
    contributing_agents: list[str] = field(default_factory=list)
    contributing_resources: list[str] = field(default_factory=list)
    parent_questions: list[str] = field(default_factory=list)
    derived_questions: list[str] = field(default_factory=list)
    branch_history: list[str] = field(default_factory=list)
    next_required_operation: str = ""
    required_capabilities: list[str] = field(default_factory=list)
    required_resources: list[dict[str, Any]] = field(default_factory=list)
    continuation_conditions: list[str] = field(default_factory=list)
    candidate_carriers: list[str] = field(default_factory=list)
    generation: int = 0
    last_event_id: Optional[str] = None
    last_event_hash: str = GENESIS_HASH
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class UQLStore:
    """Local append-only UQL event store with a mutable recoverable frontier."""

    def __init__(self, base_path: str | Path) -> None:
        base = Path(base_path)
        self.base_path = base
        self.events_path = Path(f"{base}.events.jsonl")
        self.frontier_path = Path(f"{base}.frontier.json")
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        self._frontier: dict[str, QuestionFrontier] = {}
        self._load_frontier()

    def _load_frontier(self) -> None:
        if not self.frontier_path.exists():
            self._frontier = {}
            return
        with self.frontier_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported UQL frontier schema version")
        entries = payload.get("frontier", {})
        self._frontier = {
            question_id: QuestionFrontier(**entry)
            for question_id, entry in entries.items()
        }

    def _save_frontier(self) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "frontier": {
                question_id: frontier.to_dict()
                for question_id, frontier in sorted(self._frontier.items())
            },
        }
        _atomic_write_json(self.frontier_path, payload)

    def _read_events(self) -> list[UQLEvent]:
        if not self.events_path.exists():
            return []
        events: list[UQLEvent] = []
        with self.events_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                    events.append(UQLEvent(**raw))
                except Exception as exc:
                    raise ValueError(
                        f"Invalid UQL event at line {line_number}: {exc}"
                    ) from exc
        return events

    @property
    def frontier(self) -> dict[str, QuestionFrontier]:
        return dict(self._frontier)

    def get_frontier(self, question_id: str) -> QuestionFrontier:
        try:
            return self._frontier[question_id]
        except KeyError as exc:
            raise KeyError(f"Unknown question_id: {question_id}") from exc

    def list_active(self) -> list[QuestionFrontier]:
        return [
            item
            for item in self._frontier.values()
            if item.status not in TERMINAL_STATUSES
        ]

    def _next_sequence_and_prev(self) -> tuple[int, str]:
        events = self._read_events()
        if not events:
            return 1, GENESIS_HASH
        last = events[-1]
        return last.sequence + 1, last.event_hash

    def append_event(
        self,
        *,
        event_type: str,
        question_id: str,
        process_id: str,
        payload: Mapping[str, Any],
    ) -> UQLEvent:
        event_type = str(event_type).strip()
        question_id = str(question_id).strip()
        process_id = str(process_id).strip()
        if not event_type or not question_id or not process_id:
            raise ValueError("event_type, question_id and process_id are required")

        sequence, prev_hash = self._next_sequence_and_prev()
        event_id = f"EVT-{sequence:08d}"
        raw = {
            "event_id": event_id,
            "event_type": event_type,
            "question_id": question_id,
            "process_id": process_id,
            "sequence": sequence,
            "payload": _safe(dict(payload)),
            "prev_event_hash": prev_hash,
        }
        event_hash = _hash_event(prev_hash, raw)
        event = UQLEvent(event_hash=event_hash, **raw)

        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(_canonical(event.to_dict()) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event

    def create_question(
        self,
        *,
        question_id: str,
        process_id: str,
        formulation: str,
        metadata: Optional[Mapping[str, Any]] = None,
        required_capabilities: Optional[Iterable[str]] = None,
        required_resources: Optional[Iterable[Mapping[str, Any]]] = None,
    ) -> UQLEvent:
        if question_id in self._frontier:
            raise ValueError(f"question already exists: {question_id}")
        frontier = QuestionFrontier(
            question_id=question_id,
            process_id=process_id,
            formulation=formulation,
            required_capabilities=[str(x) for x in (required_capabilities or [])],
            required_resources=[dict(x) for x in (required_resources or [])],
            metadata=dict(metadata or {}),
        )
        event = self.append_event(
            event_type="question_created",
            question_id=question_id,
            process_id=process_id,
            payload=frontier.to_dict(),
        )
        frontier.last_event_id = event.event_id
        frontier.last_event_hash = event.event_hash
        self._frontier[question_id] = frontier
        self._save_frontier()
        return event

    def update_frontier(
        self,
        *,
        question_id: str,
        event_type: str,
        patch: Mapping[str, Any],
        process_id: Optional[str] = None,
    ) -> UQLEvent:
        current = self.get_frontier(question_id)
        new_state = current.to_dict()
        for key, value in patch.items():
            if key not in new_state:
                raise ValueError(f"Unknown frontier field: {key}")
            new_state[key] = _safe(value)

        pid = process_id or current.process_id
        event = self.append_event(
            event_type=event_type,
            question_id=question_id,
            process_id=pid,
            payload={"patch": _safe(dict(patch)), "resulting_frontier": new_state},
        )
        new_state["last_event_id"] = event.event_id
        new_state["last_event_hash"] = event.event_hash
        self._frontier[question_id] = QuestionFrontier(**new_state)
        self._save_frontier()
        return event

    def append_history(
        self,
        *,
        question_id: str,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> UQLEvent:
        """Append information without changing the current frontier fields."""
        current = self.get_frontier(question_id)
        event = self.append_event(
            event_type=event_type,
            question_id=question_id,
            process_id=current.process_id,
            payload=payload,
        )
        current.last_event_id = event.event_id
        current.last_event_hash = event.event_hash
        self._frontier[question_id] = current
        self._save_frontier()
        return event

    def derive_question(
        self,
        *,
        parent_question_id: str,
        child_question_id: str,
        formulation: str,
        process_id: Optional[str] = None,
        unresolved_difference: str = "",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> UQLEvent:
        parent = self.get_frontier(parent_question_id)
        if child_question_id in self._frontier:
            raise ValueError(f"question already exists: {child_question_id}")
        child = QuestionFrontier(
            question_id=child_question_id,
            process_id=process_id or parent.process_id,
            formulation=formulation,
            unresolved_difference=unresolved_difference,
            parent_questions=[parent_question_id],
            generation=parent.generation + 1,
            metadata=dict(metadata or {}),
        )
        event = self.append_event(
            event_type="question_derived",
            question_id=child_question_id,
            process_id=child.process_id,
            payload={
                "parent_question_id": parent_question_id,
                "child_frontier": child.to_dict(),
            },
        )
        child.last_event_id = event.event_id
        child.last_event_hash = event.event_hash
        self._frontier[child_question_id] = child

        parent.derived_questions.append(child_question_id)
        parent.last_event_id = event.event_id
        parent.last_event_hash = event.event_hash
        self._frontier[parent_question_id] = parent
        self._save_frontier()
        return event

    def recover_frontier_from_events(self) -> dict[str, QuestionFrontier]:
        """Replay the event log into a fresh frontier representation."""
        rebuilt: dict[str, QuestionFrontier] = {}
        for event in self._read_events():
            payload = event.payload
            if event.event_type == "question_created":
                raw = dict(payload)
                raw["last_event_id"] = event.event_id
                raw["last_event_hash"] = event.event_hash
                rebuilt[event.question_id] = QuestionFrontier(**raw)
                continue
            if event.event_type == "question_derived":
                # A derivation event creates the child frontier and records the
                # parent->child relation atomically. The child therefore does
                # not need to exist in the replay map before this event.
                raw = dict(payload["child_frontier"])
                raw["last_event_id"] = event.event_id
                raw["last_event_hash"] = event.event_hash
                rebuilt[event.question_id] = QuestionFrontier(**raw)
                parent_id = str(payload["parent_question_id"])
                if parent_id not in rebuilt:
                    raise ValueError(
                        f"Derived-question event references unknown parent: {parent_id}"
                    )
                parent = rebuilt[parent_id]
                if event.question_id not in parent.derived_questions:
                    parent.derived_questions.append(event.question_id)
                parent.last_event_id = event.event_id
                parent.last_event_hash = event.event_hash
                rebuilt[parent_id] = parent
                continue
            if event.question_id not in rebuilt:
                raise ValueError(
                    f"Event references unknown question: {event.question_id}"
                )
            current = rebuilt[event.question_id]
            if event.event_type in {"frontier_patch", "frontier_update"}:
                patch = payload.get("patch", {})
                raw = current.to_dict()
                raw.update(patch)
                raw["last_event_id"] = event.event_id
                raw["last_event_hash"] = event.event_hash
                rebuilt[event.question_id] = QuestionFrontier(**raw)
                continue
            # Generic history events leave the frontier fields intact while
            # advancing the audit pointer.
            current.last_event_id = event.event_id
            current.last_event_hash = event.event_hash
            rebuilt[event.question_id] = current
        return rebuilt

    def verify_integrity(self, *, replay: bool = True) -> dict[str, Any]:
        events = self._read_events()
        errors: list[str] = []
        prev_hash = GENESIS_HASH
        expected_sequence = 1
        for event in events:
            if event.sequence != expected_sequence:
                errors.append(
                    f"sequence mismatch: expected {expected_sequence}, got {event.sequence}"
                )
            if event.prev_event_hash != prev_hash:
                errors.append(
                    f"prev hash mismatch at {event.event_id}"
                )
            raw = event.to_dict()
            raw.pop("event_hash")
            recalculated = _hash_event(event.prev_event_hash, raw)
            if recalculated != event.event_hash:
                errors.append(f"event hash mismatch at {event.event_id}")
            prev_hash = event.event_hash
            expected_sequence += 1

        replay_equal = True
        if replay:
            rebuilt = self.recover_frontier_from_events()
            current = {
                key: value.to_dict()
                for key, value in self._frontier.items()
            }
            replayed = {
                key: value.to_dict()
                for key, value in rebuilt.items()
            }
            replay_equal = current == replayed
            if not replay_equal:
                errors.append("frontier snapshot differs from replayed event log")

        return {
            "schema_version": SCHEMA_VERSION,
            "event_count": len(events),
            "question_count": len(self._frontier),
            "active_question_count": len(self.list_active()),
            "last_event_hash": prev_hash,
            "hash_chain_valid": not any("hash" in error or "sequence" in error for error in errors),
            "frontier_replay_equal": replay_equal,
            "valid": not errors,
            "errors": errors,
        }

    def persist_frontier_rebuild(self) -> dict[str, Any]:
        rebuilt = self.recover_frontier_from_events()
        self._frontier = rebuilt
        self._save_frontier()
        return self.verify_integrity(replay=False)

    def events_for_question(self, question_id: str) -> list[UQLEvent]:
        return [event for event in self._read_events() if event.question_id == question_id]


def _demo() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ufcps-uql-") as temp_dir:
        base = Path(temp_dir) / "uql"
        store = UQLStore(base)
        created = store.create_question(
            question_id="Q-UQL-001",
            process_id="PROC-UQL-001",
            formulation="Can the next carrier continue from a persisted unresolved frontier?",
            required_capabilities=["analysis", "simulation"],
            required_resources=[{"resource_type": "gpu", "quantity": 4, "unit": "GPU-hours"}],
            metadata={"origin": "uql_demo"},
        )
        store.update_frontier(
            question_id="Q-UQL-001",
            event_type="frontier_update",
            patch={
                "status": "blocked",
                "unresolved_difference": "Current carrier cannot continue with available resources.",
                "negative_results": ["local continuation attempt unavailable"],
                "next_required_operation": "resource_discovery",
            },
        )
        store.append_history(
            question_id="Q-UQL-001",
            event_type="deadlock_recorded",
            payload={
                "deadlock_id": "DL-UQL-001",
                "boundary_completeness": 1.0,
                "constraint_completeness": 1.0,
                "evidence_reference": "evidence://uql-demo-001",
            },
        )
        store.update_frontier(
            question_id="Q-UQL-001",
            event_type="frontier_update",
            patch={"status": "delegated", "candidate_carriers": ["agent-next-001"]},
        )
        derived = store.derive_question(
            parent_question_id="Q-UQL-001",
            child_question_id="Q-UQL-002",
            formulation="What resource substitution permits continuation?",
            unresolved_difference="Required compute is absent from the current resource set.",
        )
        integrity_before = store.verify_integrity()

        # Simulate process restart: reconstruct the store from disk only.
        restarted = UQLStore(base)
        rebuilt = restarted.persist_frontier_rebuild()
        integrity_after = restarted.verify_integrity()

        assert created.event_id == "EVT-00000001"
        assert derived.event_id == "EVT-00000005"
        assert integrity_before["valid"] is True
        assert integrity_after["valid"] is True
        assert len(restarted.events_for_question("Q-UQL-001")) == 4
        assert restarted.get_frontier("Q-UQL-002").parent_questions == ["Q-UQL-001"]
        assert restarted.get_frontier("Q-UQL-001").derived_questions == ["Q-UQL-002"]

        return {
            "status": "PASS",
            "event_file": str(store.events_path),
            "frontier_file": str(store.frontier_path),
            "integrity_before_restart": integrity_before,
            "integrity_after_restart": integrity_after,
            "rebuilt": rebuilt,
            "active_questions": [item.question_id for item in restarted.list_active()],
            "event_counts": {
                "Q-UQL-001": len(restarted.events_for_question("Q-UQL-001")),
                "Q-UQL-002": len(restarted.events_for_question("Q-UQL-002")),
            },
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run persistence demo")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.demo:
        parser.print_help()
        return 0
    result = _demo()
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("UFCPS UQL Store v1")
        print("Status:", result["status"])
        print("Integrity before restart:", result["integrity_before_restart"]["valid"])
        print("Integrity after restart:", result["integrity_after_restart"]["valid"])
        print("Active questions:", result["active_questions"])
        print("Event counts:", result["event_counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
