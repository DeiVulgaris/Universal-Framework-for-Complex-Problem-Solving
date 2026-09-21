
"""UFCPS Level 2 — Unified Economic Stress Suite v1.

Purpose
-------
Run a deterministic, integration-level stress suite for the UFCPS economic
layer without executing real payments or issuing real assets.

The suite combines:
- cost-anchored issuance control and the "first miners" / early extraction case;
- mass verified resource inflow versus capital-only inflow;
- energy deficit and demand-crash market scenarios;
- repetitive recursion pressure versus information-producing recursion;
- repeated Deadlock submissions / Deadlock spam control;
- provider reward settlement on RC and crypto rails;
- universal author royalty and zero internal protocol fee/spread invariants.

This file is a test/orchestration layer. It does not replace:
- EmissionController;
- EconomicIncentiveEngine;
- Economic Simulator;
- ProviderRewardEngine.

It also does not execute blockchain, banking, or payment-provider actions.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable


# Support both intended repository layout (swarm/*.py) and the current
# workspace layout where some latest v1 modules may temporarily live at root.
REPO_ROOT = Path(__file__).resolve().parents[1]
SWARM_DIR = Path(__file__).resolve().parent
for candidate in (str(SWARM_DIR), str(REPO_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from economic_incentive_engine_v1 import EconomicIncentiveEngine
from payment_router_v1 import AUTHOR_ROYALTY_RATE
from economic_simulator_v1 import reference_simulation_model, simulate
from emission_controller_v1 import AnnualCost, EmissionController
from provider_reward_v1 import ProviderRewardEngine


@dataclass(frozen=True)
class TestResult:
    name: str
    passed: bool
    summary: str
    observations: dict[str, Any]


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe(v) for v in value]
    return value


def _run(name: str, fn: Callable[[], tuple[bool, str, dict[str, Any]]]) -> TestResult:
    try:
        passed, summary, observations = fn()
        return TestResult(
            name=name,
            passed=bool(passed),
            summary=str(summary),
            observations=_safe(observations),
        )
    except Exception as exc:  # deterministic test harness should expose failures
        return TestResult(
            name=name,
            passed=False,
            summary=f"exception: {type(exc).__name__}: {exc}",
            observations={},
        )


def test_first_miners() -> tuple[bool, str, dict[str, Any]]:
    """Ensure early participants cannot extract the annual ceiling at once."""
    controller = EmissionController(release_shape="linear")
    cost = AnnualCost(
        year=2026,
        equipment=10000,
        energy=3000,
        maintenance=1000,
        network=500,
        storage=250,
        verification=250,
    )
    projection = controller.project_next_year(
        cost,
        target_year=2027,
        multipliers={
            "equipment": "1.05",
            "energy": "1.10",
            "maintenance": "1.05",
            "network": "1.03",
            "storage": "1.04",
            "verification": "1.05",
        },
    )
    budget = controller.build_budget(projection)

    first = controller.approve_issuance(
        budget,
        month=1,
        requested_amount=budget.maximum_total_compensation,
        already_issued=0,
        verified_contribution=budget.maximum_total_compensation,
    )

    # An attacker with enough verified compute still only receives the
    # cumulative release available in month 1.
    first_month_ok = first["approved_amount"] <= budget.monthly_release[0]
    annual_cap_ok = sum(budget.monthly_release, Decimal("0")) <= budget.projected_annual_cost * 11
    profit_cap_ok = budget.maximum_profit <= budget.projected_annual_cost * 10
    progressive_ok = first["approved_amount"] < budget.maximum_total_compensation

    passed = all((first_month_ok, annual_cap_ok, profit_cap_ok, progressive_ok))
    return passed, (
        "month-1 release remains below full annual entitlement"
        if passed else "early issuance cap failed"
    ), {
        "projected_annual_cost": budget.projected_annual_cost,
        "maximum_profit": budget.maximum_profit,
        "maximum_total_compensation": budget.maximum_total_compensation,
        "month_1_release": budget.monthly_release[0],
        "first_month_approved": first["approved_amount"],
    }


def test_mass_gpu_inflow() -> tuple[bool, str, dict[str, Any]]:
    """Verified capacity may alter supply economics; capital alone cannot."""
    engine = EconomicIncentiveEngine()
    influx = engine.assess_resource_inflow(
        current_capacity=100,
        new_verified_capacity=900,
        target_capacity=1000,
        capital_inflow=0,
        current_demand=850,
    )
    capital_only = engine.assess_resource_inflow(
        current_capacity=100,
        new_verified_capacity=0,
        target_capacity=1000,
        capital_inflow=10_000_000,
        current_demand=850,
    )

    passed = (
        influx["issuance_expansion_allowed"] is True
        and influx["capital_without_compute_signal"] is False
        and capital_only["issuance_expansion_allowed"] is False
        and capital_only["capital_without_compute_signal"] is True
    )
    return passed, (
        "verified GPU inflow affects capacity while capital-only inflow cannot mint entitlement"
        if passed else "resource-ingestion control failed"
    ), {
        "verified_inflow_index": influx["resource_inflow_index"],
        "verified_price_multiplier": influx["recommended_compute_price_multiplier"],
        "capital_only_price_multiplier": capital_only["recommended_compute_price_multiplier"],
        "capital_only_issuance_allowed": capital_only["issuance_expansion_allowed"],
    }


def test_energy_deficit() -> tuple[bool, str, dict[str, Any]]:
    """Energy shock must not create non-finite or negative market state."""
    model = reference_simulation_model()
    result = simulate(model, scenario_name="energy_shock", months=12)
    rows = result.months
    finite_ok = all(
        _finite(getattr(row, field))
        for row in rows
        for field in (
            "demand_units",
            "supply_units",
            "compute_price",
            "transaction_volume",
            "currency_issuance",
            "cumulative_supply",
            "liquidity_ratio",
            "volatility_proxy",
            "provider_margin",
        )
    )
    nonnegative_ok = all(
        getattr(row, field) >= 0
        for row in rows
        for field in (
            "demand_units",
            "supply_units",
            "compute_price",
            "transaction_volume",
            "currency_issuance",
            "cumulative_supply",
            "liquidity_ratio",
        )
    )
    invariants_ok = all(row.incentive_invariants_passed for row in rows)
    ceiling = _decimal(result.summary["annual_total_compensation_ceiling"])
    issuance_ok = sum(row.currency_issuance for row in rows) <= float(ceiling)

    passed = all((finite_ok, nonnegative_ok, invariants_ok, issuance_ok))
    return passed, (
        "12-month energy deficit remains numerically and economically bounded"
        if passed else "energy-deficit scenario violated a bound"
    ), {
        "ending_provider_margin": result.summary["average_provider_margin"],
        "total_issuance": result.summary["total_issuance"],
        "annual_ceiling": ceiling,
        "max_volatility_proxy": result.summary["max_volatility_proxy"],
    }


def test_demand_crash() -> tuple[bool, str, dict[str, Any]]:
    """Demand collapse must degrade activity, not break continuity/accounting."""
    model = reference_simulation_model()
    result = simulate(model, scenario_name="crash", months=12)
    rows = result.months
    finite_ok = all(
        _finite(getattr(row, field))
        for row in rows
        for field in ("compute_price", "transaction_volume", "cumulative_supply")
    )
    continuity_ok = all(
        rows[index].cumulative_supply >= rows[index - 1].cumulative_supply
        for index in range(1, len(rows))
    )
    issuance_ok = result.summary["total_issuance"] <= result.summary["annual_total_compensation_ceiling"]
    royal_ok = math.isclose(
        result.summary["total_author_royalty"],
        result.summary["total_transaction_volume"] * float(AUTHOR_ROYALTY_RATE),
        rel_tol=0,
        abs_tol=1e-8,
    )
    passed = all((finite_ok, continuity_ok, issuance_ok, royal_ok))
    return passed, (
        "demand crash reduces economic activity without breaking continuity or royalty accounting"
        if passed else "demand-crash accounting failed"
    ), {
        "ending_compute_price": result.summary["ending_compute_price"],
        "total_transaction_volume": result.summary["total_transaction_volume"],
        "total_issuance": result.summary["total_issuance"],
        "total_author_royalty": result.summary["total_author_royalty"],
    }


def test_recursion_repetition() -> tuple[bool, str, dict[str, Any]]:
    """Low-information repetition should cost more than useful recursion."""
    engine = EconomicIncentiveEngine()
    low = engine.assess_recursion(
        recursion_depth=24,
        repetition_score=0.98,
        new_information_score=0.01,
        unresolved_information_delta=0.02,
        base_step_cost=100,
        c5_valid=True,
    )
    useful = engine.assess_recursion(
        recursion_depth=24,
        repetition_score=0.20,
        new_information_score=0.80,
        unresolved_information_delta=0.20,
        base_step_cost=100,
        c5_valid=True,
    )
    c5_block = engine.assess_recursion(
        recursion_depth=24,
        repetition_score=0.98,
        new_information_score=0.01,
        unresolved_information_delta=0.02,
        base_step_cost=100,
        c5_valid=False,
    )

    sim = simulate(reference_simulation_model(), scenario_name="recursion_stress", months=12)
    base = simulate(reference_simulation_model(), scenario_name="base", months=12)
    sim_cost_ok = sim.summary["average_incentive_recursion_cost"] > base.summary["average_incentive_recursion_cost"]

    passed = (
        low["effective_step_cost"] > useful["effective_step_cost"]
        and c5_block["discretionary_budget_allowed"] is False
        and sim_cost_ok
    )
    return passed, (
        "repetitive recursion is economically differentiated and C5 still blocks discretionary recursion"
        if passed else "recursion stress control failed"
    ), {
        "low_information_cost": low["effective_step_cost"],
        "useful_recursion_cost": useful["effective_step_cost"],
        "c5_discretionary_budget_allowed": c5_block["discretionary_budget_allowed"],
        "sim_average_stress_cost": sim.summary["average_incentive_recursion_cost"],
        "sim_average_base_cost": base.summary["average_incentive_recursion_cost"],
    }


def test_deadlock_spam() -> tuple[bool, str, dict[str, Any]]:
    """Only verified, non-duplicate Deadlock information earns bonus."""
    engine = EconomicIncentiveEngine()
    deadlock = {
        "deadlock_id": "DL-SPAM-001",
        "boundary": 1.0,
        "constraint": 1.0,
        "attempt_trace": 1.0,
        "negative_result": 1.0,
        "evidence": 0.95,
        "substitution": 0.85,
        "reproducibility": 0.90,
    }
    budget = Decimal("1000")
    first = engine.assess_deadlock(deadlock, verified=True, duplicate=False, bonus_budget=budget)
    duplicate_bonuses = [
        engine.assess_deadlock(deadlock, verified=True, duplicate=True, bonus_budget=budget)["indicative_bonus"]
        for _ in range(10)
    ]
    unverified = engine.assess_deadlock(deadlock, verified=False, duplicate=False, bonus_budget=budget)

    duplicate_total = sum(duplicate_bonuses, Decimal("0"))
    passed = (
        first["indicative_bonus"] > 0
        and duplicate_total == 0
        and unverified["indicative_bonus"] == 0
        and first["information_density_score"] > Decimal("0.90")
    )
    return passed, (
        "Deadlock spam produces no repeated informational payout"
        if passed else "Deadlock spam control failed"
    ), {
        "first_density": first["information_density_score"],
        "first_bonus": first["indicative_bonus"],
        "duplicate_count": len(duplicate_bonuses),
        "duplicate_total_bonus": duplicate_total,
        "unverified_bonus": unverified["indicative_bonus"],
    }


def test_provider_reward_rails() -> tuple[bool, str, dict[str, Any]]:
    """Provider reward remains outcome-independent across RC and crypto rails."""
    engine = ProviderRewardEngine(crypto_per_rc="2")
    cost = engine.annual_cost(
        year=2026,
        equipment_annualized=10000,
        energy=3000,
        maintenance=1000,
        network=500,
        storage=250,
        verification=250,
    )
    multipliers = {
        "equipment": "1.05",
        "energy": "1.10",
        "maintenance": "1.05",
        "network": "1.03",
        "storage": "1.04",
        "verification": "1.05",
    }

    rc = engine.approve_and_settle(
        provider_id="provider-stress",
        resource_id="gpu-stress-rc",
        verified_compute=500,
        compute_unit="GPU-hours",
        month=1,
        already_issued_rc=0,
        requested_reward_rc=500,
        reference_cost=cost,
        target_year=2027,
        payout_rail="resource_credits",
        projection_multipliers=multipliers,
    )
    crypto = engine.approve_and_settle(
        provider_id="provider-stress",
        resource_id="gpu-stress-crypto",
        verified_compute=500,
        compute_unit="GPU-hours",
        month=1,
        already_issued_rc=0,
        requested_reward_rc=500,
        reference_cost=cost,
        target_year=2027,
        payout_rail="crypto",
        projection_multipliers=multipliers,
    )

    expected_crypto = rc.approved_reward_rc * Decimal("2")
    rc_royalty_ok = rc.author_royalty == rc.gross_payout * AUTHOR_ROYALTY_RATE
    crypto_royalty_ok = crypto.author_royalty == crypto.gross_payout * AUTHOR_ROYALTY_RATE
    zero_fee_ok = all(
        reward.protocol_fee == 0 and reward.internal_spread == 0
        for reward in (rc, crypto)
    )
    rail_ok = crypto.gross_payout == expected_crypto
    outcome_independence_ok = (
        rc.research_outcome_dependency is False
        and crypto.research_outcome_dependency is False
    )

    passed = all((rc_royalty_ok, crypto_royalty_ok, zero_fee_ok, rail_ok, outcome_independence_ok))
    return passed, (
        "provider continuity reward works on both rails and research outcome is not a payout condition"
        if passed else "provider reward rail/royalty invariant failed"
    ), {
        "rc_status": rc.status,
        "rc_gross": rc.gross_payout,
        "rc_royalty": rc.author_royalty,
        "crypto_status": crypto.status,
        "crypto_gross": crypto.gross_payout,
        "crypto_royalty": crypto.author_royalty,
        "protocol_fee_rc": rc.protocol_fee,
        "protocol_fee_crypto": crypto.protocol_fee,
        "research_outcome_dependency": rc.research_outcome_dependency,
    }


def test_nested_incentive_suite() -> tuple[bool, str, dict[str, Any]]:
    """Run the lower-level incentive integration suite as a regression gate."""
    from economic_simulator_v1 import run_incentive_stress_tests

    result = run_incentive_stress_tests()
    passed = result.get("status") == "PASS" and all(result.get("tests", {}).values())
    return passed, (
        "lower-level incentive suite passes"
        if passed else "lower-level incentive suite reported a failure"
    ), {
        "status": result.get("status"),
        "tests": result.get("tests", {}),
    }


def run_suite() -> dict[str, Any]:
    tests = [
        _run("first_miners_early_extraction", test_first_miners),
        _run("mass_verified_gpu_inflow", test_mass_gpu_inflow),
        _run("energy_deficit", test_energy_deficit),
        _run("demand_crash", test_demand_crash),
        _run("repetitive_recursion", test_recursion_repetition),
        _run("deadlock_spam", test_deadlock_spam),
        _run("provider_reward_rails", test_provider_reward_rails),
        _run("nested_incentive_regression", test_nested_incentive_suite),
    ]

    passed_count = sum(test.passed for test in tests)
    failed_count = len(tests) - passed_count

    return {
        "suite_version": "v1",
        "suite_id": "UFCPS-ECON-STRESS-V1",
        "status": "PASS" if failed_count == 0 else "FAIL",
        "tests_requested": len(tests),
        "tests_passed": passed_count,
        "tests_failed": failed_count,
        "all_passed": failed_count == 0,
        "core_invariants": {
            "author_royalty_rate": str(AUTHOR_ROYALTY_RATE),
            "author_royalty_basis": "every_transaction",
            "internal_protocol_fee": "0",
            "internal_spread": "0",
            "maximum_profit_multiple_of_annual_cost": "10",
            "maximum_total_compensation_multiple_of_annual_cost": "11",
            "verified_contribution_required_for_issuance": True,
            "capital_only_issuance_blocked": True,
            "duplicate_deadlock_bonus_blocked": True,
            "research_outcome_required_for_provider_continuity_reward": False,
        },
        "tests": [asdict(test) for test in tests],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UFCPS unified economic stress suite v1")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_suite()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result["all_passed"] else 1

    print("UFCPS Economic Stress Suite v1")
    print(f"Status: {result['status']}")
    print(f"Tests: {result['tests_passed']}/{result['tests_requested']} passed")
    for test in result["tests"]:
        print(f"{test['name']}: {'PASS' if test['passed'] else 'FAIL'} — {test['summary']}")
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
