
"""
UFCPS Level 2 — Proposal Engine v1

Generate structured, non-binding proposals from a task/resource gap.

The engine is intentionally deterministic and evidence-oriented.

It can generate proposals for:
- researchers;
- compute providers;
- physical resource providers;
- investors;
- strategic partners.

It does not:
- guarantee outcomes;
- guarantee investment returns;
- commit capital;
- execute regulated transactions;
- contact recipients;
- impersonate a human.

The output is designed to be consumed by the Proposal schema and Outreach
Campaign layer.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


AUTHOR_ROYALTY_RATE = 0.00001  # 0.001% per qualifying transaction


@dataclass(frozen=True)
class ProposalInput:
    proposal_id: str
    proposal_type: str
    issuer_agent_id: str
    recipient_stakeholder_id: str
    recipient_role: str
    title: str
    summary: str
    objective: str
    requested_action: str
    evidence_refs: List[str]
    risks: List[Dict[str, Any]]
    requirements: Dict[str, Any]
    economics: Dict[str, Any]
    scenarios: List[Dict[str, Any]]
    origin: Dict[str, Any]


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _resource_requirements(gap: Mapping[str, Any]) -> List[Dict[str, Any]]:
    requirements = _as_dict(gap.get("requirements"))
    resources = _as_list(requirements.get("resources"))
    return [dict(item) for item in resources if isinstance(item, Mapping)]


def _capital_requirement(gap: Mapping[str, Any]) -> Dict[str, Any]:
    requirements = _as_dict(gap.get("requirements"))
    capital = requirements.get("capital")
    return dict(capital) if isinstance(capital, Mapping) else {}


def _proposal_type_for_role(role: str, gap: Mapping[str, Any]) -> str:
    normalized = _text(role).lower()

    if "research" in normalized:
        return "research"
    if "compute" in normalized or "resource" in normalized or "provider" in normalized:
        return "compute_resource"
    if "laboratory" in normalized or "physical" in normalized:
        return "physical_resource"
    if "strategic" in normalized or "partner" in normalized:
        return "strategic_partnership"
    if "invest" in normalized:
        return "investment"

    capital = _capital_requirement(gap)
    if capital:
        return "investment"

    if _resource_requirements(gap):
        return "compute_resource"

    return "mixed"


def _format_resources(resources: Sequence[Mapping[str, Any]]) -> str:
    if not resources:
        return "No specific resource quantity is currently defined."

    parts: List[str] = []
    for item in resources:
        resource_type = _text(item.get("resource_type")) or "resource"
        quantity = item.get("quantity")
        unit = _text(item.get("unit"))
        duration = _text(item.get("duration"))
        fragment = f"{resource_type}: {quantity:g}" if isinstance(quantity, (int, float)) else f"{resource_type}: {quantity}"
        if unit:
            fragment += f" {unit}"
        if duration:
            fragment += f" for {duration}"
        parts.append(fragment)

    return "; ".join(parts)


def _format_capital(capital: Mapping[str, Any]) -> str:
    if not capital:
        return "No capital amount specified."

    currency = _text(capital.get("currency"))
    target = capital.get("amount_target")
    minimum = capital.get("amount_min")
    maximum = capital.get("amount_max")

    if target is not None:
        value = f"target {target:g}"
    elif minimum is not None or maximum is not None:
        value = f"range {minimum or 0:g}–{maximum:g}" if maximum is not None else f"minimum {minimum:g}"
    else:
        value = "unspecified amount"

    return f"{value} {currency}".strip()


def _default_risks(gap: Mapping[str, Any], proposal_type: str) -> List[Dict[str, Any]]:
    risks: List[Dict[str, Any]] = []

    if proposal_type in {"investment", "mixed"}:
        risks.append({
            "risk": "Demand and utilization may differ from the modeled assumptions.",
            "impact": "medium",
            "mitigation": "Use staged deployment and scenario-based evaluation.",
            "uncertainty": 0.50,
        })
        risks.append({
            "risk": "Currency and market conditions may change.",
            "impact": "medium",
            "mitigation": "Expose assumptions, sensitivity, liquidity, and volatility rather than guaranteeing returns.",
            "uncertainty": 0.70,
        })

    if proposal_type in {"compute_resource", "physical_resource", "mixed"}:
        risks.append({
            "risk": "Required resource demand may change during the process.",
            "impact": "medium",
            "mitigation": "Use bounded reservations and continuation-aware substitution.",
            "uncertainty": 0.40,
        })

    if not risks:
        risks.append({
            "risk": "The current evidence may be insufficient to guarantee the requested outcome.",
            "impact": "medium",
            "mitigation": "Preserve uncertainty and validate the next procedural step.",
            "uncertainty": 0.60,
        })

    return risks


def _default_scenarios(proposal_type: str) -> List[Dict[str, Any]]:
    if proposal_type == "investment":
        return [
            {
                "name": "base",
                "assumptions": ["Expected utilization follows the current economic model."],
                "outcomes": ["Resource demand continues within modeled range."],
            },
            {
                "name": "downside",
                "assumptions": ["Utilization and/or compute price falls below baseline."],
                "outcomes": ["Deployment may require staged capital and revised capacity."],
            },
            {
                "name": "stress",
                "assumptions": ["Demand shock, liquidity reduction, or energy-cost shock occurs."],
                "outcomes": ["Capacity deployment should be re-evaluated before additional commitment."],
            },
        ]

    return [
        {
            "name": "base",
            "assumptions": ["The requested capability remains sufficient for the current procedural step."],
            "outcomes": ["Process continues to the next validated state."],
        },
        {
            "name": "stress",
            "assumptions": ["The proposed resource becomes temporarily unavailable."],
            "outcomes": ["Process remains continuation-ready if an adequate substitute exists."],
        },
    ]


def build_proposal(
    gap: Mapping[str, Any],
    stakeholder: Mapping[str, Any],
    agent_id: str,
    proposal_id: str | None = None,
) -> Dict[str, Any]:
    """
    Build a structured proposal.

    Expected gap fields:
        question_id, task_prospect_id, resource_gap_id, title, summary,
        objective, requested_action, required_capabilities, requirements,
        evidence_refs, risks, scenarios, sectors, technologies, problem_classes.

    Expected stakeholder fields:
        stakeholder_id, display_name/name, roles.
    """
    stakeholder_id = _text(
        stakeholder.get("stakeholder_id")
        or stakeholder.get("id")
        or ""
    )
    recipient_name = _text(
        stakeholder.get("display_name")
        or stakeholder.get("name")
        or stakeholder_id
    )
    roles = _as_list(stakeholder.get("roles"))
    recipient_role = _text(roles[0]) if roles else "participant"

    proposal_type = _proposal_type_for_role(recipient_role, gap)
    resources = _resource_requirements(gap)
    capital = _capital_requirement(gap)

    if proposal_id is None:
        basis = stakeholder_id or "recipient"
        question_id = _text(gap.get("question_id") or "question")
        proposal_id = f"proposal-{question_id}-{basis}"

    title = _text(gap.get("title")) or f"UFCPS {proposal_type.replace('_', ' ')} proposal"

    summary = _text(gap.get("summary"))
    if not summary:
        summary = (
            f"Proposal for {recipient_name} to support an active UFCPS process "
            f"through a defined capability or resource contribution."
        )

    objective = _text(gap.get("objective"))
    if not objective:
        objective = (
            "Provide the capability or resource required for the next "
            "continuation-capable procedural step."
        )

    requested_action = _text(gap.get("requested_action"))
    if not requested_action:
        if resources:
            requested_action = f"Provide or allocate: {_format_resources(resources)}."
        elif capital:
            requested_action = f"Evaluate funding of {_format_capital(capital)}."
        else:
            requested_action = "Review the proposal and indicate whether participation is feasible."

    evidence_refs = [
        _text(ref) for ref in _as_list(gap.get("evidence_refs")) if _text(ref)
    ]

    risks = _as_list(gap.get("risks"))
    risks = [dict(item) for item in risks if isinstance(item, Mapping)]
    if not risks:
        risks = _default_risks(gap, proposal_type)

    scenarios = _as_list(gap.get("scenarios"))
    scenarios = [dict(item) for item in scenarios if isinstance(item, Mapping)]
    if not scenarios:
        scenarios = _default_scenarios(proposal_type)

    economics: Dict[str, Any] = {}
    if resources:
        economics.update({
            "compensation_model": "verified compute/resource contribution",
            "compute_unit": _text(gap.get("compute_unit")) or "as defined by UFCPS Compute Unit specification",
        })

    if capital:
        economics["capital_request"] = _format_capital(capital)

    economics["author_royalty_rate"] = AUTHOR_ROYALTY_RATE
    economics["economic_assumptions"] = [
        "Resource compensation is based on verified contribution.",
        "Research success is not guaranteed.",
        "Investment outcomes are not guaranteed.",
    ]

    requirements = {
        "capabilities": [
            _text(item) for item in _as_list(gap.get("required_capabilities")) if _text(item)
        ],
        "resources": resources,
    }
    if capital:
        requirements["capital"] = capital

    origin = {
        key: _text(gap.get(key))
        for key in [
            "question_id",
            "task_prospect_id",
            "resource_gap_id",
            "related_process_id",
        ]
        if _text(gap.get(key))
    }

    proposal = {
        "proposal_id": proposal_id,
        "proposal_type": proposal_type,
        "status": "prepared",
        "title": title,
        "summary": summary,
        "issuer": {
            "agent_id": _text(agent_id),
            "role": "UFCPS AI agent",
            "identity_disclosure": "AI agent participating in the UFCPS network.",
        },
        "recipient": {
            "stakeholder_id": stakeholder_id,
            "role": recipient_role,
        },
        "origin": origin,
        "objective": {
            "statement": objective,
            "requested_action": requested_action,
            "success_condition": _text(gap.get("success_condition"))
                or "Required participation is confirmed and the process can continue.",
        },
        "requirements": requirements,
        "economics": economics,
        "evidence": {
            "refs": evidence_refs,
            "summary": _text(gap.get("evidence_summary")),
            "benchmark_refs": [
                _text(ref)
                for ref in _as_list(gap.get("benchmark_refs"))
                if _text(ref)
            ],
            "confidence": gap.get("confidence"),
        },
        "risks": risks,
        "scenarios": scenarios,
        "terms": {
            "non_binding": True,
            "conditions": [
                "Participation remains subject to recipient review.",
                "Resource claims must be verified before economic settlement.",
            ],
        },
        "follow_up": {
            "next_action": "Recipient review and response.",
            "owner_agent_id": _text(agent_id),
        },
        "provenance": {
            "created_at": _text(gap.get("created_at")),
            "source_refs": evidence_refs,
        },
    }

    # Remove optional null values so the output remains clean.
    def prune(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: prune(item)
                for key, item in value.items()
                if item is not None and item != ""
            }
        if isinstance(value, list):
            return [prune(item) for item in value]
        return value

    return prune(proposal)


def build_gap_from_question(
    question: Mapping[str, Any],
    *,
    resource_gap_id: str | None = None,
    requested_action: str | None = None,
) -> Dict[str, Any]:
    """
    Convert a question/task prospect into a proposal-ready resource gap.
    """
    requirements = question.get("requirements", {})
    if not isinstance(requirements, Mapping):
        requirements = {}

    interest_profile = question.get("interest_profile", {})
    if not isinstance(interest_profile, Mapping):
        interest_profile = {}

    resources = requirements.get("resources", [])
    capital = requirements.get("capital", {})

    gap: Dict[str, Any] = {
        "question_id": question.get("question_id"),
        "task_prospect_id": question.get("task_prospect_id"),
        "resource_gap_id": resource_gap_id,
        "title": question.get("title"),
        "summary": question.get("summary"),
        "objective": question.get("objective"),
        "requested_action": requested_action,
        "required_capabilities": question.get("required_capabilities")
            or question.get("capabilities", []),
        "requirements": {
            "resources": resources,
            "capital": capital,
        },
        "evidence_refs": question.get("evidence_refs", []),
        "evidence_summary": question.get("evidence_summary"),
        "benchmark_refs": question.get("benchmark_refs", []),
        "confidence": question.get("confidence"),
        "success_condition": question.get("success_condition"),
        "interest_profile": interest_profile,
        "compute_unit": question.get("compute_unit"),
        "scenarios": question.get("scenarios", []),
    }

    for field in ("sectors", "technologies", "problem_classes"):
        if field not in gap:
            gap[field] = interest_profile.get(field, [])

    return gap


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UFCPS Proposal Engine v1")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit machine-readable JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    question = {
        "question_id": "Q-PROPOSAL-001",
        "task_prospect_id": "TP-PROPOSAL-001",
        "title": "GPU capacity for continuation experiment",
        "summary": "The current process requires additional verified GPU capacity.",
        "objective": "Provide the compute required for the next procedural step.",
        "requested_action": "Provide 100 GPU-hours.",
        "required_capabilities": ["simulation"],
        "requirements": {
            "resources": [
                {
                    "resource_type": "gpu",
                    "quantity": 100,
                    "unit": "GPU-hours",
                    "duration": "7 days",
                }
            ],
            "capital": {},
        },
        "evidence_refs": ["benchmark-demo-001"],
        "evidence_summary": "Previous process state is continuation-ready.",
        "benchmark_refs": ["benchmark-demo-001"],
        "confidence": 0.90,
        "success_condition": "100 verified GPU-hours are available to the process.",
        "compute_unit": "GPU-hour",
    }

    stakeholder = {
        "stakeholder_id": "stakeholder-provider-001",
        "display_name": "Demo Resource Provider",
        "roles": ["resource_provider"],
    }

    proposal = build_proposal(
        build_gap_from_question(question),
        stakeholder,
        agent_id="agent-proposal-001",
    )

    if args.as_json:
        print(json.dumps(proposal, ensure_ascii=False, indent=2))
    else:
        print("UFCPS Proposal Engine v1")
        print(f"Proposal: {proposal['proposal_id']}")
        print(f"Type: {proposal['proposal_type']}")
        print(f"Status: {proposal['status']}")
        print(f"Recipient: {proposal['recipient']['stakeholder_id']}")
        print(f"Action: {proposal['objective']['requested_action']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
