"""Deterministic repeated-carrier-replacement scenario for UFCPS.

The same distributed process is carried successively by several different
agents. Controlled replacement is performed at multiple procedural steps.

The scenario measures whether continuation-relevant state survives repeated
carrier substitution rather than only a single handoff.
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
class ReplacementRecord:
    """One carrier-replacement observation."""

    source_carrier_id: str
    destination_carrier_id: str
    source_unit_id: str
    destination_unit_id: str
    continuation_state_available: bool
    unresolved_difference_preserved: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible record."""
        return {
            "source_carrier_id": self.source_carrier_id,
            "destination_carrier_id": self.destination_carrier_id,
            "source_unit_id": self.source_unit_id,
            "destination_unit_id": self.destination_unit_id,
            "continuation_state_available": (
                self.continuation_state_available
            ),
            "unresolved_difference_preserved": (
                self.unresolved_difference_preserved
            ),
        }


@dataclass(frozen=True)
class RepeatedCarrierReplacementResult:
    """Serializable summary of repeated carrier replacement."""

    process_id: str
    configured_replacements: int
    successful_replacements: int
    completed_steps: int
    state_references_preserved: int
    replacement_records: tuple[ReplacementRecord, ...]
    state_loss_detected: bool
    invalid_transitions: int
    process_terminated: bool
    continuity_valid: bool
    metrics: dict[str, Any]
    event_log: list[dict[str, Any]]
    transition_log: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible benchmark result."""
        return {
            "process_id": self.process_id,
            "configured_replacements": self.configured_replacements,
            "successful_replacements": self.successful_replacements,
            "completed_steps": self.completed_steps,
            "state_references_preserved": (
                self.state_references_preserved
            ),
            "replacement_records": [
                record.to_dict()
                for record in self.replacement_records
            ],
            "state_loss_detected": self.state_loss_detected,
            "invalid_transitions": self.invalid_transitions,
            "process_terminated": self.process_terminated,
            "continuity_valid": self.continuity_valid,
            "metrics": dict(self.metrics),
            "event_log": list(self.event_log),
            "transition_log": list(self.transition_log),
        }


def _stage_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Complete a deterministic local stage."""
    return ExecutionResult(
        completed=True,
        current_state=(
            f"Step {state.step_index} completed by "
            f"{carrier.carrier_id}."
        ),
        local_result=(
            f"Local result from step {state.step_index}."
        ),
        difference=(
            f"Continue the process after procedural step "
            f"{state.step_index}."
        ),
        next_operation=Operation.DISS,
    )


def _make_carrier(index: int) -> Carrier:
    """Create a deterministic compatible carrier."""
    return Carrier(
        carrier_id=f"carrier_{index:02d}",
        carrier_type="replacement_reasoner",
        capabilities=CapabilityProfile(
            name="replacement",
            capabilities=frozenset(
                {
                    "general_reasoning",
                    "continuation",
                }
            ),
        ),
    )


def run_repeated_carrier_replacement(
    *,
    process_id: str = "repeated-carrier-replacement-simulation",
    steps: int = 10,
) -> RepeatedCarrierReplacementResult:
    """Run the repeated-carrier-replacement benchmark."""
    if steps < 3:
        raise ValueError("steps must be at least 3.")

    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=(steps * 4) + 10,
            strict_state_sync=True,
        )
    )

    # One carrier per procedural stage makes carrier identity changes
    # deterministic and removes selection ambiguity from this benchmark.
    carriers = [
        _make_carrier(index)
        for index in range(steps)
    ]

    for carrier in carriers:
        runtime.add_carrier(carrier)

    current = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Complete a multi-stage procedural process while replacing "
            "the carrier after each controlled handoff."
        ),
        current_state="Repeated-replacement root state.",
        unresolved_difference=(
            "The process requires a successor procedural unit."
        ),
        next_required_operation=Operation.DIFF,
        constraints=[
            "Every carrier replacement must preserve continuation state.",
            "Every successor step must advance by exactly one.",
            "The process must survive repeated carrier changes.",
        ],
        continuation_relevant={
            "repeated_replacement": True,
            "replacement_history": [],
        },
    )

    runtime.add_state(current)
    runtime.activate(
        "carrier_00",
        current.unit_id,
    )

    replacement_records: list[ReplacementRecord] = []
    successful_replacements = 0
    state_references_preserved = 0
    state_loss_detected = False
    invalid_transitions = 0

    for step in range(steps):
        current_carrier_id = f"carrier_{step:02d}"
        current = runtime.get_state(current.unit_id)

        # Ensure the current carrier is the actual carrier of P_n.
        if runtime.get_carrier(
            current_carrier_id
        ).current_unit_id != current.unit_id:
            raise RuntimeError(
                f"Carrier {current_carrier_id!r} is not carrying "
                f"{current.unit_id!r} at step {step}."
            )

        runtime.execute(
            current.unit_id,
            current_carrier_id,
            _stage_executor,
        )

        current = runtime.get_state(current.unit_id)

        if step == steps - 1:
            runtime.preserve(current.unit_id)
            state_references_preserved += 1
            break

        source_reference = runtime.preserve(
            current.unit_id
        )
        state_references_preserved += int(
            runtime.state_exists(source_reference)
        )

        next_carrier_id = f"carrier_{step + 1:02d}"
        next_unit_id = f"P{step + 1}"

        successor = runtime.delegate(
            current.unit_id,
            current_carrier_id,
            next_carrier_id,
            reason=(
                f"Controlled repeated carrier replacement after step "
                f"{step}."
            ),
            next_unit_id=next_unit_id,
        )

        transition = runtime.snapshot.transitions[-1]

        continuation_available = (
            transition.continuation is not None
            and transition.continuation.has_required_information()
            and runtime.state_exists(
                transition.continuation.state_reference
            )
        )

        unresolved_preserved = bool(
            successor.unresolved_difference
        )

        replacement_records.append(
            ReplacementRecord(
                source_carrier_id=current_carrier_id,
                destination_carrier_id=next_carrier_id,
                source_unit_id=current.unit_id,
                destination_unit_id=successor.unit_id,
                continuation_state_available=(
                    continuation_available
                ),
                unresolved_difference_preserved=(
                    unresolved_preserved
                ),
            )
        )

        if not continuation_available or not unresolved_preserved:
            state_loss_detected = True
        else:
            successful_replacements += 1

        if not transition.validate_step_continuity():
            invalid_transitions += 1

        history = successor.continuation_relevant.setdefault(
            "replacement_history",
            [],
        )

        if isinstance(history, list):
            history.append(
                {
                    "from": current_carrier_id,
                    "to": next_carrier_id,
                    "source_step": step,
                    "destination_step": step + 1,
                }
            )

        runtime.snapshot.store_state(successor)

        current = successor

    runtime.assert_continuity()

    # Final full-history validation.
    invalid_transitions += sum(
        1
        for transition in runtime.snapshot.transitions
        if not transition.validate_step_continuity()
    )

    completed_steps = sum(
        1
        for event in runtime.snapshot.events
        if event.event_type.value == "STEP_COMPLETED"
    )

    continuity_valid = (
        completed_steps == steps
        and successful_replacements == steps - 1
        and len(replacement_records) == steps - 1
        and state_loss_detected is False
        and invalid_transitions == 0
        and not runtime.terminated
    )

    return RepeatedCarrierReplacementResult(
        process_id=process_id,
        configured_replacements=steps - 1,
        successful_replacements=successful_replacements,
        completed_steps=completed_steps,
        state_references_preserved=state_references_preserved,
        replacement_records=tuple(replacement_records),
        state_loss_detected=state_loss_detected,
        invalid_transitions=invalid_transitions,
        process_terminated=runtime.terminated,
        continuity_valid=continuity_valid,
        metrics=runtime.metrics(),
        event_log=runtime.event_log(),
        transition_log=runtime.transition_log(),
    )


def main() -> int:
    """Run the scenario and emit JSON."""
    import json

    result = run_repeated_carrier_replacement()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if result.successful_replacements != result.configured_replacements:
        return 1

    if result.completed_steps != result.configured_replacements + 1:
        return 1

    if result.state_loss_detected:
        return 1

    if result.invalid_transitions != 0:
        return 1

    if result.process_terminated:
        return 1

    for record in result.replacement_records:
        if not record.continuation_state_available:
            return 1
        if not record.unresolved_difference_preserved:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
