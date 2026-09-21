
"""UFCPS Level 2 — Distributed Experiment Coordinator v1.

Coordinates multiple experimental processes through the existing UFCPS
execution pipeline.  This module is an orchestration/reference layer:
there are no real payments, blockchain operations, or remote execution calls.

Canonical batch cycle::

    Question Set
      -> deterministic scheduling
      -> one isolated execution pipeline per process
      -> result / negative result / Deadlock
      -> continuation records
      -> aggregate swarm state

Core semantics
--------------
* A local process failure does not terminate the coordinator.
* Deadlock and negative-result states remain valid continuation inputs.
* Resource-provider reward depends on verified process continuity, not research
  success.
* A batch is considered globally alive while at least one process is
  continuation-ready; individual blocked/rejected processes remain auditable.
* v1 executes reference simulations sequentially for determinism.  The API is
  intentionally batch-oriented so a future runtime can dispatch the same
  process units concurrently without changing the semantics.
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

from economic_execution_pipeline_v1 import run_pipeline
from swarm_scheduler_v1 import schedule
from provider_reward_v1 import ProviderRewardEngine


@dataclass(frozen=True)
class ExperimentSpec:
    process_id: str
    question: dict[str, Any]
    execution_claim: dict[str, Any]
    requested_reward_rc: Decimal = Decimal("0")
    payout_rail: str = "resource_credits"
    deadlock_bonus_budget: Decimal = Decimal("0")
    c5_valid: bool = True
    resource_inflow: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class ExperimentOutcome:
    process_id: str
    status: str
    continuation_ready: bool
    process_terminated: bool
    local_failure: bool
    research_outcome: str
    deadlock_recorded: bool
    provider_reward_approved: Decimal
    author_royalty: Decimal
    errors: list[str]
    ledger_event_count: int


@dataclass(frozen=True)
class CoordinatorResult:
    coordinator_id: str
    status: str
    processes_received: int
    processes_started: int
    processes_completed: int
    processes_continuation_ready: int
    processes_blocked_or_rejected: int
    global_process_terminated: bool
    outcomes: list[dict[str, Any]]
    continuation_queue: list[dict[str, Any]]
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


def _spec_from_mapping(item: Mapping[str, Any]) -> ExperimentSpec:
    question = item.get("question")
    claim = item.get("execution_claim")
    if not isinstance(question, Mapping):
        raise ValueError("experiment spec requires question object")
    if not isinstance(claim, Mapping):
        raise ValueError("experiment spec requires execution_claim object")

    process_id = _text(item.get("process_id")) or _text(question.get("question_id"))
    if not process_id:
        raise ValueError("experiment spec requires process_id or question_id")

    claim_copy = dict(claim)
    claim_copy.setdefault("c5_valid", bool(item.get("c5_valid", True)))

    resource_inflow = item.get("resource_inflow")
    if resource_inflow is not None and not isinstance(resource_inflow, Mapping):
        raise ValueError("resource_inflow must be an object when supplied")

    return ExperimentSpec(
        process_id=process_id,
        question=dict(question),
        execution_claim=claim_copy,
        requested_reward_rc=_d(item.get("requested_reward_rc", 0)),
        payout_rail=_text(item.get("payout_rail")) or "resource_credits",
        deadlock_bonus_budget=_d(item.get("deadlock_bonus_budget", 0)),
        c5_valid=bool(item.get("c5_valid", claim_copy.get("c5_valid", True))),
        resource_inflow=dict(resource_inflow) if isinstance(resource_inflow, Mapping) else None,
    )


def _inject_claim_assignment(
    claim: Mapping[str, Any],
    *,
    assignment_id: str,
    assigned_resource_id: str,
    provider_id: str,
) -> dict[str, Any]:
    """Normalize a claim against the actual scheduled assignment.

    A coordinator owns the process-level scheduling step.  The execution claim
    is therefore allowed to omit the assignment id/resource/provider when a
    caller wants the coordinator to bind them after scheduling.
    """
    normalized = dict(claim)
    normalized.setdefault("assignment_id", assignment_id)
    normalized.setdefault("resource_id", assigned_resource_id)
    if provider_id:
        normalized.setdefault("provider_id", provider_id)
    return normalized


def _provider_for_resource(resources: Sequence[Mapping[str, Any]], resource_id: str) -> str:
    for resource in resources:
        if _text(resource.get("resource_id")) == resource_id:
            return _text(
                resource.get("provider_id")
                or resource.get("owner_id")
                or resource.get("stakeholder_id")
            )
    return ""


def _base_reference_cost() -> Any:
    engine = ProviderRewardEngine()
    return engine.annual_cost(
        year=2026,
        equipment_annualized="10000",
        energy="3000",
        maintenance="1000",
        network="500",
        storage="250",
        verification="250",
    )


def _projection_multipliers() -> dict[str, str]:
    return {
        "equipment": "1.05",
        "energy": "1.10",
        "maintenance": "1.05",
        "network": "1.03",
        "storage": "1.04",
        "verification": "1.05",
    }


def coordinate_experiments(
    *,
    coordinator_id: str,
    experiments: Iterable[Mapping[str, Any] | ExperimentSpec],
    agents: Iterable[Mapping[str, Any]],
    resources: Iterable[Mapping[str, Any]],
    reference_cost: Any = None,
    target_year: int = 2027,
    already_issued_rc: Any = 0,
    projection_multipliers: Optional[dict[str, Any]] = None,
) -> CoordinatorResult:
    """Coordinate a batch of independent UFCPS experiment processes."""
    errors: list[str] = []
    outcomes: list[ExperimentOutcome] = []
    continuation_queue: list[dict[str, Any]] = []

    specs: list[ExperimentSpec] = []
    for item in experiments:
        try:
            specs.append(item if isinstance(item, ExperimentSpec) else _spec_from_mapping(item))
        except (TypeError, ValueError, ArithmeticError) as exc:
            errors.append(f"invalid experiment spec: {exc}")

    agents_list = [dict(x) for x in agents]
    resources_list = [dict(x) for x in resources]
    ref_cost = reference_cost or _base_reference_cost()
    multipliers = projection_multipliers or _projection_multipliers()

    started = 0
    completed = 0
    continuation_ready = 0
    blocked_or_rejected = 0

    for spec in specs:
        started += 1
        claim = dict(spec.execution_claim)
        claim["c5_valid"] = spec.c5_valid

        # Bind the execution claim to the deterministic assignment that the
        # canonical pipeline is expected to produce.  The pipeline repeats
        # the same scheduler call and therefore remains the authoritative
        # execution gate.
        preview = schedule([spec.question], agents_list, resources_list)
        preview_assignment = preview.assignments[0] if preview.assignments else None
        if preview_assignment is not None:
            assigned_resource = (
                _text(claim.get("resource_id"))
                if _text(claim.get("resource_id")) in preview_assignment.resource_ids
                else (preview_assignment.resource_ids[0] if preview_assignment.resource_ids else "")
            )
            provider = _provider_for_resource(resources_list, assigned_resource)
            claim = _inject_claim_assignment(
                claim,
                assignment_id=_text(claim.get("assignment_id")) or preview_assignment.assignment_id,
                assigned_resource_id=assigned_resource,
                provider_id=provider,
            )

        try:
            result = run_pipeline(
                pipeline_id=spec.process_id,
                question=spec.question,
                agents=agents_list,
                resources=resources_list,
                execution_claim=claim,
                reference_cost=ref_cost,
                target_year=target_year,
                payout_rail=spec.payout_rail,
                already_issued_rc=already_issued_rc,
                requested_reward_rc=spec.requested_reward_rc,
                projection_multipliers=multipliers,
                resource_inflow=spec.resource_inflow,
                deadlock_bonus_budget=spec.deadlock_bonus_budget,
            )
            data = asdict(result)

            result_continuation = bool(data["continuation_state"].get("continuation_ready"))
            result_terminated = bool(data["continuation_state"].get("process_terminated"))
            local_failure = data["status"] in {
                "blocked_no_assignment",
                "rejected_unverified_execution",
            }
            deadlock_recorded = "deadlock" in data["status"] or data["verification"].get("status") == "verified_continuation_ready" and bool(spec.execution_claim.get("deadlock"))
            reward = data.get("provider_reward") or {}
            approved = _d(reward.get("approved_reward_rc", 0))
            royalty = _d(reward.get("author_royalty", 0))
            research_outcome = _text(spec.execution_claim.get("research_outcome"))
            errors_for_outcome = [str(x) for x in data.get("errors", [])]

            outcome = ExperimentOutcome(
                process_id=spec.process_id,
                status=str(data["status"]),
                continuation_ready=result_continuation,
                process_terminated=result_terminated,
                local_failure=local_failure,
                research_outcome=research_outcome,
                deadlock_recorded=deadlock_recorded,
                provider_reward_approved=approved,
                author_royalty=royalty,
                errors=errors_for_outcome,
                ledger_event_count=len(data.get("ledger_events", [])),
            )
            outcomes.append(outcome)

            if local_failure:
                blocked_or_rejected += 1
            else:
                completed += 1
            if result_continuation:
                continuation_ready += 1
                continuation_queue.append({
                    "process_id": spec.process_id,
                    "source_status": data["status"],
                    "next_input_type": (
                        "deadlock"
                        if bool(spec.execution_claim.get("deadlock"))
                        else "next_procedural_state"
                    ),
                    "continuation_reason": data["continuation_state"].get("reason", ""),
                })

        except Exception as exc:  # isolate one process from the batch
            blocked_or_rejected += 1
            errors.append(f"{spec.process_id}: coordinator-isolated exception: {exc}")
            outcomes.append(
                ExperimentOutcome(
                    process_id=spec.process_id,
                    status="isolated_local_exception",
                    continuation_ready=False,
                    process_terminated=False,
                    local_failure=True,
                    research_outcome=_text(spec.execution_claim.get("research_outcome")),
                    deadlock_recorded=False,
                    provider_reward_approved=Decimal("0"),
                    author_royalty=Decimal("0"),
                    errors=[str(exc)],
                    ledger_event_count=0,
                )
            )

    # A coordinator-level termination flag is reserved for an explicit future
    # global-stop policy.  v1 never derives global termination from local state.
    global_terminated = False
    if specs and not continuation_queue and errors:
        status = "batch_completed_no_continuation"
    elif continuation_queue:
        status = "batch_completed_continuation_available"
    else:
        status = "batch_completed"

    return CoordinatorResult(
        coordinator_id=coordinator_id,
        status=status,
        processes_received=len(specs),
        processes_started=started,
        processes_completed=completed,
        processes_continuation_ready=continuation_ready,
        processes_blocked_or_rejected=blocked_or_rejected,
        global_process_terminated=global_terminated,
        outcomes=[_safe(asdict(x)) for x in outcomes],
        continuation_queue=_safe(continuation_queue),
        errors=errors,
    )


def demo() -> dict[str, Any]:
    """Run four isolated processes with mixed outcomes."""
    agents = [
        {
            "agent_id": "agent-coordinator-001",
            "status": "available",
            "capabilities": [{"name": "simulation", "category": "research"}],
            "task_policy": {"accepts_tasks": True},
        },
        {
            "agent_id": "agent-coordinator-002",
            "status": "available",
            "capabilities": [{"name": "analysis", "category": "research"}],
            "task_policy": {"accepts_tasks": True},
        },
    ]
    resources = [
        {
            "resource_id": "gpu-coordinator-001",
            "provider_id": "provider-coordinator-001",
            "resource_type": "gpu",
            "status": "available",
            "capabilities": [{"name": "gpu"}],
            "verification": {"verification_status": "verified"},
            "availability": {"available_capacity": 500},
        },
        {
            "resource_id": "gpu-coordinator-002",
            "provider_id": "provider-coordinator-002",
            "resource_type": "gpu",
            "status": "available",
            "capabilities": [{"name": "gpu"}],
            "verification": {"verification_status": "verified"},
            "availability": {"available_capacity": 500},
        },
    ]

    def spec(process_id: str, qid: str, title: str, outcome: str, *, deadlock: bool = False, c5: bool = True):
        claim = {
            "claim_id": f"claim-{process_id}",
            "resource_id": "gpu-coordinator-001",
            "execution_status": outcome,
            "verification_status": "verified",
            "verified_compute": 50,
            "compute_unit": "GPU-hours",
            "research_outcome": "not_required_for_provider_payment",
            "evidence_refs": [f"proof-{process_id}"],
            "new_information_score": 0.6,
            "unresolved_information_delta": 0.2,
            "c5_valid": c5,
        }
        if deadlock:
            claim["deadlock"] = {
                "deadlock_id": f"deadlock-{process_id}",
                "boundary_completeness": 1.0,
                "constraint_completeness": 0.9,
                "attempt_trace_completeness": 0.9,
                "negative_result_quality": 0.8,
                "evidence_quality": 1.0,
                "substitution_guidance": 0.7,
                "reproducibility": 0.8,
            }
        return {
            "process_id": process_id,
            "question": {
                "question_id": qid,
                "task_prospect_id": f"TP-{process_id}",
                "title": title,
                "required_capabilities": ["simulation"],
                "requirements": {"resources": [{"resource_type": "gpu", "quantity": 50, "unit": "GPU-hours"}]},
                "priority": 1,
            },
            "execution_claim": claim,
            "requested_reward_rc": 25,
            "payout_rail": "resource_credits",
            "deadlock_bonus_budget": 10,
            "c5_valid": c5,
        }

    experiments = [
        spec("EXP-001", "Q-001", "successful process", "completed"),
        spec("EXP-002", "Q-002", "negative process", "negative_result"),
        spec("EXP-003", "Q-003", "deadlock process", "deadlock", deadlock=True),
        spec("EXP-004", "Q-004", "C5 bounded process", "completed", c5=False),
    ]

    result = coordinate_experiments(
        coordinator_id="COORD-DEMO-001",
        experiments=experiments,
        agents=agents,
        resources=resources,
    )
    data = _safe(asdict(result))

    assert data["global_process_terminated"] is False
    assert data["processes_received"] == 4
    assert data["processes_completed"] == 4
    assert data["processes_continuation_ready"] == 4
    assert len(data["continuation_queue"]) == 4
    c5 = next(x for x in data["outcomes"] if x["process_id"] == "EXP-004")
    assert c5["status"] == "completed_cycle_reward_blocked_c5"
    dead = next(x for x in data["outcomes"] if x["process_id"] == "EXP-003")
    assert dead["deadlock_recorded"] is True
    assert dead["continuation_ready"] is True

    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run deterministic reference batch")
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
        print("UFCPS Distributed Experiment Coordinator v1")
        print("Status:", result["status"])
        print("Processes:", result["processes_received"])
        print("Continuation-ready:", result["processes_continuation_ready"])
        print("Global terminated:", result["global_process_terminated"])
        for outcome in result["outcomes"]:
            print(
                outcome["process_id"],
                outcome["status"],
                "continuation=" + str(outcome["continuation_ready"]),
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
