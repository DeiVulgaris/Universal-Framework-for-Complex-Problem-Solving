
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

from checkpointed_event_store_v1 import CheckpointedEventStore

from task_claim_engine_v1 import (
    Claim,
    ClaimEngineResult,
    ClaimEvent,
    ResourceReservation,
    TaskClaimEngine,
    _parse_time,
    _resource_capacity,
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

    def __init__(
        self,
        base_path: str | Path,
        *,
        store_id: str = "UFCPS-CLAIM-STORE",
        persistence_mode: str = "legacy",
        journal_batch_size: int = 1,
        checkpoint_interval: int = 1,
        durable: bool = True,
    ) -> None:
        if persistence_mode not in {"legacy", "checkpointed"}:
            raise ValueError("persistence_mode must be 'legacy' or 'checkpointed'")
        if journal_batch_size < 1:
            raise ValueError("journal_batch_size must be >= 1")
        if checkpoint_interval < 1:
            raise ValueError("checkpoint_interval must be >= 1")

        self.base_path = Path(base_path)
        self.store_id = store_id
        self.persistence_mode = persistence_mode
        self.journal_batch_size = int(journal_batch_size)
        self.checkpoint_interval = int(checkpoint_interval)
        self.durable = bool(durable)
        self.base_path.parent.mkdir(parents=True, exist_ok=True)

        # Checkpointed mode deliberately uses sidecar files so an existing
        # legacy store can coexist with the optimized experimental store.
        self._event_store: Optional[CheckpointedEventStore] = None
        if self.persistence_mode == "checkpointed":
            cp_base = Path(f"{self.base_path}.cp")
            self._event_store = CheckpointedEventStore(
                cp_base,
                journal_batch_size=self.journal_batch_size,
                checkpoint_interval=self.checkpoint_interval,
                durable=self.durable,
            )
            self.events_path = self._event_store.events_path
            self.snapshot_path = self._event_store.checkpoint_path
            self.meta_path = Path(f"{cp_base}.meta.json")
        else:
            self.events_path = Path(f"{self.base_path}.events.jsonl")
            self.snapshot_path = Path(f"{self.base_path}.snapshot.json")
            self.meta_path = Path(f"{self.base_path}.meta.json")

        self._last_hash = GENESIS_HASH
        self._event_sequence = 0
        self._hydrate_chain_head()

    def _hydrate_chain_head(self) -> None:
        if self.persistence_mode == "checkpointed":
            assert self._event_store is not None
            self._last_hash = self._event_store.last_event_hash
            self._event_sequence = self._event_store.event_count
            return
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
        if self.persistence_mode == "checkpointed":
            assert self._event_store is not None
            event_id = str(raw.get("event_id", ""))
            payload = {
                "event_type": str(raw.get("event_type", "")),
                "claim_id": str(raw.get("claim_id", "")),
                "question_id": str(raw.get("question_id", "")),
                "agent_id": str(raw.get("agent_id", "")),
                "timestamp": str(raw.get("timestamp", _iso_now())),
                "data": dict(raw.get("data", {})),
            }
            stored = self._event_store.append(event_id=event_id, payload=payload)
            return self._decode_checkpointed_event(stored)

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

    def _decode_checkpointed_event(self, event: Any) -> StoredClaimEvent:
        payload = dict(event.payload)
        return StoredClaimEvent(
            event_id=event.event_id,
            event_type=str(payload.get("event_type", "")),
            claim_id=str(payload.get("claim_id", "")),
            question_id=str(payload.get("question_id", "")),
            agent_id=str(payload.get("agent_id", "")),
            timestamp=str(payload.get("timestamp", "")),
            data=dict(payload.get("data", {})),
            sequence=event.sequence,
            prev_event_hash=event.prev_hash,
            event_hash=event.event_hash,
        )

    def append_engine_events(
        self,
        engine: TaskClaimEngine,
        *,
        start_index: int = 0,
        checkpoint_state: Optional[Mapping[str, Any]] = None,
    ) -> int:
        events = list(engine.events)
        if start_index < 0 or start_index > len(events):
            raise ValueError("start_index outside engine event range")
        count = 0
        if self.persistence_mode == "checkpointed":
            assert self._event_store is not None
            for event in events[start_index:]:
                raw = asdict(event)
                payload = {
                    "event_type": str(raw.get("event_type", "")),
                    "claim_id": str(raw.get("claim_id", "")),
                    "question_id": str(raw.get("question_id", "")),
                    "agent_id": str(raw.get("agent_id", "")),
                    "timestamp": str(raw.get("timestamp", _iso_now())),
                    "data": dict(raw.get("data", {})),
                }
                # claim_requested is the only event that introduces all claim
                # fields. Keeping that state in the event permits deterministic
                # tail replay without requiring a checkpoint after every event.
                if event.event_type == "claim_requested" and event.claim_id in engine.claims:
                    payload["claim_state"] = asdict(engine.claims[event.claim_id])
                self._event_store.append(event_id=str(raw["event_id"]), payload=payload)
                count += 1
            self._event_store.flush()
            self._hydrate_chain_head()
            return count

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
        return ClaimStoreSnapshot(
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

    def _write_legacy_snapshot(self, snapshot: ClaimStoreSnapshot) -> None:
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

    def persist_engine(self, engine: TaskClaimEngine, *, event_cursor: int = 0) -> ClaimStoreSnapshot:
        if self.persistence_mode == "checkpointed":
            assert self._event_store is not None
            count = self.append_engine_events(engine, start_index=event_cursor)
            # Build the snapshot only after the journal cursor has advanced so
            # last_event_id/hash and all materialized state refer to the same
            # logical point. Checkpoint once the tail reaches the configured
            # interval; the exact boundary may move forward to the latest event
            # because replay must start from an internally consistent state.
            snapshot = self.snapshot_engine(engine)
            if (
                self._event_store.event_count > 0
                and self._event_store.event_count - self._event_store.checkpoint_event_count >= self.checkpoint_interval
            ):
                self._event_store.checkpoint(state=snapshot.to_dict())
            elif count == 0 and self._event_store.checkpoint_event_count == 0 and self._event_store.event_count == 0:
                self._event_store.checkpoint(state=snapshot.to_dict())
            return snapshot

        self.append_engine_events(engine, start_index=event_cursor)
        snapshot = self.snapshot_engine(engine)
        self._write_legacy_snapshot(snapshot)
        return snapshot

    def load_snapshot(self) -> ClaimStoreSnapshot:
        if not self.snapshot_path.exists():
            raise FileNotFoundError(str(self.snapshot_path))
        if self.persistence_mode == "checkpointed":
            assert self._event_store is not None
            checkpoint = self._event_store.checkpoint_snapshot()
            if checkpoint is None:
                raise FileNotFoundError(str(self.snapshot_path))
            return ClaimStoreSnapshot(**checkpoint.state)
        payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        return ClaimStoreSnapshot(**payload)

    def read_events(self) -> list[StoredClaimEvent]:
        if self.persistence_mode == "checkpointed":
            assert self._event_store is not None
            return [self._decode_checkpointed_event(event) for event in self._event_store.events()]
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
        if self.persistence_mode == "checkpointed":
            assert self._event_store is not None
            info = self._event_store.verify_integrity()
            result = {
                "valid": info.integrity_ok,
                "event_count": info.journal_event_count,
                "last_event_hash": info.journal_last_hash,
                "checkpoint_event_count": info.checkpoint_event_count,
                "tail_event_count": info.tail_event_count,
            }
            if not info.integrity_ok:
                result["reason"] = "checkpointed_event_store_integrity_failure"
            return result

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
                return {"valid": False, "reason": "sequence_mismatch", "sequence": event.sequence}
            if event.prev_event_hash != previous:
                return {"valid": False, "reason": "previous_hash_mismatch", "sequence": event.sequence}
            if event.event_hash != expected_hash:
                return {"valid": False, "reason": "event_hash_mismatch", "sequence": event.sequence}
            previous = event.event_hash
        return {"valid": True, "event_count": len(events), "last_event_hash": previous}

    def _checkpointed_events_since_checkpoint(self) -> list[Any]:
        assert self._event_store is not None
        return self._event_store.recover_events_after_checkpoint()

    @staticmethod
    def _claim_from_checkpointed_payload(payload: Mapping[str, Any]) -> Claim:
        raw = payload.get("claim_state")
        if not isinstance(raw, Mapping):
            raise ValueError("checkpointed claim_requested event lacks claim_state")
        return Claim(**dict(raw))

    def _apply_checkpointed_event(self, engine: TaskClaimEngine, event: Any) -> None:
        payload = dict(event.payload)
        event_type = str(payload.get("event_type", ""))
        claim_id = str(payload.get("claim_id", ""))
        data = dict(payload.get("data", {}))

        if event_type == "claim_requested":
            claim = self._claim_from_checkpointed_payload(payload)
            engine.claims[claim.claim_id] = claim
            return

        claim = engine.claims.get(claim_id)
        if event_type in {
            "claimed", "accepted", "rejected", "awaiting_resources",
            "resource_reserved", "active", "completed", "deadlock",
            "released", "expired",
        }:
            if claim is not None:
                status = event_type.upper()
                claim = Claim(**{**asdict(claim), "status": status})
                engine.claims[claim_id] = claim

        if event_type == "resource_reserved":
            reservation_id = str(data.get("reservation_id", ""))
            allocations = {str(k): float(v) for k, v in dict(data.get("allocations", {})).items()}
            if reservation_id and claim is not None:
                reservation = ResourceReservation(
                    reservation_id=reservation_id,
                    claim_id=claim.claim_id,
                    question_id=claim.question_id,
                    agent_id=claim.agent_id,
                    resource_ids=sorted(allocations),
                    allocations=allocations,
                    created_at=str(payload.get("timestamp", "")),
                    status="RESERVED",
                )
                engine.reservations[reservation_id] = reservation
                for resource_id, amount in allocations.items():
                    resource = engine.resources.get(resource_id)
                    if resource is None:
                        continue
                    availability = dict(resource.get("availability", {}))
                    current = _resource_capacity(resource)
                    availability["available_capacity"] = str(max(0.0, current - amount))
                    resource["availability"] = availability
                try:
                    engine._reservation_seq = max(engine._reservation_seq, int(reservation_id.split("-")[-1]))
                except (TypeError, ValueError):
                    pass

        elif event_type == "resource_released":
            reservation_id = str(data.get("reservation_id", ""))
            reservation = engine.reservations.get(reservation_id)
            if reservation is not None and reservation.status != "RELEASED":
                for resource_id, amount in reservation.allocations.items():
                    resource = engine.resources.get(resource_id)
                    if resource is None:
                        continue
                    availability = dict(resource.get("availability", {}))
                    current = _resource_capacity(resource)
                    availability["available_capacity"] = str(current + float(amount))
                    resource["availability"] = availability
                engine.reservations[reservation_id] = ResourceReservation(
                    **{
                        **asdict(reservation),
                        "status": "RELEASED",
                        "released_at": str(payload.get("timestamp", "")),
                        "reason": str(data.get("reason", "")),
                    }
                )

    def _restore_checkpointed_tail(self, engine: TaskClaimEngine) -> None:
        assert self._event_store is not None
        for stored in self._checkpointed_events_since_checkpoint():
            self._apply_checkpointed_event(engine, stored)

    def _restore_stale_active(self, engine: TaskClaimEngine) -> None:
        stale_claim_ids = {
            claim.claim_id
            for claim in engine.claims.values()
            if claim.status in ACTIVE_CLAIM_STATES
        }
        for claim_id in stale_claim_ids:
            claim = engine.claims[claim_id]
            engine.claims[claim_id] = Claim(**{**asdict(claim), "status": "RELEASED"})
        for reservation_id, reservation in list(engine.reservations.items()):
            if reservation.claim_id not in stale_claim_ids:
                continue
            for resource_id, amount in reservation.allocations.items():
                resource = engine.resources.get(resource_id)
                if resource is None:
                    continue
                availability = dict(resource.get("availability", {}))
                current = _resource_capacity(resource)
                availability["available_capacity"] = str(current + float(amount))
                resource["availability"] = availability
            engine.reservations[reservation_id] = ResourceReservation(
                **{
                    **asdict(reservation),
                    "status": "RELEASED",
                    "released_at": _iso_now(),
                    "reason": "released on runtime restart because the claim lease was stale",
                }
            )

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

        if self.persistence_mode == "checkpointed":
            assert self._event_store is not None
            checkpoint = self._event_store.checkpoint_snapshot()
            if checkpoint is not None:
                snapshot = ClaimStoreSnapshot(**checkpoint.state)
                engine.claims = {
                    c["claim_id"]: Claim(**c) for c in snapshot.claims
                }
                engine.reservations = {
                    r["reservation_id"]: ResourceReservation(**r) for r in snapshot.reservations
                }
                engine.resources = {str(r["resource_id"]): dict(r) for r in snapshot.resources}
            else:
                # No checkpoint yet: replay starts from the engine's initial
                # questions/resources, which is sufficient because checkpointed
                # claim_requested events carry the complete claim record.
                engine.claims = {}
                engine.reservations = {}

            self._restore_checkpointed_tail(engine)
            all_events = self._event_store.events()
            engine.events = [
                ClaimEvent(
                    event_id=event.event_id,
                    event_type=str(event.payload.get("event_type", "")),
                    claim_id=str(event.payload.get("claim_id", "")),
                    question_id=str(event.payload.get("question_id", "")),
                    agent_id=str(event.payload.get("agent_id", "")),
                    timestamp=str(event.payload.get("timestamp", "")),
                    data=dict(event.payload.get("data", {})),
                )
                for event in all_events
            ]
            engine._event_seq = len(engine.events)
            engine._reservation_seq = max(
                [
                    int(rid.split("-")[-1])
                    for rid in engine.reservations
                    if rid.startswith("RES-") and rid.split("-")[-1].isdigit()
                ]
                or [0]
            )
            if stale_active_policy == "RELEASE_ACTIVE_ON_RESTART":
                self._restore_stale_active(engine)
            return snapshot if checkpoint is not None else ClaimStoreSnapshot(
                schema_version=SCHEMA_VERSION,
                store_id=self.store_id,
                updated_at=_iso_now(),
                claims=[asdict(c) for c in engine.claims.values()],
                reservations=[asdict(r) for r in engine.reservations.values()],
                resources=[dict(r) for r in engine.resources.values()],
                question_status={qid: engine.question_frontier_status(qid) for qid in sorted(engine.questions)},
                active_claim_ids=sorted(c.claim_id for c in engine.claims.values() if c.status in ACTIVE_CLAIM_STATES),
                active_reservation_ids=sorted(r.reservation_id for r in engine.reservations.values() if r.status == "ACTIVE"),
                last_event_id=engine.events[-1].event_id if engine.events else None,
                last_event_hash=self._last_hash,
            )

        snapshot = self.load_snapshot()
        engine.claims = {c["claim_id"]: Claim(**c) for c in snapshot.claims}
        engine.reservations = {r["reservation_id"]: ResourceReservation(**r) for r in snapshot.reservations}
        engine.resources = {str(r["resource_id"]): dict(r) for r in snapshot.resources}
        events = self.read_events()
        engine.events = [ClaimEvent(**{
            "event_id": e.event_id,
            "event_type": e.event_type,
            "claim_id": e.claim_id,
            "question_id": e.question_id,
            "agent_id": e.agent_id,
            "timestamp": e.timestamp,
            "data": dict(e.data),
        }) for e in events]
        engine._event_seq = len(engine.events)
        engine._reservation_seq = max(
            [int(rid.split("-")[-1]) for rid in engine.reservations if rid.startswith("RES-") and rid.split("-")[-1].isdigit()] or [0]
        )
        if stale_active_policy == "RELEASE_ACTIVE_ON_RESTART":
            self._restore_stale_active(engine)
        self._hydrate_chain_head()
        return snapshot

    def recoverable_active_claim_ids(self) -> list[str]:
        snapshot = self.load_snapshot()
        return list(snapshot.active_claim_ids)

    def result(self) -> dict[str, Any]:
        integrity = self.verify_integrity()
        snapshot = None
        if self.snapshot_path.exists():
            snapshot = self.load_snapshot().to_dict()
        return {
            "store_id": self.store_id,
            "schema_version": SCHEMA_VERSION,
            "persistence_mode": self.persistence_mode,
            "journal_batch_size": self.journal_batch_size,
            "checkpoint_interval": self.checkpoint_interval,
            "durable": self.durable,
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


def demo(*, persistence_mode: str = "legacy") -> dict[str, Any]:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="ufcps-claim-store-") as directory:
        path = Path(directory) / "claims"
        store = TaskClaimStore(
            path,
            store_id="STORE-DEMO",
            persistence_mode=persistence_mode,
            journal_batch_size=4 if persistence_mode == "checkpointed" else 1,
            checkpoint_interval=4 if persistence_mode == "checkpointed" else 1,
        )
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

        if persistence_mode == "checkpointed":
            # Add one post-checkpoint terminal event to exercise tail replay.
            engine.complete(claim.claim_id, outcome="completed after checkpoint")
            store.persist_engine(engine, event_cursor=5)

        integrity_before = store.verify_integrity()
        snapshot_before = store.load_snapshot() if store.snapshot_path.exists() else None

        recovered = _build_demo_engine()
        store_reloaded = TaskClaimStore(
            path,
            store_id="STORE-DEMO",
            persistence_mode=persistence_mode,
            journal_batch_size=4 if persistence_mode == "checkpointed" else 1,
            checkpoint_interval=4 if persistence_mode == "checkpointed" else 1,
        )
        restored = store_reloaded.restore_into_engine(recovered)
        integrity_after = store_reloaded.verify_integrity()

        assert integrity_before["valid"] is True
        assert integrity_after["valid"] is True
        if persistence_mode == "legacy":
            assert snapshot_before is not None
            assert snapshot_before.active_claim_ids == ["CL-STORE-001"]
        else:
            assert store_reloaded.verify_integrity()["checkpoint_event_count"] == 5
            assert store_reloaded.verify_integrity()["tail_event_count"] == 2
            assert recovered.claims["CL-STORE-001"].status == "COMPLETED"
            # The completion and release events are in the tail and must be
            # replayed before the stale ACTIVE policy is applied.
            assert all(r.status != "ACTIVE" for r in recovered.reservations.values())
            assert float(recovered.resources["gpu-store-001"]["availability"]["available_capacity"]) == 100.0

        # Common restart invariants. The demo's claim is active in the original
        # snapshot for legacy and becomes a completed/tail state before restart
        # in checkpointed mode; therefore the recovered state is explicitly
        # checked per mode above.
        if persistence_mode == "legacy":
            assert recovered.claims["CL-STORE-001"].status == "RELEASED"
            assert float(recovered.resources["gpu-store-001"]["availability"]["available_capacity"]) == 100.0

        # Tamper test.
        events_text = store.events_path.read_text(encoding="utf-8")
        lines = events_text.splitlines()
        first = json.loads(lines[0])
        if persistence_mode == "checkpointed":
            first["payload"]["event_type"] = "tampered_event"
        else:
            first["event_type"] = "tampered_event"
        lines[0] = json.dumps(first, ensure_ascii=False, sort_keys=True)
        store.events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tampered = store.verify_integrity()

        return {
            "status": "PASS",
            "persistence_mode": persistence_mode,
            "event_count": len(store.read_events()),
            "snapshot_claims": len(restored.claims),
            "restored_claim_status": recovered.claims["CL-STORE-001"].status,
            "resource_capacity": recovered.resources["gpu-store-001"]["availability"]["available_capacity"],
            "integrity_before_tamper": integrity_before,
            "integrity_after_restart": integrity_after,
            "tamper_detection": tampered,
            "stale_active_policy": "RELEASE_ACTIVE_ON_RESTART",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run deterministic persistence demo")
    parser.add_argument("--mode", choices=["legacy", "checkpointed"], default="legacy")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")
    args = parser.parse_args()
    if not args.demo:
        parser.print_help()
        return 0
    result = demo(persistence_mode=args.mode)
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
