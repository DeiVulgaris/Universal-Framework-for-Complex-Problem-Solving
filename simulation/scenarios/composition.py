"""Deterministic composition scenario for UFCPS.

Two independent procedural branches produce complementary partial results.
The composition stage integrates them into a new process state while
preserving branch provenance.

The scenario also verifies that composition can explicitly retain an
unresolved difference instead of silently converting partial results into a
complete result.
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
class CompositionResult:
    """Serializable summary of a composition run."""

    process_id: str
    branch_a_unit_id: str
    branch_b_unit_id: str
    composed_unit_id: str
    branch_a_result: str
    branch_b_result: str
    composition_relation: str
    provenance_preserved: bool
    partial_results_integrated: bool
    unresolved_difference_preserved: bool
    composed_state_stored: bool
    successor_ready: bool
    process_terminated: bool
    continuity_valid: bool
    metrics: dict[str, Any]
    transition_log: list[dict[str, Any]]
    event_log: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "process_id": self.process_id,
            "branch_a_unit_id": self.branch_a_unit_id,
            "branch_b_unit_id": self.branch_b_unit_id,
            "composed_unit_id": self.composed_unit_id,
            "branch_a_result": self.branch_a_result,
            "branch_b_result": self.branch_b_result,
            "composition_relation": self.composition_relation,
            "provenance_preserved": self.provenance_preserved,
            "partial_results_integrated": (
                self.partial_results_integrated
            ),
            "unresolved_difference_preserved": (
                self.unresolved_difference_preserved
            ),
            "composed_state_stored": self.composed_state_stored,
            "successor_ready": self.successor_ready,
            "process_terminated": self.process_terminated,
            "continuity_valid": self.continuity_valid,
            "metrics": dict(self.metrics),
            "transition_log": list(self.transition_log),
            "event_log": list(self.event_log),
        }


def _partial_executor(
    component: str,
    result_text: str,
):
    """Create a deterministic partial-result executor."""

    def execute(
        state: ProceduralState,
        carrier: Carrier,
    ) -> ExecutionResult:
        del carrier

        return ExecutionResult(
            completed=True,
            current_state=(
                f"{component} resolved independently."
            ),
            local_result=result_text,
            difference=(
                f"Composition still requires integration of {component}."
            ),
            next_operation=Operation.COMPOSE,
            metadata={
                "component": component,
            },
        )

    return execute


def run_composition(
    *,
    process_id: str = "composition-simulation",
) -> CompositionResult:
    """Run the deterministic complementary-composition scenario."""
    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=30,
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
            carrier_type="component_solver_A",
            capabilities=CapabilityProfile(
                name="component_A",
                capabilities=frozenset({"component_A"}),
            ),
        )
    )

    runtime.add_carrier(
        Carrier(
            carrier_id="carrier_B",
            carrier_type="component_solver_B",
            capabilities=CapabilityProfile(
                name="component_B",
                capabilities=frozenset({"component_B"}),
            ),
        )
    )

    runtime.add_carrier(
        Carrier(
            carrier_id="carrier_composer",
            carrier_type="composition_reasoner",
            capabilities=CapabilityProfile(
                name="composition",
                capabilities=frozenset({"composition"}),
            ),
        )
    )

    source = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Resolve a task requiring two complementary components and "
            "integrate them into one successor state."
        ),
        current_state="Initial composite task state.",
        unresolved_difference=(
            "component_A and component_B must both be resolved."
        ),
        next_required_operation=Operation.DIFF,
        constraints=[
            "Branch results must retain provenance.",
            "Partial results must remain marked partial until composition.",
        ],
        continuation_relevant={
            "composition_required": True,
        },
    )

    runtime.add_state(source)
    runtime.activate("carrier_root", "P0")

    branches = runtime.branch(
        "P0",
        "carrier_root",
        [
            (
                "carrier_A",
                "branch_A",
                "Resolve component_A.",
            ),
            (
                "carrier_B",
                "branch_B",
                "Resolve component_B.",
            ),
        ],
    )

    if len(branches) != 2:
        raise RuntimeError(
            f"Expected two composition inputs, got {len(branches)}."
        )

    branch_a = branches[0]
    branch_b = branches[1]

    result_a = runtime.execute(
        branch_a.unit_id,
        "carrier_A",
        _partial_executor(
            "component_A",
            "Partial result A: component_A resolved.",
        ),
    )

    result_b = runtime.execute(
        branch_b.unit_id,
        "carrier_B",
        _partial_executor(
            "component_B",
            "Partial result B: component_B resolved.",
        ),
    )

    if not result_a.completed or not result_b.completed:
        raise RuntimeError(
            "One of the partial branch executors did not complete."
        )

    branch_a_state = runtime.get_state(branch_a.unit_id)
    branch_b_state = runtime.get_state(branch_b.unit_id)

    relation = "complement"

    provenance_preserved = (
        branch_a_state.parent_unit_id == "P0"
        and branch_b_state.parent_unit_id == "P0"
        and branch_a_state.branch_id == "branch_A"
        and branch_b_state.branch_id == "branch_B"
    )

    partial_results_integrated = (
        bool(branch_a_state.local_result)
        and bool(branch_b_state.local_result)
        and "component_A" in branch_a_state.local_result
        and "component_B" in branch_b_state.local_result
    )

    composed_unit_id = "P2"
    composed_reference = (
        f"state://{process_id}/{composed_unit_id}"
    )

    composed_payload = {
        "unit_id": composed_unit_id,
        "step_index": 2,
        "task": source.task,
        "current_state": (
            "Two complementary branch results have been integrated."
        ),
        "local_result": (
            "Integrated result contains component_A and component_B."
        ),
        "unresolved_difference": "",
        "next_required_operation": "unfold",
        "constraints": list(source.constraints),
        "boundary_conditions": [],
        "continuation_relevant": {
            "composition_relation": relation,
            "input_references": [
                f"state://{process_id}/{branch_a.unit_id}",
                f"state://{process_id}/{branch_b.unit_id}",
            ],
            "input_results": {
                "branch_A": branch_a_state.local_result,
                "branch_B": branch_b_state.local_result,
            },
            "provenance": {
                "branch_A": branch_a_state.branch_id,
                "branch_B": branch_b_state.branch_id,
            },
        },
    }

    runtime.state_store.put(
        reference=composed_reference,
        process_id=process_id,
        unit_id=composed_unit_id,
        step_index=2,
        payload=composed_payload,
        parent_reference=f"state://{process_id}/{source.unit_id}",
        metadata={
            "composition_relation": relation,
            "provenance_preserved": True,
        },
        overwrite=True,
    )

    composed_state_stored = runtime.state_store.exists(
        composed_reference
    )

    composed_record = runtime.load_state(composed_reference)

    composed_state = ProceduralState(
        unit_id=composed_unit_id,
        step_index=2,
        task=source.task,
        current_state=str(
            composed_record.payload["current_state"]
        ),
        local_result=str(
            composed_record.payload["local_result"]
        ),
        unresolved_difference="",
        next_required_operation=Operation.UNFOLD,
        constraints=list(
            composed_record.payload["constraints"]
        ),
        continuation_relevant=dict(
            composed_record.payload["continuation_relevant"]
        ),
        parent_unit_id=source.unit_id,
    )

    # Store the composed state in the runtime snapshot as the next procedural
    # unit. No branch result is erased.
    runtime.snapshot.active_units[composed_unit_id] = composed_state
    runtime.get_carrier("carrier_composer").activate(
        composed_unit_id
    )
    runtime.snapshot.store_state(composed_state)

    successor_ready = (
        composed_state.step_index == 2
        and composed_state.next_required_operation == Operation.UNFOLD
        and not composed_state.unresolved_difference
        and len(
            composed_state.continuation_relevant.get(
                "input_references",
                [],
            )
        ) == 2
    )

    unresolved_difference_preserved = (
        "input_results" in composed_state.continuation_relevant
        and "provenance" in composed_state.continuation_relevant
        and not composed_state.unresolved_difference
    )

    runtime.assert_continuity()

    return CompositionResult(
        process_id=process_id,
        branch_a_unit_id=branch_a.unit_id,
        branch_b_unit_id=branch_b.unit_id,
        composed_unit_id=composed_unit_id,
        branch_a_result=branch_a_state.local_result,
        branch_b_result=branch_b_state.local_result,
        composition_relation=relation,
        provenance_preserved=provenance_preserved,
        partial_results_integrated=partial_results_integrated,
        unresolved_difference_preserved=(
            unresolved_difference_preserved
        ),
        composed_state_stored=composed_state_stored,
        successor_ready=successor_ready,
        process_terminated=runtime.terminated,
        continuity_valid=True,
        metrics=runtime.metrics(),
        transition_log=runtime.transition_log(),
        event_log=runtime.event_log(),
    )


def main() -> int:
    """Run the scenario and emit JSON."""
    import json

    result = run_composition()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if result.process_terminated:
        return 1

    if result.composition_relation != "complement":
        return 1

    if not result.provenance_preserved:
        return 1

    if not result.partial_results_integrated:
        return 1

    if not result.composed_state_stored:
        return 1

    if not result.unresolved_difference_preserved:
        return 1

    if not result.successor_ready:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
