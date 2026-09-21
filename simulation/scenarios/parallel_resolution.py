

One predecessor procedural unit is unfolded into two independent branches.
Each branch is executed by a different carrier and resolves a different
component of the original structural difference.

This scenario tests branch identity and state isolation before composition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core import (
    CapabilityProfile,
    Carrier,
    ExecutionResult,
    Operation,
    ProceduralState,
    RuntimeConfig,
    UFCPSRuntime,
)


@dataclass(frozen=True)
class ParallelScenarioResult:
    """Serializable summary of a parallel-resolution run."""

    process_id: str
    source_unit_id: str
    branch_ids: tuple[str, ...]
    branch_unit_ids: tuple[str, ...]
    branch_carriers: tuple[str, ...]
    branch_count: int
    branch_state_isolated: bool
    provenance_preserved: bool
    composition_inputs_ready: bool
    continuity_valid: bool
    metrics: dict[str, Any]
    transition_log: list[dict[str, Any]]
    event_log: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "process_id": self.process_id,
            "source_unit_id": self.source_unit_id,
            "branch_ids": list(self.branch_ids),
            "branch_unit_ids": list(self.branch_unit_ids),
            "branch_carriers": list(self.branch_carriers),
            "branch_count": self.branch_count,
            "branch_state_isolated": self.branch_state_isolated,
            "provenance_preserved": self.provenance_preserved,
            "composition_inputs_ready": self.composition_inputs_ready,
            "continuity_valid": self.continuity_valid,
            "metrics": dict(self.metrics),
            "transition_log": list(self.transition_log),
            "event_log": list(self.event_log),
        }


def _branch_executor(
    branch_name: str,
    resolved_difference: str,
):
    """Build a deterministic executor for one branch."""

    def execute(
        state: ProceduralState,
        carrier: Carrier,
    ) -> ExecutionResult:
        del carrier

        inherited = state.unresolved_difference

        return ExecutionResult(
            completed=True,
            current_state=(
                f"{branch_name}: resolved {resolved_difference}; "
                f"inherited difference was {inherited}."
            ),
            local_result=(
                f"Branch {branch_name} produced a partial resolution for "
                f"{resolved_difference}."
            ),
            difference=resolved_difference,
            next_operation=Operation.COMPOSE,
        )

    return execute


def run_parallel_resolution(
    *,
    process_id: str = "parallel-resolution-simulation",
) -> ParallelScenarioResult:
    """Run the deterministic parallel branch scenario."""
    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=20,
            strict_state_sync=True,
        )
    )

    runtime.add_carrier(
        Carrier(
            carrier_id="carrier_root",
            carrier_type="general_reasoner",
            capabilities=CapabilityProfile(
                name="general",
                capabilities=frozenset({"decomposition"}),
            ),
        )
    )

    runtime.add_carrier(
        Carrier(
            carrier_id="carrier_A",
            carrier_type="constraint_solver",
            capabilities=CapabilityProfile(
                name="constraint",
                capabilities=frozenset({"constraint_A"}),
            ),
        )
    )

    runtime.add_carrier(
        Carrier(
            carrier_id="carrier_B",
            carrier_type="model_solver",
            capabilities=CapabilityProfile(
                name="model",
                capabilities=frozenset({"constraint_B"}),
            ),
        )
    )

    source = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Resolve a coupled task containing two separable structural "
            "differences."
        ),
        current_state="Initial coupled state.",
        unresolved_difference=(
            "The task contains independent components difference_A and "
            "difference_B."
        ),
        next_required_operation=Operation.DIFF,
        constraints=[
            "Branch A must remain independent of branch B.",
            "Each branch receives the source continuation state.",
        ],
        continuation_relevant={
            "branchable": True,
            "source_difference": (
                "The task contains independent components difference_A "
                "and difference_B."
            ),
        },
        metadata={
            "required_capabilities": [
                "decomposition",
            ],
        },
    )

    runtime.add_state(source)
    runtime.activate("carrier_root", "P0")

    successors = runtime.branch(
        "P0",
        "carrier_root",
        [
            (
                "carrier_A",
                "branch_A",
                "difference_A",
            ),
            (
                "carrier_B",
                "branch_B",
                "difference_B",
            ),
        ],
    )

    if len(successors) != 2:
        raise RuntimeError(
            f"Expected exactly 2 branches, got {len(successors)}."
        )

    runtime.execute(
        successors[0].unit_id,
        "carrier_A",
        _branch_executor("branch_A", "difference_A"),
    )

    runtime.execute(
        successors[1].unit_id,
        "carrier_B",
        _branch_executor("branch_B", "difference_B"),
    )

    branch_a = runtime.get_state(successors[0].unit_id)
    branch_b = runtime.get_state(successors[1].unit_id)

    branch_state_isolated = (
        branch_a.branch_id != branch_b.branch_id
        and branch_a.unit_id != branch_b.unit_id
        and branch_a.unresolved_difference == "difference_A"
        and branch_b.unresolved_difference == "difference_B"
    )

    provenance_preserved = (
        branch_a.parent_unit_id == "P0"
        and branch_b.parent_unit_id == "P0"
    )

    composition_inputs_ready = (
        branch_a.local_result != ""
        and branch_b.local_result != ""
        and bool(branch_a.branch_id)
        and bool(branch_b.branch_id)
    )

    runtime.assert_continuity()

    transition_log = runtime.transition_log()

    branch_transitions = [
        transition
        for transition in transition_log
        if transition["transition_type"] == "branch"
    ]

    return ParallelScenarioResult(
        process_id=process_id,
        source_unit_id="P0",
        branch_ids=tuple(
            successor.branch_id or ""
            for successor in successors
        ),
        branch_unit_ids=tuple(
            successor.unit_id
            for successor in successors
        ),
        branch_carriers=(
            "carrier_A",
            "carrier_B",
        ),
        branch_count=len(successors),
        branch_state_isolated=branch_state_isolated,
        provenance_preserved=provenance_preserved,
        composition_inputs_ready=(
            composition_inputs_ready
            and len(branch_transitions) == 2
        ),
        continuity_valid=True,
        metrics=runtime.metrics(),
        transition_log=transition_log,
        event_log=runtime.event_log(),
    )


def main() -> int:
    """Run the scenario and print a compact JSON result."""
    import json

    result = run_parallel_resolution()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if result.branch_count != 2:
        return 1

    if not result.branch_state_isolated:
        return 1

    if not result.provenance_preserved:
        return 1

    if not result.composition_inputs_ready:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
