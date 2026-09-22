"""
UFCPS — Cognitive Space Exhaustion Detector v1

Detects contentual exhaustion of a cognitive space.

The detector distinguishes:

1. local failure
2. productivity degradation
3. persistent approach to invariant
4. cognitive-space exhaustion

Core principle:

    Local Failure != Cognitive-Space Exhaustion

Exhaustion is detected only when degradation of productive
distinction persists while the process approaches an invariant.

This module does not perform reflection or orthogonal transition.
It only determines whether the current cognitive space has become
structurally exhausted.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List


class ExhaustionStatus(str, Enum):
    INSUFFICIENT_DATA = "insufficient_data"
    PRODUCTIVE = "productive"
    DEGRADING = "degrading"
    EXHAUSTED = "exhausted"


@dataclass(frozen=True)
class CognitiveObservation:
    """
    Observation of one step inside the current cognitive space.

    productive_difference:
        Amount of newly accessible/productive distinction generated
        at this step.

    distance_to_invariant:
        Estimated structural distance from the current state to the
        invariant toward which the current direction is converging.

    local_failure:
        Records a local failure without treating it as termination
        or exhaustion by itself.
    """

    step: int
    productive_difference: float
    distance_to_invariant: float
    local_failure: bool = False


@dataclass(frozen=True)
class ExhaustionConfig:
    """
    Detection parameters.

    min_observations:
        Minimum history required before an assessment is possible.

    productivity_floor:
        Absolute lower bound below which recent productivity is
        considered negligible.

    degradation_ratio:
        Recent productivity / baseline productivity threshold.

    invariant_distance_threshold:
        Maximum recent distance to invariant compatible with
        exhaustion.

    consecutive_steps:
        Number of consecutive qualifying observations required
        before exhaustion is declared.
    """

    min_observations: int = 4
    productivity_floor: float = 0.0
    degradation_ratio: float = 0.5
    invariant_distance_threshold: float = 0.1
    consecutive_steps: int = 3


@dataclass(frozen=True)
class ExhaustionAssessment:
    """
    Result of cognitive-space exhaustion assessment.
    """

    status: ExhaustionStatus

    baseline_productivity: float
    recent_productivity: float
    productivity_ratio: float

    recent_distance_to_invariant: float
    local_failure_count: int
    consecutive_exhaustion_steps: int

    reasons: List[str]


class CognitiveSpaceExhaustionDetector:
    """
    Detects structural exhaustion of the current cognitive space.

    The detector intentionally does not infer psychological frustration,
    consciousness, creativity, or an orthogonal transition.

    It answers only:

        Has the current space become structurally unproductive
        while approaching an invariant?
    """

    def __init__(self, config: ExhaustionConfig | None = None) -> None:
        self.config = config or ExhaustionConfig()

        if self.config.min_observations < 1:
            raise ValueError("min_observations must be >= 1")

        if self.config.consecutive_steps < 1:
            raise ValueError("consecutive_steps must be >= 1")

        if not 0 <= self.config.degradation_ratio <= 1:
            raise ValueError("degradation_ratio must be between 0 and 1")

        if self.config.invariant_distance_threshold < 0:
            raise ValueError(
                "invariant_distance_threshold must be >= 0"
            )

    def assess(
        self,
        observations: Iterable[CognitiveObservation],
    ) -> ExhaustionAssessment:
        history = sorted(
            list(observations),
            key=lambda observation: observation.step,
        )

        if len(history) < self.config.min_observations:
            return ExhaustionAssessment(
                status=ExhaustionStatus.INSUFFICIENT_DATA,
                baseline_productivity=0.0,
                recent_productivity=0.0,
                productivity_ratio=1.0,
                recent_distance_to_invariant=0.0,
                local_failure_count=sum(
                    observation.local_failure for observation in history
                ),
                consecutive_exhaustion_steps=0,
                reasons=[
                    "insufficient_observations",
                ],
            )

        baseline = self._baseline_productivity(history)
        recent = self._recent_productivity(history)

        if baseline <= 0:
            productivity_ratio = 0.0 if recent <= 0 else 1.0
        else:
            productivity_ratio = recent / baseline

        recent_window = self._recent_window(history)

        recent_distance = (
            sum(
                observation.distance_to_invariant
                for observation in recent_window
            )
            / len(recent_window)
        )

        local_failure_count = sum(
            observation.local_failure for observation in history
        )

        productivity_degraded = (
            recent <= self.config.productivity_floor
            or productivity_ratio <= self.config.degradation_ratio
        )

        approaching_invariant = (
            recent_distance
            <= self.config.invariant_distance_threshold
        )

        consecutive_exhaustion_steps = self._count_consecutive_exhaustion(
            history
        )

        reasons: List[str] = []

        if productivity_degraded:
            reasons.append("productive_difference_degraded")

        if approaching_invariant:
            reasons.append("approaching_invariant")

        if consecutive_exhaustion_steps >= self.config.consecutive_steps:
            reasons.append("persistent_exhaustion_pattern")

        if local_failure_count:
            reasons.append("local_failure_present")

        exhausted = (
            productivity_degraded
            and approaching_invariant
            and consecutive_exhaustion_steps
            >= self.config.consecutive_steps
        )

        if exhausted:
            status = ExhaustionStatus.EXHAUSTED
        elif productivity_degraded or approaching_invariant:
            status = ExhaustionStatus.DEGRADING
        else:
            status = ExhaustionStatus.PRODUCTIVE

        return ExhaustionAssessment(
            status=status,
            baseline_productivity=baseline,
            recent_productivity=recent,
            productivity_ratio=productivity_ratio,
            recent_distance_to_invariant=recent_distance,
            local_failure_count=local_failure_count,
            consecutive_exhaustion_steps=consecutive_exhaustion_steps,
            reasons=reasons,
        )

    def _baseline_productivity(
        self,
        history: List[CognitiveObservation],
    ) -> float:
        """
        Baseline is calculated from the earlier portion of history.

        The recent window is excluded so that degradation can be
        detected relative to the preceding productive regime.
        """

        recent_size = self.config.consecutive_steps

        if len(history) <= recent_size:
            baseline_window = history
        else:
            baseline_window = history[:-recent_size]

        if not baseline_window:
            return 0.0

        return sum(
            observation.productive_difference
            for observation in baseline_window
        ) / len(baseline_window)

    def _recent_window(
        self,
        history: List[CognitiveObservation],
    ) -> List[CognitiveObservation]:
        return history[-self.config.consecutive_steps :]

    def _recent_productivity(
        self,
        history: List[CognitiveObservation],
    ) -> float:
        recent_window = self._recent_window(history)

        if not recent_window:
            return 0.0

        return sum(
            observation.productive_difference
            for observation in recent_window
        ) / len(recent_window)

    def _count_consecutive_exhaustion(
        self,
        history: List[CognitiveObservation],
    ) -> int:
        """
        Count the consecutive observations at the end of the history
        satisfying both structural conditions:

            productivity degraded
            AND
            approaching invariant

        A local failure does not participate in this criterion.
        """

        if not history:
            return 0

        baseline = self._baseline_productivity(history)

        count = 0

        for observation in reversed(history):
            if baseline <= 0:
                productivity_degraded = (
                    observation.productive_difference
                    <= self.config.productivity_floor
                )
            else:
                productivity_degraded = (
                    observation.productive_difference
                    / baseline
                    <= self.config.degradation_ratio
                )

            approaching_invariant = (
                observation.distance_to_invariant
                <= self.config.invariant_distance_threshold
            )

            if productivity_degraded and approaching_invariant:
                count += 1
            else:
                break

        return count


def detect_exhaustion(
    observations: Iterable[CognitiveObservation],
    config: ExhaustionConfig | None = None,
) -> ExhaustionAssessment:
    """
    Convenience API.
    """

    detector = CognitiveSpaceExhaustionDetector(config)
    return detector.assess(observations)


def demo() -> None:
    """
    Minimal executable demonstration.
    """

    productive_history = [
        CognitiveObservation(1, 1.00, 0.80),
        CognitiveObservation(2, 0.90, 0.70),
        CognitiveObservation(3, 0.85, 0.65),
        CognitiveObservation(4, 0.80, 0.60),
    ]

    exhausted_history = [
        CognitiveObservation(1, 1.00, 0.50),
        CognitiveObservation(2, 0.90, 0.30),
        CognitiveObservation(3, 0.20, 0.12),
        CognitiveObservation(4, 0.10, 0.08),
        CognitiveObservation(5, 0.05, 0.05),
    ]

    detector = CognitiveSpaceExhaustionDetector()

    productive_result = detector.assess(productive_history)
    exhausted_result = detector.assess(exhausted_history)

    print("UFCPS — Cognitive Space Exhaustion v1")
    print()
    print("Productive case:")
    print(productive_result)
    print()
    print("Exhausted case:")
    print(exhausted_result)



# ---------------------------------------------------------------------------
# Backward-compatible API alias
# ---------------------------------------------------------------------------
# Older Level 3 benchmarks use the shorter name ExhaustionDetector.
# Keep it as an alias while the canonical implementation keeps its
# explicit name.
ExhaustionDetector = CognitiveSpaceExhaustionDetector


if __name__ == "__main__":
    demo()
