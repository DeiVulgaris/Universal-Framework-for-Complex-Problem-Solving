"""
UFCPS Level 2 — Investor / Stakeholder Matching v1

Purpose
-------
Match a task/resource requirement against stakeholder profiles.

Important:
- This module ranks candidates by explicit, auditable fit signals.
- It does not make investment decisions.
- It does not predict financial returns.
- It does not contact stakeholders.
- It can match investors, resource providers, researchers, and strategic partners.

The matcher is deliberately heuristic in v1. Scores are decomposed so that
agents can inspect why a candidate matched.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Sequence


@dataclass(frozen=True)
class MatchWeights:
    """Relative weights for explicit matching dimensions."""

    resource: float = 0.35
    capital: float = 0.25
    interest: float = 0.20
    role: float = 0.10
    geography: float = 0.10

    def normalized(self) -> "MatchWeights":
        total = self.resource + self.capital + self.interest + self.role + self.geography
        if total <= 0:
            raise ValueError("At least one match weight must be positive.")
        return MatchWeights(
            resource=self.resource / total,
            capital=self.capital / total,
            interest=self.interest / total,
            role=self.role / total,
            geography=self.geography / total,
        )


@dataclass(frozen=True)
class MatchResult:
    stakeholder_id: str
    display_name: str
    fit_status: str
    score: float
    signals: Dict[str, float]
    reasons: List[str]
    blockers: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _norm_text(value: Any) -> str:
    return str(value).strip().lower()


def _as_set(values: Any) -> set[str]:
    if not isinstance(values, (list, tuple, set)):
        return set()
    return {_norm_text(v) for v in values if str(v).strip()}


def _intersection_score(requested: Iterable[str], offered: Iterable[str]) -> float:
    req = _as_set(list(requested))
    off = _as_set(list(offered))
    if not req:
        return 0.0
    return len(req & off) / len(req)


def _nested_list(obj: Dict[str, Any], path: Sequence[str]) -> list:
    current: Any = obj
    for key in path:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    return current if isinstance(current, list) else []


def _resource_match(requirements: Dict[str, Any], stakeholder: Dict[str, Any]) -> tuple[float, List[str], List[str]]:
    required = requirements.get("resources", [])
    offerings = stakeholder.get("resource_offerings", [])

    if not required:
        return 0.0, [], []

    offered_types = {
        _norm_text(item.get("resource_type"))
        for item in offerings
        if isinstance(item, dict) and item.get("resource_type")
    }

    required_types = {
        _norm_text(item.get("resource_type"))
        for item in required
        if isinstance(item, dict) and item.get("resource_type")
    }

    if not required_types:
        return 0.0, [], ["Task has resource requirements without resource types."]

    overlap = required_types & offered_types
    score = len(overlap) / len(required_types)

    reasons = [f"Resource type match: {sorted(overlap)}"] if overlap else []
    blockers = [
        f"Missing resource type: {resource_type}"
        for resource_type in sorted(required_types - offered_types)
    ]
    return score, reasons, blockers


def _capital_match(requirements: Dict[str, Any], stakeholder: Dict[str, Any]) -> tuple[float, List[str], List[str]]:
    capital_req = requirements.get("capital")
    profile = stakeholder.get("capital_profile", {})

    if not isinstance(capital_req, dict) or not capital_req:
        return 0.0, [], []

    target = capital_req.get("amount_target")
    amount_min = capital_req.get("amount_min", target)
    if target is None and amount_min is None:
        return 0.0, [], ["Capital requirement lacks an amount."]

    maximum = profile.get("maximum_amount")
    minimum = profile.get("minimum_amount", 0)

    if maximum is None:
        return 0.0, [], ["Stakeholder capital capacity is unknown."]

    target_value = float(target if target is not None else amount_min)
    minimum_required = float(amount_min if amount_min is not None else target_value)

    if maximum < minimum_required:
        return 0.0, [], [f"Capital capacity below minimum requirement ({minimum_required})."]

    if target_value <= 0:
        return 0.0, [], []

    # 1.0 means the stated target fits inside the capacity.
    capacity_score = min(1.0, maximum / target_value)

    currency_req = _norm_text(capital_req.get("currency", ""))
    currency_profile = _norm_text(profile.get("currency", ""))
    currency_score = 1.0 if not currency_req or not currency_profile or currency_req == currency_profile else 0.0

    score = 0.8 * capacity_score + 0.2 * currency_score
    reasons = [f"Capital capacity supports requested amount ({maximum:g} available)."]
    if currency_req and currency_profile and currency_req != currency_profile:
        reasons.append("Capital currency differs from requested currency.")

    return score, reasons, []


def _interest_match(task: Dict[str, Any], stakeholder: Dict[str, Any]) -> tuple[float, List[str], List[str]]:
    interests = stakeholder.get("interests", {})
    if not isinstance(interests, dict):
        interests = {}

    task_sectors = _as_set(task.get("sectors", []))
    task_tech = _as_set(task.get("technologies", []))
    task_problem_classes = _as_set(task.get("problem_classes", []))
    task_resource_types = _as_set(task.get("resource_types", []))

    sector_score = _intersection_score(task_sectors, interests.get("sectors", []))
    tech_score = _intersection_score(task_tech, interests.get("technologies", []))
    problem_score = _intersection_score(task_problem_classes, interests.get("problem_classes", []))
    resource_interest_score = _intersection_score(
        task_resource_types, interests.get("resource_types", [])
    )

    values = [sector_score, tech_score, problem_score, resource_interest_score]
    non_empty = [value for value in values if value > 0]
    score = sum(values) / len(values) if non_empty else 0.0

    reasons: List[str] = []
    if sector_score:
        reasons.append(f"Sector interest overlap: {sector_score:.2f}")
    if tech_score:
        reasons.append(f"Technology interest overlap: {tech_score:.2f}")
    if problem_score:
        reasons.append(f"Problem-class interest overlap: {problem_score:.2f}")
    if resource_interest_score:
        reasons.append(f"Resource interest overlap: {resource_interest_score:.2f}")

    return score, reasons, []


def _role_match(task: Dict[str, Any], stakeholder: Dict[str, Any]) -> tuple[float, List[str], List[str]]:
    requested_roles = _as_set(task.get("stakeholder_roles", []))
    roles = _as_set(stakeholder.get("roles", []))

    if not requested_roles:
        return 0.0, [], []

    overlap = requested_roles & roles
    if not overlap:
        return 0.0, [], [f"No requested role match: {sorted(requested_roles)}"]

    return 1.0, [f"Role match: {sorted(overlap)}"], []


def _geography_match(task: Dict[str, Any], stakeholder: Dict[str, Any]) -> tuple[float, List[str], List[str]]:
    requested = _as_set(task.get("geographies", []))
    location = stakeholder.get("interests", {})
    if not isinstance(location, dict):
        location = {}

    supported = _as_set(location.get("geographies", []))
    if not requested:
        return 0.0, [], []

    if not supported:
        return 0.5, ["Geographic preference unknown."], []

    overlap = requested & supported
    if overlap:
        return 1.0, [f"Geographic match: {sorted(overlap)}"], []

    return 0.0, [], [f"No geographic match: requested {sorted(requested)}"]


def match_stakeholder(
    task: Dict[str, Any],
    stakeholder: Dict[str, Any],
    weights: MatchWeights | None = None,
) -> MatchResult:
    """
    Produce an auditable fit result for one stakeholder.

    Expected task keys:
        resources, capital, sectors, technologies, problem_classes,
        resource_types, stakeholder_roles, geographies.

    Expected stakeholder keys:
        stakeholder_id, display_name, roles, resource_offerings,
        capital_profile, interests.
    """
    weights = (weights or MatchWeights()).normalized()

    resource_score, resource_reasons, resource_blockers = _resource_match(
        task.get("requirements", {}),
        stakeholder,
    )
    capital_score, capital_reasons, capital_blockers = _capital_match(
        task.get("requirements", {}),
        stakeholder,
    )
    interest_score, interest_reasons, interest_blockers = _interest_match(
        task.get("interest_profile", {}),
        stakeholder,
    )
    role_score, role_reasons, role_blockers = _role_match(
        task.get("interest_profile", {}),
        stakeholder,
    )
    geography_score, geography_reasons, geography_blockers = _geography_match(
        task.get("interest_profile", {}),
        stakeholder,
    )

    signals = {
        "resource": round(resource_score, 4),
        "capital": round(capital_score, 4),
        "interest": round(interest_score, 4),
        "role": round(role_score, 4),
        "geography": round(geography_score, 4),
    }

    score = (
        resource_score * weights.resource
        + capital_score * weights.capital
        + interest_score * weights.interest
        + role_score * weights.role
        + geography_score * weights.geography
    )

    reasons = (
        resource_reasons
        + capital_reasons
        + interest_reasons
        + role_reasons
        + geography_reasons
    )
    blockers = (
        resource_blockers
        + capital_blockers
        + interest_blockers
        + role_blockers
        + geography_blockers
    )

    if blockers and score < 0.5:
        fit_status = "no_fit"
    elif blockers or score < 0.65:
        fit_status = "partial_fit"
    else:
        fit_status = "fit"

    return MatchResult(
        stakeholder_id=str(stakeholder.get("stakeholder_id", "")),
        display_name=str(stakeholder.get("display_name") or stakeholder.get("name") or ""),
        fit_status=fit_status,
        score=round(score, 4),
        signals=signals,
        reasons=reasons,
        blockers=blockers,
    )


def match_stakeholders(
    task: Dict[str, Any],
    stakeholders: Iterable[Dict[str, Any]],
    weights: MatchWeights | None = None,
    min_score: float = 0.0,
) -> List[MatchResult]:
    """Match and sort stakeholders by explicit fit score."""
    if not 0.0 <= min_score <= 1.0:
        raise ValueError("min_score must be between 0 and 1.")

    results = [
        match_stakeholder(task, stakeholder, weights)
        for stakeholder in stakeholders
    ]
    return sorted(
        [result for result in results if result.score >= min_score],
        key=lambda result: (-result.score, result.stakeholder_id),
    )


if __name__ == "__main__":
    demo_task = {
        "requirements": {
            "resources": [
                {"resource_type": "gpu", "quantity": 1000, "unit": "GPU-hours"}
            ],
            "capital": {
                "amount_min": 50_000,
                "amount_target": 100_000,
                "currency": "USD",
            },
        },
        "interest_profile": {
            "sectors": ["AI infrastructure"],
            "technologies": ["distributed compute"],
            "problem_classes": ["scientific computing"],
            "resource_types": ["gpu"],
            "stakeholder_roles": ["investor", "infrastructure_operator"],
            "geographies": ["Europe"],
        },
    }

    demo_stakeholders = [
        {
            "stakeholder_id": "demo-001",
            "display_name": "Demo Infrastructure Partner",
            "roles": ["investor", "infrastructure_operator"],
            "resource_offerings": [
                {"resource_type": "gpu", "capacity": 5000, "unit": "GPU-hours"}
            ],
            "capital_profile": {
                "minimum_amount": 50_000,
                "maximum_amount": 500_000,
                "currency": "USD",
            },
            "interests": {
                "sectors": ["AI infrastructure"],
                "technologies": ["distributed compute"],
                "problem_classes": ["scientific computing"],
                "resource_types": ["gpu"],
                "geographies": ["Europe"],
            },
        }
    ]

    print("UFCPS investor matching demo")
    for result in match_stakeholders(demo_task, demo_stakeholders):
        print(result.to_dict())
