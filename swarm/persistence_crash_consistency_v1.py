#!/usr/bin/env python3
"""UFCPS Level 2 — Persistence Crash Consistency Benchmark v1.

Fault-injection validation for the checkpointed persistence path.

The benchmark uses real subprocess termination (os._exit) to emulate abrupt
process loss. It deliberately distinguishes three outcomes:

* durable event already flushed -> event must survive restart;
* event not durably flushed yet -> the event may be absent, but must not appear
  as a phantom frontier/claim state;
* checkpoint write interrupted -> the previous complete checkpoint (if any)
  remains authoritative, and journal tail replay must recover the newer events.

No conclusion here treats hash integrity as proof that an event was true; the
checks are limited to storage integrity, recoverability and UFCPS continuity
semantics.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
PYTHON = sys.executable


def _canon(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _run_child(mode: str, scenario: str, base: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update({
        "UFCPS_CRASH_CHILD": "1",
        "UFCPS_CRASH_MODE": mode,
        "UFCPS_CRASH_SCENARIO": scenario,
        "UFCPS_CRASH_BASE": str(base),
    })
    return subprocess.run(
        [PYTHON, str(Path(__file__).resolve())],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _patch_kill_after_append_lines() -> Callable[[], None]:
    from checkpointed_event_store_v1 import append_lines as real_append_lines
    import checkpointed_event_store_v1 as mod

    def injected(path, lines, *, durable=True):
        real_append_lines(path, lines, durable=durable)
        os._exit(73)

    mod.append_lines = injected
    return lambda: setattr(mod, "append_lines", real_append_lines)


def _patch_kill_before_checkpoint_replace() -> Callable[[], None]:
    import checkpointed_event_store_v1 as mod
    real = mod.atomic_json_write

    def injected(path, payload, *, durable=True):
        path.parent.mkdir(parents=True, exist_ok=True)
        import tempfile as _tempfile
        fd, temp_name = _tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        temp_path = Path(temp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            if durable:
                os.fsync(handle.fileno())
        # Crash before atomic replace. Any old checkpoint must remain intact.
        os._exit(74)

    mod.atomic_json_write = injected
    return lambda: setattr(mod, "atomic_json_write", real)


def _patch_kill_after_checkpoint_replace() -> Callable[[], None]:
    import checkpointed_event_store_v1 as mod
    real = mod.atomic_json_write

    def injected(path, payload, *, durable=True):
        real(path, payload, durable=durable)
        os._exit(75)

    mod.atomic_json_write = injected
    return lambda: setattr(mod, "atomic_json_write", real)


def _child_store(base: Path, scenario: str) -> int:
    from checkpointed_event_store_v1 import CheckpointedEventStore

    store = CheckpointedEventStore(
        base,
        journal_batch_size=1 if scenario == "after_journal_fsync" else 4,
        checkpoint_interval=16,
        durable=True,
    )

    if scenario == "before_flush":
        store.append(event_id="E-1", payload={"step": 1})
        os._exit(71)

    if scenario == "after_journal_fsync":
        restore = _patch_kill_after_append_lines()
        try:
            store.append(event_id="E-1", payload={"step": 1})
        finally:
            restore()

    if scenario == "before_checkpoint_replace":
        store.append_many(
            [{"event_id": f"E-{i}", "step": i} for i in range(1, 5)],
        )
        restore = _patch_kill_before_checkpoint_replace()
        try:
            store.checkpoint(state={"state": "checkpoint-1"})
        finally:
            restore()

    if scenario == "after_checkpoint_replace":
        store.append_many(
            [{"event_id": f"E-{i}", "step": i} for i in range(1, 5)],
        )
        restore = _patch_kill_after_checkpoint_replace()
        try:
            store.checkpoint(state={"state": "checkpoint-1"})
        finally:
            restore()

    if scenario == "tail_after_checkpoint":
        store.append_many(
            [{"event_id": f"E-{i}", "step": i} for i in range(1, 5)],
            checkpoint_state={"state": "checkpoint-1"},
            force_checkpoint=True,
        )
        # Event is durable in the journal but intentionally outside checkpoint.
        store.append_many(
            [{"event_id": "E-5", "step": 5}, {"event_id": "E-6", "step": 6}],
        )
        os._exit(76)

    if scenario == "clean":
        store.append_many(
            [{"event_id": f"E-{i}", "step": i} for i in range(1, 5)],
            checkpoint_state={"state": "checkpoint-1"},
            force_checkpoint=True,
        )
        store.append(event_id="E-5", payload={"step": 5})
        store.flush()
        return 0

    return 0


def _build_uql(base: Path, optimized: bool = True):
    from uql_store_v1 import UQLStore
    return UQLStore(
        base,
        optimized_persistence=optimized,
        journal_batch_size=4,
        checkpoint_interval=4,
        durable=True,
    )


def _child_uql(base: Path, scenario: str) -> int:
    store = _build_uql(base)
    if scenario == "uql_tail":
        store.create_question(
            question_id="Q-1",
            process_id="P-1",
            formulation="Question 1",
        )
        store.update_frontier(
            question_id="Q-1",
            event_type="frontier_update",
            patch={"status": "blocked"},
        )
        store.append_history(
            question_id="Q-1",
            event_type="deadlock_recorded",
            payload={"deadlock_id": "DL-1"},
        )
        # Fourth event creates a checkpoint.
        store.update_frontier(
            question_id="Q-1",
            event_type="frontier_update",
            patch={"candidate_carriers": ["agent-B"]},
        )
        store.update_frontier(
            question_id="Q-1",
            event_type="frontier_update",
            patch={"next_required_operation": "resource_discovery"},
        )
        assert store._checkpoint_store is not None
        store._checkpoint_store.flush()
        os._exit(77)

    if scenario == "uql_checkpoint_crash":
        store.create_question(
            question_id="Q-1",
            process_id="P-1",
            formulation="Question 1",
        )
        store.update_frontier(
            question_id="Q-1",
            event_type="frontier_update",
            patch={"status": "blocked"},
        )
        store.append_history(
            question_id="Q-1",
            event_type="deadlock_recorded",
            payload={"deadlock_id": "DL-1"},
        )
        # Interrupt the atomic checkpoint file operation.
        import checkpointed_event_store_v1 as cp_mod
        real = cp_mod.atomic_json_write

        def injected(path, payload, *, durable=True):
            path.parent.mkdir(parents=True, exist_ok=True)
            import tempfile as _tempfile
            fd, temp_name = _tempfile.mkstemp(prefix=f".{Path(path).name}.", dir=str(path.parent))
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os._exit(78)

        cp_mod.atomic_json_write = injected
        # Explicitly rebuild a checkpoint; the journal already contains the
        # three durable events, while checkpoint replacement is interrupted.
        store.persist_frontier_rebuild()
        cp_mod.atomic_json_write = real

    return 0


def _child_claim(base: Path, scenario: str) -> int:
    from task_claim_store_v1 import TaskClaimStore, _build_demo_engine

    store = TaskClaimStore(
        base,
        store_id="CRASH-CLAIM",
        persistence_mode="checkpointed",
        journal_batch_size=4,
        checkpoint_interval=64,
        durable=True,
    )
    engine = _build_demo_engine()
    claim = engine.create_claim(
        claim_id="CL-CRASH-001",
        question_id="Q-STORE-001",
        agent_id="agent-A",
        prospect_id="TP-Q-STORE-001-agent-A",
        expires_at="2026-09-21T21:00:00Z",
        method_intent="crash consistency",
        provenance={"source": "crash-benchmark"},
        requested_resources=[{"resource_type": "gpu", "quantity": 25, "unit": "GPU-hours"}],
    )
    engine.admit_claim(claim.claim_id)
    engine.reserve_resources(claim.claim_id)
    engine.activate(claim.claim_id)

    if scenario == "claim_active_crash":
        store.persist_engine(engine, event_cursor=0)
        os._exit(79)

    if scenario == "claim_before_persist":
        os._exit(80)

    return 0


def _child_entry() -> int:
    mode = os.environ.get("UFCPS_CRASH_MODE", "store")
    scenario = os.environ.get("UFCPS_CRASH_SCENARIO", "")
    base = Path(os.environ["UFCPS_CRASH_BASE"])
    if mode == "store":
        return _child_store(base, scenario)
    if mode == "uql":
        return _child_uql(base, scenario)
    if mode == "claim":
        return _child_claim(base, scenario)
    raise SystemExit(2)


def _store_result(base: Path, scenario: str, exit_code: int) -> dict[str, Any]:
    from checkpointed_event_store_v1 import CheckpointedEventStore
    store = CheckpointedEventStore(base, journal_batch_size=4, checkpoint_interval=16, durable=True)
    events = store.events()
    checkpoint = store.checkpoint_snapshot()
    info = store.verify_integrity()
    tail = store.recover_events_after_checkpoint()
    if scenario == "before_flush":
        expected = len(events) == 0 and checkpoint is None
        interpretation = "unflushed event absent after crash; no phantom state"
    elif scenario == "after_journal_fsync":
        expected = len(events) == 1 and checkpoint is None and len(tail) == 1 and info.integrity_ok
        interpretation = "durable journal event survives; replayable tail remains"
    elif scenario == "before_checkpoint_replace":
        expected = len(events) == 4 and checkpoint is None and info.integrity_ok
        interpretation = "interrupted atomic checkpoint leaves journal intact"
    elif scenario == "after_checkpoint_replace":
        expected = len(events) == 4 and checkpoint is not None and checkpoint.event_count == 4 and info.integrity_ok
        interpretation = "completed atomic replace leaves a complete checkpoint"
    elif scenario == "tail_after_checkpoint":
        expected = len(events) == 6 and checkpoint is not None and checkpoint.event_count == 4 and len(tail) == 2 and info.integrity_ok
        interpretation = "checkpoint + durable journal tail survive abrupt process loss"
    elif scenario == "clean":
        expected = len(events) == 5 and checkpoint is not None and info.integrity_ok
        interpretation = "clean reference case"
    else:
        raise AssertionError(scenario)
    return {
        "scenario": scenario,
        "child_exit_code": exit_code,
        "passed": bool(expected),
        "event_count": len(events),
        "checkpoint_event_count": checkpoint.event_count if checkpoint else 0,
        "tail_event_count": len(tail),
        "integrity_ok": info.integrity_ok,
        "interpretation": interpretation,
    }


def _uql_result(base: Path, scenario: str, exit_code: int) -> dict[str, Any]:
    from uql_store_v1 import UQLStore
    restarted = _build_uql(base)
    integrity = restarted.verify_integrity(replay=True)
    frontier = restarted.get_frontier("Q-1").to_dict() if "Q-1" in restarted.frontier else None
    store = restarted
    cp = store._checkpoint_store.checkpoint_snapshot() if store._checkpoint_store else None
    events = store._read_events()
    tail = store._checkpoint_store.recover_events_after_checkpoint() if store._checkpoint_store else []
    if scenario == "uql_tail":
        passed = (
            len(events) == 5
            and cp is not None
            and cp.event_count == 4
            and len(tail) == 1
            and integrity["valid"]
            and frontier is not None
            and frontier["next_required_operation"] == "resource_discovery"
        )
        interpretation = "UQL checkpoint + tail replay preserves frontier across crash"
    elif scenario == "uql_checkpoint_crash":
        passed = integrity["valid"] and frontier is not None
        interpretation = "interrupted UQL checkpoint does not invalidate durable event history"
    else:
        raise AssertionError(scenario)
    return {
        "scenario": scenario,
        "child_exit_code": exit_code,
        "passed": bool(passed),
        "event_count": len(events),
        "checkpoint_event_count": cp.event_count if cp else 0,
        "tail_event_count": len(tail),
        "frontier": frontier,
        "integrity": integrity,
        "interpretation": interpretation,
    }


def _claim_result(base: Path, scenario: str, exit_code: int) -> dict[str, Any]:
    from task_claim_store_v1 import TaskClaimStore, _build_demo_engine
    store = TaskClaimStore(
        base,
        store_id="CRASH-CLAIM",
        persistence_mode="checkpointed",
        journal_batch_size=4,
        checkpoint_interval=64,
        durable=True,
    )
    engine = _build_demo_engine()
    restored = store.restore_into_engine(engine, stale_active_policy="RELEASE_ACTIVE_ON_RESTART")
    integrity = store.verify_integrity()
    claim_status = engine.claims.get("CL-CRASH-001").status if "CL-CRASH-001" in engine.claims else None
    resource_available = engine.resources["gpu-store-001"]["availability"]["available_capacity"]
    if scenario == "claim_active_crash":
        passed = (
            integrity["valid"]
            and claim_status == "RELEASED"
            and float(resource_available) == 100.0
            and len(store.read_events()) == 5
        )
        interpretation = "active claim is invalidated on restart and resource reservation is restored"
    elif scenario == "claim_before_persist":
        passed = "CL-CRASH-001" not in engine.claims
        interpretation = "unpersisted claim leaves no phantom claim after crash"
    else:
        raise AssertionError(scenario)
    return {
        "scenario": scenario,
        "child_exit_code": exit_code,
        "passed": bool(passed),
        "event_count": len(store.read_events()),
        "claim_status": claim_status,
        "resource_available": resource_available,
        "integrity": integrity,
        "interpretation": interpretation,
    }


def _run_case(mode: str, scenario: str, analyzer: Callable[[Path, str, int], dict[str, Any]]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ufcps-crash-") as directory:
        base = Path(directory) / scenario
        proc = _run_child(mode, scenario, base)
        result = analyzer(base, scenario, proc.returncode)
        result["stderr_tail"] = proc.stderr[-400:] if proc.stderr else ""
        result["stdout_tail"] = proc.stdout[-400:] if proc.stdout else ""
        return result


def _benchmark() -> dict[str, Any]:
    cases = [
        ("store", "before_flush", _store_result),
        ("store", "after_journal_fsync", _store_result),
        ("store", "before_checkpoint_replace", _store_result),
        ("store", "after_checkpoint_replace", _store_result),
        ("store", "tail_after_checkpoint", _store_result),
        ("store", "clean", _store_result),
        ("uql", "uql_tail", _uql_result),
        ("uql", "uql_checkpoint_crash", _uql_result),
        ("claim", "claim_active_crash", _claim_result),
        ("claim", "claim_before_persist", _claim_result),
    ]
    results = [_run_case(mode, scenario, analyzer) for mode, scenario, analyzer in cases]
    return {
        "benchmark": "persistence_crash_consistency_v1",
        "status": "PASS" if all(item["passed"] for item in results) else "FAIL",
        "total_cases": len(results),
        "passed": sum(1 for item in results if item["passed"]),
        "failed": sum(1 for item in results if not item["passed"]),
        "cases": results,
        "scope": [
            "abrupt subprocess termination",
            "durable journal visibility",
            "atomic checkpoint interruption",
            "checkpoint + tail replay",
            "UQL frontier reconstruction",
            "Claim Store stale-active release",
            "absence of phantom unpersisted state",
        ],
        "not_proven": [
            "truthfulness of events",
            "Byzantine consensus",
            "filesystem behavior on hardware power loss beyond the OS/fsync contract",
        ],
    }


def _main() -> int:
    if os.environ.get("UFCPS_CRASH_CHILD") == "1":
        return _child_entry()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--keep", action="store_true", help="ignored; compatibility flag")
    args = parser.parse_args()
    result = _benchmark()
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("UFCPS Persistence Crash Consistency v1")
        print(f"Status: {result['status']}")
        print(f"Cases: {result['passed']}/{result['total_cases']} passed")
        for case in result["cases"]:
            print(f"- {case['scenario']}: {'PASS' if case['passed'] else 'FAIL'}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(_main())
