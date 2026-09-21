#!/usr/bin/env python3
"""UFCPS Level 2 — Economic Execution Pipeline v1.

Unifies the Level-2 economic execution loop without executing real payments.

Canonical reference cycle::

    Question
      -> Task Prospect / scheduler input
      -> Resource Discovery + Assignment
      -> Execution Claim
      -> Verification Gate
      -> Incentive Assessment
      -> Provider Reward
      -> Payment/Settlement Projection
      -> Ledger Events
      -> Continuation State

Core semantics
--------------
* A resource provider is compensated for VERIFIED provision of process
  continuity, not for producing a successful research outcome.
* A verified Deadlock may be an information resource; it does not terminate
  the global process.
* Economic controls do not replace C5 semantic recursion control.
* Payment records are reference projections only: no bank, blockchain, or
  payment-provider side effects occur in this module.
* ProviderRewardEngine owns payout arithmetic so the universal 0.001% author
  royalty is not accidentally applied twice by this orchestration layer.

This is an orchestration/reference layer, not a production settlement engine.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

SWARM_DIR = Path(__file__).resolve().parent
if str(SWARM_DIR) not in sys.path:
    sys.path.insert(0, str(SWARM_DIR))

from economic_incentive_engine_v1 import EconomicIncentiveEngine
from provider_reward_v1 import ProviderRewardEngine, ProviderReward
from swarm_scheduler_v1 import SchedulerResult, schedule


CONTINUATION_STATUSES = {
    "completed",
    "deadlock",
    "technologically_unresolved",
    "negative_result",
    "failed_but_continuation_ready",
}


@dataclass(frozen=True)
class ExecutionClaim:
    claim_id: str
    assignment_id: str
    provider_id: str
    resource_id: str
    execution_status: str
    verified_compute: Decimal
    compute_unit: str
    research_outcome: str
    deadlock: Optional[dict[str, Any]]
    evidence_refs: list[str]
    verification_status: str = "verified"
    c5_valid: bool = True
    recursion_depth: Decimal = Decimal("0")
    repetition_score: Decimal = Decimal("0")
    new_information_score: Decimal = Decimal("0")
    unresolved_information_delta: Decimal = Decimal("0")
    base_step_cost: Decimal = Decimal("1")


@dataclass(frozen=True)
class VerificationGate:
    status: str
    verified_compute: Decimal
    evidence_refs: list[str]
    resource_verified: bool
    execution_verified: bool
    continuation_ready: bool
    reason: str


@dataclass(frozen=True)
class PaymentSettlement:
    reward_id: str
    provider_id: str
    resource_id: str
    rail: str
    gross: Decimal
    author_royalty: Decimal
    protocol_fee: Decimal
    internal_spread: Decimal
    provider_net: Decimal
    execution: str


@dataclass(frozen=True)
class PipelineResult:
    pipeline_id: str
    status: str
    assignment: Optional[dict[str, Any]]
    verification: dict[str, Any]
    incentive: dict[str, Any]
    provider_reward: Optional[dict[str, Any]]
    payment: Optional[dict[str, Any]]
    ledger_events: list[dict[str, Any]]
    continuation_state: dict[str, Any]
    errors: list[str]


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


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _claim_from_mapping(claim: Mapping[str, Any]) -> ExecutionClaim:
    deadlock = claim.get("deadlock")
    if deadlock is not None and not isinstance(deadlock, Mapping):
        raise ValueError("deadlock must be an object when supplied")

    return ExecutionClaim(
        claim_id=_text(claim.get("claim_id")) or "claim-unknown",
        assignment_id=_text(claim.get("assignment_id")),
        provider_id=_text(claim.get("provider_id")),
        resource_id=_text(claim.get("resource_id")),
        execution_status=_text(claim.get("execution_status")).lower(),
        verified_compute=_d(claim.get("verified_compute", 0)),
        compute_unit=_text(claim.get("compute_unit")) or "GPU-hour",
        research_outcome=_text(claim.get("research_outcome")).lower(),
        deadlock=dict(deadlock) if isinstance(deadlock, Mapping) else None,
        evidence_refs=[_text(x) for x in claim.get("evidence_refs", []) if _text(x)],
        verification_status=_text(claim.get("verification_status")) or "verified",
        c5_valid=bool(claim.get("c5_valid", True)),
        recursion_depth=_d(claim.get("recursion_depth", 0)),
        repetition_score=_d(claim.get("repetition_score", 0)),
        new_information_score=_d(claim.get("new_information_score", 0)),
        unresolved_information_delta=_d(claim.get("unresolved_information_delta", 0)),
        base_step_cost=_d(claim.get("base_step_cost", 1)),
    )


def verify_execution_claim(
    claim: ExecutionClaim,
    assignment: Mapping[str, Any],
) -> VerificationGate:
    """Apply the pipeline's minimal verification gate.

    This gate does not decide scientific correctness. It checks that the
    upstream verification contract has marked the execution as verified and
    that the verified quantity/evidence is coherent with the assignment.
    """
    errors: list[str] = []

    assignment_resources = [str(x) for x in assignment.get("resource_ids", [])]
    resource_verified = claim.resource_id in assignment_resources
    execution_verified = claim.verification_status == "verified"

    if not _text(claim.assignment_id):
        errors.append("assignment_id is required")
    if claim.assignment_id != _text(assignment.get("assignment_id")):
        errors.append("claim assignment_id does not match scheduled assignment")
    if not resource_verified:
        errors.append("claimed resource is not part of the scheduled assignment")
    if claim.verified_compute <= 0:
        errors.append("verified_compute must be > 0")
    if not claim.compute_unit:
        errors.append("compute_unit is required")
    if not claim.evidence_refs:
        errors.append("at least one evidence reference is required")
    if not execution_verified:
        errors.append("verification_status is not verified")

    passed = not errors
    continuation_ready = passed and (
        claim.execution_status in CONTINUATION_STATUSES
    )

    if not passed:
        status = "rejected"
        reason = "; ".join(errors)
    elif continuation_ready:
        status = "verified_continuation_ready"
        reason = "verified execution is continuation-ready"
    else:
        status = "verified_but_terminal_or_unknown_status"
        reason = "execution verified, but continuation status is not classified"

    return VerificationGate(
        status=status,
        verified_compute=claim.verified_compute if passed else Decimal("0"),
        evidence_refs=list(claim.evidence_refs),
        resource_verified=resource_verified,
        execution_verified=execution_verified,
        continuation_ready=continuation_ready,
        reason=reason,
    )


def _resource_ids(resources: Iterable[Mapping[str, Any]]) -> set[str]:
    return {str(item.get("resource_id")) for item in resources if item.get("resource_id")}


def _provider_for_resource(
    resources: Sequence[Mapping[str, Any]],
    resource_id: str,
) -> str:
    for resource in resources:
        if str(resource.get("resource_id")) == resource_id:
            return _text(
                resource.get("provider_id")
                or resource.get("owner_id")
                or resource.get("stakeholder_id")
            )
    return ""


def _ledger_event(event_type: str, **payload: Any) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "payload": _safe(payload),
    }


def run_pipeline(
    *,
    pipeline_id: str,
    question: Mapping[str, Any],
    agents: Iterable[Mapping[str, Any]],
    resources: Iterable[Mapping[str, Any]],
    execution_claim: Mapping[str, Any],
    reference_cost: Any,
    target_year: int,
    payout_rail: str = "resource_credits",
    already_issued_rc: Any = 0,
    requested_reward_rc: Any = 0,
    projection_multipliers: Optional[dict[str, Any]] = None,
    resource_inflow: Optional[Mapping[str, Any]] = None,
    deadlock_bonus_budget: Any = "0",
) -> PipelineResult:
    """Run one complete reference execution cycle."""
    errors: list[str] = []
    resources_list = list(resources)
    agents_list = list(agents)
    claim = _claim_from_mapping(execution_claim)

    # 1. Schedule / assign.
    scheduler_result: SchedulerResult = schedule(
        [question],
        agents_list,
        resources_list,
    )

    assignment_obj = scheduler_result.assignments[0] if scheduler_result.assignments else None
    assignment = asdict(assignment_obj) if assignment_obj else None

    if assignment is None:
        ledger = [
            _ledger_event(
                "process_blocked",
                pipeline_id=pipeline_id,
                question_id=question.get("question_id"),
                scheduler_status=scheduler_result.status,
            )
        ]
        return PipelineResult(
            pipeline_id=pipeline_id,
            status="blocked_no_assignment",
            assignment=None,
            verification=asdict(
                VerificationGate(
                    status="not_started",
                    verified_compute=Decimal("0"),
                    evidence_refs=[],
                    resource_verified=False,
                    execution_verified=False,
                    continuation_ready=False,
                    reason="no schedulable agent/resource assignment",
                )
            ),
            incentive={},
            provider_reward=None,
            payment=None,
            ledger_events=ledger,
            continuation_state={
                "process_terminated": False,
                "continuation_ready": False,
                "reason": "local resource/agent blockage",
            },
            errors=[
                f"scheduler status={scheduler_result.status}",
                *scheduler_result.unassigned_questions,
            ],
        )

    # 2. Verification gate.
    gate = verify_execution_claim(claim, assignment)
    ledger = [
        _ledger_event(
            "assignment_created",
            pipeline_id=pipeline_id,
            assignment_id=assignment["assignment_id"],
            question_id=assignment["question_id"],
            agent_id=assignment["agent_id"],
            resource_ids=assignment["resource_ids"],
        ),
        _ledger_event(
            "verification_gate",
            pipeline_id=pipeline_id,
            claim_id=claim.claim_id,
            status=gate.status,
            verified_compute=gate.verified_compute,
            evidence_refs=gate.evidence_refs,
        ),
    ]

    if gate.status == "rejected":
        return PipelineResult(
            pipeline_id=pipeline_id,
            status="rejected_unverified_execution",
            assignment=assignment,
            verification=asdict(gate),
            incentive={},
            provider_reward=None,
            payment=None,
            ledger_events=ledger,
            continuation_state={
                "process_terminated": False,
                "continuation_ready": False,
                "reason": "verification failed; no economic settlement",
            },
            errors=[gate.reason],
        )

    # 3. Incentive assessment.
    incentive_engine = EconomicIncentiveEngine()
    recursion = incentive_engine.assess_recursion(
        recursion_depth=claim.recursion_depth,
        repetition_score=claim.repetition_score,
        new_information_score=claim.new_information_score,
        unresolved_information_delta=claim.unresolved_information_delta,
        base_step_cost=claim.base_step_cost,
        c5_valid=claim.c5_valid,
    )

    deadlock_result: Optional[dict[str, Any]] = None
    if claim.deadlock is not None:
        deadlock_result = incentive_engine.assess_deadlock(
            claim.deadlock,
            verified=True,
            duplicate=False,
            bonus_budget=deadlock_bonus_budget,
        )

    resource_result: Optional[dict[str, Any]] = None
    if resource_inflow is not None:
        resource_result = incentive_engine.assess_resource_inflow(
            current_capacity=resource_inflow.get("current_capacity", 0),
            new_verified_capacity=resource_inflow.get("new_verified_capacity", 0),
            target_capacity=resource_inflow.get("target_capacity", 0),
            capital_inflow=resource_inflow.get("capital_inflow", 0),
            current_demand=resource_inflow.get("current_demand", 0),
        )

    incentive = {
        "recursion": recursion,
        "deadlock": deadlock_result,
        "resource_inflow": resource_result,
        "c5_valid": claim.c5_valid,
    }
    ledger.append(
        _ledger_event(
            "incentive_assessed",
            pipeline_id=pipeline_id,
            recursion_cost=recursion.get("effective_step_cost"),
            deadlock_bonus=(deadlock_result or {}).get("indicative_bonus", 0),
            resource_inflow_index=(resource_result or {}).get("resource_inflow_index", 0),
        )
    )

    # 4. Provider reward. No research-outcome condition is imposed here.
    provider_id = claim.provider_id or _provider_for_resource(resources_list, claim.resource_id)
    if not provider_id:
        errors.append("provider_id missing from execution claim and resource registry")

    provider_reward: Optional[ProviderReward] = None
    payment: Optional[PaymentSettlement] = None

    if provider_id and _d(requested_reward_rc) > 0:
        reward_engine = ProviderRewardEngine()
        provider_reward = reward_engine.approve_and_settle(
            provider_id=provider_id,
            resource_id=claim.resource_id,
            verified_compute=gate.verified_compute,
            compute_unit=claim.compute_unit,
            month=1,
            already_issued_rc=already_issued_rc,
            requested_reward_rc=requested_reward_rc,
            reference_cost=reference_cost,
            target_year=target_year,
            payout_rail=payout_rail,
            c5_valid=claim.c5_valid,
            projection_multipliers=projection_multipliers,
            metadata={
                "pipeline_id": pipeline_id,
                "claim_id": claim.claim_id,
                "research_outcome": claim.research_outcome,
                "outcome_dependency": False,
            },
        )
        reward_dict = asdict(provider_reward)
        ledger.append(
            _ledger_event(
                "provider_reward_calculated",
                pipeline_id=pipeline_id,
                reward_id=provider_reward.reward_id,
                status=provider_reward.status,
                approved_reward_rc=provider_reward.approved_reward_rc,
                research_outcome_dependency=provider_reward.research_outcome_dependency,
            )
        )

        settlement = reward_engine.settlement_projection(reward=provider_reward)
        payment = PaymentSettlement(
            reward_id=str(settlement["reward_id"]),
            provider_id=str(settlement["provider_id"]),
            resource_id=str(settlement["resource_id"]),
            rail=str(settlement["rail"]),
            gross=_d(settlement["gross"]),
            author_royalty=_d(settlement["author_royalty"]),
            protocol_fee=_d(settlement["protocol_fee"]),
            internal_spread=_d(settlement["internal_spread"]),
            provider_net=_d(settlement["provider_net"]),
            execution=str(settlement["execution"]),
        )
        ledger.append(
            _ledger_event(
                "payment_settlement_projection",
                pipeline_id=pipeline_id,
                reward_id=payment.reward_id,
                rail=payment.rail,
                gross=payment.gross,
                author_royalty=payment.author_royalty,
                protocol_fee=payment.protocol_fee,
                internal_spread=payment.internal_spread,
                provider_net=payment.provider_net,
                execution=payment.execution,
            )
        )
    elif _d(requested_reward_rc) <= 0:
        errors.append("requested_reward_rc is zero; reward calculation skipped")

    # 5. Continuation state. A deadlock/negative result does not terminate the
    # global process; the local unit records the state for the next unit.
    local_status = claim.execution_status or "unknown"
    continuation_ready = gate.continuation_ready
    process_terminated = False

    if local_status in {"deadlock", "negative_result", "technologically_unresolved", "failed_but_continuation_ready"}:
        continuation_reason = "local outcome recorded as input to the next procedural state"
    elif local_status == "completed":
        continuation_reason = "validated result recorded; next state may unfold"
    else:
        continuation_reason = "execution state recorded without global process termination"

    ledger.append(
        _ledger_event(
            "continuation_state",
            pipeline_id=pipeline_id,
            execution_status=local_status,
            process_terminated=process_terminated,
            continuation_ready=continuation_ready,
            reason=continuation_reason,
        )
    )

    status = "completed_reference_cycle"
    if claim.c5_valid is False and provider_reward is not None and provider_reward.status == "rejected_c5":
        status = "completed_cycle_reward_blocked_c5"
    elif claim.deadlock is not None:
        status = "completed_cycle_deadlock_recorded"

    return PipelineResult(
        pipeline_id=pipeline_id,
        status=status,
        assignment=assignment,
        verification=asdict(gate),
        incentive=incentive,
        provider_reward=asdict(provider_reward) if provider_reward else None,
        payment=asdict(payment) if payment else None,
        ledger_events=ledger,
        continuation_state={
            "process_terminated": process_terminated,
            "continuation_ready": continuation_ready,
            "reason": continuation_reason,
        },
        errors=errors,
    )


def demo() -> dict[str, Any]:
    """Run deterministic reference cases for the unified pipeline."""
    agents = [
        {
            "agent_id": "agent-simulation-001",
            "status": "available",
            "capabilities": [{"name": "simulation", "category": "research"}],
            "task_policy": {"accepts_tasks": True},
        }
    ]
    resources = [
        {
            "resource_id": "gpu-provider-001",
            "provider_id": "provider-001",
            "resource_type": "gpu",
            "status": "available",
            "capabilities": [{"name": "gpu"}],
            "verification": {"verification_status": "verified"},
            "availability": {"available_capacity": 500},
        }
    ]
    question = {
        "question_id": "Q-PIPE-001",
        "task_prospect_id": "TP-PIPE-001",
        "title": "Continuation experiment",
        "required_capabilities": ["simulation"],
        "requirements": {
            "resources": [{
                "resource_type": "gpu",
                "quantity": 100,
                "unit": "GPU-hours",
            }]
        },
        "priority": 1,
    }
    claim = {
        "claim_id": "claim-PIPE-001",
        "assignment_id": "assign-Q-PIPE-001-agent-simulation-001",
        "provider_id": "provider-001",
        "resource_id": "gpu-provider-001",
        "execution_status": "completed",
        "verification_status": "verified",
        "verified_compute": 100,
        "compute_unit": "GPU-hours",
        "research_outcome": "not_required_for_provider_payment",
        "evidence_refs": ["exec-proof-001"],
        "new_information_score": 0.6,
        "unresolved_information_delta": 0.2,
    }

    reward_engine = ProviderRewardEngine()
    reference_cost = reward_engine.annual_cost(
        year=2026,
        equipment_annualized=10000,
        energy=3000,
        maintenance=1000,
        network=500,
        storage=250,
        verification=250,
    )

    result = run_pipeline(
        pipeline_id="UFCPS-PIPE-DEMO-001",
        question=question,
        agents=agents,
        resources=resources,
        execution_claim=claim,
        reference_cost=reference_cost,
        target_year=2027,
        requested_reward_rc=100,
        payout_rail="resource_credits",
        projection_multipliers={
            "equipment": "1.05",
            "energy": "1.10",
            "maintenance": "1.05",
            "network": "1.03",
            "storage": "1.04",
            "verification": "1.05",
        },
    )

    return _safe(asdict(result))


def _assert_demo(result: Mapping[str, Any]) -> None:
    assert result["status"] == "completed_reference_cycle"
    assert result["verification"]["status"] == "verified_continuation_ready"
    assert result["continuation_state"]["process_terminated"] is False
    assert result["provider_reward"]["research_outcome_dependency"] is False
    assert result["payment"]["protocol_fee"] in ("0", Decimal("0"))
    assert result["payment"]["internal_spread"] in ("0", Decimal("0"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UFCPS Economic Execution Pipeline v1")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    result = demo()
    _assert_demo(result)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print("UFCPS Economic Execution Pipeline v1")
        print(f"Status: {result['status']}")
        print(f"Verification: {result['verification']['status']}")
        print(f"Provider reward: {result['provider_reward']['status']}")
        print(f"Payment execution: {result['payment']['execution']}")
        print(f"Process terminated: {result['continuation_state']['process_terminated']}")
        print(f"Ledger events: {len(result['ledger_events'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
