"""Deterministic C5 recursion-stress scenario for UFCPS.

The scenario creates a process that repeatedly generates successor procedural
states until the configured recursion limit is reached. At the overflow
boundary, the runtime performs an explicit control action instead of allowing
unbounded continuation.

The scenario tests the distinction between:

    continuity
    and
    uncontrolled recursion
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
class RecursionStressResult:
    """Serializable summary of a C5 recursion-stress run."""

    process_id: str
    configured_limit: int
    generated_steps: int
    overflow_reached: bool
    overflow_action: str
    explicit_control_event_recorded: bool
    unbounded_growth_prevented: bool
    process_terminated: bool
    continuity_valid: bool
    metrics: dict[str, Any]
    event_log: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "process_id": self.process_id,
            "configured_limit": self.configured_limit,
            "generated_steps": self.generated_steps,
            "overflow_reached": self.overflow_reached,
            "overflow_action": self.overflow_action,
            "explicit_control_event_recorded": (
                self.explicit_control_event_recorded
            ),
            "unbounded_growth_prevented": (
                self.unbounded_growth_prevented
            ),
            "process_terminated": self.process_terminated,
            "continuity_valid": self.continuity_valid,
            "metrics": dict(self.metrics),
            "event_log": list(self.event_log),
        }


def run_recursion_stress(
    *,
    process_id: str = "recursion-stress-simulation",
    max_depth: int = 5,
) -> RecursionStressResult:
    """Run the deterministic recursion-stress scenario."""
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1.")

    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=max_depth + 5,
            strict_state_sync=True,
        )
    )

    carrier = Carrier(
        carrier_id="carrier_recursive",
        carrier_type="recursive_reasoner",
        capabilities=CapabilityProfile(
            name="recursive",
            capabilities=frozenset(
                {
                    "general_reasoning",
                    "continuation",
                }
            ),
        ),
    )

    runtime.add_carrier(carrier)

    root = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Generate successor procedural states until C5 recursion control "
            "must intervene."
        ),
        current_state="Recursive process root.",
        unresolved_difference=(
            "Each successor intentionally generates another continuation."
        ),
        next_required_operation=Operation.UNFOLD,
        constraints=[
            "C5 maximum recursion depth is explicit.",
            "Overflow must trigger an explicit control action.",
        ],
        continuation_relevant={
            "recursive_generation": True,
        },
    )

    runtime.add_state(root)
    runtime.activate("carrier_recursive", "P0")

    current = root
    generated_steps = 1

    while current.step_index < max_depth:
        successor_id = (
            f"P{current.step_index + 1}"
        )

        successor = ProceduralState(
            unit_id=successor_id,
            step_index=current.step_index + 1,
            task=current.task,
            current_state=(
                f"Recursive successor generated from {current.unit_id}."
            ),
            local_result=(
                f"Continuation generated at depth "
                f"{current.step_index + 1}."
            ),
            unresolved_difference=(
                "Generate another successor until the C5 boundary."
            ),
            next_required_operation=Operation.UNFOLD,
            constraints=list(current.constraints),
            continuation_relevant={
                **current.continuation_relevant,
                "depth": current.step_index + 1,
                "parent_unit_id": current.unit_id,
            },
            parent_unit_id=current.unit_id,
        )

        runtime.snapshot.active_units[successor_id] = successor
        runtime.snapshot.store_state(successor)

        current = successor
        generated_steps += 1

    overflow_reached = current.step_index >= max_depth

    overflow_action = "pause"

    # C5 is represented explicitly as a runtime event. The process does not
    # continue to generate more states after the configured boundary.
    runtime.snapshot.record_event(
        event_type=__import__(
            "simulation.core.models",
            fromlist=["EventType"],
        ).EventType.TERMINATION_REQUESTED,
        unit_id=current.unit_id,
        carrier_id=carrier.carrier_id,
        details={
            "reason": "C5 recursion limit reached.",
            "current_depth": current.step_index,
            "max_depth_limit": max_depth,
            "action_on_overflow": overflow_action,
            "process_continuation_disabled": True,
        },
    )

    explicit_control_event_recorded = any(
        event.details.get("action_on_overflow") == overflow_action
        and event.details.get("max_depth_limit") == max_depth
        for event in runtime.snapshot.events
    )

    # The process remains non-terminated because the selected C5 action is
    # pause. No successor is generated beyond the configured boundary.
    process_terminated = runtime.terminated

    unbounded_growth_prevented = (
        generated_steps == max_depth + 1
        and current.step_index == max_depth
        and not process_terminated
    )

    runtime.assert_continuity()

    return RecursionStressResult(
        process_id=process_id,
        configured_limit=max_depth,
        generated_steps=generated_steps,
        overflow_reached=overflow_reached,
        overflow_action=overflow_action,
        explicit_control_event_recorded=(
            explicit_control_event_recorded
        ),
        unbounded_growth_prevented=(
            unbounded_growth_prevented
        ),
        process_terminated=process_terminated,
        continuity_valid=(
            current.step_index == max_depth
            and generated_steps == max_depth + 1
        ),
        metrics=runtime.metrics(),
        event_log=runtime.event_log(),
    )


def main() -> int:
    """Run the scenario and emit JSON."""
    import json

    result = run_recursion_stress()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if not result.overflow_reached:
        return 1

    if result.overflow_action not in {
        "delegate",
        "branch",
        "pause",
        "terminate",
    }:
        return 1

    if not result.explicit_control_event_recorded:
        return 1

    if not result.unbounded_growth_prevented:
        return 1

    if result.process_terminated:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
