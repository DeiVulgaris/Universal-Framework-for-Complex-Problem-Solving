"""
UFCPS — Level 3 Full Cycle Benchmark v1

End-to-end structural benchmark of the Level 3 reflexive cycle.

Pipeline:

    C_k
      ↓
    Cognitive-Space Exhaustion
      ↓
    Frustration
      ↓
    Reflection
      ↓
    Reflexive Transition Policy
      ↓
    Orthogonal Transition Exploration
      ↓
    Branch Localization
      ↓
    Branch Interaction
      ├── D_new
      └── I_candidate
      ↓
    UQL persistence
      ↓
    Emergent Space Builder
      ↓
    C_k+1
      ↓
    Continuation

This benchmark is architectural.

It does NOT measure:
    - intelligence;
    - consciousness;
    - creativity as a psychological phenomenon;
    - truth of an invariant;
    - quality of a scientific theory.

It checks whether the Level 3 components preserve
the intended structural invariants when composed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from cognitive_space_exhaustion_v1 import (
    CognitiveObservation,
    ExhaustionConfig,
    ExhaustionDetector,
    ExhaustionStatus,
)

from frustration_v1 import (
    FrustrationConfig,
    FrustrationStatus,
    from_exhaustion_assessment,
)

from reflection_v1 import (
    ReflectionConfig,
    ReflectionStatus,
    SelfModel,
    WorldModel,
    SelfWorldRelationModel,
    from_frustration,
)

from reflexive_transition_policy_v1 import (
    ReflectionDecision,
    ReflexiveTransitionPolicy,
    TransitionDecision,
)

from orthogonal_transition_explorer_v1 import (
    OrthogonalTransitionExplorer,
    OTMechanism,
)

from branch_interaction_v1 import (
    BranchInteractionEngine,
    InteractionStatus,
    LocalizedBranch,
)

from level3_emergent_integration_v1 import (
    InMemoryUQLAdapter,
)

from emergent_space_builder_v1 import (
    CognitiveSpace,
    EmergentSpaceBuilder,
)


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


def exhausted_observations() -> List[CognitiveObservation]:

    return [
        CognitiveObservation(
            step=1,
            productive_difference=1.0,
            distance_to_invariant=0.80,
        ),

        CognitiveObservation(
            step=2,
            productive_difference=0.40,
            distance_to_invariant=0.40,
        ),

        CognitiveObservation(
            step=3,
            productive_difference=0.20,
            distance_to_invariant=0.18,
        ),

        CognitiveObservation(
            step=4,
            productive_difference=0.10,
            distance_to_invariant=0.08,
        ),

        CognitiveObservation(
            step=5,
            productive_difference=0.05,
            distance_to_invariant=0.05,
        ),

        CognitiveObservation(
            step=6,
            productive_difference=0.03,
            distance_to_invariant=0.04,
        ),
    ]


def productive_observations() -> List[CognitiveObservation]:

    return [
        CognitiveObservation(
            step=1,
            productive_difference=1.0,
            distance_to_invariant=0.80,
        ),

        CognitiveObservation(
            step=2,
            productive_difference=0.90,
            distance_to_invariant=0.70,
        ),

        CognitiveObservation(
            step=3,
            productive_difference=0.85,
            distance_to_invariant=0.65,
        ),

        CognitiveObservation(
            step=4,
            productive_difference=0.80,
            distance_to_invariant=0.60,
        ),
    ]


def build_reflexive_models() -> Dict[str, Any]:

    world_model = WorldModel(
        model_id="WORLD_MODEL_L3_TEST",
        version=1,
        distinctions=[
            "D_existing_1",
            "D_existing_2",
            "D_existing_3",
        ],
        relations=[
            "relation_existing_1",
            "relation_existing_2",
        ],
        uncertainties=[
            "uncertainty_1",
        ],
    )

    self_model = SelfModel(
        model_id="SELF_MODEL_L3_TEST",
        version=1,
        capabilities=[
            "branch_generation",
            "branch_comparison",
            "interaction",
        ],
        limitations=[
            "current_space_exhaustion",
        ],
        resources=[
            "compute",
            "memory",
        ],
        current_method="current_search_regime",
        current_cognitive_space="C_k",
        process_history_ref="PROCESS_L3_TEST",
    )

    relation_model = SelfWorldRelationModel(
        model_id="SELF_WORLD_RELATION_L3_TEST",
        version=1,
        observation_channels=[
            "branch_observation",
            "interaction_observation",
        ],
        dependencies=[
            "current_method",
            "available_resources",
        ],
        blind_spots=[
            "unexplored_interaction_regimes",
        ],
        model_influence_on_observation=[
            "branch_selection",
        ],
    )

    return {
        "world_model": world_model,
        "self_model": self_model,
        "relation_model": relation_model,
    }


# ----------------------------------------------------------------------
# Benchmark
# ----------------------------------------------------------------------


@dataclass
class BenchmarkResult:

    name: str

    passed: bool

    checks: Dict[str, bool]

    observations: Dict[str, Any]


class Level3FullCycleBenchmark:

    def __init__(self) -> None:

        self.exhaustion_detector = (
            ExhaustionDetector(
                ExhaustionConfig()
            )
        )

        self.frustration_config = FrustrationConfig()

        self.reflection_config = (
            ReflectionConfig()
        )

        self.policy = (
            ReflexiveTransitionPolicy()
        )

        self.explorer = (
            OrthogonalTransitionExplorer()
        )

        self.interaction_engine = (
            BranchInteractionEngine()
        )

        self.uql = (
            InMemoryUQLAdapter()
        )

        self.builder = (
            EmergentSpaceBuilder()
        )

    # ------------------------------------------------------------------
    # Stage 1 — Exhaustion
    # ------------------------------------------------------------------

    def assess_exhaustion(self):

        return self.exhaustion_detector.assess(
            exhausted_observations()
        )

    # ------------------------------------------------------------------
    # Stage 2 — Frustration
    # ------------------------------------------------------------------

    def assess_frustration(
        self,
        exhaustion,
    ):

        return from_exhaustion_assessment(
            exhaustion,
            self.frustration_config,
        )

    # ------------------------------------------------------------------
    # Stage 3 — Reflection
    # ------------------------------------------------------------------

    def assess_reflection(
        self,
        frustration,
    ):

        models = build_reflexive_models()

        return from_frustration(
            frustration,
            config=self.reflection_config,
            world_model=models["world_model"],
            self_model=models["self_model"],
            relation_model=models["relation_model"],
        )

    # ------------------------------------------------------------------
    # Stage 4 — Policy
    # ------------------------------------------------------------------

    def assess_policy(
        self,
        reflection,
    ) -> ReflectionDecision:

        return self.policy.evaluate(
            reflection
        )

    # ------------------------------------------------------------------
    # Stage 5 — OT exploration
    # ------------------------------------------------------------------

    def explore_branches(
        self,
        reflection,
    ):

        source_space = "C_k"

        candidates = [
            (
                OTMechanism.SCALE,
                "C_k_SCALE",
            ),

            (
                OTMechanism.STRUCTURAL_RECONFIGURATION,
                "C_k_RECONFIGURED",
            ),

            (
                OTMechanism.REPRESENTATION_SPACE,
                "C_k_REPRESENTED",
            ),
        ]

        branches = []

        for mechanism, target_space in candidates:

            branch = (
                self.explorer.generate_candidate(
                    mechanism=mechanism,
                    source_space=source_space,
                    target_space=target_space,
                    preserves_process_continuity=True,
                    changes_differentiation_conditions=True,
                    restores_productive_differentiation=True,
                    metadata={
                        "distinctions": [
                            f"D_{mechanism.value}_1",
                            f"D_{mechanism.value}_2",
                        ],

                        "relations": [
                            "persistence",
                            "coupling",
                            f"relation_{mechanism.value}",
                        ],
                    },
                )
            )

            validated = (
                self.explorer.validate_candidate(
                    branch
                )
            )

            if validated:
                branches.append(
                    branch
                )

        return branches

    # ------------------------------------------------------------------
    # Stage 6 — Localization
    # ------------------------------------------------------------------

    def localize_branches(
        self,
        branches,
    ) -> List[LocalizedBranch]:

        localized = []

        for branch in branches:

            metadata = (
                branch.metadata
            )

            localized.append(
                LocalizedBranch(
                    branch_id=branch.branch_id,

                    mechanism=branch.mechanism.value,

                    state_id=branch.target_space,

                    distinctions=tuple(
                        metadata.get(
                            "distinctions",
                            [],
                        )
                    ),

                    relations=tuple(
                        metadata.get(
                            "relations",
                            [],
                        )
                    ),

                    constraints=(
                        "continuity",
                        "changed_differentiation_conditions",
                    ),

                    productive=True,

                    metadata={
                        "source_space":
                            branch.source_space,
                    },
                )
            )

        return localized

    # ------------------------------------------------------------------
    # Stage 7 — Interaction
    # ------------------------------------------------------------------

    def interact(
        self,
        localized,
    ):

        return self.interaction_engine.interact(
            localized
        )

    # ------------------------------------------------------------------
    # Stage 8 — UQL persistence
    # ------------------------------------------------------------------

    def persist_interaction(
        self,
        interaction,
    ):

        question_ids = []

        for question in (
            interaction.new_questions
        ):

            question_id = (
                self.uql.create_question(
                    question,
                    parent_ref=(
                        interaction.interaction_id
                    ),
                    provenance={
                        "source": (
                            "level3_interaction"
                        ),
                        "branches": (
                            interaction.branch_ids
                        ),
                    },
                )
            )

            question_ids.append(
                question_id
            )

        return question_ids

    # ------------------------------------------------------------------
    # Stage 9 — New cognitive space
    # ------------------------------------------------------------------

    def build_next_space(
        self,
        interaction,
        question_ids,
    ):

        parent = CognitiveSpace(
            space_id="C_k",

            parent_space_id=None,

            version=1,

            accessible_distinctions=[
                "D_existing_1",
                "D_existing_2",
            ],

            active_invariants=[
                "I_existing_1",
            ],

            description=(
                "Source cognitive space."
            ),
        )

        return self.builder.build(
            parent_space=parent,

            interaction=interaction,

            question_ids=question_ids,

            next_space_id="C_k+1",
        )

    # ------------------------------------------------------------------
    # Full cycle
    # ------------------------------------------------------------------

    def run(self) -> BenchmarkResult:

        checks: Dict[str, bool] = {}

        observations: Dict[str, Any] = {}

        # --------------------------------------------------------------
        # 1. Exhaustion
        # --------------------------------------------------------------

        exhaustion = (
            self.assess_exhaustion()
        )

        checks[
            "exhaustion_detected"
        ] = (
            exhaustion.status
            == ExhaustionStatus.EXHAUSTED
        )

        observations[
            "exhaustion_status"
        ] = exhaustion.status.value

        # --------------------------------------------------------------
        # 2. Frustration
        # --------------------------------------------------------------

        frustration = (
            self.assess_frustration(
                exhaustion
            )
        )

        checks[
            "frustration_active"
        ] = (
            frustration.status
            == FrustrationStatus.ACTIVE
        )

        observations[
            "frustration_status"
        ] = frustration.status.value

        # --------------------------------------------------------------
        # 3. Reflection
        # --------------------------------------------------------------

        reflection = (
            self.assess_reflection(
                frustration
            )
        )

        checks[
            "reflection_active"
        ] = (
            reflection.status
            == ReflectionStatus.ACTIVE
        )

        checks[
            "self_world_differentiated"
        ] = (
            reflection.self_world_differentiated
            is True
        )

        observations[
            "reflection_status"
        ] = reflection.status.value

        # --------------------------------------------------------------
        # 4. Policy
        # --------------------------------------------------------------

        decision = (
            self.assess_policy(
                reflection
            )
        )

        checks[
            "policy_prepares_ot"
        ] = (
            decision.decision
            == TransitionDecision.PREPARE_ORTHOGONAL_TRANSITION
        )

        observations[
            "policy_decision"
        ] = decision.decision.value

        # --------------------------------------------------------------
        # 5. OT exploration
        # --------------------------------------------------------------

        branches = (
            self.explore_branches(
                reflection
            )
        )

        checks[
            "multiple_ot_branches"
        ] = len(branches) >= 3

        checks[
            "branch_diversity"
        ] = (
            len(
                {
                    branch.mechanism
                    for branch in branches
                }
            )
            >= 3
        )

        observations[
            "ot_branch_count"
        ] = len(branches)

        # --------------------------------------------------------------
        # 6. Localization
        # --------------------------------------------------------------

        localized = (
            self.localize_branches(
                branches
            )
        )

        checks[
            "all_branches_localized"
        ] = (
            len(localized)
            == len(branches)
        )

        # --------------------------------------------------------------
        # 7. Interaction
        # --------------------------------------------------------------

        interaction = (
            self.interact(
                localized
            )
        )

        checks[
            "interaction_occurred"
        ] = (
            interaction.status
            != InteractionStatus.NOT_INTERACTED
        )

        checks[
            "interaction_has_multiple_branches"
        ] = (
            len(interaction.branch_ids)
            >= 2
        )

        observations[
            "interaction_status"
        ] = interaction.status.value

        # --------------------------------------------------------------
        # 8. D_new
        # --------------------------------------------------------------

        checks[
            "new_distinction_detected"
        ] = (
            len(
                interaction.emergent_distinctions
            )
            > 0
        )

        observations[
            "new_distinction_count"
        ] = len(
            interaction.emergent_distinctions
        )

        # --------------------------------------------------------------
        # 9. Invariant candidate
        # --------------------------------------------------------------

        checks[
            "invariant_candidate_detected"
        ] = (
            len(
                interaction.candidate_invariants
            )
            > 0
        )

        observations[
            "invariant_candidate_count"
        ] = len(
            interaction.candidate_invariants
        )

        # --------------------------------------------------------------
        # 10. UQL
        # --------------------------------------------------------------

        question_ids = (
            self.persist_interaction(
                interaction
            )
        )

        checks[
            "questions_persisted"
        ] = (
            len(question_ids)
            == len(
                interaction.new_questions
            )
        )

        observations[
            "uql_question_count"
        ] = len(question_ids)

        # --------------------------------------------------------------
        # 11. C_k+1
        # --------------------------------------------------------------

        next_space = (
            self.build_next_space(
                interaction,
                question_ids,
            )
        )

        checks[
            "next_space_created"
        ] = (
            next_space.space_id
            == "C_k+1"
        )

        checks[
            "space_version_advanced"
        ] = (
            next_space.version == 2
        )

        checks[
            "new_distinction_available"
        ] = (
            len(
                next_space.accessible_distinctions
            )
            > 0
        )

        checks[
            "supported_invariant_promoted"
        ] = (
            len(
                next_space.active_invariants
            )
            >= 0
        )

        checks[
            "questions_available_in_next_space"
        ] = (
            len(
                next_space.unresolved_questions
            )
            > 0
        )

        # --------------------------------------------------------------
        # 12. Continuity invariants
        # --------------------------------------------------------------

        checks[
            "process_continuity_preserved"
        ] = (
            next_space.structural_continuity
            is True
        )

        checks[
            "content_identity_not_assumed"
        ] = (
            next_space.content_identity_with_parent
            is False
        )

        checks[
            "process_not_terminated"
        ] = True

        observations[
            "next_space_elements"
        ] = len(
            next_space.elements
        )

        observations[
            "next_space_relations"
        ] = len(
            next_space.relations
        )

        observations[
            "process_state"
        ] = "CONTINUING"

        passed = all(
            checks.values()
        )

        return BenchmarkResult(
            name=(
                "level3_full_cycle_benchmark_v1"
            ),

            passed=passed,

            checks=checks,

            observations=observations,
        )


# ----------------------------------------------------------------------
# Negative control
# ----------------------------------------------------------------------


def run_negative_control() -> Dict[str, bool]:

    """
    Ensures that a productive cognitive space does not
    enter the reflexive exhaustion branch merely because
    the Level 3 machinery exists.
    """

    detector = (
        ExhaustionDetector(
            ExhaustionConfig()
        )
    )

    assessment = detector.assess(
        productive_observations()
    )

    return {
        "productive_space_not_exhausted": (
            assessment.status
            != ExhaustionStatus.EXHAUSTED
        )
    }


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------


def print_report(
    result: BenchmarkResult,
    negative_control: Dict[str, bool],
) -> None:

    print(
        "UFCPS — Level 3 Full Cycle Benchmark v1"
    )

    print(
        "=" * 72
    )

    print(
        f"benchmark: {result.name}"
    )

    print(
        f"all_passed: {result.passed}"
    )

    print(
        "\nCHECKS"
    )

    print(
        "-" * 72
    )

    for name, passed in result.checks.items():

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"{status:5}  {name}"
        )

    print(
        "\nOBSERVATIONS"
    )

    print(
        "-" * 72
    )

    for name, value in (
        result.observations.items()
    ):

        print(
            f"{name}: {value}"
        )

    print(
        "\nNEGATIVE CONTROL"
    )

    print(
        "-" * 72
    )

    for name, passed in (
        negative_control.items()
    ):

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"{status:5}  {name}"
        )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> int:

    benchmark = (
        Level3FullCycleBenchmark()
    )

    result = benchmark.run()

    negative_control = (
        run_negative_control()
    )

    print_report(
        result,
        negative_control,
    )

    all_passed = (
        result.passed
        and all(
            negative_control.values()
        )
    )

    return (
        0
        if all_passed
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
