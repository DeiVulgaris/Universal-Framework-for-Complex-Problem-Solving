
"""UFCPS Level 2 — System Benchmark v1.

Measures observable runtime characteristics of the current Level 2 prototype.

This benchmark is intentionally descriptive rather than evaluative.  It does
not claim that one configuration is universally better than another and does
not establish scientific correctness or intelligence emergence.

Measured dimensions
-------------------
* end-to-end wall-clock latency;
* throughput in runtime processes / second;
* UQL persistence overhead;
* claim-store persistence overhead;
* claim + reservation overhead;
* audit ingestion overhead;
* process replay overhead;
* approximate cost of one observed P_n -> P_n+1 transition;
* scaling with batch size and process count.

The benchmark runs deterministic synthetic workloads against the local UFCPS
Level 2 components already present in the repository.  Times are local
machine measurements and are not hardware-normalized forecasts.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

SWARM_DIR = Path(__file__).resolve().parent
if str(SWARM_DIR) not in sys.path:
    sys.path.insert(0, str(SWARM_DIR))

from event_audit_bus_v1 import EventAuditBus
from process_replay_v1 import replay_process
from swarm_runtime_v1 import SwarmRuntime


@dataclass(frozen=True)
class TimingStats:
    samples: int
    mean_ms: float
    median_ms: float
    min_ms: float
    max_ms: float
    stdev_ms: float

    @staticmethod
    def from_seconds(values: Sequence[float]) -> "TimingStats":
        if not values:
            raise ValueError("timing sample set must not be empty")
        ms = [x * 1000.0 for x in values]
        return TimingStats(
            samples=len(ms),
            mean_ms=statistics.mean(ms),
            median_ms=statistics.median(ms),
            min_ms=min(ms),
            max_ms=max(ms),
            stdev_ms=statistics.stdev(ms) if len(ms) > 1 else 0.0,
        )


@dataclass(frozen=True)
class BenchmarkRun:
    workload: int
    batch_size: int
    persistence: bool
    timing: TimingStats
    processes_started: int
    continuations_created: int
    claims_created: int
    reservations: int
    audit_events: int
    replay_events: int
    queue_remaining: int
    errors: int

    @property
    def throughput_processes_per_sec(self) -> float:
        total_s = self.timing.mean_ms / 1000.0
        return self.processes_started / total_s if total_s > 0 else 0.0

    @property
    def transition_cost_ms(self) -> float:
        transitions = max(1, self.processes_started + self.continuations_created)
        return self.timing.mean_ms / transitions

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["throughput_processes_per_sec"] = self.throughput_processes_per_sec
        data["transition_cost_ms"] = self.transition_cost_ms
        return data


@dataclass(frozen=True)
class ComponentOverhead:
    component: str
    stats: TimingStats
    unit: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SystemBenchmarkResult:
    benchmark_version: str
    environment: dict[str, Any]
    runs: list[BenchmarkRun]
    scaling: list[BenchmarkRun]
    overhead: list[ComponentOverhead]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_version": self.benchmark_version,
            "environment": self.environment,
            "runs": [r.to_dict() for r in self.runs],
            "scaling": [r.to_dict() for r in self.scaling],
            "overhead": [o.to_dict() for o in self.overhead],
            "summary": self.summary,
        }


def _resources(count: int = 8) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for i in range(count):
        resources.append(
            {
                "resource_id": f"gpu-bench-{i:03d}",
                "provider_id": f"provider-bench-{i:03d}",
                "resource_type": "gpu",
                "status": "available",
                "capabilities": [{"capability_id": "gpu", "name": "gpu", "category": "compute"}],
                "verification": {"verification_status": "verified"},
                "availability": {
                    "available_capacity": 100000,
                    "capacity_unit": "GPU-hours",
                },
            }
        )
    return resources


def _agents(count: int) -> list[dict[str, Any]]:
    return [
        {
            "agent_id": f"agent-bench-{i:03d}",
            "status": "available",
            "capabilities": [
                {"name": "simulation", "category": "research", "confidence": 0.95}
            ],
            "task_policy": {"accepts_tasks": True},
        }
        for i in range(count)
    ]


def _questions(count: int, agent_id: str) -> list[dict[str, Any]]:
    return [
        {
            "question_id": f"Q-BENCH-{i:05d}",
            "process_id": f"PROC-BENCH-{i:05d}",
            "title": f"synthetic benchmark question {i}",
            "required_capabilities": ["simulation"],
            "requirements": {
                "resources": [
                    {"resource_type": "gpu", "quantity": 25, "unit": "GPU-hours"}
                ]
            },
            "requested_reward_rc": 10,
            "agent_decisions": {agent_id: "accept"},
        }
        for i in range(count)
    ]


def _run_runtime_once(workload: int, batch_size: int, persistence: bool) -> BenchmarkRun:
    with tempfile.TemporaryDirectory(prefix="ufcps-bench-") as temp_dir:
        persistence_path = Path(temp_dir) / "uql" if persistence else None
        resources = _resources(max(4, workload))
        agents = _agents(max(1, min(8, workload)))
        primary_agent = agents[0]["agent_id"]
        questions = _questions(workload, primary_agent)
        runtime = SwarmRuntime(
            runtime_id=f"BENCH-{workload}-{batch_size}-{int(persistence)}",
            agents=agents,
            resources=resources,
            max_batch_size=batch_size,
            persistence_path=persistence_path,
        )
        runtime.seed_questions(questions)
        start = time.perf_counter()
        result = runtime.run(max_ticks=1)
        elapsed = time.perf_counter() - start
        claims_created = sum(
            t["claims_created"] for t in result.tick_history
        )
        reservations = sum(
            t["claims_resource_reserved"] for t in result.tick_history
        )
        return BenchmarkRun(
            workload=workload,
            batch_size=batch_size,
            persistence=persistence,
            timing=TimingStats.from_seconds([elapsed]),
            processes_started=result.processes_started,
            continuations_created=result.continuations_created,
            claims_created=claims_created,
            reservations=reservations,
            audit_events=0,
            replay_events=0,
            queue_remaining=result.current_queue_size,
            errors=len(result.errors),
        )


def _measure_component_overhead() -> list[ComponentOverhead]:
    overhead: list[ComponentOverhead] = []
    with tempfile.TemporaryDirectory(prefix="ufcps-component-bench-") as temp_dir:
        base = Path(temp_dir)

        # UQL write overhead.
        from uql_store_v1 import UQLStore
        uql_samples: list[float] = []
        for i in range(30):
            store = UQLStore(base / f"uql-{i}")
            t0 = time.perf_counter()
            store.create_question(
                question_id=f"Q-{i}",
                process_id=f"P-{i}",
                formulation="benchmark",
                required_capabilities=["simulation"],
                required_resources=[],
                metadata={"benchmark": True},
            )
            uql_samples.append(time.perf_counter() - t0)
        overhead.append(ComponentOverhead(
            "uql_create_question",
            TimingStats.from_seconds(uql_samples),
            "ms/event",
            "Local append + atomic frontier snapshot.",
        ))

        # Claim/reservation overhead, isolated from the rest of runtime.
        from task_claim_engine_v1 import TaskClaimEngine
        claim_samples: list[float] = []
        for i in range(30):
            engine = TaskClaimEngine(
                engine_id=f"CLAIM-BENCH-{i}",
                questions=[{"question_id": "Q", "status": "unresolved"}],
                prospects=[{
                    "prospect_id": "TP-Q-A",
                    "question_id": "Q",
                    "agent_id": "A",
                    "required_capabilities": ["simulation"],
                    "required_resources": [{"resource_type": "gpu", "quantity": 25, "unit": "GPU-hours"}],
                }],
                agents=[{"agent_id": "A", "capabilities": ["simulation"]}],
                resources=[{
                    "resource_id": "R",
                    "resource_type": "gpu",
                    "provider_id": "PROV",
                    "status": "available",
                    "verification": {"verification_status": "verified"},
                    "availability": {"available_capacity": 100, "capacity_unit": "GPU-hours"},
                }],
                now="2026-09-21T21:00:00Z",
            )
            t0 = time.perf_counter()
            engine.create_claim(
                claim_id=f"CL-{i}", question_id="Q", agent_id="A", prospect_id="TP-Q-A",
                expires_at="2026-09-21T22:00:00Z", method_intent="bench",
                requested_resources=[{"resource_type": "gpu", "quantity": 25, "unit": "GPU-hours"}],
            )
            engine.admit_claim(f"CL-{i}")
            engine.reserve_resources(f"CL-{i}")
            engine.activate(f"CL-{i}")
            claim_samples.append(time.perf_counter() - t0)
        overhead.append(ComponentOverhead(
            "claim_plus_reservation",
            TimingStats.from_seconds(claim_samples),
            "ms/claim",
            "Claim admission plus one resource reservation and activation.",
        ))

        # Audit append overhead.
        audit = EventAuditBus(base / "audit", bus_id="BENCH-AUDIT")
        audit_samples: list[float] = []
        parent = None
        for i in range(30):
            t0 = time.perf_counter()
            event = audit.append(
                event_type="benchmark_event",
                domain="RUNTIME",
                source_system="level2_system_benchmark_v1",
                source_event_id=f"EV-{i}",
                process_id="PROC-BENCH",
                question_id="Q-BENCH",
                causal_parent_event_id=parent,
                verification_status="verified",
                payload={"i": i},
            )
            audit_samples.append(time.perf_counter() - t0)
            parent = event.event_id
        overhead.append(ComponentOverhead(
            "audit_append",
            TimingStats.from_seconds(audit_samples),
            "ms/event",
            "Local JSONL append with SHA-256 causal hash chain.",
        ))

        # Replay overhead on the same chain.
        replay_samples: list[float] = []
        events = audit.events()
        for _ in range(30):
            t0 = time.perf_counter()
            replay_process(events, process_id="PROC-BENCH")
            replay_samples.append(time.perf_counter() - t0)
        overhead.append(ComponentOverhead(
            "process_replay",
            TimingStats.from_seconds(replay_samples),
            "ms/process",
            "Observational reconstruction of the audit chain; no re-execution.",
        ))
    return overhead


def _measure_audit_and_replay_for_workload(workload: int) -> tuple[int, int]:
    with tempfile.TemporaryDirectory(prefix="ufcps-audit-workload-") as temp_dir:
        bus = EventAuditBus(Path(temp_dir) / "audit", bus_id="BENCH-WORKLOAD-AUDIT")
        for i in range(workload):
            qid = f"Q-W-{i:05d}"
            pid = f"P-W-{i:05d}"
            parent = bus.append(
                event_type="question_created", domain="UQL", source_system="bench",
                source_event_id=f"Q-{i}", process_id=pid, question_id=qid,
                verification_status="verified", payload={"status": "unresolved"},
            ).event_id
            parent = bus.append(
                event_type="claim_accepted", domain="CLAIM", source_system="bench",
                source_event_id=f"C-{i}", process_id=pid, question_id=qid,
                actor_id="agent-bench-000", causal_parent_event_id=parent,
                verification_status="verified", payload={"claim_id": f"CL-{i}"},
            ).event_id
            bus.append(
                event_type="execution_completed", domain="EXECUTION", source_system="bench",
                source_event_id=f"E-{i}", process_id=pid, question_id=qid,
                actor_id="agent-bench-000", causal_parent_event_id=parent,
                verification_status="verified", payload={"result": "reference"},
            )
        events = bus.events()
        replay_events = 0
        for i in range(workload):
            replay = replay_process(events, process_id=f"P-W-{i:05d}")
            replay_events += replay.event_count
            assert replay.integrity_valid
        assert bus.verify_integrity()["valid"]
        return len(events), replay_events


def run_benchmark(
    *,
    workloads: Sequence[int] = (4, 8, 16, 32),
    batch_sizes: Sequence[int] = (1, 4, 8, 16),
) -> SystemBenchmarkResult:
    runs: list[BenchmarkRun] = []
    for workload in workloads:
        for batch_size in batch_sizes:
            for persistence in (False, True):
                run = _run_runtime_once(workload, min(batch_size, workload), persistence)
                runs.append(run)

    scaling = [
        _run_runtime_once(workload, workload, persistence=False)
        for workload in workloads
    ]
    overhead = _measure_component_overhead()

    audit_events, replay_events = _measure_audit_and_replay_for_workload(max(workloads))

    enrichment = []
    for run in runs:
        enrichment.append(BenchmarkRun(
            workload=run.workload,
            batch_size=run.batch_size,
            persistence=run.persistence,
            timing=run.timing,
            processes_started=run.processes_started,
            continuations_created=run.continuations_created,
            claims_created=run.claims_created,
            reservations=run.reservations,
            audit_events=audit_events if run.workload == max(workloads) else 0,
            replay_events=replay_events if run.workload == max(workloads) else 0,
            queue_remaining=run.queue_remaining,
            errors=run.errors,
        ))

    persistence_pairs = {}
    for workload in workloads:
        for batch_size in batch_sizes:
            off = next(r for r in enrichment if r.workload == workload and r.batch_size == min(batch_size, workload) and not r.persistence)
            on = next(r for r in enrichment if r.workload == workload and r.batch_size == min(batch_size, workload) and r.persistence)
            key = f"workload={workload},batch={min(batch_size, workload)}"
            persistence_pairs[key] = {
                "without_persistence_ms": off.timing.mean_ms,
                "with_persistence_ms": on.timing.mean_ms,
                "delta_ms": on.timing.mean_ms - off.timing.mean_ms,
                "multiplicative_factor": on.timing.mean_ms / off.timing.mean_ms if off.timing.mean_ms else 0.0,
            }

    finite_transition_costs = [r.transition_cost_ms for r in enrichment if r.processes_started > 0]
    summary = {
        "method": "deterministic_local_prototype_measurement",
        "interpretation": "Observed runtime characteristics only; not a hardware-normalized forecast.",
        "max_workload": max(workloads),
        "max_batch_size": max(batch_sizes),
        "transition_cost_ms_mean_across_runs": statistics.mean(finite_transition_costs),
        "persistence_comparison": persistence_pairs,
        "all_run_errors": sum(r.errors for r in enrichment),
        "scaling_note": "Use scaling rows to inspect how wall time changes with workload; no universal scaling law is inferred.",
    }

    return SystemBenchmarkResult(
        benchmark_version="1.0",
        environment={
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "workloads": list(workloads),
            "batch_sizes": list(batch_sizes),
        },
        runs=enrichment,
        scaling=scaling,
        overhead=overhead,
        summary=summary,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--workloads", nargs="+", type=int, default=[4, 8, 16, 32])
    parser.add_argument("--batches", nargs="+", type=int, default=[1, 4, 8, 16])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_benchmark(workloads=args.workloads, batch_sizes=args.batches)
    data = result.to_dict()
    if args.as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("UFCPS Level 2 System Benchmark v1")
        print("Runs:", len(data["runs"]))
        print("Max workload:", data["summary"]["max_workload"])
        print("Mean observed transition cost (ms):", round(data["summary"]["transition_cost_ms_mean_across_runs"], 4))
        print("Total run errors:", data["summary"]["all_run_errors"])
        print("Persistence comparison:")
        for key, value in data["summary"]["persistence_comparison"].items():
            print(
                f"  {key}: off={value['without_persistence_ms']:.3f} ms | "
                f"on={value['with_persistence_ms']:.3f} ms | "
                f"factor={value['multiplicative_factor']:.2f}"
            )
        print("Component overhead:")
        for item in data["overhead"]:
            print(
                f"  {item['component']}: mean={item['stats']['mean_ms']:.3f} ms | "
                f"median={item['stats']['median_ms']:.3f} ms/{item['unit']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
