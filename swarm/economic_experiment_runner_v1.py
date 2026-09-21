#!/usr/bin/env python3
"""
UFCPS Level 2 — Economic Experiment Runner v1

Run competing economic policy variants against the same UFCPS compute-economy
model and stress scenarios.

The runner deliberately does NOT produce an overall "best" economic design.
It produces comparable measurements so agents can inspect trade-offs and decide
which hypotheses deserve further investigation.

Usage
-----
    python swarm/economic_experiment_runner_v1.py
    python swarm/economic_experiment_runner_v1.py --months 24
    python swarm/economic_experiment_runner_v1.py --scenario crash
    python swarm/economic_experiment_runner_v1.py --json
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

try:
    from economic_simulator_v1 import load_model, simulate
except ImportError:
    # Allows execution as:
    # python -m swarm.economic_experiment_runner_v1
    from swarm.economic_simulator_v1 import load_model, simulate


@dataclass(frozen=True)
class PolicyVariant:
    variant_id: str
    name: str
    hypothesis: str
    description: str
    parameter_changes: Dict[str, Any]


@dataclass
class VariantScenarioResult:
    variant_id: str
    variant_name: str
    scenario_name: str
    summary: Dict[str, Any]


def deep_set(model: Dict[str, Any], path: Sequence[str], value: Any) -> None:
    """Set a nested model parameter, creating dictionaries where needed."""
    if not path:
        raise ValueError("Parameter path cannot be empty.")

    current = model
    for key in path[:-1]:
        child = current.get(key)
        if not isinstance(child, dict):
            child = {}
            current[key] = child
        current = child

    current[path[-1]] = copy.deepcopy(value)


def apply_variant(
    base_model: Mapping[str, Any],
    variant: PolicyVariant,
) -> Dict[str, Any]:
    """Return a modified copy of the base model."""
    model = copy.deepcopy(dict(base_model))

    for key, value in variant.parameter_changes.items():
        parts = key.split(".")
        deep_set(model, parts, value)

    # v1 invariant: author royalty remains 0.001% per qualifying transaction.
    royalty = model.get("settlement", {}).get("author_royalty_rate")
    if royalty != 0.00001:
        raise ValueError(
            "Economic experiment variant attempted to change the v1 author "
            "royalty rate. That parameter is fixed at 0.001% in v1."
        )

    return model


def default_variants() -> List[PolicyVariant]:
    """
    Candidate hypotheses.

    These are deliberately illustrative. They are experimental policy variants,
    not recommended designs.
    """
    return [
        PolicyVariant(
            variant_id="V1_BASE",
            name="Baseline",
            hypothesis="Current baseline provides a useful reference point.",
            description="No changes to the supplied economic model.",
            parameter_changes={},
        ),
        PolicyVariant(
            variant_id="V2_LOW_ISSUANCE",
            name="Low Issuance",
            hypothesis="Lower issuance may reduce supply-side inflation pressure.",
            description="Reduce the issuance rate by 50%.",
            parameter_changes={
                "issuance.rate": 0.5,
                "issuance.limits.max_issuance_rate": 0.05,
            },
        ),
        PolicyVariant(
            variant_id="V3_HIGH_LIQUIDITY",
            name="High Liquidity Buffer",
            hypothesis="Higher liquidity buffers may reduce settlement stress.",
            description="Increase target and reserve liquidity ratios.",
            parameter_changes={
                "liquidity.target_liquidity_ratio": 0.40,
                "liquidity.reserve_ratio": 0.20,
            },
        ),
        PolicyVariant(
            variant_id="V4_LOW_TX_COST",
            name="Low Transaction Cost",
            hypothesis="Lower settlement friction may improve micro-provider participation.",
            description="Lower the modeled transaction fee and minimum settlement.",
            parameter_changes={
                "settlement.transaction_fee_rate": 0.0005,
                "settlement.base_transaction_fee": 0.0005,
                "settlement.minimum_settlement": 0.005,
            },
        ),
        PolicyVariant(
            variant_id="V5_CONSERVATIVE_HYBRID",
            name="Conservative Hybrid",
            hypothesis="Combining bounded issuance with stronger liquidity may improve resilience.",
            description="Reduce issuance and increase liquidity buffers together.",
            parameter_changes={
                "issuance.rate": 0.75,
                "issuance.limits.max_issuance_rate": 0.075,
                "liquidity.target_liquidity_ratio": 0.35,
                "liquidity.reserve_ratio": 0.15,
            },
        ),
    ]


def scenario_names(
    model: Mapping[str, Any],
    requested_scenario: str | None,
) -> List[str]:
    if requested_scenario:
        return [requested_scenario]

    names = [
        entry.get("name")
        for entry in model.get("scenarios", [])
        if isinstance(entry, dict) and entry.get("name")
    ]
    return list(dict.fromkeys(names))


def compare_variant(
    base_model: Mapping[str, Any],
    variant: PolicyVariant,
    scenarios: Iterable[str],
    months: int,
) -> List[VariantScenarioResult]:
    model = apply_variant(base_model, variant)

    results: List[VariantScenarioResult] = []
    for scenario in scenarios:
        result = simulate(model, scenario_name=scenario, months=months)
        results.append(
            VariantScenarioResult(
                variant_id=variant.variant_id,
                variant_name=variant.name,
                scenario_name=result.scenario_name,
                summary=result.summary,
            )
        )
    return results


def summarize_variants(
    results: Sequence[VariantScenarioResult],
) -> List[Dict[str, Any]]:
    """Create a trade-off table without collapsing outcomes into one score."""
    grouped: Dict[str, List[VariantScenarioResult]] = {}

    for item in results:
        grouped.setdefault(item.variant_id, []).append(item)

    summaries: List[Dict[str, Any]] = []

    for variant_id, entries in grouped.items():
        by_name = entries[0].variant_name

        avg_utilization = sum(
            item.summary["average_utilization"] for item in entries
        ) / len(entries)

        avg_volatility = sum(
            item.summary["average_volatility_proxy"] for item in entries
        ) / len(entries)

        avg_margin = sum(
            item.summary["average_provider_margin"] for item in entries
        ) / len(entries)

        min_liquidity = min(
            item.summary["ending_liquidity_ratio"] for item in entries
        )

        total_issuance = sum(
            item.summary["total_issuance"] for item in entries
        )

        total_royalty = sum(
            item.summary["total_author_royalty"] for item in entries
        )

        summaries.append(
            {
                "variant_id": variant_id,
                "variant_name": by_name,
                "scenarios_tested": len(entries),
                "average_utilization": avg_utilization,
                "average_volatility_proxy": avg_volatility,
                "average_provider_margin": avg_margin,
                "minimum_ending_liquidity_ratio": min_liquidity,
                "total_issuance_across_scenarios": total_issuance,
                "total_author_royalty_across_scenarios": total_royalty,
            }
        )

    return summaries


def run_experiment(
    model: Mapping[str, Any],
    variants: Iterable[PolicyVariant],
    months: int,
    requested_scenario: str | None = None,
) -> Dict[str, Any]:
    scenarios = scenario_names(model, requested_scenario)

    all_results: List[VariantScenarioResult] = []

    for variant in variants:
        all_results.extend(
            compare_variant(
                base_model=model,
                variant=variant,
                scenarios=scenarios,
                months=months,
            )
        )

    return {
        "runner_version": "v1",
        "months": months,
        "scenarios": scenarios,
        "variants": [
            {
                "variant_id": variant.variant_id,
                "name": variant.name,
                "hypothesis": variant.hypothesis,
                "description": variant.description,
                "parameter_changes": variant.parameter_changes,
            }
            for variant in variants
        ],
        "summary": summarize_variants(all_results),
        "results": [asdict(item) for item in all_results],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="UFCPS Level 2 Economic Experiment Runner v1"
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=Path(__file__).with_name("compute_economy_model_v1.json"),
        help="Path to the base economic model.",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=24,
        help="Simulation horizon in months.",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Run only one named stress scenario.",
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

    if args.months < 1:
        parser.error("--months must be >= 1.")

    model = load_model(args.model)
    available = scenario_names(model, None)

    if args.scenario and args.scenario not in available:
        parser.error(
            f"Unknown scenario '{args.scenario}'. "
            f"Available: {', '.join(available)}"
        )

    variants = default_variants()
    output = run_experiment(
        model=model,
        variants=variants,
        months=args.months,
        requested_scenario=args.scenario,
    )

    if args.as_json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("UFCPS Economic Experiment Runner v1")
        print(f"Months: {output['months']}")
        print("Scenarios:", ", ".join(output["scenarios"]))
        print()
        print("Variant comparison (no overall ranking):")
        for row in output["summary"]:
            print(
                f"- {row['variant_id']} | "
                f"util={row['average_utilization']:.4f} | "
                f"vol={row['average_volatility_proxy']:.4f} | "
                f"margin={row['average_provider_margin']:.4f} | "
                f"min_liq={row['minimum_ending_liquidity_ratio']:.4f} | "
                f"issuance={row['total_issuance_across_scenarios']:.4f}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
