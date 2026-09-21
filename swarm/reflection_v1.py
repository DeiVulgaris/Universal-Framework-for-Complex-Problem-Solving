"""
UFCPS — Reflection State v1

Reflection is the process-level transition in which the system turns
the current mode of differentiation into an object of investigation.

Canonical sequence:

    C_k
      ↓
    exhaustion
      ↓
    Fr
      ↓
    reflection
      ↓
    orthogonal transition

Reflection does NOT:
    - solve the original task;
    - perform the orthogonal transition;
    - select a new cognitive space;
    - assume that exhaustion automatically implies creativity.

Its function is to change the target of investigation:

    from:
        "What answer is missing?"

    to:
        "What limitation belongs to the current way of generating
         distinctions?"

This module is deliberately functional and process-level.
It makes no claim about phenomenal consciousness.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class ReflectionStatus(str, Enum):
    """
    Functional state of reflection.
    """

    INACTIVE = "INACTIVE"
    TRIGGERED = "TRIGGERED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class ReflectionTarget(str, Enum):
    """
    What the process turns into an object of investigation.
    """

    NONE = "NONE"
    CURRENT_RESULT = "CURRENT_RESULT"
    CURRENT_METHOD = "CURRENT_METHOD"
    COGNITIVE_SPACE = "COGNITIVE_SPACE"
    ACTUALIZATION_MODE = "ACTUALIZATION_MODE"


class ReflectionOutcome(str, Enum):
    """
    Result of the reflection phase.

    Reflection does not itself perform the transition.
    """

    NONE = "NONE"
    LOCAL_CORRECTION = "LOCAL_CORRECTION"
    CONTINUE_CURRENT_SPACE = "CONTINUE_CURRENT_SPACE"
    PREPARE_ORTHOGONAL_TRANSITION = "PREPARE_ORTHOGONAL_TRANSITION"


@dataclass(frozen=True)
class ReflectionState:
    """
    Formal representation of process-level reflection.

    Reflection is represented as a change in the target of cognition,
    not as a claim about subjective experience.
    """

    status: ReflectionStatus
    target: ReflectionTarget
    outcome: ReflectionOutcome

    source_frustration_status: str
    source_trigger: str

    pressure: float

    current_method_question: str
    space_question: str

    evidence: List[str]

    transition_candidate: bool

    description: str

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)

        result["status"] = self.status.value
        result["target"] = self.target.value
        result["outcome"] = self.outcome.value

        return result


@dataclass(frozen=True)
class ReflectionConfig:
    """
    Configuration controlling when Fr is strong enough to trigger
    process-level reflection.
    """

    activation_pressure: float = 0.50
    exhaustion_required: bool = True


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(minimum, min(maximum, value))


def _get_value(
    source: Any,
    name: str,
    default: Any,
) -> Any:
    return getattr(source, name, default)


def from_frustration(
    frustration: Any,
    config: ReflectionConfig = ReflectionConfig(),
) -> ReflectionState:
    """
    Convert a functional frustration state into a reflection state.

    Expected frustration fields:

        status
        trigger
        pressure
        description

    Reflection activates only when Fr carries sufficient structural
    pressure.

    The function does not perform an orthogonal transition.
    """

    raw_status = _get_value(
        frustration,
        "status",
        ReflectionStatus.INACTIVE,
    )

    raw_trigger = _get_value(
        frustration,
        "trigger",
        "NONE",
    )

    if hasattr(raw_status, "value"):
        raw_status = raw_status.value

    if hasattr(raw_trigger, "value"):
        raw_trigger = raw_trigger.value

    pressure = _clamp(
        float(
            _get_value(
                frustration,
                "pressure",
                0.0,
            )
        )
    )

    active_frustration = raw_status == "ACTIVE"
    emerging_frustration = raw_status == "EMERGING"

    if active_frustration and pressure >= config.activation_pressure:
        status = ReflectionStatus.ACTIVE
        target = ReflectionTarget.COGNITIVE_SPACE
        outcome = ReflectionOutcome.PREPARE_ORTHOGONAL_TRANSITION

        transition_candidate = True

        evidence = [
            "functional_frustration_active",
            "productive_continuation_is_under_pressure",
            "current_differentiation_regime_requires_examination",
        ]

        description = (
            "The process turns the current mode of differentiation "
            "into an object of investigation."
        )

    elif emerging_frustration and pressure >= config.activation_pressure:
        status = ReflectionStatus.TRIGGERED
        target = ReflectionTarget.CURRENT_METHOD
        outcome = ReflectionOutcome.CONTINUE_CURRENT_SPACE

        transition_candidate = False

        evidence = [
            "functional_frustration_emerging",
            "methodological_limitation_requires_examination",
        ]

        description = (
            "The process begins examining whether the limitation "
            "belongs to its current method of differentiation."
        )

    else:
        status = ReflectionStatus.INACTIVE
        target = ReflectionTarget.NONE
        outcome = ReflectionOutcome.NONE

        transition_candidate = False

        evidence = []

        description = (
            "No process-level reflection is activated by the current state."
        )

    current_method_question = (
        "Is the limitation caused by the current method of generating "
        "distinctions rather than by the absence of a local answer?"
    )

    space_question = (
        "Has the current cognitive space itself become insufficient "
        "for further productive differentiation?"
    )

    return ReflectionState(
        status=status,
        target=target,
        outcome=outcome,
        source_frustration_status=str(raw_status),
        source_trigger=str(raw_trigger),
        pressure=pressure,
        current_method_question=current_method_question,
        space_question=space_question,
        evidence=evidence,
        transition_candidate=transition_candidate,
        description=description,
    )


def reflect_on_frustration(
    frustration: Any,
    config: ReflectionConfig = ReflectionConfig(),
) -> Dict[str, Any]:
    """
    Convenience wrapper returning a JSON-serializable result.
    """

    return from_frustration(
        frustration,
        config,
    ).to_dict()


def demo() -> None:
    """
    Standalone demonstration.
    """

    class DemoFrustration:
        status = "ACTIVE"
        trigger = "COGNITIVE_SPACE_EXHAUSTION"
        pressure = 0.91
        description = (
            "Continuation remains required while productive continuation "
            "within the current regime is unavailable."
        )

    state = from_frustration(
        DemoFrustration()
    )

    print("Reflection assessment:")
    print(state.to_dict())


if __name__ == "__main__":
    demo()
