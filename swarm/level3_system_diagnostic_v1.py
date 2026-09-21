"""
UFCPS — Level 3 System Diagnostic v1

Diagnostic runner for the integrated Level 3 architecture.

Tests the real chain:

    C_k
      ↓
    Level 3 Emergent Integration
      ↓
    C_(k+1)
      ↓
    Level 3 Emergent Integration
      ↓
    C_(k+2)

Unlike the structural benchmarks, this diagnostic is intended
to expose interface, provenance, persistence, and continuation
problems between the already implemented components.

It does not evaluate intelligence or scientific validity.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from level3_emergent_integration_v1 import (
    InMemoryUQLAdapter,
    Level3EmergentIntegration,
)


# ----------------------------------------------------------------------
# Diagnostic result
# ----------------------------------------------------------------------


@dataclass
class DiagnosticCheck:

    name: str

    passed: bool

    value: Any = None

    expected: Any = None

    error: str | None = None


@dataclass
class DiagnosticReport:

    checks: List[DiagnosticCheck] = field(
        default_factory=list
    )

    observations: Dict[str, Any] = field(
        default_factory=dict
    )

    all_passed: bool = False

    runtime_errors: List[str] = field(
        default_factory=list
    )


# ----------------------------------------------------------------------
# Diagnostic runner
# ----------------------------------------------------------------------


class Level3SystemDiagnostic:

    def __init__(self) -> None:

        self.uql = (
            InMemoryUQLAdapter()
        )

        self.integration = (
            Level3EmergentIntegration(
                uql=self.uql
            )
        )

        self.first = None
        self.second = None

    # ------------------------------------------------------------------
    # Safe check
    # ------------------------------------------------------------------

    def check(
        self,
        report: DiagnosticReport,
        name: str,
        function: Callable[[], Any],
        expected: Any = None,
    ) -> Any:

        try:

            value = function()

            passed = (
                True
                if expected is None
                else value == expected
            )

            report.checks.append(
                DiagnosticCheck(
                    name=name,

                    passed=passed,

                    value=value,

                    expected=expected,
                )
            )

            return value

        except Exception as exc:

            error = (
                f"{type(exc).__name__}: {exc}"
            )

            report.checks.append(
                DiagnosticCheck(
                    name=name,

                    passed=False,

                    error=error,
                )
            )

            report.runtime_errors.append(
                traceback.format_exc()
            )

            return None

    # ------------------------------------------------------------------
    # First cycle
    # ------------------------------------------------------------------

    def run_first_cycle(
        self,
        report: DiagnosticReport,
    ):

        self.first = self.check(
            report,

            "cycle_1_execution",

            lambda: self.integration.run(
                source_space_id="C_k",

                source_space_version=1,
            ),
        )

        return self.first

    # ------------------------------------------------------------------
    # Second cycle
    # ------------------------------------------------------------------

    def run_second_cycle(
        self,
        report: DiagnosticReport,
    ):

        if self.first is None:

            return None

        self.second = self.check(
            report,

            "cycle_2_execution",

            lambda: self.integration.run(
                source_space_id=(
                    self.first.next_space.space_id
                ),

                source_space_version=(
                    self.first.next_space.version
                ),
            ),
        )

        return self.second

    # ------------------------------------------------------------------
    # Structural checks
    # ------------------------------------------------------------------

    def check_first_cycle(
        self,
        report: DiagnosticReport,
    ) -> None:

        if self.first is None:
            return

        first = self.first

        self.check(
            report,

            "cycle_1_source",

            lambda: first.source_space,

            "C_k",
        )

        self.check(
            report,

            "cycle_1_next_space",

            lambda: first.next_space.space_id,

            "C_k+1",
        )

        self.check(
            report,

            "cycle_1_version",

            lambda: first.next_space.version,

            2,
        )

        self.check(
            report,

            "cycle_1_continuation",

            lambda: first.continuation_ready,

            True,
        )

        self.check(
            report,

            "cycle_1_not_terminated",

            lambda: first.process_terminated,

            False,
        )

        self.check(
            report,

            "cycle_1_has_emergence",

            lambda: (
                len(
                    first.interaction
                    .emergent_distinctions
                )
                > 0
            ),

            True,
        )

        self.check(
            report,

            "cycle_1_has_questions",

            lambda: (
                len(
                    first.generated_question_ids
                )
                > 0
            ),

            True,
        )

    # ------------------------------------------------------------------
    # Second-cycle checks
    # ------------------------------------------------------------------

    def check_second_cycle(
        self,
        report: DiagnosticReport,
    ) -> None:

        if (
            self.first is None
            or self.second is None
        ):
            return

        first = self.first
        second = self.second

        self.check(
            report,

            "cycle_2_source_is_cycle_1_output",

            lambda: second.source_space,

            first.next_space.space_id,
        )

        self.check(
            report,

            "cycle_2_parent_is_cycle_1_output",

            lambda: second.next_space.parent_space_id,

            first.next_space.space_id,
        )

        self.check(
            report,

            "cycle_2_version_advances",

            lambda: second.next_space.version,

            first.next_space.version + 1,
        )

        self.check(
            report,

            "cycle_2_continuation",

            lambda: second.continuation_ready,

            True,
        )

        self.check(
            report,

            "cycle_2_not_terminated",

            lambda: second.process_terminated,

            False,
        )

        self.check(
            report,

            "cycle_2_has_emergence",

            lambda: (
                len(
                    second.interaction
                    .emergent_distinctions
                )
                > 0
            ),

            True,
        )

    # ------------------------------------------------------------------
    # UQL checks
    # ------------------------------------------------------------------

    def check_uql(
        self,
        report: DiagnosticReport,
    ) -> None:

        self.check(
            report,

            "uql_has_events",

            lambda: (
                len(
                    self.uql.events
                )
                > 0
            ),

            True,
        )

        self.check(
            report,

            "uql_has_questions",

            lambda: (
                len(
                    self.uql.questions
                )
                > 0
            ),

            True,
        )

        self.check(
            report,

            "uql_has_two_space_events",

            lambda: sum(
                event.event_type
                == "COGNITIVE_SPACE_CREATED"
                for event in self.uql.events
            ),

            2,
        )

        self.check(
            report,

            "uql_question_ids_unique",

            lambda: (
                len(
                    {
                        question.question_id
                        for question
                        in self.uql.questions
                    }
                )
                == len(
                    self.uql.questions
                )
            ),

            True,
        )

        self.check(
            report,

            "uql_event_ids_unique",

            lambda: (
                len(
                    {
                        event.event_id
                        for event
                        in self.uql.events
                    }
                )
                == len(
                    self.uql.events
                )
            ),

            True,
        )

    # ------------------------------------------------------------------
    # Provenance checks
    # ------------------------------------------------------------------

    def check_provenance(
        self,
        report: DiagnosticReport,
    ) -> None:

        if (
            self.first is None
            or self.second is None
        ):
            return

        first = self.first
        second = self.second

        self.check(
            report,

            "cycle_1_provenance",

            lambda: (
                first.provenance[
                    "source_space"
                ]
            ),

            "C_k",
        )

        self.check(
            report,

            "cycle_2_provenance",

            lambda: (
                second.provenance[
                    "source_space"
                ]
            ),

            first.next_space.space_id,
        )

        self.check(
            report,

            "cycle_1_continuation_event",

            lambda: (
                bool(
                    first.provenance.get(
                        "continuation_event"
                    )
                )
            ),

            True,
        )

        self.check(
            report,

            "cycle_2_continuation_event",

            lambda: (
                bool(
                    second.provenance.get(
                        "continuation_event"
                    )
                )
            ),

            True,
        )

    # ------------------------------------------------------------------
    # Content checks
    # ------------------------------------------------------------------

    def check_content(
        self,
        report: DiagnosticReport,
    ) -> None:

        if (
            self.first is None
            or self.second is None
        ):
            return

        c1 = self.first.next_space
        c2 = self.second.next_space

        d1 = set(
            c1.accessible_distinctions
        )

        d2 = set(
            c2.accessible_distinctions
        )

        self.check(
            report,

            "c1_contains_distinctions",

            lambda: len(d1) > 0,

            True,
        )

        self.check(
            report,

            "c2_contains_distinctions",

            lambda: len(d2) > 0,

            True,
        )

        self.check(
            report,

            "c1_content_survives",

            lambda: d1 <= d2,

            True,
        )

        self.check(
            report,

            "c2_adds_content",

            lambda: len(d2 - d1) > 0,

            True,
        )

        self.check(
            report,

            "c1_is_not_c2",

            lambda: c1.space_id != c2.space_id,

            True,
        )

        self.check(
            report,

            "c1_content_identity_not_assumed",

            lambda: (
                c1.content_identity_with_parent
                is False
            ),

            True,
        )

        self.check(
            report,

            "c2_content_identity_not_assumed",

            lambda: (
                c2.content_identity_with_parent
                is False
            ),

            True,
        )

    # ------------------------------------------------------------------
    # Interaction checks
    # ------------------------------------------------------------------

    def check_interactions(
        self,
        report: DiagnosticReport,
    ) -> None:

        if (
            self.first is None
            or self.second is None
        ):
            return

        self.check(
            report,

            "first_interaction",

            lambda: (
                self.first.interaction.status.value
                != "NOT_INTERACTED"
            ),

            True,
        )

        self.check(
            report,

            "second_interaction",

            lambda: (
                self.second.interaction.status.value
                != "NOT_INTERACTED"
            ),

            True,
        )

        self.check(
            report,

            "branch_diversity_first_cycle",

            lambda: (
                len(
                    set(
                        self.first.interaction
                        .branch_ids
                    )
                )
                >= 2
            ),

            True,
        )

        self.check(
            report,

            "branch_diversity_second_cycle",

            lambda: (
                len(
                    set(
                        self.second.interaction
                        .branch_ids
                    )
                )
                >= 2
            ),

            True,
        )

    # ------------------------------------------------------------------
    # Diagnostic observations
    # ------------------------------------------------------------------

    def collect_observations(
        self,
        report: DiagnosticReport,
    ) -> None:

        report.observations[
            "uql_event_count"
        ] = len(
            self.uql.events
        )

        report.observations[
            "uql_question_count"
        ] = len(
            self.uql.questions
        )

        if self.first is not None:

            report.observations[
                "cycle_1_source"
            ] = (
                self.first.source_space
            )

            report.observations[
                "cycle_1_target"
            ] = (
                self.first.next_space.space_id
            )

            report.observations[
                "cycle_1_version"
            ] = (
                self.first.next_space.version
            )

            report.observations[
                "cycle_1_distinctions"
            ] = len(
                self.first.next_space
                .accessible_distinctions
            )

            report.observations[
                "cycle_1_invariants"
            ] = len(
                self.first.next_space
                .active_invariants
            )

        if self.second is not None:

            report.observations[
                "cycle_2_source"
            ] = (
                self.second.source_space
            )

            report.observations[
                "cycle_2_target"
            ] = (
                self.second.next_space.space_id
            )

            report.observations[
                "cycle_2_version"
            ] = (
                self.second.next_space.version
            )

            report.observations[
                "cycle_2_distinctions"
            ] = len(
                self.second.next_space
                .accessible_distinctions
            )

            report.observations[
                "cycle_2_invariants"
            ] = len(
                self.second.next_space
                .active_invariants
            )

        report.observations[
            "runtime_error_count"
        ] = len(
            report.runtime_errors
        )

    # ------------------------------------------------------------------
    # Full diagnostic
    # ------------------------------------------------------------------

    def run(
        self,
    ) -> DiagnosticReport:

        report = (
            DiagnosticReport()
        )

        # --------------------------------------------------------------
        # Execute actual cycles
        # --------------------------------------------------------------

        self.run_first_cycle(
            report
        )

        self.run_second_cycle(
            report
        )

        # --------------------------------------------------------------
        # Structural diagnostics
        # --------------------------------------------------------------

        self.check_first_cycle(
            report
        )

        self.check_second_cycle(
            report
        )

        self.check_uql(
            report
        )

        self.check_provenance(
            report
        )

        self.check_content(
            report
        )

        self.check_interactions(
            report
        )

        self.collect_observations(
            report
        )

        report.all_passed = (
            len(
                report.runtime_errors
            )
            == 0
            and all(
                check.passed
                for check in report.checks
            )
        )

        return report


# ----------------------------------------------------------------------
# Report printer
# ----------------------------------------------------------------------


def print_report(
    report: DiagnosticReport,
) -> None:

    print(
        "UFCPS — Level 3 System Diagnostic v1"
    )

    print(
        "=" * 76
    )

    print(
        f"all_passed: {report.all_passed}"
    )

    print(
        f"checks: {len(report.checks)}"
    )

    print(
        f"runtime_errors: "
        f"{len(report.runtime_errors)}"
    )

    print(
        "\nCHECKS"
    )

    print(
        "-" * 76
    )

    for check in report.checks:

        status = (
            "PASS"
            if check.passed
            else "FAIL"
        )

        if check.error is not None:

            print(
                f"{status:5} "
                f"{check.name} "
                f"[{check.error}]"
            )

        else:

            print(
                f"{status:5} "
                f"{check.name} "
                f"value={check.value!r}"
            )

    print(
        "\nOBSERVATIONS"
    )

    print(
        "-" * 76
    )

    for name, value in (
        report.observations.items()
    ):

        print(
            f"{name}: {value}"
        )

    if report.runtime_errors:

        print(
            "\nRUNTIME ERRORS"
        )

        print(
            "-" * 76
        )

        for error in (
            report.runtime_errors
        ):

            print(
                error
            )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> int:

    diagnostic = (
        Level3SystemDiagnostic()
    )

    report = diagnostic.run()

    print_report(
        report
    )

    return (
        0
        if report.all_passed
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
