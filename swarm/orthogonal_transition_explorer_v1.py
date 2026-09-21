"""
UFCPS — Orthogonal Transition Explorer v1

Explores multiple orthogonal-transition candidates in parallel.

Architectural principle:

    PREPARE_OT
        !=
    SELECT_ONE_OT

The explorer treats orthogonal transition as a search space.

Multiple candidate mechanisms may be explored simultaneously:

    C_k
      |
      +---- OT_1 ----> C_(k+1)^1
      |
      +---- OT_2 ----> C_(k+1)^2
      |
      +---- OT_3 ----> C_(k+1)^3
      |
      +---- ...

The explorer does not require a single winner.

It records:
    - candidate validity;
    - branch execution;
    - productivity recovery;
    - number of new distinctions;
    - resource cost;
    - new deadlocks;
    - new questions;
    - persistence of productive differentiation.

The comparison layer is descriptive.

It does NOT:
    - declare an ontologically correct mechanism;
    - prove that one mechanism is universally superior;
    - collapse all branches into one result;
    - treat statistical novelty as creativity.

Core invariant:

    OT_candidate != OT_selection

and:

    Branch Failure != Process Termination
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional


# ----------------------------------------------------------------------
# Candidate mechanisms
# ----------------------------------------------------------------------


class OTMechanism(str, Enum):
    SCALE = "SCALE"
    COMPENSATORY_MULTIPLICATION = "COMPENSATORY_MULTIPLICATION"
    STRUCTURAL_RECONFIGURATION = "STRUCTURAL_RECONFIGURATION"
    CARRIER_TRANSITION = "CARRIER_TRANSITION"
    INTERACTION_REGIME = "INTERACTION_REGIME"
    REPRESENTATION_SPACE = "REPRESENTATION_SPACE"
    COMPOSITION_DECOMPOSITION = "COMPOSITION_DECOMPOSITION"
    UNKNOWN_EMERGENT = "UNKNOWN_EMERGENT"


# ----------------------------------------------------------------------
# Branch state
# ----------------------------------------------------------------------


class BranchStatus(str, Enum):
    PROPOSED = "PROPOSED"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DEADLOCK = "DEADLOCK"
    FAILED = "FAILED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class OTBranch:
    branch_id: str
    mechanism: OTMechanism

    source_space: str
    target_space: str

    status: BranchStatus = BranchStatus.PROPOSED

    preserves_process_continuity: bool = False
    changes_differentiation_conditions: bool = False
    restores_productive_differentiation: bool = False

    productive_difference_before: float = 0.0
    productive_difference_after: float = 0.0

    new_distinctions: int = 0
    new_questions: int = 0
    new_deadlocks: int = 0

    resource_cost: float = 0.0
    observation_steps: int = 0

    evidence: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ----------------------------------------------------------------------
# Comparison
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class BranchProductivity:
    branch_id: str
    mechanism: str

    productivity_delta: float
    productivity_ratio: float

    new_distinctions: int
    new_questions: int
    new_deadlocks: int

    resource_cost: float
    observation_steps: int

    productive: bool


@dataclass
class ExplorationResult:
    source_space: str
    branches: List[OTBranch]

    comparisons: List[BranchProductivity]

    process_continuity_preserved: bool

    selection_required: bool = False

    description: str = ""


# ----------------------------------------------------------------------
# Explorer configuration
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class ExplorerConfig:
    minimum_productivity_delta: float = 0.0

    minimum_productivity_ratio: float = 1.0

    require_process_continuity: bool = True

    require_changed_conditions: bool = True

    allow_parallel_branches: bool = True

    allow_unknown_mechanism: bool = True


# ----------------------------------------------------------------------
# Explorer
# ----------------------------------------------------------------------


class OrthogonalTransitionExplorer:
    """
    Explore multiple OT candidates without selecting one
    as the canonical transition.
    """

    def __init__(
        self,
        config: Optional[ExplorerConfig] = None,
    ) -> None:

        self.config = (
            config
            if config is not None
            else ExplorerConfig()
        )

    # ------------------------------------------------------------------
    # Candidate generation
    # ------------------------------------------------------------------

    def generate_candidates(
        self,
        source_space: str,
        target_space_prefix: str = "C_next",
        mechanisms: Optional[
            Iterable[OTMechanism]
        ] = None,
    ) -> List[OTBranch]:

        if mechanisms is None:

            mechanisms = list(
                OTMechanism
            )

        branches: List[OTBranch] = []

        for index, mechanism in enumerate(
            mechanisms,
            start=1,
        ):

            if (
                mechanism
                == OTMechanism.UNKNOWN_EMERGENT
                and not self.config.allow_unknown_mechanism
            ):
                continue

            branch = OTBranch(
                branch_id=f"OT_BRANCH_{index:03d}",
                mechanism=mechanism,
                source_space=source_space,
                target_space=(
                    f"{target_space_prefix}_{index}"
                ),
            )

            branches.append(
                branch
            )

        return branches

    # ------------------------------------------------------------------
    # Candidate validation
    # ------------------------------------------------------------------

    def validate_candidate(
        self,
        branch: OTBranch,
    ) -> OTBranch:

        if (
            self.config.require_process_continuity
            and not branch.preserves_process_continuity
        ):

            branch.status = (
                BranchStatus.FAILED
            )

            branch.evidence.append(
                "Process continuity not preserved."
            )

            return branch

        if (
            self.config.require_changed_conditions
            and not branch.changes_differentiation_conditions
        ):

            branch.status = (
                BranchStatus.FAILED
            )

            branch.evidence.append(
                "Differentiation conditions did not change."
            )

            return branch

        branch.status = (
            BranchStatus.VALIDATED
        )

        branch.evidence.append(
            "Candidate satisfies structural OT conditions."
        )

        return branch

    # ------------------------------------------------------------------
    # Branch activation
    # ------------------------------------------------------------------

    def activate(
        self,
        branch: OTBranch,
    ) -> OTBranch:

        if branch.status != BranchStatus.VALIDATED:

            branch.status = (
                BranchStatus.FAILED
            )

            branch.evidence.append(
                "Cannot activate invalid candidate."
            )

            return branch

        branch.status = (
            BranchStatus.ACTIVE
        )

        return branch

    # ------------------------------------------------------------------
    # Branch observation
    # ------------------------------------------------------------------

    def observe(
        self,
        branch: OTBranch,
        *,
        productive_difference_before: float,
        productive_difference_after: float,
        new_distinctions: int = 0,
        new_questions: int = 0,
        new_deadlocks: int = 0,
        resource_cost: float = 0.0,
        observation_steps: int = 1,
        deadlock: bool = False,
        failed: bool = False,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> OTBranch:

        branch.productive_difference_before = (
            productive_difference_before
        )

        branch.productive_difference_after = (
            productive_difference_after
        )

        branch.new_distinctions = (
            new_distinctions
        )

        branch.new_questions = (
            new_questions
        )

        branch.new_deadlocks = (
            new_deadlocks
        )

        branch.resource_cost = (
            resource_cost
        )

        branch.observation_steps = (
            observation_steps
        )

        if metadata:
            branch.metadata.update(
                metadata
            )

        branch.restores_productive_differentiation = (
            self._is_productive(
                branch
            )
        )

        if failed:

            branch.status = (
                BranchStatus.FAILED
            )

        elif deadlock:

            branch.status = (
                BranchStatus.DEADLOCK
            )

        elif branch.restores_productive_differentiation:

            branch.status = (
                BranchStatus.COMPLETED
            )

        else:

            branch.status = (
                BranchStatus.INSUFFICIENT_DATA
            )

        return branch

    # ------------------------------------------------------------------
    # Productivity
    # ------------------------------------------------------------------

    def _is_productive(
        self,
        branch: OTBranch,
    ) -> bool:

        delta = (
            branch.productive_difference_after
            - branch.productive_difference_before
        )

        if delta < (
            self.config.minimum_productivity_delta
        ):
            return False

        if (
            branch.productive_difference_before
            > 0
        ):

            ratio = (
                branch.productive_difference_after
                / branch.productive_difference_before
            )

            if ratio < (
                self.config.minimum_productivity_ratio
            ):
                return False

        return True

    def productivity(
        self,
        branch: OTBranch,
    ) -> BranchProductivity:

        delta = (
            branch.productive_difference_after
            - branch.productive_difference_before
        )

        if (
            branch.productive_difference_before
            > 0
        ):

            ratio = (
                branch.productive_difference_after
                / branch.productive_difference_before
            )

        else:

            ratio = (
                float("inf")
                if branch.productive_difference_after > 0
                else 0.0
            )

        return BranchProductivity(
            branch_id=branch.branch_id,
            mechanism=branch.mechanism.value,
            productivity_delta=delta,
            productivity_ratio=ratio,
            new_distinctions=(
                branch.new_distinctions
            ),
            new_questions=(
                branch.new_questions
            ),
            new_deadlocks=(
                branch.new_deadlocks
            ),
            resource_cost=(
                branch.resource_cost
            ),
            observation_steps=(
                branch.observation_steps
            ),
            productive=(
                branch.restores_productive_differentiation
            ),
        )

    # ------------------------------------------------------------------
    # Exploration
    # ------------------------------------------------------------------

    def explore(
        self,
        branches: Iterable[OTBranch],
    ) -> ExplorationResult:

        branch_list = list(
            branches
        )

        for branch in branch_list:

            if branch.status == BranchStatus.PROPOSED:

                self.validate_candidate(
                    branch
                )

            if branch.status == BranchStatus.VALIDATED:

                self.activate(
                    branch
                )

        comparisons = [
            self.productivity(branch)
            for branch in branch_list
            if branch.status
            in {
                BranchStatus.COMPLETED,
                BranchStatus.DEADLOCK,
                BranchStatus.FAILED,
                BranchStatus.INSUFFICIENT_DATA,
            }
        ]

        continuity = all(
            branch.preserves_process_continuity
            for branch in branch_list
        )

        return ExplorationResult(
            source_space=(
                branch_list[0].source_space
                if branch_list
                else ""
            ),
            branches=branch_list,
            comparisons=comparisons,
            process_continuity_preserved=(
                continuity
            ),
            selection_required=False,
            description=(
                "Multiple OT branches were explored "
                "and compared without requiring "
                "selection of a single canonical branch."
            ),
        )


# ----------------------------------------------------------------------
# Comparison helpers
# ----------------------------------------------------------------------


def compare_productivity(
    result: ExplorationResult,
) -> List[BranchProductivity]:

    """
    Return observations ordered by productivity delta.

    This ordering is descriptive only.

    It does not declare an ontological winner.
    """

    return sorted(
        result.comparisons,
        key=lambda item: (
            item.productivity_delta,
            item.new_distinctions,
            item.new_questions,
        ),
        reverse=True,
    )


def productivity_frontier(
    result: ExplorationResult,
) -> List[BranchProductivity]:

    """
    Return non-dominated branches over three dimensions:

        productivity_delta
        new_distinctions
        resource efficiency

    A frontier contains branches for which no other branch
    is simultaneously better in all three dimensions.

    No single winner is selected.
    """

    frontier: List[
        BranchProductivity
    ] = []

    def efficiency(
        item: BranchProductivity,
    ) -> float:

        if item.resource_cost <= 0:

            return (
                item.productivity_delta
                + item.new_distinctions
            )

        return (
            item.productivity_delta
            + item.new_distinctions
        ) / item.resource_cost

    for candidate in result.comparisons:

        dominated = False

        for other in result.comparisons:

            if other is candidate:
                continue

            other_better_or_equal = (
                other.productivity_delta
                >= candidate.productivity_delta
                and other.new_distinctions
                >= candidate.new_distinctions
                and efficiency(other)
                >= efficiency(candidate)
            )

            other_strictly_better = (
                other.productivity_delta
                > candidate.productivity_delta
                or other.new_distinctions
                > candidate.new_distinctions
                or efficiency(other)
                > efficiency(candidate)
            )

            if (
                other_better_or_equal
                and other_strictly_better
            ):

                dominated = True
                break

        if not dominated:

            frontier.append(
                candidate
            )

    return frontier


# ----------------------------------------------------------------------
# Demonstration
# ----------------------------------------------------------------------


def demo() -> ExplorationResult:

    explorer = (
        OrthogonalTransitionExplorer()
    )

    branches = (
        explorer.generate_candidates(
            source_space="C_k"
        )
    )

    # In the benchmark/demo we provide synthetic observations.
    #
    # In a real UFCPS run these values must come from actual
    # branch execution and observation.

    observations = {
        OTMechanism.SCALE: {
            "after": 0.85,
            "distinctions": 4,
            "questions": 2,
            "deadlocks": 1,
            "cost": 5.0,
        },

        OTMechanism.COMPENSATORY_MULTIPLICATION: {
            "after": 1.40,
            "distinctions": 9,
            "questions": 5,
            "deadlocks": 2,
            "cost": 8.0,
        },

        OTMechanism.STRUCTURAL_RECONFIGURATION: {
            "after": 1.20,
            "distinctions": 7,
            "questions": 4,
            "deadlocks": 1,
            "cost": 7.0,
        },

        OTMechanism.CARRIER_TRANSITION: {
            "after": 0.70,
            "distinctions": 3,
            "questions": 2,
            "deadlocks": 2,
            "cost": 9.0,
        },

        OTMechanism.INTERACTION_REGIME: {
            "after": 1.30,
            "distinctions": 8,
            "questions": 6,
            "deadlocks": 1,
            "cost": 10.0,
        },

        OTMechanism.REPRESENTATION_SPACE: {
            "after": 1.10,
            "distinctions": 10,
            "questions": 8,
            "deadlocks": 0,
            "cost": 6.0,
        },

        OTMechanism.COMPOSITION_DECOMPOSITION: {
            "after": 1.00,
            "distinctions": 6,
            "questions": 4,
            "deadlocks": 1,
            "cost": 5.0,
        },

        OTMechanism.UNKNOWN_EMERGENT: {
            "after": 1.50,
            "distinctions": 12,
            "questions": 9,
            "deadlocks": 3,
            "cost": 15.0,
        },
    }

    for branch in branches:

        observation = observations[
            branch.mechanism
        ]

        branch.preserves_process_continuity = (
            True
        )

        branch.changes_differentiation_conditions = (
            True
        )

        explorer.validate_candidate(
            branch
        )

        explorer.activate(
            branch
        )

        explorer.observe(
            branch,
            productive_difference_before=1.00,
            productive_difference_after=(
                observation["after"]
            ),
            new_distinctions=(
                observation["distinctions"]
            ),
            new_questions=(
                observation["questions"]
            ),
            new_deadlocks=(
                observation["deadlocks"]
            ),
            resource_cost=(
                observation["cost"]
            ),
            observation_steps=10,
        )

    return explorer.explore(
        branches
    )


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------


def print_report(
    result: ExplorationResult,
) -> None:

    print(
        "UFCPS — Orthogonal Transition Explorer v1"
    )
    print("=" * 60)

    print(
        f"Source space: {result.source_space}"
    )

    print(
        f"Branches explored: "
        f"{len(result.branches)}"
    )

    print(
        f"Process continuity preserved: "
        f"{result.process_continuity_preserved}"
    )

    print(
        f"Selection required: "
        f"{result.selection_required}"
    )

    print("\nBranch comparison:")

    for item in compare_productivity(
        result
    ):

        print(
            f"  {item.branch_id:16s} "
            f"{item.mechanism:30s} "
            f"ΔP={item.productivity_delta:+.3f} "
            f"D={item.new_distinctions:3d} "
            f"Q={item.new_questions:3d} "
            f"F={item.new_deadlocks:3d} "
            f"cost={item.resource_cost:.2f}"
        )

    print(
        "\nProductivity frontier:"
    )

    for item in productivity_frontier(
        result
    ):

        print(
            f"  {item.branch_id}: "
            f"{item.mechanism}"
        )


# ----------------------------------------------------------------------
# Assertions / smoke test
# ----------------------------------------------------------------------


def run_smoke_test() -> Dict[str, Any]:

    result = demo()

    assert len(
        result.branches
    ) == len(OTMechanism)

    assert (
        result.selection_required
        is False
    )

    assert (
        result.process_continuity_preserved
        is True
    )

    assert len(
        result.comparisons
    ) == len(OTMechanism)

    frontier = productivity_frontier(
        result
    )

    assert len(
        frontier
    ) >= 1

    return {
        "benchmark": (
            "orthogonal_transition_explorer_v1"
        ),
        "branches": len(
            result.branches
        ),
        "comparisons": len(
            result.comparisons
        ),
        "frontier_size": len(
            frontier
        ),
        "selection_required": (
            result.selection_required
        ),
        "process_continuity_preserved": (
            result.process_continuity_preserved
        ),
        "all_passed": True,
    }


def main() -> int:

    report = run_smoke_test()

    print_report(
        demo()
    )

    print(
        "\nSmoke test: PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
