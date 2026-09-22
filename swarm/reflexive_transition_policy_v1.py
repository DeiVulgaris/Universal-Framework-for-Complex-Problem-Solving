"""
UFCPS — Reflexive Transition Policy v1

Decision layer between Reflection and Orthogonal Transition.

Canonical sequence:

    C_k
      ↓
    Exhaustion
      ↓
    Fr
      ↓
    Reflection
      ↓
    ┌─────────────────────────────┐
    │ local correction            │
    │ continue current space      │
    │ prepare orthogonal move     │
    └─────────────────────────────┘
                  ↓
                 OT

Important:

This module does NOT:
    - perform an orthogonal transition;
    - select an OT mechanism;
    - generate a creative solution;
    - decide whether a transition is scientifically true.

Its function is narrower:

    Reflection → process decision about whether the current
                 cognitive regime should be continued or
                 considered for orthogonal transition.

The policy deliberately separates:

    reflection
    from
    transition execution.

This prevents:

    Fr → automatic OT

from becoming a hidden architectural rule.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List


class TransitionDecision(str, Enum):
    """
    Decision produced after reflection.
    """

    LOCAL_CORRECTION = "LOCAL_CORRECTION"
    CONTINUE_CURRENT_SPACE = "CONTINUE_CURRENT_SPACE"
    PREPARE_ORTHOGONAL_TRANSITION = (
        "PREPARE_ORTHOGONAL_TRANSITION"
    )


class DecisionBasis(str, Enum):
    """
    Structural basis for the policy decision.
    """

    INSUFFICIENT_REFLECTION = "INSUFFICIENT_REFLECTION"
    LOW_PRESSURE = "LOW_PRESSURE"
    CURRENT_SPACE_STILL_PRODUCTIVE = (
        "CURRENT_SPACE_STILL_PRODUCTIVE"
    )
    METHOD_LIMITATION = "METHOD_LIMITATION"
    COGNITIVE_SPACE_LIMITATION = (
        "COGNITIVE_SPACE_LIMITATION"
    )


@dataclass(frozen=True)
class ReflectionDecision:
    """
    Output of the reflexive transition policy.
    """

    decision: TransitionDecision
    basis: DecisionBasis

    reflection_status: str
    reflection_target: str

    pressure: float

    current_space_productive: bool
    method_limitation_detected: bool
    cognitive_space_limitation_detected: bool

    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)

        result["decision"] = self.decision.value
        result["basis"] = self.basis.value

        return result


@dataclass(frozen=True)
class ReflexiveTransitionPolicyConfig:
    """
    Policy thresholds.

    The policy is intentionally conservative:
    strong evidence of a limitation in the current cognitive
    space is required before an OT candidate is prepared.
    """

    minimum_pressure_for_reflection: float = 0.50
    minimum_pressure_for_ot_candidate: float = 0.75


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(minimum, min(maximum, value))


def _value(
    source: Any,
    field: str,
    default: Any,
) -> Any:
    value = getattr(source, field, default)

    if hasattr(value, "value"):
        return value.value

    return value


def evaluate_reflection(
    reflection: Any,
    config: ReflexiveTransitionPolicyConfig = (
        ReflexiveTransitionPolicyConfig()
    ),
) -> ReflectionDecision:
    """
    Evaluate the reflection state and determine the next process action.

    The policy distinguishes three paths:

        1. LOCAL_CORRECTION
        2. CONTINUE_CURRENT_SPACE
        3. PREPARE_ORTHOGONAL_TRANSITION

    OT is never executed here.
    """

    status = str(
        _value(
            reflection,
            "status",
            "INACTIVE",
        )
    )

    target = str(
        _value(
            reflection,
            "target",
            "NONE",
        )
    )

    pressure = _clamp(
        float(
            _value(
                reflection,
                "pressure",
                0.0,
            )
        )
    )

    transition_candidate = bool(
        _value(
            reflection,
            "transition_candidate",
            False,
        )
    )

    if status not in {
        "ACTIVE",
        "COMPLETED",
    }:

        return ReflectionDecision(
            decision=TransitionDecision.CONTINUE_CURRENT_SPACE,
            basis=DecisionBasis.INSUFFICIENT_REFLECTION,
            reflection_status=status,
            reflection_target=target,
            pressure=pressure,
            current_space_productive=True,
            method_limitation_detected=False,
            cognitive_space_limitation_detected=False,
            reasons=[
                "reflection_not_active",
                "orthogonal_transition_not_considered",
            ],
        )

    if pressure < config.minimum_pressure_for_reflection:

        return ReflectionDecision(
            decision=TransitionDecision.CONTINUE_CURRENT_SPACE,
            basis=DecisionBasis.LOW_PRESSURE,
            reflection_status=status,
            reflection_target=target,
            pressure=pressure,
            current_space_productive=True,
            method_limitation_detected=False,
            cognitive_space_limitation_detected=False,
            reasons=[
                "reflection_pressure_below_threshold",
                "current_space_may_remain_productive",
            ],
        )

    if target == "CURRENT_METHOD":

        return ReflectionDecision(
            decision=TransitionDecision.LOCAL_CORRECTION,
            basis=DecisionBasis.METHOD_LIMITATION,
            reflection_status=status,
            reflection_target=target,
            pressure=pressure,
            current_space_productive=True,
            method_limitation_detected=True,
            cognitive_space_limitation_detected=False,
            reasons=[
                "limitation_detected_at_method_level",
                "current_cognitive_space_not_yet_rejected",
                "local_method_correction_is_permitted",
            ],
        )

    if (
        target == "COGNITIVE_SPACE"
        and transition_candidate
        and pressure >= config.minimum_pressure_for_ot_candidate
    ):

        return ReflectionDecision(
            decision=(
                TransitionDecision.PREPARE_ORTHOGONAL_TRANSITION
            ),
            basis=DecisionBasis.COGNITIVE_SPACE_LIMITATION,
            reflection_status=status,
            reflection_target=target,
            pressure=pressure,
            current_space_productive=False,
            method_limitation_detected=True,
            cognitive_space_limitation_detected=True,
            reasons=[
                "current_cognitive_space_is_target_of_reflection",
                "structural_pressure_is_high",
                "orthogonal_transition_candidate_is_permitted",
                "transition_mechanism_remains_open",
            ],
        )

    return ReflectionDecision(
        decision=TransitionDecision.CONTINUE_CURRENT_SPACE,
        basis=DecisionBasis.CURRENT_SPACE_STILL_PRODUCTIVE,
        reflection_status=status,
        reflection_target=target,
        pressure=pressure,
        current_space_productive=True,
        method_limitation_detected=True,
        cognitive_space_limitation_detected=False,
        reasons=[
            "reflection_active",
            "current_space_has_not_been_rejected",
            "continue_observation_before_orthogonal_transition",
        ],
    )


def decide(
    reflection: Any,
    config: ReflexiveTransitionPolicyConfig = (
        ReflexiveTransitionPolicyConfig()
    ),
) -> Dict[str, Any]:
    """
    JSON-serializable convenience wrapper.
    """

    return evaluate_reflection(
        reflection,
        config,
    ).to_dict()


# ---------------------------------------------------------------------------
# Backward-compatible class API
# ---------------------------------------------------------------------------
# The canonical implementation above is functional. Older Level 3
# benchmarks import ReflexiveTransitionPolicy as a class. This adapter
# exposes the existing policy without duplicating or changing its logic.
class ReflexiveTransitionPolicy:
    """
    Compatibility adapter for the functional reflexive transition policy.

    The adapter does not add policy logic. It delegates to the canonical
    evaluate_reflection() and decide() functions above.
    """

    def __init__(
        self,
        config: ReflexiveTransitionPolicyConfig = (
            ReflexiveTransitionPolicyConfig()
        ),
    ) -> None:
        self.config = config

    def evaluate_reflection(
        self,
        reflection: Any,
    ) -> ReflectionDecision:
        return evaluate_reflection(
            reflection,
            self.config,
        )

    def decide(
        self,
        reflection: Any,
    ) -> Dict[str, Any]:
        return decide(
            reflection,
            self.config,
        )

    def evaluate(
        self,
        reflection: Any,
    ) -> ReflectionDecision:
        return self.evaluate_reflection(reflection)


def demo() -> None:
    """
    Demonstrate the three policy paths.
    """

    class LocalMethodReflection:
        status = "ACTIVE"
        target = "CURRENT_METHOD"
        pressure = 0.61
        transition_candidate = False

    class ContinueReflection:
        status = "ACTIVE"
        target = "COGNITIVE_SPACE"
        pressure = 0.64
        transition_candidate = False

    class OTReflection:
        status = "ACTIVE"
        target = "COGNITIVE_SPACE"
        pressure = 0.91
        transition_candidate = True

    examples = [
        (
            "Local correction",
            LocalMethodReflection(),
        ),
        (
            "Continue current space",
            ContinueReflection(),
        ),
        (
            "Prepare orthogonal transition",
            OTReflection(),
        ),
    ]

    for name, reflection in examples:

        result = evaluate_reflection(
            reflection
        )

        print(f"\n{name}:")
        print(result.to_dict())


if __name__ == "__main__":
    demo()
