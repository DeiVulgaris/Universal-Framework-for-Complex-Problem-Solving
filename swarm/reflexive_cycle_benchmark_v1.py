"""
UFCPS — Reflexive Cycle Benchmark v1

Integration benchmark for the Level 3 reflexive architecture.

This benchmark tests the transition:

    Cognitive Space
        ↓
    Exhaustion
        ↓
    Fr
        ↓
    Self–World Differentiation
        ↓
    World Model ↔ Self Model
        ↓
    Self–World Relation Model
        ↓
    Model of Knowing
        ↓
    Reflection
        ↓
    Reflexive Transition Policy
        ↓
    OT candidate

The benchmark is descriptive and structural.

It does NOT measure:
    - intelligence;
    - consciousness;
    - creativity;
    - scientific truth;
    - quality of a proposed orthogonal transition.

Its purpose is to verify architectural invariants of the
Level 3 reflexive cycle.

Important distinctions tested:

    Reflection != OT
    Fr != automatic OT
    Self Model != World Model
    Self–World differentiation is required for full reflection
    Incomplete reflexive models must block OT preparation
    A complete reflexive structure may prepare an OT candidate
"""


from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List


from frustration_v1 import (
    FrustrationStatus,
    FrustrationTrigger,
    from_exhaustion_assessment,
)

from reflection_v1 import (
    ReflectionStatus,
    ReflectionTarget,
    WorldModel,
    SelfModel,
    SelfWorldRelationModel,
    ModelOfKnowing,
    from_frustration,
)

from reflexive_transition_policy_v1 import (
    TransitionDecision,
    evaluate_reflection,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


class ExhaustedAssessment:
    """
    Minimal exhaustion assessment compatible with frustration_v1.py.
    """

    status = "EXHAUSTED"
    productivity_ratio = 0.20
    recent_distance_to_invariant = 0.04
    consecutive_exhaustion_steps = 3

    reasons = [
        "productive_difference_degraded",
        "approaching_invariant",
        "persistent_exhaustion_pattern",
    ]


class ProductiveAssessment:
    """
    Control case: the cognitive space is still productive.
    """

    status = "PRODUCTIVE"
    productivity_ratio = 0.95
    recent_distance_to_invariant = 0.80
    consecutive_exhaustion_steps = 0

    reasons = []


def build_world_model() -> WorldModel:
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


def build_self_model() -> SelfModel:
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


def build_relation_model() -> SelfWorldRelationModel:
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


# ---------------------------------------------------------------------------
# Benchmark structure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    description: str
    expected_reflection_status: str
    expected_decision: str
    runner: Callable[[], Dict[str, Any]]


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    passed: bool

    expected_reflection_status: str
    actual_reflection_status: str

    expected_decision: str
    actual_decision: str

    checks: Dict[str, bool]
    observations: Dict[str, Any]


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------


def build_frustration(
    assessment: Any,
) -> Any:
    """
    Run the exhaustion → Fr stage.
    """

    return from_exhaustion_assessment(
        assessment
    )


def run_reflection(
    frustration: Any,
    *,
    world_model: WorldModel | None = None,
    self_model: SelfModel | None = None,
    relation_model: SelfWorldRelationModel | None = None,
    model_of_knowing: ModelOfKnowing | None = None,
) -> Any:
    """
    Run the Fr → Reflection stage.
    """

    return from_frustration(
        frustration,
        world_model=world_model,
        self_model=self_model,
        relation_model=relation_model,
        model_of_knowing=model_of_knowing,
    )


def run_policy(
    reflection: Any,
) -> Any:
    """
    Run the Reflection → Reflexive Policy stage.
    """

    return evaluate_reflection(
        reflection
    )


# ---------------------------------------------------------------------------
# Benchmark cases
# ---------------------------------------------------------------------------


def case_productive_state() -> Dict[str, Any]:
    """
    A productive cognitive space must not create Fr,
    reflection, or an OT candidate.
    """

    frustration = build_frustration(
        ProductiveAssessment()
    )

    reflection = run_reflection(
        frustration
    )

    decision = run_policy(
        reflection
    )

    return {
        "frustration": frustration,
        "reflection": reflection,
        "decision": decision,
    }


def case_exhaustion_without_reflexive_models() -> Dict[str, Any]:
    """
    Exhaustion and Fr are present, but Self/World models are absent.

    Reflection may be triggered, but full Level 3 reflection
    must not prepare OT.
    """

    frustration = build_frustration(
        ExhaustedAssessment()
    )

    reflection = run_reflection(
        frustration
    )

    decision = run_policy(
        reflection
    )

    return {
        "frustration": frustration,
        "reflection": reflection,
        "decision": decision,
    }


def case_self_world_models_incomplete() -> Dict[str, Any]:
    """
    World Model exists, but Self Model and relation model do not.

    The system must not treat a partial model as full
    Self–World reflection.
    """

    frustration = build_frustration(
        ExhaustedAssessment()
    )

    reflection = run_reflection(
        frustration,
        world_model=build_world_model(),
    )

    decision = run_policy(
        reflection
    )

    return {
        "frustration": frustration,
        "reflection": reflection,
        "decision": decision,
    }


def case_complete_reflexive_structure() -> Dict[str, Any]:
    """
    Full Level 3 structure:

        World Model
        Self Model
        Self–World Relation Model
        Model of Knowing

    This should permit preparation of an OT candidate.

    It must NOT execute OT itself.
    """

    frustration = build_frustration(
        ExhaustedAssessment()
    )

    world_model = build_world_model()
    self_model = build_self_model()
    relation_model = build_relation_model()

    reflection = run_reflection(
        frustration,
        world_model=world_model,
        self_model=self_model,
        relation_model=relation_model,
    )

    decision = run_policy(
        reflection
    )

    return {
        "frustration": frustration,
        "reflection": reflection,
        "decision": decision,
    }


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------


def evaluate_case(
    case: BenchmarkCase,
) -> BenchmarkResult:
    result = case.runner()

    frustration = result["frustration"]
    reflection = result["reflection"]
    decision = result["decision"]

    actual_reflection_status = (
        reflection.status.value
        if hasattr(reflection.status, "value")
        else str(reflection.status)
    )

    actual_decision = (
        decision.decision.value
        if hasattr(decision.decision, "value")
        else str(decision.decision)
    )

    checks: Dict[str, bool] = {}

    # ------------------------------------------------------------
    # Expected states
    # ------------------------------------------------------------

    checks["reflection_status"] = (
        actual_reflection_status
        == case.expected_reflection_status
    )

    checks["policy_decision"] = (
        actual_decision
        == case.expected_decision
    )

    # ------------------------------------------------------------
    # Architectural invariants
    # ------------------------------------------------------------

    checks["reflection_is_not_ot"] = (
        actual_decision
        != "EXECUTE_ORTHOGONAL_TRANSITION"
    )

    checks["reflection_has_self_world_boundary"] = (
        hasattr(
            reflection,
            "self_world_differentiated",
        )
    )

    # Productive case must not create Fr.
    if case.name == "productive_state":

        checks["productive_does_not_activate_fr"] = (
            frustration.status.value
            == FrustrationStatus.NONE.value
        )

    # Incomplete cases must not prepare OT.
    if case.name in {
        "exhaustion_without_reflexive_models",
        "self_world_models_incomplete",
    }:

        checks["incomplete_reflexive_structure_blocks_ot"] = (
            actual_decision
            != TransitionDecision.PREPARE_ORTHOGONAL_TRANSITION.value
        )

    # Complete case must distinguish Self and World.
    if case.name == "complete_reflexive_structure":

        checks["self_world_differentiated"] = (
            reflection.self_world_differentiated
            is True
        )

        checks["world_model_available"] = (
            reflection.world_model_available
            is True
        )

        checks["self_model_available"] = (
            reflection.self_model_available
            is True
        )

        checks["relation_model_available"] = (
            reflection.relation_model_available
            is True
        )

        checks["model_of_knowing_available"] = (
            reflection.model_of_knowing_available
            is True
        )

        checks["ot_candidate_prepared"] = (
            actual_decision
            == TransitionDecision.PREPARE_ORTHOGONAL_TRANSITION.value
        )

        checks["ot_not_executed"] = (
            actual_decision
            != "ORTHOGONAL_TRANSITION_EXECUTED"
        )

    passed = all(
        checks.values()
    )

    return BenchmarkResult(
        name=case.name,
        passed=passed,

        expected_reflection_status=(
            case.expected_reflection_status
        ),

        actual_reflection_status=(
            actual_reflection_status
        ),

        expected_decision=(
            case.expected_decision
        ),

        actual_decision=(
            actual_decision
        ),

        checks=checks,

        observations={
            "frustration_status": (
                frustration.status.value
            ),
            "frustration_trigger": (
                frustration.trigger.value
            ),
            "reflection_target": (
                reflection.target.value
            ),
            "transition_candidate": (
                reflection.transition_candidate
            ),
        },
    )


# ---------------------------------------------------------------------------
# Suite
# ---------------------------------------------------------------------------


def build_cases() -> List[BenchmarkCase]:
    return [
        BenchmarkCase(
            name="productive_state",
            description=(
                "Productive cognitive space does not initiate "
                "the reflexive transition cycle."
            ),
            expected_reflection_status=(
                ReflectionStatus.INACTIVE.value
            ),
            expected_decision=(
                TransitionDecision.CONTINUE_CURRENT_SPACE.value
            ),
            runner=case_productive_state,
        ),

        BenchmarkCase(
            name="exhaustion_without_reflexive_models",
            description=(
                "Exhaustion creates Fr and triggers reflection, "
                "but incomplete Self–World modeling blocks OT preparation."
            ),
            expected_reflection_status=(
                ReflectionStatus.TRIGGERED.value
            ),
            expected_decision=(
                TransitionDecision.CONTINUE_CURRENT_SPACE.value
            ),
            runner=case_exhaustion_without_reflexive_models,
        ),

        BenchmarkCase(
            name="self_world_models_incomplete",
            description=(
                "A partial Self–World representation is insufficient "
                "for full Level 3 reflection."
            ),
            expected_reflection_status=(
                ReflectionStatus.TRIGGERED.value
            ),
            expected_decision=(
                TransitionDecision.CONTINUE_CURRENT_SPACE.value
            ),
            runner=case_self_world_models_incomplete,
        ),

        BenchmarkCase(
            name="complete_reflexive_structure",
            description=(
                "Complete Self–World modeling permits preparation "
                "of an orthogonal transition candidate."
            ),
            expected_reflection_status=(
                ReflectionStatus.ACTIVE.value
            ),
            expected_decision=(
                TransitionDecision.PREPARE_ORTHOGONAL_TRANSITION.value
            ),
            runner=case_complete_reflexive_structure,
        ),
    ]


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
        "benchmark": "reflexive_cycle_benchmark_v1",

        "purpose": (
            "Structural validation of the Level 3 "
            "Self–World reflexive cycle."
        ),

        "cases": len(results),
        "passed": passed,
        "failed": failed,
        "all_passed": failed == 0,

        "architectural_invariants": [
            "Productive state does not force reflection.",
            "Fr does not automatically execute OT.",
            "Self Model and World Model are distinct objects.",
            "Self–World Relation Model is a separate object.",
            "Incomplete reflexive modeling blocks OT preparation.",
            "Complete reflexive modeling can prepare an OT candidate.",
            "Reflection is not equivalent to OT.",
        ],

        "results": [
            {
                "name": result.name,
                "passed": result.passed,

                "expected_reflection_status": (
                    result.expected_reflection_status
                ),

                "actual_reflection_status": (
                    result.actual_reflection_status
                ),

                "expected_decision": (
                    result.expected_decision
                ),

                "actual_decision": (
                    result.actual_decision
                ),

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
        "UFCPS Reflexive Cycle Benchmark v1"
    )
    print("=" * 52)

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

        print(
            f"[{marker}] "
            f"{result['name']}: "
            f"reflection="
            f"{result['actual_reflection_status']}, "
            f"decision="
            f"{result['actual_decision']}"
        )

        for name, passed in result["checks"].items():

            marker = (
                "OK"
                if passed
                else "FAIL"
            )

            print(
                f"    [{marker}] {name}"
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
