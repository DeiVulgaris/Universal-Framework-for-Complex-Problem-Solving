

The source procedural unit begins on a general carrier. A capability
requirement emerges that is outside the source carrier's profile. The
continuation state is preserved and the successor unit is assigned to a
specialized carrier.

The scenario isolates the distinction between:

    carrier capability
    and
    process continuity
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
from ..policies import CapabilityMatchedPolicy


@dataclass(frozen=True)
class CarrierSubstitutionResult:
    """Serializable summary of a carrier-substitution run."""

    process_id: str
    source_carrier_id: str
    destination_carrier_id: str
    source_carrier_type: str
    destination_carrier_type: str
    source_unit_id: str
    successor_unit_id: str
    required_capability: str
    capability_was_unavailable_locally: bool
    continuation_preserved: bool
    carrier_type_changed: bool
    successor_completed: bool
    process_terminated: bool
    continuity_valid: bool
    metrics: dict[str, Any]
    transition_log: list[dict[str, Any]]
    event_log: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "process_id": self.process_id,
            "source_carrier_id": self.source_carrier_id,
            "destination_carrier_id": self.destination_carrier_id,
            "source_carrier_type": self.source_carrier_type,
            "destination_carrier_type": self.destination_carrier_type,
            "source_unit_id": self.source_unit_id,
            "successor_unit_id": self.successor_unit_id,
            "required_capability": self.required_capability,
            "capability_was_unavailable_locally": (
                self.capability_was_unavailable_locally
            ),
            "continuation_preserved": self.continuation_preserved,
            "carrier_type_changed": self.carrier_type_changed,
            "successor_completed": self.successor_completed,
            "process_terminated": self.process_terminated,
            "continuity_valid": self.continuity_valid,
            "metrics": dict(self.metrics),
            "transition_log": list(self.transition_log),
            "event_log": list(self.event_log),
        }


def _source_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Stop at a capability boundary on the source carrier."""
    del carrier

    required_capability = (
        state.metadata.get("required_capability")
        or "specialized_analysis"
    )

    difference = (
        f"The next operation requires {required_capability}."
    )

    return ExecutionResult(
        completed=False,
        current_state=(
            "General carrier completed the portion available within its "
            "capability profile."
        ),
        local_result=(
            "Local execution is valid but insufficient for the next stage."
        ),
        difference=difference,
        next_operation=Operation.DISS,
        deadlock_state={
            "state": (
                "General carrier reached a capability boundary."
            ),
            "constraint": (
                f"Required capability {required_capability} is unavailable "
                "on the current carrier."
            ),
            "boundary": "Source carrier capability profile.",
            "unresolved": difference,
        },
    )


def _specialist_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Complete the successor step on the specialized carrier."""
    required_capability = (
        state.metadata.get("required_capability")
        or "specialized_analysis"
    )

    if carrier.capabilities is None:
        return ExecutionResult(
            completed=False,
            current_state=state.current_state,
            local_result="Destination carrier has no capability profile.",
            difference=(
                f"Missing capability {required_capability}."
            ),
            next_operation=Operation.DIFF,
            deadlock_state={
                "state": state.current_state,
                "constraint": (
                    f"Required capability {required_capability} "
                    "is not declared."
                ),
                "boundary": "Destination carrier capability profile.",
                "unresolved": (
                    f"Missing capability {required_capability}."
                ),
            },
        )

    if not carrier.capabilities.supports(required_capability):
        return ExecutionResult(
            completed=False,
            current_state=state.current_state,
            local_result=(
                "Destination carrier does not satisfy the required "
                "specialization."
            ),
            difference=(
                f"Missing capability {required_capability}."
            ),
            next_operation=Operation.DIFF,
            deadlock_state={
                "state": state.current_state,
                "constraint": (
                    f"Required capability {required_capability} "
                    "is unavailable."
                ),
                "boundary": "Destination carrier capability profile.",
                "unresolved": (
                    f"Missing capability {required_capability}."
                ),
            },
        )

    return ExecutionResult(
        completed=True,
        current_state=(
            "Specialized carrier completed the capability-dependent "
            "successor step using preserved process state."
        ),
        local_result=(
            "The specialized operation was completed without reconstructing "
            "the previous carrier session."
        ),
        next_operation=None,
    )


def run_carrier_substitution(
    *,
    process_id: str = "carrier-substitution-simulation",
) -> CarrierSubstitutionResult:
    """Run the deterministic carrier-substitution scenario."""
    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=20,
            strict_state_sync=True,
        )
    )

    source_carrier = Carrier(
        carrier_id="carrier_general",
        carrier_type="general_reasoner",
        capabilities=CapabilityProfile(
            name="general",
            capabilities=frozenset(
                {
                    "general_reasoning",
                    "decomposition",
                }
            ),
        ),
    )

    specialist_carrier = Carrier(
        carrier_id="carrier_specialist",
        carrier_type="specialized_reasoner",
        capabilities=CapabilityProfile(
            name="specialist",
            capabilities=frozenset(
                {
                    "general_reasoning",
                    "decomposition",
                    "specialized_analysis",
                }
            ),
        ),
    )

    fallback_carrier = Carrier(
        carrier_id="carrier_fallback",
        carrier_type="general_reasoner",
        capabilities=CapabilityProfile(
            name="fallback",
            capabilities=frozenset(
                {
                    "general_reasoning",
                }
            ),
        ),
    )

    runtime.add_carrier(source_carrier)
    runtime.add_carrier(specialist_carrier)
    runtime.add_carrier(fallback_carrier)

    state = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Execute a task whose initial stage is general reasoning and "
            "whose successor stage requires specialized analysis."
        ),
        current_state="Initial process state.",
        constraints=[
            "The required capability must be explicit.",
            "The successor must inherit continuation-relevant state.",
        ],
        boundary_conditions=[
            "The source carrier intentionally lacks specialized_analysis."
        ],
        continuation_relevant={
            "required_capability": "specialized_analysis",
            "source_stage": "general_reasoning",
        },
        metadata={
            "required_capabilities": [
                "specialized_analysis",
            ],
            "required_capability": "specialized_analysis",
        },
        next_required_operation=Operation.DIFF,
    )

    source_reference = runtime.add_state(state)
    runtime.activate("carrier_general", "P0")

    source_result = runtime.execute(
        "P0",
        "carrier_general",
        _source_executor,
    )

    if source_result.completed:
        raise RuntimeError(
            "Source carrier unexpectedly completed a specialized step."
        )

    source_state = runtime.get_state("P0")
    capability_was_unavailable_locally = (
        source_state.deadlock is not None
        and "specialized_analysis" in source_state.deadlock.constraint
    )

    # The policy operates independently of the continuity engine.
    policy = CapabilityMatchedPolicy()
    selected = policy.select(
        source_state,
        runtime.snapshot.carriers.values(),
        required_capability="specialized_analysis",
    )

    if selected.carrier_id != "carrier_specialist":
        raise RuntimeError(
            "CapabilityMatchedPolicy did not select the specialized carrier."
        )

    runtime.preserve("P0")

    successor = runtime.delegate(
        "P0",
        "carrier_general",
        selected.carrier_id,
        reason=(
            "The source carrier lacks the capability required for the "
            "successor step. Preserve process state and substitute a "
            "compatible specialized carrier."
        ),
        next_unit_id="P1",
    )

    successor.continuation_relevant["source_state_reference"] = source_reference
    successor.metadata["required_capability"] = "specialized_analysis"

    # Make the requirement available to the successor executor through state.
    runtime.snapshot.store_state(successor)

    successor_result = runtime.execute(
        "P1",
        selected.carrier_id,
        _specialist_executor,
    )

    transition = runtime.snapshot.transitions[-1]

    runtime.assert_continuity()

    continuation_preserved = (
        transition.continuation is not None
        and transition.continuation.has_required_information()
        and runtime.state_exists(
            transition.continuation.state_reference
        )
    )

    carrier_type_changed = (
        source_carrier.carrier_type
        != selected.carrier_type
    )

    return CarrierSubstitutionResult(
        process_id=process_id,
        source_carrier_id="carrier_general",
        destination_carrier_id=selected.carrier_id,
        source_carrier_type=source_carrier.carrier_type,
        destination_carrier_type=selected.carrier_type,
        source_unit_id="P0",
        successor_unit_id=successor.unit_id,
        required_capability="specialized_analysis",
        capability_was_unavailable_locally=(
            capability_was_unavailable_locally
        ),
        continuation_preserved=continuation_preserved,
        carrier_type_changed=carrier_type_changed,
        successor_completed=bool(successor_result.completed),
        process_terminated=runtime.terminated,
        continuity_valid=True,
        metrics=runtime.metrics(),
        transition_log=runtime.transition_log(),
        event_log=runtime.event_log(),
    )


def main() -> int:
    """Run the scenario and emit JSON."""
    import json

    result = run_carrier_substitution()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if result.process_terminated:
        return 1

    if not result.capability_was_unavailable_locally:
        return 1

    if not result.continuation_preserved:
        return 1

    if not result.carrier_type_changed:
        return 1

    if not result.successor_completed:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
