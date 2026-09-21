
"""UFCPS Level 2 — Runtime Recovery / Carrier Destruction Test v1.

This artifact tests whether the process represented by ``SwarmRuntime`` survives
abrupt destruction of its current computational carrier.

The test uses a child process for the destructive phase and a fresh runtime
instance for recovery.  Persistence is configured in the experimental
checkpointed mode for both UQL and Task Claim Store.

Scenario boundary model
-----------------------
    Question -> Discovery -> Decision -> Claim -> Reservation -> Execution
              -> Result -> Continuation -> UQL

At selected boundaries the child terminates abruptly with ``os._exit``.  The
parent then creates a new runtime instance from the same persistent material.

The artifact distinguishes three classes of result:

* PASS   — the documented recovery invariant is observed;
* FAIL   — the current implementation violates a tested recovery invariant;
* N/A    — the existing runtime does not expose enough durable semantics to
           prove the requested property (for example, real payment settlement).

This is an architectural test, not a distributed Byzantine-consensus proof.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable


SWARM_DIR = Path(__file__).resolve().parent
if str(SWARM_DIR) not in sys.path:
    sys.path.insert(0, str(SWARM_DIR))

import swarm_runtime_v1 as runtime_module
from swarm_runtime_v1 import SwarmRuntime, _text
from task_claim_store_v1 import TaskClaimStore
from uql_store_v1 import UQLStore


CRASH_EXIT = 73

AGENTS = [
    {
        "agent_id": "recovery-agent-001",
        "status": "available",
        "capabilities": [{"name": "simulation", "category": "research"}],
        "task_policy": {"accepts_tasks": True},
    },
    {
        "agent_id": "recovery-agent-002",
        "status": "available",
        "capabilities": [{"name": "analysis", "category": "research"}],
        "task_policy": {"accepts_tasks": True},
    },
]

RESOURCES = [
    {
        "resource_id": "recovery-gpu-001",
        "provider_id": "recovery-provider-001",
        "resource_type": "gpu",
        "status": "available",
        "capabilities": [{"name": "gpu"}],
        "verification": {"verification_status": "verified"},
        "availability": {"available_capacity": 1000, "capacity_unit": "GPU-hours"},
    },
]

QUESTION = {
    "question_id": "Q-RUNTIME-RECOVERY-001",
    "task_prospect_id": "TP-RUNTIME-RECOVERY-001",
    "title": "runtime recovery question",
    "formulation": "Can a fresh carrier continue the process after abrupt runtime destruction?",
    "required_capabilities": ["simulation"],
    "requirements": {
        "resources": [{"resource_type": "gpu", "quantity": 25, "unit": "GPU-hours"}]
    },
    "priority": 2,
    "requested_reward_rc": 10,
    "agent_decisions": {"recovery-agent-001": "accept"},
}


# ---------------------------------------------------------------------------
# Runtime construction helpers
# ---------------------------------------------------------------------------


def build_runtime(base: Path, *, recover: bool) -> SwarmRuntime:
    """Build a SwarmRuntime with explicit experimental checkpointed stores."""
    runtime = SwarmRuntime(
        runtime_id="RUNTIME-RECOVERY",
        agents=deepcopy(AGENTS),
        resources=deepcopy(RESOURCES),
        max_batch_size=1,
        persistence_path=None,
        claim_persistence_path=None,
        recover_existing=False,
    )
    runtime.uql_store = UQLStore(
        base,
        optimized_persistence=True,
        journal_batch_size=1,
        checkpoint_interval=8,
        durable=True,
    )
    runtime.persistence_path = str(base)

    claim_base = Path(f"{base}.claims")
    runtime.claim_store = TaskClaimStore(
        claim_base,
        store_id="RUNTIME-RECOVERY-claim-store",
        persistence_mode="checkpointed",
        journal_batch_size=1,
        checkpoint_interval=8,
        durable=True,
    )
    runtime.claim_persistence_path = str(claim_base)

    if recover:
        runtime._restore_from_uql()
    return runtime


def prepare_seed(base: Path) -> SwarmRuntime:
    runtime = build_runtime(base, recover=False)
    runtime.seed_questions([QUESTION])
    runtime.discover()
    runtime.record_agent_decision(
        question_id=QUESTION["question_id"],
        agent_id="recovery-agent-001",
        decision="accept",
    )
    return runtime


# ---------------------------------------------------------------------------
# Destructive worker
# ---------------------------------------------------------------------------


def _crash_worker(stage: str, base: Path) -> None:
    runtime = prepare_seed(base)

    if stage == "before_claim":
        os._exit(CRASH_EXIT)

    if stage == "after_claim":
        original = runtime._prepare_claim

        def wrapped(entry: Any, prospects: Any) -> Any:
            result = original(entry, prospects)
            os._exit(CRASH_EXIT)

        runtime._prepare_claim = wrapped  # type: ignore[method-assign]
        runtime.tick()
        return

    if stage == "during_execution":
        def crash_coordinator(*args: Any, **kwargs: Any) -> Any:
            os._exit(CRASH_EXIT)

        runtime_module.coordinate_experiments = crash_coordinator  # type: ignore[assignment]
        runtime.tick()
        return

    if stage == "after_result_before_continuation":
        original = runtime._make_continuation_question

        def wrapped(entry: Any, outcome: Any) -> Any:
            # The runtime has already persisted the parent outcome and
            # ``continuation_ready`` before entering this function.
            _ = original  # keep the original callable intentionally unused.
            os._exit(CRASH_EXIT)

        runtime._make_continuation_question = wrapped  # type: ignore[method-assign]
        runtime.tick()
        return

    if stage == "after_continuation":
        original = runtime._persist_entry

        def wrapped(entry: Any, *, event_type: str = "runtime_state") -> None:
            original(entry, event_type=event_type)
            if event_type == "continuation_discovery":
                os._exit(CRASH_EXIT)

        runtime._persist_entry = wrapped  # type: ignore[method-assign]
        runtime.tick()
        return

    raise ValueError(f"unknown stage: {stage}")


def run_worker(stage: str, base: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--worker", stage, str(base)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        check=False,
    )
    return result


# ---------------------------------------------------------------------------
# Recovery observations
# ---------------------------------------------------------------------------


def recover(base: Path) -> SwarmRuntime:
    runtime = build_runtime(base, recover=True)
    runtime.discover()
    # Force claim-store restoration so stale leases are released.
    runtime._ensure_claim_engine(list(runtime.prospects.values()))
    return runtime


def claim_counts(runtime: SwarmRuntime) -> dict[str, int]:
    engine = runtime.claim_engine
    if engine is None:
        return {"total": 0, "active": 0, "released": 0, "completed": 0}
    return {
        "total": len(engine.claims),
        "active": sum(1 for c in engine.claims.values() if c.status == "ACTIVE"),
        "released": sum(1 for c in engine.claims.values() if c.status == "RELEASED"),
        "completed": sum(1 for c in engine.claims.values() if c.status == "COMPLETED"),
    }


def resource_capacity(runtime: SwarmRuntime) -> float:
    for resource in runtime.resources:
        if resource.get("resource_id") == "recovery-gpu-001":
            return float(resource.get("availability", {}).get("available_capacity", 0))
    return 0.0


def find_seed(runtime: SwarmRuntime) -> Any:
    for entry in runtime.ledger.values():
        if _text(entry.question.get("question_id")) == QUESTION["question_id"]:
            return entry
    return None


def fresh_accept_and_continue(runtime: SwarmRuntime) -> dict[str, Any]:
    entry = find_seed(runtime)
    if entry is None:
        return {"accepted": False, "reason": "seed question missing"}
    try:
        runtime.record_agent_decision(
            question_id=QUESTION["question_id"],
            agent_id="recovery-agent-001",
            decision="accept",
        )
        tick = runtime.tick()
    except Exception as exc:  # pragma: no cover - defensive diagnostic
        return {"accepted": False, "reason": f"resume exception: {exc}"}
    snap = runtime.snapshot()
    return {
        "accepted": True,
        "tick": asdict(tick),
        "snapshot": asdict(snap),
        "continuations": snap.continuations_created,
        "global_process_terminated": snap.global_process_terminated,
    }


# ---------------------------------------------------------------------------
# Scenario assertions
# ---------------------------------------------------------------------------


def scenario_before_claim(base: Path) -> dict[str, Any]:
    proc = run_worker("before_claim", base)
    runtime = recover(base)
    entry = find_seed(runtime)
    claims = claim_counts(runtime)
    return {
        "stage": "before_claim",
        "worker_exit": proc.returncode,
        "worker_crashed_as_expected": proc.returncode == CRASH_EXIT,
        "seed_survived": entry is not None,
        "seed_is_discoverable": bool(entry and entry.status == "discoverable"),
        "no_claim_was_created": claims["total"] == 0,
        "uql_integrity": runtime.persistence_integrity(),
        "status": "PASS"
        if proc.returncode == CRASH_EXIT
        and entry is not None
        and entry.status == "discoverable"
        and claims["total"] == 0
        else "FAIL",
    }


def scenario_after_claim(base: Path) -> dict[str, Any]:
    proc = run_worker("after_claim", base)
    runtime = recover(base)
    entry = find_seed(runtime)
    claims = claim_counts(runtime)
    resumed = fresh_accept_and_continue(runtime)
    return {
        "stage": "after_claim",
        "worker_exit": proc.returncode,
        "worker_crashed_as_expected": proc.returncode == CRASH_EXIT,
        "seed_survived": entry is not None,
        "stale_active_released": claims["active"] == 0 and claims["released"] >= 1,
        "resource_capacity_restored": resource_capacity(runtime) == 1000.0,
        "resume_completed_one_tick": bool(resumed.get("accepted")),
        "process_not_globally_terminated": resumed.get("global_process_terminated") is False,
        "continuation_created_after_resume": resumed.get("continuations") == 1,
        "uql_integrity": runtime.persistence_integrity(),
        "claim_store_integrity": runtime.claim_store.verify_integrity() if runtime.claim_store else None,
        "status": "PASS"
        if proc.returncode == CRASH_EXIT
        and entry is not None
        and claims["active"] == 0
        and claims["released"] >= 1
        and resource_capacity(runtime) == 1000.0
        and resumed.get("accepted")
        and resumed.get("global_process_terminated") is False
        and resumed.get("continuations") == 1
        else "FAIL",
    }


def scenario_during_execution(base: Path) -> dict[str, Any]:
    proc = run_worker("during_execution", base)
    runtime = recover(base)
    entry = find_seed(runtime)
    claims = claim_counts(runtime)
    resumed = fresh_accept_and_continue(runtime)
    return {
        "stage": "during_execution",
        "worker_exit": proc.returncode,
        "worker_crashed_as_expected": proc.returncode == CRASH_EXIT,
        "seed_survived": entry is not None,
        "stale_active_released": claims["active"] == 0 and claims["released"] >= 1,
        "resource_capacity_restored": resource_capacity(runtime) == 1000.0,
        "fresh_carrier_resumed": bool(resumed.get("accepted")),
        "process_not_globally_terminated": resumed.get("global_process_terminated") is False,
        "continuation_created_after_resume": resumed.get("continuations") == 1,
        "status": "PASS"
        if proc.returncode == CRASH_EXIT
        and entry is not None
        and claims["active"] == 0
        and claims["released"] >= 1
        and resource_capacity(runtime) == 1000.0
        and resumed.get("accepted")
        and resumed.get("global_process_terminated") is False
        and resumed.get("continuations") == 1
        else "FAIL",
    }


def scenario_after_result_before_continuation(base: Path) -> dict[str, Any]:
    proc = run_worker("after_result_before_continuation", base)
    runtime = recover(base)
    seed = find_seed(runtime)
    child_count = sum(1 for e in runtime.ledger.values() if e.source == "continuation")

    # Strong invariant: once the parent result was durably recorded as
    # continuation_ready, restart should not leave the process in a state where
    # the only recoverable action is to rerun the parent. The current runtime
    # does not yet synthesize a missing child continuation on restart.
    unsafe_rerun_shape = bool(seed and seed.status == "continuation_ready" and child_count == 0)
    return {
        "stage": "after_result_before_continuation",
        "worker_exit": proc.returncode,
        "worker_crashed_as_expected": proc.returncode == CRASH_EXIT,
        "parent_result_survived": bool(seed and seed.metadata.get("latest_outcome")),
        "parent_marked_continuation_ready": bool(seed and seed.status == "continuation_ready"),
        "continuation_child_present": child_count > 0,
        "duplicate_parent_rerun_risk": unsafe_rerun_shape,
        "status": "FAIL" if unsafe_rerun_shape else "PASS",
        "diagnostic": (
            "Parent continuation_ready is durable, but child continuation was not yet materialized. "
            "On restart the current SwarmRuntime may rediscover and rerun the parent instead of "
            "materializing P(n+1)."
            if unsafe_rerun_shape
            else "No missing-continuation gap observed."
        ),
    }


def scenario_after_continuation(base: Path) -> dict[str, Any]:
    proc = run_worker("after_continuation", base)
    runtime = recover(base)
    child_count = sum(1 for e in runtime.ledger.values() if e.source == "continuation")
    child_discoverable = sum(1 for e in runtime.ledger.values() if e.source == "continuation" and e.status == "discoverable")
    seed = find_seed(runtime)
    return {
        "stage": "after_continuation",
        "worker_exit": proc.returncode,
        "worker_crashed_as_expected": proc.returncode == CRASH_EXIT,
        "seed_survived": seed is not None,
        "continuation_child_survived": child_count == 1,
        "continuation_is_discoverable": child_discoverable == 1,
        "uql_integrity": runtime.persistence_integrity(),
        "status": "PASS"
        if proc.returncode == CRASH_EXIT
        and seed is not None
        and child_count == 1
        and child_discoverable == 1
        else "FAIL",
    }


def run_scenario(name: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"ufcps-runtime-recovery-{name}-") as temp:
        return {
            **globals()[f"scenario_{name}"](Path(temp) / "uql"),
        }


def run_suite() -> dict[str, Any]:
    scenario_names = [
        "before_claim",
        "after_claim",
        "during_execution",
        "after_result_before_continuation",
        "after_continuation",
    ]
    results = [run_scenario(name) for name in scenario_names]

    # Payment settlement is intentionally not scored: runtime v1 only produces
    # economic outcome/projection data; durable idempotent payment settlement is
    # implemented outside this runtime recovery artifact.
    payment_check = {
        "status": "N/A",
        "reason": "SwarmRuntime v1 does not execute a durable payment ledger/settlement step.",
    }

    passed = sum(r["status"] == "PASS" for r in results)
    failed = sum(r["status"] == "FAIL" for r in results)
    return {
        "schema_version": "1.0",
        "suite": "level2_runtime_recovery_v1",
        "scenarios_requested": len(results),
        "passed": passed,
        "failed": failed,
        "payment_idempotency": payment_check,
        "global_process_termination": False,
        "results": results,
        "status": "PASS" if failed == 0 else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=[
        "before_claim",
        "after_claim",
        "during_execution",
        "after_result_before_continuation",
        "after_continuation",
    ])
    parser.add_argument("stage", nargs="?")
    args = parser.parse_args()

    if args.worker:
        if not args.stage:
            raise SystemExit("worker requires a stage path")
        _crash_worker(args.worker, Path(args.stage))
        return 0

    result = run_suite()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
