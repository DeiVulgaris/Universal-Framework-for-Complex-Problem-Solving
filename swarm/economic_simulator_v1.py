#!/usr/bin/env python3
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
- author royalty (0.001% per qualifying transaction);
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


def load_model(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Economic model not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Economic model root must be a JSON object.")
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

        issuance = verified_compute * issuance_rate
        issuance = min(issuance, issuance_max_period)
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
            )
        )

        previous_price = compute_price

    prices = [row.compute_price for row in months_out]
    volatilities = [row.volatility_proxy for row in months_out]
    utilization_values = [row.utilization for row in months_out]
    margins = [row.provider_margin for row in months_out]

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
    }

    return SimulationResult(
        scenario_id=f"S-{scenario_name.upper()}",
        scenario_name=scenario_name,
        months=months_out,
        summary=summary,
    )


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

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
