"""
UFCPS — Level 3 Runtime Cycle Benchmark v1

End-to-end recursive test of the actual Level 3 integration.

This benchmark uses:

    Level3EmergentIntegration
            ↓
        C_(k+1)
            ↓
    Level3EmergentIntegration
            ↓
        C_(k+2)

The important distinction from the previous benchmark is that
this test does NOT use a separate synthetic recursive engine.

The actual integration pipeline is executed twice.

Pipeline:

    C_k
      ↓
    OT branches
      ↓
    Branch Interaction
      ↓
    D_new / I_candidate
      ↓
    UQL
      ↓
    Emergent Space Builder
      ↓
    C_(k+1)
      ↓
    SAME INTEGRATION AGAIN
      ↓
    C_(k+2)

The benchmark checks architectural recursion.

It does NOT measure:
    - intelligence;
    - consciousness;
    - creativity;
    - scientific truth;
    - quality of generated distinctions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set

from level3_emergent_integration_v1 import (
    InMemoryUQLAdapter,
    Level3EmergentIntegration,
)


# ----------------------------------------------------------------------
# Result
# ----------------------------------------------------------------------


@dataclass
class RuntimeCycleBenchmarkResult:

    benchmark: str

    passed: bool

    checks: Dict[str, bool]

    observations: Dict[str, Any]


# ----------------------------------------------------------------------
# Benchmark
# ----------------------------------------------------------------------


class Level3RuntimeCycleBenchmark:

    def __init__(self) -> None:

        # One UQL instance is intentionally shared between
        # both cycles.
        #
        # This is important:
        #
        #     C_k → C_(k+1) → C_(k+2)
        #
        # must remain one persistent process history.

        self.uql = (
            InMemoryUQLAdapter()
        )

        self.integration = (
            Level3EmergentIntegration(
                uql=self.uql
            )
        )

    # ------------------------------------------------------------------
    # First cycle
    # ------------------------------------------------------------------

    def run_first_cycle(self):

        return self.integration.run(
            source_space_id="C_k",
            source_space_version=1,
        )

    # ------------------------------------------------------------------
    # Second cycle
    # ------------------------------------------------------------------

    def run_second_cycle(
        self,
        first_result,
    ):

        # The output of the first cycle becomes
        # the explicit source of the second cycle.

        return self.integration.run(
            source_space_id=(
                first_result.next_space.space_id
            ),

            source_space_version=(
                first_result.next_space.version
            ),
        )

    # ------------------------------------------------------------------
    # Run benchmark
    # ------------------------------------------------------------------

    def run(
        self,
    ) -> RuntimeCycleBenchmarkResult:

        checks: Dict[str, bool] = {}

        observations: Dict[str, Any] = {}

        # ==============================================================
        # C_k → C_(k+1)
        # ==============================================================

        first = (
            self.run_first_cycle()
        )

        c1 = (
            first.next_space
        )

        # ==============================================================
        # C_(k+1) → C_(k+2)
        # ==============================================================

        second = (
            self.run_second_cycle(
                first
            )
        )

        c2 = (
            second.next_space
        )

        # ==============================================================
        # 1. First transition exists
        # ==============================================================

        checks[
            "first_transition_created"
        ] = (
            c1.space_id
            == "C_k+1"
        )

        checks[
            "first_transition_advanced_version"
        ] = (
            c1.version
            == 2
        )

        # ==============================================================
        # 2. Second transition is based on C_(k+1)
        # ==============================================================

        checks[
            "second_cycle_source_is_c1"
        ] = (
            second.source_space
            == c1.space_id
        )

        checks[
            "second_cycle_parent_is_c1"
        ] = (
            c2.parent_space_id
            == c1.space_id
        )

        checks[
            "second_transition_advanced_version"
        ] = (
            c2.version
            == c1.version + 1
        )

        # ==============================================================
        # 3. Space identity changes
        # ==============================================================

        checks[
            "c1_differs_from_source"
        ] = (
            c1.space_id
            != first.source_space
        )

        checks[
            "c2_differs_from_c1"
        ] = (
            c2.space_id
            != c1.space_id
        )

        # ==============================================================
        # 4. First cycle produced new distinctions
        # ==============================================================

        first_distinctions = set(
            c1.accessible_distinctions
        )

        checks[
            "first_cycle_created_distinctions"
        ] = (
            len(
                first_distinctions
            )
            > 0
        )

        # ==============================================================
        # 5. Second cycle also produced distinctions
        # ==============================================================

        second_distinctions = set(
            c2.accessible_distinctions
        )

        checks[
            "second_cycle_has_distinctions"
        ] = (
            len(
                second_distinctions
            )
            > 0
        )

        # ==============================================================
        # 6. Second space retains first-space content
        # ==============================================================

        checks[
            "c1_content_survives"
        ] = (
            first_distinctions
            <= second_distinctions
        )

        # ==============================================================
        # 7. Second cycle adds something beyond C1
        # ==============================================================

        second_only = (
            second_distinctions
            - first_distinctions
        )

        checks[
            "second_cycle_adds_content"
        ] = (
            len(second_only)
            > 0
        )

        # ==============================================================
        # 8. Interaction occurred twice
        # ==============================================================

        checks[
            "first_interaction_occurred"
        ] = (
            first.interaction.status.value
            != "NOT_INTERACTED"
        )

        checks[
            "second_interaction_occurred"
        ] = (
            second.interaction.status.value
            != "NOT_INTERACTED"
        )

        # ==============================================================
        # 9. New distinctions occurred in both cycles
        # ==============================================================

        checks[
            "first_cycle_has_emergence"
        ] = (
            len(
                first.interaction
                .emergent_distinctions
            )
            > 0
        )

        checks[
            "second_cycle_has_emergence"
        ] = (
            len(
                second.interaction
                .emergent_distinctions
            )
            > 0
        )

        # ==============================================================
        # 10. Invariants survive continuation
        # ==============================================================

        first_invariants = set(
            first.invariant_ids
        )

        second_invariants = set(
            second.invariant_ids
        )

        checks[
            "first_cycle_has_invariant_output"
        ] = (
            len(
                first_invariants
            )
            > 0
        )

        checks[
            "second_cycle_has_invariant_output"
        ] = (
            len(
                second_invariants
            )
            > 0
        )

        # ==============================================================
        # 11. UQL is persistent across both cycles
        # ==============================================================

        checks[
            "uql_contains_events"
        ] = (
            len(
                self.uql.events
            )
            > 0
        )

        checks[
            "uql_contains_questions"
        ] = (
            len(
                self.uql.questions
            )
            > 0
        )

        # At least one event must belong to each
        # cognitive-space generation.

        generated_spaces = [
            event
            for event in self.uql.events
            if (
                event.event_type
                == "COGNITIVE_SPACE_CREATED"
            )
        ]

        checks[
            "uql_records_both_space_generations"
        ] = (
            len(
                generated_spaces
            )
            >= 2
        )

        # ==============================================================
        # 12. Provenance chain
        # ==============================================================

        checks[
            "first_provenance_points_to_source"
        ] = (
            first.provenance[
                "source_space"
            ]
            == "C_k"
        )

        checks[
            "second_provenance_points_to_c1"
        ] = (
            second.provenance[
                "source_space"
            ]
            == c1.space_id
        )

        # ==============================================================
        # 13. Process continuity
        # ==============================================================

        checks[
            "first_process_not_terminated"
        ] = (
            first.process_terminated
            is False
        )

        checks[
            "second_process_not_terminated"
        ] = (
            second.process_terminated
            is False
        )

        checks[
            "first_continuation_ready"
        ] = (
            first.continuation_ready
            is True
        )

        checks[
            "second_continuation_ready"
        ] = (
            second.continuation_ready
            is True
        )

        # ==============================================================
        # 14. Structural continuity
        # ==============================================================

        checks[
            "c1_structural_continuity"
        ] = (
            c1.structural_continuity
            is True
        )

        checks[
            "c2_structural_continuity"
        ] = (
            c2.structural_continuity
            is True
        )

        checks[
            "content_identity_not_assumed_c1"
        ] = (
            c1.content_identity_with_parent
            is False
        )

        checks[
            "content_identity_not_assumed_c2"
        ] = (
            c2.content_identity_with_parent
            is False
        )

        # ==============================================================
        # 15. Global process chain
        # ==============================================================

        checks[
            "three_level_chain_exists"
        ] = (
            first.source_space
            == "C_k"
            and
            c1.space_id
            == "C_k+1"
            and
            c2.space_id
            == "C_k+1+1"
        )

        # ==============================================================
        # Observations
        # ==============================================================

        observations[
            "process_chain"
        ] = (
            f"{first.source_space}"
            f" → "
            f"{c1.space_id}"
            f" → "
            f"{c2.space_id}"
        )

        observations[
            "c1_version"
        ] = c1.version

        observations[
            "c2_version"
        ] = c2.version

        observations[
            "first_cycle_emergent_distinctions"
        ] = len(
            first.interaction
            .emergent_distinctions
        )

        observations[
            "second_cycle_emergent_distinctions"
        ] = len(
            second.interaction
            .emergent_distinctions
        )

        observations[
            "first_cycle_invariants"
        ] = sorted(
            first_invariants
        )

        observations[
            "second_cycle_invariants"
        ] = sorted(
            second_invariants
        )

        observations[
            "c1_total_distinctions"
        ] = len(
            first_distinctions
        )

        observations[
            "c2_total_distinctions"
        ] = len(
            second_distinctions
        )

        observations[
            "c2_new_content"
        ] = sorted(
            second_only
        )

        observations[
            "uql_event_count"
        ] = len(
            self.uql.events
        )

        observations[
            "uql_question_count"
        ] = len(
            self.uql.questions
        )

        observations[
            "process_terminated"
        ] = (
            first.process_terminated
            or second.process_terminated
        )

        observations[
            "interpretation"
        ] = (
            "The actual Level 3 integration "
            "can use its generated cognitive "
            "space as the source of a subsequent "
            "reflexive cycle."
        )

        passed = all(
            checks.values()
        )

        return RuntimeCycleBenchmarkResult(
            benchmark=(
                "level3_runtime_cycle_benchmark_v1"
            ),

            passed=passed,

            checks=checks,

            observations=observations,
        )


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------


def print_report(
    result: RuntimeCycleBenchmarkResult,
) -> None:

    print(
        "UFCPS — Level 3 Runtime Cycle Benchmark v1"
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
        Level3RuntimeCycleBenchmark()
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
