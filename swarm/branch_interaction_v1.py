"""
UFCPS — Branch Interaction v1

Interaction layer for localized orthogonal-transition branches.

Purpose
-------
Model interaction between independently explored OT branches and detect:

    1. emergent distinctions;
    2. candidate invariants;
    3. new questions;
    4. interaction deadlocks.

The interaction layer does NOT assume that an invariant exists.

Core process:

    localized branches
          ↓
      interaction
          ↓
    ┌─────┴─────┐
    ↓           ↓
 D_new       I_candidate
    ↓           ↓
    └─────┬─────┘
          ↓
      new state

Important distinction:

    Emergent distinction
        = something newly accessible through interaction.

    Candidate invariant
        = a relation that appears preserved across
          distinguishable branch realizations.

A candidate invariant remains revisable.
"""


from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ----------------------------------------------------------------------
# Status
# ----------------------------------------------------------------------


class InteractionStatus(str, Enum):
    NOT_INTERACTED = "NOT_INTERACTED"
    INTERACTED = "INTERACTED"
    EMERGENT_DISTINCTION = "EMERGENT_DISTINCTION"
    CANDIDATE_INVARIANT = "CANDIDATE_INVARIANT"
    BOTH = "BOTH"
    DEADLOCK = "DEADLOCK"


class InvariantStatus(str, Enum):
    NONE = "NONE"
    CANDIDATE = "CANDIDATE"
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    REOPENED = "REOPENED"


# ----------------------------------------------------------------------
# Localized branch representation
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class LocalizedBranch:
    branch_id: str
    mechanism: str
    state_id: str

    distinctions: Tuple[str, ...] = ()
    relations: Tuple[str, ...] = ()
    constraints: Tuple[str, ...] = ()

    productive: bool = True

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ----------------------------------------------------------------------
# Emergent distinction
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class EmergentDistinction:
    distinction_id: str

    source_branches: Tuple[str, ...]

    description: str

    generated_from_relations: Tuple[str, ...]

    novelty_basis: str

    accessible_after_interaction: bool = True


# ----------------------------------------------------------------------
# Candidate invariant
# ----------------------------------------------------------------------


@dataclass
class CandidateInvariant:
    invariant_id: str

    source_branches: Tuple[str, ...]

    relation: str

    observed_realizations: Tuple[str, ...]

    status: InvariantStatus = (
        InvariantStatus.CANDIDATE
    )

    transformation_tests: int = 0

    preservation_count: int = 0

    violation_count: int = 0

    evidence: List[str] = field(
        default_factory=list
    )


# ----------------------------------------------------------------------
# Interaction result
# ----------------------------------------------------------------------


@dataclass
class InteractionResult:

    interaction_id: str

    branch_ids: Tuple[str, ...]

    status: InteractionStatus

    emergent_distinctions: List[
        EmergentDistinction
    ] = field(
        default_factory=list
    )

    candidate_invariants: List[
        CandidateInvariant
    ] = field(
        default_factory=list
    )

    new_questions: List[str] = field(
        default_factory=list
    )

    deadlocks: List[str] = field(
        default_factory=list
    )

    description: str = ""


# ----------------------------------------------------------------------
# Interaction engine
# ----------------------------------------------------------------------


class BranchInteractionEngine:
    """
    Detects relations created by interaction between localized branches.

    The engine is intentionally conservative:

        difference alone
            !=
        emergent distinction

    and:

        repeated similarity
            !=
        invariant

    An emergent distinction must arise from a relation between
    participating branches.

    An invariant must subsequently survive transformation tests.
    """

    def __init__(
        self,
        *,
        require_multiple_branches: bool = True,
    ) -> None:

        self.require_multiple_branches = (
            require_multiple_branches
        )

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def interact(
        self,
        branches: Iterable[LocalizedBranch],
        interaction_id: str = "INTERACTION_001",
    ) -> InteractionResult:

        branch_list = list(
            branches
        )

        if (
            self.require_multiple_branches
            and len(branch_list) < 2
        ):

            return InteractionResult(
                interaction_id=interaction_id,
                branch_ids=tuple(
                    branch.branch_id
                    for branch in branch_list
                ),
                status=(
                    InteractionStatus.DEADLOCK
                ),
                deadlocks=[
                    "Interaction requires at least two localized branches."
                ],
                description=(
                    "Insufficient branch multiplicity."
                ),
            )

        if not branch_list:

            return InteractionResult(
                interaction_id=interaction_id,
                branch_ids=(),
                status=(
                    InteractionStatus.DEADLOCK
                ),
                deadlocks=[
                    "No localized branches available."
                ],
                description=(
                    "Interaction has no input."
                ),
            )

        emergent = (
            self._detect_emergent_distinctions(
                branch_list
            )
        )

        invariants = (
            self._detect_candidate_invariants(
                branch_list
            )
        )

        questions = (
            self._generate_questions(
                branch_list,
                emergent,
                invariants,
            )
        )

        if emergent and invariants:

            status = InteractionStatus.BOTH

        elif emergent:

            status = (
                InteractionStatus.EMERGENT_DISTINCTION
            )

        elif invariants:

            status = (
                InteractionStatus.CANDIDATE_INVARIANT
            )

        else:

            status = (
                InteractionStatus.INTERACTED
            )

        return InteractionResult(
            interaction_id=interaction_id,

            branch_ids=tuple(
                branch.branch_id
                for branch in branch_list
            ),

            status=status,

            emergent_distinctions=emergent,

            candidate_invariants=invariants,

            new_questions=questions,

            description=(
                "Localized OT branches were "
                "interacted without collapsing "
                "their individual identities."
            ),
        )

    # ------------------------------------------------------------------
    # Emergent distinctions
    # ------------------------------------------------------------------

    def _detect_emergent_distinctions(
        self,
        branches: List[LocalizedBranch],
    ) -> List[EmergentDistinction]:

        results: List[
            EmergentDistinction
        ] = []

        seen_relations = set()

        for index, left in enumerate(
            branches
        ):

            for right in branches[
                index + 1:
            ]:

                shared_relations = (
                    set(left.relations)
                    & set(right.relations)
                )

                relation_difference = (
                    set(left.relations)
                    ^ set(right.relations)
                )

                # A relation between branch-specific
                # structures is itself a possible new
                # distinction.
                #
                # We require some actual structural
                # difference between the branches.

                if not relation_difference:
                    continue

                signature = (
                    left.branch_id,
                    right.branch_id,
                    tuple(
                        sorted(
                            relation_difference
                        )
                    ),
                )

                if signature in seen_relations:
                    continue

                seen_relations.add(
                    signature
                )

                generated = (
                    tuple(
                        sorted(
                            relation_difference
                        )
                    )
                )

                results.append(
                    EmergentDistinction(
                        distinction_id=(
                            f"DNEW_"
                            f"{len(results) + 1:03d}"
                        ),

                        source_branches=(
                            left.branch_id,
                            right.branch_id,
                        ),

                        description=(
                            "Interaction between "
                            f"{left.branch_id} and "
                            f"{right.branch_id} exposes "
                            "a relation unavailable "
                            "as an isolated branch property."
                        ),

                        generated_from_relations=(
                            generated
                        ),

                        novelty_basis=(
                            "cross_branch_relation"
                        ),
                    )
                )

        return results

    # ------------------------------------------------------------------
    # Candidate invariants
    # ------------------------------------------------------------------

    def _detect_candidate_invariants(
        self,
        branches: List[LocalizedBranch],
    ) -> List[CandidateInvariant]:

        if len(branches) < 2:
            return []

        # Relations shared by all branches are candidates.
        #
        # They are NOT yet accepted as invariants.
        shared = set(
            branches[0].relations
        )

        for branch in branches[1:]:

            shared &= set(
                branch.relations
            )

        candidates: List[
            CandidateInvariant
        ] = []

        for relation in sorted(
            shared
        ):

            candidates.append(
                CandidateInvariant(
                    invariant_id=(
                        f"I_{len(candidates) + 1:03d}"
                    ),

                    source_branches=tuple(
                        branch.branch_id
                        for branch in branches
                    ),

                    relation=relation,

                    observed_realizations=tuple(
                        branch.state_id
                        for branch in branches
                    ),

                    status=(
                        InvariantStatus.CANDIDATE
                    ),

                    evidence=[
                        (
                            "Relation observed across "
                            "multiple distinguishable "
                            "branch realizations."
                        )
                    ],
                )
            )

        return candidates

    # ------------------------------------------------------------------
    # Questions
    # ------------------------------------------------------------------

    def _generate_questions(
        self,
        branches: List[LocalizedBranch],
        distinctions: List[EmergentDistinction],
        invariants: List[CandidateInvariant],
    ) -> List[str]:

        questions: List[str] = []

        if distinctions:

            questions.append(
                "Does the emergent distinction "
                "persist under further branch transformation?"
            )

        if invariants:

            questions.append(
                "Does the candidate invariant "
                "remain preserved under independent "
                "transformations of the branches?"
            )

        if distinctions and invariants:

            questions.append(
                "Does the emergent distinction "
                "depend on the candidate invariant?"
            )

        if len(branches) > 2:

            questions.append(
                "Does the interaction outcome persist "
                "when an additional branch is introduced?"
            )

        return questions

    # ------------------------------------------------------------------
    # Invariant testing
    # ------------------------------------------------------------------

    def test_invariant(
        self,
        candidate: CandidateInvariant,
        *,
        preserved: bool,
        transformation_id: str,
    ) -> CandidateInvariant:

        candidate.transformation_tests += 1

        if preserved:

            candidate.preservation_count += 1

            candidate.evidence.append(
                f"Preserved under {transformation_id}."
            )

        else:

            candidate.violation_count += 1

            candidate.evidence.append(
                f"Violated under {transformation_id}."
            )

        if candidate.violation_count > 0:

            candidate.status = (
                InvariantStatus.REFUTED
            )

        elif (
            candidate.transformation_tests >= 2
            and candidate.preservation_count
            == candidate.transformation_tests
        ):

            candidate.status = (
                InvariantStatus.SUPPORTED
            )

        else:

            candidate.status = (
                InvariantStatus.CANDIDATE
            )

        return candidate

    # ------------------------------------------------------------------
    # Reopen
    # ------------------------------------------------------------------

    def reopen_invariant(
        self,
        candidate: CandidateInvariant,
        reason: str,
    ) -> CandidateInvariant:

        candidate.status = (
            InvariantStatus.REOPENED
        )

        candidate.evidence.append(
            f"Reopened: {reason}"
        )

        return candidate


# ----------------------------------------------------------------------
# Example interaction
# ----------------------------------------------------------------------


def demo() -> InteractionResult:

    branches = [

        LocalizedBranch(
            branch_id="OT_A",
            mechanism="SCALE",
            state_id="STATE_A",

            distinctions=(
                "node",
                "distance",
                "relation_A",
            ),

            relations=(
                "coupling",
                "persistence",
            ),
        ),

        LocalizedBranch(
            branch_id="OT_B",
            mechanism="STRUCTURAL_RECONFIGURATION",
            state_id="STATE_B",

            distinctions=(
                "node",
                "boundary",
                "relation_B",
            ),

            relations=(
                "coupling",
                "persistence",
            ),
        ),

        LocalizedBranch(
            branch_id="OT_C",
            mechanism="REPRESENTATION_SPACE",
            state_id="STATE_C",

            distinctions=(
                "representation",
                "node",
                "relation_C",
            ),

            relations=(
                "coupling",
                "persistence",
            ),
        ),
    ]

    engine = (
        BranchInteractionEngine()
    )

    return engine.interact(
        branches,
        interaction_id="INTERACTION_DEMO_001",
    )


# ----------------------------------------------------------------------
# Smoke test
# ----------------------------------------------------------------------


def run_smoke_test() -> Dict[str, Any]:

    engine = (
        BranchInteractionEngine()
    )

    branches = [

        LocalizedBranch(
            branch_id="B1",
            mechanism="OT_A",
            state_id="S1",

            distinctions=(
                "x",
                "a",
            ),

            relations=(
                "persistence",
                "coupling",
            ),
        ),

        LocalizedBranch(
            branch_id="B2",
            mechanism="OT_B",
            state_id="S2",

            distinctions=(
                "y",
                "b",
            ),

            relations=(
                "persistence",
                "coupling",
            ),
        ),

        LocalizedBranch(
            branch_id="B3",
            mechanism="OT_C",
            state_id="S3",

            distinctions=(
                "z",
                "c",
            ),

            relations=(
                "persistence",
                "coupling",
            ),
        ),
    ]

    result = engine.interact(
        branches
    )

    assert len(
        result.branch_ids
    ) == 3

    assert len(
        result.candidate_invariants
    ) == 2

    assert all(
        candidate.status
        == InvariantStatus.CANDIDATE
        for candidate
        in result.candidate_invariants
    )

    # Test persistence of one candidate.
    candidate = (
        result.candidate_invariants[0]
    )

    engine.test_invariant(
        candidate,
        preserved=True,
        transformation_id="T1",
    )

    assert (
        candidate.status
        == InvariantStatus.CANDIDATE
    )

    engine.test_invariant(
        candidate,
        preserved=True,
        transformation_id="T2",
    )

    assert (
        candidate.status
        == InvariantStatus.SUPPORTED
    )

    # Now test a counterexample on another candidate.
    candidate_2 = (
        result.candidate_invariants[1]
    )

    engine.test_invariant(
        candidate_2,
        preserved=True,
        transformation_id="T1",
    )

    engine.test_invariant(
        candidate_2,
        preserved=False,
        transformation_id="T2",
    )

    assert (
        candidate_2.status
        == InvariantStatus.REFUTED
    )

    return {
        "benchmark": (
            "branch_interaction_v1"
        ),

        "branches": len(
            result.branch_ids
        ),

        "emergent_distinctions": len(
            result.emergent_distinctions
        ),

        "candidate_invariants": len(
            result.candidate_invariants
        ),

        "new_questions": len(
            result.new_questions
        ),

        "invariant_test": "PASS",

        "all_passed": True,
    }


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------


def print_report(
    result: InteractionResult,
) -> None:

    print(
        "UFCPS — Branch Interaction v1"
    )

    print(
        "=" * 58
    )

    print(
        f"Interaction: "
        f"{result.interaction_id}"
    )

    print(
        f"Status: "
        f"{result.status.value}"
    )

    print(
        f"Branches: "
        f"{len(result.branch_ids)}"
    )

    print(
        "\nEmergent distinctions:"
    )

    for distinction in (
        result.emergent_distinctions
    ):

        print(
            f"  {distinction.distinction_id}: "
            f"{distinction.description}"
        )

    print(
        "\nCandidate invariants:"
    )

    for invariant in (
        result.candidate_invariants
    ):

        print(
            f"  {invariant.invariant_id}: "
            f"{invariant.relation} "
            f"[{invariant.status.value}]"
        )

    print(
        "\nQuestions:"
    )

    for question in (
        result.new_questions
    ):

        print(
            f"  - {question}"
        )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> int:

    report = run_smoke_test()

    print(
        "Smoke test: PASS"
    )

    result = demo()

    print()

    print_report(
        result
    )

    print()

    print(
        f"Emergent distinctions: "
        f"{report['emergent_distinctions']}"
    )

    print(
        f"Candidate invariants: "
        f"{report['candidate_invariants']}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
