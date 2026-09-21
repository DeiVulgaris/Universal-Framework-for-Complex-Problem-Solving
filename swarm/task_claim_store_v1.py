
"""UFCPS Level 2 — Persistent Task Claim Store v1.

Persistent append-oriented storage for Task Claim Engine state.

The store deliberately separates claim persistence from the claim engine:

    Claim Engine
        -> claim / reservation events
        -> append-only claim journal
        -> recoverable state snapshot

It provides:

* append-only JSONL event history;
* SHA-256 hash chaining for claim events;
* atomic current-state snapshot;
* restart recovery of claims and reservations;
* restoration of active claim state into ``TaskClaimEngine``;
* explicit handling of stale ACTIVE claims after restart;
* tamper detection;
* deterministic serialization suitable for tests and later distributed
  replication.

v1 is local persistence. It does not provide distributed consensus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from task_claim_engine_v1 import (
    Claim,
    ClaimEngineResult,
    ClaimEvent,
    ResourceReservation,
    TaskClaimEngine,
    _parse_time,
)

GENESIS_HASH = "0" * 64
SCHEMA_VERSION = "1.0"
ACTIVE_CLAIM_STATES = {
    "CLAIM_REQUESTED",
    "CLAIMED",
    "ACCEPTED",
    "RESOURCE_RESERVED",
    "ACTIVE",
    "AWAITING_RESOURCES",
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_event(payload: Mapping[str, Any], previous_hash: str) -> str:
    body = _canonical({"prev_event_hash": previous_hash, **dict(payload)})
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


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


@dataclass(frozen=True)
class StoredClaimEvent:
    event_id: str
    event_type: str
    claim_id: str
    question_id: str
    agent_id: str
    timestamp: str
    data: dict[str, Any]
    sequence: int
    prev_event_hash: str
    event_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClaimStoreSnapshot:
    schema_version: str
    store_id: str
    updated_at: str
    claims: list[dict[str, Any]]
    reservations: list[dict[str, Any]]
    resources: list[dict[str, Any]]
    question_status: dict[str, str]
    active_claim_ids: list[str]
    active_reservation_ids: list[str]
    last_event_id: Optional[str]
    last_event_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TaskClaimStore:
    """Persistent local journal and snapshot for TaskClaimEngine."""

    def __init__(self, base_path: str | Path, *, store_id: str = "UFCPS-CLAIM-STORE") -> None:
        self.base_path = Path(base_path)
        self.events_path = Path(f"{self.base_path}.events.jsonl")
        self.snapshot_path = Path(f"{self.base_path}.snapshot.json")
        self.meta_path = Path(f"{self.base_path}.meta.json")
        self.store_id = store_id
        self.base_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = GENESIS_HASH
        self._event_sequence = 0
        self._hydrate_chain_head()

    def _hydrate_chain_head(self) -> None:
        if not self.events_path.exists():
            return
        last: Optional[dict[str, Any]] = None
        with self.events_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                last = json.loads(line)
        if last:
            self._last_hash = str(last.get("event_hash", GENESIS_HASH))
            self._event_sequence = int(last.get("sequence", 0))

    def append_event(self, event: ClaimEvent | Mapping[str, Any]) -> StoredClaimEvent:
        raw = asdict(event) if isinstance(event, ClaimEvent) else dict(event)
        self._event_sequence += 1
        payload = {
            "event_id": str(raw.get("event_id", "")),
            "event_type": str(raw.get("event_type", "")),
            "claim_id": str(raw.get("claim_id", "")),
            "question_id": str(raw.get("question_id", "")),
            "agent_id": str(raw.get("agent_id", "")),
            "timestamp": str(raw.get("timestamp", _iso_now())),
            "data": dict(raw.get("data", {})),
            "sequence": self._event_sequence,
        }
        event_hash = _hash_event(payload, self._last_hash)
        stored = StoredClaimEvent(
            **payload,
            prev_event_hash=self._last_hash,
            event_hash=event_hash,
        )
        _append_line(self.events_path, stored.to_dict())
        self._last_hash = event_hash
        return stored

    def append_engine_events(
        self,
        engine: TaskClaimEngine,
        *,
        start_index: int = 0,
    ) -> int:
        events = list(engine.events)
        if start_index < 0 or start_index > len(events):
            raise ValueError("start_index outside engine event range")
        count = 0
        for event in events[start_index:]:
            self.append_event(event)
            count += 1
        return count

    def snapshot_engine(self, engine: TaskClaimEngine) -> ClaimStoreSnapshot:
        claims = [asdict(claim) for claim in engine.claims.values()]
        reservations = [asdict(reservation) for reservation in engine.reservations.values()]
        resources = [dict(resource) for resource in engine.resources.values()]
        question_status = {
            qid: engine.question_frontier_status(qid)
            for qid in sorted(engine.questions)
        }
        snapshot = ClaimStoreSnapshot(
            schema_version=SCHEMA_VERSION,
            store_id=self.store_id,
            updated_at=_iso_now(),
            claims=claims,
            reservations=reservations,
            resources=resources,
            question_status=question_status,
            active_claim_ids=sorted(
                claim.claim_id
                for claim in engine.claims.values()
                if claim.status in ACTIVE_CLAIM_STATES
            ),
            active_reservation_ids=sorted(
                reservation.reservation_id
                for reservation in engine.reservations.values()
                if reservation.status == "ACTIVE"
            ),
            last_event_id=engine.events[-1].event_id if engine.events else None,
            last_event_hash=self._last_hash,
        )
        _atomic_write_json(self.snapshot_path, snapshot.to_dict())
        _atomic_write_json(
            self.meta_path,
            {
                "schema_version": SCHEMA_VERSION,
                "store_id": self.store_id,
                "updated_at": snapshot.updated_at,
                "last_event_hash": self._last_hash,
                "last_event_id": snapshot.last_event_id,
                "event_count": self._event_sequence,
            },
        )
        return snapshot

    def persist_engine(self, engine: TaskClaimEngine, *, event_cursor: int = 0) -> ClaimStoreSnapshot:
        self.append_engine_events(engine, start_index=event_cursor)
        return self.snapshot_engine(engine)

    def load_snapshot(self) -> ClaimStoreSnapshot:
        if not self.snapshot_path.exists():
            raise FileNotFoundError(str(self.snapshot_path))
        payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        return ClaimStoreSnapshot(**payload)

    def read_events(self) -> list[StoredClaimEvent]:
        if not self.events_path.exists():
            return []
        result: list[StoredClaimEvent] = []
        with self.events_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                result.append(StoredClaimEvent(**json.loads(line)))
        return result

    def verify_integrity(self) -> dict[str, Any]:
        events = self.read_events()
        previous = GENESIS_HASH
        for expected_sequence, event in enumerate(events, start=1):
            payload = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "claim_id": event.claim_id,
                "question_id": event.question_id,
                "agent_id": event.agent_id,
                "timestamp": event.timestamp,
                "data": event.data,
                "sequence": event.sequence,
            }
            expected_hash = _hash_event(payload, previous)
            if event.sequence != expected_sequence:
                return {
                    "valid": False,
                    "reason": "sequence_mismatch",
                    "sequence": event.sequence,
                }
            if event.prev_event_hash != previous:
                return {
                    "valid": False,
                    "reason": "previous_hash_mismatch",
                    "sequence": event.sequence,
                }
            if event.event_hash != expected_hash:
                return {
                    "valid": False,
                    "reason": "event_hash_mismatch",
                    "sequence": event.sequence,
                }
            previous = event.event_hash
        return {
            "valid": True,
            "event_count": len(events),
            "last_event_hash": previous,
        }

    def restore_into_engine(
        self,
        engine: TaskClaimEngine,
        *,
        stale_active_policy: str = "RELEASE_ACTIVE_ON_RESTART",
    ) -> ClaimStoreSnapshot:
        if stale_active_policy not in {
            "RELEASE_ACTIVE_ON_RESTART",
            "KEEP_ACTIVE",
        }:
            raise ValueError("unsupported stale_active_policy")
        snapshot = self.load_snapshot()
        claims: dict[str, Claim] = {}
        for raw in snapshot.claims:
            claim = Claim(**raw)
            if stale_active_policy == "RELEASE_ACTIVE_ON_RESTART" and claim.status in ACTIVE_CLAIM_STATES:
                # ACTIVE participation is a lease, not permanent ownership.
                claim = Claim(**{**asdict(claim), "status": "RELEASED"})
            claims[claim.claim_id] = claim
        stale_claim_ids = {
            raw["claim_id"]
            for raw in snapshot.claims
            if stale_active_policy == "RELEASE_ACTIVE_ON_RESTART"
            and raw.get("status") in ACTIVE_CLAIM_STATES
        }
        restored_reservations: dict[str, ResourceReservation] = {}
        for raw in snapshot.reservations:
            reservation = ResourceReservation(**raw)
            if stale_active_policy == "RELEASE_ACTIVE_ON_RESTART" and reservation.claim_id in stale_claim_ids:
                reservation = ResourceReservation(**{
                    **asdict(reservation),
                    "status": "RELEASED",
                    "released_at": _iso_now(),
                    "reason": "released on runtime restart because the claim lease was stale",
                })
            restored_reservations[reservation.reservation_id] = reservation
        engine.claims = claims
        engine.reservations = restored_reservations
        engine.resources = {str(r["resource_id"]): dict(r) for r in snapshot.resources}
        engine.events = []
        engine._event_seq = 0
        engine._reservation_seq = 0
        if stale_active_policy == "RELEASE_ACTIVE_ON_RESTART":
            # Snapshot resources are stored after reservation. Restore their
            # capacity by releasing reservations belonging to stale claims.
            for raw in snapshot.reservations:
                if raw.get("claim_id") not in stale_claim_ids:
                    continue
                for resource_id, amount in dict(raw.get("allocations", {})).items():
                    resource = engine.resources.get(resource_id)
                    if resource is None:
                        continue
                    availability = dict(resource.get("availability", {}))
                    current = float(availability.get("available_capacity", 0))
                    availability["available_capacity"] = current + float(amount)
                    resource["availability"] = availability

        self._hydrate_chain_head()
        return snapshot

    def recoverable_active_claim_ids(self) -> list[str]:
        snapshot = self.load_snapshot()
        return list(snapshot.active_claim_ids)

    def result(self) -> dict[str, Any]:
        integrity = self.verify_integrity()
        snapshot = self.load_snapshot().to_dict() if self.snapshot_path.exists() else None
        return {
            "store_id": self.store_id,
            "schema_version": SCHEMA_VERSION,
            "integrity": integrity,
            "snapshot": snapshot,
        }


def _build_demo_engine() -> TaskClaimEngine:
    questions = [
        {"question_id": "Q-STORE-001", "status": "unresolved"},
    ]
    prospects = [
        {
            "prospect_id": "TP-Q-STORE-001-agent-A",
            "question_id": "Q-STORE-001",
            "agent_id": "agent-A",
            "required_capabilities": ["simulation"],
            "required_resources": [
                {"resource_type": "gpu", "quantity": 25, "unit": "GPU-hours"}
            ],
        }
    ]
    agents = [
        {"agent_id": "agent-A", "capabilities": ["simulation"]},
    ]
    resources = [
        {
            "resource_id": "gpu-store-001",
            "resource_type": "gpu",
            "status": "available",
            "verification": {"verification_status": "verified"},
            "availability": {"available_capacity": 100, "capacity_unit": "GPU-hours"},
        }
    ]
    return TaskClaimEngine(
        engine_id="STORE-DEMO",
        questions=questions,
        prospects=prospects,
        agents=agents,
        resources=resources,
        now="2026-09-21T20:00:00Z",
    )


def demo() -> dict[str, Any]:
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory(prefix="ufcps-claim-store-") as directory:
        path = Path(directory) / "claims"
        store = TaskClaimStore(path, store_id="STORE-DEMO")
        engine = _build_demo_engine()

        claim = engine.create_claim(
            claim_id="CL-STORE-001",
            question_id="Q-STORE-001",
            agent_id="agent-A",
            prospect_id="TP-Q-STORE-001-agent-A",
            expires_at="2026-09-21T21:00:00Z",
            method_intent="persistent demo claim",
            provenance={"discovery_event": "DISC-STORE-001"},
            requested_resources=[
                {"resource_type": "gpu", "quantity": 25, "unit": "GPU-hours"}
            ],
        )
        engine.admit_claim(claim.claim_id)
        engine.reserve_resources(claim.claim_id)
        engine.activate(claim.claim_id)
        store.persist_engine(engine, event_cursor=0)

        integrity_before = store.verify_integrity()
        snapshot_before = store.load_snapshot()

        recovered = _build_demo_engine()
        store_reloaded = TaskClaimStore(path, store_id="STORE-DEMO")
        store_reloaded.restore_into_engine(recovered)
        integrity_after = store_reloaded.verify_integrity()
        snapshot_after = store_reloaded.load_snapshot()

        assert integrity_before["valid"] is True
        assert integrity_after["valid"] is True
        assert snapshot_before.active_claim_ids == ["CL-STORE-001"]
        assert recovered.claims["CL-STORE-001"].status == "RELEASED"
        assert all(r.status != "ACTIVE" for r in recovered.reservations.values())
        assert recovered.resources["gpu-store-001"]["availability"]["available_capacity"] == 100.0

        # Tamper test: alter one event in the journal and ensure verification fails.
        events_text = store.events_path.read_text(encoding="utf-8")
        lines = events_text.splitlines()
        first = json.loads(lines[0])
        first["event_type"] = "tampered_event"
        lines[0] = json.dumps(first, ensure_ascii=False, sort_keys=True)
        store.events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tampered = store.verify_integrity()
        assert tampered["valid"] is False

        # Keep the public result based on the valid pre-tamper state.
        return {
            "status": "PASS",
            "event_count": len(store_reloaded.read_events()),
            "snapshot_claims": len(snapshot_after.claims),
            "active_claims_before_restart": snapshot_before.active_claim_ids,
            "restored_claim_status": recovered.claims["CL-STORE-001"].status,
            "resource_capacity_restored": recovered.resources["gpu-store-001"]["availability"]["available_capacity"],
            "integrity_before_tamper": integrity_before,
            "integrity_after_restart": integrity_after,
            "tamper_detection": tampered,
            "stale_active_policy": "RELEASE_ACTIVE_ON_RESTART",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run deterministic persistence demo")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")
    args = parser.parse_args()
    if not args.demo:
        parser.print_help()
        return 0
    result = demo()
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("UFCPS Task Claim Store v1")
        print("Status:", result["status"])
        print("Events:", result["event_count"])
        print("Snapshot claims:", result["snapshot_claims"])
        print("Restored claim status:", result["restored_claim_status"])
        print("Resource capacity restored:", result["resource_capacity_restored"])
        print("Integrity before tamper:", result["integrity_before_tamper"]["valid"])
        print("Integrity after restart:", result["integrity_after_restart"]["valid"])
        print("Tamper detected:", not result["tamper_detection"]["valid"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
