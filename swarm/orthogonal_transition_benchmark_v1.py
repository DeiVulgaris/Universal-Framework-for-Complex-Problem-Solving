"""
UFCPS — Orthogonal Transition Benchmark v1

Structural benchmark for testing the mechanism-independence of
Orthogonal Transition (OT).

This benchmark does NOT measure intelligence, creativity, or scientific
validity.

It tests whether the UFCPS OT evaluator:

1. accepts structurally valid transitions;
2. rejects retries within the same differentiation space;
3. rejects mere parameter changes;
4. rejects mere quantitative increases;
5. treats different mechanisms using the same structural criteria;
6. does not require compensatory multiplication;
7. permits an unknown/emergent mechanism;
8. preserves the distinction between OT and its realization mechanism.

Canonical structure:

    C_k
      ↓
    exhaustion
      ↓
    Fr
      ↓
    reflection
      ↓
    OT
      ↓
    mechanism M_i
      ↓
    C_k+1
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

from orthogonal_transition_v1 import (
    TransitionCandidate,
    TransitionMechanism,
    TransitionStatus,
    evaluate_transition,
)


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    candidate: TransitionCandidate
    expected_status: TransitionStatus
    expected_orthogonal: bool


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    passed: bool
    expected_status: str
    actual_status: str
    expected_orthogonal: bool
    actual_orthogonal: bool
    reasons: List[str]


def _valid_candidate(
    name: str,
    mechanism: TransitionMechanism,
) -> BenchmarkCase:
    return BenchmarkCase(
        name=name,
        candidate=TransitionCandidate(
            mechanism=mechanism,
            source_space="C_k",
            target_space="C_k+1",
            preserves_process_continuity=True,
            changes_differentiation_conditions=True,
            restores_productive_differentiation=True,
            merely_retries_current_space=False,
            merely_changes_parameters=False,
            merely_changes_quantity=False,
            evidence=[
                "process_continuity_preserved",
                "differentiation_conditions_changed",
                "productive_differentiation_restored",
            ],
            description=(
                f"Valid candidate using {mechanism.value}."
            ),
        ),
        expected_status=TransitionStatus.ACCEPTED,
        expected_orthogonal=True,
    )


def build_benchmark_cases() -> List[BenchmarkCase]:
    """
    Construct the structural test suite.

    Several different mechanisms are deliberately represented as valid.
    This is the central test of mechanism independence.
    """

    cases = [
        _valid_candidate(
            "valid_scale_transition",
            TransitionMechanism.SCALE,
        ),

        _valid_candidate(
            "valid_compensatory_multiplication",
            TransitionMechanism.COMPENSATORY_MULTIPLICATION,
        ),

        _valid_candidate(
            "valid_structural_reconfiguration",
            TransitionMechanism.STRUCTURAL_RECONFIGURATION,
        ),

        _valid_candidate(
            "valid_carrier_transition",
            TransitionMechanism.CARRIER_TRANSITION,
        ),

        _valid_candidate(
            "valid_interaction_regime_transition",
            TransitionMechanism.INTERACTION_REGIME,
        ),

        _valid_candidate(
            "valid_representation_space_transition",
            TransitionMechanism.REPRESENTATION_SPACE,
        ),

        _valid_candidate(
            "valid_composition_decomposition",
            TransitionMechanism.COMPOSITION_DECOMPOSITION,
        ),

        _valid_candidate(
            "valid_unknown_emergent_mechanism",
            TransitionMechanism.UNKNOWN_EMERGENT,
        ),
    ]

    cases.extend(
        [
            BenchmarkCase(
                name="reject_local_retry",
                candidate=TransitionCandidate(
                    mechanism=TransitionMechanism.SCALE,
                    source_space="C_k",
                    target_space="C_k",
                    preserves_process_continuity=True,
                    changes_differentiation_conditions=False,
                    restores_productive_differentiation=False,
                    merely_retries_current_space=True,
                    merely_changes_parameters=False,
                    merely_changes_quantity=False,
                    evidence=[
                        "same_cognitive_space",
                        "same_differentiation_conditions",
                    ],
                    description=(
                        "Retry within the exhausted space."
                    ),
                ),
                expected_status=TransitionStatus.REJECTED,
                expected_orthogonal=False,
            ),

            BenchmarkCase(
                name="reject_parameter_change",
                candidate=TransitionCandidate(
                    mechanism=TransitionMechanism.SCALE,
                    source_space="C_k",
                    target_space="C_k",
                    preserves_process_continuity=True,
                    changes_differentiation_conditions=False,
                    restores_productive_differentiation=False,
                    merely_retries_current_space=False,
                    merely_changes_parameters=True,
                    merely_changes_quantity=False,
                    evidence=[
                        "parameter_values_changed",
                    ],
                    description=(
                        "Only parameters changed; the differentiation "
                        "space remains unchanged."
                    ),
                ),
                expected_status=TransitionStatus.REJECTED,
                expected_orthogonal=False,
            ),

            BenchmarkCase(
                name="reject_quantity_only",
                candidate=TransitionCandidate(
                    mechanism=TransitionMechanism.COMPENSATORY_MULTIPLICATION,
                    source_space="C_k",
                    target_space="C_k",
                    preserves_process_continuity=True,
                    changes_differentiation_conditions=False,
                    restores_productive_differentiation=False,
                    merely_retries_current_space=False,
                    merely_changes_parameters=False,
                    merely_changes_quantity=True,
                    evidence=[
                        "more_nodes",
                        "same_relational_regime",
                        "same_differentiation_conditions",
                    ],
                    description=(
                        "Quantity increased without changing the "
                        "conditions of differentiation."
                    ),
                ),
                expected_status=TransitionStatus.REJECTED,
                expected_orthogonal=False,
            ),

            BenchmarkCase(
                name="reject_termination",
                candidate=TransitionCandidate(
                    mechanism=TransitionMechanism.UNKNOWN_EMERGENT,
                    source_space="C_k",
                    target_space="C_k+1",
                    preserves_process_continuity=False,
                    changes_differentiation_conditions=True,
                    restores_productive_differentiation=True,
                    merely_retries_current_space=False,
                    merely_changes_parameters=False,
                    merely_changes_quantity=False,
                    evidence=[
                        "old_process_terminated",
                        "new_process_started",
                    ],
                    description=(
                        "A new process replaces the old one without "
                        "continuity."
                    ),
                ),
                expected_status=TransitionStatus.REJECTED,
                expected_orthogonal=False,
            ),
        ]
    )

    return cases


def run_case(case: BenchmarkCase) -> BenchmarkResult:
    result = evaluate_transition(case.candidate)

    passed = (
        result.status == case.expected_status
        and result.orthogonal == case.expected_orthogonal
    )

    return BenchmarkResult(
        name=case.name,
        passed=passed,
        expected_status=case.expected_status.value,
        actual_status=result.status.value,
        expected_orthogonal=case.expected_orthogonal,
        actual_orthogonal=result.orthogonal,
        reasons=result.reasons,
    )


def run_benchmark() -> Dict[str, object]:
    """
    Execute the complete structural benchmark.
    """

    cases = build_benchmark_cases()
    results = [run_case(case) for case in cases]

    passed = sum(
        1
        for result in results
        if result.passed
    )

    failed = len(results) - passed

    return {
        "benchmark": "orthogonal_transition_benchmark_v1",
        "purpose": (
            "Test mechanism-independence and structural validity "
            "of orthogonal transition."
        ),
        "cases": len(results),
        "passed": passed,
        "failed": failed,
        "all_passed": failed == 0,
        "mechanism_independence_test": {
            "valid_mechanisms_tested": sum(
                1
                for result in results
                if result.name.startswith("valid_")
            ),
            "principle": (
                "No single realization mechanism is required "
                "for OT."
            ),
        },
        "results": [
            {
                "name": result.name,
                "passed": result.passed,
                "expected_status": result.expected_status,
                "actual_status": result.actual_status,
                "expected_orthogonal": result.expected_orthogonal,
                "actual_orthogonal": result.actual_orthogonal,
                "reasons": result.reasons,
            }
            for result in results
        ],
    }


def print_report(report: Dict[str, object]) -> None:
    """
    Print a compact human-readable benchmark report.
    """

    print("UFCPS Orthogonal Transition Benchmark v1")
    print("=" * 48)

    print(
        f"Cases:   {report['cases']}"
    )
    print(
        f"Passed:  {report['passed']}"
    )
    print(
        f"Failed:  {report['failed']}"
    )
    print(
        f"All:     {report['all_passed']}"
    )

    print("\nCases:")

    for result in report["results"]:
        marker = "PASS" if result["passed"] else "FAIL"

        print(
            f"[{marker}] {result['name']}: "
            f"{result['actual_status']}, "
            f"orthogonal={result['actual_orthogonal']}"
        )

    mechanism_test = report["mechanism_independence_test"]

    print("\nMechanism independence:")
    print(
        f"Valid mechanisms tested: "
        f"{mechanism_test['valid_mechanisms_tested']}"
    )


def main() -> int:
    report = run_benchmark()
    print_report(report)

    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
