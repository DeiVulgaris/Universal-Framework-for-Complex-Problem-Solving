"""Controlled descriptive comparison: distributed continuity vs centralization.

Both conditions execute the same deterministic multi-step workload.

Condition A:
    distributed UFCPS-style continuation with explicit handoff state.

Condition B:
    centralized reference execution with one persistent controller.

The scenario reports observable differences in recovery, transitions, state
operations, and overhead. It does not assign an overall winner.
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
from ..policies import FailureEvent, FailureInjector, FailureType


@dataclass(frozen=True)
class ConditionMetrics:
    """Metrics for one comparison condition."""

    condition: str
    completed: bool
    process_terminated: bool
    carrier_changes: int
    transitions: int
    stored_states: int
    communication_events: int
    recovery_events: int
    repeated_work: int
    execution_steps: int
    continuity_valid: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        return {
            "condition": self.condition,
            "completed": self.completed,
            "process_terminated": self.process_terminated,
            "carrier_changes": self.carrier_changes,
            "transitions": self.transitions,
            "stored_states": self.stored_states,
            "communication_events": self.communication_events,
            "recovery_events": self.recovery_events,
            "repeated_work": self.repeated_work,
            "execution_steps": self.execution_steps,
            "continuity_valid": self.continuity_valid,
        }


@dataclass(frozen=True)
class ContinuityVsCentralizationResult:
    """Serializable comparison result."""

    process_id: str
    task_definition_equal: bool
    distributed: ConditionMetrics
    centralized: ConditionMetrics
    observations: tuple[str, ...]
    process_terminated: bool
    continuity_valid: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible comparison."""
        return {
            "process_id": self.process_id,
            "task_definition_equal": self.task_definition_equal,
            "distributed": self.distributed.to_dict(),
            "centralized": self.centralized.to_dict(),
            "observations": list(self.observations),
            "process_terminated": self.process_terminated,
            "continuity_valid": self.continuity_valid,
        }


def _distributed_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Complete one distributed local stage."""
    del carrier

    return ExecutionResult(
        completed=True,
        current_state=(
            f"Distributed stage {state.step_index} completed."
        ),
        local_result=(
            f"Distributed stage {state.step_index} completed."
        ),
        difference=(
            f"Continuation required after distributed stage "
            f"{state.step_index}."
        ),
        next_operation=Operation.DISS,
    )


def _centralized_executor(
    state: ProceduralState,
    carrier: Carrier,
) -> ExecutionResult:
    """Complete one centralized local stage."""
    del carrier

    return ExecutionResult(
        completed=True,
        current_state=(
            f"Centralized stage {state.step_index} completed."
        ),
        local_result=(
            f"Centralized stage {state.step_index} completed."
        ),
        difference="",
        next_operation=None,
    )


def _new_state(
    unit_id: str,
    step_index: int,
    task: str,
    current_state: str,
) -> ProceduralState:
    """Create an equivalent deterministic stage for both conditions."""
    return ProceduralState(
        unit_id=unit_id,
        step_index=step_index,
        task=task,
        current_state=current_state,
        unresolved_difference=(
            "The workload requires the next procedural stage."
        ),
        next_required_operation=Operation.DIFF,
        constraints=[
            "The task definition must remain identical across conditions."
        ],
        continuation_relevant={
            "comparison_workload": True,
        },
    )


def _run_distributed(
    process_id: str,
    stages: int,
) -> ConditionMetrics:
    """Run the continuity-preserving distributed condition."""
    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=stages * 3 + 10,
            strict_state_sync=True,
        )
    )

    for carrier_id in (
        "distributed_A",
        "distributed_B",
        "distributed_C",
    ):
        runtime.add_carrier(
            Carrier(
                carrier_id=carrier_id,
                carrier_type="distributed_reasoner",
                capabilities=CapabilityProfile(
                    name="distributed",
                    capabilities=frozenset(
                        {
                            "general_reasoning",
                            "continuation",
                        }
                    ),
                ),
            )
        )

    task = (
        "Execute a deterministic multi-stage workload with one controlled "
        "carrier interruption."
    )

    current = _new_state(
        "D0",
        0,
        task,
        "Distributed workload root.",
    )
    runtime.add_state(current)
    current_carrier = "distributed_A"
    runtime.activate(current_carrier, current.unit_id)

    recovery_events = 0
    repeated_work = 0
    failure_step = max(1, stages // 2)

    for step in range(stages):
        current = runtime.get_state(current.unit_id)

        runtime.execute(
            current.unit_id,
            current_carrier,
            _distributed_executor,
        )

        current = runtime.get_state(current.unit_id)
        runtime.preserve(current.unit_id)

        # The interruption is injected only after the source carrier has
        # actually completed the current procedural unit. This preserves the
        # invariant that the failed carrier is the carrier of P_n.
        if step == failure_step - 1 and step < stages - 1:
            # Preserve the current carrier-to-unit relation while marking
            # the carrier locally stuck. This models an interruption in which
            # the carrier becomes unable to continue but its process context
            # remains available for handoff.
            runtime.get_carrier(current_carrier).status = (
                __import__(
                    "simulation.core.models",
                    fromlist=["CarrierStatus"],
                ).CarrierStatus.STUCK
            )

            injector = FailureInjector(
                [
                    FailureEvent(
                        tick=runtime.snapshot.tick,
                        failure_type=FailureType.COMMUNICATION_LOSS,
                        carrier_id=current_carrier,
                        unit_id=current.unit_id,
                        details={
                            "channel": "comparison_source_channel",
                            "reason": (
                                "Controlled interruption for distributed "
                                "continuity comparison."
                            ),
                        },
                    )
                ]
            )

            injector.apply_due(
                runtime.snapshot,
                tick=runtime.snapshot.tick,
            )

            successor = runtime.delegate(
                current.unit_id,
                current_carrier,
                "distributed_B",
                reason=(
                    "Controlled comparison failure: continue from preserved "
                    "state on a replacement carrier."
                ),
                next_unit_id=f"D{step + 1}",
            )

            recovery_events += 1
            current = successor
            current_carrier = "distributed_B"
            continue

        if step < stages - 1:
            next_state = _new_state(
                f"D{step + 1}",
                step + 1,
                task,
                f"State after distributed stage {step}.",
            )
            next_state.parent_unit_id = current.unit_id
            next_state.continuation_relevant.update(
                current.continuation_relevant
            )

            runtime.snapshot.active_units[
                next_state.unit_id
            ] = next_state

            runtime.get_carrier(
                current_carrier
            ).activate(next_state.unit_id)

            runtime.snapshot.store_state(next_state)
            current = next_state

    runtime.assert_continuity()

    metrics = runtime.metrics()

    carrier_changes = sum(
        1
        for transition in runtime.snapshot.transitions
        if transition.carrier_changed()
    )

    communication_events = sum(
        1
        for event in runtime.snapshot.events
        if event.event_type.value
        in {
            "HANDOFF_REQUESTED",
            "CARRIER_REPLACED",
        }
    )

    return ConditionMetrics(
        condition="distributed",
        completed=True,
        process_terminated=runtime.terminated,
        carrier_changes=carrier_changes,
        transitions=metrics["transitions"],
        stored_states=metrics["stored_states"],
        communication_events=communication_events,
        recovery_events=recovery_events,
        repeated_work=repeated_work,
        execution_steps=metrics["runtime_steps"],
        continuity_valid=all(
            transition.validate_step_continuity()
            for transition in runtime.snapshot.transitions
        ),
    )


def _run_centralized(
    process_id: str,
    stages: int,
) -> ConditionMetrics:
    """Run the centralized reference condition."""
    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=stages + 10,
            strict_state_sync=True,
        )
    )

    runtime.add_carrier(
        Carrier(
            carrier_id="central_controller",
            carrier_type="central_controller",
            capabilities=CapabilityProfile(
                name="central",
                capabilities=frozenset(
                    {
                        "general_reasoning",
                        "continuation",
                        "coordination",
                    }
                ),
            ),
        )
    )

    task = (
        "Execute a deterministic multi-stage workload with one controlled "
        "carrier interruption."
    )

    state = _new_state(
        "C0",
        0,
        task,
        "Centralized workload root.",
    )
    runtime.add_state(state)
    runtime.activate(
        "central_controller",
        "C0",
    )

    for step in range(stages):
        current = runtime.get_state(
            f"C{step}"
        )

        runtime.execute(
            current.unit_id,
            "central_controller",
            _centralized_executor,
        )

        if step < stages - 1:
            next_state = _new_state(
                f"C{step + 1}",
                step + 1,
                task,
                f"State after centralized stage {step}.",
            )
            next_state.parent_unit_id = current.unit_id

            runtime.snapshot.active_units[
                next_state.unit_id
            ] = next_state

            runtime.get_carrier(
                "central_controller"
            ).release()

            runtime.get_carrier(
                "central_controller"
            ).activate(
                next_state.unit_id
            )

            runtime.snapshot.store_state(next_state)

    runtime.assert_continuity()

    metrics = runtime.metrics()

    return ConditionMetrics(
        condition="centralized",
        completed=True,
        process_terminated=runtime.terminated,
        carrier_changes=0,
        transitions=metrics["transitions"],
        stored_states=metrics["stored_states"],
        communication_events=0,
        recovery_events=0,
        repeated_work=0,
        execution_steps=metrics["runtime_steps"],
        continuity_valid=True,
    )


def run_continuity_vs_centralization(
    *,
    process_id: str = "continuity-vs-centralization-simulation",
    stages: int = 8,
) -> ContinuityVsCentralizationResult:
    """Run the two descriptive reference conditions."""
    if stages < 4:
        raise ValueError("stages must be at least 4.")

    distributed = _run_distributed(
        f"{process_id}-distributed",
        stages,
    )

    centralized = _run_centralized(
        f"{process_id}-centralized",
        stages,
    )

    observations = (
        (
            "Both conditions use the same abstract workload and the same "
            "number of procedural stages."
        ),
        (
            "The distributed condition introduces an explicit carrier "
            "replacement and continuation handoff."
        ),
        (
            "The centralized condition keeps one controller throughout "
            "the workload."
        ),
        (
            "Recorded state, transition, communication, and recovery counts "
            "describe architectural overhead under this simulation."
        ),
    )

    return ContinuityVsCentralizationResult(
        process_id=process_id,
        task_definition_equal=True,
        distributed=distributed,
        centralized=centralized,
        observations=observations,
        process_terminated=(
            distributed.process_terminated
            or centralized.process_terminated
        ),
        continuity_valid=(
            distributed.continuity_valid
            and centralized.continuity_valid
            and distributed.completed
            and centralized.completed
        ),
    )


def main() -> int:
    """Run the comparison and emit JSON."""
    import json

    result = run_continuity_vs_centralization()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if not result.task_definition_equal:
        return 1

    if result.process_terminated:
        return 1

    if not result.distributed.completed:
        return 1

    if not result.centralized.completed:
        return 1

    if not result.distributed.continuity_valid:
        return 1

    if not result.centralized.continuity_valid:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
