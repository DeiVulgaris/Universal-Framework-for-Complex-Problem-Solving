"""
UFCPS — Branch Interaction Benchmark v1

Validates the interaction layer between localized OT branches.

The benchmark verifies:

    1. interaction can generate an emergent distinction;
    2. interaction can expose a candidate invariant;
    3. a candidate invariant can become SUPPORTED after
       repeated preservation under transformations;
    4. a candidate invariant can become REFUTED after a
       counterexample;
    5. branch interaction does not collapse branch identity;
    6. branch failure does not terminate the global process;
    7. emergent distinction and invariant detection are
       separate outcomes.

This benchmark uses synthetic fixtures.

It validates architecture, not physical or empirical claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from branch_interaction_v1 import (
    BranchInteractionEngine,
    CandidateInvariant,
    InvariantStatus,
    InteractionStatus,
    LocalizedBranch,
)


# ----------------------------------------------------------------------
# Benchmark fixture
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class InteractionFixture:
    name: str
    branches: List[LocalizedBranch]


def fixture_common_invariant() -> InteractionFixture:

    return InteractionFixture(
        name="common_invariant",

        branches=[
            LocalizedBranch(
                branch_id="OT_A",
                mechanism="SCALE",
                state_id="STATE_A",

                distinctions=(
                    "node",
                    "distance",
                    "boundary_A",
                ),

                relations=(
                    "persistence",
                    "coupling",
                ),
            ),

            LocalizedBranch(
                branch_id="OT_B",
                mechanism="STRUCTURAL_RECONFIGURATION",
                state_id="STATE_B",

                distinctions=(
                    "node",
                    "topology",
                    "boundary_B",
                ),

                relations=(
                    "persistence",
                    "coupling",
                ),
            ),

            LocalizedBranch(
                branch_id="OT_C",
                mechanism="REPRESENTATION_SPACE",
                state_id="STATE_C",

                distinctions=(
                    "representation",
                    "node",
                    "boundary_C",
                ),

                relations=(
                    "persistence",
                    "coupling",
                ),
            ),
        ],
    )


def fixture_emergent_difference() -> InteractionFixture:

    return InteractionFixture(
        name="emergent_difference",

        branches=[
            LocalizedBranch(
                branch_id="OT_A",
                mechanism="SCALE",
                state_id="STATE_A",

                distinctions=(
                    "node",
                    "distance",
                ),

                relations=(
                    "coupling",
                    "persistence",
                    "scale_relation_A",
                ),
            ),

            LocalizedBranch(
                branch_id="OT_B",
                mechanism="INTERACTION_REGIME",
                state_id="STATE_B",

                distinctions=(
                    "node",
                    "boundary",
                ),

                relations=(
                    "coupling",
                    "persistence",
                    "interaction_relation_B",
                ),
            ),
        ],
    )


def fixture_no_invariant() -> InteractionFixture:

    return InteractionFixture(
        name="no_common_invariant",

        branches=[
            LocalizedBranch(
                branch_id="OT_A",
                mechanism="SCALE",
                state_id="STATE_A",

                distinctions=(
                    "a",
                ),

                relations=(
                    "relation_A",
                ),
            ),

            LocalizedBranch(
                branch_id="OT_B",
                mechanism="CARRIER_TRANSITION",
                state_id="STATE_B",

                distinctions=(
                    "b",
                ),

                relations=(
                    "relation_B",
                ),
            ),

            LocalizedBranch(
                branch_id="OT_C",
                mechanism="REPRESENTATION_SPACE",
                state_id="STATE_C",

                distinctions=(
                    "c",
                ),

                relations=(
                    "relation_C",
                ),
            ),
        ],
    )


# ----------------------------------------------------------------------
# Benchmark
# ----------------------------------------------------------------------


class BranchInteractionBenchmark:

    def __init__(self) -> None:

        self.engine = (
            BranchInteractionEngine()
        )

    # ------------------------------------------------------------------
    # Test 1
    # ------------------------------------------------------------------

    def test_emergent_distinction(
        self,
    ) -> Dict[str, Any]:

        fixture = (
            fixture_emergent_difference()
        )

        result = self.engine.interact(
            fixture.branches,
            interaction_id="TEST_DNEW",
        )

        passed = (
            len(
                result.emergent_distinctions
            )
            > 0
        )

        return {
            "passed": passed,
            "interaction_status": (
                result.status.value
            ),
            "emergent_distinctions": len(
                result.emergent_distinctions
            ),
            "questions": len(
                result.new_questions
            ),
        }

    # ------------------------------------------------------------------
    # Test 2
    # ------------------------------------------------------------------

    def test_candidate_invariant(
        self,
    ) -> Dict[str, Any]:

        fixture = (
            fixture_common_invariant()
        )

        result = self.engine.interact(
            fixture.branches,
            interaction_id="TEST_INVARIANT",
        )

        candidates = (
            result.candidate_invariants
        )

        passed = (
            len(candidates) >= 1
            and all(
                candidate.status
                == InvariantStatus.CANDIDATE
                for candidate in candidates
            )
        )

        return {
            "passed": passed,
            "candidate_count": len(
                candidates
            ),
            "status": [
                candidate.status.value
                for candidate in candidates
            ],
        }

    # ------------------------------------------------------------------
    # Test 3
    # ------------------------------------------------------------------

    def test_invariant_support(
        self,
    ) -> Dict[str, Any]:

        fixture = (
            fixture_common_invariant()
        )

        result = self.engine.interact(
            fixture.branches,
            interaction_id="TEST_SUPPORT",
        )

        if not result.candidate_invariants:

            return {
                "passed": False,
                "reason": (
                    "No candidate invariant generated."
                ),
            }

        candidate = (
            result.candidate_invariants[0]
        )

        self.engine.test_invariant(
            candidate,
            preserved=True,
            transformation_id="T1",
        )

        status_after_t1 = (
            candidate.status.value
        )

        self.engine.test_invariant(
            candidate,
            preserved=True,
            transformation_id="T2",
        )

        status_after_t2 = (
            candidate.status.value
        )

        passed = (
            status_after_t1
            == InvariantStatus.CANDIDATE.value
            and status_after_t2
            == InvariantStatus.SUPPORTED.value
        )

        return {
            "passed": passed,
            "status_after_T1": status_after_t1,
            "status_after_T2": status_after_t2,
            "preservation_count": (
                candidate.preservation_count
            ),
            "violation_count": (
                candidate.violation_count
            ),
        }

    # ------------------------------------------------------------------
    # Test 4
    # ------------------------------------------------------------------

    def test_invariant_refutation(
        self,
    ) -> Dict[str, Any]:

        fixture = (
            fixture_common_invariant()
        )

        result = self.engine.interact(
            fixture.branches,
            interaction_id="TEST_REFUTATION",
        )

        if not result.candidate_invariants:

            return {
                "passed": False,
                "reason": (
                    "No candidate invariant generated."
                ),
            }

        candidate = (
            result.candidate_invariants[0]
        )

        self.engine.test_invariant(
            candidate,
            preserved=True,
            transformation_id="T1",
        )

        self.engine.test_invariant(
            candidate,
            preserved=False,
            transformation_id="T2_COUNTEREXAMPLE",
        )

        passed = (
            candidate.status
            == InvariantStatus.REFUTED
        )

        return {
            "passed": passed,
            "final_status": (
                candidate.status.value
            ),
            "preservation_count": (
                candidate.preservation_count
            ),
            "violation_count": (
                candidate.violation_count
            ),
        }

    # ------------------------------------------------------------------
    # Test 5
    # ------------------------------------------------------------------

    def test_no_invariant(
        self,
    ) -> Dict[str, Any]:

        fixture = (
            fixture_no_invariant()
        )

        result = self.engine.interact(
            fixture.branches,
            interaction_id="TEST_NO_INVARIANT",
        )

        passed = (
            len(
                result.candidate_invariants
            )
            == 0
        )

        return {
            "passed": passed,
            "candidate_count": len(
                result.candidate_invariants
            ),
            "status": result.status.value,
        }

    # ------------------------------------------------------------------
    # Test 6
    # ------------------------------------------------------------------

    def test_branch_identity_preserved(
        self,
    ) -> Dict[str, Any]:

        fixture = (
            fixture_common_invariant()
        )

        original_ids = tuple(
            branch.branch_id
            for branch in fixture.branches
        )

        result = self.engine.interact(
            fixture.branches,
            interaction_id="TEST_IDENTITY",
        )

        resulting_ids = (
            result.branch_ids
        )

        passed = (
            original_ids
            == resulting_ids
        )

        return {
            "passed": passed,
            "original_branch_ids": (
                original_ids
            ),
            "result_branch_ids": (
                resulting_ids
            ),
        }

    # ------------------------------------------------------------------
    # Test 7
    # ------------------------------------------------------------------

    def test_branch_failure_does_not_terminate_process(
        self,
    ) -> Dict[str, Any]:

        branches = [

            LocalizedBranch(
                branch_id="OT_FAILED",
                mechanism="SCALE",
                state_id="STATE_FAILED",

                distinctions=(
                    "failed_node",
                ),

                relations=(
                    "failed_relation",
                ),

                productive=False,
            ),

            LocalizedBranch(
                branch_id="OT_ACTIVE",
                mechanism="REPRESENTATION_SPACE",
                state_id="STATE_ACTIVE",

                distinctions=(
                    "active_node",
                ),

                relations=(
                    "persistence",
                ),

                productive=True,
            ),

            LocalizedBranch(
                branch_id="OT_ACTIVE_2",
                mechanism="INTERACTION_REGIME",
                state_id="STATE_ACTIVE_2",

                distinctions=(
                    "active_node_2",
                ),

                relations=(
                    "persistence",
                ),

                productive=True,
            ),
        ]

        result = self.engine.interact(
            branches,
            interaction_id="TEST_FAILURE_CONTINUITY",
        )

        passed = (
            len(result.branch_ids) == 3
            and result.status
            != InteractionStatus.DEADLOCK
        )

        return {
            "passed": passed,
            "branch_count": len(
                result.branch_ids
            ),
            "interaction_status": (
                result.status.value
            ),
        }

    # ------------------------------------------------------------------
    # Test 8
    # ------------------------------------------------------------------

    def test_interaction_generates_questions(
        self,
    ) -> Dict[str, Any]:

        fixture = (
            fixture_common_invariant()
        )

        result = self.engine.interact(
            fixture.branches,
            interaction_id="TEST_QUESTIONS",
        )

        passed = (
            len(
                result.new_questions
            )
            > 0
        )

        return {
            "passed": passed,
            "question_count": len(
                result.new_questions
            ),
        }

    # ------------------------------------------------------------------
    # Test 9
    # ------------------------------------------------------------------

    def test_emergent_distinction_and_invariant_are_distinct(
        self,
    ) -> Dict[str, Any]:

        fixture = (
            fixture_common_invariant()
        )

        result = self.engine.interact(
            fixture.branches,
            interaction_id="TEST_BOTH",
        )

        has_distinction = (
            len(
                result.emergent_distinctions
            )
            > 0
        )

        has_invariant = (
            len(
                result.candidate_invariants
            )
            > 0
        )

        passed = (
            has_distinction
            and has_invariant
            and result.status
            == InteractionStatus.BOTH
        )

        return {
            "passed": passed,
            "has_emergent_distinction": (
                has_distinction
            ),
            "has_candidate_invariant": (
                has_invariant
            ),
            "status": result.status.value,
        }

    # ------------------------------------------------------------------
    # Run all
    # ------------------------------------------------------------------

    def run(
        self,
    ) -> Dict[str, Any]:

        tests = {
            "emergent_distinction": (
                self.test_emergent_distinction()
            ),

            "candidate_invariant": (
                self.test_candidate_invariant()
            ),

            "invariant_support": (
                self.test_invariant_support()
            ),

            "invariant_refutation": (
                self.test_invariant_refutation()
            ),

            "no_invariant": (
                self.test_no_invariant()
            ),

            "branch_identity_preserved": (
                self.test_branch_identity_preserved()
            ),

            "branch_failure_does_not_terminate_process": (
                self.test_branch_failure_does_not_terminate_process()
            ),

            "interaction_generates_questions": (
                self.test_interaction_generates_questions()
            ),

            "distinction_and_invariant_are_distinct": (
                self.test_emergent_distinction_and_invariant_are_distinct()
            ),
        }

        passed = sum(
            1
            for test in tests.values()
            if test["passed"]
        )

        failed = (
            len(tests)
            - passed
        )

        return {
            "benchmark": (
                "branch_interaction_benchmark_v1"
            ),

            "tests": len(tests),

            "passed": passed,

            "failed": failed,

            "all_passed": (
                failed == 0
            ),

            "results": tests,

            "invariants": [
                "Interaction can generate D_new",
                "Interaction can expose I_candidate",
                "Candidate invariant requires testing",
                "Counterexample can refute invariant",
                "Branch identity survives interaction",
                "Branch failure does not imply process termination",
                "Interaction can generate new questions",
                "D_new and I_candidate are distinct outcomes",
            ],
        }


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------


def print_report(
    report: Dict[str, Any],
) -> None:

    print(
        "UFCPS — Branch Interaction Benchmark v1"
    )

    print(
        "=" * 66
    )

    print(
        f"Tests:      {report['tests']}"
    )

    print(
        f"Passed:     {report['passed']}"
    )

    print(
        f"Failed:     {report['failed']}"
    )

    print(
        f"All passed: {report['all_passed']}"
    )

    print(
        "\nResults:"
    )

    for name, result in (
        report["results"].items()
    ):

        marker = (
            "PASS"
            if result["passed"]
            else "FAIL"
        )

        print(
            f"  [{marker}] {name}"
        )

        for key, value in result.items():

            if key == "passed":
                continue

            print(
                f"      {key}: {value}"
            )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> int:

    benchmark = (
        BranchInteractionBenchmark()
    )

    report = benchmark.run()

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
