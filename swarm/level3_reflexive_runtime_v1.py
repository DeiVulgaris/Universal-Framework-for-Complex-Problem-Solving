"""
UFCPS — Level 3 Reflexive Runtime v1

Integrated execution layer for the Level 3 reflexive cycle.

Canonical process:

    Observation
        ↓
    Cognitive Space Assessment
        ↓
    Frustration
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
    CONTINUE_CURRENT_SPACE
        or
    LOCAL_CORRECTION
        or
    PREPARE_ORTHOGONAL_TRANSITION

Important architectural boundary:

    This runtime does NOT:
        - execute an orthogonal transition;
        - select an OT mechanism;
        - construct C_k+1;
        - generate a creative solution;
        - claim consciousness or phenomenology.

It integrates the Level 3 components and produces a
process decision that can be consumed by a later OT layer.

The runtime therefore implements:

    cognition → reflection → transition readiness

rather than:

    cognition → automatic creativity.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

from cognitive_space_exhaustion_v1 import (
    CognitiveObservation,
    CognitiveSpaceExhaustionDetector,
    ExhaustionConfig,
)

from frustration_v1 import (
    FrustrationConfig,
    FrustrationState,
    from_exhaustion_assessment,
)

from reflection_v1 import (
    ReflectionConfig,
    ReflectionState,
    WorldModel,
    SelfModel,
    SelfWorldRelationModel,
    ModelOfKnowing,
    from_frustration,
)

from reflexive_transition_policy_v1 import (
    ReflexiveTransitionPolicyConfig,
    ReflectionDecision,
    TransitionDecision,
    evaluate_reflection,
)


class RuntimeDecision(str, Enum):
    """
    Top-level decision emitted by the Level 3 runtime.
    """

    CONTINUE_CURRENT_SPACE = "CONTINUE_CURRENT_SPACE"
    LOCAL_CORRECTION = "LOCAL_CORRECTION"
    PREPARE_ORTHOGONAL_TRANSITION = (
        "PREPARE_ORTHOGONAL_TRANSITION"
    )


@dataclass(frozen=True)
class RuntimeConfig:
    """
    Configuration of the complete Level 3 reflexive runtime.
    """

    exhaustion: ExhaustionConfig = ExhaustionConfig()
    frustration: FrustrationConfig = FrustrationConfig()
    reflection: ReflectionConfig = ReflectionConfig()
    policy: ReflexiveTransitionPolicyConfig = (
        ReflexiveTransitionPolicyConfig()
    )


@dataclass(frozen=True)
class RuntimeState:
    """
    Complete state produced by one Level 3 runtime evaluation.
    """

    runtime_version: str

    decision: RuntimeDecision

    exhaustion_status: str
    frustration_status: str
    reflection_status: str

    reflection_target: str
    policy_basis: str

    self_world_differentiated: bool

    world_model_available: bool
    self_model_available: bool
    relation_model_available: bool
    model_of_knowing_available: bool

    transition_candidate: bool

    evidence: List[str]

    description: str

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)

        result["decision"] = self.decision.value

        return result


class Level3ReflexiveRuntime:
    """
    Integrated Level 3 runtime.

    The runtime composes existing modules rather than duplicating
    their internal logic.
    """

    VERSION = "1.0"

    def __init__(
        self,
        config: RuntimeConfig = RuntimeConfig(),
    ) -> None:

        self.config = config

        self.exhaustion_detector = (
            CognitiveSpaceExhaustionDetector(
                config=self.config.exhaustion
            )
        )

    # ------------------------------------------------------------------
    # Cognitive-space assessment
    # ------------------------------------------------------------------

    def assess_cognitive_space(
        self,
        observations: List[CognitiveObservation],
    ) -> Any:
        """
        Assess whether the current cognitive-space regime
        remains productive.
        """

        return self.exhaustion_detector.assess(
            observations
        )

    # ------------------------------------------------------------------
    # Frustration
    # ------------------------------------------------------------------

    def assess_frustration(
        self,
        exhaustion_assessment: Any,
    ) -> FrustrationState:
        """
        Convert cognitive-space exhaustion into functional Fr.
        """

        return from_exhaustion_assessment(
            exhaustion_assessment,
            self.config.frustration,
        )

    # ------------------------------------------------------------------
    # Reflection
    # ------------------------------------------------------------------

    def assess_reflection(
        self,
        frustration: FrustrationState,
        *,
        world_model: Optional[WorldModel] = None,
        self_model: Optional[SelfModel] = None,
        relation_model: Optional[SelfWorldRelationModel] = None,
        model_of_knowing: Optional[ModelOfKnowing] = None,
    ) -> ReflectionState:
        """
        Perform Level 3 Self–World reflection.
        """

        return from_frustration(
            frustration,
            world_model=world_model,
            self_model=self_model,
            relation_model=relation_model,
            model_of_knowing=model_of_knowing,
            config=self.config.reflection,
        )

    # ------------------------------------------------------------------
    # Reflexive policy
    # ------------------------------------------------------------------

    def evaluate_policy(
        self,
        reflection: ReflectionState,
    ) -> ReflectionDecision:
        """
        Decide what the process should do next.

        This does NOT execute OT.
        """

        return evaluate_reflection(
            reflection,
            self.config.policy,
        )

    # ------------------------------------------------------------------
    # Complete cycle
    # ------------------------------------------------------------------

    def run(
        self,
        observations: List[CognitiveObservation],
        *,
        world_model: Optional[WorldModel] = None,
        self_model: Optional[SelfModel] = None,
        relation_model: Optional[SelfWorldRelationModel] = None,
        model_of_knowing: Optional[ModelOfKnowing] = None,
    ) -> RuntimeState:
        """
        Execute one complete Level 3 reflexive evaluation.

        The process stops at transition preparation.

        It does not construct or execute C_k+1.
        """

        exhaustion = self.assess_cognitive_space(
            observations
        )

        frustration = self.assess_frustration(
            exhaustion
        )

        reflection = self.assess_reflection(
            frustration,
            world_model=world_model,
            self_model=self_model,
            relation_model=relation_model,
            model_of_knowing=model_of_knowing,
        )

        policy = self.evaluate_policy(
            reflection
        )

        decision = self._map_policy_decision(
            policy.decision
        )

        evidence: List[str] = []

        evidence.extend(
            getattr(
                exhaustion,
                "reasons",
                [],
            )
        )

        evidence.extend(
            getattr(
                reflection,
                "evidence",
                [],
            )
        )

        evidence.extend(
            policy.reasons
        )

        evidence = self._deduplicate(
            evidence
        )

        description = self._build_description(
            decision,
            exhaustion,
            frustration,
            reflection,
            policy,
        )

        return RuntimeState(
            runtime_version=self.VERSION,

            decision=decision,

            exhaustion_status=(
                self._enum_value(
                    exhaustion.status
                )
            ),

            frustration_status=(
                self._enum_value(
                    frustration.status
                )
            ),

            reflection_status=(
                self._enum_value(
                    reflection.status
                )
            ),

            reflection_target=(
                self._enum_value(
                    reflection.target
                )
            ),

            policy_basis=(
                self._enum_value(
                    policy.basis
                )
            ),

            self_world_differentiated=(
                reflection.self_world_differentiated
            ),

            world_model_available=(
                reflection.world_model_available
            ),

            self_model_available=(
                reflection.self_model_available
            ),

            relation_model_available=(
                reflection.relation_model_available
            ),

            model_of_knowing_available=(
                reflection.model_of_knowing_available
            ),

            transition_candidate=(
                reflection.transition_candidate
            ),

            evidence=evidence,

            description=description,
        )

    # ------------------------------------------------------------------
    # Decision mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _map_policy_decision(
        decision: TransitionDecision,
    ) -> RuntimeDecision:

        if decision == TransitionDecision.LOCAL_CORRECTION:
            return RuntimeDecision.LOCAL_CORRECTION

        if (
            decision
            == TransitionDecision.PREPARE_ORTHOGONAL_TRANSITION
        ):
            return (
                RuntimeDecision.PREPARE_ORTHOGONAL_TRANSITION
            )

        return RuntimeDecision.CONTINUE_CURRENT_SPACE

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _enum_value(
        value: Any,
    ) -> str:

        if hasattr(value, "value"):
            return str(value.value)

        return str(value)

    @staticmethod
    def _deduplicate(
        values: List[str],
    ) -> List[str]:

        result: List[str] = []

        for value in values:

            if value not in result:
                result.append(value)

        return result

    @staticmethod
    def _build_description(
        decision: RuntimeDecision,
        exhaustion: Any,
        frustration: FrustrationState,
        reflection: ReflectionState,
        policy: ReflectionDecision,
    ) -> str:

        if (
            decision
            == RuntimeDecision.PREPARE_ORTHOGONAL_TRANSITION
        ):
            return (
                "The current cognitive-space regime has reached "
                "functional exhaustion; Self–World reflexive modeling "
                "is available and the process is permitted to prepare "
                "an orthogonal transition. No transition has yet "
                "been executed."
            )

        if decision == RuntimeDecision.LOCAL_CORRECTION:
            return (
                "Reflection identified a limitation at the level of "
                "the current method. Local correction remains possible "
                "without changing the cognitive space."
            )

        if (
            frustration.status.value == "NONE"
        ):
            return (
                "The current cognitive-space regime remains sufficiently "
                "productive for continued operation."
            )

        if (
            reflection.status.value == "TRIGGERED"
        ):
            return (
                "Functional frustration has triggered reflection, "
                "but the reflexive structure is not yet sufficient "
                "to prepare an orthogonal transition."
            )

        return (
            "The process remains within the current cognitive-space "
            "regime."
        )


# ----------------------------------------------------------------------
# Convenience API
# ----------------------------------------------------------------------


def run_reflexive_cycle(
    observations: List[CognitiveObservation],
    *,
    world_model: Optional[WorldModel] = None,
    self_model: Optional[SelfModel] = None,
    relation_model: Optional[SelfWorldRelationModel] = None,
    model_of_knowing: Optional[ModelOfKnowing] = None,
    config: RuntimeConfig = RuntimeConfig(),
) -> Dict[str, Any]:
    """
    Run the complete Level 3 cycle and return JSON-compatible state.
    """

    runtime = Level3ReflexiveRuntime(
        config=config
    )

    state = runtime.run(
        observations,
        world_model=world_model,
        self_model=self_model,
        relation_model=relation_model,
        model_of_knowing=model_of_knowing,
    )

    return state.to_dict()


# ----------------------------------------------------------------------
# Demonstration
# ----------------------------------------------------------------------


def demo() -> None:
    """
    Demonstrate the complete Level 3 runtime.

    The demonstration intentionally supplies an exhausted cognitive
    trajectory and complete Self–World models.

    Expected final decision:

        PREPARE_ORTHOGONAL_TRANSITION

    The runtime must not execute OT.
    """

    observations = [
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

    world_model = WorldModel(
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

    self_model = SelfModel(
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

    relation_model = SelfWorldRelationModel(
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

    runtime = Level3ReflexiveRuntime()

    result = runtime.run(
        observations,
        world_model=world_model,
        self_model=self_model,
        relation_model=relation_model,
    )

    print(
        "UFCPS Level 3 Reflexive Runtime v1"
    )
    print("=" * 48)

    print(
        result.to_dict()
    )


if __name__ == "__main__":
    demo()
