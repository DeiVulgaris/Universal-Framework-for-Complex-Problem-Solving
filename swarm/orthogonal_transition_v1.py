"""
UFCPS — Orthogonal Transition v1

An orthogonal transition (OT) changes the conditions under which
subsequent distinctions can be generated.

Canonical sequence:

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
    C_k+1

Important architectural constraints:

    OT != random variation
    OT != local retry
    OT != parameter adjustment
    OT != mere scale change
    OT != one predefined mechanism

This module does NOT prescribe how the new regime is realized.

Instead, it validates whether a proposed transition candidate
satisfies the minimal structural requirements of OT.

Candidate realization mechanisms may include:

    - scale transition
    - compensatory multiplication
    - structural reconfiguration
    - carrier transition
    - interaction-regime transition
    - representation-space transition
    - composition/decomposition transition
    - unknown/emergent mechanism

No candidate mechanism is constitutive of OT.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List


class TransitionStatus(str, Enum):
    """
    Functional status of an orthogonal transition candidate.
    """

    REJECTED = "REJECTED"
    CANDIDATE = "CANDIDATE"
    ACCEPTED = "ACCEPTED"


class TransitionMechanism(str, Enum):
    """
    Candidate realization mechanisms.

    The list is intentionally open.
    """

    SCALE = "SCALE"
    COMPENSATORY_MULTIPLICATION = "COMPENSATORY_MULTIPLICATION"
    STRUCTURAL_RECONFIGURATION = "STRUCTURAL_RECONFIGURATION"
    CARRIER_TRANSITION = "CARRIER_TRANSITION"
    INTERACTION_REGIME = "INTERACTION_REGIME"
    REPRESENTATION_SPACE = "REPRESENTATION_SPACE"
    COMPOSITION_DECOMPOSITION = "COMPOSITION_DECOMPOSITION"
    UNKNOWN_EMERGENT = "UNKNOWN_EMERGENT"


@dataclass(frozen=True)
class TransitionCandidate:
    """
    Proposed transition from C_k to C_k+1.

    The fields describe structural properties of the proposed
    transition. They do not claim that the transition is physically
    or cognitively valid beyond the specified evidence.
    """

    mechanism: TransitionMechanism

    source_space: str
    target_space: str

    preserves_process_continuity: bool
    changes_differentiation_conditions: bool
    restores_productive_differentiation: bool

    merely_retries_current_space: bool
    merely_changes_parameters: bool
    merely_changes_quantity: bool

    evidence: List[str]

    description: str

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["mechanism"] = self.mechanism.value
        return result


@dataclass(frozen=True)
class OrthogonalTransitionResult:
    """
    Result of structural evaluation of an OT candidate.
    """

    status: TransitionStatus

    mechanism: str

    source_space: str
    target_space: str

    reasons: List[str]

    preserved_continuity: bool
    changed_differentiation_conditions: bool
    restored_productivity: bool

    orthogonal: bool

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        return result


def evaluate_transition(
    candidate: TransitionCandidate,
) -> OrthogonalTransitionResult:
    """
    Evaluate a proposed transition against the minimal OT criteria.

    Minimal positive criteria:

        1. process continuity is preserved;
        2. conditions of differentiation change;
        3. productive differentiation is restored or expanded.

    Explicit rejection conditions:

        - merely retrying the current space;
        - merely changing parameters;
        - merely increasing quantity.

    The evaluator does not select mechanisms and does not execute
    the transition.
    """

    reasons: List[str] = []

    if not candidate.preserves_process_continuity:
        reasons.append(
            "process_continuity_not_preserved"
        )

    if not candidate.changes_differentiation_conditions:
        reasons.append(
            "differentiation_conditions_unchanged"
        )

    if not candidate.restores_productive_differentiation:
        reasons.append(
            "productive_differentiation_not_restored"
        )

    if candidate.merely_retries_current_space:
        reasons.append(
            "merely_retries_current_space"
        )

    if candidate.merely_changes_parameters:
        reasons.append(
            "merely_changes_parameters"
        )

    if candidate.merely_changes_quantity:
        reasons.append(
            "merely_changes_quantity"
        )

    hard_rejection = (
        not candidate.preserves_process_continuity
        or not candidate.changes_differentiation_conditions
        or not candidate.restores_productive_differentiation
        or candidate.merely_retries_current_space
        or candidate.merely_changes_parameters
        or candidate.merely_changes_quantity
    )

    if hard_rejection:
        status = TransitionStatus.REJECTED
        orthogonal = False

    else:
        status = TransitionStatus.ACCEPTED
        orthogonal = True

        reasons.append(
            "conditions_of_further_differentiation_changed"
        )

        reasons.append(
            "productive_differentiation_restored_or_expanded"
        )

    return OrthogonalTransitionResult(
        status=status,
        mechanism=candidate.mechanism.value,
        source_space=candidate.source_space,
        target_space=candidate.target_space,
        reasons=reasons,
        preserved_continuity=candidate.preserves_process_continuity,
        changed_differentiation_conditions=(
            candidate.changes_differentiation_conditions
        ),
        restored_productivity=(
            candidate.restores_productive_differentiation
        ),
        orthogonal=orthogonal,
    )


def transition_from_reflection(
    reflection: Any,
    candidate: TransitionCandidate,
) -> OrthogonalTransitionResult:
    """
    Evaluate an OT candidate only after reflection has identified
    a possible limitation in the current differentiation regime.

    Reflection is a prerequisite in the UFCPS Level 3 process model,
    but this function does not infer reflection itself.
    """

    reflection_status = getattr(
        reflection,
        "status",
        None,
    )

    if hasattr(reflection_status, "value"):
        reflection_status = reflection_status.value

    if reflection_status not in {
        "ACTIVE",
        "COMPLETED",
    }:
        return OrthogonalTransitionResult(
            status=TransitionStatus.REJECTED,
            mechanism=candidate.mechanism.value,
            source_space=candidate.source_space,
            target_space=candidate.target_space,
            reasons=[
                "reflection_not_active",
            ],
            preserved_continuity=(
                candidate.preserves_process_continuity
            ),
            changed_differentiation_conditions=(
                candidate.changes_differentiation_conditions
            ),
            restored_productivity=(
                candidate.restores_productive_differentiation
            ),
            orthogonal=False,
        )

    return evaluate_transition(candidate)


def demo() -> None:
    """
    Demonstrate two different candidate mechanisms.

    Both are evaluated using the same structural OT criteria.
    """

    compensatory_multiplication = TransitionCandidate(
        mechanism=TransitionMechanism.COMPENSATORY_MULTIPLICATION,
        source_space="C_k",
        target_space="C_k+1",
        preserves_process_continuity=True,
        changes_differentiation_conditions=True,
        restores_productive_differentiation=True,
        merely_retries_current_space=False,
        merely_changes_parameters=False,
        merely_changes_quantity=False,
        evidence=[
            "scale_regime_changed",
            "local_nodes_created",
            "node_interactions_generate_new_distinctions",
        ],
        description=(
            "Scale/regime transition compensated by multiplication "
            "of local actualization nodes."
        ),
    )

    parameter_retry = TransitionCandidate(
        mechanism=TransitionMechanism.SCALE,
        source_space="C_k",
        target_space="C_k",
        preserves_process_continuity=True,
        changes_differentiation_conditions=False,
        restores_productive_differentiation=False,
        merely_retries_current_space=True,
        merely_changes_parameters=True,
        merely_changes_quantity=False,
        evidence=[
            "different_parameter_values",
        ],
        description=(
            "Retry within the same differentiation space."
        ),
    )

    accepted = evaluate_transition(
        compensatory_multiplication
    )

    rejected = evaluate_transition(
        parameter_retry
    )

    print("Accepted candidate:")
    print(accepted.to_dict())

    print("\nRejected candidate:")
    print(rejected.to_dict())


if __name__ == "__main__":
    demo()
