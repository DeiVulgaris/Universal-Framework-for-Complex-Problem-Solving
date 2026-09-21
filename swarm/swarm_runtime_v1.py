#!/usr/bin/env python3
"""UFCPS Level 2 — Swarm Runtime v1.

Continuous in-memory orchestration layer for the distributed swarm.

The runtime keeps the process alive by cycling structured questions through
Distributed Experiment Coordinator v1.  It deliberately does not solve the
questions itself and does not execute real remote compute or payments.

Canonical cycle::

    Question Ledger
      -> Task Discovery
      -> explicit agent decision
      -> admission
      -> Distributed Experiment Coordinator
      -> Result / Negative Result / Deadlock
      -> continuation record
      -> Question Ledger
      -> next runtime tick

Core invariants
---------------
* local failure never implies global process termination;
* Deadlock is a valid continuation input;
* negative result is a valid continuation input;
* provider compensation is independent of research success;
* runtime state is explicit and auditable;
* v1 is deterministic and single-threaded; concurrency can be added later
  without changing the process semantics.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Deque, Iterable, Mapping, Optional, Sequence

SWARM_DIR = Path(__file__).resolve().parent
if str(SWARM_DIR) not in sys.path:
    sys.path.insert(0, str(SWARM_DIR))

from distributed_experiment_coordinator_v1 import CoordinatorResult, coordinate_experiments
from task_discovery_engine_v1 import TaskProspect, discover as discover_task_prospects
from uql_store_v1 import UQLStore


TERMINAL_QUESTION_STATES = {
    "resolved",
    "cancelled",
    "invalid",
}


@dataclass
class LedgerEntry:
    entry_id: str
    process_id: str
    question: dict[str, Any]
    source: str = "seed"
    status: str = "queued"
    generation: int = 0
    parent_entry_id: Optional[str] = None
    last_runtime_tick: int = 0
    last_process_status: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeTick:
    tick_id: str
    tick_number: int
    prospects_generated: int
    agent_decisions_recorded: int
    entries_admitted: int
    processes_started: int
    processes_completed: int
    continuation_enqueued: int
    blocked_or_rejected: int
    global_process_terminated: bool
    coordinator_status: str
    errors: list[str]


@dataclass(frozen=True)
class RuntimeResult:
    runtime_id: str
    status: str
    ticks_executed: int
    questions_seeded: int
    prospects_current: int
    discoverable_count: int
    agent_decisions: list[dict[str, str]]
    processes_started: int
    continuations_created: int
    current_queue_size: int
    global_process_terminated: bool
    persistence_enabled: bool
    uql_integrity_valid: Optional[bool]
    uql_event_count: Optional[int]
    ledger_snapshot: list[dict[str, Any]]
    tick_history: list[dict[str, Any]]
    errors: list[str]


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _d(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe(v) for v in value]
    return value


class SwarmRuntime:
    """Deterministic runtime around the existing UFCPS coordinator."""

    def __init__(
        self,
        *,
        runtime_id: str,
        agents: Iterable[Mapping[str, Any]],
        resources: Iterable[Mapping[str, Any]],
        max_batch_size: int = 8,
        persistence_path: Optional[str | Path] = None,
        recover_existing: bool = True,
    ) -> None:
        if max_batch_size < 1:
            raise ValueError("max_batch_size must be >= 1")
        self.runtime_id = runtime_id
        self.agents = [dict(x) for x in agents]
        self.resources = [dict(x) for x in resources]
        self.max_batch_size = max_batch_size
        self.queue: Deque[str] = deque()
        self.ledger: dict[str, LedgerEntry] = {}
        self.tick_history: list[RuntimeTick] = []
        self.prospects: dict[str, TaskProspect] = {}
        self.agent_decisions: dict[tuple[str, str], str] = {}
        self._tick_number = 0
        self._entry_sequence = 0
        self._continuation_sequence = 0
        self.errors: list[str] = []
        self.global_process_terminated = False
        self.uql_store = UQLStore(persistence_path) if persistence_path is not None else None
        self.persistence_path = str(persistence_path) if persistence_path is not None else None
        if self.uql_store is not None and recover_existing:
            self._restore_from_uql()


    def _runtime_metadata(self, entry: LedgerEntry) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "runtime_entry_id": entry.entry_id,
            "runtime_question": _safe(entry.question),
            "runtime_status": entry.status,
            "source": entry.source,
            "parent_entry_id": entry.parent_entry_id,
            "generation": entry.generation,
            "last_runtime_tick": entry.last_runtime_tick,
            "last_process_status": entry.last_process_status,
            "agent_decisions": _safe(entry.metadata.get("agent_decisions", {})),
            "latest_outcome": _safe(entry.metadata.get("latest_outcome")),
            "from_outcome": _safe(entry.metadata.get("from_outcome")),
            "last_runtime_event": _safe(entry.metadata.get("last_runtime_event")),
        }

    def _uql_status(self, entry: LedgerEntry) -> str:
        if entry.status == "terminated_local":
            return "resolved"
        if entry.status == "rejected_by_agent":
            return "abandoned_with_reason"
        if entry.status == "blocked_local":
            return "blocked"
        if entry.status == "local_exception":
            return "unresolved"
        if entry.status == "continuation_ready":
            return "delegated"
        return entry.status

    def _persist_entry(self, entry: LedgerEntry, *, event_type: str = "runtime_state") -> None:
        if self.uql_store is None:
            return
        question_id = _text(entry.question.get("question_id"))
        required_capabilities = entry.question.get("required_capabilities", [])
        requirements = entry.question.get("requirements", {})
        required_resources = requirements.get("resources", []) if isinstance(requirements, Mapping) else []
        entry.metadata["last_runtime_event"] = event_type
        metadata = self._runtime_metadata(entry)
        try:
            frontier = self.uql_store.get_frontier(question_id)
        except KeyError:
            self.uql_store.create_question(
                question_id=question_id,
                process_id=entry.process_id,
                formulation=_text(entry.question.get("formulation")) or _text(entry.question.get("title")) or question_id,
                required_capabilities=[str(x) for x in required_capabilities],
                required_resources=[dict(x) for x in required_resources if isinstance(x, Mapping)],
                metadata=metadata,
            )
            return
        patch = {
            "status": self._uql_status(entry),
            "generation": entry.generation,
            "candidate_carriers": list(frontier.candidate_carriers),
            "required_capabilities": [str(x) for x in required_capabilities],
            "required_resources": [dict(x) for x in required_resources if isinstance(x, Mapping)],
            "metadata": metadata,
        }
        self.uql_store.update_frontier(
            question_id=question_id,
            event_type="frontier_update",
            patch=patch,
            process_id=entry.process_id,
        )

    def _restore_from_uql(self) -> None:
        """Recover runtime entries and pending work from persisted UQL frontier."""
        if self.uql_store is None:
            return
        max_entry = 0
        max_cont = 0
        max_tick = 0
        for frontier in self.uql_store.frontier.values():
            meta = dict(frontier.metadata or {})
            runtime_question = meta.get("runtime_question")
            runtime_id = _text(meta.get("runtime_id"))
            if runtime_question is None or (runtime_id and runtime_id != self.runtime_id):
                continue
            question = dict(runtime_question)
            question.setdefault("question_id", frontier.question_id)
            question.setdefault("process_id", frontier.process_id)
            entry_id = _text(meta.get("runtime_entry_id")) or f"Q-{frontier.question_id}"
            source = _text(meta.get("source")) or ("continuation" if meta.get("parent_entry_id") else "seed")
            status = _text(meta.get("runtime_status")) or frontier.status
            if status == "queued":
                status = "discoverable"
            if status == "admitted":
                status = "accepted"
            entry = LedgerEntry(
                entry_id=entry_id,
                process_id=frontier.process_id,
                question=question,
                source=source,
                status=status,
                generation=int(meta.get("generation", frontier.generation or 0)),
                parent_entry_id=meta.get("parent_entry_id"),
                last_runtime_tick=int(meta.get("last_runtime_tick", 0)),
                last_process_status=_text(meta.get("last_process_status")),
                metadata={
                    "agent_decisions": dict(meta.get("agent_decisions") or {}),
                    "latest_outcome": meta.get("latest_outcome"),
                    "from_outcome": meta.get("from_outcome"),
                    "last_runtime_event": meta.get("last_runtime_event"),
                },
            )
            self.ledger[entry_id] = entry
            for agent_id, decision in entry.metadata.get("agent_decisions", {}).items():
                self.agent_decisions[(frontier.question_id, _text(agent_id))] = _text(decision)
            if status == "accepted":
                self.queue.append(entry_id)
            max_entry = max(max_entry, self._trailing_number(entry_id))
            max_cont = max(max_cont, self._trailing_number(_text(question.get("question_id"))))
            max_tick = max(max_tick, entry.last_runtime_tick)
        self._entry_sequence = max_entry
        self._continuation_sequence = max_cont
        self._tick_number = max_tick

    @staticmethod
    def _trailing_number(value: str) -> int:
        try:
            return int(value.rsplit("-", 1)[-1])
        except (ValueError, IndexError):
            return 0

    def persistence_integrity(self) -> dict[str, Any] | None:
        if self.uql_store is None:
            return None
        return self.uql_store.verify_integrity()

    def _next_entry_id(self, prefix: str = "LEDGER") -> str:
        self._entry_sequence += 1
        return f"{prefix}-{self._entry_sequence:04d}"

    def _next_continuation_id(self) -> str:
        self._continuation_sequence += 1
        return f"CONT-{self._continuation_sequence:04d}"

    def seed_questions(self, questions: Iterable[Mapping[str, Any]]) -> int:
        seeded = 0
        for raw in questions:
            question = dict(raw)
            question_id = _text(question.get("question_id"))
            if not question_id:
                self.errors.append("seed question without question_id rejected")
                continue
            process_id = _text(question.get("process_id")) or f"PROC-{question_id}"
            entry_id = self._next_entry_id("Q")
            entry = LedgerEntry(
                entry_id=entry_id,
                process_id=process_id,
                question=question,
            )
            self.ledger[entry_id] = entry
            entry.status = "discoverable"
            seeded += 1

            declared = question.get("agent_decisions", {})
            if isinstance(declared, Mapping):
                for agent_id, decision in declared.items():
                    try:
                        self.record_agent_decision(
                            question_id=question_id,
                            agent_id=_text(agent_id),
                            decision=_text(decision),
                        )
                    except ValueError as exc:
                        self.errors.append(f"{question_id}: invalid predeclared decision: {exc}")
            self._persist_entry(entry, event_type="question_created" if self.uql_store is not None and question_id not in self.uql_store.frontier else "runtime_state")
        return seeded

    def discover(self) -> list[TaskProspect]:
        """Refresh agent-specific prospects from all currently discoverable entries."""
        active_questions = []
        for entry in self.ledger.values():
            if entry.status in TERMINAL_QUESTION_STATES:
                continue
            question = dict(entry.question)
            question["status"] = "unresolved"
            active_questions.append(question)
        prospects = discover_task_prospects(active_questions, self.agents, self.resources)
        self.prospects = {p.prospect_id: p for p in prospects}
        return prospects

    def record_agent_decision(self, *, question_id: str, agent_id: str, decision: str) -> bool:
        """Record an explicit agent choice; discovery never invents this decision."""
        decision = decision.strip().lower()
        prospects = [
            p for p in self.prospects.values()
            if p.question_id == question_id and p.agent_id == agent_id
        ]
        if not prospects:
            self.discover()
            prospects = [
                p for p in self.prospects.values()
                if p.question_id == question_id and p.agent_id == agent_id
            ]
        if not prospects:
            raise ValueError(f"no discovery prospect for question={question_id}, agent={agent_id}")
        prospect = prospects[0]
        if decision not in prospect.decision_options:
            raise ValueError(
                f"decision {decision!r} is not allowed; options={prospect.decision_options}"
            )
        self.agent_decisions[(question_id, agent_id)] = decision
        for entry in self.ledger.values():
            if _text(entry.question.get("question_id")) != question_id:
                continue
            entry.metadata.setdefault("agent_decisions", {})[agent_id] = decision
            if decision == "accept":
                if entry.status in {"discoverable", "deferred", "watching", "awaiting_resources"}:
                    entry.status = "accepted"
                if entry.entry_id not in self.queue:
                    self.queue.append(entry.entry_id)
            elif decision == "defer":
                entry.status = "deferred"
            elif decision == "watch":
                entry.status = "watching"
            elif decision == "request_resources":
                entry.status = "awaiting_resources"
            elif decision == "reject":
                entry.status = "rejected_by_agent"
            self._persist_entry(entry, event_type="agent_decision")
            return True
        return False

    def _build_experiment(self, entry: LedgerEntry) -> dict[str, Any]:
        """Build the minimal coordinator input from a ledger entry."""
        q = dict(entry.question)
        claim = dict(q.get("execution_claim", {}))
        if not claim:
            claim = {
                "claim_id": f"claim-{entry.process_id}-{entry.generation}",
                "execution_status": "completed",
                "verification_status": "verified",
                "verified_compute": 25,
                "compute_unit": "GPU-hours",
                "research_outcome": "not_required_for_provider_payment",
                "evidence_refs": [f"proof-{entry.process_id}-{entry.generation}"],
                "new_information_score": 0.5,
                "unresolved_information_delta": 0.1,
                "c5_valid": True,
            }
        return {
            "process_id": entry.process_id,
            "question": q,
            "execution_claim": claim,
            "requested_reward_rc": q.get("requested_reward_rc", 0),
            "payout_rail": q.get("payout_rail", "resource_credits"),
            "deadlock_bonus_budget": q.get("deadlock_bonus_budget", 0),
            "c5_valid": q.get("c5_valid", claim.get("c5_valid", True)),
            "resource_inflow": q.get("resource_inflow"),
        }

    def _make_continuation_question(self, entry: LedgerEntry, outcome: Mapping[str, Any]) -> dict[str, Any]:
        source_status = _text(outcome.get("status"))
        next_type = "deadlock" if bool(outcome.get("deadlock_recorded")) else "next_procedural_state"
        child_question = dict(entry.question)
        child_question.pop("execution_claim", None)
        child_question.pop("agent_decisions", None)
        child_question["question_id"] = self._next_continuation_id()
        child_question["parent_question_id"] = _text(entry.question.get("question_id"))
        child_question["continuation_type"] = next_type
        child_question["continuation_reason"] = source_status
        child_question["generation"] = entry.generation + 1
        child_question["priority"] = min(100, int(child_question.get("priority", 1)) + 1)
        child_question["source_process_id"] = entry.process_id
        child_question["research_outcome"] = _text(outcome.get("research_outcome"))
        return child_question

    def tick(self) -> RuntimeTick:
        self._tick_number += 1
        tick_id = f"TICK-{self._tick_number:04d}"
        prospects = self.discover()
        decisions_recorded = 0
        for entry in self.ledger.values():
            declared = entry.question.get("agent_decisions", {})
            if isinstance(declared, Mapping):
                for agent_id, decision in declared.items():
                    key = (_text(entry.question.get("question_id")), _text(agent_id))
                    if key in self.agent_decisions:
                        continue
                    try:
                        if self.record_agent_decision(
                            question_id=key[0],
                            agent_id=key[1],
                            decision=_text(decision),
                        ):
                            decisions_recorded += 1
                    except ValueError as exc:
                        self.errors.append(str(exc))

        if self.global_process_terminated:
            tick = RuntimeTick(
                tick_id=tick_id,
                tick_number=self._tick_number,
                prospects_generated=len(prospects),
                agent_decisions_recorded=decisions_recorded,
                entries_admitted=0,
                processes_started=0,
                processes_completed=0,
                continuation_enqueued=0,
                blocked_or_rejected=0,
                global_process_terminated=True,
                coordinator_status="global_terminated",
                errors=[],
            )
            self.tick_history.append(tick)
            return tick

        admitted_ids: list[str] = []
        while self.queue and len(admitted_ids) < self.max_batch_size:
            entry_id = self.queue.popleft()
            entry = self.ledger[entry_id]
            if entry.status in TERMINAL_QUESTION_STATES:
                continue
            entry.status = "admitted"
            entry.last_runtime_tick = self._tick_number
            self._persist_entry(entry, event_type="runtime_admission")
            admitted_ids.append(entry_id)

        if not admitted_ids:
            tick = RuntimeTick(
                tick_id=tick_id,
                tick_number=self._tick_number,
                prospects_generated=len(prospects),
                agent_decisions_recorded=decisions_recorded,
                entries_admitted=0,
                processes_started=0,
                processes_completed=0,
                continuation_enqueued=0,
                blocked_or_rejected=0,
                global_process_terminated=False,
                coordinator_status="idle",
                errors=[],
            )
            self.tick_history.append(tick)
            return tick

        specs = [self._build_experiment(self.ledger[eid]) for eid in admitted_ids]
        try:
            result: CoordinatorResult = coordinate_experiments(
                coordinator_id=f"{self.runtime_id}-{tick_id}",
                experiments=specs,
                agents=self.agents,
                resources=self.resources,
            )
            result_dict = asdict(result)
        except Exception as exc:
            message = f"tick {tick_id} isolated coordinator exception: {exc}"
            self.errors.append(message)
            for eid in admitted_ids:
                entry = self.ledger[eid]
                entry.status = "local_exception"
                self._persist_entry(entry, event_type="runtime_exception")
            tick = RuntimeTick(
                tick_id=tick_id,
                tick_number=self._tick_number,
                prospects_generated=len(prospects),
                agent_decisions_recorded=decisions_recorded,
                entries_admitted=len(admitted_ids),
                processes_started=0,
                processes_completed=0,
                continuation_enqueued=0,
                blocked_or_rejected=len(admitted_ids),
                global_process_terminated=False,
                coordinator_status="tick_isolated_exception",
                errors=[message],
            )
            self.tick_history.append(tick)
            return tick

        by_process = {o["process_id"]: o for o in result_dict.get("outcomes", [])}
        continuation_count = 0
        for entry_id in admitted_ids:
            entry = self.ledger[entry_id]
            outcome = by_process.get(entry.process_id)
            if outcome is None:
                entry.status = "missing_outcome"
                self.errors.append(f"{entry.process_id}: missing coordinator outcome")
                continue
            entry.last_process_status = _text(outcome.get("status"))
            entry.metadata["latest_outcome"] = _safe(outcome)
            if outcome.get("process_terminated"):
                entry.status = "terminated_local"
                self._persist_entry(entry, event_type="process_terminated")
            elif outcome.get("continuation_ready"):
                entry.status = "continuation_ready"
                self._persist_entry(entry, event_type="continuation_ready")
                child_question = self._make_continuation_question(entry, outcome)
                child_entry_id = self._next_entry_id("C")
                child = LedgerEntry(
                    entry_id=child_entry_id,
                    process_id=entry.process_id,
                    question=child_question,
                    source="continuation",
                    status="discoverable",
                    generation=entry.generation + 1,
                    parent_entry_id=entry.entry_id,
                    last_runtime_tick=self._tick_number,
                    last_process_status=_text(outcome.get("status")),
                    metadata={"from_outcome": _safe(outcome)},
                )
                self.ledger[child_entry_id] = child
                if self.uql_store is not None:
                    parent_qid = _text(entry.question.get("question_id"))
                    child_qid = _text(child.question.get("question_id"))
                    formulation = _text(child.question.get("formulation")) or _text(child.question.get("title")) or child_qid
                    try:
                        self.uql_store.derive_question(
                            parent_question_id=parent_qid,
                            child_question_id=child_qid,
                            formulation=formulation,
                            process_id=child.process_id,
                            unresolved_difference=_text(outcome.get("unresolved_difference")),
                            metadata=self._runtime_metadata(child),
                        )
                        self._persist_entry(child, event_type="continuation_discovery")
                    except ValueError as exc:
                        self.errors.append(f"{child_qid}: UQL continuation persistence failed: {exc}")
                continuation_count += 1
            elif outcome.get("local_failure"):
                entry.status = "blocked_local"
                self._persist_entry(entry, event_type="local_failure")
            else:
                entry.status = "processed"
                self._persist_entry(entry, event_type="process_processed")

        self.global_process_terminated = bool(result_dict.get("global_process_terminated", False))
        tick = RuntimeTick(
            tick_id=tick_id,
            tick_number=self._tick_number,
            prospects_generated=len(prospects),
            agent_decisions_recorded=decisions_recorded,
            entries_admitted=len(admitted_ids),
            processes_started=int(result_dict.get("processes_started", 0)),
            processes_completed=int(result_dict.get("processes_completed", 0)),
            continuation_enqueued=continuation_count,
            blocked_or_rejected=int(result_dict.get("processes_blocked_or_rejected", 0)),
            global_process_terminated=self.global_process_terminated,
            coordinator_status=_text(result_dict.get("status")),
            errors=[str(x) for x in result_dict.get("errors", [])],
        )
        self.tick_history.append(tick)
        self.errors.extend(tick.errors)
        return tick

    def run(self, *, max_ticks: int = 1) -> RuntimeResult:
        if max_ticks < 0:
            raise ValueError("max_ticks must be >= 0")
        seeded = sum(1 for e in self.ledger.values() if e.source == "seed")
        before = len(self.tick_history)
        for _ in range(max_ticks):
            tick = self.tick()
            if self.global_process_terminated or not self.queue:
                break
            if tick.entries_admitted == 0:
                break
        ticks = self.tick_history[before:]
        return self.snapshot(seeded=seeded, ticks_executed=len(ticks))

    def snapshot(self, *, seeded: Optional[int] = None, ticks_executed: Optional[int] = None) -> RuntimeResult:
        seed_count = seeded if seeded is not None else sum(1 for e in self.ledger.values() if e.source == "seed")
        continuation_count = sum(1 for e in self.ledger.values() if e.source == "continuation")
        started = sum(t.entries_admitted for t in self.tick_history)
        discoverable_count = sum(
            1 for e in self.ledger.values()
            if e.status in {"discoverable", "deferred", "watching", "awaiting_resources"}
        )
        if self.global_process_terminated:
            status = "global_terminated"
        elif self.queue:
            status = "active_with_pending_work"
        elif discoverable_count:
            status = "awaiting_agent_decision"
        else:
            status = "idle_no_pending_work"
        return RuntimeResult(
            runtime_id=self.runtime_id,
            status=status,
            ticks_executed=ticks_executed if ticks_executed is not None else len(self.tick_history),
            questions_seeded=seed_count,
            prospects_current=len(self.prospects),
            discoverable_count=discoverable_count,
            agent_decisions=[
                {"question_id": qid, "agent_id": aid, "decision": decision}
                for (qid, aid), decision in sorted(self.agent_decisions.items())
            ],
            processes_started=started,
            continuations_created=continuation_count,
            current_queue_size=len(self.queue),
            global_process_terminated=self.global_process_terminated,
            persistence_enabled=self.uql_store is not None,
            uql_integrity_valid=(self.persistence_integrity() or {}).get("valid") if self.uql_store is not None else None,
            uql_event_count=(self.persistence_integrity() or {}).get("event_count") if self.uql_store is not None else None,
            ledger_snapshot=[_safe(asdict(e)) for e in self.ledger.values()],
            tick_history=[_safe(asdict(t)) for t in self.tick_history],
            errors=list(self.errors),
        )


def demo() -> dict[str, Any]:
    """Run a deterministic runtime + restart-recovery demonstration."""
    with __import__("tempfile").TemporaryDirectory(prefix="ufcps-runtime-") as temp_dir:
        base = Path(temp_dir) / "uql"

        agents = [
            {
                "agent_id": "agent-runtime-001",
                "status": "available",
                "capabilities": [{"name": "simulation", "category": "research"}],
                "task_policy": {"accepts_tasks": True},
            },
            {
                "agent_id": "agent-runtime-002",
                "status": "available",
                "capabilities": [{"name": "analysis", "category": "research"}],
                "task_policy": {"accepts_tasks": True},
            },
        ]
        resources = [
            {
                "resource_id": "gpu-runtime-001",
                "provider_id": "provider-runtime-001",
                "resource_type": "gpu",
                "status": "available",
                "capabilities": [{"name": "gpu"}],
                "verification": {"verification_status": "verified"},
                "availability": {"available_capacity": 1000},
            },
            {
                "resource_id": "gpu-runtime-002",
                "provider_id": "provider-runtime-002",
                "resource_type": "gpu",
                "status": "available",
                "capabilities": [{"name": "gpu"}],
                "verification": {"verification_status": "verified"},
                "availability": {"available_capacity": 1000},
            },
        ]
        questions = [
            {
                "question_id": "Q-RUNTIME-PERSIST-001",
                "task_prospect_id": "TP-RUNTIME-PERSIST-001",
                "title": "persistent seed process",
                "required_capabilities": ["simulation"],
                "requirements": {"resources": [{"resource_type": "gpu", "quantity": 25, "unit": "GPU-hours"}]},
                "priority": 2,
                "requested_reward_rc": 10,
                "agent_decisions": {"agent-runtime-001": "accept"},
            },
            {
                "question_id": "Q-RUNTIME-PERSIST-002",
                "task_prospect_id": "TP-RUNTIME-PERSIST-002",
                "title": "persistent second process",
                "required_capabilities": ["simulation"],
                "requirements": {"resources": [{"resource_type": "gpu", "quantity": 25, "unit": "GPU-hours"}]},
                "priority": 1,
                "requested_reward_rc": 10,
                "agent_decisions": {"agent-runtime-001": "accept"},
            },
        ]

        runtime1 = SwarmRuntime(
            runtime_id="RUNTIME-PERSIST-DEMO",
            agents=agents,
            resources=resources,
            max_batch_size=2,
            persistence_path=base,
        )
        seeded = runtime1.seed_questions(questions)
        first = runtime1.tick()
        snapshot_before = runtime1.snapshot(seeded=seeded, ticks_executed=1)

        # Simulate a process restart. The new runtime reconstructs the active
        # frontier and accepted pending work exclusively from UQL persistence.
        runtime2 = SwarmRuntime(
            runtime_id="RUNTIME-PERSIST-DEMO",
            agents=agents,
            resources=resources,
            max_batch_size=2,
            persistence_path=base,
        )
        recovered_entries = len(runtime2.ledger)
        recovered_queue_before_decisions = len(runtime2.queue)
        continuation_entries = [
            entry for entry in runtime2.ledger.values()
            if entry.source == "continuation" and entry.status == "discoverable"
        ]
        for entry in continuation_entries:
            runtime2.discover()
            runtime2.record_agent_decision(
                question_id=_text(entry.question.get("question_id")),
                agent_id="agent-runtime-001",
                decision="accept",
            )
        second = runtime2.tick()
        snapshot_after = runtime2.snapshot(seeded=seeded, ticks_executed=runtime2._tick_number)
        integrity = runtime2.persistence_integrity() or {}

        assert first.global_process_terminated is False
        assert second.global_process_terminated is False
        assert recovered_entries == 4
        assert recovered_queue_before_decisions == 0
        assert len(continuation_entries) == 2
        assert snapshot_after.continuations_created == 4
        assert integrity.get("valid") is True
        assert integrity.get("hash_chain_valid") is True
        assert integrity.get("frontier_replay_equal") is True

        return {
            "status": "PASS",
            "persistence_path": str(base),
            "first_tick": _safe(asdict(first)),
            "recovered_entries": recovered_entries,
            "recovered_queue_before_decisions": recovered_queue_before_decisions,
            "recovered_continuation_entries": len(continuation_entries),
            "second_runtime": _safe(asdict(snapshot_after)),
            "integrity": integrity,
            "persisted_question_ids": sorted(runtime2.uql_store.frontier.keys()) if runtime2.uql_store else [],
            "pre_restart_event_count": snapshot_before.uql_event_count,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run deterministic runtime demo")
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
        print("UFCPS Swarm Runtime v1")
        print("Status:", result["status"])
        print("Recovered entries:", result["recovered_entries"])
        print("Recovered queue before decisions:", result["recovered_queue_before_decisions"])
        print("Recovered continuations:", result["recovered_continuation_entries"])
        print("Second runtime status:", result["second_runtime"]["status"])
        print("Second runtime continuations:", result["second_runtime"]["continuations_created"])
        print("Second runtime processes:", result["second_runtime"]["processes_started"])
        print("Second runtime queue:", result["second_runtime"]["current_queue_size"])
        print("UQL integrity:", result["integrity"]["valid"])
        print("UQL hash chain:", result["integrity"]["hash_chain_valid"])
        print("UQL events:", result["integrity"]["event_count"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
