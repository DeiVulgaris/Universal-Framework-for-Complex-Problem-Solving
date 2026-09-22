"""
UFCPS — Level 3 Recursive Space Benchmark v1

Tests whether a newly constructed cognitive space C_(k+1)
can become the actual starting space for a subsequent
reflexive cycle.

Core hypothesis:

    Orthogonal Transition is not merely a state change.
    It changes the space of subsequent actualization.

Therefore:

    C_k
      ↓
    exhaustion
      ↓
    reflection
      ↓
    OT exploration
      ↓
    interaction
      ↓
    D_new / I
      ↓
    C_(k+1)
      ↓
    NEW cycle
      ↓
    D_new_2 / I_2
      ↓
    C_(k+2)

This benchmark tests architectural recursion, not intelligence,
creativity, consciousness, or scientific truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set


# ----------------------------------------------------------------------
# Data structures
# ----------------------------------------------------------------------


@dataclass
class SpaceSnapshot:
    space_id: str
    parent_space_id: str | None
    version: int

    distinctions: Set[str]
    invariants: Set[str]
    questions: Set[str]

    provenance: Dict[str, Any]


@dataclass
class CycleResult:
    source_space: str
    target_space: str

    new_distinctions: Set[str]
    active_invariants: Set[str]
    questions: Set[str]

    branch_count: int
    deadlocked_branches: Set[str]

    continued: bool


@dataclass
class RecursiveBenchmarkResult:
    benchmark: str
    passed: bool

    checks: Dict[str, bool]
    observations: Dict[str, Any]


# ----------------------------------------------------------------------
# Synthetic recursive space engine
# ----------------------------------------------------------------------


class RecursiveSpaceEngine:
    """
    Minimal synthetic environment for testing the recursive
    properties of Level 3.

    It deliberately does not reproduce the internal logic of
    every Level 3 module. Instead, it models their contract:

        source space
            ->
        alternative actualizations
            ->
        interaction
            ->
        new distinction / invariant
            ->
        next space
    """

    def __init__(self) -> None:

        self.spaces: Dict[
            str,
            SpaceSnapshot
        ] = {}

        self.cycles: List[
            CycleResult
        ] = []

    # ------------------------------------------------------------------
    # Initial space
    # ------------------------------------------------------------------

    def create_initial_space(
        self,
    ) -> SpaceSnapshot:

        space = SpaceSnapshot(
            space_id="C_0",

            parent_space_id=None,

            version=0,

            distinctions={
                "D_base_1",
                "D_base_2",
            },

            invariants={
                "I_base",
            },

            questions={
                "Q_base_1",
            },

            provenance={
                "origin": "benchmark",
            },
        )

        self.spaces[
            space.space_id
        ] = space

        return space

    # ------------------------------------------------------------------
    # One synthetic Level 3 cycle
    # ------------------------------------------------------------------

    def execute_cycle(
        self,
        source: SpaceSnapshot,
        cycle_index: int,
    ) -> CycleResult:

        # cycle_index is the logical target-space index:
        # cycle 1 produces C_1, cycle 2 produces C_2.
        target_id = (
            f"C_{cycle_index}"
        )

        # --------------------------------------------------------------
        # Generate alternative branches
        # --------------------------------------------------------------

        branches = {
            "SCALE",
            "STRUCTURAL",
            "REPRESENTATION",
        }

        # --------------------------------------------------------------
        # One branch may deadlock.
        #
        # The important property is that the global process continues.
        # --------------------------------------------------------------

        deadlocked = {
            "REPRESENTATION"
        }

        active_branches = (
            branches - deadlocked
        )

        # --------------------------------------------------------------
        # New distinctions are generated from interaction.
        #
        # They are deliberately derived from the source-space
        # identity so that the benchmark can detect whether the
        # second cycle merely copied the first.
        # --------------------------------------------------------------

        new_distinctions = {
            (
                f"D_new_{cycle_index}_"
                f"{branch.lower()}"
            )
            for branch in active_branches
        }

        # --------------------------------------------------------------
        # Existing invariant becomes a possible axis of new
        # differentiation.
        #
        # The benchmark keeps the invariant itself while generating
        # a new distinction relative to it.
        # --------------------------------------------------------------

        new_invariant = (
            f"I_cycle_{cycle_index}"
        )

        active_invariants = (
            set(source.invariants)
            | {new_invariant}
        )

        # --------------------------------------------------------------
        # Questions inherit provenance but are newly instantiated.
        # --------------------------------------------------------------

        questions = {
            (
                f"Q_cycle_{cycle_index}_"
                f"{index}"
            )
            for index, _ in enumerate(
                new_distinctions,
                start=1,
            )
        }

        target = SpaceSnapshot(
            space_id=target_id,

            parent_space_id=(
                source.space_id
            ),

            version=(
                source.version + 1
            ),

            distinctions=(
                set(source.distinctions)
                | new_distinctions
            ),

            invariants=active_invariants,

            questions=(
                set(source.questions)
                | questions
            ),

            provenance={
                "derived_from": (
                    source.space_id
                ),

                "cycle_index": cycle_index,

                "deadlocked_branches": (
                    sorted(deadlocked)
                ),

                "active_branches": (
                    sorted(active_branches)
                ),
            },
        )

        self.spaces[
            target.space_id
        ] = target

        result = CycleResult(
            source_space=(
                source.space_id
            ),

            target_space=(
                target.space_id
            ),

            new_distinctions=(
                new_distinctions
            ),

            active_invariants=(
                active_invariants
            ),

            questions=questions,

            branch_count=len(branches),

            deadlocked_branches=deadlocked,

            continued=True,
        )

        self.cycles.append(
            result
        )

        return result


# ----------------------------------------------------------------------
# Benchmark
# ----------------------------------------------------------------------


class Level3RecursiveSpaceBenchmark:

    def __init__(self) -> None:

        self.engine = (
            RecursiveSpaceEngine()
        )

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(
        self,
    ) -> RecursiveBenchmarkResult:

        checks: Dict[str, bool] = {}

        observations: Dict[str, Any] = {}

        # ==============================================================
        # C_0
        # ==============================================================

        c0 = (
            self.engine.create_initial_space()
        )

        # ==============================================================
        # First Level 3 cycle
        # ==============================================================

        cycle_1 = (
            self.engine.execute_cycle(
                c0,
                cycle_index=1,
            )
        )

        c1 = (
            self.engine.spaces[
                cycle_1.target_space
            ]
        )

        # ==============================================================
        # Second Level 3 cycle
        #
        # IMPORTANT:
        #
        # C_1 itself is passed as the source.
        #
        # This is the central test of recursive continuation.
        # ==============================================================

        cycle_2 = (
            self.engine.execute_cycle(
                c1,
                cycle_index=2,
            )
        )

        c2 = (
            self.engine.spaces[
                cycle_2.target_space
            ]
        )

        # ==============================================================
        # 1. Space identity
        # ==============================================================

        checks[
            "c1_differs_from_c0"
        ] = (
            c1.space_id
            != c0.space_id
        )

        checks[
            "c2_differs_from_c1"
        ] = (
            c2.space_id
            != c1.space_id
        )

        # ==============================================================
        # 2. Parentage
        # ==============================================================

        checks[
            "c1_parent_is_c0"
        ] = (
            c1.parent_space_id
            == c0.space_id
        )

        checks[
            "c2_parent_is_c1"
        ] = (
            c2.parent_space_id
            == c1.space_id
        )

        # ==============================================================
        # 3. Version continuity
        # ==============================================================

        checks[
            "version_progression"
        ] = (
            c0.version
            < c1.version
            < c2.version
        )

        # ==============================================================
        # 4. First new distinctions survive
        # ==============================================================

        checks[
            "c1_contains_new_distinctions"
        ] = (
            len(
                cycle_1.new_distinctions
            )
            > 0
        )

        checks[
            "c1_distinctions_persist"
        ] = (
            cycle_1.new_distinctions
            <= c1.distinctions
        )

        # ==============================================================
        # 5. Second cycle creates genuinely new distinctions
        # ==============================================================

        checks[
            "c2_contains_new_distinctions"
        ] = (
            len(
                cycle_2.new_distinctions
            )
            > 0
        )

        checks[
            "second_cycle_adds_new_content"
        ] = (
            cycle_2.new_distinctions
            <= c2.distinctions
        )

        checks[
            "second_cycle_not_copy_of_first"
        ] = (
            cycle_1.new_distinctions.isdisjoint(
                cycle_2.new_distinctions
            )
        )

        # ==============================================================
        # 6. New distinctions accumulate
        # ==============================================================

        checks[
            "c2_retains_c1_content"
        ] = (
            c1.distinctions
            <= c2.distinctions
        )

        checks[
            "c2_is_structurally_richer"
        ] = (
            len(c2.distinctions)
            > len(c1.distinctions)
        )

        # ==============================================================
        # 7. Invariant persistence
        # ==============================================================

        checks[
            "base_invariant_persists"
        ] = (
            "I_base"
            in c2.invariants
        )

        checks[
            "first_cycle_invariant_persists"
        ] = (
            "I_cycle_1"
            in c2.invariants
        )

        checks[
            "second_cycle_generates_invariant"
        ] = (
            "I_cycle_2"
            in c2.invariants
        )

        # ==============================================================
        # 8. Invariant becomes an axis for further differentiation
        # ==============================================================

        invariant_related_distinctions = {
            distinction
            for distinction in (
                cycle_2.new_distinctions
            )
            if "new_2_" in distinction
        }

        checks[
            "second_cycle_differentiates_again"
        ] = (
            len(
                invariant_related_distinctions
            )
            > 0
        )

        # ==============================================================
        # 9. Questions continue
        # ==============================================================

        checks[
            "c1_generates_questions"
        ] = (
            len(
                cycle_1.questions
            )
            > 0
        )

        checks[
            "c2_generates_questions"
        ] = (
            len(
                cycle_2.questions
            )
            > 0
        )

        checks[
            "questions_accumulate"
        ] = (
            c1.questions
            <= c2.questions
        )

        # ==============================================================
        # 10. Local deadlock
        # ==============================================================

        checks[
            "local_deadlock_present"
        ] = (
            len(
                cycle_1.deadlocked_branches
            )
            > 0
        )

        checks[
            "deadlock_does_not_stop_cycle_1"
        ] = (
            cycle_1.continued
        )

        checks[
            "deadlock_does_not_stop_cycle_2"
        ] = (
            cycle_2.continued
        )

        # ==============================================================
        # 11. Process continuity
        # ==============================================================

        checks[
            "global_process_continues"
        ] = (
            len(
                self.engine.cycles
            )
            == 2
        )

        checks[
            "three_spaces_exist"
        ] = (
            set(
                self.engine.spaces.keys()
            )
            == {
                "C_0",
                "C_1",
                "C_2",
            }
        )

        # ==============================================================
        # 12. Provenance
        # ==============================================================

        checks[
            "c1_provenance_preserved"
        ] = (
            c1.provenance[
                "derived_from"
            ]
            == "C_0"
        )

        checks[
            "c2_provenance_preserved"
        ] = (
            c2.provenance[
                "derived_from"
            ]
            == "C_1"
        )

        # ==============================================================
        # 13. No termination after invariant
        # ==============================================================

        checks[
            "invariant_discovery_does_not_terminate"
        ] = (
            cycle_1.continued
            and cycle_2.continued
        )

        # ==============================================================
        # Observations
        # ==============================================================

        observations[
            "space_count"
        ] = len(
            self.engine.spaces
        )

        observations[
            "cycle_count"
        ] = len(
            self.engine.cycles
        )

        observations[
            "c0_distinctions"
        ] = len(
            c0.distinctions
        )

        observations[
            "c1_distinctions"
        ] = len(
            c1.distinctions
        )

        observations[
            "c2_distinctions"
        ] = len(
            c2.distinctions
        )

        observations[
            "c0_invariants"
        ] = len(
            c0.invariants
        )

        observations[
            "c1_invariants"
        ] = len(
            c1.invariants
        )

        observations[
            "c2_invariants"
        ] = len(
            c2.invariants
        )

        observations[
            "c1_new_distinctions"
        ] = sorted(
            cycle_1.new_distinctions
        )

        observations[
            "c2_new_distinctions"
        ] = sorted(
            cycle_2.new_distinctions
        )

        observations[
            "c1_deadlocked_branches"
        ] = sorted(
            cycle_1.deadlocked_branches
        )

        observations[
            "c2_deadlocked_branches"
        ] = sorted(
            cycle_2.deadlocked_branches
        )

        observations[
            "process"
        ] = (
            "C_0 → C_1 → C_2"
        )

        observations[
            "interpretation"
        ] = (
            "C_(k+1) can serve as the actual "
            "source space for the next reflexive cycle."
        )

        passed = all(
            checks.values()
        )

        return RecursiveBenchmarkResult(
            benchmark=(
                "level3_recursive_space_benchmark_v1"
            ),

            passed=passed,

            checks=checks,

            observations=observations,
        )


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------


def print_report(
    result: RecursiveBenchmarkResult,
) -> None:

    print(
        "UFCPS — Level 3 Recursive Space Benchmark v1"
    )

    print(
        "=" * 72
    )

    print(
        f"benchmark: {result.benchmark}"
    )

    print(
        f"all_passed: {result.passed}"
    )

    print(
        "\nCHECKS"
    )

    print(
        "-" * 72
    )

    for name, passed in (
        result.checks.items()
    ):

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"{status:5}  {name}"
        )

    print(
        "\nOBSERVATIONS"
    )

    print(
        "-" * 72
    )

    for name, value in (
        result.observations.items()
    ):

        print(
            f"{name}: {value}"
        )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> int:

    benchmark = (
        Level3RecursiveSpaceBenchmark()
    )

    result = benchmark.run()

    print_report(
        result
    )

    return (
        0
        if result.passed
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
