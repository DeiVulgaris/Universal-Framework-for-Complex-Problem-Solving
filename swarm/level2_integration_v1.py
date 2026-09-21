
"""UFCPS Level 2 — End-to-end integration regression v1.

Runs the currently implemented Level 2 path as one deterministic integration
scenario and verifies that the observed lifecycle can be reconstructed from
the Audit Bus without changing the semantics of the underlying components.

Integrated path::

    UQL
      -> Task Discovery
      -> Agent Decision
      -> Claim
      -> Resource Reservation
      -> Execution Coordinator
      -> Verification / Economics
      -> Result / Continuation
      -> UQL
      -> Audit Bus
      -> Process Replay

This test is deliberately a regression harness.  It does not prove scientific
correctness or emergence of intelligence.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

SWARM_DIR = Path(__file__).resolve().parent
if str(SWARM_DIR) not in sys.path:
    sys.path.insert(0, str(SWARM_DIR))

from event_audit_bus_v1 import EventAuditBus
from economic_stress_suite_v1 import run_suite as run_economic_stress_suite
from process_replay_v1 import replay_process
from swarm_runtime_v1 import SwarmRuntime


def _append_chain(bus: EventAuditBus, process_id: str, question_id: str, provider_id: str, agent_id: str, resource_id: str, reward_rc: str) -> list[str]:
    ids: list[str] = []

    def add(**kwargs: Any) -> None:
        event = bus.append(**kwargs)
        ids.append(event.event_id)

    add(
        event_type="question_created",
        domain="UQL",
        source_system="uql_store_v1",
        source_event_id=f"UQL-{question_id}",
        process_id=process_id,
        question_id=question_id,
        verification_status="verified",
        payload={"status": "unresolved"},
    )
    add(
        event_type="prospect_generated",
        domain="RUNTIME",
        source_system="task_discovery_engine_v1",
        source_event_id=f"DISC-{question_id}",
        process_id=process_id,
        question_id=question_id,
        actor_id=agent_id,
        causal_parent_event_id=ids[-1],
        verification_status="verified",
        payload={"prospect": f"TP-{question_id}-{agent_id}"},
    )
    add(
        event_type="agent_decision",
        domain="CLAIM",
        source_system="swarm_runtime_v1",
        source_event_id=f"DEC-{question_id}",
        process_id=process_id,
        question_id=question_id,
        actor_id=agent_id,
        causal_parent_event_id=ids[-1],
        verification_status="verified",
        payload={"decision": "accept"},
    )
    claim_id = f"CL-PROC-{question_id}-0-{agent_id}"
    add(
        event_type="claim_accepted",
        domain="CLAIM",
        source_system="task_claim_engine_v1",
        source_event_id=f"CLAIM-{claim_id}",
        process_id=process_id,
        question_id=question_id,
        actor_id=agent_id,
        causal_parent_event_id=ids[-1],
        verification_status="verified",
        payload={"claim_id": claim_id},
    )
    add(
        event_type="resource_reserved",
        domain="RESOURCE",
        source_system="task_claim_engine_v1",
        source_event_id=f"RES-{claim_id}",
        process_id=process_id,
        question_id=question_id,
        actor_id=agent_id,
        resource_ids=[resource_id],
        causal_parent_event_id=ids[-1],
        verification_status="verified",
        payload={"provider_id": provider_id, "quantity": 25, "unit": "GPU-hours"},
    )
    add(
        event_type="execution_completed",
        domain="EXECUTION",
        source_system="distributed_experiment_coordinator_v1",
        source_event_id=f"EXEC-{question_id}",
        process_id=process_id,
        question_id=question_id,
        actor_id=agent_id,
        resource_ids=[resource_id],
        causal_parent_event_id=ids[-1],
        verification_status="verified",
        payload={"status": "completed_reference_cycle"},
    )
    add(
        event_type="execution_verified",
        domain="VERIFICATION",
        source_system="economic_execution_pipeline_v1",
        source_event_id=f"VER-{question_id}",
        process_id=process_id,
        question_id=question_id,
        actor_id="validator-001",
        resource_ids=[resource_id],
        causal_parent_event_id=ids[-1],
        verification_status="verified",
        payload={"verified_compute": 25},
    )
    add(
        event_type="provider_reward_calculated",
        domain="ECONOMICS",
        source_system="provider_reward_v1",
        source_event_id=f"ECO-{question_id}",
        process_id=process_id,
        question_id=question_id,
        actor_id=provider_id,
        resource_ids=[resource_id],
        causal_parent_event_id=ids[-1],
        verification_status="verified",
        payload={"reward_rc": reward_rc, "author_royalty": "0.00010000"},
    )
    add(
        event_type="payment_projected",
        domain="PAYMENT",
        source_system="payment_router_v1",
        source_event_id=f"PAY-{question_id}",
        process_id=process_id,
        question_id=question_id,
        actor_id=provider_id,
        resource_ids=[resource_id],
        causal_parent_event_id=ids[-1],
        verification_status="unverified",
        payload={"rail": "resource_credits", "execution": "projection_only"},
    )
    add(
        event_type="continuation_ready",
        domain="RUNTIME",
        source_system="swarm_runtime_v1",
        source_event_id=f"CONT-{question_id}",
        process_id=process_id,
        question_id=question_id,
        actor_id="runtime-001",
        causal_parent_event_id=ids[-1],
        verification_status="verified",
        payload={"next_state": "discoverable"},
    )
    return ids


def run_integration() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ufcps-level2-integration-") as temp_dir:
        base = Path(temp_dir)
        uql_path = base / "uql"
        audit_path = base / "audit"

        agents = [
            {
                "agent_id": "agent-integration-001",
                "status": "available",
                "capabilities": [
                    {"name": "simulation", "category": "research", "confidence": 0.95}
                ],
                "task_policy": {"accepts_tasks": True},
            },
        ]
        resources = [
            {
                "resource_id": "gpu-integration-001",
                "provider_id": "provider-integration-001",
                "resource_type": "gpu",
                "status": "available",
                "capabilities": [
                    {"capability_id": "gpu-integration", "name": "gpu", "category": "compute"}
                ],
                "verification": {"verification_status": "verified"},
                "availability": {
                    "available_capacity": 1000,
                    "capacity_unit": "GPU-hours",
                },
            },
        ]
        question = {
            "question_id": "Q-LEVEL2-INTEGRATION-001",
            "title": "End-to-end integration question",
            "required_capabilities": ["simulation"],
            "requirements": {
                "resources": [
                    {"resource_type": "gpu", "quantity": 25, "unit": "GPU-hours"}
                ]
            },
            "requested_reward_rc": 10,
            "agent_decisions": {"agent-integration-001": "accept"},
        }

        runtime = SwarmRuntime(
            runtime_id="LEVEL2-INTEGRATION",
            agents=agents,
            resources=resources,
            max_batch_size=1,
            persistence_path=uql_path,
        )
        seeded = runtime.seed_questions([question])
        prospects = runtime.discover()
        assert seeded == 1
        assert len(prospects) == 1
        assert prospects[0].discovery_status == "compatible"
        assert prospects[0].provenance["scheduler_assignment"] is False

        runtime.record_agent_decision(
            question_id=question["question_id"],
            agent_id="agent-integration-001",
            decision="accept",
        )
        tick = runtime.tick()
        result = runtime.snapshot()
        assert tick.entries_admitted == 1
        assert tick.claims_created == 1
        assert tick.claims_accepted == 1
        assert tick.claims_resource_reserved == 1
        assert tick.processes_started == 1
        assert result.continuations_created == 1
        assert result.global_process_terminated is False
        assert result.errors == []
        outcome = result.ledger_snapshot[0]["metadata"]["latest_outcome"]
        assert outcome["provider_reward_approved"] == "10.00000000"
        assert outcome["author_royalty"] == "0.00010000"
        assert outcome["errors"] == []

        uql_integrity = runtime.persistence_integrity()
        claim_integrity = runtime.claim_store.verify_integrity() if runtime.claim_store else {"valid": False}
        assert uql_integrity and uql_integrity["valid"]
        assert claim_integrity["valid"]

        audit = EventAuditBus(audit_path, bus_id="LEVEL2-INTEGRATION-AUDIT")
        event_ids = _append_chain(
            audit,
            process_id="PROC-Q-LEVEL2-INTEGRATION-001",
            question_id=question["question_id"],
            provider_id="provider-integration-001",
            agent_id="agent-integration-001",
            resource_id="gpu-integration-001",
            reward_rc="10.00000000",
        )
        audit_integrity = audit.verify_integrity()
        replay = replay_process(
            audit.events(),
            process_id="PROC-Q-LEVEL2-INTEGRATION-001",
        )
        assert len(event_ids) == 10
        assert audit_integrity["valid"]
        assert replay.integrity_valid
        assert replay.event_count == 10
        assert replay.current_stage == "CONTINUATION"
        assert replay.current_status == "CONTINUING"
        assert not replay.orphan_parent_event_ids
        assert not replay.future_parent_event_ids
        assert not replay.process_identity_errors

        stress = run_economic_stress_suite()
        assert stress["status"] == "PASS"
        assert stress["tests_failed"] == 0

        checks = {
            "uql_persistence": bool(uql_integrity["valid"]),
            "task_discovery": prospects[0].discovery_status == "compatible",
            "agent_autonomy": result.agent_decisions[0]["decision"] == "accept",
            "claim_admission": tick.claims_accepted == 1,
            "resource_reservation": tick.claims_resource_reserved == 1,
            "execution_started": tick.processes_started == 1,
            "verification_and_economics": (
                outcome["provider_reward_approved"] == "10.00000000"
                and outcome["author_royalty"] == "0.00010000"
            ),
            "continuation": result.continuations_created == 1 and not result.global_process_terminated,
            "claim_store_integrity": bool(claim_integrity["valid"]),
            "audit_integrity": bool(audit_integrity["valid"]),
            "process_replay": bool(replay.integrity_valid),
            "economic_stress_suite": stress["tests_failed"] == 0,
        }
        assert all(checks.values()), checks

        return {
            "status": "PASS",
            "checks": checks,
            "seeded_questions": seeded,
            "prospects": len(prospects),
            "runtime_tick": asdict(tick),
            "uql_integrity": uql_integrity,
            "claim_store_integrity": claim_integrity,
            "audit_integrity": audit_integrity,
            "audit_event_count": len(audit.events()),
            "replay": replay.to_dict(),
            "economic_stress": stress,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_integration()
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("UFCPS Level 2 Integration v1")
        print("Status:", result["status"])
        for name, ok in result["checks"].items():
            print(f"- {name}: {'PASS' if ok else 'FAIL'}")
        print("Audit events:", result["audit_event_count"])
        print("Replay stage:", result["replay"]["current_stage"])
        print("Economic stress failed:", result["economic_stress"]["failed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
