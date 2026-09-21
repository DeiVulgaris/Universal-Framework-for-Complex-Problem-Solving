
"""UFCPS Level 2 — End-to-End Persistence Comparison v1.

Compares the current Level 2 runtime with the legacy persistence path and the
checkpointed persistence path under the same deterministic synthetic workload.

This is a descriptive systems benchmark, not an intelligence score and not a
claim of universal performance superiority. All timing values are local
observations on the machine running the benchmark.

The benchmark measures:
* end-to-end runtime wall-clock time;
* throughput in processed runtime ticks / second;
* UQL and Claim Store event counts;
* persistence integrity after the run;
* semantic state equivalence across persistence modes;
* observed persistence speedup ratio for the tested configuration;
* sensitivity to checkpoint and journal batch cadence.

The optimized store is configured through the existing public store APIs. The
runtime orchestration code itself is not modified by this benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SWARM_DIR = Path(__file__).resolve().parent
if str(SWARM_DIR) not in sys.path:
    sys.path.insert(0, str(SWARM_DIR))

from swarm_runtime_v1 import SwarmRuntime
from task_claim_store_v1 import TaskClaimStore
from uql_store_v1 import UQLStore


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
            raise ValueError("timing samples must not be empty")
        ms = [value * 1000.0 for value in values]
        return TimingStats(
            samples=len(ms),
            mean_ms=statistics.mean(ms),
            median_ms=statistics.median(ms),
            min_ms=min(ms),
            max_ms=max(ms),
            stdev_ms=statistics.stdev(ms) if len(ms) > 1 else 0.0,
        )


@dataclass(frozen=True)
class RuntimeMode:
    name: str
    optimized_persistence: bool
    journal_batch_size: int = 1
    checkpoint_interval: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModeRun:
    mode: RuntimeMode
    workload: int
    ticks_requested: int
    timing: TimingStats
    ticks_executed: int
    processes_started: int
    continuations_created: int
    current_queue_size: int
    discoverable_count: int
    uql_event_count: int
    claim_event_count: int
    uql_integrity_valid: bool
    claim_integrity_valid: bool
    global_process_terminated: bool
    errors: int
    semantic_digest: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["mode"] = self.mode.to_dict()
        data["ticks_per_second"] = (
            self.ticks_executed / (self.timing.mean_ms / 1000.0)
            if self.timing.mean_ms > 0
            else 0.0
        )
        return data


def _agents(count: int = 2) -> list[dict[str, Any]]:
    return [
        {
            "agent_id": f"agent-e2e-{i:03d}",
            "status": "available",
            "capabilities": [
                {"name": "simulation", "category": "research", "confidence": 0.95}
            ],
            "task_policy": {"accepts_tasks": True},
        }
        for i in range(count)
    ]


def _resources(count: int) -> list[dict[str, Any]]:
    return [
        {
            "resource_id": f"gpu-e2e-{i:03d}",
            "provider_id": f"provider-e2e-{i:03d}",
            "resource_type": "gpu",
            "status": "available",
            "capabilities": [
                {"capability_id": "gpu", "name": "gpu", "category": "compute"}
            ],
            "verification": {"verification_status": "verified"},
            "availability": {
                "available_capacity": 100000,
                "capacity_unit": "GPU-hours",
            },
        }
        for i in range(count)
    ]


def _questions(count: int, agent_id: str) -> list[dict[str, Any]]:
    return [
        {
            "question_id": f"Q-E2E-{i:05d}",
            "process_id": f"PROC-E2E-{i:05d}",
            "title": f"synthetic persistence comparison {i}",
            "formulation": f"synthetic process {i}",
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


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, float):
        return round(value, 10)
    return value


def _semantic_snapshot(runtime: SwarmRuntime) -> dict[str, Any]:
    ledger: list[dict[str, Any]] = []
    for entry_id, entry in sorted(runtime.ledger.items()):
        question = dict(entry.question)
        question.pop("execution_claim", None)
        question.pop("agent_decisions", None)
        metadata = dict(entry.metadata)
        claim = dict(metadata.get("claim") or {})
        claim.pop("created_at", None)
        claim.pop("expires_at", None)
        metadata["claim"] = claim
        historical = []
        for item in metadata.get("historical_claims", []):
            item = dict(item)
            item.pop("created_at", None)
            historical.append(item)
        metadata["historical_claims"] = historical
        metadata.pop("last_runtime_event", None)
        ledger.append(
            {
                "entry_id": entry_id,
                "process_id": entry.process_id,
                "question": question,
                "source": entry.source,
                "status": entry.status,
                "generation": entry.generation,
                "parent_entry_id": entry.parent_entry_id,
                "last_process_status": entry.last_process_status,
                "metadata": metadata,
            }
        )

    claims: list[dict[str, Any]] = []
    if runtime.claim_engine is not None:
        for claim_id, claim in sorted(runtime.claim_engine.claims.items()):
            raw = asdict(claim)
            raw.pop("created_at", None)
            raw.pop("expires_at", None)
            claims.append(raw)

    resources: list[dict[str, Any]] = []
    if runtime.claim_engine is not None:
        for resource_id, resource in sorted(runtime.claim_engine.resources.items()):
            resources.append(dict(resource))
    else:
        resources = [dict(x) for x in sorted(runtime.resources, key=lambda r: str(r.get("resource_id", "")))]

    return {
        "ledger": ledger,
        "claims": claims,
        "resources": resources,
        "queue": list(runtime.queue),
        "global_process_terminated": runtime.global_process_terminated,
        "agent_decisions": [
            {"question_id": q, "agent_id": a, "decision": d}
            for (q, a), d in sorted(runtime.agent_decisions.items())
        ],
    }


def _digest(snapshot: Mapping[str, Any]) -> str:
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _configure_persistence(
    runtime: SwarmRuntime,
    base: Path,
    mode: RuntimeMode,
) -> None:
    """Install the chosen persistence backends without altering runtime code."""
    runtime.uql_store = UQLStore(
        base / "uql",
        optimized_persistence=mode.optimized_persistence,
        journal_batch_size=mode.journal_batch_size,
        checkpoint_interval=mode.checkpoint_interval,
        durable=True,
    )
    claim_path = base / "claims"
    runtime.claim_store = TaskClaimStore(
        claim_path,
        store_id=f"{runtime.runtime_id}-claim-store",
        persistence_mode="checkpointed" if mode.optimized_persistence else "legacy",
        journal_batch_size=mode.journal_batch_size,
        checkpoint_interval=mode.checkpoint_interval,
        durable=True,
    )
    runtime.persistence_path = str(base / "uql")
    runtime.claim_persistence_path = str(claim_path)
    runtime._claim_store_event_cursor = 0
    runtime.claim_store_recovered = False


def _accept_pending(runtime: SwarmRuntime, agent_id: str) -> int:
    """Explicitly accept all currently discoverable continuation questions."""
    runtime.discover()
    accepted = 0
    entries = list(runtime.ledger.values())
    for entry in entries:
        if entry.status not in {"discoverable", "deferred", "watching", "awaiting_resources"}:
            continue
        question_id = str(entry.question.get("question_id", ""))
        if not question_id:
            continue
        prospects = [
            p for p in runtime.prospects.values()
            if p.question_id == question_id and p.agent_id == agent_id
        ]
        if not prospects:
            continue
        try:
            if runtime.record_agent_decision(
                question_id=question_id,
                agent_id=agent_id,
                decision="accept",
            ):
                accepted += 1
        except ValueError as exc:
            runtime.errors.append(str(exc))
    return accepted


def _run_once(
    mode: RuntimeMode,
    *,
    workload: int,
    ticks: int,
    batch_size: int,
) -> ModeRun:
    agents = _agents(max(2, min(4, workload)))
    resources = _resources(max(4, workload))
    primary_agent = agents[0]["agent_id"]

    with tempfile.TemporaryDirectory(prefix="ufcps-level2-persistence-compare-") as temp_dir:
        base = Path(temp_dir) / mode.name
        runtime = SwarmRuntime(
            runtime_id=f"E2E-{mode.name}-{workload}-{batch_size}",
            agents=agents,
            resources=resources,
            max_batch_size=batch_size,
            persistence_path=None,
            claim_persistence_path=None,
            recover_existing=False,
        )
        _configure_persistence(runtime, base, mode)
        runtime.seed_questions(_questions(workload, primary_agent))

        start = time.perf_counter()
        for _ in range(ticks):
            _accept_pending(runtime, primary_agent)
            tick = runtime.tick()
            if runtime.global_process_terminated:
                break
            if tick.entries_admitted == 0:
                # Keep the semantics explicit: no automatic continuation claim
                # is invented when the discovery layer did not admit work.
                break
        elapsed = time.perf_counter() - start

        # Force any intentionally batched journal data to disk before observing
        # final integrity and counts.
        runtime.uql_store.flush()
        if runtime.claim_store and runtime.claim_store.persistence_mode == "checkpointed":
            assert runtime.claim_store._event_store is not None
            runtime.claim_store._event_store.flush()

        uql_integrity = runtime.uql_store.verify_integrity()
        claim_integrity = runtime.claim_store.verify_integrity()
        semantic = _semantic_snapshot(runtime)

        return ModeRun(
            mode=mode,
            workload=workload,
            ticks_requested=ticks,
            timing=TimingStats.from_seconds([elapsed]),
            ticks_executed=len(runtime.tick_history),
            processes_started=sum(t.entries_admitted for t in runtime.tick_history),
            continuations_created=sum(1 for e in runtime.ledger.values() if e.source == "continuation"),
            current_queue_size=len(runtime.queue),
            discoverable_count=sum(
                1
                for e in runtime.ledger.values()
                if e.status in {"discoverable", "deferred", "watching", "awaiting_resources"}
            ),
            uql_event_count=int(uql_integrity.get("event_count", 0)),
            claim_event_count=int(claim_integrity.get("event_count", 0)),
            uql_integrity_valid=bool(uql_integrity.get("valid")),
            claim_integrity_valid=bool(claim_integrity.get("valid")),
            global_process_terminated=runtime.global_process_terminated,
            errors=len(runtime.errors),
            semantic_digest=_digest(semantic),
        )


def _compare_semantics(left: ModeRun, right: ModeRun) -> dict[str, Any]:
    fields = [
        "workload",
        "ticks_executed",
        "processes_started",
        "continuations_created",
        "current_queue_size",
        "discoverable_count",
        "uql_event_count",
        "claim_event_count",
        "uql_integrity_valid",
        "claim_integrity_valid",
        "global_process_terminated",
        "errors",
    ]
    mismatches = [
        field
        for field in fields
        if getattr(left, field) != getattr(right, field)
    ]
    return {
        "equivalent_observables": not mismatches and left.semantic_digest == right.semantic_digest,
        "observable_mismatches": mismatches,
        "semantic_digest_equal": left.semantic_digest == right.semantic_digest,
        "left_digest": left.semantic_digest,
        "right_digest": right.semantic_digest,
    }


def run_benchmark(
    *,
    workload: int = 8,
    ticks: int = 4,
    batch_size: int = 4,
    repeat: int = 3,
) -> dict[str, Any]:
    if workload < 1 or ticks < 1 or batch_size < 1 or repeat < 1:
        raise ValueError("workload, ticks, batch_size and repeat must be >= 1")

    mode_specs = [
        RuntimeMode("legacy", False, 1, 1),
        RuntimeMode("checkpointed_4_4", True, 4, 4),
        RuntimeMode("checkpointed_16_16", True, 16, 16),
        RuntimeMode("checkpointed_16_64", True, 16, 64),
    ]

    samples: dict[str, list[ModeRun]] = {spec.name: [] for spec in mode_specs}
    for _ in range(repeat):
        for spec in mode_specs:
            samples[spec.name].append(
                _run_once(
                    spec,
                    workload=workload,
                    ticks=ticks,
                    batch_size=batch_size,
                )
            )

    aggregate: dict[str, Any] = {}
    for spec in mode_specs:
        runs = samples[spec.name]
        aggregate[spec.name] = {
            "mode": spec.to_dict(),
            "timing_ms": TimingStats.from_seconds(
                [run.timing.mean_ms / 1000.0 for run in runs]
            ).__dict__,
            "ticks_executed_mean": statistics.mean(r.ticks_executed for r in runs),
            "processes_started_mean": statistics.mean(r.processes_started for r in runs),
            "continuations_created_mean": statistics.mean(r.continuations_created for r in runs),
            "uql_event_count": runs[-1].uql_event_count,
            "claim_event_count": runs[-1].claim_event_count,
            "uql_integrity_valid": all(r.uql_integrity_valid for r in runs),
            "claim_integrity_valid": all(r.claim_integrity_valid for r in runs),
            "semantic_digests": [r.semantic_digest for r in runs],
            "semantic_digest_stable_across_repeats": len({r.semantic_digest for r in runs}) == 1,
            "errors_total": sum(r.errors for r in runs),
        }

    legacy_time = float(aggregate["legacy"]["timing_ms"]["mean_ms"])
    speedup: dict[str, float] = {}
    for spec in mode_specs[1:]:
        optimized_time = float(aggregate[spec.name]["timing_ms"]["mean_ms"])
        speedup[spec.name] = legacy_time / optimized_time if optimized_time > 0 else 0.0

    baseline = samples["legacy"][0]
    comparisons = {
        name: _compare_semantics(baseline, runs[0])
        for name, runs in samples.items()
        if name != "legacy"
    }

    all_integrity = all(
        value["uql_integrity_valid"] and value["claim_integrity_valid"]
        for value in aggregate.values()
    )
    all_semantic_repeatable = all(
        value["semantic_digest_stable_across_repeats"]
        for value in aggregate.values()
    )

    return {
        "benchmark_version": "level2-persistence-comparison-v1",
        "descriptor": "Descriptive end-to-end persistence comparison; local machine observations only.",
        "configuration": {
            "workload": workload,
            "ticks": ticks,
            "batch_size": batch_size,
            "repeat": repeat,
        },
        "results": aggregate,
        "legacy_to_checkpointed_time_ratio": speedup,
        "semantic_comparison_to_legacy": comparisons,
        "validation": {
            "all_integrity_valid": all_integrity,
            "all_semantic_results_stable_across_repeats": all_semantic_repeatable,
            "all_runs_error_free": all(value["errors_total"] == 0 for value in aggregate.values()),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workload", type=int, default=8)
    parser.add_argument("--ticks", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_benchmark(
        workload=args.workload,
        ticks=args.ticks,
        batch_size=args.batch_size,
        repeat=args.repeat,
    )
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("UFCPS Level 2 — persistence comparison")
        print(json.dumps(result["configuration"], ensure_ascii=False))
        for name, value in result["results"].items():
            timing = value["timing_ms"]
            print(
                f"{name:24s} mean={timing['mean_ms']:.3f} ms "
                f"median={timing['median_ms']:.3f} ms "
                f"UQL={value['uql_event_count']} "
                f"CLAIM={value['claim_event_count']}"
            )
        print("ratios:", json.dumps(result["legacy_to_checkpointed_time_ratio"], indent=2))
        print("validation:", json.dumps(result["validation"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
