
"""UFCPS Level 2 — Event Audit Bus v1.

Unified append-oriented event history for the distributed swarm.

The Audit Bus is an observability and provenance layer.  It does not decide
research validity, allocate resources, approve claims, calculate rewards, or
terminate processes.  It accepts events emitted by those subsystems and makes
one causal history available for inspection and later process replay.

Canonical sources supported by v1:

    UQL / CLAIM / RESOURCE / EXECUTION / VERIFICATION / DEADLOCK / ECONOMICS / PAYMENT

Storage layout for ``base_path``::

    <base_path>.events.jsonl
    <base_path>.meta.json

The event chain is tamper-evident through SHA-256 chaining.  v1 is local and
single-writer oriented; it does not provide distributed consensus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

GENESIS_HASH = "0" * 64
SCHEMA_VERSION = "audit-bus-v1"
VALID_DOMAINS = {
    "UQL",
    "CLAIM",
    "RESOURCE",
    "EXECUTION",
    "VERIFICATION",
    "DEADLOCK",
    "ECONOMICS",
    "PAYMENT",
    "RUNTIME",
}
VALID_VERIFICATION_STATUSES = {"unknown", "unverified", "verified", "rejected"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_event(previous_hash: str, payload: Mapping[str, Any]) -> str:
    body = f"{previous_hash}|{_canonical(dict(payload))}".encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _append_line(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, Mapping)):
        return [str(item) for item in value if str(item)]
    return []


@dataclass(frozen=True)
class AuditEvent:
    """Canonical event stored by the Audit Bus."""

    event_id: str
    event_type: str
    domain: str
    source_system: str
    source_event_id: str
    process_id: str
    question_id: str
    actor_id: str
    resource_ids: list[str]
    timestamp: str
    causal_parent_event_id: Optional[str]
    verification_status: str
    payload: dict[str, Any]
    sequence: int
    prev_hash: str
    event_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditQueryResult:
    """Filtered event-history result."""

    events: list[dict[str, Any]]
    total: int
    filters: dict[str, Any]


@dataclass(frozen=True)
class AuditBusResult:
    """Machine-readable state and integrity summary."""

    bus_id: str
    schema_version: str
    event_count: int
    domains: dict[str, int]
    processes: list[str]
    integrity: dict[str, Any]
    last_event_id: Optional[str]
    last_event_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EventAuditBus:
    """Append-only local event bus with tamper-evident history."""

    def __init__(self, base_path: str | Path, *, bus_id: str = "UFCPS-AUDIT-BUS") -> None:
        self.base_path = Path(base_path)
        self.events_path = Path(f"{self.base_path}.events.jsonl")
        self.meta_path = Path(f"{self.base_path}.meta.json")
        self.bus_id = bus_id
        self.base_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = GENESIS_HASH
        self._sequence = 0
        self._source_index: dict[tuple[str, str], AuditEvent] = {}
        self._hydrate()

    def _hydrate(self) -> None:
        if not self.events_path.exists():
            return
        for raw in self._read_raw_events():
            event = AuditEvent(**raw)
            key = (event.source_system, event.source_event_id)
            if event.source_event_id:
                self._source_index[key] = event
            self._sequence = max(self._sequence, event.sequence)
            self._last_hash = event.event_hash

    def _read_raw_events(self) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.events_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def _validate_event_fields(
        self,
        *,
        domain: str,
        source_system: str,
        event_type: str,
        process_id: str,
        question_id: str,
        verification_status: str,
    ) -> None:
        if domain not in VALID_DOMAINS:
            raise ValueError(f"unsupported audit domain: {domain}")
        if not _text(source_system):
            raise ValueError("source_system is required")
        if not _text(event_type):
            raise ValueError("event_type is required")
        if not _text(process_id):
            raise ValueError("process_id is required")
        if not _text(question_id):
            raise ValueError("question_id is required")
        if verification_status not in VALID_VERIFICATION_STATUSES:
            raise ValueError(f"unsupported verification_status: {verification_status}")

    def append(
        self,
        *,
        event_type: str,
        domain: str,
        source_system: str,
        source_event_id: str,
        process_id: str,
        question_id: str,
        actor_id: str = "",
        resource_ids: Sequence[str] = (),
        timestamp: Optional[str] = None,
        causal_parent_event_id: Optional[str] = None,
        verification_status: str = "unknown",
        payload: Optional[Mapping[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> AuditEvent:
        """Append an event, or return the existing event for duplicate source IDs."""
        self._validate_event_fields(
            domain=domain,
            source_system=source_system,
            event_type=event_type,
            process_id=process_id,
            question_id=question_id,
            verification_status=verification_status,
        )
        source_event_id = _text(source_event_id)
        if not source_event_id:
            raise ValueError("source_event_id is required for audit idempotency")

        existing = self._source_index.get((source_system, source_event_id))
        if existing is not None:
            return existing

        if causal_parent_event_id:
            if not self.has_event(causal_parent_event_id):
                raise ValueError(f"unknown causal_parent_event_id: {causal_parent_event_id}")

        self._sequence += 1
        payload_data = dict(payload or {})
        timestamp = timestamp or _now_iso()
        normalized_resources = sorted(set(_string_list(resource_ids)))
        event_id = event_id or f"AE-{uuid.uuid4().hex[:16]}"

        body = {
            "event_id": event_id,
            "event_type": event_type,
            "domain": domain,
            "source_system": source_system,
            "source_event_id": source_event_id,
            "process_id": process_id,
            "question_id": question_id,
            "actor_id": actor_id,
            "resource_ids": normalized_resources,
            "timestamp": timestamp,
            "causal_parent_event_id": causal_parent_event_id,
            "verification_status": verification_status,
            "payload": payload_data,
            "sequence": self._sequence,
        }
        event_hash = _hash_event(self._last_hash, body)
        event = AuditEvent(
            **body,
            prev_hash=self._last_hash,
            event_hash=event_hash,
        )
        _append_line(self.events_path, event.to_dict())
        self._last_hash = event_hash
        self._source_index[(source_system, source_event_id)] = event
        self._write_meta(event)
        return event

    def append_many(self, events: Iterable[Mapping[str, Any] | AuditEvent]) -> list[AuditEvent]:
        """Append a sequence while preserving the supplied causal order."""
        appended: list[AuditEvent] = []
        for raw in events:
            data = raw.to_dict() if isinstance(raw, AuditEvent) else dict(raw)
            appended.append(self.append(**data_without_chain_fields(data)))
        return appended

    def _write_meta(self, event: AuditEvent) -> None:
        _atomic_write_json(
            self.meta_path,
            {
                "schema_version": SCHEMA_VERSION,
                "bus_id": self.bus_id,
                "updated_at": _now_iso(),
                "event_count": self._sequence,
                "last_event_id": event.event_id,
                "last_event_hash": event.event_hash,
            },
        )

    def has_event(self, event_id: str) -> bool:
        return any(event.event_id == event_id for event in self.events())

    def events(self) -> list[AuditEvent]:
        return [AuditEvent(**raw) for raw in self._read_raw_events()]

    def events_for_process(self, process_id: str) -> list[AuditEvent]:
        return [event for event in self.events() if event.process_id == process_id]

    def query(
        self,
        *,
        process_id: Optional[str] = None,
        question_id: Optional[str] = None,
        domain: Optional[str] = None,
        actor_id: Optional[str] = None,
        event_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        verification_status: Optional[str] = None,
    ) -> AuditQueryResult:
        events = self.events()
        if process_id:
            events = [e for e in events if e.process_id == process_id]
        if question_id:
            events = [e for e in events if e.question_id == question_id]
        if domain:
            events = [e for e in events if e.domain == domain]
        if actor_id:
            events = [e for e in events if e.actor_id == actor_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if resource_id:
            events = [e for e in events if resource_id in e.resource_ids]
        if verification_status:
            events = [e for e in events if e.verification_status == verification_status]
        filters = {
            "process_id": process_id,
            "question_id": question_id,
            "domain": domain,
            "actor_id": actor_id,
            "event_type": event_type,
            "resource_id": resource_id,
            "verification_status": verification_status,
        }
        return AuditQueryResult(
            events=[event.to_dict() for event in events],
            total=len(events),
            filters=filters,
        )

    def verify_integrity(self) -> dict[str, Any]:
        events = self.events()
        previous = GENESIS_HASH
        for expected_sequence, event in enumerate(events, start=1):
            body = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "domain": event.domain,
                "source_system": event.source_system,
                "source_event_id": event.source_event_id,
                "process_id": event.process_id,
                "question_id": event.question_id,
                "actor_id": event.actor_id,
                "resource_ids": event.resource_ids,
                "timestamp": event.timestamp,
                "causal_parent_event_id": event.causal_parent_event_id,
                "verification_status": event.verification_status,
                "payload": event.payload,
                "sequence": event.sequence,
            }
            if event.sequence != expected_sequence:
                return {"valid": False, "reason": "sequence_mismatch", "sequence": event.sequence}
            if event.prev_hash != previous:
                return {"valid": False, "reason": "previous_hash_mismatch", "sequence": event.sequence}
            expected_hash = _hash_event(previous, body)
            if event.event_hash != expected_hash:
                return {"valid": False, "reason": "event_hash_mismatch", "sequence": event.sequence}
            previous = event.event_hash
        return {
            "valid": True,
            "event_count": len(events),
            "last_event_hash": previous,
        }

    def result(self) -> AuditBusResult:
        events = self.events()
        domains: dict[str, int] = {}
        processes: set[str] = set()
        for event in events:
            domains[event.domain] = domains.get(event.domain, 0) + 1
            processes.add(event.process_id)
        integrity = self.verify_integrity()
        return AuditBusResult(
            bus_id=self.bus_id,
            schema_version=SCHEMA_VERSION,
            event_count=len(events),
            domains=dict(sorted(domains.items())),
            processes=sorted(processes),
            integrity=integrity,
            last_event_id=events[-1].event_id if events else None,
            last_event_hash=events[-1].event_hash if events else GENESIS_HASH,
        )

    def export_snapshot(self, path: str | Path) -> None:
        """Write a read-only inspection snapshot; it is not the authoritative log."""
        snapshot = {
            "schema_version": SCHEMA_VERSION,
            "bus_id": self.bus_id,
            "generated_at": _now_iso(),
            "events": [event.to_dict() for event in self.events()],
            "integrity": self.verify_integrity(),
        }
        _atomic_write_json(Path(path), snapshot)


def data_without_chain_fields(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Remove stored chain fields before appending through the public API."""
    ignored = {"sequence", "prev_hash", "event_hash"}
    return {key: value for key, value in dict(raw).items() if key not in ignored}


def _uql_event(bus: EventAuditBus, source_event_id: str, process_id: str, question_id: str, parent: Optional[str], event_type: str, payload: Mapping[str, Any]) -> AuditEvent:
    return bus.append(
        event_type=event_type,
        domain="UQL",
        source_system="uql_store_v1",
        source_event_id=source_event_id,
        process_id=process_id,
        question_id=question_id,
        causal_parent_event_id=parent,
        verification_status="verified",
        payload=payload,
    )


def demo() -> dict[str, Any]:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="ufcps-audit-bus-") as directory:
        path = Path(directory) / "audit"
        bus = EventAuditBus(path, bus_id="AUDIT-DEMO")

        e1 = _uql_event(
            bus, "UQL-001", "PROC-001", "Q-001", None,
            "question_created", {"status": "unresolved"},
        )
        e2 = bus.append(
            event_type="claim_accepted", domain="CLAIM", source_system="task_claim_engine_v1",
            source_event_id="CL-001-ACCEPT", process_id="PROC-001", question_id="Q-001",
            actor_id="agent-A", causal_parent_event_id=e1.event_id,
            verification_status="verified", payload={"claim_id": "CL-001"},
        )
        e3 = bus.append(
            event_type="resource_reserved", domain="RESOURCE", source_system="task_claim_engine_v1",
            source_event_id="RES-001", process_id="PROC-001", question_id="Q-001",
            actor_id="agent-A", resource_ids=["gpu-001"], causal_parent_event_id=e2.event_id,
            verification_status="verified", payload={"allocation": "25 GPU-hours"},
        )
        e4 = bus.append(
            event_type="execution_verified", domain="VERIFICATION", source_system="compute_verifier_v1",
            source_event_id="VER-001", process_id="PROC-001", question_id="Q-001",
            actor_id="validator-001", resource_ids=["gpu-001"], causal_parent_event_id=e3.event_id,
            verification_status="verified", payload={"verified_compute": 25},
        )
        e5 = bus.append(
            event_type="provider_reward_calculated", domain="ECONOMICS", source_system="provider_reward_v1",
            source_event_id="ECO-001", process_id="PROC-001", question_id="Q-001",
            actor_id="provider-001", resource_ids=["gpu-001"], causal_parent_event_id=e4.event_id,
            verification_status="verified", payload={"reward_rc": "10", "author_royalty": "0.0001"},
        )
        e6 = bus.append(
            event_type="payment_projected", domain="PAYMENT", source_system="payment_router_v1",
            source_event_id="PAY-001", process_id="PROC-001", question_id="Q-001",
            actor_id="provider-001", resource_ids=["gpu-001"], causal_parent_event_id=e5.event_id,
            verification_status="unverified", payload={"rail": "resource_credits", "execution": "projection_only"},
        )
        e7 = bus.append(
            event_type="deadlock_recorded", domain="DEADLOCK", source_system="execution_pipeline_v1",
            source_event_id="DL-001", process_id="PROC-001", question_id="Q-001",
            actor_id="agent-A", resource_ids=["gpu-001"], causal_parent_event_id=e6.event_id,
            verification_status="verified", payload={"deadlock_ref": "deadlock-001", "information_density": "0.83"},
        )
        e8 = bus.append(
            event_type="continuation_created", domain="RUNTIME", source_system="swarm_runtime_v1",
            source_event_id="CONT-001", process_id="PROC-001", question_id="Q-001",
            actor_id="runtime-001", causal_parent_event_id=e7.event_id,
            verification_status="verified", payload={"next_unit": "P-002"},
        )

        # Duplicate source event is idempotent.
        duplicate = bus.append(
            event_type="claim_accepted", domain="CLAIM", source_system="task_claim_engine_v1",
            source_event_id="CL-001-ACCEPT", process_id="PROC-001", question_id="Q-001",
            actor_id="agent-A", causal_parent_event_id=e1.event_id,
            verification_status="verified", payload={"claim_id": "CL-001"},
        )
        assert duplicate.event_id == e2.event_id

        integrity = bus.verify_integrity()
        process_events = bus.events_for_process("PROC-001")
        query = bus.query(process_id="PROC-001", domain="ECONOMICS")
        assert integrity["valid"] is True
        assert len(process_events) == 8
        assert query.total == 1
        assert process_events[-1].causal_parent_event_id == e7.event_id
        assert process_events[1].actor_id == "agent-A"
        assert process_events[2].resource_ids == ["gpu-001"]

        # Restart recovery keeps the chain head and source-id index.
        reloaded = EventAuditBus(path, bus_id="AUDIT-DEMO")
        restart_integrity = reloaded.verify_integrity()
        assert restart_integrity["valid"] is True
        assert len(reloaded.events()) == 8
        assert reloaded.append(
            event_type="claim_accepted", domain="CLAIM", source_system="task_claim_engine_v1",
            source_event_id="CL-001-ACCEPT", process_id="PROC-001", question_id="Q-001",
            actor_id="agent-A", causal_parent_event_id=e1.event_id,
            verification_status="verified", payload={"claim_id": "CL-001"},
        ).event_id == e2.event_id

        # Tamper detection is intentionally demonstrated on a copy of the journal.
        rows = bus._read_raw_events()
        rows[3]["payload"]["verified_compute"] = 999
        bus.events_path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
            encoding="utf-8",
        )
        tampered = bus.verify_integrity()
        assert tampered["valid"] is False

        # Report valid-state facts from before tampering.
        return {
            "status": "PASS",
            "event_count_before_tamper": 8,
            "domain_count": len(bus.result().domains),
            "domains_before_tamper": {
                "UQL": 1,
                "CLAIM": 1,
                "RESOURCE": 1,
                "VERIFICATION": 1,
                "ECONOMICS": 1,
                "PAYMENT": 1,
                "DEADLOCK": 1,
                "RUNTIME": 1,
            },
            "process_events": len(process_events),
            "economic_query_events": query.total,
            "restart_integrity": restart_integrity,
            "idempotent_source_event": True,
            "tamper_detection": tampered,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run deterministic audit-bus demo")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")
    parser.add_argument("--path", help="audit base path for manual inspection")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.demo:
        result = demo()
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("UFCPS Event Audit Bus v1")
            print("Status:", result["status"])
            print("Events before tamper:", result["event_count_before_tamper"])
            print("Domains:", result["domains_before_tamper"])
            print("Process events:", result["process_events"])
            print("Economic query events:", result["economic_query_events"])
            print("Restart integrity:", result["restart_integrity"]["valid"])
            print("Idempotent source event:", result["idempotent_source_event"])
            print("Tamper detected:", not result["tamper_detection"]["valid"])
        return 0
    if args.path:
        bus = EventAuditBus(args.path)
        print(json.dumps(bus.result().to_dict(), ensure_ascii=False, indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
