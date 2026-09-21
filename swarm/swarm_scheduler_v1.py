
"""
UFCPS Level 2 — Swarm Scheduler v1

Purpose
-------
Coordinate unresolved questions, task prospects, agents, and resources.

The scheduler is intentionally a lightweight orchestration layer. It does not
become the owner of process continuity. It selects compatible carriers and
resources, creates an assignment, and records why the assignment was made.

Core flow:

    unresolved question
        -> task prospect
        -> candidate agents
        -> candidate resources
        -> matching
        -> reservation plan
        -> process assignment

The scheduler does not:
- guarantee that a question can be solved;
- guarantee research success;
- decide financial investments;
- replace the Level 1 process engine;
- assume one permanent agent or resource.

Usage
-----
    python swarm/swarm_scheduler_v1.py
    python swarm/swarm_scheduler_v1.py --json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


@dataclass(frozen=True)
class Assignment:
    assignment_id: str
    question_id: str
    task_prospect_id: str
    agent_id: str
    resource_ids: List[str]
    score: float
    status: str
    reasons: List[str]
    blockers: List[str]


@dataclass(frozen=True)
class SchedulerResult:
    status: str
    assignments: List[Assignment]
    unassigned_questions: List[str]
    summary: Dict[str, Any]


def _norm(value: Any) -> str:
    return str(value).strip().lower()


def _as_set(values: Any) -> set[str]:
    if not isinstance(values, (list, tuple, set)):
        return set()
    return {_norm(v) for v in values if str(v).strip()}


def _resource_types(resource: Mapping[str, Any]) -> set[str]:
    types = {_norm(resource.get("resource_type", ""))}
    for capability in resource.get("capabilities", []):
        if isinstance(capability, Mapping):
            name = capability.get("name")
            category = capability.get("category")
            if name:
                types.add(_norm(name))
            if category:
                types.add(_norm(category))
    return {item for item in types if item}


def _resource_capacity(resource: Mapping[str, Any]) -> float:
    availability = resource.get("availability", {})
    if not isinstance(availability, Mapping):
        return 0.0
    return float(availability.get("available_capacity", 0.0) or 0.0)


def _resource_is_available(resource: Mapping[str, Any]) -> bool:
    if resource.get("status") not in {"available", "discovered"}:
        return False
    verification = resource.get("verification", {})
    if isinstance(verification, Mapping):
        verification_status = verification.get("verification_status")
        if verification_status not in {None, "verified", "pending"}:
            return False
    return True


def _agent_is_available(agent: Mapping[str, Any]) -> bool:
    if agent.get("status") not in {"available", "registered"}:
        return False
    policy = agent.get("task_policy", {})
    if isinstance(policy, Mapping) and policy.get("accepts_tasks") is False:
        return False
    return True


def _agent_capability_score(
    requirements: Sequence[str],
    agent: Mapping[str, Any],
) -> Tuple[float, List[str], List[str]]:
    required = _as_set(requirements)
    if not required:
        return 0.0, [], []

    offered = set()
    for capability in agent.get("capabilities", []):
        if isinstance(capability, Mapping):
            if capability.get("name"):
                offered.add(_norm(capability["name"]))
            if capability.get("category"):
                offered.add(_norm(capability["category"]))
            if capability.get("capability_id"):
                offered.add(_norm(capability["capability_id"]))

    matched = required & offered
    missing = required - offered
    score = len(matched) / len(required)

    reasons = [f"Agent capability match: {sorted(matched)}"] if matched else []
    blockers = [f"Missing agent capability: {item}" for item in sorted(missing)]
    return score, reasons, blockers


def _resource_match(
    requirements: Sequence[Mapping[str, Any]],
    resources: Sequence[Mapping[str, Any]],
) -> Tuple[float, List[str], List[str], List[str]]:
    if not requirements:
        return 0.0, [], [], []

    available = [r for r in resources if _resource_is_available(r)]

    selected: List[str] = []
    reasons: List[str] = []
    blockers: List[str] = []

    total_required = 0
    total_matched = 0

    for requirement in requirements:
        resource_type = _norm(requirement.get("resource_type", ""))
        quantity = float(requirement.get("quantity", 0.0) or 0.0)
        total_required += 1

        candidates = [
            resource for resource in available
            if resource_type in _resource_types(resource)
            and _resource_capacity(resource) >= quantity
        ]

        if candidates:
            chosen = sorted(
                candidates,
                key=lambda item: (
                    -_resource_capacity(item),
                    str(item.get("resource_id", "")),
                ),
            )[0]
            selected.append(str(chosen["resource_id"]))
            total_matched += 1
            reasons.append(
                f"Resource match for {resource_type}: "
                f"{chosen['resource_id']} "
                f"capacity={_resource_capacity(chosen):g}"
            )
        else:
            blockers.append(
                f"No available verified resource for {resource_type} "
                f"quantity={quantity:g}"
            )

    score = total_matched / total_required if total_required else 0.0
    return score, reasons, blockers, selected


def _task_identity(task: Mapping[str, Any]) -> Tuple[str, str]:
    question_id = str(
        task.get("question_id")
        or task.get("origin", {}).get("question_id")
        or task.get("id")
        or ""
    )
    prospect_id = str(
        task.get("task_prospect_id")
        or task.get("prospect_id")
        or task.get("id")
        or ""
    )
    return question_id, prospect_id


def _build_matching_task(prospect: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize Task Prospect data into the matching interface used by
    investor_matching_v1.
    """
    requirements = prospect.get("requirements", {})
    if not isinstance(requirements, Mapping):
        requirements = {}

    interest = prospect.get("interest_profile", {})
    if not isinstance(interest, Mapping):
        interest = {}

    required_capabilities = prospect.get("required_capabilities", [])
    if not required_capabilities:
        required_capabilities = prospect.get("capabilities", [])

    return {
        "requirements": {
            "resources": list(requirements.get("resources", [])),
            "capital": requirements.get("capital", {}),
        },
        "interest_profile": {
            "sectors": list(interest.get("sectors", [])),
            "technologies": list(interest.get("technologies", [])),
            "problem_classes": list(interest.get("problem_classes", [])),
            "resource_types": list(interest.get("resource_types", [])),
            "stakeholder_roles": list(interest.get("stakeholder_roles", [])),
            "geographies": list(interest.get("geographies", [])),
        },
        "agent_capabilities": list(required_capabilities),
    }


def schedule(
    questions: Iterable[Mapping[str, Any]],
    agents: Iterable[Mapping[str, Any]],
    resources: Iterable[Mapping[str, Any]],
) -> SchedulerResult:
    """
    Schedule available agents/resources for task prospects.

    Questions may contain:
        question_id
        task_prospect_id
        required_capabilities
        requirements.resources
        priority

    The scheduler makes at most one initial assignment per question in v1.
    """
    questions = list(questions)
    agents = [agent for agent in agents if _agent_is_available(agent)]
    resources = list(resources)

    assignments: List[Assignment] = []
    unassigned: List[str] = []

    # Import lazily so the module remains usable as a library if the matching
    # component has not yet been installed in the caller's package path.
    try:
        from investor_matching_v1 import match_stakeholder
        matching_available = True
    except ImportError:
        matching_available = False

    for question in questions:
        question_id, prospect_id = _task_identity(question)
        if not question_id:
            unassigned.append(prospect_id or "unknown")
            continue

        required_caps = question.get("required_capabilities", [])
        if not required_caps:
            required_caps = question.get("capabilities", [])

        task_for_match = _build_matching_task(question)

        candidates: List[Tuple[float, Dict[str, Any], List[str], List[str], float]] = []

        for agent in agents:
            capability_score, cap_reasons, cap_blockers = _agent_capability_score(
                required_caps,
                agent,
            )

            resource_requirements = question.get(
                "requirements", {}
            )
            if not isinstance(resource_requirements, Mapping):
                resource_requirements = {}

            resource_score, resource_reasons, resource_blockers, resource_ids = _resource_match(
                resource_requirements.get("resources", []),
                resources,
            )

            # Optional reuse of the general-purpose matcher as an additional
            # interest/role signal. A synthetic stakeholder profile lets us
            # retain the auditable matching logic without treating an agent as
            # an investor.
            general_score = 0.0
            general_reasons: List[str] = []
            general_blockers: List[str] = []
            if matching_available:
                result = match_stakeholder(
                    task_for_match,
                    {
                        "stakeholder_id": str(agent.get("agent_id", "")),
                        "display_name": str(agent.get("agent_id", "")),
                        "roles": ["agent"],
                        "resource_offerings": [],
                        "capital_profile": {},
                        "interests": {
                            "sectors": question.get("interest_profile", {}).get(
                                "sectors", []
                            ) if isinstance(question.get("interest_profile"), Mapping) else [],
                            "technologies": question.get("interest_profile", {}).get(
                                "technologies", []
                            ) if isinstance(question.get("interest_profile"), Mapping) else [],
                            "problem_classes": question.get("interest_profile", {}).get(
                                "problem_classes", []
                            ) if isinstance(question.get("interest_profile"), Mapping) else [],
                            "resource_types": question.get("interest_profile", {}).get(
                                "resource_types", []
                            ) if isinstance(question.get("interest_profile"), Mapping) else [],
                            "geographies": question.get("interest_profile", {}).get(
                                "geographies", []
                            ) if isinstance(question.get("interest_profile"), Mapping) else [],
                        },
                    },
                )
                general_score = result.score * 0.20
                general_reasons = result.reasons
                general_blockers = result.blockers

            # v1 scheduler score:
            # agent capability has the largest weight; resource feasibility is
            # equally important; general contextual matching is secondary.
            score = (
                0.45 * capability_score
                + 0.45 * resource_score
                + 0.10 * general_score
            )

            reasons = cap_reasons + resource_reasons + general_reasons
            blockers = cap_blockers + resource_blockers + general_blockers

            candidates.append(
                (score, agent, reasons, blockers, resource_score)
            )

        if not candidates:
            unassigned.append(question_id)
            continue

        candidates.sort(
            key=lambda item: (
                -item[0],
                str(item[1].get("agent_id", "")),
            )
        )

        score, agent, reasons, blockers, resource_score = candidates[0]

        # An assignment requires both a meaningful agent match and available
        # resources for required resource demands. Questions without resource
        # demands may still be scheduled based on agent capabilities.
        has_resource_requirements = bool(
            isinstance(question.get("requirements"), Mapping)
            and question["requirements"].get("resources")
        )

        if score < 0.50 or (has_resource_requirements and resource_score < 1.0):
            unassigned.append(question_id)
            continue

        _, _, _, selected_resource_ids = _resource_match(
            question.get("requirements", {}).get("resources", [])
            if isinstance(question.get("requirements"), Mapping)
            else [],
            resources,
        )

        assignments.append(
            Assignment(
                assignment_id=f"assign-{question_id}-{agent.get('agent_id')}",
                question_id=question_id,
                task_prospect_id=prospect_id,
                agent_id=str(agent.get("agent_id", "")),
                resource_ids=selected_resource_ids,
                score=round(score, 4),
                status="planned",
                reasons=reasons,
                blockers=blockers,
            )
        )

    status = "scheduled" if assignments else "no_assignments"

    summary = {
        "questions_received": len(questions),
        "agents_available": len(agents),
        "resources_visible": len(resources),
        "assignments_created": len(assignments),
        "questions_unassigned": len(unassigned),
    }

    return SchedulerResult(
        status=status,
        assignments=assignments,
        unassigned_questions=unassigned,
        summary=summary,
    )


def result_to_dict(result: SchedulerResult) -> Dict[str, Any]:
    return {
        "scheduler_version": "v1",
        "status": result.status,
        "summary": result.summary,
        "assignments": [asdict(item) for item in result.assignments],
        "unassigned_questions": result.unassigned_questions,
    }


def demo_inputs() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    questions = [
        {
            "question_id": "Q-SWARM-001",
            "task_prospect_id": "TP-SWARM-001",
            "required_capabilities": ["hypothesis_analysis"],
            "interest_profile": {
                "sectors": ["AI"],
                "technologies": ["distributed compute"],
                "problem_classes": ["research"],
                "resource_types": ["gpu"],
                "geographies": ["Europe"],
            },
            "requirements": {
                "resources": [
                    {
                        "resource_type": "gpu",
                        "quantity": 8,
                        "unit": "GPU-hours",
                    }
                ]
            },
        },
        {
            "question_id": "Q-SWARM-002",
            "task_prospect_id": "TP-SWARM-002",
            "required_capabilities": ["simulation"],
            "requirements": {
                "resources": [
                    {
                        "resource_type": "gpu",
                        "quantity": 1000,
                        "unit": "GPU-hours",
                    }
                ]
            },
        },
    ]

    agents = [
        {
            "agent_id": "agent-research-001",
            "agent_type": "research",
            "status": "available",
            "capabilities": [
                {
                    "capability_id": "cap-hypothesis",
                    "name": "hypothesis_analysis",
                    "category": "research",
                    "confidence": 0.95,
                }
            ],
            "task_policy": {"accepts_tasks": True},
        },
        {
            "agent_id": "agent-sim-001",
            "agent_type": "research",
            "status": "available",
            "capabilities": [
                {
                    "capability_id": "cap-sim",
                    "name": "simulation",
                    "category": "simulation",
                    "confidence": 0.90,
                }
            ],
            "task_policy": {"accepts_tasks": True},
        },
    ]

    resources = [
        {
            "resource_id": "gpu-small-001",
            "resource_type": "gpu",
            "status": "available",
            "capabilities": [
                {
                    "capability_id": "gpu-compute",
                    "name": "gpu",
                    "category": "compute",
                }
            ],
            "availability": {
                "available_capacity": 16,
                "capacity_unit": "GPU-hours",
            },
            "verification": {"verification_status": "verified"},
        },
        {
            "resource_id": "gpu-large-001",
            "resource_type": "gpu",
            "status": "available",
            "capabilities": [
                {
                    "capability_id": "gpu-compute-large",
                    "name": "gpu",
                    "category": "compute",
                }
            ],
            "availability": {
                "available_capacity": 5000,
                "capacity_unit": "GPU-hours",
            },
            "verification": {"verification_status": "verified"},
        },
    ]

    return questions, agents, resources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="UFCPS Level 2 Swarm Scheduler v1"
    )
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

    questions, agents, resources = demo_inputs()
    result = schedule(questions, agents, resources)

    if args.as_json:
        print(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2))
    else:
        print("UFCPS Swarm Scheduler v1")
        print(f"Status: {result.status}")
        print(f"Assignments: {len(result.assignments)}")
        print(f"Unassigned: {len(result.unassigned_questions)}")
        for assignment in result.assignments:
            print(
                f"- {assignment.assignment_id} | "
                f"score={assignment.score:.4f} | "
                f"agent={assignment.agent_id} | "
                f"resources={','.join(assignment.resource_ids)}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
