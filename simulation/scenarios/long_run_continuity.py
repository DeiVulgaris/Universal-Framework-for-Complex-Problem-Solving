

The scenario executes a longer procedural chain and injects several local
interruptions at controlled points. Each interruption requires continuation
from preserved process state.

The scenario measures whether continuity remains stable as the number of
successive carrier changes grows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core import (
    CapabilityProfile,
    Carrier,
    Operation,
    ProceduralState,
    RuntimeConfig,
    UFCPSRuntime,
)


@dataclass(frozen=True)
class LongRunContinuityResult:
    """Serializable summary of the long-run continuity run."""

    process_id: str
    configured_steps: int
    completed_steps: int
    carrier_changes: int
    interruptions_injected: int
    interruptions_recovered: int
    state_references_preserved: int
    continuity_checks_passed: int
    invalid_transitions: int
    state_loss_detected: bool
    process_terminated: bool
    continuity_valid: bool
    metrics: dict[str, Any]
    event_log: list[dict[str, Any]]
    transition_log: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "process_id": self.process_id,
            "configured_steps": self.configured_steps,
            "completed_steps": self.completed_steps,
            "carrier_changes": self.carrier_changes,
            "interruptions_injected": self.interruptions_injected,
            "interruptions_recovered": self.interruptions_recovered,
            "state_references_preserved": (
                self.state_references_preserved
            ),
            "continuity_checks_passed": (
                self.continuity_checks_passed
            ),
            "invalid_transitions": self.invalid_transitions,
            "state_loss_detected": self.state_loss_detected,
            "process_terminated": self.process_terminated,
            "continuity_valid": self.continuity_valid,
            "metrics": dict(self.metrics),
            "event_log": list(self.event_log),
            "transition_log": list(self.transition_log),
        }


def _make_carrier(
    carrier_id: str,
    carrier_type: str,
) -> Carrier:
    """Create a deterministic compatible carrier."""
    return Carrier(
        carrier_id=carrier_id,
        carrier_type=carrier_type,
        capabilities=CapabilityProfile(
            name=carrier_type,
            capabilities=frozenset(
                {
                    "general_reasoning",
                    "continuation",
                }
            ),
        ),
    )


def _step_executor(
    *,
    complete: bool,
):
    """Create a deterministic executor for one procedural step.

    Intermediate steps that are about to be handed off remain
    continuation-capable. A terminal step may complete normally.
    """

    def execute(
        local_state: ProceduralState,
        local_carrier: Carrier,
    ):
        from ..core import ExecutionResult

        next_difference = (
            f"Continue procedural chain after step "
            f"{local_state.step_index}."
        )

        return ExecutionResult(
            completed=complete,
            current_state=(
                f"Processed deterministic long-run step "
                f"{local_state.step_index} by "
                f"{local_carrier.carrier_id}."
            ),
            local_result=(
                f"Step {local_state.step_index} processed successfully."
            ),
            difference=next_difference,
            next_operation=(
                Operation.DISS if not complete else Operation.UNFOLD
            ),
        )

    return execute


def run_long_run_continuity(
    *,
    process_id: str = "long-run-continuity-simulation",
    configured_steps: int = 12,
) -> LongRunContinuityResult:
    """Run the long-run continuity scenario."""
    if configured_steps < 4:
        raise ValueError(
            "configured_steps must be at least 4."
        )

    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=(configured_steps * 3) + 10,
            strict_state_sync=True,
        )
    )

    carriers = [
        _make_carrier(
            f"carrier_{index:02d}",
            "continuity_reasoner",
        )
        for index in range(configured_steps)
    ]

    for carrier in carriers:
        runtime.add_carrier(carrier)

    root = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Execute a long procedural chain while preserving continuation "
            "across controlled carrier interruptions."
        ),
        current_state="Long-run root state.",
        unresolved_difference=(
            "Continue deterministic chain."
        ),
        next_required_operation=Operation.DIFF,
        constraints=[
            "Every successor step must advance exactly one procedural index.",
            "Continuation-relevant state must survive every handoff.",
            "Local interruption must not terminate the process.",
        ],
        continuation_relevant={
            "long_run": True,
            "history": [],
        },
    )

    runtime.add_state(root)
    runtime.activate("carrier_00", "P0")

    completed_steps = 0
    carrier_changes = 0
    interruptions_injected = 0
    interruptions_recovered = 0
    state_references_preserved = 0
    continuity_checks_passed = 0
    invalid_transitions = 0
    state_loss_detected = False

    current_unit = "P0"
    current_carrier = "carrier_00"

    # Interruptions occur at deterministic points rather than randomly.
    interruption_points = {
        max(1, configured_steps // 3),
        max(2, (configured_steps * 2) // 3),
        configured_steps - 1,
    }

    for step in range(configured_steps):
        state = runtime.get_state(current_unit)
        carrier = runtime.get_carrier(current_carrier)

        if carrier.current_unit_id != current_unit:
            raise RuntimeError(
                f"Carrier {current_carrier!r} is not carrying "
                f"{current_unit!r}."
            )

        handoff_this_step = (
            step in interruption_points
            and step < configured_steps - 1
        )

        result = runtime.execute(
            current_unit,
            current_carrier,
            _step_executor(complete=not handoff_this_step),
        )

        if handoff_this_step:
            if result.completed:
                raise RuntimeError(
                    f"Step {step} must remain continuation-capable before handoff."
                )
        elif not result.completed:
            raise RuntimeError(
                f"Unexpected failure at step {step}."
            )

        completed_steps += 1

        state = runtime.get_state(current_unit)
        history = state.continuation_relevant.setdefault(
            "history",
            [],
        )

        if isinstance(history, list):
            history.append(
                {
                    "step_index": state.step_index,
                    "carrier_id": current_carrier,
                    "local_result": state.local_result,
                }
            )

        reference = runtime.preserve(current_unit)
        state_references_preserved += int(
            runtime.state_exists(reference)
        )

        # Explicit continuity check before every possible handoff.
        before_transitions = len(runtime.snapshot.transitions)

        if step in interruption_points and step < configured_steps - 1:
            interruptions_injected += 1

            available_destination = None
            for candidate in carriers:
                if (
                    candidate.carrier_id != current_carrier
                    and candidate.status.value
                    in {
                        "available",
                        "released",
                        "completed",
                    }
                ):
                    available_destination = candidate
                    break

            if available_destination is None:
                raise RuntimeError(
                    f"No destination carrier available at step {step}."
                )

            next_state = runtime.delegate(
                current_unit,
                current_carrier,
                available_destination.carrier_id,
                reason=(
                    f"Controlled interruption after long-run step {step}; "
                    "continue from preserved state."
                ),
                next_unit_id=f"P{step + 1}",
            )

            carrier_changes += 1
            interruptions_recovered += 1

            # Ensure inherited continuation context remains available.
            if not next_state.unresolved_difference:
                state_loss_detected = True

            next_state.continuation_relevant.setdefault(
                "history",
                list(
                    state.continuation_relevant.get(
                        "history",
                        [],
                    )
                ),
            )

            runtime.snapshot.store_state(next_state)

            current_unit = next_state.unit_id
            current_carrier = available_destination.carrier_id
        elif step < configured_steps - 1:
            # Sequential continuation without carrier replacement.
            next_carrier = current_carrier
            next_unit = ProceduralState(
                unit_id=f"P{step + 1}",
                step_index=step + 1,
                task=state.task,
                current_state=(
                    f"Successor state after step {step}."
                ),
                local_result="",
                unresolved_difference=state.unresolved_difference,
                next_required_operation=Operation.DIFF,
                constraints=list(state.constraints),
                boundary_conditions=list(state.boundary_conditions),
                continuation_relevant={
                    **state.continuation_relevant,
                    "history": list(
                        state.continuation_relevant.get(
                            "history",
                            [],
                        )
                    ),
                },
                parent_unit_id=current_unit,
            )

            runtime.snapshot.active_units[
                next_unit.unit_id
            ] = next_unit

            # Reactivate the same carrier for the local sequential case.
            runtime.get_carrier(next_carrier).activate(
                next_unit.unit_id
            )
            runtime.snapshot.store_state(next_unit)

            current_unit = next_unit.unit_id

        after_transitions = len(runtime.snapshot.transitions)

        new_transitions = runtime.snapshot.transitions[
            before_transitions:after_transitions
        ]

        for transition in new_transitions:
            if transition.validate_step_continuity():
                continuity_checks_passed += 1
            else:
                invalid_transitions += 1

    runtime.assert_continuity()

    # A final consistency pass checks the entire transition history.
    for transition in runtime.snapshot.transitions:
        if not transition.validate_step_continuity():
            invalid_transitions += 1

    continuity_valid = (
        completed_steps == configured_steps
        and interruptions_recovered == interruptions_injected
        and invalid_transitions == 0
        and state_loss_detected is False
        and not runtime.terminated
    )

    return LongRunContinuityResult(
        process_id=process_id,
        configured_steps=configured_steps,
        completed_steps=completed_steps,
        carrier_changes=carrier_changes,
        interruptions_injected=interruptions_injected,
        interruptions_recovered=interruptions_recovered,
        state_references_preserved=state_references_preserved,
        continuity_checks_passed=continuity_checks_passed,
        invalid_transitions=invalid_transitions,
        state_loss_detected=state_loss_detected,
        process_terminated=runtime.terminated,
        continuity_valid=continuity_valid,
        metrics=runtime.metrics(),
        event_log=runtime.event_log(),
        transition_log=runtime.transition_log(),
    )


def main() -> int:
    """Run the scenario and emit JSON."""
    import json

    result = run_long_run_continuity()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if result.completed_steps != result.configured_steps:
        return 1

    if result.interruptions_injected != result.interruptions_recovered:
        return 1

    if result.invalid_transitions != 0:
        return 1

    if result.state_loss_detected:
        return 1

    if result.process_terminated:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
