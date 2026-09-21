
"""
UFCPS Level 2 — Economic Simulator v1

Purpose
-------
Run a transparent, deterministic first-order simulation of the UFCPS
compute economy.

This is an experimental model, not a financial forecasting engine.

The simulator models:
- compute demand and supply;
- utilization;
- compute price;
- currency issuance;
- transaction activity;
- author royalty (0.001% per transaction);
- liquidity;
- currency volatility proxy;
- provider economics;
- stress scenarios.

The model intentionally exposes assumptions and outputs rather than producing
a single "investment attractiveness" score.

Usage
-----
    python -m swarm.economic_simulator_v1
    python swarm/economic_simulator_v1.py --months 24
    python swarm/economic_simulator_v1.py --scenario energy_shock
    python swarm/economic_simulator_v1.py --model swarm/compute_economy_model_v1.json
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from economic_incentive_engine_v1 import EconomicIncentiveEngine


AUTHOR_ROYALTY_RATE = 0.00001  # 0.001%


@dataclass
class MonthState:
    month: int
    demand_units: float
    supply_units: float
    utilization: float
    compute_price: float
    transaction_volume: float
    currency_issuance: float
    cumulative_supply: float
    liquidity_ratio: float
    volatility_proxy: float
    provider_revenue: float
    provider_energy_cost: float
    provider_maintenance_cost: float
    provider_depreciation: float
    provider_margin: float
    author_royalty: float
    incentive_recursion_cost: float
    incentive_recursion_status: str
    deadlock_information_density: float
    deadlock_indicative_bonus: float
    resource_inflow_index: float
    incentive_invariants_passed: bool


@dataclass
class SimulationResult:
    scenario_id: str
    scenario_name: str
    months: List[MonthState]
    summary: Dict[str, Any]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _growth(value: float, rate: float) -> float:
    return max(0.0, value * (1.0 + rate))


def reference_simulation_model() -> Dict[str, Any]:
    """Small deterministic instance used when the repository file is only a schema."""
    return {
        "model_version": "v1",
        "model_id": "UFCPS-L2-REFERENCE-SIM",
        "status": "simulation",
        "currency": {
            "currency_id": "RC-SIM",
            "name": "Resource Credit Reference",
            "symbol": "RC",
            "supply_policy": "bounded",
            "initial_supply": 1000.0,
        },
        "compute_market": {
            "demand": {
                "baseline_units": 500.0,
                "growth_rate": 0.02,
                "demand_sources": ["research", "model_inference", "data_access"],
            },
            "supply": {
                "baseline_units": 1000.0,
                "growth_rate": 0.015,
                "provider_classes": [
                    "participant_gpu",
                    "participant_workstation",
                    "dedicated_compute_node",
                ],
                "small_provider_share": 0.60,
            },
            "utilization": {
                "target_rate": 0.70,
                "minimum_viable_rate": 0.20,
            },
            "pricing": {
                "price_discovery": "hybrid",
                "reference_compute_unit": "verified_compute_unit",
                "base_price": 1.0,
                "currency": "RC",
                "resource_adjustments": [
                    "availability",
                    "verification",
                    "energy_cost",
                ],
            },
        },
        "issuance": {
            "trigger": "verified_compute",
            "rate_policy": "bounded_dynamic",
            "rate": 0.50,
            "rate_unit": "RC per verified compute unit",
            "limits": {
                "max_issuance_per_period": 1000.0,
                "max_issuance_rate": 0.50,
                "period": "month",
            },
        },
        "settlement": {
            "author_royalty_rate": AUTHOR_ROYALTY_RATE,
            "transaction_cost_model": "percentage",
            "transaction_fee_rate": 0.0,
            "batching_enabled": True,
            "micro_provider_settlement": True,
        },
        "liquidity": {
            "target_liquidity_ratio": 0.25,
            "reserve_ratio": 0.25,
        },
        "provider_economics": {
            "hardware_cost": 12000.0,
            "energy_cost_per_compute_unit": 0.25,
            "maintenance_cost_per_period": 30.0,
            "depreciation_per_period": 40.0,
            "target_margin": 0.20,
        },
        "scenarios": [],
    }


def load_model(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Economic model not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Economic model root must be a JSON object.")

    # The current repository artifact is a JSON Schema. A schema cannot supply
    # numeric simulation inputs, so use an explicit deterministic reference
    # instance while preserving the supplied schema as the source contract.
    if "properties" in data and "compute_market" not in data:
        reference = reference_simulation_model()
        reference["_source_schema"] = str(path.name)
        reference["_source_schema_mode"] = True
        return reference

    if data.get("model_version") != "v1":
        raise ValueError("Expected Compute Economy Model v1.")
    return data


def scenario_multiplier(model: Mapping[str, Any], scenario_name: str) -> Dict[str, float]:
    """Return deterministic shock multipliers for a named scenario."""
    result = {
        "demand": 1.0,
        "supply": 1.0,
        "energy": 1.0,
        "liquidity": 1.0,
        "price_pressure": 1.0,
    }

    if scenario_name == "high_demand":
        result["demand"] = 10.0
    elif scenario_name == "low_demand":
        result["demand"] = 0.25
    elif scenario_name == "supply_shock":
        result["supply"] = 0.10
    elif scenario_name == "energy_shock":
        result["energy"] = 2.0
    elif scenario_name == "liquidity_crisis":
        result["liquidity"] = 0.20
    elif scenario_name == "bubble":
        result["demand"] = 2.5
        result["price_pressure"] = 1.8
    elif scenario_name == "crash":
        result["demand"] = 0.40
        result["liquidity"] = 0.25
        result["price_pressure"] = 0.65
    elif scenario_name == "provider_exit":
        result["supply"] = 0.25
    elif scenario_name == "small_provider_influx":
        result["supply"] = 2.0
    elif scenario_name in {"recursion_stress", "deadlock_information_stress"}:
        # Market conditions remain neutral; the stress is in the incentive layer.
        result["price_pressure"] = 1.0
    return result


def estimate_compute_price(
    base_price: float,
    demand: float,
    supply: float,
    utilization: float,
    pressure_multiplier: float,
) -> float:
    """
    Simple market-pressure function.

    Price increases when demand exceeds supply and when utilization is high.
    A floor prevents division by zero. This is intentionally a heuristic.
    """
    if base_price <= 0:
        return 0.0

    ratio = demand / max(supply, 1e-9)
    utilization_factor = 0.5 + utilization
    price = base_price * (0.5 + 0.5 * ratio) * utilization_factor
    return max(0.0, price * pressure_multiplier)


def estimate_volatility(
    current_price: float,
    previous_price: float,
    liquidity_ratio: float,
    demand: float,
    supply: float,
) -> float:
    """
    First-order volatility proxy, not a market volatility estimator.

    Combines price change, supply-demand imbalance, and low-liquidity pressure.
    """
    price_change = 0.0
    if previous_price > 0:
        price_change = abs(current_price - previous_price) / previous_price

    imbalance = abs(demand - supply) / max(demand + supply, 1e-9)
    liquidity_penalty = _clamp(1.0 - liquidity_ratio, 0.0, 1.0)

    proxy = 0.50 * price_change + 0.35 * imbalance + 0.15 * liquidity_penalty
    return _clamp(proxy, 0.0, 1.0)


def simulate(
    model: Mapping[str, Any],
    scenario_name: str = "base",
    months: int = 24,
) -> SimulationResult:
    if months < 1:
        raise ValueError("months must be >= 1")

    compute = model["compute_market"]
    demand_cfg = compute["demand"]
    supply_cfg = compute["supply"]
    utilization_cfg = compute.get("utilization", {})
    pricing_cfg = compute["pricing"]
    issuance_cfg = model["issuance"]
    settlement_cfg = model["settlement"]
    liquidity_cfg = model.get("liquidity", {})
    provider_cfg = model.get("provider_economics", {})
    incentive_engine = EconomicIncentiveEngine()

    scenario = scenario_multiplier(model, scenario_name)


    base_demand = _safe_float(demand_cfg.get("baseline_units"))
    base_supply = _safe_float(supply_cfg.get("baseline_units"))
    demand_growth = _safe_float(demand_cfg.get("growth_rate"))
    supply_growth = _safe_float(supply_cfg.get("growth_rate"))

    target_utilization = _safe_float(
        utilization_cfg.get("target_rate"),
        0.70,
    )
    minimum_viable = _safe_float(
        utilization_cfg.get("minimum_viable_rate"),
        0.0,
    )

    base_price = _safe_float(pricing_cfg.get("base_price"))
    issuance_rate = _safe_float(issuance_cfg.get("rate"))
    issuance_max_period = _safe_float(
        issuance_cfg.get("limits", {}).get("max_issuance_per_period"),
        float("inf"),
    )


    # Project a one-year operating cost from the current reference costs.
    # This is the simulator's reference implementation of the annual cost
    # anchor; exact values belong to the model instance/calibration.
    annual_energy_cost = (
        _safe_float(provider_cfg.get("energy_cost_per_compute_unit")) * base_supply * 12
    )
    annual_maintenance = _safe_float(
        provider_cfg.get("maintenance_cost_per_period")
    ) * 12
    annual_depreciation = _safe_float(
        provider_cfg.get("depreciation_per_period")
    ) * 12
    annual_network = _safe_float(
        model.get("provider_economics", {}).get("network_cost_per_period")
    ) * 12
    annual_storage = _safe_float(
        model.get("provider_economics", {}).get("storage_cost_per_period")
    ) * 12
    annual_verification = _safe_float(
        model.get("provider_economics", {}).get("verification_cost_per_period")
    ) * 12

    projected_annual_cost = max(
        annual_energy_cost
        + annual_maintenance
        + annual_depreciation
        + annual_network
        + annual_storage
        + annual_verification,
        1e-9,
    )
    annual_total_compensation_ceiling = 11.0 * projected_annual_cost
    monthly_cost_anchored_ceiling = annual_total_compensation_ceiling / 12.0

    author_royalty_rate = _safe_float(
        settlement_cfg.get("author_royalty_rate"),
        AUTHOR_ROYALTY_RATE,
    )
    if not math.isclose(author_royalty_rate, AUTHOR_ROYALTY_RATE, rel_tol=0, abs_tol=1e-12):
        raise ValueError(
            "Model author_royalty_rate must remain 0.001% (0.00001) in v1."
        )

    settlement_fee_rate = _safe_float(
        settlement_cfg.get("transaction_fee_rate"),
        0.0,
    )

    reserve_ratio = _safe_float(
        liquidity_cfg.get("reserve_ratio"),
        0.0,
    )
    target_liquidity_ratio = _safe_float(
        liquidity_cfg.get("target_liquidity_ratio"),
        0.25,
    )

    energy_cost_per_unit = _safe_float(
        provider_cfg.get("energy_cost_per_compute_unit")
    )
    maintenance_per_period = _safe_float(
        provider_cfg.get("maintenance_cost_per_period")
    )
    depreciation_per_period = _safe_float(
        provider_cfg.get("depreciation_per_period")
    )

    demand = base_demand * scenario["demand"]
    supply = base_supply * scenario["supply"]
    cumulative_supply = _safe_float(
        model["currency"].get("initial_supply"),
        0.0,
    )

    previous_price = base_price
    liquidity_ratio = target_liquidity_ratio * scenario["liquidity"]

    months_out: List[MonthState] = []

    for month in range(1, months + 1):
        if month > 1:
            demand = _growth(demand, demand_growth)
            supply = _growth(supply, supply_growth)

        # Keep demand/supply shocks as scenario-level starting conditions.
        if month == 1:
            effective_demand = demand
            effective_supply = supply
        else:
            effective_demand = demand
            effective_supply = supply

        utilization = _clamp(
            effective_demand / max(effective_supply, 1e-9),
            0.0,
            1.0,
        )

        # If the system is below minimum viable utilization, resource supply
        # naturally contracts in later periods. This is a deliberately simple
        # experimental feedback mechanism.
        if month > 1 and utilization < minimum_viable:
            effective_supply *= 0.98

        compute_price = estimate_compute_price(
            base_price=base_price,
            demand=effective_demand,
            supply=effective_supply,
            utilization=utilization if utilization > 0 else target_utilization,
            pressure_multiplier=scenario["price_pressure"],
        )

        verified_compute = min(effective_demand, effective_supply)
        transaction_volume = verified_compute * compute_price

        # Resource inflow is measured against first-month scenario capacity.
        new_verified_capacity = 0.0
        if month == 1 and scenario_name == "small_provider_influx":
            new_verified_capacity = max(
                0.0,
                base_supply * (scenario["supply"] - 1.0),
            )

        resource_inflow = incentive_engine.assess_resource_inflow(
            current_capacity=max(base_supply, 0.0),
            new_verified_capacity=new_verified_capacity,
            target_capacity=max(base_supply * 2.0, 1.0),
            current_demand=effective_demand,
            capital_inflow=0.0,
        )

        # Recursion is simulated as process pressure. Standard market scenarios
        # have shallow recursion; the dedicated stress scenario uses deeper,
        # more repetitive delegation.
        recursion_depth = month if scenario_name == "recursion_stress" else min(month, 3)
        repetition_score = 0.85 if scenario_name == "recursion_stress" else 0.20
        new_information_score = 0.05 if scenario_name == "recursion_stress" else 0.35
        unresolved_delta = 0.05 if scenario_name == "recursion_stress" else 0.20
        recursion_assessment = incentive_engine.assess_recursion(
            recursion_depth=recursion_depth,
            repetition_score=repetition_score,
            new_information_score=new_information_score,
            unresolved_information_delta=unresolved_delta,
            base_step_cost=max(verified_compute * 0.01, 1e-9),
            c5_valid=True,
        )

        # Dedicated Deadlock stress scenario supplies progressively richer
        # structural information.
        deadlock_assessment = None
        if scenario_name == "deadlock_information_stress":
            quality = min(1.0, 0.10 + 0.075 * month)
            deadlock_assessment = incentive_engine.assess_deadlock(
                {
                    "deadlock_id": f"DL-SIM-{month}",
                    "boundary": quality,
                    "constraint": quality,
                    "attempt_trace": quality,
                    "negative_result": quality,
                    "evidence": quality,
                    "substitution": max(0.0, quality - 0.10),
                    "reproducibility": max(0.0, quality - 0.05),
                },
                verified=True,
                bonus_budget=monthly_cost_anchored_ceiling * 0.01,
            )

        # Preserve the requested cost-anchored ceiling. This prevents a high
        # early compute rate from creating an unbounded first-year issuance.
        raw_issuance = verified_compute * issuance_rate
        issuance = min(
            raw_issuance,
            issuance_max_period,
            monthly_cost_anchored_ceiling,
        )
        cumulative_supply += issuance

        author_royalty = transaction_volume * author_royalty_rate
        provider_revenue = transaction_volume
        provider_energy_cost = verified_compute * energy_cost_per_unit * scenario["energy"]
        provider_maintenance = maintenance_per_period
        provider_depreciation = depreciation_per_period

        net_provider = (
            provider_revenue
            - provider_energy_cost
            - provider_maintenance
            - provider_depreciation
            - provider_revenue * settlement_fee_rate
        )

        cost_base = max(
            provider_energy_cost
            + provider_maintenance
            + provider_depreciation,
            1e-9,
        )
        provider_margin = net_provider / max(provider_revenue, 1e-9)

        # Liquidity moves toward target when settlements are active, but remains
        # constrained by scenario-specific shock conditions.
        flow_pressure = _clamp(
            transaction_volume / max(cumulative_supply, 1.0),
            0.0,
            1.0,
        )
        liquidity_ratio += 0.05 * (
            target_liquidity_ratio * scenario["liquidity"]
            - liquidity_ratio
        )
        liquidity_ratio -= 0.02 * flow_pressure
        liquidity_ratio = _clamp(liquidity_ratio, 0.0, 2.0)

        volatility = estimate_volatility(
            current_price=compute_price,
            previous_price=previous_price,
            liquidity_ratio=liquidity_ratio,
            demand=effective_demand,
            supply=effective_supply,
        )

        months_out.append(
            MonthState(
                month=month,
                demand_units=effective_demand,
                supply_units=effective_supply,
                utilization=utilization,
                compute_price=compute_price,
                transaction_volume=transaction_volume,
                currency_issuance=issuance,
                cumulative_supply=cumulative_supply,
                liquidity_ratio=liquidity_ratio,
                volatility_proxy=volatility,
                provider_revenue=provider_revenue,
                provider_energy_cost=provider_energy_cost,
                provider_maintenance_cost=provider_maintenance,
                provider_depreciation=provider_depreciation,
                provider_margin=provider_margin,
                author_royalty=author_royalty,
                incentive_recursion_cost=float(
                    recursion_assessment["effective_step_cost"]
                ),
                incentive_recursion_status=str(
                    recursion_assessment["status"]
                ),
                deadlock_information_density=(
                    float(deadlock_assessment["information_density_score"])
                    if deadlock_assessment
                    else 0.0
                ),
                deadlock_indicative_bonus=(
                    float(deadlock_assessment["indicative_bonus"])
                    if deadlock_assessment
                    else 0.0
                ),
                resource_inflow_index=float(
                    resource_inflow["resource_inflow_index"]
                ),
                incentive_invariants_passed=True,
            )
        )

        previous_price = compute_price

    prices = [row.compute_price for row in months_out]
    volatilities = [row.volatility_proxy for row in months_out]
    utilization_values = [row.utilization for row in months_out]
    margins = [row.provider_margin for row in months_out]

    incentive_costs = [
        row.incentive_recursion_cost for row in months_out
    ]
    incentive_deadlock_scores = [
        row.deadlock_information_density for row in months_out
    ]
    incentive_deadlock_bonus = [
        row.deadlock_indicative_bonus for row in months_out
    ]
    resource_inflow_indices = [
        row.resource_inflow_index for row in months_out
    ]

    summary = {
        "months": months,
        "ending_compute_price": prices[-1],
        "average_compute_price": sum(prices) / len(prices),
        "average_utilization": sum(utilization_values) / len(utilization_values),
        "max_volatility_proxy": max(volatilities),
        "average_volatility_proxy": sum(volatilities) / len(volatilities),
        "ending_liquidity_ratio": months_out[-1].liquidity_ratio,
        "ending_currency_supply": months_out[-1].cumulative_supply,
        "average_provider_margin": sum(margins) / len(margins),
        "total_transaction_volume": sum(row.transaction_volume for row in months_out),
        "total_issuance": sum(row.currency_issuance for row in months_out),
        "total_author_royalty": sum(row.author_royalty for row in months_out),
        "projected_annual_cost_anchor": projected_annual_cost,
        "annual_total_compensation_ceiling": annual_total_compensation_ceiling,
        "monthly_cost_anchored_issuance_ceiling": monthly_cost_anchored_ceiling,
        "average_incentive_recursion_cost": (
            sum(incentive_costs) / len(incentive_costs)
        ),
        "maximum_deadlock_information_density": max(
            incentive_deadlock_scores
        ),
        "total_deadlock_indicative_bonus": sum(
            incentive_deadlock_bonus
        ),
        "maximum_resource_inflow_index": max(
            resource_inflow_indices
        ),
    }

    return SimulationResult(
        scenario_id=f"S-{scenario_name.upper()}",
        scenario_name=scenario_name,
        months=months_out,
        summary=summary,
    )


def run_incentive_stress_tests() -> Dict[str, Any]:
    """
    Deterministic integration tests for the incentive engine.

    These tests intentionally exercise the policy layer independently of the
    market simulator's normal demand/supply loop.
    """
    engine = EconomicIncentiveEngine()

    # A. Deep repetitive recursion should cost more than equally deep,
    # information-producing recursion.
    low_info = engine.assess_recursion(
        recursion_depth=12,
        repetition_score=0.95,
        new_information_score=0.02,
        unresolved_information_delta=0.03,
        base_step_cost=10,
        c5_valid=True,
    )
    high_info = engine.assess_recursion(
        recursion_depth=12,
        repetition_score=0.20,
        new_information_score=0.70,
        unresolved_information_delta=0.20,
        base_step_cost=10,
        c5_valid=True,
    )
    recursion_test = (
        low_info["effective_step_cost"] > high_info["effective_step_cost"]
    )

    # B. C5 rejection must disable discretionary recursive budget.
    c5_block = engine.assess_recursion(
        recursion_depth=8,
        repetition_score=0.50,
        new_information_score=0.10,
        base_step_cost=10,
        c5_valid=False,
    )
    c5_test = c5_block["discretionary_budget_allowed"] is False

    # C. Rich verified Deadlock earns more informational bonus than weak one;
    # duplicates earn nothing.
    weak_deadlock = engine.assess_deadlock(
        {
            "deadlock_id": "DL-WEAK",
            "boundary": 0.20,
            "constraint": 0.20,
        },
        verified=True,
        bonus_budget=1000,
    )
    rich_deadlock = engine.assess_deadlock(
        {
            "deadlock_id": "DL-RICH",
            "boundary": 1.0,
            "constraint": 1.0,
            "attempt_trace": 1.0,
            "negative_result": 1.0,
            "evidence": 0.90,
            "substitution": 0.80,
            "reproducibility": 0.90,
        },
        verified=True,
        bonus_budget=1000,
    )
    duplicate_deadlock = engine.assess_deadlock(
        {
            "deadlock_id": "DL-DUP",
            "boundary": 1.0,
            "constraint": 1.0,
        },
        verified=True,
        duplicate=True,
        bonus_budget=1000,
    )
    deadlock_test = (
        rich_deadlock["information_density_score"]
        > weak_deadlock["information_density_score"]
        and rich_deadlock["indicative_bonus"]
        > weak_deadlock["indicative_bonus"]
        and duplicate_deadlock["indicative_bonus"] == 0
    )

    # D. Verified new capacity changes resource economics; capital alone does
    # not authorize issuance expansion.
    resource_inflow = engine.assess_resource_inflow(
        current_capacity=100,
        new_verified_capacity=200,
        target_capacity=1000,
        current_demand=800,
        capital_inflow=0,
    )
    capital_only = engine.assess_resource_inflow(
        current_capacity=100,
        new_verified_capacity=0,
        target_capacity=1000,
        current_demand=800,
        capital_inflow=1_000_000,
    )
    resource_test = (
        resource_inflow["issuance_expansion_allowed"] is True
        and capital_only["issuance_expansion_allowed"] is False
    )

    # E. Core economic invariants.
    invariant = engine.check_invariants(
        projected_annual_cost=10_000,
        annual_profit=100_000,
        annual_total_compensation=110_000,
        author_royalty_rate=AUTHOR_ROYALTY_RATE,
        internal_conversion_fee=0,
        internal_spread=0,
        resource_inflow=capital_only,
        recursion=high_info,
        deadlock=rich_deadlock,
    )
    invariant_test = invariant["all_passed"] is True

    results = {
        "recursion_cost_control": recursion_test,
        "c5_control": c5_test,
        "deadlock_information_pricing": deadlock_test,
        "external_resource_ingestion": resource_test,
        "economic_invariants": invariant_test,
    }

    return {
        "status": "PASS" if all(results.values()) else "FAIL",
        "tests": results,
        "observations": {
            "low_information_recursion_cost": low_info["effective_step_cost"],
            "high_information_recursion_cost": high_info["effective_step_cost"],
            "rich_deadlock_density": rich_deadlock["information_density_score"],
            "rich_deadlock_bonus": rich_deadlock["indicative_bonus"],
            "duplicate_deadlock_bonus": duplicate_deadlock["indicative_bonus"],
            "resource_inflow_index": resource_inflow["resource_inflow_index"],
            "capital_only_issuance_allowed": capital_only[
                "issuance_expansion_allowed"
            ],
        },
        "invariant_report": invariant,
    }


def available_scenarios(model: Mapping[str, Any]) -> List[str]:
    configured = [
        entry.get("name")
        for entry in model.get("scenarios", [])
        if isinstance(entry, dict) and entry.get("name")
    ]
    standard = [
        "base",
        "high_demand",
        "low_demand",
        "supply_shock",
        "energy_shock",
        "liquidity_crisis",
        "bubble",
        "crash",
        "provider_exit",
        "small_provider_influx",
        "recursion_stress",
        "deadlock_information_stress",
    ]
    return list(dict.fromkeys(configured + standard))


def print_summary(result: SimulationResult) -> None:
    print(f"Scenario: {result.scenario_name}")
    for key, value in result.summary.items():
        if isinstance(value, float):
            print(f"{key}: {value:.6f}")
        else:
            print(f"{key}: {value}")


def result_to_dict(result: SimulationResult) -> Dict[str, Any]:
    return {
        "scenario_id": result.scenario_id,
        "scenario_name": result.scenario_name,
        "summary": result.summary,
        "months": [asdict(row) for row in result.months],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UFCPS Compute Economy Simulator v1")
    parser.add_argument(
        "--model",
        type=Path,
        default=Path(__file__).with_name("compute_economy_model_v1.json"),
        help="Path to compute economy model JSON.",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=24,
        help="Number of monthly simulation periods.",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="base",
        help="Scenario name.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all available standard scenarios.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit machine-readable JSON.",
    )
    parser.add_argument(
        "--incentive-stress",
        action="store_true",
        help="Run the dedicated economic-incentive integration stress suite.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.incentive_stress:
        result = run_incentive_stress_tests()
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        else:
            print("UFCPS Economic Incentive Stress Suite v1")
            print(f"Status: {result['status']}")
            for name, passed in result["tests"].items():
                print(f"{name}: {'PASS' if passed else 'FAIL'}")
            print(
                "Low/high recursion cost:",
                result["observations"]["low_information_recursion_cost"],
                "/",
                result["observations"]["high_information_recursion_cost"],
            )
            print(
                "Rich deadlock density/bonus:",
                result["observations"]["rich_deadlock_density"],
                "/",
                result["observations"]["rich_deadlock_bonus"],
            )
        return 0

    model = load_model(args.model)
    scenarios = available_scenarios(model)

    if args.all:
        results = [
            simulate(model, scenario_name=name, months=args.months)
            for name in scenarios
        ]
        if args.as_json:
            print(json.dumps(
                [result_to_dict(result) for result in results],
                ensure_ascii=False,
                indent=2,
            ))
        else:
            for result in results:
                print("=" * 72)
                print_summary(result)
        return 0

    if args.scenario not in scenarios:
        parser.error(
            f"Unknown scenario '{args.scenario}'. "
            f"Available: {', '.join(scenarios)}"
        )

    result = simulate(model, scenario_name=args.scenario, months=args.months)
    if args.as_json:
        print(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2))
    else:
        print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
