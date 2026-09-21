#!/usr/bin/env python3
"""UFCPS Level 2 — Persistence Optimization Benchmark v1.

Experimental benchmark for locating persistence overhead without changing any
production UFCPS persistence semantics.

The benchmark separates five cost classes:

    1. canonical JSON serialization
    2. SHA-256 event-chain hashing
    3. append + flush + fsync of an event journal
    4. atomic JSON snapshot replacement
    5. atomic metadata replacement

It then compares persistence patterns:

    durable_per_event
        Current v1-style behavior: durable journal write plus atomic snapshot
        and metadata update for every logical event.

    journal_only
        Durable journal write only. Useful for measuring the cost of removing
        the per-event snapshot path. This is a benchmark variant, not a
        production recommendation.

    batched_journal
        Same deterministic journal records, written in batches with one
        flush+fsync per batch. This preserves event bytes and the hash chain
        while changing durability granularity between batch boundaries.

    batched_journal_snapshot
        Batched journal plus a deterministic snapshot checkpoint every N
        events. This makes checkpoint frequency an explicit variable.

    non_durable_reference
        No fsync and no atomic snapshot/metadata durability. This is included
        only as a lower-bound reference and is NOT semantically equivalent to
        durable persistence.

The script does not modify the UFCPS runtime or persistence modules. It uses
small deterministic payloads representative of UQL, Claim Store and Audit Bus
records, and validates byte-for-byte equivalence of durable and batched event
journals before reporting timings.

Usage examples:

    python persistence_optimization_benchmark_v1.py
    python persistence_optimization_benchmark_v1.py --json
    python persistence_optimization_benchmark_v1.py --events 256 --batch-sizes 1 4 16 64
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

GENESIS_HASH = "0" * 64
BENCHMARK_VERSION = "1.0"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def chain_hash(previous_hash: str, payload: Mapping[str, Any]) -> str:
    body = f"{previous_hash}|{canonical(dict(payload))}".encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def fsync_supported() -> bool:
    return hasattr(os, "fsync")


def durable_append(path: Path, lines: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def non_durable_append(path: Path, lines: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line)
        handle.flush()


def atomic_json_write(path: Path, payload: Any, *, durable: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        tmp_path = Path(temp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            if durable:
                os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                pass


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


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
class ComponentMeasurement:
    component: str
    unit: str
    stats: TimingStats
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PatternMeasurement:
    pattern: str
    event_count: int
    batch_size: int
    stats: TimingStats
    event_bytes: int
    final_hash: str
    journal_equivalent_to_reference: bool
    durable: bool
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EquivalenceResult:
    same_journal_bytes: bool
    same_event_count: bool
    same_final_hash: bool
    same_logical_state: bool
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OptimizationResult:
    benchmark_version: str
    environment: dict[str, Any]
    components: list[ComponentMeasurement]
    patterns: list[PatternMeasurement]
    equivalence: EquivalenceResult
    contribution_estimate: dict[str, Any]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_version": self.benchmark_version,
            "environment": self.environment,
            "components": [item.to_dict() for item in self.components],
            "patterns": [item.to_dict() for item in self.patterns],
            "equivalence": self.equivalence.to_dict(),
            "contribution_estimate": self.contribution_estimate,
            "summary": self.summary,
        }


def build_records(event_count: int) -> tuple[list[str], str, dict[str, Any]]:
    """Build a deterministic representative event stream.

    Payloads deliberately resemble all three persistent stores while staying
    independent of production implementation details. The final logical state
    is a compact replay of event sequence -> event hash.
    """
    lines: list[str] = []
    previous = GENESIS_HASH
    state: dict[str, Any] = {
        "process_id": "P-OPT-BENCH",
        "question_id": "Q-OPT-BENCH",
        "last_sequence": 0,
        "last_event_hash": GENESIS_HASH,
    }
    for sequence in range(1, event_count + 1):
        if sequence % 3 == 1:
            domain = "UQL"
            event_type = "frontier_update"
            payload = {
                "question_id": "Q-OPT-BENCH",
                "unresolved_difference": f"difference-{sequence}",
                "continuation": True,
                "required_capabilities": ["simulation", "analysis"],
            }
        elif sequence % 3 == 2:
            domain = "CLAIM"
            event_type = "claim_state"
            payload = {
                "question_id": "Q-OPT-BENCH",
                "claim_id": f"CL-{sequence:06d}",
                "agent_id": "agent-bench-000",
                "resource_ids": ["gpu-bench-000"],
                "status": "ACTIVE",
            }
        else:
            domain = "RUNTIME"
            event_type = "execution_step"
            payload = {
                "question_id": "Q-OPT-BENCH",
                "process_id": "P-OPT-BENCH",
                "result_status": "unresolved" if sequence < event_count else "deadlock",
                "observations": [f"observation-{sequence}", "persistent-state"],
            }

        body = {
            "event_id": f"AE-BENCH-{sequence:08d}",
            "event_type": event_type,
            "domain": domain,
            "source_system": "persistence_optimization_benchmark_v1",
            "source_event_id": f"SRC-{sequence:08d}",
            "process_id": "P-OPT-BENCH",
            "question_id": "Q-OPT-BENCH",
            "actor_id": "agent-bench-000",
            "resource_ids": ["gpu-bench-000"] if domain == "CLAIM" else [],
            "timestamp": f"2026-09-21T00:00:{sequence % 60:02d}Z",
            "causal_parent_event_id": None if sequence == 1 else f"AE-BENCH-{sequence - 1:08d}",
            "verification_status": "verified",
            "payload": payload,
            "sequence": sequence,
        }
        event_hash = chain_hash(previous, body)
        record = {**body, "prev_hash": previous, "event_hash": event_hash}
        lines.append(canonical(record) + "\n")
        previous = event_hash
        state["last_sequence"] = sequence
        state["last_event_hash"] = event_hash
    return lines, previous, state


def benchmark_callable(callable_fn: Callable[[], None], samples: int) -> TimingStats:
    durations: list[float] = []
    for _ in range(samples):
        t0 = time.perf_counter()
        callable_fn()
        durations.append(time.perf_counter() - t0)
    return TimingStats.from_seconds(durations)


def _measure_components(event_lines: Sequence[str], samples: int) -> list[ComponentMeasurement]:
    components: list[ComponentMeasurement] = []
    example_record = json.loads(event_lines[0])
    example_payload = dict(example_record)
    example_payload.pop("event_hash", None)
    previous = str(example_record["prev_hash"])

    serialization_stats = benchmark_callable(lambda: canonical(example_payload), samples)
    components.append(ComponentMeasurement(
        component="json_canonicalization",
        unit="ms/event",
        stats=serialization_stats,
        notes="Canonical JSON only; no disk I/O.",
    ))

    hash_stats = benchmark_callable(lambda: chain_hash(previous, example_payload), samples)
    components.append(ComponentMeasurement(
        component="sha256_chain_hash",
        unit="ms/event",
        stats=hash_stats,
        notes="Event-chain hash only; excludes JSON and disk I/O.",
    ))

    with tempfile.TemporaryDirectory(prefix="ufcps-persist-components-") as temp_dir:
        base = Path(temp_dir)
        journal = base / "journal.jsonl"
        journal_durations = benchmark_callable(
            lambda: durable_append(journal, [event_lines[0]]),
            samples,
        )
        components.append(ComponentMeasurement(
            component="journal_append_flush_fsync",
            unit="ms/event",
            stats=journal_durations,
            notes="Representative single-line append with flush + fsync.",
        ))

        snapshot_payload = {
            "schema_version": "bench-v1",
            "process_id": "P-OPT-BENCH",
            "question_id": "Q-OPT-BENCH",
            "state": {"last_sequence": 1, "status": "unresolved"},
            "history": ["event-1"],
        }
        snapshot = base / "frontier.json"
        snapshot_durations = benchmark_callable(
            lambda: atomic_json_write(snapshot, snapshot_payload, durable=True),
            samples,
        )
        components.append(ComponentMeasurement(
            component="atomic_snapshot_replace",
            unit="ms/write",
            stats=snapshot_durations,
            notes="Temp-file write + flush + fsync + os.replace.",
        ))

        meta = base / "meta.json"
        meta_payload = {
            "schema_version": "bench-v1",
            "event_count": 1,
            "last_event_hash": example_record["event_hash"],
        }
        meta_durations = benchmark_callable(
            lambda: atomic_json_write(meta, meta_payload, durable=True),
            samples,
        )
        components.append(ComponentMeasurement(
            component="atomic_metadata_replace",
            unit="ms/write",
            stats=meta_durations,
            notes="Temp-file write + flush + fsync + os.replace.",
        ))

        no_durable = base / "no-durable-journal.jsonl"
        no_durable_durations = benchmark_callable(
            lambda: non_durable_append(no_durable, [event_lines[0]]),
            samples,
        )
        components.append(ComponentMeasurement(
            component="journal_append_no_fsync",
            unit="ms/event",
            stats=no_durable_durations,
            notes="Reference only; relaxed durability semantics.",
        ))

    return components


def write_pattern(
    root: Path,
    lines: Sequence[str],
    pattern: str,
    batch_size: int,
) -> tuple[float, str, int]:
    journal = root / "journal.jsonl"
    snapshot = root / "snapshot.json"
    meta = root / "meta.json"
    start = time.perf_counter()
    if pattern == "durable_per_event":
        for line in lines:
            durable_append(journal, [line])
            record = json.loads(line)
            atomic_json_write(snapshot, {"last_sequence": record["sequence"], "last_event_hash": record["event_hash"]})
            atomic_json_write(meta, {"event_count": record["sequence"], "last_event_hash": record["event_hash"]})
    elif pattern == "journal_only":
        for line in lines:
            durable_append(journal, [line])
    elif pattern == "batched_journal":
        for start_index in range(0, len(lines), batch_size):
            durable_append(journal, lines[start_index:start_index + batch_size])
    elif pattern == "batched_journal_snapshot":
        for start_index in range(0, len(lines), batch_size):
            batch = lines[start_index:start_index + batch_size]
            durable_append(journal, batch)
            record = json.loads(batch[-1])
            atomic_json_write(snapshot, {"last_sequence": record["sequence"], "last_event_hash": record["event_hash"]})
            atomic_json_write(meta, {"event_count": record["sequence"], "last_event_hash": record["event_hash"]})
    elif pattern == "non_durable_reference":
        for start_index in range(0, len(lines), batch_size):
            non_durable_append(journal, lines[start_index:start_index + batch_size])
    else:
        raise ValueError(f"unknown persistence pattern: {pattern}")
    elapsed = time.perf_counter() - start
    journal_bytes = journal.read_bytes() if journal.exists() else b""
    final_hash = json.loads(lines[-1])["event_hash"] if lines else GENESIS_HASH
    return elapsed, hashlib.sha256(journal_bytes).hexdigest(), len(journal_bytes)


def measure_pattern(
    lines: Sequence[str],
    pattern: str,
    batch_size: int,
    samples: int,
) -> PatternMeasurement:
    durations: list[float] = []
    digests: list[str] = []
    journal_sizes: list[int] = []
    for _ in range(samples):
        with tempfile.TemporaryDirectory(prefix="ufcps-persist-pattern-") as temp_dir:
            elapsed, digest, journal_size = write_pattern(
                Path(temp_dir), lines, pattern, batch_size
            )
            durations.append(elapsed)
            digests.append(digest)
            journal_sizes.append(journal_size)
    reference_digest: str
    with tempfile.TemporaryDirectory(prefix="ufcps-persist-ref-") as temp_dir:
        _, reference_digest, _ = write_pattern(Path(temp_dir), lines, "durable_per_event", 1)
    same = all(digest == reference_digest for digest in digests)
    return PatternMeasurement(
        pattern=pattern,
        event_count=len(lines),
        batch_size=batch_size,
        stats=TimingStats.from_seconds(durations),
        event_bytes=sum(len(line.encode("utf-8")) for line in lines),
        final_hash=json.loads(lines[-1])["event_hash"] if lines else GENESIS_HASH,
        journal_equivalent_to_reference=same,
        durable=pattern != "non_durable_reference",
        notes={
            "durable_per_event": "Current-style per-event journal + snapshot + metadata persistence.",
            "journal_only": "Durable event journal without frontier/meta checkpoint writes.",
            "batched_journal": "Durable journal with one fsync per batch; no snapshot/meta checkpoint.",
            "batched_journal_snapshot": "Durable journal + snapshot/meta once per batch.",
            "non_durable_reference": "No fsync and no checkpoint; lower-bound reference only.",
        }[pattern],
    )


def estimate_contributions(components: Sequence[ComponentMeasurement]) -> dict[str, Any]:
    per_event_items = {
        item.component: item.stats.mean_ms
        for item in components
        if item.component in {
            "json_canonicalization",
            "sha256_chain_hash",
            "journal_append_flush_fsync",
            "atomic_snapshot_replace",
            "atomic_metadata_replace",
        }
    }
    baseline = sum(per_event_items.values())
    shares = {
        name: {
            "mean_ms": value,
            "share_of_component_sum": value / baseline if baseline else 0.0,
        }
        for name, value in per_event_items.items()
    }
    return {
        "method": "component_mean_divided_by_sum_of_measured_component_means",
        "warning": "This is a local diagnostic decomposition, not a causal proof of total runtime share.",
        "component_sum_ms_per_event": baseline,
        "shares": shares,
    }


def run_benchmark(
    *,
    event_count: int = 128,
    batch_sizes: Sequence[int] = (1, 4, 16, 64),
    component_samples: int = 20,
    pattern_samples: int = 5,
) -> OptimizationResult:
    if event_count < 1:
        raise ValueError("event_count must be >= 1")
    normalized_batches = sorted({max(1, min(int(size), event_count)) for size in batch_sizes})
    lines, final_hash, logical_state = build_records(event_count)

    components = _measure_components(lines, component_samples)

    patterns: list[PatternMeasurement] = []
    patterns.append(measure_pattern(lines, "durable_per_event", 1, pattern_samples))
    patterns.append(measure_pattern(lines, "journal_only", 1, pattern_samples))
    for batch_size in normalized_batches:
        patterns.append(measure_pattern(lines, "batched_journal", batch_size, pattern_samples))
        patterns.append(measure_pattern(lines, "batched_journal_snapshot", batch_size, pattern_samples))
        if batch_size in {1, max(normalized_batches)}:
            patterns.append(measure_pattern(lines, "non_durable_reference", batch_size, pattern_samples))

    with tempfile.TemporaryDirectory(prefix="ufcps-persist-equivalence-") as temp_dir:
        root = Path(temp_dir)
        ref_root = root / "reference"
        batch_root = root / "batch"
        write_pattern(ref_root, lines, "durable_per_event", 1)
        write_pattern(batch_root, lines, "batched_journal_snapshot", normalized_batches[-1])
        ref_bytes = (ref_root / "journal.jsonl").read_bytes()
        batch_bytes = (batch_root / "journal.jsonl").read_bytes()
        same_journal = ref_bytes == batch_bytes
        ref_records = [json.loads(line) for line in ref_bytes.decode("utf-8").splitlines()]
        batch_records = [json.loads(line) for line in batch_bytes.decode("utf-8").splitlines()]
        same_count = len(ref_records) == len(batch_records) == event_count
        same_hash = (ref_records[-1]["event_hash"] == batch_records[-1]["event_hash"] == final_hash)
        same_state = {
            "last_sequence": ref_records[-1]["sequence"],
            "last_event_hash": ref_records[-1]["event_hash"],
        } == {
            "last_sequence": batch_records[-1]["sequence"],
            "last_event_hash": batch_records[-1]["event_hash"],
        } == {
            "last_sequence": logical_state["last_sequence"],
            "last_event_hash": logical_state["last_event_hash"],
        }

    equivalence = EquivalenceResult(
        same_journal_bytes=same_journal,
        same_event_count=same_count,
        same_final_hash=same_hash,
        same_logical_state=same_state,
        notes=(
            "Durable per-event and batched-journal+snapshot use the same deterministic event records; "
            "batching changes persistence granularity, not event content."
        ),
    )

    contributions = estimate_contributions(components)
    baseline = next(item for item in patterns if item.pattern == "durable_per_event")
    journal_only = next(item for item in patterns if item.pattern == "journal_only")
    batched = [item for item in patterns if item.pattern == "batched_journal_snapshot"]

    summary = {
        "interpretation": "Observed characteristics of this local prototype; no hardware-normalized forecast and no universal scaling law.",
        "baseline_mean_ms": baseline.stats.mean_ms,
        "journal_only_mean_ms": journal_only.stats.mean_ms,
        "journal_only_delta_ms": journal_only.stats.mean_ms - baseline.stats.mean_ms,
        "batch_results": [
            {
                "batch_size": item.batch_size,
                "mean_ms": item.stats.mean_ms,
                "delta_vs_baseline_ms": item.stats.mean_ms - baseline.stats.mean_ms,
                "factor_vs_baseline": item.stats.mean_ms / baseline.stats.mean_ms if baseline.stats.mean_ms else 0.0,
                "journal_equivalent": item.journal_equivalent_to_reference,
            }
            for item in batched
        ],
        "non_durable_reference_note": "Non-durable reference is intentionally not treated as a production-equivalent optimization.",
        "largest_component_by_measured_mean": max(
            contributions["shares"].items(), key=lambda pair: pair[1]["mean_ms"]
        )[0],
        "all_pattern_journal_equivalent": all(item.journal_equivalent_to_reference for item in patterns if item.pattern != "non_durable_reference"),
    }

    return OptimizationResult(
        benchmark_version=BENCHMARK_VERSION,
        environment={
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "os_name": os.name,
            "fsync_available": fsync_supported(),
            "event_count": event_count,
            "batch_sizes": normalized_batches,
            "component_samples": component_samples,
            "pattern_samples": pattern_samples,
        },
        components=components,
        patterns=patterns,
        equivalence=equivalence,
        contribution_estimate=contributions,
        summary=summary,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--events", type=int, default=128)
    parser.add_argument("--batch-sizes", nargs="+", type=int, default=[1, 4, 16, 64])
    parser.add_argument("--component-samples", type=int, default=20)
    parser.add_argument("--pattern-samples", type=int, default=5)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_benchmark(
        event_count=args.events,
        batch_sizes=args.batch_sizes,
        component_samples=args.component_samples,
        pattern_samples=args.pattern_samples,
    )
    data = result.to_dict()
    if args.as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    print("UFCPS Level 2 Persistence Optimization Benchmark v1")
    print(f"Events: {args.events}")
    print(f"Equivalence: journal_bytes={data['equivalence']['same_journal_bytes']} | "
          f"count={data['equivalence']['same_event_count']} | "
          f"final_hash={data['equivalence']['same_final_hash']} | "
          f"state={data['equivalence']['same_logical_state']}")
    print("Components:")
    for item in data["components"]:
        stats = item["stats"]
        print(f"  {item['component']}: mean={stats['mean_ms']:.4f} ms/{item['unit'].split('/')[-1]}")
    print("Patterns:")
    for item in data["patterns"]:
        stats = item["stats"]
        print(f"  {item['pattern']}: batch={item['batch_size']} mean={stats['mean_ms']:.3f} ms | "
              f"factor_vs_reference={stats['mean_ms'] / data['summary']['baseline_mean_ms']:.2f} | "
              f"equivalent={item['journal_equivalent_to_reference']}")
    print("Measured component with largest standalone mean:", data["summary"]["largest_component_by_measured_mean"])
    print("All non-reference durable patterns journal-equivalent:", data["summary"]["all_pattern_journal_equivalent"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
