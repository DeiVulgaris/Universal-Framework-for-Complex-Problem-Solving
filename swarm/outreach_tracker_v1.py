
"""
UFCPS Level 2 — Outreach Tracker v1

Track stakeholder outreach as process state.

The tracker records:
- contacts;
- proposals;
- responses;
- follow-ups;
- commitments;
- rejection reasons;
- learning signals.

The history is persistent process information. A new agent can reconstruct
the current outreach state without relying on the memory of the previous agent.

This module is deliberately non-invasive:
- it does not send messages;
- it does not make financial commitments;
- it does not infer private preferences;
- it does not rank people by protected or sensitive attributes.

Usage
-----
    python swarm/outreach_tracker_v1.py
    python swarm/outreach_tracker_v1.py --json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


VALID_OUTCOMES = {
    "no_response",
    "interest",
    "information_requested",
    "meeting",
    "proposal_requested",
    "declined",
    "deferred",
    "commitment",
    "other",
}

VALID_STATUSES = {
    "identified",
    "qualified",
    "contacted",
    "engaged",
    "evaluating",
    "proposed",
    "committed",
    "declined",
    "deferred",
    "unresponsive",
    "blocked",
}

VALID_CHANNELS = {
    "email",
    "linkedin",
    "x",
    "website",
    "platform",
    "forum",
    "referral",
    "other",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Interaction:
    interaction_id: str
    stakeholder_id: str
    channel: str
    timestamp: str
    proposal_id: str | None
    outcome: str
    summary: str
    next_action: str | None = None
    follow_up_at: str | None = None
    agent_id: str | None = None
    evidence_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.interaction_id.strip():
            raise ValueError("interaction_id must not be empty.")
        if not self.stakeholder_id.strip():
            raise ValueError("stakeholder_id must not be empty.")
        if self.channel not in VALID_CHANNELS:
            raise ValueError(f"Unsupported channel: {self.channel}")
        if self.outcome not in VALID_OUTCOMES:
            raise ValueError(f"Unsupported outcome: {self.outcome}")


@dataclass
class StakeholderHistory:
    stakeholder_id: str
    status: str = "identified"
    interactions: List[Interaction] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)
    accepted_signals: List[str] = field(default_factory=list)
    commitments: List[Dict[str, Any]] = field(default_factory=list)
    last_interaction_at: str | None = None
    next_action: str | None = None
    next_action_at: str | None = None

    def __post_init__(self) -> None:
        if not self.stakeholder_id.strip():
            raise ValueError("stakeholder_id must not be empty.")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Unsupported stakeholder status: {self.status}")

    def add_interaction(self, interaction: Interaction) -> None:
        if interaction.stakeholder_id != self.stakeholder_id:
            raise ValueError(
                "Interaction stakeholder_id does not match history stakeholder_id."
            )

        self.interactions.append(interaction)
        self.last_interaction_at = interaction.timestamp

        # State transitions are explicit and deterministic.
        transition = {
            "interest": "engaged",
            "information_requested": "engaged",
            "meeting": "engaged",
            "proposal_requested": "evaluating",
            "commitment": "committed",
            "declined": "declined",
            "deferred": "deferred",
            "no_response": "unresponsive",
        }
        if interaction.outcome in transition:
            self.status = transition[interaction.outcome]
        elif interaction.outcome == "other":
            self.status = "contacted"

        self.next_action = interaction.next_action
        self.next_action_at = interaction.follow_up_at

    def record_learning(
        self,
        *,
        accepted_signal: str | None = None,
        rejection_reason: str | None = None,
    ) -> None:
        if accepted_signal:
            signal = accepted_signal.strip()
            if signal and signal not in self.accepted_signals:
                self.accepted_signals.append(signal)

        if rejection_reason:
            reason = rejection_reason.strip()
            if reason and reason not in self.rejection_reasons:
                self.rejection_reasons.append(reason)

    def add_commitment(
        self,
        *,
        commitment_id: str,
        commitment_type: str,
        amount: float | None = None,
        unit: str | None = None,
        notes: str | None = None,
    ) -> None:
        if not commitment_id.strip():
            raise ValueError("commitment_id must not be empty.")
        if amount is not None and amount < 0:
            raise ValueError("commitment amount must be non-negative.")

        self.commitments.append({
            "commitment_id": commitment_id,
            "commitment_type": commitment_type,
            "amount": amount,
            "unit": unit,
            "notes": notes,
            "recorded_at": utc_now(),
        })
        self.status = "committed"


class OutreachTracker:
    """In-memory tracker with deterministic export."""

    def __init__(self) -> None:
        self._records: Dict[str, StakeholderHistory] = {}

    def ensure_stakeholder(
        self,
        stakeholder_id: str,
        *,
        status: str = "identified",
    ) -> StakeholderHistory:
        if stakeholder_id not in self._records:
            self._records[stakeholder_id] = StakeholderHistory(
                stakeholder_id=stakeholder_id,
                status=status,
            )
        return self._records[stakeholder_id]

    def add_interaction(
        self,
        interaction_id: str,
        stakeholder_id: str,
        channel: str,
        outcome: str,
        summary: str,
        *,
        proposal_id: str | None = None,
        next_action: str | None = None,
        follow_up_at: str | None = None,
        agent_id: str | None = None,
        timestamp: str | None = None,
        evidence_refs: Iterable[str] = (),
    ) -> Interaction:
        interaction = Interaction(
            interaction_id=interaction_id,
            stakeholder_id=stakeholder_id,
            channel=channel,
            timestamp=timestamp or utc_now(),
            proposal_id=proposal_id,
            outcome=outcome,
            summary=summary,
            next_action=next_action,
            follow_up_at=follow_up_at,
            agent_id=agent_id,
            evidence_refs=[str(x) for x in evidence_refs],
        )

        record = self.ensure_stakeholder(stakeholder_id)
        record.add_interaction(interaction)
        return interaction

    def add_learning(
        self,
        stakeholder_id: str,
        *,
        accepted_signal: str | None = None,
        rejection_reason: str | None = None,
    ) -> None:
        record = self.ensure_stakeholder(stakeholder_id)
        record.record_learning(
            accepted_signal=accepted_signal,
            rejection_reason=rejection_reason,
        )

    def add_commitment(
        self,
        stakeholder_id: str,
        *,
        commitment_id: str,
        commitment_type: str,
        amount: float | None = None,
        unit: str | None = None,
        notes: str | None = None,
    ) -> None:
        record = self.ensure_stakeholder(stakeholder_id)
        record.add_commitment(
            commitment_id=commitment_id,
            commitment_type=commitment_type,
            amount=amount,
            unit=unit,
            notes=notes,
        )

    def get(self, stakeholder_id: str) -> StakeholderHistory | None:
        return self._records.get(stakeholder_id)

    def export(self) -> Dict[str, Any]:
        return {
            "tracker_version": "v1",
            "generated_at": utc_now(),
            "stakeholders": [
                asdict(record)
                for record in sorted(
                    self._records.values(),
                    key=lambda item: item.stakeholder_id,
                )
            ],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OutreachTracker":
        if payload.get("tracker_version") != "v1":
            raise ValueError("Expected Outreach Tracker v1.")

        tracker = cls()
        stakeholders = payload.get("stakeholders", [])
        if not isinstance(stakeholders, list):
            raise ValueError("stakeholders must be an array.")

        for item in stakeholders:
            if not isinstance(item, Mapping):
                raise ValueError("Each stakeholder record must be an object.")

            record = StakeholderHistory(
                stakeholder_id=str(item.get("stakeholder_id", "")),
                status=str(item.get("status", "identified")),
                rejection_reasons=[
                    str(x) for x in item.get("rejection_reasons", [])
                ],
                accepted_signals=[
                    str(x) for x in item.get("accepted_signals", [])
                ],
                commitments=[
                    dict(x)
                    for x in item.get("commitments", [])
                    if isinstance(x, Mapping)
                ],
                last_interaction_at=item.get("last_interaction_at"),
                next_action=item.get("next_action"),
                next_action_at=item.get("next_action_at"),
            )

            for raw in item.get("interactions", []):
                if not isinstance(raw, Mapping):
                    raise ValueError("Each interaction must be an object.")
                interaction = Interaction(
                    interaction_id=str(raw.get("interaction_id", "")),
                    stakeholder_id=str(raw.get("stakeholder_id", "")),
                    channel=str(raw.get("channel", "")),
                    timestamp=str(raw.get("timestamp", "")),
                    proposal_id=raw.get("proposal_id"),
                    outcome=str(raw.get("outcome", "")),
                    summary=str(raw.get("summary", "")),
                    next_action=raw.get("next_action"),
                    follow_up_at=raw.get("follow_up_at"),
                    agent_id=raw.get("agent_id"),
                    evidence_refs=[
                        str(x) for x in raw.get("evidence_refs", [])
                    ],
                )
                if interaction.stakeholder_id != record.stakeholder_id:
                    raise ValueError("Interaction stakeholder mismatch.")
                record.interactions.append(interaction)

            tracker._records[record.stakeholder_id] = record

        return tracker


def campaign_metrics(tracker: OutreachTracker) -> Dict[str, Any]:
    records = list(tracker._records.values())
    interactions = [
        interaction
        for record in records
        for interaction in record.interactions
    ]

    outcome_counts: Dict[str, int] = {}
    channel_counts: Dict[str, int] = {}
    for interaction in interactions:
        outcome_counts[interaction.outcome] = (
            outcome_counts.get(interaction.outcome, 0) + 1
        )
        channel_counts[interaction.channel] = (
            channel_counts.get(interaction.channel, 0) + 1
        )

    responses = [
        item
        for item in interactions
        if item.outcome != "no_response"
    ]
    qualified = [
        item
        for item in interactions
        if item.outcome in {
            "interest",
            "information_requested",
            "meeting",
            "proposal_requested",
            "commitment",
        }
    ]

    return {
        "stakeholders_tracked": len(records),
        "interactions": len(interactions),
        "responses": len(responses),
        "response_rate": (
            len(responses) / len(interactions)
            if interactions else 0.0
        ),
        "qualified_responses": len(qualified),
        "qualified_response_rate": (
            len(qualified) / len(interactions)
            if interactions else 0.0
        ),
        "commitments": sum(
            1 for record in records if record.commitments
        ),
        "outcome_counts": outcome_counts,
        "channel_counts": channel_counts,
    }


def demo_tracker() -> OutreachTracker:
    tracker = OutreachTracker()

    tracker.add_interaction(
        interaction_id="interaction-001",
        stakeholder_id="stakeholder-demo-001",
        channel="email",
        outcome="information_requested",
        summary="Recipient requested technical evidence and resource requirements.",
        proposal_id="proposal-demo-001",
        next_action="Provide benchmark dossier.",
        agent_id="agent-outreach-001",
        evidence_refs=["benchmark-demo-001"],
    )

    tracker.add_learning(
        "stakeholder-demo-001",
        accepted_signal="Interest increased after receiving concrete compute requirements.",
    )

    tracker.add_interaction(
        interaction_id="interaction-002",
        stakeholder_id="stakeholder-demo-001",
        channel="email",
        outcome="commitment",
        summary="Recipient indicated willingness to provide a staged compute allocation.",
        proposal_id="proposal-demo-001",
        next_action="Start resource verification.",
        agent_id="agent-outreach-001",
    )

    tracker.add_commitment(
        "stakeholder-demo-001",
        commitment_id="commitment-001",
        commitment_type="compute",
        amount=1000,
        unit="GPU-hours",
        notes="Staged allocation subject to verification.",
    )

    tracker.add_interaction(
        interaction_id="interaction-003",
        stakeholder_id="stakeholder-demo-002",
        channel="linkedin",
        outcome="declined",
        summary="Recipient declined because the current project stage was outside its mandate.",
        proposal_id="proposal-demo-002",
        next_action="No further contact until mandate changes.",
        agent_id="agent-outreach-001",
    )

    tracker.add_learning(
        "stakeholder-demo-002",
        rejection_reason="Project stage outside stated mandate.",
    )

    return tracker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="UFCPS Outreach Tracker v1"
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

    tracker = demo_tracker()
    output = tracker.export()
    output["metrics"] = campaign_metrics(tracker)

    # Round-trip persistence test.
    restored = OutreachTracker.from_dict(output)
    assert restored.export()["stakeholders"][0]["stakeholder_id"] == (
        output["stakeholders"][0]["stakeholder_id"]
    )
    assert campaign_metrics(restored)["interactions"] == 3
    assert campaign_metrics(restored)["commitments"] == 1

    if args.as_json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("UFCPS Outreach Tracker v1")
        metrics = output["metrics"]
        print(f"Stakeholders: {metrics['stakeholders_tracked']}")
        print(f"Interactions: {metrics['interactions']}")
        print(f"Response rate: {metrics['response_rate']:.4f}")
        print(f"Qualified responses: {metrics['qualified_responses']}")
        print(f"Commitments: {metrics['commitments']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
