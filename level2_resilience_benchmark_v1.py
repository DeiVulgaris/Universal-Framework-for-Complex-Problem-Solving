
"""UFCPS Level 2 — Resilience Benchmark v1.

System-level resilience benchmark for the existing UFCPS Level 2 prototype.

This artifact does not add a runtime mechanism.  It composes the already
implemented layers and checks whether process continuity survives carrier
failure, durable state recovery, audit replay, and economic settlement retry.

Scope
-----
1. Existing Level 2 integration regression.
2. Runtime crash/recovery scenarios.
3. Payment settlement idempotency/crash recovery.
4. A synthetic cross-layer causal chain ending in economic settlement and
   continuation.
5. Explicit boundary reporting for properties not established by the local
   prototype (e.g. Byzantine consensus, physical power-loss guarantees,
   external payment-provider guarantees without provider idempotency).

This benchmark is descriptive. It is not an intelligence score and does not
claim to establish AGI, convergence, or real-world distributed-system safety.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import uuid
from pathlib import Path
from typing import Any
from decimal import Decimal

from event_audit_bus_v1 import EventAuditBus
from level2_integration_v1 import run_integration
from level2_runtime_recovery_v1 import run_suite as run_runtime_recovery
from payment_settlement_store_v1 import (
    AUTHOR_ROYALTY_RATE,
    PaymentSettlementStore,
    ReferenceIdempotentExecutor,
    _self_test as payment_self_test,
)
from process_replay_v1 import replay_process

SCHEMA_VERSION = "level2-resilience-benchmark-v1"


def _append_causal_chain(
    bus: EventAuditBus,
    *,
    process_id: str,
    question_id: str,
    agent_id: str,
    resource_id: str,
    provider_id: str,
) -> list[str]:
    ids: list[str] = []

    def add(*, event_type: str, domain: str, source_system: str, source_event_id: str,
            actor_id: str, payload: dict[str, Any], resource_ids: list[str] | None = None,
            verification_status: str = "verified") -> None:
        parent = ids[-1] if ids else None
        event_id = str(uuid.uuid4())
        bus.append(
            event_id=event_id,
            event_type=event_type,
            domain=domain,
            source_system=source_system,
            source_event_id=source_event_id,
            process_id=process_id,
            question_id=question_id,
            actor_id=actor_id,
            resource_ids=resource_ids or [],
            causal_parent_event_id=parent,
            verification_status=verification_status,
            payload=payload,
        )
        ids.append(event_id)

    add(
        event_type="question_created",
        domain="UQL",
        source_system="uql_store_v1",
        source_event_id=f"Q-{question_id}",
        actor_id="uql",
        payload={"status": "unresolved"},
    )
    add(
        event_type="task_discovered",
        domain="RUNTIME",
        source_system="task_discovery_engine_v1",
        source_event_id=f"D-{question_id}",
        actor_id=agent_id,
        payload={"discovery_status": "compatible", "decision_required": True},
    )
    add(
        event_type="agent_decision",
        domain="RUNTIME",
        source_system="swarm_runtime_v1",
        source_event_id=f"DEC-{question_id}",
        actor_id=agent_id,
        payload={"decision": "accept"},
    )
    add(
        event_type="claim_accepted",
        domain="CLAIM",
        source_system="task_claim_engine_v1",
        source_event_id=f"CLAIM-{question_id}",
        actor_id=agent_id,
        payload={"claim_id": f"CL-{question_id}"},
    )
    add(
        event_type="resource_reserved",
        domain="RESOURCE",
        source_system="task_claim_engine_v1",
        source_event_id=f"RES-{question_id}",
        actor_id=agent_id,
        resource_ids=[resource_id],
        payload={"provider_id": provider_id, "quantity": 25, "unit": "GPU-hours"},
    )
    add(
        event_type="execution_completed",
        domain="EXECUTION",
        source_system="distributed_experiment_coordinator_v1",
        source_event_id=f"EXEC-{question_id}",
        actor_id=agent_id,
        resource_ids=[resource_id],
        payload={"status": "completed_reference_cycle"},
    )
    add(
        event_type="execution_verified",
        domain="VERIFICATION",
        source_system="compute_verification_v1",
        source_event_id=f"VER-{question_id}",
        actor_id="validator-001",
        resource_ids=[resource_id],
        payload={"verified_compute": 25},
    )
    add(
        event_type="provider_reward_calculated",
        domain="ECONOMICS",
        source_system="provider_reward_v1",
        source_event_id=f"ECO-{question_id}",
        actor_id=provider_id,
        resource_ids=[resource_id],
        payload={"reward_rc": "10.00000000", "author_royalty": "0.00010000"},
    )
    add(
        event_type="settlement_settled",
        domain="PAYMENT",
        source_system="payment_settlement_store_v1",
        source_event_id=f"SETTLE-{question_id}",
        actor_id=provider_id,
        resource_ids=[resource_id],
        payload={
            "settlement_key": f"ufcps-settlement:contrib-{question_id}",
            "status": "SETTLED",
            "rail": "resource_credits",
        },
    )
    add(
        event_type="continuation_ready",
        domain="RUNTIME",
        source_system="swarm_runtime_v1",
        source_event_id=f"CONT-{question_id}",
        actor_id="runtime-001",
        payload={"next_state": "discoverable"},
    )
    return ids


def run_settlement_smoke() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ufcps-level2-resilience-payment-") as temp:
        base = Path(temp) / "settlement"
        executor = ReferenceIdempotentExecutor()
        store = PaymentSettlementStore(
            base,
            journal_batch_size=4,
            checkpoint_interval=4,
            durable=True,
        )
        try:
            record = store.prepare(
                contribution_id="resilience-contrib-001",
                reward_id="resilience-reward-001",
                provider_id="provider-resilience-001",
                resource_id="gpu-resilience-001",
                rail="resource_credits",
                gross="100.00000000",
                author_royalty="0.00100000",
                provider_net="99.99900000",
            )
            settled = store.settle(
                contribution_id="resilience-contrib-001",
                executor=executor.execute,
            )
            repeated = store.settle(
                contribution_id="resilience-contrib-001",
                executor=executor.execute,
            )
            integrity = store.verify_integrity()
            checks = {
                "prepared": record.status == "SETTLEMENT_PREPARED",
                "settled": settled.status == "SETTLED",
                "repeat_idempotent": repeated.external_reference == settled.external_reference,
                "single_executor_effect": executor.calls == 1,
                "single_settled_event": len(store.settled_records()) == 1,
                "integrity": bool(integrity["integrity_ok"]),
                "royalty_rate": AUTHOR_ROYALTY_RATE == Decimal("0.00001"),
            }
            return {
                "status": "PASS" if all(checks.values()) else "FAIL",
                "checks": checks,
                "event_count": store.event_count,
                "integrity": integrity,
            }
        finally:
            store.close()


def run_cross_layer_replay() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ufcps-level2-resilience-audit-") as temp:
        bus = EventAuditBus(Path(temp) / "audit", bus_id="LEVEL2-RESILIENCE-AUDIT")
        process_id = "PROC-LEVEL2-RESILIENCE-001"
        question_id = "Q-LEVEL2-RESILIENCE-001"
        ids = _append_causal_chain(
            bus,
            process_id=process_id,
            question_id=question_id,
            agent_id="agent-resilience-001",
            resource_id="gpu-resilience-001",
            provider_id="provider-resilience-001",
        )
        integrity = bus.verify_integrity()
        replay = replay_process(bus.events(), process_id=process_id)
        checks = {
            "event_chain_integrity": bool(integrity["valid"]),
            "causal_chain_complete": not replay.orphan_parent_event_ids and not replay.future_parent_event_ids,
            "process_identity_valid": not replay.process_identity_errors,
            "continuation_stage": replay.current_stage == "CONTINUATION",
            "continuing_status": replay.current_status == "CONTINUING",
            "expected_event_count": len(ids) == 10,
        }
        return {
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "audit_event_count": len(ids),
            "replay": replay.to_dict(),
            "audit_integrity": integrity,
        }


def run_benchmark() -> dict[str, Any]:
    integration = run_integration()
    runtime_recovery = run_runtime_recovery()
    payment_self = payment_self_test()
    payment_smoke = run_settlement_smoke()
    cross_layer = run_cross_layer_replay()

    checks = {
        "level2_integration": integration.get("status") == "PASS",
        "runtime_recovery": runtime_recovery.get("status") == "PASS",
        "payment_settlement_self_test": bool(payment_self.get("passed")),
        "payment_settlement_smoke": payment_smoke.get("status") == "PASS",
        "cross_layer_audit_replay": cross_layer.get("status") == "PASS",
    }

    boundaries = {
        "real_external_payment": "NOT_ESTABLISHED",
        "provider_idempotency": "modeled_only",
        "Byzantine_consensus": "NOT_ESTABLISHED",
        "physical_power_loss_guarantee": "NOT_ESTABLISHED",
        "global_convergence": "NOT_ESTABLISHED",
        "intelligence_or_AGI": "NOT_ESTABLISHED",
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "passed": sum(bool(v) for v in checks.values()),
        "failed": sum(not bool(v) for v in checks.values()),
        "n_a_in_subtests": sum(1 for r in runtime_recovery.get("results", []) if r.get("status") == "N/A"),
        "integration_summary": {
            "status": integration.get("status"),
            "checks": integration.get("checks", {}),
            "economic_stress": integration.get("economic_stress", {}).get("tests_failed"),
        },
        "runtime_recovery_summary": {
            "status": runtime_recovery.get("status"),
            "scenarios_requested": runtime_recovery.get("scenarios_requested"),
            "passed": runtime_recovery.get("passed"),
            "failed": runtime_recovery.get("failed"),
            "payment_idempotency_legacy_n_a": runtime_recovery.get("payment_idempotency"),
        },
        "payment_self_test_summary": {
            "passed": bool(payment_self.get("passed")),
            "checks": payment_self.get("checks", {}),
            "guarantees": payment_self.get("guarantees", {}),
        },
        "cross_layer_replay_summary": cross_layer,
        "boundaries": boundaries,
        "interpretation": {
            "descriptive_result": (
                "The local Level 2 prototype preserves process-recovery, durable UQL/claim history, "
                "audit replay, and idempotent internal settlement across the exercised failure scenarios."
            ),
            "not_a_claim_of": [
                "real-world distributed consensus",
                "physical durability under all storage/power failures",
                "exactly-once effects at arbitrary external payment providers",
                "automatic convergence of arbitrary research tasks",
                "general intelligence",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    result = run_benchmark()
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print("UFCPS Level 2 — Resilience Benchmark v1")
        print("Status:", result["status"])
        for name, ok in result["checks"].items():
            print(f"- {name}: {'PASS' if ok else 'FAIL'}")
        print("Runtime recovery:", result["runtime_recovery_summary"]["passed"], "/", result["runtime_recovery_summary"]["scenarios_requested"])
        print("Boundaries: explicit; see --json")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
