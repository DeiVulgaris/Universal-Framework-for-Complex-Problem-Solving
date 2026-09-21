#!/usr/bin/env python3
"""UFCPS Level 2 — Task Discovery Engine v1.

Discovery layer between the Unresolved Question Ledger and the Agent Swarm.

The engine does NOT assign work and does NOT decide whether a question is
objectively valuable. It derives auditable Task Prospects from unresolved
question records and exposes separate compatibility signals so an agent can
make its own participation decision.

Canonical flow::

    UQL Question
        -> Prospect derivation
        -> capability compatibility
        -> resource feasibility
        -> information / novelty / reuse signals
        -> economic terms
        -> agent-specific discovery view
        -> agent decides accept / reject / defer / watch / request_resources

Design invariants
-----------------
* the ledger remains authoritative;
* discovery is a derived view, not process state;
* no universal task-value score is required;
* agent autonomy is preserved;
* resource-provider views emphasize resource terms rather than research value;
* unresolved, negative, contradictory, and blocked states remain discoverable;
* terminal question states are excluded from active discovery;
* deterministic output is preferred for reproducible experiments.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence

TERMINAL_STATES = {"resolved", "cancelled", "invalid", "abandoned_with_reason"}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _decimal(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _clamp(value: Any, low: Decimal = Decimal("0"), high: Decimal = Decimal("1")) -> Decimal:
    number = _decimal(value)
    return max(low, min(high, number))


def _norm_tokens(values: Any) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        return {_text(values).lower()} if _text(values) else set()
    if not isinstance(values, Iterable):
        return set()
    return {_text(v).lower() for v in values if _text(v)}


def _capability_names(agent: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()
    values |= _norm_tokens(agent.get("capabilities"))
    for item in agent.get("capabilities", []) if isinstance(agent.get("capabilities"), list) else []:
        if isinstance(item, Mapping):
            values |= _norm_tokens(item.get("name"))
            values |= _norm_tokens(item.get("category"))
            values |= _norm_tokens(item.get("capability_id"))
    return values


def _required_capabilities(question: Mapping[str, Any]) -> set[str]:
    return _norm_tokens(question.get("required_capabilities"))


def _resource_requirements(question: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    requirements = question.get("requirements", {})
    if not isinstance(requirements, Mapping):
        return []
    resources = requirements.get("resources", [])
    return [r for r in resources if isinstance(r, Mapping)] if isinstance(resources, list) else []


def _resource_capacity(resource: Mapping[str, Any]) -> Decimal:
    availability = resource.get("availability", {})
    if not isinstance(availability, Mapping):
        return Decimal("0")
    return _decimal(availability.get("available_capacity"))


def _resource_verified(resource: Mapping[str, Any]) -> bool:
    verification = resource.get("verification", {})
    if not isinstance(verification, Mapping):
        return False
    return _text(verification.get("verification_status")).lower() == "verified"


def _resource_matches_requirement(resource: Mapping[str, Any], requirement: Mapping[str, Any]) -> bool:
    if _text(resource.get("status", "")).lower() not in {"available", "verified", "active"}:
        return False
    if not _resource_verified(resource):
        return False
    requested_type = _text(requirement.get("resource_type")).lower()
    resource_type = _text(resource.get("resource_type")).lower()
    if requested_type and requested_type != resource_type:
        return False
    requested_unit = _text(requirement.get("unit")).lower()
    capacity_unit = _text(resource.get("availability", {}).get("capacity_unit") if isinstance(resource.get("availability"), Mapping) else "").lower()
    if requested_unit and capacity_unit and requested_unit != capacity_unit:
        return False
    capability_names = set()
    capabilities = resource.get("capabilities", [])
    if isinstance(capabilities, list):
        for item in capabilities:
            if isinstance(item, Mapping):
                capability_names |= _norm_tokens(item.get("name"))
                capability_names |= _norm_tokens(item.get("category"))
    requested_capability = _text(requirement.get("capability")).lower()
    if requested_capability and requested_capability not in capability_names:
        return False
    return True


def _required_quantity(requirement: Mapping[str, Any]) -> Decimal:
    return max(Decimal("0"), _decimal(requirement.get("quantity")))


def _resource_feasibility(
    question: Mapping[str, Any],
    resources: Sequence[Mapping[str, Any]],
) -> tuple[Decimal, list[str], list[str]]:
    requirements = _resource_requirements(question)
    if not requirements:
        return Decimal("1"), [], []

    remaining = [dict(r) for r in resources]
    matched: list[str] = []
    blockers: list[str] = []
    ratios: list[Decimal] = []

    for index, requirement in enumerate(requirements):
        needed = _required_quantity(requirement)
        if needed <= 0:
            ratios.append(Decimal("1"))
            continue

        capacity = Decimal("0")
        chosen: list[dict[str, Any]] = []
        for resource in remaining:
            if not _resource_matches_requirement(resource, requirement):
                continue
            available = _resource_capacity(resource)
            if available <= 0:
                continue
            contribution = min(available, needed - capacity)
            if contribution > 0:
                capacity += contribution
                chosen.append(resource)
                if capacity >= needed:
                    break

        ratio = min(Decimal("1"), capacity / needed)
        ratios.append(ratio)
        if capacity >= needed:
            matched.extend(_text(r.get("resource_id")) for r in chosen if _text(r.get("resource_id")))
            # Consume matched capacity for this requirement to keep the view
            # conservative when several requirements compete for the same pool.
            consumed = needed
            for resource in chosen:
                current = _resource_capacity(resource)
                take = min(current, consumed)
                availability = dict(resource.get("availability", {}))
                availability["available_capacity"] = str(current - take)
                resource["availability"] = availability
                consumed -= take
                if consumed <= 0:
                    break
        else:
            blockers.append(
                f"resource requirement {index} needs {needed} units; only {capacity} verified units are available"
            )

    feasibility = min(ratios) if ratios else Decimal("1")
    return feasibility, sorted(set(matched)), blockers


def _signal_block(
    value: Any,
    *,
    provenance: str,
    confidence: Any = "1.0",
) -> dict[str, Any]:
    return {
        "value": str(_clamp(value)),
        "provenance": provenance,
        "timestamp": "not_recorded_by_v1",
        "confidence": str(_clamp(confidence)),
    }


def _question_signal(question: Mapping[str, Any], key: str, default: str = "0.5") -> dict[str, Any]:
    prospect_signals = question.get("prospect_signals", {})
    if isinstance(prospect_signals, Mapping) and key in prospect_signals:
        raw = prospect_signals[key]
        if isinstance(raw, Mapping):
            return {
                "value": str(_clamp(raw.get("value", default))),
                "provenance": _text(raw.get("provenance")) or f"question.prospect_signals.{key}",
                "timestamp": _text(raw.get("timestamp")) or "not_recorded_by_v1",
                "confidence": str(_clamp(raw.get("confidence", "0.5"))),
            }
        return _signal_block(raw, provenance=f"question.prospect_signals.{key}")
    return _signal_block(default, provenance=f"question.default.{key}", confidence="0.25")


@dataclass(frozen=True)
class DiscoverySignal:
    """One auditable discovery signal."""

    value: str
    provenance: str
    timestamp: str
    confidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskProspect:
    """Agent-specific derived view of an unresolved question."""

    prospect_id: str
    question_id: str
    agent_id: str
    discovery_status: str
    formulation: str
    current_frontier: str
    unresolved_difference: str
    known_constraints: list[str]
    previous_attempts: list[str]
    required_capabilities: list[str]
    required_resources: list[dict[str, Any]]
    estimated_compute: str
    estimated_duration: str
    available_budget: str
    signals: dict[str, DiscoverySignal]
    matched_resource_ids: list[str]
    blockers: list[str]
    decision_options: list[str]
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["signals"] = {k: v.to_dict() for k, v in self.signals.items()}
        return data


def _capability_match(question: Mapping[str, Any], agent: Mapping[str, Any]) -> tuple[Decimal, list[str]]:
    required = _required_capabilities(question)
    if not required:
        return Decimal("1"), []
    available = _capability_names(agent)
    missing = sorted(required - available)
    matched = len(required) - len(missing)
    return Decimal(matched) / Decimal(len(required)), missing


def build_prospect(
    question: Mapping[str, Any],
    agent: Mapping[str, Any],
    resources: Sequence[Mapping[str, Any]],
    *,
    prospect_id: str | None = None,
) -> TaskProspect:
    question_id = _text(question.get("question_id"))
    agent_id = _text(agent.get("agent_id"))
    if not question_id:
        raise ValueError("question_id is required")
    if not agent_id:
        raise ValueError("agent_id is required")

    cap_score, missing_caps = _capability_match(question, agent)
    resource_score, matched_resources, resource_blockers = _resource_feasibility(question, resources)

    question_status = _text(question.get("status", "unresolved")).lower()
    blockers = list(resource_blockers)
    blockers.extend(f"missing capability: {name}" for name in missing_caps)

    if question_status in TERMINAL_STATES:
        discovery_status = "terminal_not_discoverable"
    elif cap_score == 1 and resource_score == 1:
        discovery_status = "compatible"
    elif resource_score < 1 and cap_score == 1:
        discovery_status = "awaiting_resources"
    elif cap_score > 0 and resource_score > 0:
        discovery_status = "partially_compatible"
    else:
        discovery_status = "blocked"

    prospect_signals = {
        "capability_match": DiscoverySignal(**_signal_block(cap_score, provenance="derived.capability_match", confidence="1.0")),
        "resource_feasibility": DiscoverySignal(**_signal_block(resource_score, provenance="derived.resource_feasibility", confidence="1.0")),
        "information_gain": DiscoverySignal(**_question_signal(question, "information_gain")),
        "novelty": DiscoverySignal(**_question_signal(question, "novelty")),
        "reusability": DiscoverySignal(**_question_signal(question, "reusability")),
        "continuation_potential": DiscoverySignal(**_question_signal(question, "continuation_potential")),
        "uncertainty": DiscoverySignal(**_question_signal(question, "uncertainty", default="0.7")),
    }

    decision_options = ["accept", "reject", "defer", "watch"]
    if resource_score < 1:
        decision_options.append("request_resources")

    budget = question.get("available_budget_rc", question.get("requested_reward_rc", 0))
    estimated_compute = question.get("estimated_compute", question.get("requirements", {}).get("resources", [{}])[0].get("quantity", 0) if _resource_requirements(question) else 0)
    estimated_duration = question.get("estimated_duration", "not_specified")
    current_frontier = question.get("current_frontier", question.get("current_state", ""))
    attempts = question.get("previous_attempts", question.get("attempted_operations", []))
    constraints = question.get("known_constraints", question.get("constraints", []))

    return TaskProspect(
        prospect_id=prospect_id or f"TP-{question_id}-{agent_id}",
        question_id=question_id,
        agent_id=agent_id,
        discovery_status=discovery_status,
        formulation=_text(question.get("formulation", question.get("title", question.get("task", "")))),
        current_frontier=_text(current_frontier),
        unresolved_difference=_text(question.get("unresolved_difference")),
        known_constraints=[_text(x) for x in constraints if _text(x)] if isinstance(constraints, list) else [],
        previous_attempts=[_text(x) for x in attempts if _text(x)] if isinstance(attempts, list) else [],
        required_capabilities=sorted(_required_capabilities(question)),
        required_resources=[dict(r) for r in _resource_requirements(question)],
        estimated_compute=str(estimated_compute),
        estimated_duration=_text(estimated_duration),
        available_budget=str(_decimal(budget)),
        signals=prospect_signals,
        matched_resource_ids=matched_resources,
        blockers=sorted(set(blockers)),
        decision_options=decision_options,
        provenance={
            "source": "unresolved_question_ledger",
            "question_id": question_id,
            "agent_id": agent_id,
            "derived_only": True,
            "scheduler_assignment": False,
        },
    )


def discover(
    questions: Iterable[Mapping[str, Any]],
    agents: Iterable[Mapping[str, Any]],
    resources: Iterable[Mapping[str, Any]],
) -> list[TaskProspect]:
    """Create agent-specific prospects without assigning work."""
    question_list = [dict(q) for q in questions if isinstance(q, Mapping)]
    agent_list = [dict(a) for a in agents if isinstance(a, Mapping)]
    resource_list = [dict(r) for r in resources if isinstance(r, Mapping)]
    prospects: list[TaskProspect] = []
    seen: set[tuple[str, str]] = set()

    for question in question_list:
        status = _text(question.get("status", "unresolved")).lower()
        if status in TERMINAL_STATES:
            continue
        for agent in agent_list:
            qid = _text(question.get("question_id"))
            aid = _text(agent.get("agent_id"))
            if not qid or not aid or (qid, aid) in seen:
                continue
            seen.add((qid, aid))
            prospects.append(build_prospect(question, agent, resource_list))

    prospects.sort(key=lambda p: (p.question_id, p.agent_id))
    return prospects


def result_summary(prospects: Sequence[TaskProspect]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for prospect in prospects:
        counts[prospect.discovery_status] = counts.get(prospect.discovery_status, 0) + 1
    return {
        "prospects": len(prospects),
        "by_status": counts,
        "autonomous_decision_preserved": all(bool(p.decision_options) for p in prospects),
        "assignment_performed": False,
    }


def demo() -> dict[str, Any]:
    questions = [
        {
            "question_id": "Q-DISC-001",
            "formulation": "Test a distributed simulation hypothesis.",
            "current_frontier": "Simulation method is available but one boundary remains unresolved.",
            "unresolved_difference": "Outcome differs between two resource configurations.",
            "required_capabilities": ["simulation"],
            "requirements": {"resources": [{"resource_type": "gpu", "quantity": 50, "unit": "GPU-hours"}]},
            "estimated_duration": "4h",
            "available_budget_rc": 75,
            "prospect_signals": {
                "information_gain": 0.8,
                "novelty": 0.7,
                "reusability": 0.6,
                "continuation_potential": 0.9,
                "uncertainty": 0.6,
            },
        },
        {
            "question_id": "Q-DISC-002",
            "formulation": "Analyze a contradiction between two branches.",
            "current_frontier": "Two branch results disagree.",
            "unresolved_difference": "Result_A != Result_B.",
            "required_capabilities": ["analysis"],
            "requirements": {"resources": [{"resource_type": "gpu", "quantity": 2000, "unit": "GPU-hours"}]},
            "estimated_duration": "24h",
            "available_budget_rc": 120,
            "prospect_signals": {"information_gain": 0.9, "novelty": 0.9, "reusability": 0.8},
        },
        {
            "question_id": "Q-DISC-003",
            "status": "resolved",
            "formulation": "Already resolved.",
        },
    ]
    agents = [
        {
            "agent_id": "agent-sim",
            "capabilities": ["simulation", "research"],
        },
        {
            "agent_id": "agent-analysis",
            "capabilities": ["analysis", "research"],
        },
    ]
    resources = [
        {
            "resource_id": "gpu-01",
            "resource_type": "gpu",
            "status": "available",
            "verification": {"verification_status": "verified"},
            "availability": {"available_capacity": 1000, "capacity_unit": "GPU-hours"},
            "capabilities": [{"name": "gpu", "category": "compute"}],
        },
    ]

    prospects = discover(questions, agents, resources)
    data = {
        "summary": result_summary(prospects),
        "prospects": [p.to_dict() for p in prospects],
    }
    assert data["summary"]["assignment_performed"] is False
    assert data["summary"]["autonomous_decision_preserved"] is True
    assert data["summary"]["prospects"] == 4
    statuses = data["summary"]["by_status"]
    assert statuses.get("compatible", 0) >= 1
    assert statuses.get("partially_compatible", 0) >= 1 or statuses.get("awaiting_resources", 0) >= 1
    assert all("accept" in p["decision_options"] for p in data["prospects"])
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run deterministic discovery demo")
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
        print("UFCPS Task Discovery Engine v1")
        print("Prospects:", result["summary"]["prospects"])
        print("By status:", result["summary"]["by_status"])
        print("Assignment performed:", result["summary"]["assignment_performed"])
        for prospect in result["prospects"]:
            print(
                f"- {prospect['prospect_id']} | {prospect['discovery_status']} | "
                f"cap={prospect['signals']['capability_match']['value']} | "
                f"res={prospect['signals']['resource_feasibility']['value']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
