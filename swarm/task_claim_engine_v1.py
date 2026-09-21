
"""UFCPS Level 2 — Task Claim Engine v1.

Executable implementation of ``swarm/task_claim_protocol_v1.md``.

The engine models the participation boundary between Task Discovery and
execution.  It deliberately keeps these concepts separate:

    discovery != claim != acceptance != resource reservation != execution

The engine is deterministic and in-memory in v1.  It does not perform real
network operations, scheduler assignment, compute execution, or payment.
Instead it creates auditable claim/resource state and emits append-oriented
claim events that a persistent UQL layer or runtime can consume.

Core invariants
---------------
* a claim is not ownership;
* a claim is not execution;
* a claim is not payment;
* rejected/expired/released claims do not terminate the question;
* concurrent claims are preserved rather than silently deleted;
* resource reservation is independently represented;
* agent/resource loss releases the execution path but preserves the question;
* handoff preserves parent-claim provenance;
* only accepted claims can reserve resources;
* terminal question states block admission.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional, Sequence

TERMINAL_QUESTION_STATES = {
    "resolved",
    "cancelled",
    "invalid",
    "abandoned_with_reason",
}

VALID_CLAIM_STATES = {
    "DISCOVERED",
    "CLAIM_REQUESTED",
    "CLAIMED",
    "ACCEPTED",
    "RESOURCE_RESERVED",
    "ACTIVE",
    "COMPLETED",
    "DEADLOCK",
    "RELEASED",
    "EXPIRED",
    "REJECTED",
    "AWAITING_RESOURCES",
}

VALID_DECISIONS = {
    "ACCEPT_ALL_AS_PARALLEL",
    "ACCEPT_ONE_AND_QUEUE_OTHERS",
    "REJECT_WITH_REASON",
    "DEFER",
}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _parse_time(value: str) -> datetime:
    text = _text(value)
    if not text:
        raise ValueError("timestamp is required")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _now_iso() -> str:
    return _iso(datetime.now(timezone.utc))


def _list_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, Mapping)):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _capability_names(agent: Mapping[str, Any]) -> set[str]:
    raw = agent.get("capabilities", [])
    names: set[str] = set()
    if isinstance(raw, str):
        names.add(raw.strip().lower())
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, Mapping):
                for key in ("name", "category", "capability_id"):
                    value = _text(item.get(key)).lower()
                    if value:
                        names.add(value)
            else:
                value = _text(item).lower()
                if value:
                    names.add(value)
    return names


def _required_capabilities(prospect: Mapping[str, Any]) -> set[str]:
    return {x.lower() for x in _list_strings(prospect.get("required_capabilities"))}


def _resource_requirements(prospect: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = prospect.get("required_resources", prospect.get("requirements", []))
    if isinstance(raw, Mapping):
        raw = raw.get("resources", [])
    if not isinstance(raw, list):
        return []
    return [dict(x) for x in raw if isinstance(x, Mapping)]


def _resource_verified(resource: Mapping[str, Any]) -> bool:
    verification = resource.get("verification", {})
    return isinstance(verification, Mapping) and _text(
        verification.get("verification_status")
    ).lower() == "verified"


def _resource_available(resource: Mapping[str, Any]) -> bool:
    status = _text(resource.get("status")).lower()
    return status in {"available", "verified", "active"} and _resource_verified(resource)


def _resource_capacity(resource: Mapping[str, Any]) -> float:
    availability = resource.get("availability", {})
    if not isinstance(availability, Mapping):
        return 0.0
    try:
        return max(0.0, float(availability.get("available_capacity", 0)))
    except (TypeError, ValueError):
        return 0.0


def _matches_requirement(resource: Mapping[str, Any], requirement: Mapping[str, Any]) -> bool:
    if not _resource_available(resource):
        return False
    req_type = _text(requirement.get("resource_type")).lower()
    res_type = _text(resource.get("resource_type")).lower()
    if req_type and req_type != res_type:
        return False

    req_unit = _text(requirement.get("unit")).lower()
    availability = resource.get("availability", {})
    res_unit = _text(availability.get("capacity_unit") if isinstance(availability, Mapping) else "").lower()
    if req_unit and res_unit and req_unit != res_unit:
        return False

    req_cap = _text(requirement.get("capability")).lower()
    if req_cap:
        caps = set()
        raw_caps = resource.get("capabilities", [])
        if isinstance(raw_caps, list):
            for item in raw_caps:
                if isinstance(item, Mapping):
                    for key in ("name", "category", "capability_id"):
                        value = _text(item.get(key)).lower()
                        if value:
                            caps.add(value)
                else:
                    caps.add(_text(item).lower())
        if req_cap not in caps:
            return False
    return True


@dataclass(frozen=True)
class Claim:
    claim_id: str
    question_id: str
    agent_id: str
    prospect_id: str
    created_at: str
    expires_at: str
    status: str
    requested_capabilities: list[str]
    requested_resources: list[dict[str, Any]]
    method_intent: str
    parent_claim_id: Optional[str]
    provenance: dict[str, Any]
    estimated_compute: str = "0"
    estimated_duration: str = ""
    requested_resource_window: str = ""
    preferred_execution_mode: str = ""
    agent_confidence: str = ""
    agent_notes: str = ""


@dataclass(frozen=True)
class ResourceReservation:
    reservation_id: str
    claim_id: str
    question_id: str
    agent_id: str
    resource_ids: list[str]
    allocations: dict[str, float]
    created_at: str
    status: str
    released_at: Optional[str] = None
    reason: str = ""


@dataclass(frozen=True)
class ClaimEvent:
    event_id: str
    event_type: str
    claim_id: str
    question_id: str
    agent_id: str
    timestamp: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ClaimResult:
    claim_id: str
    accepted: bool
    status: str
    reason: str
    question_terminated: bool
    resource_reservation_id: Optional[str]


@dataclass(frozen=True)
class ClaimEngineResult:
    engine_id: str
    claims: list[dict[str, Any]]
    reservations: list[dict[str, Any]]
    events: list[dict[str, Any]]
    question_status: dict[str, str]
    invariants: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TaskClaimEngine:
    """Deterministic executable claim lifecycle."""

    def __init__(
        self,
        *,
        engine_id: str,
        questions: Iterable[Mapping[str, Any]],
        prospects: Iterable[Mapping[str, Any]],
        agents: Iterable[Mapping[str, Any]],
        resources: Iterable[Mapping[str, Any]],
        now: str,
    ) -> None:
        self.engine_id = engine_id
        self.questions = {str(q["question_id"]): dict(q) for q in questions if _text(q.get("question_id"))}
        self._initial_question_status = {qid: _text(q.get("status", "unresolved")).lower() or "unresolved" for qid, q in self.questions.items()}
        self.prospects = {str(p["prospect_id"]): dict(p) for p in prospects if _text(p.get("prospect_id"))}
        self.agents = {str(a["agent_id"]): dict(a) for a in agents if _text(a.get("agent_id"))}
        self.resources = {str(r["resource_id"]): dict(r) for r in resources if _text(r.get("resource_id"))}
        self.claims: dict[str, Claim] = {}
        self.reservations: dict[str, ResourceReservation] = {}
        self.events: list[ClaimEvent] = []
        self._event_seq = 0
        self._reservation_seq = 0
        self.now = _parse_time(now)

    def _event(self, event_type: str, claim: Claim, data: Optional[Mapping[str, Any]] = None) -> None:
        self._event_seq += 1
        event = ClaimEvent(
            event_id=f"CE-{self._event_seq:04d}",
            event_type=event_type,
            claim_id=claim.claim_id,
            question_id=claim.question_id,
            agent_id=claim.agent_id,
            timestamp=_iso(self.now),
            data=dict(data or {}),
        )
        self.events.append(event)

    def create_claim(
        self,
        *,
        claim_id: str,
        question_id: str,
        agent_id: str,
        prospect_id: str,
        expires_at: str,
        method_intent: str,
        parent_claim_id: Optional[str] = None,
        provenance: Optional[Mapping[str, Any]] = None,
        requested_capabilities: Optional[Sequence[str]] = None,
        requested_resources: Optional[Sequence[Mapping[str, Any]]] = None,
        estimated_compute: Any = "0",
        estimated_duration: str = "",
        requested_resource_window: str = "",
        preferred_execution_mode: str = "",
        agent_confidence: Any = "",
        agent_notes: str = "",
    ) -> Claim:
        if claim_id in self.claims:
            raise ValueError(f"claim already exists: {claim_id}")
        question = self.questions.get(question_id)
        prospect = self.prospects.get(prospect_id)
        agent = self.agents.get(agent_id)
        if question is None:
            raise ValueError("question_id does not reference a known question")
        if prospect is None:
            raise ValueError("prospect_id does not reference a known Task Prospect")
        if agent is None:
            raise ValueError("agent_id does not reference a known agent")
        if _text(prospect.get("question_id")) != question_id:
            raise ValueError("prospect does not reference the claimed question")
        if _text(prospect.get("agent_id")) != agent_id:
            raise ValueError("prospect is not addressed to the claiming agent")
        expires = _parse_time(expires_at)
        if expires <= _parse_time(_iso(self.now)):
            raise ValueError("expires_at must be later than current engine time")
        if not _text(method_intent):
            raise ValueError("method_intent is required")

        claim = Claim(
            claim_id=claim_id,
            question_id=question_id,
            agent_id=agent_id,
            prospect_id=prospect_id,
            created_at=_iso(self.now),
            expires_at=_iso(expires),
            status="CLAIM_REQUESTED",
            requested_capabilities=list(requested_capabilities or prospect.get("required_capabilities", [])),
            requested_resources=[dict(x) for x in (requested_resources or prospect.get("required_resources", [])) if isinstance(x, Mapping)],
            method_intent=method_intent,
            parent_claim_id=parent_claim_id,
            provenance={
                **dict(provenance or {}),
                "source_prospect_id": prospect_id,
                "question_id": question_id,
                "agent_id": agent_id,
            },
            estimated_compute=str(estimated_compute),
            estimated_duration=estimated_duration,
            requested_resource_window=requested_resource_window,
            preferred_execution_mode=preferred_execution_mode,
            agent_confidence=str(agent_confidence),
            agent_notes=agent_notes,
        )
        self.claims[claim_id] = claim
        self._event("claim_requested", claim)
        return claim

    def _replace_claim(self, claim_id: str, status: str, *, data: Optional[Mapping[str, Any]] = None) -> Claim:
        old = self.claims[claim_id]
        new = Claim(**{**asdict(old), "status": status})
        self.claims[claim_id] = new
        self._event(status.lower(), new, data=data)
        return new

    def _validate_admission(self, claim: Claim) -> list[str]:
        reasons: list[str] = []
        question = self.questions.get(claim.question_id)
        prospect = self.prospects.get(claim.prospect_id)
        agent = self.agents.get(claim.agent_id)
        if question is None:
            reasons.append("unknown question")
            return reasons
        if prospect is None:
            reasons.append("unknown prospect")
        if agent is None:
            reasons.append("unknown agent")
        question_status = _text(question.get("status", "unresolved")).lower()
        if question_status in TERMINAL_QUESTION_STATES:
            reasons.append(f"terminal question state: {question_status}")
        if _parse_time(claim.expires_at) <= self.now:
            reasons.append("claim expired before admission")
        if not claim.provenance.get("source_prospect_id"):
            reasons.append("missing provenance source_prospect_id")
        if not claim.provenance.get("question_id") or not claim.provenance.get("agent_id"):
            reasons.append("incomplete provenance")
        if prospect is not None:
            if _text(prospect.get("question_id")) != claim.question_id:
                reasons.append("prospect/question mismatch")
            if _text(prospect.get("agent_id")) != claim.agent_id:
                reasons.append("prospect/agent mismatch")
        if agent is not None:
            missing = sorted({c.lower() for c in claim.requested_capabilities} - _capability_names(agent))
            if missing:
                reasons.append("missing capability: " + ", ".join(missing))
        return reasons

    def admit_claim(self, claim_id: str) -> ClaimResult:
        claim = self.claims[claim_id]
        if claim.status != "CLAIM_REQUESTED":
            return ClaimResult(claim_id, False, claim.status, "claim is not awaiting admission", False, None)
        reasons = self._validate_admission(claim)
        if reasons:
            updated = self._replace_claim(claim_id, "REJECTED", data={"reason": "; ".join(reasons)})
            return ClaimResult(claim_id, False, updated.status, "; ".join(reasons), False, None)
        updated = self._replace_claim(claim_id, "CLAIMED")
        updated = self._replace_claim(claim_id, "ACCEPTED")
        return ClaimResult(claim_id, True, updated.status, "claim structurally accepted", False, None)

    def arbitrate_claims(self, claim_ids: Sequence[str], *, policy: str) -> list[ClaimResult]:
        if policy not in VALID_DECISIONS:
            raise ValueError(f"unsupported arbitration policy: {policy}")
        question_groups: dict[str, list[str]] = {}
        for claim_id in claim_ids:
            if claim_id not in self.claims:
                raise ValueError(f"unknown claim: {claim_id}")
            question_groups.setdefault(self.claims[claim_id].question_id, []).append(claim_id)

        results: list[ClaimResult] = []
        for _, ids in sorted(question_groups.items()):
            # Preserve all competing claims in event/history; policy determines
            # which claims advance.
            ordered = sorted(ids)
            if policy == "ACCEPT_ALL_AS_PARALLEL":
                for claim_id in ordered:
                    results.append(self.admit_claim(claim_id))
            elif policy == "ACCEPT_ONE_AND_QUEUE_OTHERS":
                first = True
                for claim_id in ordered:
                    if first:
                        results.append(self.admit_claim(claim_id))
                        first = False
                    else:
                        claim = self.claims[claim_id]
                        if claim.status == "CLAIM_REQUESTED":
                            claim = self.claims[claim_id]
                            self._event(
                                "claim_queued",
                                claim,
                                data={"queued_behind_claim": ordered[0]},
                            )
                            results.append(
                                ClaimResult(claim_id, False, claim.status, "queued behind accepted competing claim", False, None)
                            )
                        else:
                            results.append(
                                ClaimResult(claim_id, False, claim.status, "claim not requestable", False, None)
                            )
            elif policy == "REJECT_WITH_REASON":
                for claim_id in ordered:
                    claim = self.claims[claim_id]
                    if claim.status == "CLAIM_REQUESTED":
                        updated = self._replace_claim(
                            claim_id,
                            "REJECTED",
                            data={"reason": "concurrent-claim policy rejected this claim"},
                        )
                        results.append(ClaimResult(claim_id, False, updated.status, "rejected by policy", False, None))
            else:  # DEFER
                for claim_id in ordered:
                    claim = self.claims[claim_id]
                    results.append(ClaimResult(claim_id, False, claim.status, "deferred by policy", False, None))
        return results

    def reserve_resources(self, claim_id: str) -> ClaimResult:
        claim = self.claims[claim_id]
        if claim.status != "ACCEPTED":
            return ClaimResult(claim_id, False, claim.status, "only ACCEPTED claims can reserve resources", False, None)

        allocations: dict[str, float] = {}
        working_capacity = {rid: _resource_capacity(resource) for rid, resource in self.resources.items()}
        requirements = claim.requested_resources

        # Plan the complete reservation against a shadow capacity map first.
        # Nothing is mutated until every requirement is satisfiable.
        for requirement in requirements:
            try:
                needed = max(0.0, float(requirement.get("quantity", 0)))
            except (TypeError, ValueError):
                needed = 0.0
            if needed <= 0:
                continue
            remaining = needed
            for rid in sorted(self.resources):
                resource = self.resources[rid]
                if not _matches_requirement(resource, requirement):
                    continue
                available = max(0.0, working_capacity.get(rid, 0.0))
                if available <= 0:
                    continue
                take = min(available, remaining)
                if take > 0:
                    allocations[rid] = allocations.get(rid, 0.0) + take
                    working_capacity[rid] = available - take
                    remaining -= take
                if remaining <= 1e-12:
                    break
            if remaining > 1e-12:
                self._replace_claim(
                    claim_id,
                    "AWAITING_RESOURCES",
                    data={
                        "reason": "verified resources unavailable",
                        "partial_allocations": dict(allocations),
                    },
                )
                return ClaimResult(claim_id, False, "AWAITING_RESOURCES", "verified resources unavailable", False, None)

        # Commit the planned reservation.
        for rid, amount in allocations.items():
            resource = self.resources[rid]
            availability = dict(resource.get("availability", {}))
            availability["available_capacity"] = str(max(0.0, _resource_capacity(resource) - amount))
            resource["availability"] = availability

        self._reservation_seq += 1
        reservation_id = f"RES-{self._reservation_seq:04d}"
        reservation = ResourceReservation(
            reservation_id=reservation_id,
            claim_id=claim_id,
            question_id=claim.question_id,
            agent_id=claim.agent_id,
            resource_ids=sorted(allocations),
            allocations=dict(allocations),
            created_at=_iso(self.now),
            status="RESERVED",
        )
        self.reservations[reservation_id] = reservation
        self._replace_claim(claim_id, "RESOURCE_RESERVED", data={"reservation_id": reservation_id, "allocations": dict(allocations)})
        return ClaimResult(claim_id, True, "RESOURCE_RESERVED", "resources reserved", False, reservation_id)

    def activate(self, claim_id: str) -> ClaimResult:
        claim = self.claims[claim_id]
        if claim.status != "RESOURCE_RESERVED":
            return ClaimResult(claim_id, False, claim.status, "claim requires RESOURCE_RESERVED before ACTIVE", False, None)
        updated = self._replace_claim(claim_id, "ACTIVE")
        return ClaimResult(claim_id, True, updated.status, "claim active", False, self._reservation_for_claim(claim_id))

    def complete(self, claim_id: str, *, outcome: str = "completed") -> ClaimResult:
        return self._end_active(claim_id, "COMPLETED", outcome)

    def deadlock(self, claim_id: str, *, deadlock_ref: str) -> ClaimResult:
        if not _text(deadlock_ref):
            raise ValueError("deadlock_ref is required")
        return self._end_active(claim_id, "DEADLOCK", deadlock_ref)

    def _end_active(self, claim_id: str, status: str, payload: str) -> ClaimResult:
        claim = self.claims[claim_id]
        if claim.status != "ACTIVE":
            return ClaimResult(claim_id, False, claim.status, "claim is not ACTIVE", False, self._reservation_for_claim(claim_id))
        reservation_id = self._reservation_for_claim(claim_id)
        self._replace_claim(claim_id, status, data={"outcome": payload})
        if reservation_id:
            self._release_reservation(reservation_id, reason=f"claim ended: {status.lower()}")
        return ClaimResult(claim_id, True, status, payload, False, reservation_id)

    def release(self, claim_id: str, *, reason: str) -> ClaimResult:
        if not _text(reason):
            raise ValueError("release reason is required")
        claim = self.claims[claim_id]
        if claim.status not in {"CLAIM_REQUESTED", "CLAIMED", "ACCEPTED", "RESOURCE_RESERVED", "ACTIVE", "AWAITING_RESOURCES"}:
            return ClaimResult(claim_id, False, claim.status, "claim is not releasable", False, self._reservation_for_claim(claim_id))
        reservation_id = self._reservation_for_claim(claim_id)
        updated = self._replace_claim(claim_id, "RELEASED", data={"reason": reason})
        if reservation_id:
            self._release_reservation(reservation_id, reason=reason)
        # Intentionally does NOT mutate the question into a terminal state.
        return ClaimResult(claim_id, True, updated.status, reason, False, reservation_id)

    def expire(self, claim_id: str) -> ClaimResult:
        claim = self.claims[claim_id]
        if _parse_time(claim.expires_at) > self.now:
            return ClaimResult(claim_id, False, claim.status, "claim has not expired", False, self._reservation_for_claim(claim_id))
        if claim.status in {"COMPLETED", "DEADLOCK", "RELEASED", "EXPIRED", "REJECTED"}:
            return ClaimResult(claim_id, False, claim.status, "claim already terminal", False, self._reservation_for_claim(claim_id))
        reservation_id = self._reservation_for_claim(claim_id)
        updated = self._replace_claim(claim_id, "EXPIRED", data={"reason": "lease expired"})
        if reservation_id:
            self._release_reservation(reservation_id, reason="claim expired")
        return ClaimResult(claim_id, True, updated.status, "claim expired", False, reservation_id)

    def handoff(self, claim_id: str, *, new_claim_id: str, new_agent_id: str, new_prospect_id: str, expires_at: str, method_intent: str) -> Claim:
        old = self.claims[claim_id]
        if old.status not in {"CLAIMED", "ACCEPTED", "RESOURCE_RESERVED", "ACTIVE", "RELEASED", "DEADLOCK", "EXPIRED"}:
            raise ValueError("claim state does not permit handoff")
        new_claim = self.create_claim(
            claim_id=new_claim_id,
            question_id=old.question_id,
            agent_id=new_agent_id,
            prospect_id=new_prospect_id,
            expires_at=expires_at,
            method_intent=method_intent,
            parent_claim_id=old.claim_id,
            provenance={
                "handoff_from_claim_id": old.claim_id,
                "handoff_reason": "continuation transfer",
            },
            requested_capabilities=old.requested_capabilities,
            requested_resources=old.requested_resources,
            estimated_compute=old.estimated_compute,
            estimated_duration=old.estimated_duration,
            requested_resource_window=old.requested_resource_window,
            preferred_execution_mode=old.preferred_execution_mode,
            agent_confidence=old.agent_confidence,
            agent_notes=old.agent_notes,
        )
        self._event("claim_handoff_created", new_claim, data={"parent_claim_id": old.claim_id})
        if old.status not in {"RELEASED", "DEADLOCK", "EXPIRED"}:
            self.release(old.claim_id, reason="handoff to successor claim")
        return new_claim

    def agent_loss(self, agent_id: str, *, reason: str = "agent unavailable") -> int:
        affected = 0
        for claim_id, claim in list(self.claims.items()):
            if claim.agent_id != agent_id:
                continue
            if claim.status in {"CLAIMED", "ACCEPTED", "RESOURCE_RESERVED", "ACTIVE", "AWAITING_RESOURCES"}:
                self.release(claim_id, reason=f"agent loss: {reason}")
                affected += 1
        return affected

    def _reservation_for_claim(self, claim_id: str) -> Optional[str]:
        for rid, reservation in self.reservations.items():
            if reservation.claim_id == claim_id and reservation.status == "RESERVED":
                return rid
        return None

    def _release_reservation(self, reservation_id: str, *, reason: str) -> None:
        reservation = self.reservations[reservation_id]
        if reservation.status == "RELEASED":
            return
        for rid, amount in reservation.allocations.items():
            resource = self.resources.get(rid)
            if resource is None:
                continue
            availability = dict(resource.get("availability", {}))
            current = _resource_capacity(resource)
            availability["available_capacity"] = str(current + float(amount))
            resource["availability"] = availability

        released = ResourceReservation(
            **{
                **asdict(reservation),
                "status": "RELEASED",
                "released_at": _iso(self.now),
                "reason": reason,
            }
        )
        self.reservations[reservation_id] = released
        claim = self.claims[reservation.claim_id]
        self._event("resource_released", claim, data={"reservation_id": reservation_id, "reason": reason})

    def question_frontier_status(self, question_id: str) -> str:
        question = self.questions.get(question_id)
        if question is None:
            raise ValueError("unknown question")
        return _text(question.get("status", "unresolved")).lower() or "unresolved"

    def result(self) -> ClaimEngineResult:
        claim_values = [asdict(x) for x in self.claims.values()]
        reservation_values = [asdict(x) for x in self.reservations.values()]
        event_values = [asdict(x) for x in self.events]

        question_terminated = {
            qid: _text(q.get("status", "unresolved")).lower() in TERMINAL_QUESTION_STATES
            for qid, q in self.questions.items()
        }

        invariants = {
            "discovery_not_claim": all(bool(c["prospect_id"]) for c in claim_values),
            "claim_not_execution": all(c["status"] != "ACTIVE" or self._has_reservation(c["claim_id"]) for c in claim_values),
            "claim_not_payment": all("payment" not in c["status"].lower() for c in claim_values),
            "rejected_does_not_terminate_question": all(
                self._initial_question_status.get(c["question_id"], "unresolved") in TERMINAL_QUESTION_STATES
                or not question_terminated.get(c["question_id"], False)
                for c in claim_values if c["status"] == "REJECTED"
            ),
            "expired_does_not_terminate_question": all(
                self._initial_question_status.get(c["question_id"], "unresolved") in TERMINAL_QUESTION_STATES
                or not question_terminated.get(c["question_id"], False)
                for c in claim_values if c["status"] == "EXPIRED"
            ),
            "released_does_not_terminate_question": all(
                self._initial_question_status.get(c["question_id"], "unresolved") in TERMINAL_QUESTION_STATES
                or not question_terminated.get(c["question_id"], False)
                for c in claim_values if c["status"] == "RELEASED"
            ),
            "reservation_requires_acceptance": all(
                any(c["claim_id"] == r["claim_id"] and c["status"] in {"RESOURCE_RESERVED", "ACTIVE", "COMPLETED", "DEADLOCK", "RELEASED", "EXPIRED"} for c in claim_values)
                for r in reservation_values
            ),
            "reservation_has_allocations": all(
                bool(r.get("allocations")) == bool(r.get("resource_ids"))
                for r in reservation_values
            ),
            "handoff_provenance": all(
                c["parent_claim_id"] is None or bool(c["provenance"].get("handoff_from_claim_id"))
                for c in claim_values
            ),
            "events_append_only": [e["event_id"] for e in event_values] == [f"CE-{i:04d}" for i in range(1, len(event_values) + 1)],
        }
        return ClaimEngineResult(
            engine_id=self.engine_id,
            claims=claim_values,
            reservations=reservation_values,
            events=event_values,
            question_status={qid: _text(q.get("status", "unresolved")).lower() or "unresolved" for qid, q in self.questions.items()},
            invariants=invariants,
        )

    def _has_reservation(self, claim_id: str) -> bool:
        return any(r.claim_id == claim_id for r in self.reservations.values())


def demo() -> dict[str, Any]:
    now = "2026-09-21T20:00:00Z"
    questions = [
        {"question_id": "Q-CLAIM-001", "status": "unresolved"},
        {"question_id": "Q-CLAIM-002", "status": "resolved"},
    ]
    prospects = [
        {
            "prospect_id": "TP-Q-CLAIM-001-agent-A",
            "question_id": "Q-CLAIM-001",
            "agent_id": "agent-A",
            "required_capabilities": ["simulation"],
            "required_resources": [{"resource_type": "gpu", "quantity": 50, "unit": "GPU-hours"}],
        },
        {
            "prospect_id": "TP-Q-CLAIM-001-agent-B",
            "question_id": "Q-CLAIM-001",
            "agent_id": "agent-B",
            "required_capabilities": ["simulation"],
            "required_resources": [{"resource_type": "gpu", "quantity": 50, "unit": "GPU-hours"}],
        },
        {
            "prospect_id": "TP-Q-CLAIM-001-agent-C",
            "question_id": "Q-CLAIM-001",
            "agent_id": "agent-C",
            "required_capabilities": ["analysis"],
            "required_resources": [{"resource_type": "gpu", "quantity": 500, "unit": "GPU-hours"}],
        },
        {
            "prospect_id": "TP-Q-CLAIM-002-agent-A",
            "question_id": "Q-CLAIM-002",
            "agent_id": "agent-A",
            "required_capabilities": ["simulation"],
            "required_resources": [],
        },
    ]
    agents = [
        {"agent_id": "agent-A", "capabilities": ["simulation"]},
        {"agent_id": "agent-B", "capabilities": ["simulation"]},
        {"agent_id": "agent-C", "capabilities": ["analysis"]},
    ]
    resources = [
        {
            "resource_id": "gpu-01",
            "resource_type": "gpu",
            "status": "available",
            "verification": {"verification_status": "verified"},
            "availability": {"available_capacity": 100, "capacity_unit": "GPU-hours"},
            "capabilities": [{"name": "gpu", "category": "compute"}],
        },
    ]

    engine = TaskClaimEngine(
        engine_id="CLAIM-DEMO-001",
        questions=questions,
        prospects=prospects,
        agents=agents,
        resources=resources,
        now=now,
    )

    c1 = engine.create_claim(
        claim_id="CL-001",
        question_id="Q-CLAIM-001",
        agent_id="agent-A",
        prospect_id="TP-Q-CLAIM-001-agent-A",
        expires_at="2026-09-21T21:00:00Z",
        method_intent="independent simulation branch",
        provenance={"discovery_event": "DISC-001"},
    )
    c2 = engine.create_claim(
        claim_id="CL-002",
        question_id="Q-CLAIM-001",
        agent_id="agent-B",
        prospect_id="TP-Q-CLAIM-001-agent-B",
        expires_at="2026-09-21T21:30:00Z",
        method_intent="independent simulation branch B",
        provenance={"discovery_event": "DISC-002"},
    )
    c3 = engine.create_claim(
        claim_id="CL-003",
        question_id="Q-CLAIM-001",
        agent_id="agent-C",
        prospect_id="TP-Q-CLAIM-001-agent-C",
        expires_at="2026-09-21T21:15:00Z",
        method_intent="alternative analytical branch",
        provenance={"discovery_event": "DISC-003"},
    )
    rejected_terminal = engine.create_claim(
        claim_id="CL-004",
        question_id="Q-CLAIM-002",
        agent_id="agent-A",
        prospect_id="TP-Q-CLAIM-002-agent-A",
        expires_at="2026-09-21T21:00:00Z",
        method_intent="attempt resolved question",
        provenance={"discovery_event": "DISC-004"},
    )

    results = engine.arbitrate_claims([c1.claim_id, c2.claim_id, c3.claim_id], policy="ACCEPT_ALL_AS_PARALLEL")
    assert all(r.accepted for r in results)

    reserve_a = engine.reserve_resources("CL-001")
    assert reserve_a.accepted and reserve_a.status == "RESOURCE_RESERVED"
    activate_a = engine.activate("CL-001")
    assert activate_a.accepted and activate_a.status == "ACTIVE"
    deadlock_a = engine.deadlock("CL-001", deadlock_ref="deadlock-001")
    assert deadlock_a.accepted and deadlock_a.status == "DEADLOCK"

    release_b = engine.release("CL-002", reason="agent voluntarily deferred participation")
    assert release_b.accepted and release_b.status == "RELEASED"

    engine.now = _parse_time("2026-09-21T21:45:00Z")
    expired_c = engine.expire("CL-003")
    assert expired_c.accepted and expired_c.status == "EXPIRED"

    terminal_result = engine.admit_claim("CL-004")
    assert not terminal_result.accepted and terminal_result.status == "REJECTED"
    assert engine.question_frontier_status("Q-CLAIM-002") == "resolved"

    # Handoff from the deadlocked branch to a fresh agent/prospect.
    handoff_prospect = {
        "prospect_id": "TP-Q-CLAIM-001-agent-B2",
        "question_id": "Q-CLAIM-001",
        "agent_id": "agent-B",
        "required_capabilities": ["simulation"],
        "required_resources": [],
    }
    engine.prospects[handoff_prospect["prospect_id"]] = handoff_prospect
    new_claim = engine.handoff(
        "CL-001",
        new_claim_id="CL-005",
        new_agent_id="agent-B",
        new_prospect_id=handoff_prospect["prospect_id"],
        expires_at="2026-09-21T22:30:00Z",
        method_intent="continue from preserved deadlock",
    )
    assert new_claim.parent_claim_id == "CL-001"
    assert new_claim.provenance["handoff_from_claim_id"] == "CL-001"

    data = engine.result().to_dict()
    assert all(data["invariants"].values()), data["invariants"]
    assert data["question_status"]["Q-CLAIM-001"] == "unresolved"
    assert data["question_status"]["Q-CLAIM-002"] == "resolved"
    assert any(c["status"] == "DEADLOCK" for c in data["claims"])
    assert any(c["status"] == "RELEASED" for c in data["claims"])
    assert any(c["status"] == "EXPIRED" for c in data["claims"])
    assert any(c["parent_claim_id"] == "CL-001" for c in data["claims"])
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run deterministic claim-engine demo")
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
        print("UFCPS Task Claim Engine v1")
        print("Claims:", len(result["claims"]))
        print("Reservations:", len(result["reservations"]))
        print("Events:", len(result["events"]))
        print("Question statuses:", result["question_status"])
        print("All invariants:", all(result["invariants"].values()))
        for key, value in result["invariants"].items():
            print(f"- {key}: {'PASS' if value else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
