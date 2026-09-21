
"""UFCPS Level 2 — Process Replay v1.

Reconstruct an observable process trajectory from ``event_audit_bus_v1``.

The replayer is deliberately observational.  It does not execute the process,
does not infer scientific truth, and does not recalculate economics.  It uses
the audit history to reconstruct:

    P0 -> observed event -> observed transition -> ... -> current frontier

It also checks causal-parent references, sequence integrity, process/question
identity consistency, and branch structure.

Canonical replay outputs
------------------------
* event order for a process;
* reconstructed lifecycle stage;
* primary causal path to the latest event;
* branch roots/leaves;
* causal-chain gaps;
* identity inconsistencies;
* replay integrity status;
* auditable transition observations.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

SWARM_DIR = Path(__file__).resolve().parent
if str(SWARM_DIR) not in sys.path:
    sys.path.insert(0, str(SWARM_DIR))

from event_audit_bus_v1 import AuditEvent, EventAuditBus


STAGE_BY_EVENT = {
    "question_created": "QUESTION",
    "question_derived": "QUESTION_CONTINUATION",
    "continuation_ready": "CONTINUATION",
    "continuation_discovery": "DISCOVERY",
    "prospect_generated": "DISCOVERY",
    "task_prospect_created": "DISCOVERY",
    "agent_decision": "DISCOVERY_DECISION",
    "claim_requested": "CLAIM_REQUESTED",
    "claim_accepted": "CLAIM_ACCEPTED",
    "claim_queued": "CLAIM_QUEUED",
    "resource_reserved": "RESOURCE_RESERVED",
    "claim_active": "ACTIVE_EXECUTION",
    "execution_started": "EXECUTION",
    "execution_verified": "VERIFIED_EXECUTION",
    "execution_completed": "EXECUTION_COMPLETED",
    "provider_reward_calculated": "ECONOMICS",
    "payment_projected": "PAYMENT_PROJECTION",
    "payment_settled": "PAYMENT_SETTLED",
    "deadlock_recorded": "DEADLOCK",
    "claim_released": "RELEASED",
    "claim_expired": "EXPIRED",
    "claim_handoff": "HANDOFF",
    "runtime_exception": "LOCAL_EXCEPTION",
}

STAGE_RANK = {
    "QUESTION": 10,
    "QUESTION_CONTINUATION": 15,
    "DISCOVERY": 20,
    "DISCOVERY_DECISION": 25,
    "CLAIM_REQUESTED": 30,
    "CLAIM_QUEUED": 32,
    "CLAIM_ACCEPTED": 35,
    "RESOURCE_RESERVED": 40,
    "ACTIVE_EXECUTION": 45,
    "EXECUTION": 50,
    "VERIFIED_EXECUTION": 60,
    "EXECUTION_COMPLETED": 65,
    "ECONOMICS": 70,
    "PAYMENT_PROJECTION": 75,
    "PAYMENT_SETTLED": 80,
    "DEADLOCK": 55,
    "RELEASED": 55,
    "EXPIRED": 55,
    "HANDOFF": 58,
    "CONTINUATION": 85,
    "LOCAL_EXCEPTION": 50,
    "UNKNOWN": 0,
}


@dataclass(frozen=True)
class ReplayTransition:
    sequence: int
    event_id: str
    event_type: str
    domain: str
    stage: str
    from_stage: str
    to_stage: str
    actor_id: str
    resource_ids: list[str]
    causal_parent_event_id: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayPath:
    event_ids: list[str]
    event_types: list[str]
    sequences: list[int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProcessReplayResult:
    process_id: str
    question_ids: list[str]
    event_count: int
    first_event_id: Optional[str]
    last_event_id: Optional[str]
    current_stage: str
    current_status: str
    primary_path: ReplayPath
    branch_roots: list[str]
    branch_leaves: list[str]
    orphan_parent_event_ids: list[str]
    future_parent_event_ids: list[str]
    process_identity_errors: list[str]
    replay_warnings: list[str]
    integrity_valid: bool
    transitions: list[ReplayTransition] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["primary_path"] = self.primary_path.to_dict()
        data["transitions"] = [item.to_dict() for item in self.transitions]
        return data


@dataclass(frozen=True)
class ReplaySuiteResult:
    bus_integrity_valid: bool
    processes: list[ProcessReplayResult]
    process_count: int
    all_replays_valid: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "bus_integrity_valid": self.bus_integrity_valid,
            "processes": [item.to_dict() for item in self.processes],
            "process_count": self.process_count,
            "all_replays_valid": self.all_replays_valid,
        }


def _stage_for_event(event: AuditEvent) -> str:
    if event.event_type in STAGE_BY_EVENT:
        return STAGE_BY_EVENT[event.event_type]
    return event.domain or "UNKNOWN"


def _event_index(events: Sequence[AuditEvent]) -> dict[str, AuditEvent]:
    return {event.event_id: event for event in events}


def _build_parent_graph(events: Sequence[AuditEvent]) -> tuple[dict[str, list[str]], list[str], list[str]]:
    by_id = _event_index(events)
    children: dict[str, list[str]] = defaultdict(list)
    orphan: list[str] = []
    future: list[str] = []
    for event in events:
        parent_id = event.causal_parent_event_id
        if not parent_id:
            continue
        parent = by_id.get(parent_id)
        if parent is None:
            orphan.append(parent_id)
            continue
        children[parent_id].append(event.event_id)
        if parent.sequence >= event.sequence:
            future.append(event.event_id)
    for key in list(children):
        children[key] = sorted(children[key], key=lambda eid: by_id[eid].sequence)
    return children, sorted(set(orphan)), sorted(set(future))


def _primary_path(events: Sequence[AuditEvent]) -> ReplayPath:
    if not events:
        return ReplayPath([], [], [])
    by_id = _event_index(events)
    current = events[-1]
    path: list[AuditEvent] = []
    visited: set[str] = set()
    while current is not None:
        if current.event_id in visited:
            break
        visited.add(current.event_id)
        path.append(current)
        parent_id = current.causal_parent_event_id
        if not parent_id:
            break
        current = by_id.get(parent_id)
        if current is None:
            break
    path.reverse()
    return ReplayPath(
        event_ids=[event.event_id for event in path],
        event_types=[event.event_type for event in path],
        sequences=[event.sequence for event in path],
    )


def _branch_roots(events: Sequence[AuditEvent]) -> list[str]:
    ids = {event.event_id for event in events}
    return [
        event.event_id
        for event in events
        if not event.causal_parent_event_id or event.causal_parent_event_id not in ids
    ]


def _branch_leaves(events: Sequence[AuditEvent]) -> list[str]:
    parent_ids = {event.causal_parent_event_id for event in events if event.causal_parent_event_id}
    return [event.event_id for event in events if event.event_id not in parent_ids]


def _identity_errors(events: Sequence[AuditEvent], process_id: str) -> list[str]:
    errors: list[str] = []
    question_ids = {event.question_id for event in events}
    for event in events:
        if event.process_id != process_id:
            errors.append(f"sequence {event.sequence}: process_id mismatch")
        if not event.question_id:
            errors.append(f"sequence {event.sequence}: empty question_id")
    if len(question_ids) > 1:
        # Multiple questions are valid only when the event history explicitly
        # exposes continuation/derivation.  We keep this as a warning-level
        # identity observation rather than a hard invalidation.
        explicit_derivation = any(
            event.event_type in {"question_derived", "continuation_discovery", "continuation_ready"}
            for event in events
        )
        if not explicit_derivation:
            errors.append(
                "multiple question_ids observed without explicit continuation/derivation event"
            )
    return errors


def replay_process(events: Iterable[AuditEvent], *, process_id: str) -> ProcessReplayResult:
    selected = sorted(
        [event for event in events if event.process_id == process_id],
        key=lambda event: event.sequence,
    )
    if not selected:
        raise ValueError(f"no audit events for process_id={process_id}")

    seen_sequences: set[int] = set()
    sequence_errors: list[str] = []
    transitions: list[ReplayTransition] = []
    previous_stage = "START"
    for event in selected:
        if event.sequence in seen_sequences:
            sequence_errors.append(f"duplicate sequence: {event.sequence}")
        seen_sequences.add(event.sequence)
        stage = _stage_for_event(event)
        transitions.append(
            ReplayTransition(
                sequence=event.sequence,
                event_id=event.event_id,
                event_type=event.event_type,
                domain=event.domain,
                stage=stage,
                from_stage=previous_stage,
                to_stage=stage,
                actor_id=event.actor_id,
                resource_ids=list(event.resource_ids),
                causal_parent_event_id=event.causal_parent_event_id,
            )
        )
        previous_stage = stage

    _, orphan, future = _build_parent_graph(selected)
    identity_errors = _identity_errors(selected, process_id)

    warnings: list[str] = []
    if orphan:
        warnings.append("one or more causal parents are missing from the process history")
    if future:
        warnings.append("one or more causal parents occur at the same/later sequence")
    if sequence_errors:
        warnings.extend(sequence_errors)

    # Sequence gaps are observational warnings, not necessarily failures:
    # events from other processes may occupy the global audit sequence.
    sequences = [event.sequence for event in selected]
    if any(b <= a for a, b in zip(sequences, sequences[1:])):
        warnings.append("non-monotonic process-local sequence order")

    children, _, _ = _build_parent_graph(selected)
    leaves = _branch_leaves(selected)
    roots = _branch_roots(selected)
    if any(len(children.get(root, [])) > 1 for root in roots):
        warnings.append("causal branching detected")

    integrity_valid = not orphan and not future and not identity_errors and not sequence_errors
    last = selected[-1]
    last_stage = _stage_for_event(last)
    if last_stage in {
        "DEADLOCK",
        "RELEASED",
        "EXPIRED",
        "HANDOFF",
        "CONTINUATION",
        "QUESTION_CONTINUATION",
    }:
        status = "CONTINUING"
    elif last_stage in {"PAYMENT_SETTLED", "EXECUTION_COMPLETED"}:
        status = "OBSERVED_COMPLETE"
    else:
        status = "OBSERVED"
    return ProcessReplayResult(
        process_id=process_id,
        question_ids=sorted({event.question_id for event in selected}),
        event_count=len(selected),
        first_event_id=selected[0].event_id,
        last_event_id=last.event_id,
        current_stage=_stage_for_event(last),
        current_status=status,
        primary_path=_primary_path(selected),
        branch_roots=roots,
        branch_leaves=leaves,
        orphan_parent_event_ids=orphan,
        future_parent_event_ids=future,
        process_identity_errors=identity_errors,
        replay_warnings=warnings,
        integrity_valid=integrity_valid,
        transitions=transitions,
    )


def replay_bus(bus: EventAuditBus) -> ReplaySuiteResult:
    bus_integrity = bus.verify_integrity()
    all_events = bus.events()
    process_ids = sorted({event.process_id for event in all_events})
    replays = [replay_process(all_events, process_id=process_id) for process_id in process_ids]
    all_valid = bool(bus_integrity.get("valid")) and all(item.integrity_valid for item in replays)
    return ReplaySuiteResult(
        bus_integrity_valid=bool(bus_integrity.get("valid")),
        processes=replays,
        process_count=len(replays),
        all_replays_valid=all_valid,
    )


def demo() -> dict[str, Any]:
    """Build a deterministic branched process and replay it."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="ufcps-process-replay-") as directory:
        bus = EventAuditBus(Path(directory) / "audit", bus_id="REPLAY-DEMO")
        e1 = bus.append(
            event_type="question_created", domain="UQL", source_system="uql_store_v1",
            source_event_id="UQL-R-001", process_id="PROC-REPLAY-001", question_id="Q-REPLAY-001",
            verification_status="verified", payload={"status": "unresolved"},
        )
        e2 = bus.append(
            event_type="claim_accepted", domain="CLAIM", source_system="task_claim_engine_v1",
            source_event_id="CL-R-001", process_id="PROC-REPLAY-001", question_id="Q-REPLAY-001",
            actor_id="agent-A", causal_parent_event_id=e1.event_id,
            verification_status="verified", payload={"claim_id": "CL-R-001"},
        )
        e3 = bus.append(
            event_type="resource_reserved", domain="RESOURCE", source_system="task_claim_engine_v1",
            source_event_id="RES-R-001", process_id="PROC-REPLAY-001", question_id="Q-REPLAY-001",
            actor_id="agent-A", resource_ids=["gpu-R-001"], causal_parent_event_id=e2.event_id,
            verification_status="verified", payload={"quantity": 25},
        )
        e4 = bus.append(
            event_type="execution_verified", domain="VERIFICATION", source_system="compute_verifier_v1",
            source_event_id="VER-R-001", process_id="PROC-REPLAY-001", question_id="Q-REPLAY-001",
            actor_id="validator-A", resource_ids=["gpu-R-001"], causal_parent_event_id=e3.event_id,
            verification_status="verified", payload={"verified_compute": 25},
        )
        e5 = bus.append(
            event_type="deadlock_recorded", domain="DEADLOCK", source_system="execution_pipeline_v1",
            source_event_id="DL-R-001", process_id="PROC-REPLAY-001", question_id="Q-REPLAY-001",
            actor_id="agent-A", resource_ids=["gpu-R-001"], causal_parent_event_id=e4.event_id,
            verification_status="verified", payload={"deadlock_ref": "DL-R-001"},
        )
        e6 = bus.append(
            event_type="question_derived", domain="UQL", source_system="uql_store_v1",
            source_event_id="UQL-R-002", process_id="PROC-REPLAY-001", question_id="Q-REPLAY-002",
            actor_id="system", causal_parent_event_id=e5.event_id,
            verification_status="verified", payload={"parent_question_id": "Q-REPLAY-001"},
        )
        e7 = bus.append(
            event_type="claim_accepted", domain="CLAIM", source_system="task_claim_engine_v1",
            source_event_id="CL-R-002", process_id="PROC-REPLAY-001", question_id="Q-REPLAY-002",
            actor_id="agent-B", causal_parent_event_id=e6.event_id,
            verification_status="verified", payload={"claim_id": "CL-R-002"},
        )
        e8 = bus.append(
            event_type="execution_completed", domain="EXECUTION", source_system="distributed_experiment_coordinator_v1",
            source_event_id="EX-R-002", process_id="PROC-REPLAY-001", question_id="Q-REPLAY-002",
            actor_id="agent-B", causal_parent_event_id=e7.event_id,
            verification_status="verified", payload={"result": "partial"},
        )

        replay = replay_process(bus.events(), process_id="PROC-REPLAY-001")
        suite = replay_bus(bus)

        assert bus.verify_integrity()["valid"] is True
        assert replay.integrity_valid is True
        assert replay.event_count == 8
        assert replay.current_stage == "EXECUTION_COMPLETED"
        assert replay.current_status == "OBSERVED_COMPLETE"
        assert replay.primary_path.sequences == list(range(1, 9))
        assert replay.question_ids == ["Q-REPLAY-001", "Q-REPLAY-002"]
        assert not any("causal branching detected" in warning for warning in replay.replay_warnings)
        assert suite.all_replays_valid is True

        # Negative test: create a replay-only event object with a nonexistent
        # causal parent; the Audit Bus itself would reject this, but the
        # replayer must remain capable of detecting malformed imported data.
        malformed = list(bus.events())
        malformed.append(
            AuditEvent(
                event_id="AE-MALFORMED",
                event_type="execution_started",
                domain="EXECUTION",
                source_system="test",
                source_event_id="BAD-001",
                process_id="PROC-REPLAY-001",
                question_id="Q-REPLAY-002",
                actor_id="agent-B",
                resource_ids=[],
                timestamp=e8.timestamp,
                causal_parent_event_id="AE-NONEXISTENT",
                verification_status="unknown",
                payload={},
                sequence=9,
                prev_hash="",
                event_hash="",
            )
        )
        malformed_replay = replay_process(malformed, process_id="PROC-REPLAY-001")
        assert malformed_replay.integrity_valid is False
        assert "AE-NONEXISTENT" in malformed_replay.orphan_parent_event_ids

        return {
            "status": "PASS",
            "replay": replay.to_dict(),
            "suite": suite.to_dict(),
            "malformed_parent_detection": {
                "integrity_valid": malformed_replay.integrity_valid,
                "orphan_parent_event_ids": malformed_replay.orphan_parent_event_ids,
            },
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run deterministic replay demo")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.demo:
        parser.print_help()
        return 0
    result = demo()
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("UFCPS Process Replay v1")
        print("Status:", result["status"])
        replay = result["replay"]
        print("Process:", replay["process_id"])
        print("Events:", replay["event_count"])
        print("Current stage:", replay["current_stage"])
        print("Primary path:", " -> ".join(replay["primary_path"]["event_types"]))
        print("Replay integrity:", replay["integrity_valid"])
        print("Malformed parent detected:", bool(result["malformed_parent_detection"]["orphan_parent_event_ids"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
