
"""UFCPS Level 2 — Checkpointed Event Store v1.

A persistence primitive for UFCPS stores whose logical history is append-only
but whose materialized state can be checkpointed less frequently.

Core model
----------

    event journal = authoritative process history
    checkpoint    = recoverable materialized state

The two durability frequencies are independent:

    journal_batch_size
        Number of events accumulated before one journal flush+fsync.

    checkpoint_interval
        Number of committed events between atomic checkpoint writes.

Defaults are intentionally conservative and preserve the v1 per-event durable
pattern: both values are 1.

The class is storage infrastructure only. It does not interpret UFCPS events,
make scheduling decisions, or decide whether a process is valid. A caller
supplies an optional checkpoint payload representing its current materialized
state.

Crash/restart semantics
-----------------------
* The journal is authoritative for committed events.
* A checkpoint is a performance artifact, not the sole source of history.
* On restart, the latest checkpoint may be followed by a journal tail.
* ``recover_events_after_checkpoint`` exposes that tail for caller-side replay.
* Hash chaining makes the journal tamper-evident.
* Atomic checkpoint replacement prevents a partially-written JSON checkpoint.

This module is designed so UQL, Claim Store and Audit Bus can migrate to the
same persistence primitive later without changing their higher-level
semantics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

GENESIS_HASH = "0" * 64
SCHEMA_VERSION = "checkpointed-event-store-v1"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def hash_event(previous_hash: str, body: Mapping[str, Any]) -> str:
    payload = f"{previous_hash}|{canonical(dict(body))}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def atomic_json_write(path: Path, payload: Any, *, durable: bool = True) -> None:
    """Atomically replace *path* with JSON payload."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            if durable:
                os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise


def append_lines(path: Path, lines: Sequence[str], *, durable: bool = True) -> None:
    if not lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line)
        handle.flush()
        if durable:
            os.fsync(handle.fileno())


@dataclass(frozen=True)
class StoredEvent:
    event_id: str
    sequence: int
    payload: dict[str, Any]
    prev_hash: str
    event_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StoreSnapshot:
    schema_version: str
    event_count: int
    last_event_id: Optional[str]
    last_event_hash: str
    state: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecoveryInfo:
    checkpoint_event_count: int
    journal_event_count: int
    tail_event_count: int
    checkpoint_hash: str
    journal_last_hash: str
    integrity_ok: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CheckpointedEventStore:
    """Append-only event journal with independently controlled checkpoints."""

    def __init__(
        self,
        base_path: str | Path,
        *,
        journal_batch_size: int = 1,
        checkpoint_interval: int = 1,
        durable: bool = True,
    ) -> None:
        if journal_batch_size < 1:
            raise ValueError("journal_batch_size must be >= 1")
        if checkpoint_interval < 1:
            raise ValueError("checkpoint_interval must be >= 1")

        self.base_path = Path(base_path)
        self.events_path = Path(f"{self.base_path}.events.jsonl")
        self.checkpoint_path = Path(f"{self.base_path}.checkpoint.json")
        self.journal_batch_size = int(journal_batch_size)
        self.checkpoint_interval = int(checkpoint_interval)
        self.durable = bool(durable)

        self._sequence = 0
        self._last_hash = GENESIS_HASH
        self._pending: list[str] = []
        self._pending_events: list[StoredEvent] = []
        self._checkpoint_state: Any = None
        self._checkpoint_event_count = 0
        self._hydrate()

    # --------------------------- lifecycle ---------------------------

    def _hydrate(self) -> None:
        events = self.events()
        if events:
            self._sequence = events[-1].sequence
            self._last_hash = events[-1].event_hash
        if self.checkpoint_path.exists():
            raw = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
            if raw.get("schema_version") != SCHEMA_VERSION:
                raise ValueError("Unsupported checkpoint schema version")
            self._checkpoint_state = raw.get("state")
            self._checkpoint_event_count = int(raw.get("event_count", 0))
            checkpoint_hash = str(raw.get("last_event_hash", GENESIS_HASH))
            if self._checkpoint_event_count > self._sequence:
                raise ValueError("checkpoint is ahead of event journal")
            if self._checkpoint_event_count == self._sequence and checkpoint_hash != self._last_hash:
                raise ValueError("checkpoint hash does not match journal tail")

    @property
    def event_count(self) -> int:
        return self._sequence

    @property
    def last_event_hash(self) -> str:
        return self._last_hash

    @property
    def pending_count(self) -> int:
        return len(self._pending_events)

    @property
    def checkpoint_event_count(self) -> int:
        return self._checkpoint_event_count

    def close(self) -> None:
        self.flush()

    # ----------------------------- append ----------------------------

    def append(
        self,
        *,
        event_id: str,
        payload: Mapping[str, Any],
        checkpoint_state: Any = None,
        force_checkpoint: bool = False,
    ) -> StoredEvent:
        """Create one event and optionally update the materialized checkpoint.

        The event is considered committed when its current journal batch is
        flushed. A checkpoint is written only after the corresponding journal
        batch has been durably flushed when ``durable=True``.
        """
        event_id = str(event_id).strip()
        if not event_id:
            raise ValueError("event_id is required")

        self._sequence += 1
        body = {
            "event_id": event_id,
            "sequence": self._sequence,
            "payload": json.loads(canonical(dict(payload))),
        }
        current = StoredEvent(
            **body,
            prev_hash=self._last_hash,
            event_hash=hash_event(self._last_hash, body),
        )
        self._pending_events.append(current)
        self._pending.append(canonical(current.to_dict()) + "\n")
        self._last_hash = current.event_hash

        if checkpoint_state is not None:
            self._checkpoint_state = json.loads(canonical(checkpoint_state))

        should_flush = len(self._pending) >= self.journal_batch_size
        should_checkpoint = force_checkpoint or (
            checkpoint_state is not None and self._sequence % self.checkpoint_interval == 0
        )
        if should_checkpoint:
            # A checkpoint must never get ahead of an uncommitted journal tail.
            self.flush()
            self.checkpoint()
        elif should_flush:
            self.flush()

        return current

    def append_many(
        self,
        events: Iterable[Mapping[str, Any]],
        *,
        checkpoint_state: Any = None,
        force_checkpoint: bool = False,
    ) -> list[StoredEvent]:
        stored: list[StoredEvent] = []
        for raw in events:
            data = dict(raw)
            event_id = str(data.pop("event_id"))
            stored.append(self.append(event_id=event_id, payload=data))
        if stored and checkpoint_state is not None:
            self._checkpoint_state = json.loads(canonical(checkpoint_state))
        if force_checkpoint and stored:
            self.flush()
            self.checkpoint()
        else:
            self.flush()
        return stored

    def flush(self) -> None:
        if not self._pending:
            return
        append_lines(self.events_path, self._pending, durable=self.durable)
        self._pending.clear()
        self._pending_events.clear()

    # -------------------------- checkpoints --------------------------

    def checkpoint(self, state: Any = None) -> StoreSnapshot:
        """Write one atomic checkpoint for the latest committed journal state."""
        self.flush()
        if state is not None:
            self._checkpoint_state = json.loads(canonical(state))
        snapshot = StoreSnapshot(
            schema_version=SCHEMA_VERSION,
            event_count=self._sequence,
            last_event_id=self.events()[-1].event_id if self._sequence else None,
            last_event_hash=self._last_hash,
            state=self._checkpoint_state,
        )
        atomic_json_write(self.checkpoint_path, snapshot.to_dict(), durable=self.durable)
        self._checkpoint_event_count = self._sequence
        return snapshot

    # ----------------------------- read -------------------------------

    def events(self) -> list[StoredEvent]:
        if not self.events_path.exists():
            return []
        result: list[StoredEvent] = []
        with self.events_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    result.append(StoredEvent(**json.loads(line)))
                except Exception as exc:
                    raise ValueError(f"invalid event at line {line_no}: {exc}") from exc
        return result

    def checkpoint_snapshot(self) -> Optional[StoreSnapshot]:
        if not self.checkpoint_path.exists():
            return None
        return StoreSnapshot(**json.loads(self.checkpoint_path.read_text(encoding="utf-8")))

    def recover_events_after_checkpoint(self) -> list[StoredEvent]:
        """Return journal tail that is not represented in the latest checkpoint."""
        events = self.events()
        return [event for event in events if event.sequence > self._checkpoint_event_count]

    def verify_integrity(self) -> RecoveryInfo:
        events = self.events()
        previous = GENESIS_HASH
        ok = True
        for expected_sequence, event in enumerate(events, start=1):
            body = {
                "event_id": event.event_id,
                "sequence": event.sequence,
                "payload": event.payload,
            }
            if event.sequence != expected_sequence:
                ok = False
                break
            if event.prev_hash != previous:
                ok = False
                break
            if event.event_hash != hash_event(previous, body):
                ok = False
                break
            previous = event.event_hash

        checkpoint_hash = GENESIS_HASH
        if self.checkpoint_path.exists():
            checkpoint = self.checkpoint_snapshot()
            assert checkpoint is not None
            if checkpoint.event_count > len(events):
                ok = False
            elif checkpoint.event_count:
                checkpoint_hash = events[checkpoint.event_count - 1].event_hash
                if checkpoint.last_event_hash != checkpoint_hash:
                    ok = False

        return RecoveryInfo(
            checkpoint_event_count=self._checkpoint_event_count,
            journal_event_count=len(events),
            tail_event_count=max(0, len(events) - self._checkpoint_event_count),
            checkpoint_hash=checkpoint_hash,
            journal_last_hash=previous if events else GENESIS_HASH,
            integrity_ok=ok,
        )


def _self_test() -> dict[str, Any]:
    """Minimal deterministic proof of batching/checkpoint separation."""
    with tempfile.TemporaryDirectory(prefix="ufcps-store-test-") as temp_dir:
        base = Path(temp_dir) / "store"
        store = CheckpointedEventStore(
            base,
            journal_batch_size=4,
            checkpoint_interval=4,
            durable=True,
        )
        final_state: dict[str, Any] = {"value": 0}
        for i in range(1, 13):
            final_state["value"] = i
            store.append(
                event_id=f"EV-{i:04d}",
                payload={"value": i},
                checkpoint_state=final_state,
            )
        store.close()

        recovered = CheckpointedEventStore(
            base,
            journal_batch_size=4,
            checkpoint_interval=4,
            durable=True,
        )
        integrity = recovered.verify_integrity()
        checkpoint = recovered.checkpoint_snapshot()
        tail = recovered.recover_events_after_checkpoint()
        expected = {
            "event_count": 12,
            "checkpoint_event_count": 12,
            "tail_event_count": 0,
            "state_value": 12,
            "integrity_ok": True,
        }
        actual = {
            "event_count": recovered.event_count,
            "checkpoint_event_count": integrity.checkpoint_event_count,
            "tail_event_count": len(tail),
            "state_value": checkpoint.state["value"] if checkpoint else None,
            "integrity_ok": integrity.integrity_ok,
        }
        if actual != expected:
            raise AssertionError(f"self-test mismatch: {actual} != {expected}")

        # Prove that a non-checkpointed tail remains recoverable.
        recovered.append(
            event_id="EV-0013",
            payload={"value": 13},
            checkpoint_state={"value": 13},
        )
        recovered.flush()
        tail_after = recovered.recover_events_after_checkpoint()
        if [event.event_id for event in tail_after] != ["EV-0013"]:
            raise AssertionError("tail recovery failed")

        return {
            "passed": True,
            "event_count": actual["event_count"],
            "checkpoint_event_count": actual["checkpoint_event_count"],
            "tail_after_extra_event": [event.event_id for event in tail_after],
            "integrity_ok": integrity.integrity_ok,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run deterministic persistence self-test")
    parser.add_argument("--print-schema", action="store_true", help="print machine-readable configuration schema")
    args = parser.parse_args()

    if args.print_schema:
        print(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "config": {
                "journal_batch_size": "integer >= 1",
                "checkpoint_interval": "integer >= 1",
                "durable": "boolean",
            },
            "default_semantics": {
                "journal_batch_size": 1,
                "checkpoint_interval": 1,
                "durable": True,
            },
            "invariants": [
                "event journal is append-only",
                "hash chain is deterministic",
                "checkpoint never gets ahead of committed journal",
                "checkpoint replacement is atomic",
                "checkpoint is not the sole source of process history",
                "journal tail after checkpoint is recoverable",
            ],
        }, ensure_ascii=False, indent=2))
        return 0

    if args.self_test or len(os.sys.argv) == 1:
        result = _self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
