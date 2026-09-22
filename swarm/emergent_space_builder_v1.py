"""
UFCPS — Emergent Space Builder v1

Builds the next cognitive space from interaction results.

Core transition:

    C_k
      ↓
    OT exploration
      ↓
    branch interaction
      ↓
    ┌───────────────┬────────────────┐
    ↓               ↓                ↓
  D_new       I_candidate        questions
    │               │                │
    └───────────────┴────────────────┘
                    ↓
          Emergent Space Builder
                    ↓
                 C_k+1

The builder does not decide:
    - whether a distinction is true;
    - whether an invariant is universally valid;
    - which OT mechanism is superior;
    - whether the resulting space is scientifically correct.

Its task is architectural:

    convert interaction outputs into a structured
    space of subsequently accessible distinctions.

Important:

    C_k+1 != C_k

but:

    structural_continuity(C_k, C_k+1) == True

when the continuation requirements are preserved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple

from branch_interaction_v1 import (
    CandidateInvariant,
    EmergentDistinction,
    InvariantStatus,
    InteractionResult,
)


# ----------------------------------------------------------------------
# Space elements
# ----------------------------------------------------------------------


class SpaceElementType(str, Enum):
    DISTINCTION = "DISTINCTION"
    INVARIANT = "INVARIANT"
    QUESTION = "QUESTION"
    RELATION = "RELATION"


class SpaceElementStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CANDIDATE = "CANDIDATE"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class SpaceElement:
    element_id: str
    element_type: SpaceElementType
    status: SpaceElementStatus

    description: str

    provenance: Tuple[str, ...] = ()

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ----------------------------------------------------------------------
# Cognitive space
# ----------------------------------------------------------------------


@dataclass
class CognitiveSpace:
    space_id: str
    parent_space_id: Optional[str]

    version: int

    elements: List[SpaceElement] = field(
        default_factory=list
    )

    accessible_distinctions: List[str] = field(
        default_factory=list
    )

    active_invariants: List[str] = field(
        default_factory=list
    )

    unresolved_questions: List[str] = field(
        default_factory=list
    )

    relations: List[str] = field(
        default_factory=list
    )

    structural_continuity: bool = True

    content_identity_with_parent: bool = False

    description: str = ""


# ----------------------------------------------------------------------
# Builder configuration
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class EmergentSpaceBuilderConfig:
    require_parent_space: bool = True

    promote_supported_invariants: bool = True

    include_candidate_invariants: bool = True

    include_emergent_distinctions: bool = True

    include_interaction_questions: bool = True

    preserve_process_continuity: bool = True


# ----------------------------------------------------------------------
# Builder
# ----------------------------------------------------------------------


class EmergentSpaceBuilder:
    """
    Converts interaction output into a new cognitive space.

    The builder is intentionally conservative.

    It does not interpret the semantic truth of an element.

    It records what became accessible after interaction.
    """

    def __init__(
        self,
        config: Optional[
            EmergentSpaceBuilderConfig
        ] = None,
    ) -> None:

        self.config = (
            config
            if config is not None
            else EmergentSpaceBuilderConfig()
        )

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(
        self,
        *,
        parent_space: CognitiveSpace,
        interaction: InteractionResult,
        question_ids: Optional[
            Iterable[str]
        ] = None,
        next_space_id: Optional[str] = None,
    ) -> CognitiveSpace:

        if (
            self.config.require_parent_space
            and parent_space is None
        ):
            raise ValueError(
                "Parent cognitive space is required."
            )

        if next_space_id is None:

            next_space_id = (
                f"{parent_space.space_id}_NEXT"
            )

        next_version = (
            parent_space.version + 1
        )

        space = CognitiveSpace(
            space_id=next_space_id,

            parent_space_id=(
                parent_space.space_id
            ),

            version=next_version,

            structural_continuity=(
                self.config.preserve_process_continuity
            ),

            content_identity_with_parent=False,

            description=(
                "Cognitive space generated from "
                "interaction between localized "
                "orthogonal-transition branches."
            ),
        )

        # Recursive continuity:
        # C_k+1 inherits the accessible content of C_k
        # and then adds the new content produced by the
        # current interaction.
        self._inherit_parent_content(
            parent_space=parent_space,
            space=space,
        )

        self._add_distinctions(
            space,
            interaction.emergent_distinctions,
        )

        self._add_invariants(
            space,
            interaction.candidate_invariants,
        )

        self._add_questions(
            space,
            interaction,
            question_ids,
        )

        self._derive_relations(
            space
        )

        return space

    # ------------------------------------------------------------------
    # Parent-content inheritance
    # ------------------------------------------------------------------

    def _inherit_parent_content(
        self,
        *,
        parent_space: CognitiveSpace,
        space: CognitiveSpace,
    ) -> None:
        """
        Preserve the accumulated content of C_k in C_k+1.

        Recursive cognitive-space construction is additive:

            C_k+1 = C_k + D_new + I_new + Q_new + R_new

        The new space receives a new identity and version, so
        content inheritance does not imply content identity.

        Copies are made explicitly so mutable metadata and lists
        are not shared between generations.
        """

        for element in parent_space.elements:
            space.elements.append(
                SpaceElement(
                    element_id=element.element_id,
                    element_type=element.element_type,
                    status=element.status,
                    description=element.description,
                    provenance=tuple(element.provenance),
                    metadata=dict(element.metadata),
                )
            )

        space.accessible_distinctions.extend(
            parent_space.accessible_distinctions
        )

        space.active_invariants.extend(
            parent_space.active_invariants
        )

        space.unresolved_questions.extend(
            parent_space.unresolved_questions
        )

        space.relations.extend(
            parent_space.relations
        )

    def _unique_element_id(
        self,
        *,
        space: CognitiveSpace,
        requested_id: str,
    ) -> str:
        """Return an ID that does not collide inside the new space."""

        existing = {
            element.element_id
            for element in space.elements
        }

        if requested_id not in existing:
            return requested_id

        base = (
            f"{space.space_id}::{requested_id}"
        )

        if base not in existing:
            return base

        index = 2

        while (
            f"{base}::{index}"
            in existing
        ):
            index += 1

        return (
            f"{base}::{index}"
        )


    # ------------------------------------------------------------------
    # Distinctions
    # ------------------------------------------------------------------

    def _add_distinctions(
        self,
        space: CognitiveSpace,
        distinctions: Iterable[
            EmergentDistinction
        ],
    ) -> None:

        if not self.config.include_emergent_distinctions:
            return

        for distinction in distinctions:

            element_id = self._unique_element_id(
                space=space,
                requested_id=(
                    distinction.distinction_id
                ),
            )

            element = SpaceElement(
                element_id=element_id,

                element_type=(
                    SpaceElementType.DISTINCTION
                ),

                status=(
                    SpaceElementStatus.ACTIVE
                ),

                description=(
                    distinction.description
                ),

                provenance=(
                    distinction.source_branches
                ),

                metadata={
                    "novelty_basis": (
                        distinction.novelty_basis
                    ),

                    "generated_from_relations": (
                        distinction.generated_from_relations
                    ),

                    "source_distinction_id": (
                        distinction.distinction_id
                    ),

                    "generated_in_space": (
                        space.space_id
                    ),
                },
            )

            space.elements.append(
                element
            )

            space.accessible_distinctions.append(
                element_id
            )

    # ------------------------------------------------------------------
    # Invariants
    # ------------------------------------------------------------------

    def _add_invariants(
        self,
        space: CognitiveSpace,
        invariants: Iterable[
            CandidateInvariant
        ],
    ) -> None:

        for invariant in invariants:

            element_id = self._unique_element_id(
                space=space,
                requested_id=(
                    invariant.invariant_id
                ),
            )

            if (
                invariant.status
                == InvariantStatus.SUPPORTED
            ):

                if not self.config.promote_supported_invariants:
                    continue

                status = (
                    SpaceElementStatus.ACTIVE
                )

                space.active_invariants.append(
                    element_id
                )

            elif (
                invariant.status
                == InvariantStatus.CANDIDATE
            ):

                if not self.config.include_candidate_invariants:
                    continue

                status = (
                    SpaceElementStatus.CANDIDATE
                )

            else:

                # Refuted and reopened invariants
                # are not promoted into the active
                # structural basis.
                continue

            element = SpaceElement(
                element_id=element_id,

                element_type=(
                    SpaceElementType.INVARIANT
                ),

                status=status,

                description=(
                    f"Relation: "
                    f"{invariant.relation}"
                ),

                provenance=(
                    invariant.source_branches
                ),

                metadata={
                    "relation": (
                        invariant.relation
                    ),

                    "observed_realizations": (
                        invariant.observed_realizations
                    ),

                    "transformation_tests": (
                        invariant.transformation_tests
                    ),

                    "preservation_count": (
                        invariant.preservation_count
                    ),

                    "violation_count": (
                        invariant.violation_count
                    ),

                    "source_invariant_id": (
                        invariant.invariant_id
                    ),

                    "generated_in_space": (
                        space.space_id
                    ),
                },
            )

            space.elements.append(
                element
            )

    # ------------------------------------------------------------------
    # Questions
    # ------------------------------------------------------------------

    def _add_questions(
        self,
        space: CognitiveSpace,
        interaction: InteractionResult,
        question_ids: Optional[
            Iterable[str]
        ],
    ) -> None:

        if not self.config.include_interaction_questions:
            return

        ids = list(
            question_ids
            if question_ids is not None
            else []
        )

        for index, question in enumerate(
            interaction.new_questions,
            start=1,
        ):

            requested_question_id = (
                ids[index - 1]
                if index <= len(ids)
                else (
                    f"INTERACTION_Q_{index:03d}"
                )
            )

            question_id = self._unique_element_id(
                space=space,
                requested_id=requested_question_id,
            )

            element = SpaceElement(
                element_id=question_id,

                element_type=(
                    SpaceElementType.QUESTION
                ),

                status=(
                    SpaceElementStatus.UNRESOLVED
                ),

                description=question,

                provenance=(
                    interaction.branch_ids
                ),

                metadata={
                    "interaction_id": (
                        interaction.interaction_id
                    )
                },
            )

            space.elements.append(
                element
            )

            space.unresolved_questions.append(
                question_id
            )

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------

    def _derive_relations(
        self,
        space: CognitiveSpace,
    ) -> None:

        distinction_ids = (
            space.accessible_distinctions
        )

        invariant_ids = (
            space.active_invariants
        )

        question_ids = (
            space.unresolved_questions
        )

        if distinction_ids and invariant_ids:

            space.relations.append(
                "DISTINCTION_RELATIVE_TO_INVARIANT"
            )

        if distinction_ids and question_ids:

            space.relations.append(
                "DISTINCTION_GENERATES_QUESTION"
            )

        if invariant_ids and question_ids:

            space.relations.append(
                "INVARIANT_GENERATES_TEST_QUESTION"
            )

    # ------------------------------------------------------------------
    # Structural validation
    # ------------------------------------------------------------------

    def validate(
        self,
        *,
        parent_space: CognitiveSpace,
        new_space: CognitiveSpace,
    ) -> Dict[str, Any]:

        checks = {
            "new_space_identity": (
                new_space.space_id
                != parent_space.space_id
            ),

            "parent_reference_preserved": (
                new_space.parent_space_id
                == parent_space.space_id
            ),

            "version_advanced": (
                new_space.version
                > parent_space.version
            ),

            "content_identity_not_assumed": (
                new_space.content_identity_with_parent
                is False
            ),

            "structural_continuity": (
                new_space.structural_continuity
                is True
            ),

            "space_contains_new_content": (
                len(new_space.elements)
                > len(parent_space.elements)
            ),
        }

        return checks


# ----------------------------------------------------------------------
# Helper: promote invariant after testing
# ----------------------------------------------------------------------


def promote_supported_invariant(
    invariant: CandidateInvariant,
) -> CandidateInvariant:

    if (
        invariant.status
        != InvariantStatus.SUPPORTED
    ):
        raise ValueError(
            "Only SUPPORTED invariants can be promoted."
        )

    return invariant


# ----------------------------------------------------------------------
# Demonstration
# ----------------------------------------------------------------------


def demo() -> CognitiveSpace:

    parent = CognitiveSpace(
        space_id="C_k",
        parent_space_id=None,
        version=1,

        accessible_distinctions=[
            "D_existing_1",
            "D_existing_2",
        ],

        description=(
            "Initial cognitive space."
        ),
    )

    distinction = (
        EmergentDistinction(
            distinction_id="DNEW_001",

            source_branches=(
                "OT_A",
                "OT_B",
            ),

            description=(
                "Interaction revealed a new "
                "cross-branch relation."
            ),

            generated_from_relations=(
                "coupling_A",
                "coupling_B",
            ),

            novelty_basis=(
                "cross_branch_relation"
            ),
        )
    )

    invariant = (
        CandidateInvariant(
            invariant_id="I_001",

            source_branches=(
                "OT_A",
                "OT_B",
                "OT_C",
            ),

            relation="persistence",

            observed_realizations=(
                "STATE_A",
                "STATE_B",
                "STATE_C",
            ),

            status=(
                InvariantStatus.SUPPORTED
            ),

            transformation_tests=2,

            preservation_count=2,
        )
    )

    interaction = InteractionResult(
        interaction_id="INTERACTION_001",

        branch_ids=(
            "OT_A",
            "OT_B",
            "OT_C",
        ),

        status=(
            # Both products exist.
            # We use the enum value through the imported
            # InteractionStatus indirectly in the fixture
            # construction below.
            __import__(
                "branch_interaction_v1"
            ).InteractionStatus.BOTH
        ),

        emergent_distinctions=[
            distinction
        ],

        candidate_invariants=[
            invariant
        ],

        new_questions=[
            "Does DNEW_001 persist under transformation?",
            "Does I_001 remain invariant under new realizations?",
        ],
    )

    builder = (
        EmergentSpaceBuilder()
    )

    return builder.build(
        parent_space=parent,
        interaction=interaction,
        question_ids=[
            "UQL-Q-0001",
            "UQL-Q-0002",
        ],
        next_space_id="C_k+1",
    )


# ----------------------------------------------------------------------
# Smoke test
# ----------------------------------------------------------------------


def run_smoke_test() -> Dict[str, Any]:

    parent = CognitiveSpace(
        space_id="C_k",
        parent_space_id=None,
        version=1,

        accessible_distinctions=[
            "D_old_1",
        ],

        active_invariants=[
            "I_old",
        ],

        description=(
            "Parent cognitive space."
        ),
    )

    distinction = (
        EmergentDistinction(
            distinction_id="DNEW_001",

            source_branches=(
                "OT_A",
                "OT_B",
            ),

            description=(
                "New distinction produced by interaction."
            ),

            generated_from_relations=(
                "relation_A",
                "relation_B",
            ),

            novelty_basis=(
                "cross_branch_relation"
            ),
        )
    )

    candidate = (
        CandidateInvariant(
            invariant_id="I_CANDIDATE_001",

            source_branches=(
                "OT_A",
                "OT_B",
            ),

            relation="persistence",

            observed_realizations=(
                "STATE_A",
                "STATE_B",
            ),

            status=(
                InvariantStatus.CANDIDATE
            ),
        )
    )

    supported = (
        CandidateInvariant(
            invariant_id="I_SUPPORTED_001",

            source_branches=(
                "OT_A",
                "OT_B",
                "OT_C",
            ),

            relation="coupling",

            observed_realizations=(
                "STATE_A",
                "STATE_B",
                "STATE_C",
            ),

            status=(
                InvariantStatus.SUPPORTED
            ),

            transformation_tests=2,

            preservation_count=2,
        )
    )

    interaction = InteractionResult(
        interaction_id="INTERACTION_TEST",

        branch_ids=(
            "OT_A",
            "OT_B",
            "OT_C",
        ),

        status=(
            __import__(
                "branch_interaction_v1"
            ).InteractionStatus.BOTH
        ),

        emergent_distinctions=[
            distinction
        ],

        candidate_invariants=[
            candidate,
            supported,
        ],

        new_questions=[
            "What follows from DNEW_001?",
            "Can I_SUPPORTED_001 survive another transformation?",
        ],
    )

    builder = (
        EmergentSpaceBuilder()
    )

    new_space = builder.build(
        parent_space=parent,
        interaction=interaction,
        question_ids=[
            "UQL-Q-0001",
            "UQL-Q-0002",
        ],
        next_space_id="C_k+1",
    )

    checks = builder.validate(
        parent_space=parent,
        new_space=new_space,
    )

    # Core expectations.

    assert checks[
        "new_space_identity"
    ]

    assert checks[
        "parent_reference_preserved"
    ]

    assert checks[
        "version_advanced"
    ]

    assert checks[
        "content_identity_not_assumed"
    ]

    assert checks[
        "structural_continuity"
    ]

    assert checks[
        "space_contains_new_content"
    ]

    assert (
        "DNEW_001"
        in new_space.accessible_distinctions
    )

    assert (
        "I_SUPPORTED_001"
        in new_space.active_invariants
    )

    assert (
        "I_CANDIDATE_001"
        not in new_space.active_invariants
    )

    assert (
        "I_CANDIDATE_001"
        not in [
            element.element_id
            for element
            in new_space.elements
            if element.element_type
            == SpaceElementType.INVARIANT
            and element.status
            == SpaceElementStatus.ACTIVE
        ]
    )

    assert (
        len(
            new_space.unresolved_questions
        )
        == 2
    )

    assert (
        "DISTINCTION_RELATIVE_TO_INVARIANT"
        in new_space.relations
    )

    assert (
        "DISTINCTION_GENERATES_QUESTION"
        in new_space.relations
    )

    assert (
        "INVARIANT_GENERATES_TEST_QUESTION"
        in new_space.relations
    )

    return {
        "benchmark": (
            "emergent_space_builder_v1"
        ),

        "parent_space": (
            parent.space_id
        ),

        "new_space": (
            new_space.space_id
        ),

        "version": (
            new_space.version
        ),

        "elements": len(
            new_space.elements
        ),

        "accessible_distinctions": len(
            new_space.accessible_distinctions
        ),

        "active_invariants": len(
            new_space.active_invariants
        ),

        "unresolved_questions": len(
            new_space.unresolved_questions
        ),

        "relations": len(
            new_space.relations
        ),

        "checks": checks,

        "all_passed": all(
            checks.values()
        ),
    }


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------


def print_report(
    report: Dict[str, Any],
) -> None:

    print(
        "UFCPS — Emergent Space Builder v1"
    )

    print(
        "=" * 62
    )

    for key, value in report.items():

        print(
            f"{key}: {value}"
        )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> int:

    report = (
        run_smoke_test()
    )

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
