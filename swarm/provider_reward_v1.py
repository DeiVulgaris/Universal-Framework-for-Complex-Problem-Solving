
"""
UFCPS Level 2 — Provider Reward v1

Calculates a resource-provider reward from VERIFIED compute.

Architecture:
    verified compute
        -> annual cost anchor
        -> EmissionController release limit
        -> provider reward
        -> PaymentRouter-style settlement
        -> RC or crypto

Core semantics:
- reward compensates verified provision of process continuity;
- research outcome is NOT required for compute reward;
- no reward is generated from an unverified resource claim;
- the annual economic model caps profit at 10x projected annual cost;
- total compensation is capped at 11x projected annual cost;
- release is progressive rather than front-loaded by default;
- author royalty is 0.001% of EVERY payout transaction;
- internal crypto <-> RC conversion has zero protocol fee and zero spread;
- RC and crypto are optional payout rails.

Reference implementation only. It does not send money or perform blockchain operations.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from pathlib import Path
from typing import Any, Optional

from emission_controller_v1 import AnnualCost, EmissionController
from payment_router_v1 import AUTHOR_ROYALTY_RATE


def D(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid numeric value: {value!r}") from exc


def q8(value: Any) -> Decimal:
    return D(value).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)


class ProviderRewardError(ValueError):
    pass


@dataclass(frozen=True)
class ProviderReward:
    reward_id: str
    provider_id: str
    resource_id: str
    verified_compute: Decimal
    compute_unit: str
    approved_reward_rc: Decimal
    payout_rail: str
    gross_payout: Decimal
    author_royalty: Decimal
    protocol_fee: Decimal
    internal_spread: Decimal
    provider_net_payout: Decimal
    status: str
    research_outcome_dependency: bool
    continuity_basis: str
    metadata: dict[str, Any]


class ProviderRewardEngine:
    """Provider reward calculation layer."""

    def __init__(
        self,
        *,
        emission_controller: Optional[EmissionController] = None,
        crypto_per_rc: Decimal | str = "1.0",
    ) -> None:
        self.controller = emission_controller or EmissionController(
            release_shape="linear"
        )
        self.crypto_per_rc = D(crypto_per_rc)
        if self.crypto_per_rc <= 0:
            raise ProviderRewardError("crypto_per_rc must be > 0")

    @staticmethod
    def annual_cost(
        *,
        year: int,
        equipment_annualized: Any,
        energy: Any,
        maintenance: Any,
        network: Any = "0",
        storage: Any = "0",
        verification: Any = "0",
    ) -> AnnualCost:
        cost = AnnualCost(
            year=year,
            equipment=equipment_annualized,
            energy=energy,
            maintenance=maintenance,
            network=network,
            storage=storage,
            verification=verification,
        )
        if cost.total <= 0:
            raise ProviderRewardError("annual cost must be > 0")
        return cost

    def projected_budget(
        self,
        *,
        reference_cost: AnnualCost,
        target_year: int,
        projection_multipliers: Optional[
            dict[str, Decimal | str | int | float]
        ] = None,
    ):
        projection = self.controller.project_next_year(
            reference_cost,
            target_year=target_year,
            multipliers=projection_multipliers,
        )
        return projection, self.controller.build_budget(projection)

    def _rail_amount(self, reward_rc: Decimal, rail: str) -> Decimal:
        if reward_rc < 0:
            raise ProviderRewardError("reward cannot be negative")

        if rail == "resource_credits":
            return q8(reward_rc)

        if rail == "crypto":
            return q8(reward_rc * self.crypto_per_rc)

        raise ProviderRewardError(
            "payout_rail must be resource_credits or crypto"
        )

    @staticmethod
    def _settle_payout(
        *,
        rail: str,
        gross: Decimal,
    ) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        """
        Return:
            gross, author royalty, protocol fee, internal spread, net

        Python tuple is intentionally explicit through this method's contract.
        """
        if gross <= 0:
            raise ProviderRewardError("gross payout must be > 0")

        royalty = q8(gross * AUTHOR_ROYALTY_RATE)
        protocol_fee = Decimal("0")
        spread = Decimal("0")
        net = q8(gross - royalty)
        return gross, royalty, protocol_fee, spread, net

    def approve_and_settle(
        self,
        *,
        provider_id: str,
        resource_id: str,
        verified_compute: Any,
        compute_unit: str,
        month: int,
        already_issued_rc: Any,
        requested_reward_rc: Any,
        reference_cost: AnnualCost,
        target_year: int,
        payout_rail: str = "resource_credits",
        c5_valid: bool = True,
        projection_multipliers: Optional[
            dict[str, Decimal | str | int | float]
        ] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ProviderReward:
        if not provider_id.strip():
            raise ProviderRewardError("provider_id is required")
        if not resource_id.strip():
            raise ProviderRewardError("resource_id is required")
        if not compute_unit.strip():
            raise ProviderRewardError("compute_unit is required")

        compute = D(verified_compute)
        requested = D(requested_reward_rc)
        already = D(already_issued_rc)

        if compute <= 0:
            raise ProviderRewardError("verified_compute must be > 0")
        if requested <= 0:
            raise ProviderRewardError("requested_reward_rc must be > 0")
        if already < 0:
            raise ProviderRewardError("already_issued_rc cannot be negative")

        projection, budget = self.projected_budget(
            reference_cost=reference_cost,
            target_year=target_year,
            projection_multipliers=projection_multipliers,
        )

        approved = self.controller.approve_issuance(
            budget,
            month=month,
            requested_amount=requested,
            already_issued=already,
            verified_contribution=compute,
            reward_rate=requested / compute,
        )

        approved_rc = q8(approved["approved_amount"])

        if not c5_valid:
            # Economic engine/controller does not replace C5.
            # A caller marked the process step as outside the allowed recursion
            # boundary, so discretionary provider reward is blocked.
            approved_rc = Decimal("0")
            status = "rejected_c5"
        elif approved_rc <= 0:
            status = "rejected"
        elif approved_rc < requested:
            status = "partially_approved"
        else:
            status = "approved"

        if approved_rc <= 0:
            return ProviderReward(
                reward_id=f"reward-{provider_id}-{resource_id}-{month}",
                provider_id=provider_id,
                resource_id=resource_id,
                verified_compute=q8(compute),
                compute_unit=compute_unit,
                approved_reward_rc=Decimal("0"),
                payout_rail=payout_rail,
                gross_payout=Decimal("0"),
                author_royalty=Decimal("0"),
                protocol_fee=Decimal("0"),
                internal_spread=Decimal("0"),
                provider_net_payout=Decimal("0"),
                status=status,
                research_outcome_dependency=False,
                continuity_basis="verified process continuity contribution",
                metadata={
                    **(metadata or {}),
                    "emission_approval": approved,
                },
            )

        gross = self._rail_amount(approved_rc, payout_rail)
        _, royalty, protocol_fee, spread, net = self._settle_payout(
            rail=payout_rail,
            gross=gross,
        )

        return ProviderReward(
            reward_id=f"reward-{provider_id}-{resource_id}-{month}",
            provider_id=provider_id,
            resource_id=resource_id,
            verified_compute=q8(compute),
            compute_unit=compute_unit,
            approved_reward_rc=approved_rc,
            payout_rail=payout_rail,
            gross_payout=gross,
            author_royalty=royalty,
            protocol_fee=protocol_fee,
            internal_spread=spread,
            provider_net_payout=net,
            status=status,
            research_outcome_dependency=False,
            continuity_basis="verified process continuity contribution",
            metadata={
                **(metadata or {}),
                "emission_approval": approved,
                "reference_year": reference_cost.year,
                "target_year": target_year,
                "projected_annual_cost": budget.projected_annual_cost,
                "maximum_profit": budget.maximum_profit,
                "maximum_total_compensation": (
                    budget.maximum_total_compensation
                ),
            },
        )

    def settlement_projection(
        self,
        *,
        reward: ProviderReward,
    ) -> dict[str, Any]:
        """Machine-readable settlement summary without executing it."""
        return {
            "reward_id": reward.reward_id,
            "provider_id": reward.provider_id,
            "resource_id": reward.resource_id,
            "rail": reward.payout_rail,
            "gross": reward.gross_payout,
            "author_royalty": reward.author_royalty,
            "protocol_fee": reward.protocol_fee,
            "internal_spread": reward.internal_spread,
            "provider_net": reward.provider_net_payout,
            "execution": "not_executed_reference_only",
        }


def safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [safe(v) for v in value]
    return value


def demo() -> dict[str, Any]:
    engine = ProviderRewardEngine(crypto_per_rc="2.0")

    reference_cost = engine.annual_cost(
        year=2026,
        equipment_annualized="10000",
        energy="3000",
        maintenance="1000",
        network="500",
        storage="250",
        verification="250",
    )

    multipliers = {
        "equipment": "1.05",
        "energy": "1.10",
        "maintenance": "1.05",
        "network": "1.03",
        "storage": "1.04",
        "verification": "1.05",
    }

    rc_reward = engine.approve_and_settle(
        provider_id="participant-001",
        resource_id="gpu-001",
        verified_compute="100",
        compute_unit="verified_compute_unit",
        month=1,
        already_issued_rc="0",
        requested_reward_rc="50",
        reference_cost=reference_cost,
        target_year=2027,
        payout_rail="resource_credits",
        projection_multipliers=multipliers,
    )

    crypto_reward = engine.approve_and_settle(
        provider_id="participant-002",
        resource_id="gpu-002",
        verified_compute="100",
        compute_unit="verified_compute_unit",
        month=1,
        already_issued_rc="0",
        requested_reward_rc="50",
        reference_cost=reference_cost,
        target_year=2027,
        payout_rail="crypto",
        projection_multipliers=multipliers,
    )

    c5_blocked = engine.approve_and_settle(
        provider_id="participant-003",
        resource_id="gpu-003",
        verified_compute="100",
        compute_unit="verified_compute_unit",
        month=1,
        already_issued_rc="0",
        requested_reward_rc="50",
        reference_cost=reference_cost,
        target_year=2027,
        payout_rail="resource_credits",
        c5_valid=False,
        projection_multipliers=multipliers,
    )

    assert rc_reward.approved_reward_rc == Decimal("50.00000000")
    assert rc_reward.research_outcome_dependency is False
    assert rc_reward.author_royalty == Decimal("0.00050000")
    assert rc_reward.protocol_fee == Decimal("0")
    assert rc_reward.internal_spread == Decimal("0")

    assert crypto_reward.gross_payout == Decimal("100.00000000")
    assert crypto_reward.author_royalty == Decimal("0.00100000")
    assert crypto_reward.provider_net_payout == Decimal("99.99900000")

    assert c5_blocked.approved_reward_rc == Decimal("0")
    assert c5_blocked.status == "rejected_c5"

    return safe({
        "status": "PASS",
        "annual_cost_2026": reference_cost.total,
        "rewards": {
            "rc": asdict(rc_reward),
            "crypto": asdict(crypto_reward),
            "c5_blocked": asdict(c5_blocked),
        },
        "policy": {
            "author_royalty_rate": AUTHOR_ROYALTY_RATE,
            "crypto_rc_internal_fee": Decimal("0"),
            "crypto_rc_internal_spread": Decimal("0"),
            "research_outcome_dependency": False,
        },
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if args.demo:
        result = demo()
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("UFCPS Provider Reward v1")
            print("Status: PASS")
            print("RC reward:", result["rewards"]["rc"]["provider_net_payout"], "RC net")
            print("Crypto reward:", result["rewards"]["crypto"]["provider_net_payout"], "crypto net")
            print("C5 block:", result["rewards"]["c5_blocked"]["status"])
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
