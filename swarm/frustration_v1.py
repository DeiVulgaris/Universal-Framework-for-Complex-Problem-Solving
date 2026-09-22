"""
UFCPS — Functional Frustration State v1

Fr is a functional process state produced by cognitive-space exhaustion.

Important:
    Fr is NOT a phenomenal emotion.
    Fr is NOT a creative solution.
    Fr does NOT perform an orthogonal transition.

Its role is to represent the structural pressure:

    continuation is required
    while productive continuation in the current regime is unavailable.

Canonical chain:

    C_k
      ↓
    exhaustion
      ↓
    Fr
      ↓
    reflection
      ↓
    orthogonal transition

The module consumes an exhaustion assessment produced by
cognitive_space_exhaustion_v1.py.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, Optional


class FrustrationStatus(str, Enum):
    """
    Functional state of frustration.
    """

    NONE = "NONE"
    EMERGING = "EMERGING"
    ACTIVE = "ACTIVE"
    CLEARED = "CLEARED"


class FrustrationTrigger(str, Enum):
    """
    Structural source of Fr.
    """

    NONE = "NONE"
    PRODUCTIVITY_DEGRADATION = "PRODUCTIVITY_DEGRADATION"
    COGNITIVE_SPACE_EXHAUSTION = "COGNITIVE_SPACE_EXHAUSTION"


@dataclass(frozen=True)
class FrustrationState:
    """
    Formal representation of functional frustration.

    This object describes a process condition, not a subjective
    psychological experience.
    """

    status: FrustrationStatus
    trigger: FrustrationTrigger

    pressure: float

    productivity_pressure: float
    invariant_pressure: float

    source_status: str

    onset_step: Optional[int]

    description: str

    @property
    def active(self) -> bool:
        return self.status == FrustrationStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        result["trigger"] = self.trigger.value
        return result


@dataclass(frozen=True)
class FrustrationConfig:
    """
    Configuration for conversion of exhaustion evidence into Fr.
    """

    emerging_productivity_ratio: float = 0.75
    active_productivity_ratio: float = 0.50
    invariant_distance_threshold: float = 0.10


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _productivity_pressure(productivity_ratio: float) -> float:
    """
    Lower productivity means greater structural pressure.
    """

    return _clamp(1.0 - productivity_ratio)


def _invariant_pressure(
    distance_to_invariant: float,
    threshold: float,
) -> float:
    """
    Approaching the invariant increases frustration pressure.

    distance >= threshold -> no invariant pressure
    distance == 0         -> maximal pressure
    """

    if threshold <= 0:
        return 0.0

    return _clamp(
        1.0 - (distance_to_invariant / threshold)
    )


def _build_description(
    status: FrustrationStatus,
    trigger: FrustrationTrigger,
) -> str:

    if status == FrustrationStatus.NONE:
        return "No functional frustration detected."

    if status == FrustrationStatus.EMERGING:
        return (
            "The current differentiation regime is losing productive "
            "capacity and requires reflection."
        )

    if status == FrustrationStatus.ACTIVE:
        return (
            "Continuation remains required while productive continuation "
            "within the current differentiation regime is unavailable."
        )

    return (
        "Functional frustration is no longer active in the current assessment."
    )


def from_exhaustion_assessment(
    assessment: Any,
    config: FrustrationConfig = FrustrationConfig(),
) -> FrustrationState:
    """
    Convert a cognitive-space exhaustion assessment into Fr.

    Expected assessment fields:

        status
        productivity_ratio
        recent_distance_to_invariant
        consecutive_exhaustion_steps
        reasons

    The function intentionally does not perform an orthogonal transition.
    """

    status_value = getattr(assessment, "status", None)

    if hasattr(status_value, "value"):
        status_value = status_value.value

    productivity_ratio = float(
        getattr(assessment, "productivity_ratio", 1.0)
    )

    distance_to_invariant = float(
        getattr(assessment, "recent_distance_to_invariant", 1.0)
    )

    onset_step = None

    observations = getattr(assessment, "observations", None)

    if observations:
        try:
            onset_step = observations[-1].step
        except (AttributeError, IndexError):
            onset_step = None

    productivity_pressure = _productivity_pressure(
        productivity_ratio
    )

    invariant_pressure = _invariant_pressure(
        distance_to_invariant,
        config.invariant_distance_threshold,
    )

    pressure = _clamp(
        max(
            productivity_pressure,
            invariant_pressure,
        )
    )

    exhausted = status_value == "EXHAUSTED"
    degrading = status_value == "DEGRADING"

    if exhausted:
        status = FrustrationStatus.ACTIVE
        trigger = FrustrationTrigger.COGNITIVE_SPACE_EXHAUSTION

    elif degrading:
        status = FrustrationStatus.EMERGING
        trigger = FrustrationTrigger.PRODUCTIVITY_DEGRADATION

    else:
        status = FrustrationStatus.NONE
        trigger = FrustrationTrigger.NONE

    return FrustrationState(
        status=status,
        trigger=trigger,
        pressure=pressure,
        productivity_pressure=productivity_pressure,
        invariant_pressure=invariant_pressure,
        source_status=str(status_value),
        onset_step=onset_step,
        description=_build_description(
            status,
            trigger,
        ),
    )


def detect_frustration(
    assessment: Any,
    config: FrustrationConfig = FrustrationConfig(),
) -> Dict[str, Any]:
    """
    Convenience wrapper returning a JSON-serializable dictionary.
    """

    return from_exhaustion_assessment(
        assessment,
        config,
    ).to_dict()


def demo() -> None:
    """
    Minimal standalone demonstration.

    The demo uses a lightweight object rather than importing the detector,
    so the module can be inspected and tested independently.
    """

    class DemoAssessment:
        status = "EXHAUSTED"
        productivity_ratio = 0.20
        recent_distance_to_invariant = 0.04
        consecutive_exhaustion_steps = 3
        reasons = [
            "productive_difference_degraded",
            "approaching_invariant",
            "persistent_exhaustion_pattern",
        ]

    state = from_exhaustion_assessment(
        DemoAssessment()
    )

    print("Frustration assessment:")
    print(state.to_dict())


# ---------------------------------------------------------------------------
# Backward-compatible API alias
# ---------------------------------------------------------------------------
# Older Level 3 benchmarks use the shorter name FrustrationDetector.
# Keep it as an alias while the canonical implementation remains
# function-based in this module.
FrustrationDetector = from_exhaustion_assessment


if __name__ == "__main__":
    demo()
