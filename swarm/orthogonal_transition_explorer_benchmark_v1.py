"""
UFCPS — Orthogonal Transition Explorer Benchmark v1

Benchmark for parallel exploration of orthogonal transitions.

Core principle:

    One exhausted cognitive space
                |
        Reflexive transition
                |
        +-------+-------+-------+
        |       |       |       |
       OT₁     OT₂     OT₃     ...
        |       |       |       |
        +-------+-------+-------+
                |
        comparative observation

All branches start from the same source state.

The benchmark compares branches by observed properties rather than
selecting a single canonical winner.

Primary dimensions:

    1. productivity recovery
    2. expansion of distinctions
    3. generation of new questions
    4. deadlock generation
    5. resource cost
    6. observation horizon

The benchmark explicitly preserves:

    Branch Failure != Process Termination

and:

    Comparative Productivity != Ontological Truth

The synthetic branch data in this benchmark are fixtures for testing
the exploration/comparison architecture. They are not empirical
measurements of the mechanisms themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from orthogonal_transition_explorer_v1 import (
    OTMechanism,
    OrthogonalTransitionExplorer,
    BranchStatus,
    ExplorationResult,
    BranchProductivity,
    productivity_frontier,
)


# ----------------------------------------------------------------------
# Benchmark configuration
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class BenchmarkConfig:
    source_space: str = "C_k"

    initial_productivity: float = 1.0

    observation_steps: int = 10

    require_process_continuity: bool = True

    require_changed_conditions: bool = True


# ----------------------------------------------------------------------
# Synthetic branch fixtures
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class BranchFixture:
    mechanism: OTMechanism

    productivity_after: float

    new_distinctions: int

    new_questions: int

    new_deadlocks: int

    resource_cost: float

    preserves_continuity: bool = True

    changes_conditions: bool = True

    failed: bool = False

    deadlock: bool = False


def default_fixtures() -> List[BranchFixture]:

    return [

        BranchFixture(
            mechanism=OTMechanism.SCALE,
            productivity_after=0.90,
            new_distinctions=4,
            new_questions=2,
            new_deadlocks=1,
            resource_cost=5.0,
        ),

        BranchFixture(
            mechanism=OTMechanism.COMPENSATORY_MULTIPLICATION,
            productivity_after=1.35,
            new_distinctions=9,
            new_questions=5,
            new_deadlocks=2,
            resource_cost=8.0,
        ),

        BranchFixture(
            mechanism=OTMechanism.STRUCTURAL_RECONFIGURATION,
            productivity_after=1.25,
            new_distinctions=7,
            new_questions=4,
            new_deadlocks=1,
            resource_cost=7.0,
        ),

        BranchFixture(
            mechanism=OTMechanism.CARRIER_TRANSITION,
            productivity_after=0.75,
            new_distinctions=3,
            new_questions=2,
            new_deadlocks=2,
            resource_cost=9.0,
        ),

        BranchFixture(
            mechanism=OTMechanism.INTERACTION_REGIME,
            productivity_after=1.30,
            new_distinctions=8,
            new_questions=6,
            new_deadlocks=1,
            resource_cost=10.0,
        ),

        BranchFixture(
            mechanism=OTMechanism.REPRESENTATION_SPACE,
            productivity_after=1.15,
            new_distinctions=10,
            new_questions=8,
            new_deadlocks=0,
            resource_cost=6.0,
        ),

        BranchFixture(
            mechanism=OTMechanism.COMPOSITION_DECOMPOSITION,
            productivity_after=1.05,
            new_distinctions=6,
            new_questions=4,
            new_deadlocks=1,
            resource_cost=5.0,
        ),

        BranchFixture(
            mechanism=OTMechanism.UNKNOWN_EMERGENT,
            productivity_after=1.45,
            new_distinctions=12,
            new_questions=9,
            new_deadlocks=3,
            resource_cost=15.0,
        ),
    ]


# ----------------------------------------------------------------------
# Benchmark runner
# ----------------------------------------------------------------------


class OrthogonalTransitionExplorerBenchmark:

    def __init__(
        self,
        config: BenchmarkConfig | None = None,
    ) -> None:

        self.config = (
            config
            if config is not None
            else BenchmarkConfig()
        )

        self.explorer = (
            OrthogonalTransitionExplorer()
        )

    # ------------------------------------------------------------------
    # Build common source state
    # ------------------------------------------------------------------

    def create_branches(
        self,
        fixtures: List[BranchFixture],
    ):

        branches = (
            self.explorer.generate_candidates(
                source_space=(
                    self.config.source_space
                ),
                mechanisms=[
                    fixture.mechanism
                    for fixture in fixtures
                ],
            )
        )

        fixture_by_mechanism = {
            fixture.mechanism: fixture
            for fixture in fixtures
        }

        for branch in branches:

            fixture = fixture_by_mechanism[
                branch.mechanism
            ]

            branch.preserves_process_continuity = (
                fixture.preserves_continuity
            )

            branch.changes_differentiation_conditions = (
                fixture.changes_conditions
            )

        return branches

    # ------------------------------------------------------------------
    # Execute all branches
    # ------------------------------------------------------------------

    def execute(
        self,
        fixtures: List[BranchFixture],
    ) -> ExplorationResult:

        branches = self.create_branches(
            fixtures
        )

        fixture_by_mechanism = {
            fixture.mechanism: fixture
            for fixture in fixtures
        }

        for branch in branches:

            fixture = fixture_by_mechanism[
                branch.mechanism
            ]

            self.explorer.validate_candidate(
                branch
            )

            if branch.status == BranchStatus.VALIDATED:

                self.explorer.activate(
                    branch
                )

            if branch.status != BranchStatus.ACTIVE:
                continue

            self.explorer.observe(
                branch,

                productive_difference_before=(
                    self.config.initial_productivity
                ),

                productive_difference_after=(
                    fixture.productivity_after
                ),

                new_distinctions=(
                    fixture.new_distinctions
                ),

                new_questions=(
                    fixture.new_questions
                ),

                new_deadlocks=(
                    fixture.new_deadlocks
                ),

                resource_cost=(
                    fixture.resource_cost
                ),

                observation_steps=(
                    self.config.observation_steps
                ),

                deadlock=(
                    fixture.deadlock
                ),

                failed=(
                    fixture.failed
                ),
            )

        return self.explorer.explore(
            branches
        )


# ----------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------


def branch_efficiency(
    item: BranchProductivity,
) -> float:

    """
    Simple descriptive efficiency:

        (productivity gain + new distinctions)
        / resource cost

    This is NOT an intelligence score.

    It exists only to make resource/productivity tradeoffs
    observable.
    """

    numerator = (
        item.productivity_delta
        + item.new_distinctions
    )

    if item.resource_cost <= 0:
        return numerator

    return numerator / item.resource_cost


def branch_diversification(
    item: BranchProductivity,
) -> float:

    """
    Descriptive measure of generated possibility space.

    New distinctions and new questions are both counted because
    a branch may be productive by creating new problems rather
    than immediately producing stable results.
    """

    return float(
        item.new_distinctions
        + item.new_questions
    )


def compare_branches(
    result: ExplorationResult,
) -> List[Dict[str, Any]]:

    rows: List[Dict[str, Any]] = []

    for item in result.comparisons:

        rows.append(
            {
                "branch_id": item.branch_id,
                "mechanism": item.mechanism,

                "productivity_delta": (
                    item.productivity_delta
                ),

                "productivity_ratio": (
                    item.productivity_ratio
                ),

                "new_distinctions": (
                    item.new_distinctions
                ),

                "new_questions": (
                    item.new_questions
                ),

                "new_deadlocks": (
                    item.new_deadlocks
                ),

                "resource_cost": (
                    item.resource_cost
                ),

                "efficiency": (
                    branch_efficiency(item)
                ),

                "diversification": (
                    branch_diversification(item)
                ),

                "productive": (
                    item.productive
                ),
            }
        )

    return rows


# ----------------------------------------------------------------------
# Invariant tests
# ----------------------------------------------------------------------


def test_same_initial_state(
    result: ExplorationResult,
    config: BenchmarkConfig,
) -> bool:

    return all(
        branch.productive_difference_before
        == config.initial_productivity
        for branch in result.branches
        if branch.observation_steps > 0
    )


def test_parallel_branches(
    result: ExplorationResult,
) -> bool:

    return (
        len(result.branches)
        > 1
        and len(result.comparisons)
        > 1
    )


def test_no_forced_selection(
    result: ExplorationResult,
) -> bool:

    return (
        result.selection_required
        is False
    )


def test_process_continuity(
    result: ExplorationResult,
) -> bool:

    return (
        result.process_continuity_preserved
        is True
    )


def test_branch_results_are_distinguishable(
    result: ExplorationResult,
) -> bool:

    mechanisms = {
        item.mechanism
        for item in result.comparisons
    }

    return (
        len(mechanisms)
        > 1
    )


def test_productivity_is_observed(
    result: ExplorationResult,
) -> bool:

    return all(
        item.productivity_ratio >= 0
        for item in result.comparisons
    )


def test_frontier_exists(
    result: ExplorationResult,
) -> bool:

    frontier = productivity_frontier(
        result
    )

    return len(frontier) >= 1


# ----------------------------------------------------------------------
# Explicit failure branch test
# ----------------------------------------------------------------------


def test_branch_failure_does_not_terminate_process() -> bool:

    fixtures = default_fixtures()

    fixtures = list(
        fixtures
    )

    fixtures[0] = BranchFixture(
        mechanism=OTMechanism.SCALE,

        productivity_after=0.0,

        new_distinctions=0,

        new_questions=0,

        new_deadlocks=1,

        resource_cost=5.0,

        preserves_continuity=True,

        changes_conditions=True,

        failed=True,
    )

    benchmark = (
        OrthogonalTransitionExplorerBenchmark()
    )

    result = benchmark.execute(
        fixtures
    )

    failed_branch = next(
        branch
        for branch in result.branches
        if branch.mechanism
        == OTMechanism.SCALE
    )

    other_branches = [
        branch
        for branch in result.branches
        if branch.mechanism
        != OTMechanism.SCALE
    ]

    return (
        failed_branch.status
        == BranchStatus.FAILED
        and len(other_branches)
        > 0
        and result.process_continuity_preserved
        is True
    )


# ----------------------------------------------------------------------
# Full benchmark
# ----------------------------------------------------------------------


def run_benchmark() -> Dict[str, Any]:

    config = BenchmarkConfig()

    fixtures = default_fixtures()

    benchmark = (
        OrthogonalTransitionExplorerBenchmark(
            config=config
        )
    )

    result = benchmark.execute(
        fixtures
    )

    checks = {
        "same_initial_state": (
            test_same_initial_state(
                result,
                config,
            )
        ),

        "parallel_branches": (
            test_parallel_branches(
                result
            )
        ),

        "no_forced_selection": (
            test_no_forced_selection(
                result
            )
        ),

        "process_continuity": (
            test_process_continuity(
                result
            )
        ),

        "branch_results_distinguishable": (
            test_branch_results_are_distinguishable(
                result
            )
        ),

        "productivity_observed": (
            test_productivity_is_observed(
                result
            )
        ),

        "frontier_exists": (
            test_frontier_exists(
                result
            )
        ),

        "branch_failure_does_not_terminate_process": (
            test_branch_failure_does_not_terminate_process()
        ),
    }

    rows = compare_branches(
        result
    )

    return {
        "benchmark": (
            "orthogonal_transition_explorer_benchmark_v1"
        ),

        "source_space": (
            config.source_space
        ),

        "initial_productivity": (
            config.initial_productivity
        ),

        "observation_steps": (
            config.observation_steps
        ),

        "branches": len(
            result.branches
        ),

        "comparisons": len(
            result.comparisons
        ),

        "checks": checks,

        "passed": sum(
            1
            for value in checks.values()
            if value
        ),

        "failed": sum(
            1
            for value in checks.values()
            if not value
        ),

        "all_passed": all(
            checks.values()
        ),

        "selection_required": (
            result.selection_required
        ),

        "process_continuity_preserved": (
            result.process_continuity_preserved
        ),

        "branch_comparison": rows,

        "productivity_frontier": [
            {
                "branch_id": item.branch_id,
                "mechanism": item.mechanism,
                "productivity_delta": (
                    item.productivity_delta
                ),
                "new_distinctions": (
                    item.new_distinctions
                ),
                "new_questions": (
                    item.new_questions
                ),
                "resource_cost": (
                    item.resource_cost
                ),
                "efficiency": (
                    branch_efficiency(item)
                ),
            }
            for item in productivity_frontier(
                result
            )
        ],

        "invariants": [
            "Same initial state for all branches",
            "Parallel OT exploration",
            "No mandatory branch selection",
            "Branch results remain individually observable",
            "Branch failure does not terminate the process",
            "Comparative productivity is descriptive",
            "Productivity is not an ontological truth criterion",
        ],
    }


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------


def print_report(
    report: Dict[str, Any],
) -> None:

    print(
        "UFCPS — Orthogonal Transition Explorer "
        "Benchmark v1"
    )

    print(
        "=" * 68
    )

    print(
        f"Source space: "
        f"{report['source_space']}"
    )

    print(
        f"Branches: "
        f"{report['branches']}"
    )

    print(
        f"Comparisons: "
        f"{report['comparisons']}"
    )

    print(
        f"Passed: "
        f"{report['passed']}"
    )

    print(
        f"Failed: "
        f"{report['failed']}"
    )

    print(
        f"All passed: "
        f"{report['all_passed']}"
    )

    print(
        "\nChecks:"
    )

    for name, passed in (
        report["checks"].items()
    ):

        marker = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"  [{marker}] {name}"
        )

    print(
        "\nBranch comparison:"
    )

    for row in (
        report["branch_comparison"]
    ):

        print(
            f"  {row['branch_id']:16s} "
            f"{row['mechanism']:30s} "
            f"ΔP={row['productivity_delta']:+.3f} "
            f"D={row['new_distinctions']:2d} "
            f"Q={row['new_questions']:2d} "
            f"F={row['new_deadlocks']:2d} "
            f"cost={row['resource_cost']:.1f} "
            f"eff={row['efficiency']:.3f}"
        )

    print(
        "\nProductivity frontier:"
    )

    for row in (
        report["productivity_frontier"]
    ):

        print(
            f"  {row['branch_id']:16s} "
            f"{row['mechanism']}"
        )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> int:

    report = run_benchmark()

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
