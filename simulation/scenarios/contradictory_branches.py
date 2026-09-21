"""Deterministic contradictory-branches scenario for UFCPS.

Two branches independently produce incompatible results:

    Result_A = X
    Result_B = not X

The scenario verifies that the contradiction remains explicit and can become
the unresolved difference for a subsequent procedural unit.
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
class ContradictionResult:
    """Serializable summary of a contradictory-branches run."""

    process_id: str
    branch_a_unit_id: str
    branch_b_unit_id: str
    branch_a_result: str
    branch_b_result: str
    contradiction_detected: bool
    contradiction_preserved: bool
    provenance_preserved: bool
    unresolved_difference_created: bool
    successor_question_ready: bool
    process_terminated: bool
    continuity_valid: bool
    metrics: dict[str, Any]
    event_log: list[dict[str, Any]]
    transition_log: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "process_id": self.process_id,
            "branch_a_unit_id": self.branch_a_unit_id,
            "branch_b_unit_id": self.branch_b_unit_id,
            "branch_a_result": self.branch_a_result,
            "branch_b_result": self.branch_b_result,
            "contradiction_detected": self.contradiction_detected,
            "contradiction_preserved": self.contradiction_preserved,
            "provenance_preserved": self.provenance_preserved,
            "unresolved_difference_created": (
                self.unresolved_difference_created
            ),
            "successor_question_ready": self.successor_question_ready,
            "process_terminated": self.process_terminated,
            "continuity_valid": self.continuity_valid,
            "metrics": dict(self.metrics),
            "event_log": list(self.event_log),
            "transition_log": list(self.transition_log),
        }


def _result_executor(
    result_text: str,
):
    """Create an executor that produces one fixed branch result."""

    def execute(
        state: ProceduralState,
        carrier: Carrier,
    ) -> ExecutionResult:
        del carrier

        return ExecutionResult(
            completed=True,
            current_state=(
                f"Independent branch evaluated the proposition and produced "
                f"result {result_text}."
            ),
            local_result=result_text,
            difference=state.unresolved_difference,
            next_operation=Operation.COMPOSE,
        )

    return execute


def run_contradictory_branches(
    *,
    process_id: str = "contradictory-branches-simulation",
) -> ContradictionResult:
    """Run the deterministic contradictory-branches scenario."""
    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=20,
            strict_state_sync=True,
        )
    )

    for carrier_id, carrier_type, capability in (
        (
            "carrier_root",
            "general_reasoner",
            "decomposition",
        ),
        (
            "carrier_A",
            "branch_reasoner_A",
            "hypothesis_A",
        ),
        (
            "carrier_B",
            "branch_reasoner_B",
            "hypothesis_B",
        ),
    ):
        runtime.add_carrier(
            Carrier(
                carrier_id=carrier_id,
                carrier_type=carrier_type,
                capabilities=CapabilityProfile(
                    name=carrier_type,
                    capabilities=frozenset(
                        {
                            capability,
                            "general_reasoning",
                        }
                    ),
                ),
            )
        )

    source = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Evaluate proposition X through two independent procedural paths."
        ),
        current_state="Proposition X is unresolved.",
        unresolved_difference=(
            "Independent paths must determine whether proposition X holds."
        ),
        next_required_operation=Operation.DIFF,
        constraints=[
            "Branches must remain independent.",
            "Contradictory results must not be silently normalized.",
        ],
        continuation_relevant={
            "proposition": "X",
            "contradiction_sensitive": True,
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
                "Evaluate proposition X under method A.",
            ),
            (
                "carrier_B",
                "branch_B",
                "Evaluate proposition X under method B.",
            ),
        ],
    )

    if len(successors) != 2:
        raise RuntimeError(
            f"Expected two contradictory branches, got {len(successors)}."
        )

    runtime.execute(
        successors[0].unit_id,
        "carrier_A",
        _result_executor("X"),
    )

    runtime.execute(
        successors[1].unit_id,
        "carrier_B",
        _result_executor("not X"),
    )

    branch_a = runtime.get_state(successors[0].unit_id)
    branch_b = runtime.get_state(successors[1].unit_id)

    contradiction_detected = (
        branch_a.local_result.strip() == "X"
        and branch_b.local_result.strip() == "not X"
        and branch_a.local_result != branch_b.local_result
    )

    provenance_preserved = (
        branch_a.parent_unit_id == "P0"
        and branch_b.parent_unit_id == "P0"
        and branch_a.branch_id == "branch_A"
        and branch_b.branch_id == "branch_B"
    )

    unresolved_difference = (
        "Contradiction between independent evaluations of proposition X."
    )

    # Composition is represented here as a new process-level state in the
    # shared environment. The contradiction itself is preserved rather than
    # normalized away.
    contradiction_reference = (
        f"state://{process_id}/P2-contradiction"
    )

    contradiction_payload = {
        "unit_id": "P2-contradiction",
        "step_index": 2,
        "task": source.task,
        "current_state": (
            "Independent branches produced contradictory results."
        ),
        "local_result": (
            "Contradiction preserved as an explicit process state."
        ),
        "unresolved_difference": unresolved_difference,
        "next_required_operation": Operation.DIFF.value,
        "constraints": list(source.constraints),
        "boundary_conditions": [],
        "continuation_relevant": {
            "branch_A_result": branch_a.local_result,
            "branch_B_result": branch_b.local_result,
            "branch_A_reference": (
                f"state://{process_id}/{branch_a.unit_id}"
            ),
            "branch_B_reference": (
                f"state://{process_id}/{branch_b.unit_id}"
            ),
            "contradiction": True,
        },
    }

    runtime.state_store.put(
        reference=contradiction_reference,
        process_id=process_id,
        unit_id="P2-contradiction",
        step_index=2,
        payload=contradiction_payload,
        parent_reference=f"state://{process_id}/P0",
        metadata={
            "composition_relation": "contradiction",
            "provenance_preserved": True,
        },
        overwrite=True,
    )

    contradiction_preserved = (
        runtime.state_store.exists(contradiction_reference)
        and runtime.state_store.get(
            contradiction_reference
        ).payload["continuation_relevant"]["branch_A_result"]
        == "X"
        and runtime.state_store.get(
            contradiction_reference
        ).payload["continuation_relevant"]["branch_B_result"]
        == "not X"
    )

    successor_question = (
        "Which condition can distinguish the conflicting evaluations of "
        "proposition X?"
    )

    runtime.snapshot.record_event(
        event_type=runtime.snapshot.events[-1].event_type
        if False
        else __import__(
            "simulation.core.models",
            fromlist=["EventType"],
        ).EventType.CONTRADICTION_DETECTED,
        unit_id="P2-contradiction",
        details={
            "branch_A": branch_a.local_result,
            "branch_B": branch_b.local_result,
            "unresolved_difference": unresolved_difference,
            "next_question": successor_question,
        },
    )

    runtime.assert_continuity()

    return ContradictionResult(
        process_id=process_id,
        branch_a_unit_id=branch_a.unit_id,
        branch_b_unit_id=branch_b.unit_id,
        branch_a_result=branch_a.local_result,
        branch_b_result=branch_b.local_result,
        contradiction_detected=contradiction_detected,
        contradiction_preserved=contradiction_preserved,
        provenance_preserved=provenance_preserved,
        unresolved_difference_created=(
            bool(unresolved_difference)
            and contradiction_preserved
        ),
        successor_question_ready=bool(successor_question),
        process_terminated=runtime.terminated,
        continuity_valid=True,
        metrics=runtime.metrics(),
        event_log=runtime.event_log(),
        transition_log=runtime.transition_log(),
    )


def main() -> int:
    """Run the scenario and emit JSON."""
    import json

    result = run_contradictory_branches()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if result.process_terminated:
        return 1

    if not result.contradiction_detected:
        return 1

    if not result.contradiction_preserved:
        return 1

    if not result.provenance_preserved:
        return 1

    if not result.unresolved_difference_created:
        return 1

    if not result.successor_question_ready:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
