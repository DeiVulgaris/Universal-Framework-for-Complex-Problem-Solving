"""
UFCPS — Level 3 Runtime Benchmark v1

Integration benchmark for the executable Level 3 reflexive runtime.

Pipeline under test:

    Observation
        ↓
    Cognitive Space Assessment
        ↓
    Fr
        ↓
    Self–World Differentiation
        ↓
    World Model ↔ Self Model
        ↓
    Reflection
        ↓
    Reflexive Policy
        ↓
    Runtime Decision

The benchmark verifies the separation between:

    Local Failure
    Cognitive-Space Exhaustion
    Frustration
    Reflection
    Orthogonal Transition Readiness
    Process Termination

This benchmark is descriptive and architectural.

It does NOT measure:
    - intelligence;
    - consciousness;
    - creativity;
    - scientific validity;
    - quality of any OT mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from cognitive_space_exhaustion_v1 import CognitiveObservation
from frustration_v1 import FrustrationStatus
from reflection_v1 import ReflectionStatus
from reflexive_transition_policy_v1 import TransitionDecision
from level3_reflexive_runtime_v1 import (
    Level3ReflexiveRuntime,
    RuntimeDecision,
)
from reflection_v1 import (
    WorldModel,
    SelfModel,
    SelfWorldRelationModel,
)


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


def productive_observations() -> List[CognitiveObservation]:
    return [
        CognitiveObservation(
            step=1,
            productive_difference=1.00,
            distance_to_invariant=0.90,
            local_failure=False,
        ),
        CognitiveObservation(
            step=2,
            productive_difference=0.95,
            distance_to_invariant=0.80,
            local_failure=False,
        ),
        CognitiveObservation(
            step=3,
            productive_difference=0.90,
            distance_to_invariant=0.75,
            local_failure=False,
        ),
        CognitiveObservation(
            step=4,
            productive_difference=0.88,
            distance_to_invariant=0.70,
            local_failure=False,
        ),
    ]


def local_failure_observations() -> List[CognitiveObservation]:
    return [
        CognitiveObservation(
            step=1,
            productive_difference=1.00,
            distance_to_invariant=0.80,
            local_failure=False,
        ),
        CognitiveObservation(
            step=2,
            productive_difference=0.95,
            distance_to_invariant=0.70,
            local_failure=True,
        ),
        CognitiveObservation(
            step=3,
            productive_difference=0.92,
            distance_to_invariant=0.68,
            local_failure=False,
        ),
        CognitiveObservation(
            step=4,
            productive_difference=0.90,
            distance_to_invariant=0.65,
            local_failure=True,
        ),
    ]


def exhausted_observations() -> List[CognitiveObservation]:
    return [
        CognitiveObservation(
            step=1,
            productive_difference=1.00,
            distance_to_invariant=0.80,
            local_failure=False,
        ),
        CognitiveObservation(
            step=2,
            productive_difference=0.60,
            distance_to_invariant=0.30,
            local_failure=False,
        ),
        CognitiveObservation(
            step=3,
            productive_difference=0.20,
            distance_to_invariant=0.08,
            local_failure=False,
        ),
        CognitiveObservation(
            step=4,
            productive_difference=0.10,
            distance_to_invariant=0.04,
            local_failure=True,
        ),
    ]


def complete_world_model() -> WorldModel:
    return WorldModel(
        model_id="world_v1",
        version="1.0",
        distinctions=[
            "observed_state",
            "external_constraint",
            "task_result",
        ],
        relations=[
            "causal_relation",
            "temporal_relation",
        ],
        uncertainties=[
            "unresolved_relation",
        ],
    )


def complete_self_model() -> SelfModel:
    return SelfModel(
        model_id="self_v1",
        version="1.0",
        capabilities=[
            "observation",
            "reasoning",
            "memory",
            "self_monitoring",
        ],
        limitations=[
            "finite_resources",
            "representation_bias",
            "incomplete_model",
        ],
        resources=[
            "memory",
            "compute",
            "agent_swarm",
        ],
        current_method="recursive_search",
        current_cognitive_space="C_k",
        process_history_ref="process_history_v1",
    )


def complete_relation_model() -> SelfWorldRelationModel:
    return SelfWorldRelationModel(
        model_id="self_world_relation_v1",
        version="1.0",
        observation_channels=[
            "sensor",
            "language",
            "simulation",
        ],
        dependencies=[
            "representation",
            "observation_method",
        ],
        blind_spots=[
            "unobserved_state",
            "model-dependent_distinction",
        ],
        model_influence_on_observation=[
            "selection_of_observables",
            "interpretation_of_results",
        ],
    )


# ----------------------------------------------------------------------
# Benchmark case
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    description: str
    runner: Callable[[], Dict[str, Any]]


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    passed: bool
    checks: Dict[str, bool]
    observations: Dict[str, Any]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def run_runtime(
    observations: List[CognitiveObservation],
    *,
    complete_models: bool = False,
) -> Dict[str, Any]:

    runtime = Level3ReflexiveRuntime()

    if complete_models:

        result = runtime.run(
            observations,
            world_model=complete_world_model(),
            self_model=complete_self_model(),
            relation_model=complete_relation_model(),
        )

    else:

        result = runtime.run(
            observations
        )

    return result.to_dict()


# ----------------------------------------------------------------------
# Cases
# ----------------------------------------------------------------------


def case_productive() -> Dict[str, Any]:
    """
    Productive process.

    Expected:
        no exhaustion
        no Fr
        no reflection
        continue current space
    """

    return run_runtime(
        productive_observations()
    )


def case_local_failure() -> Dict[str, Any]:
    """
    Local failures occur, but the cognitive space remains productive.

    Expected:
        local failures do not become cognitive-space exhaustion.
    """

    return run_runtime(
        local_failure_observations()
    )


def case_exhaustion_without_models() -> Dict[str, Any]:
    """
    Cognitive-space exhaustion occurs, but the Self–World structure
    is not available.

    Expected:
        Fr
        reflection triggered
        no OT preparation
    """

    return run_runtime(
        exhausted_observations()
    )


def case_exhaustion_with_complete_models() -> Dict[str, Any]:
    """
    Full Level 3 case.

    Expected:
        exhaustion
        Fr
        active reflection
        Self–World differentiation
        OT preparation

    The runtime must stop before OT execution.
    """

    return run_runtime(
        exhausted_observations(),
        complete_models=True,
    )


def case_process_continuity() -> Dict[str, Any]:
    """
    A transition-readiness state must still represent a continuing
    process rather than termination.

    This case is structurally identical to the complete reflexive case,
    but explicitly tests the continuity invariant.
    """

    return run_runtime(
        exhausted_observations(),
        complete_models=True,
    )


# ----------------------------------------------------------------------
# Evaluation
# ----------------------------------------------------------------------


def evaluate_productive(
    result: Dict[str, Any],
) -> Dict[str, bool]:

    return {
        "no_exhaustion": (
            result["exhaustion_status"]
            != "EXHAUSTED"
        ),
        "no_frustration": (
            result["frustration_status"]
            == FrustrationStatus.NONE.value
        ),
        "no_ot_candidate": (
            result["transition_candidate"]
            is False
        ),
        "continue_current_space": (
            result["decision"]
            == RuntimeDecision.CONTINUE_CURRENT_SPACE.value
        ),
    }


def evaluate_local_failure(
    result: Dict[str, Any],
) -> Dict[str, bool]:

    return {
        "not_exhausted": (
            result["exhaustion_status"]
            != "EXHAUSTED"
        ),
        "local_failure_does_not_force_ot": (
            result["decision"]
            != RuntimeDecision.PREPARE_ORTHOGONAL_TRANSITION.value
        ),
        "process_continues": (
            result["decision"]
            == RuntimeDecision.CONTINUE_CURRENT_SPACE.value
        ),
    }


def evaluate_incomplete_reflexive(
    result: Dict[str, Any],
) -> Dict[str, bool]:

    return {
        "exhausted": (
            result["exhaustion_status"]
            == "EXHAUSTED"
        ),
        "fr_active": (
            result["frustration_status"]
            == FrustrationStatus.ACTIVE.value
        ),
        "reflection_triggered": (
            result["reflection_status"]
            == ReflectionStatus.TRIGGERED.value
        ),
        "self_world_not_complete": (
            result["self_world_differentiated"]
            is False
        ),
        "ot_not_prepared": (
            result["decision"]
            != RuntimeDecision.PREPARE_ORTHOGONAL_TRANSITION.value
        ),
    }


def evaluate_complete_reflexive(
    result: Dict[str, Any],
) -> Dict[str, bool]:

    return {
        "exhausted": (
            result["exhaustion_status"]
            == "EXHAUSTED"
        ),
        "fr_active": (
            result["frustration_status"]
            == FrustrationStatus.ACTIVE.value
        ),
        "reflection_active": (
            result["reflection_status"]
            == ReflectionStatus.ACTIVE.value
        ),
        "self_world_differentiated": (
            result["self_world_differentiated"]
            is True
        ),
        "world_model_available": (
            result["world_model_available"]
            is True
        ),
        "self_model_available": (
            result["self_model_available"]
            is True
        ),
        "relation_model_available": (
            result["relation_model_available"]
            is True
        ),
        "model_of_knowing_available": (
            result["model_of_knowing_available"]
            is True
        ),
        "ot_candidate_prepared": (
            result["decision"]
            == RuntimeDecision.PREPARE_ORTHOGONAL_TRANSITION.value
        ),
        "ot_not_executed": (
            result["decision"]
            != "ORTHOGONAL_TRANSITION_EXECUTED"
        ),
    }


def evaluate_continuity(
    result: Dict[str, Any],
) -> Dict[str, bool]:

    return {
        "process_not_terminated": (
            result["decision"]
            != "PROCESS_TERMINATED"
        ),
        "ot_is_only_prepared": (
            result["decision"]
            == RuntimeDecision.PREPARE_ORTHOGONAL_TRANSITION.value
        ),
        "transition_candidate_present": (
            result["transition_candidate"]
            is True
        ),
    }


# ----------------------------------------------------------------------
# Suite
# ----------------------------------------------------------------------


def build_cases() -> List[BenchmarkCase]:

    return [
        BenchmarkCase(
            name="productive",
            description=(
                "A productive cognitive space remains in ordinary "
                "continuation."
            ),
            runner=case_productive,
        ),

        BenchmarkCase(
            name="local_failure",
            description=(
                "Local failures do not by themselves constitute "
                "cognitive-space exhaustion."
            ),
            runner=case_local_failure,
        ),

        BenchmarkCase(
            name="exhaustion_without_models",
            description=(
                "Exhaustion creates Fr and reflection pressure, "
                "but incomplete Self–World modeling blocks OT preparation."
            ),
            runner=case_exhaustion_without_models,
        ),

        BenchmarkCase(
            name="complete_reflexive_cycle",
            description=(
                "Complete Level 3 reflection permits preparation "
                "of an orthogonal transition."
            ),
            runner=case_exhaustion_with_complete_models,
        ),

        BenchmarkCase(
            name="process_continuity",
            description=(
                "Transition readiness does not equal process termination."
            ),
            runner=case_process_continuity,
        ),
    ]


def evaluate_case(
    case: BenchmarkCase,
) -> BenchmarkResult:

    result = case.runner()

    if case.name == "productive":
        checks = evaluate_productive(
            result
        )

    elif case.name == "local_failure":
        checks = evaluate_local_failure(
            result
        )

    elif case.name == "exhaustion_without_models":
        checks = evaluate_incomplete_reflexive(
            result
        )

    elif case.name == "complete_reflexive_cycle":
        checks = evaluate_complete_reflexive(
            result
        )

    elif case.name == "process_continuity":
        checks = evaluate_continuity(
            result
        )

    else:
        raise ValueError(
            f"Unknown benchmark case: {case.name}"
        )

    return BenchmarkResult(
        name=case.name,
        passed=all(checks.values()),
        checks=checks,
        observations={
            "decision": result["decision"],
            "exhaustion_status": (
                result["exhaustion_status"]
            ),
            "frustration_status": (
                result["frustration_status"]
            ),
            "reflection_status": (
                result["reflection_status"]
            ),
            "reflection_target": (
                result["reflection_target"]
            ),
            "transition_candidate": (
                result["transition_candidate"]
            ),
        },
    )


def run_benchmark() -> Dict[str, Any]:

    cases = build_cases()

    results = [
        evaluate_case(case)
        for case in cases
    ]

    passed = sum(
        1
        for result in results
        if result.passed
    )

    failed = len(results) - passed

    return {
        "benchmark": "level3_runtime_benchmark_v1",

        "purpose": (
            "Integration validation of the Level 3 "
            "reflexive runtime."
        ),

        "cases": len(results),
        "passed": passed,
        "failed": failed,
        "all_passed": failed == 0,

        "core_invariants": [
            "Local Failure != Cognitive-Space Exhaustion",
            "Cognitive-Space Exhaustion != Process Termination",
            "Fr != automatic OT",
            "Reflection != OT",
            "Incomplete Self–World modeling blocks OT preparation",
            "Complete Self–World modeling can prepare OT",
            "OT preparation != OT execution",
        ],

        "results": [
            {
                "name": result.name,
                "passed": result.passed,
                "checks": result.checks,
                "observations": result.observations,
            }
            for result in results
        ],
    }


def print_report(
    report: Dict[str, Any],
) -> None:

    print(
        "UFCPS Level 3 Runtime Benchmark v1"
    )
    print("=" * 54)

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

        marker = (
            "PASS"
            if result["passed"]
            else "FAIL"
        )

        observations = result["observations"]

        print(
            f"[{marker}] {result['name']}: "
            f"decision={observations['decision']}, "
            f"exhaustion="
            f"{observations['exhaustion_status']}, "
            f"reflection="
            f"{observations['reflection_status']}"
        )

        for check, passed in result["checks"].items():

            check_marker = (
                "OK"
                if passed
                else "FAIL"
            )

            print(
                f"    [{check_marker}] {check}"
            )


def main() -> int:

    report = run_benchmark()

    print_report(
        report
    )

    return (
        0
        if report["all_passed"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
