
"""UFCPS Level 2 — Economic Incentive Engine v1.

Pure calculation layer for:
- recursive delegation cost pressure;
- Deadlock information density and indicative bonus;
- external resource inflow;
- economic invariant checks.

It does not issue credits/tokens, execute payments, reserve resources,
or decide research correctness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Any, Mapping


def D(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid numeric value: {value!r}") from exc


def q8(value: Any) -> Decimal:
    return D(value).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)


def clamp(value: Decimal, lo: Decimal = Decimal("0"), hi: Decimal = Decimal("1")) -> Decimal:
    return max(lo, min(hi, value))


class EconomicIncentiveError(ValueError):
    pass


class EconomicIncentiveEngine:
    """Configurable v1 calculation engine."""

    def __init__(
        self,
        *,
        alpha: Any = "0.10",  # depth pressure
        beta: Any = "0.50",   # repetition pressure
        gamma: Any = "0.75",  # information relief
        deadlock_weights: Mapping[str, Any] | None = None,
        resource_price_sensitivity: Any = "0.25",
        price_floor: Any = "0.75",
        price_ceiling: Any = "1.50",
    ) -> None:
        self.alpha = D(alpha)
        self.beta = D(beta)
        self.gamma = D(gamma)
        self.resource_price_sensitivity = D(resource_price_sensitivity)
        self.price_floor = D(price_floor)
        self.price_ceiling = D(price_ceiling)

        if any(x < 0 for x in (
            self.alpha, self.beta, self.gamma,
            self.resource_price_sensitivity,
        )):
            raise EconomicIncentiveError("coefficients cannot be negative")
        if not 0 < self.price_floor <= self.price_ceiling:
            raise EconomicIncentiveError("invalid price bounds")

        weights = {
            "boundary_completeness": D("0.20"),
            "constraint_completeness": D("0.20"),
            "attempt_trace_completeness": D("0.15"),
            "negative_result_quality": D("0.15"),
            "evidence_quality": D("0.10"),
            "substitution_guidance": D("0.10"),
            "reproducibility": D("0.10"),
        }
        if deadlock_weights:
            weights.update({k: D(v) for k, v in deadlock_weights.items()})
        total = sum(weights.values(), Decimal("0"))
        if total <= 0 or any(v < 0 for v in weights.values()):
            raise EconomicIncentiveError("invalid deadlock weights")
        self.deadlock_weights = {k: v / total for k, v in weights.items()}

    # ---------- recursion ----------

    def assess_recursion(
        self,
        *,
        recursion_depth: int,
        repetition_score: Any = "0",
        new_information_score: Any = "0",
        unresolved_information_delta: Any = "0",
        base_step_cost: Any = "1",
        c5_valid: bool = True,
    ) -> dict[str, Any]:
        if recursion_depth < 0:
            raise EconomicIncentiveError("recursion_depth cannot be negative")

        repetition = clamp(D(repetition_score))
        new_info = clamp(D(new_information_score))
        unresolved = clamp(D(unresolved_information_delta))
        base = D(base_step_cost)

        if base < 0:
            raise EconomicIncentiveError("base_step_cost cannot be negative")

        information_relief = clamp(new_info + unresolved)
        recursion_multiplier = Decimal("1") + self.alpha * recursion_depth
        redundancy_multiplier = Decimal("1") + self.beta * repetition

        raw_penalty = recursion_multiplier * redundancy_multiplier
        effective_penalty = max(
            Decimal("0"),
            raw_penalty * (Decimal("1") - self.gamma * information_relief),
        )
        effective_cost = q8(base * effective_penalty)

        if not c5_valid:
            status = "c5_rejected"
        elif repetition >= D("0.80") and information_relief < D("0.20"):
            status = "high_redundancy_pressure"
        elif information_relief >= D("0.60"):
            status = "information_supported_recursion"
        else:
            status = "normal"

        return {
            "recursion_depth": recursion_depth,
            "repetition_score": q8(repetition),
            "new_information_score": q8(new_info),
            "unresolved_information_delta": q8(unresolved),
            "information_relief": q8(information_relief),
            "recursion_multiplier": q8(recursion_multiplier),
            "redundancy_multiplier": q8(redundancy_multiplier),
            "effective_penalty_multiplier": q8(effective_penalty),
            "effective_step_cost": effective_cost,
            "c5_valid": c5_valid,
            "discretionary_budget_allowed": c5_valid,
            "status": status,
        }

    # ---------- Deadlock ----------

    @staticmethod
    def _field(obj: Mapping[str, Any], name: str) -> Decimal:
        value = obj.get(name, 0)
        if isinstance(value, Mapping):
            for key in (
                "score", "completeness", "quality", "coverage",
                "confidence", "value"
            ):
                if key in value:
                    value = value[key]
                    break
        if isinstance(value, bool):
            return D(1 if value else 0)
        try:
            return clamp(D(value))
        except (ValueError, InvalidOperation):
            return D(0)

    @staticmethod
    def fingerprint(deadlock: Mapping[str, Any]) -> str:
        excluded = {
            "deadlock_id", "id", "timestamp",
            "created_at", "updated_at", "event_id", "provenance",
        }
        stable = {
            str(k): v for k, v in deadlock.items()
            if str(k) not in excluded
        }
        payload = json.dumps(
            stable, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), default=str
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    def assess_deadlock(
        self,
        deadlock: Mapping[str, Any],
        *,
        verified: bool,
        duplicate: bool = False,
        bonus_budget: Any = "0",
    ) -> dict[str, Any]:
        values = {
            "boundary_completeness": self._field(deadlock, "boundary_completeness")
                or self._field(deadlock, "boundary"),
            "constraint_completeness": self._field(deadlock, "constraint_completeness")
                or self._field(deadlock, "constraint")
                or self._field(deadlock, "constraints"),
            "attempt_trace_completeness": self._field(deadlock, "attempt_trace_completeness")
                or self._field(deadlock, "attempt_trace")
                or self._field(deadlock, "attempts"),
            "negative_result_quality": self._field(deadlock, "negative_result_quality")
                or self._field(deadlock, "negative_result"),
            "evidence_quality": self._field(deadlock, "evidence_quality")
                or self._field(deadlock, "evidence"),
            "substitution_guidance": self._field(deadlock, "substitution_guidance")
                or self._field(deadlock, "substitution"),
            "reproducibility": self._field(deadlock, "reproducibility"),
        }
        dis = clamp(sum(
            self.deadlock_weights[name] * values[name]
            for name in values
        ))
        budget = D(bonus_budget)
        if budget < 0:
            raise EconomicIncentiveError("bonus_budget cannot be negative")

        if not verified:
            bonus = D(0)
            status = "unverified"
        elif duplicate:
            bonus = D(0)
            status = "duplicate"
        elif dis == 0:
            bonus = D(0)
            status = "verified_but_low_information"
        else:
            bonus = q8(budget * dis)
            status = "verified_information_resource"

        deadlock_id = str(
            deadlock.get("deadlock_id")
            or deadlock.get("id")
            or self.fingerprint(deadlock)[:16]
        )
        result = {
            "deadlock_id": deadlock_id,
            **{k: q8(v) for k, v in values.items()},
            "information_density_score": q8(dis),
            "bonus_budget": q8(budget),
            "indicative_bonus": bonus,
            "verified": verified,
            "duplicate": duplicate,
            "status": status,
        }
        return result

    # ---------- external resources ----------

    def assess_resource_inflow(
        self,
        *,
        current_capacity: Any,
        new_verified_capacity: Any,
        target_capacity: Any,
        capital_inflow: Any = "0",
        current_demand: Any = "0",
    ) -> dict[str, Any]:
        current = D(current_capacity)
        new = D(new_verified_capacity)
        target = D(target_capacity)
        capital = D(capital_inflow)
        demand = D(current_demand)

        for name, value in {
            "current_capacity": current,
            "new_verified_capacity": new,
            "target_capacity": target,
            "capital_inflow": capital,
            "current_demand": demand,
        }.items():
            if value < 0:
                raise EconomicIncentiveError(f"{name} cannot be negative")

        inflow_index = q8(new / target) if target > 0 else D(0)
        after = current + new
        demand_pressure = clamp(demand / after) if after > 0 else D(0)
        supply_relief = clamp(inflow_index)

        price_pressure = demand_pressure - (
            supply_relief * self.resource_price_sensitivity
        )
        price_multiplier = clamp(
            D(1) + self.resource_price_sensitivity * price_pressure,
            self.price_floor,
            self.price_ceiling,
        )

        capital_only = capital > 0 and new == 0

        return {
            "current_capacity": q8(current),
            "new_verified_capacity": q8(new),
            "target_capacity": q8(target),
            "resource_inflow_index": inflow_index,
            "capacity_growth_rate": q8(new / current) if current > 0 else inflow_index,
            "capital_inflow": q8(capital),
            "capital_without_compute_signal": capital_only,
            "recommended_compute_price_multiplier": q8(price_multiplier),
            "issuance_expansion_allowed": new > 0,
            "status": (
                "capital_inflow_without_compute"
                if capital_only else
                "verified_resource_inflow"
                if new > 0 else
                "no_new_verified_capacity"
            ),
        }

    # ---------- invariants ----------

    @staticmethod
    def check_invariants(
        *,
        projected_annual_cost: Any,
        annual_profit: Any,
        annual_total_compensation: Any,
        author_royalty_rate: Any,
        internal_conversion_fee: Any,
        internal_spread: Any,
        resource_inflow: Mapping[str, Any],
        recursion: Mapping[str, Any] | None = None,
        deadlock: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        cost = D(projected_annual_cost)
        profit = D(annual_profit)
        total = D(annual_total_compensation)
        royalty = D(author_royalty_rate)
        fee = D(internal_conversion_fee)
        spread = D(internal_spread)

        checks = {
            "maximum_profit_le_10x_annual_cost": profit <= cost * 10,
            "maximum_total_compensation_le_11x_annual_cost": total <= cost * 11,
            "author_royalty_is_0_001_percent": royalty == D("0.00001"),
            "internal_crypto_rc_fee_is_zero": fee == 0,
            "internal_crypto_rc_spread_is_zero": spread == 0,
        }

        # Capital alone does not authorize expansion.
        if resource_inflow.get("capital_without_compute_signal"):
            checks["capital_only_does_not_expand_issuance"] = (
                resource_inflow.get("issuance_expansion_allowed") is False
            )

        if recursion is not None:
            checks["c5_controls_recursive_discretion"] = (
                recursion.get("discretionary_budget_allowed")
                == recursion.get("c5_valid")
            )

        if deadlock is not None:
            checks["unverified_deadlock_zero_bonus"] = (
                deadlock.get("verified") or D(deadlock.get("indicative_bonus", 0)) == 0
            )
            checks["duplicate_deadlock_zero_bonus"] = (
                not deadlock.get("duplicate")
                or D(deadlock.get("indicative_bonus", 0)) == 0
            )

        violations = [k for k, v in checks.items() if not v]
        return {
            "checks": checks,
            "all_passed": not violations,
            "violations": violations,
        }

    # ---------- combined ----------

    def evaluate(
        self,
        *,
        transition: Mapping[str, Any],
        deadlock: Mapping[str, Any] | None,
        resource_state: Mapping[str, Any],
        economic_state: Mapping[str, Any],
    ) -> dict[str, Any]:
        recursion = self.assess_recursion(
            recursion_depth=int(transition.get("recursion_depth", 0)),
            repetition_score=transition.get("repetition_score", 0),
            new_information_score=transition.get("new_information_score", 0),
            unresolved_information_delta=transition.get(
                "unresolved_information_delta", 0
            ),
            base_step_cost=transition.get("base_step_cost", 1),
            c5_valid=bool(transition.get("c5_valid", True)),
        )
        deadlock_result = (
            self.assess_deadlock(
                deadlock,
                verified=bool(deadlock.get("verified", False)),
                duplicate=bool(deadlock.get("duplicate", False)),
                bonus_budget=economic_state.get("deadlock_bonus_budget", 0),
            )
            if deadlock is not None else None
        )
        resource_result = self.assess_resource_inflow(
            current_capacity=resource_state.get("current_capacity", 0),
            new_verified_capacity=resource_state.get("new_verified_capacity", 0),
            target_capacity=resource_state.get("target_capacity", 0),
            capital_inflow=resource_state.get("capital_inflow", 0),
            current_demand=resource_state.get("current_demand", 0),
        )
        invariants = self.check_invariants(
            projected_annual_cost=economic_state.get("projected_annual_cost", 0),
            annual_profit=economic_state.get("annual_profit", 0),
            annual_total_compensation=economic_state.get(
                "annual_total_compensation", 0
            ),
            author_royalty_rate=economic_state.get(
                "author_royalty_rate", "0.00001"
            ),
            internal_conversion_fee=economic_state.get(
                "internal_conversion_fee", 0
            ),
            internal_spread=economic_state.get("internal_spread", 0),
            resource_inflow=resource_result,
            recursion=recursion,
            deadlock=deadlock_result,
        )
        return {
            "engine_version": "v1",
            "recursion": recursion,
            "deadlock": deadlock_result,
            "resource_inflow": resource_result,
            "invariants": invariants,
            "authority": {
                "can_issue": False,
                "can_pay": False,
                "can_reserve": False,
                "can_decide_research_correctness": False,
            },
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
    engine = EconomicIncentiveEngine()

    low_info = engine.assess_recursion(
        recursion_depth=8,
        repetition_score="0.90",
        new_information_score="0.05",
        unresolved_information_delta="0.05",
        base_step_cost="10",
        c5_valid=True,
    )
    high_info = engine.assess_recursion(
        recursion_depth=8,
        repetition_score="0.20",
        new_information_score="0.70",
        unresolved_information_delta="0.20",
        base_step_cost="10",
        c5_valid=True,
    )
    assert low_info["effective_step_cost"] > high_info["effective_step_cost"]

    c5_rejected = engine.assess_recursion(
        recursion_depth=4,
        repetition_score="0.5",
        new_information_score="0.1",
        base_step_cost="10",
        c5_valid=False,
    )
    assert not c5_rejected["discretionary_budget_allowed"]

    low_deadlock = engine.assess_deadlock(
        {"deadlock_id": "DL-LOW", "boundary": 0.2, "constraint": 0.2},
        verified=True,
        bonus_budget="1000",
    )
    rich_deadlock = engine.assess_deadlock(
        {
            "deadlock_id": "DL-HIGH",
            "boundary": 1.0,
            "constraint": 1.0,
            "attempt_trace": 1.0,
            "negative_result": 1.0,
            "evidence": 0.9,
            "substitution": 0.8,
            "reproducibility": 0.9,
        },
        verified=True,
        bonus_budget="1000",
    )
    duplicate = engine.assess_deadlock(
        {"deadlock_id": "DL-DUP", "boundary": 1.0, "constraint": 1.0},
        verified=True,
        duplicate=True,
        bonus_budget="1000",
    )
    assert rich_deadlock["information_density_score"] > low_deadlock["information_density_score"]
    assert rich_deadlock["indicative_bonus"] > low_deadlock["indicative_bonus"]
    assert duplicate["indicative_bonus"] == 0

    inflow = engine.assess_resource_inflow(
        current_capacity="100",
        new_verified_capacity="50",
        target_capacity="500",
        current_demand="300",
    )
    capital_only = engine.assess_resource_inflow(
        current_capacity="100",
        new_verified_capacity="0",
        target_capacity="500",
        capital_inflow="100000",
        current_demand="300",
    )
    assert inflow["issuance_expansion_allowed"]
    assert capital_only["capital_without_compute_signal"]
    assert not capital_only["issuance_expansion_allowed"]

    invariant = engine.check_invariants(
        projected_annual_cost="10000",
        annual_profit="100000",
        annual_total_compensation="110000",
        author_royalty_rate="0.00001",
        internal_conversion_fee="0",
        internal_spread="0",
        resource_inflow=capital_only,
        recursion=high_info,
        deadlock=rich_deadlock,
    )
    assert invariant["all_passed"]

    return safe({
        "status": "PASS",
        "recursion": {
            "low_information_cost": low_info["effective_step_cost"],
            "high_information_cost": high_info["effective_step_cost"],
            "c5_rejected_discretionary_budget": c5_rejected["discretionary_budget_allowed"],
        },
        "deadlock": {
            "low_information_density": low_deadlock["information_density_score"],
            "rich_information_density": rich_deadlock["information_density_score"],
            "low_bonus": low_deadlock["indicative_bonus"],
            "rich_bonus": rich_deadlock["indicative_bonus"],
            "duplicate_bonus": duplicate["indicative_bonus"],
        },
        "resources": {
            "inflow_index": inflow["resource_inflow_index"],
            "price_multiplier": inflow["recommended_compute_price_multiplier"],
            "capital_only_issuance": capital_only["issuance_expansion_allowed"],
        },
        "invariants": invariant,
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if args.demo:
        result = demo()
        print(json.dumps(result if args.as_json else safe(result), ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
