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
            elif outcome.get("continuation_ready"):
                entry.status = "continuation_ready"
                child_question = self._make_continuation_question(entry, outcome)
                child_entry_id = self._next_entry_id("C")
                child = LedgerEntry(
                    entry_id=child_entry_id,
                    process_id=entry.process_id,
                    question=child_question,
                    source="continuation",
                    status="queued",
                    generation=entry.generation + 1,
                    parent_entry_id=entry.entry_id,
                    last_runtime_tick=self._tick_number,
                    last_process_status=_text(outcome.get("status")),
                    metadata={"from_outcome": _safe(outcome)},
                )
                self.ledger[child_entry_id] = child
                self.queue.append(child_entry_id)
                continuation_count += 1
            elif outcome.get("local_failure"):
                entry.status = "blocked_local"
            else:
                entry.status = "processed"

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
            ledger_snapshot=[_safe(asdict(e)) for e in self.ledger.values()],
            tick_history=[_safe(asdict(t)) for t in self.tick_history],
            errors=list(self.errors),
        )


def demo() -> dict[str, Any]:
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
            "question_id": "Q-RUNTIME-001",
            "task_prospect_id": "TP-RUNTIME-001",
            "title": "seed process",
            "required_capabilities": ["simulation"],
            "requirements": {"resources": [{"resource_type": "gpu", "quantity": 25, "unit": "GPU-hours"}]},
            "priority": 2,
            "requested_reward_rc": 10,
            "agent_decisions": {"agent-runtime-001": "accept"},
        },
        {
            "question_id": "Q-RUNTIME-002",
            "task_prospect_id": "TP-RUNTIME-002",
            "title": "seed deadlock process",
            "required_capabilities": ["simulation"],
            "requirements": {"resources": [{"resource_type": "gpu", "quantity": 25, "unit": "GPU-hours"}]},
            "priority": 1,
            "requested_reward_rc": 10,
            "execution_claim": {
                "claim_id": "claim-Q-RUNTIME-002",
                "execution_status": "deadlock",
                "verification_status": "verified",
                "verified_compute": 25,
                "compute_unit": "GPU-hours",
                "research_outcome": "not_required_for_provider_payment",
                "evidence_refs": ["proof-Q-RUNTIME-002"],
                "new_information_score": 0.8,
                "unresolved_information_delta": 0.3,
                "c5_valid": True,
                "deadlock": {
                    "deadlock_id": "deadlock-Q-RUNTIME-002",
                    "boundary_completeness": 1.0,
                    "constraint_completeness": 0.9,
                    "attempt_trace_completeness": 0.9,
                    "negative_result_quality": 0.8,
                    "evidence_quality": 1.0,
                    "substitution_guidance": 0.7,
                    "reproducibility": 0.8,
                },
            },
            "deadlock_bonus_budget": 10,
            "agent_decisions": {"agent-runtime-001": "accept"},
        },
    ]

    runtime = SwarmRuntime(
        runtime_id="RUNTIME-DEMO-001",
        agents=agents,
        resources=resources,
        max_batch_size=2,
    )
    seeded = runtime.seed_questions(questions)
    # Tick 1 runs the explicitly accepted seed questions.
    first_tick = runtime.tick()

    # Continuations must re-enter discovery. The demo simulates two explicit
    # agent decisions before Tick 2 rather than inheriting the old decision.
    continuation_entries = [
        entry for entry in runtime.ledger.values() if entry.source == "continuation"
    ]
    for entry in continuation_entries:
        runtime.record_agent_decision(
            question_id=_text(entry.question.get("question_id")),
            agent_id="agent-runtime-001",
            decision="accept",
        )

    second_tick = runtime.tick()
    data = _safe(asdict(runtime.snapshot(seeded=seeded, ticks_executed=2)))

    assert data["global_process_terminated"] is False
    assert data["questions_seeded"] == 2
    assert data["ticks_executed"] == 2
    assert data["continuations_created"] == 4
    assert data["current_queue_size"] == 2
    assert data["prospects_current"] >= 4
    assert all(t["prospects_generated"] >= 4 for t in data["tick_history"])
    assert all(t["global_process_terminated"] is False for t in data["tick_history"])
    assert any(e["source"] == "continuation" for e in data["ledger_snapshot"])

    return data


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
        print("Ticks:", result["ticks_executed"])
        print("Questions seeded:", result["questions_seeded"])
        print("Prospects current:", result["prospects_current"])
        print("Discoverable count:", result["discoverable_count"])
        print("Agent decisions:", len(result["agent_decisions"]))
        print("Processes started:", result["processes_started"])
        print("Continuations created:", result["continuations_created"])
        print("Queue size:", result["current_queue_size"])
        print("Global terminated:", result["global_process_terminated"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
