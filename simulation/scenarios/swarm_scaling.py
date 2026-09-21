"""Deterministic swarm-scaling scenario for UFCPS.

The scenario runs the same structural workload with progressively larger
carrier pools. It measures observable scaling effects such as branch count,
stored states, transitions, and carrier availability.

The scenario deliberately does not interpret larger carrier pools as better
or worse. It only records how the simulated process behaves as scale changes.
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
class ScalingRun:
    """Measurements for one swarm size."""

    carrier_count: int
    branch_count: int
    transitions: int
    stored_states: int
    event_count: int
    completed_branches: int
    state_isolation_valid: bool
    provenance_valid: bool
    continuity_valid: bool
    process_terminated: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible run summary."""
        return {
            "carrier_count": self.carrier_count,
            "branch_count": self.branch_count,
            "transitions": self.transitions,
            "stored_states": self.stored_states,
            "event_count": self.event_count,
            "completed_branches": self.completed_branches,
            "state_isolation_valid": self.state_isolation_valid,
            "provenance_valid": self.provenance_valid,
            "continuity_valid": self.continuity_valid,
            "process_terminated": self.process_terminated,
        }


@dataclass(frozen=True)
class SwarmScalingResult:
    """Serializable summary of the swarm-scaling benchmark."""

    process_id: str
    runs: tuple[ScalingRun, ...]
    scale_points: tuple[int, ...]
    continuity_valid: bool
    any_process_termination: bool
    all_runs_isolated: bool
    all_runs_provenance_valid: bool
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible benchmark summary."""
        return {
            "process_id": self.process_id,
            "runs": [
                run.to_dict()
                for run in self.runs
            ],
            "scale_points": list(self.scale_points),
            "continuity_valid": self.continuity_valid,
            "any_process_termination": (
                self.any_process_termination
            ),
            "all_runs_isolated": self.all_runs_isolated,
            "all_runs_provenance_valid": (
                self.all_runs_provenance_valid
            ),
            "metrics": dict(self.metrics),
        }


def _branch_executor(
    branch_index: int,
):
    """Create a deterministic branch executor."""

    def execute(
        state: ProceduralState,
        carrier: Carrier,
    ) -> ExecutionResult:
        del carrier

        result = (
            f"Branch {branch_index} completed by carrier "
            f"for unit {state.unit_id}."
        )

        return ExecutionResult(
            completed=True,
            current_state=result,
            local_result=result,
            difference=(
                f"Branch {branch_index} produced a completed local result."
            ),
            next_operation=Operation.COMPOSE,
        )

    return execute


def _run_scale_point(
    *,
    process_id: str,
    carrier_count: int,
) -> ScalingRun:
    """Run one deterministic scale point."""
    if carrier_count < 2:
        raise ValueError("carrier_count must be at least 2.")

    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=(carrier_count * 5) + 10,
            strict_state_sync=True,
        )
    )

    for index in range(carrier_count):
        runtime.add_carrier(
            Carrier(
                carrier_id=f"carrier_{index:03d}",
                carrier_type="scaling_reasoner",
                capabilities=CapabilityProfile(
                    name="scaling",
                    capabilities=frozenset(
                        {
                            "general_reasoning",
                            "parallel_resolution",
                        }
                    ),
                ),
            )
        )

    source = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Resolve a workload whose independent components can be "
            "distributed over multiple carriers."
        ),
        current_state="Scaling benchmark root state.",
        unresolved_difference=(
            "The workload contains independent branch components."
        ),
        next_required_operation=Operation.DIFF,
        constraints=[
            "Each branch must have an independent carrier.",
            "Branch state must remain isolated.",
            "Branch provenance must remain recoverable.",
        ],
        continuation_relevant={
            "scaling_test": True,
        },
    )

    runtime.add_state(source)
    runtime.activate("carrier_000", "P0")

    branch_count = carrier_count - 1

    branches = [
        (
            f"carrier_{index:03d}",
            f"branch_{index:03d}",
            f"difference_{index:03d}",
        )
        for index in range(1, carrier_count)
    ]

    successors = runtime.branch(
        "P0",
        "carrier_000",
        branches,
    )

    completed_branches = 0

    for index, successor in enumerate(successors, start=1):
        result = runtime.execute(
            successor.unit_id,
            f"carrier_{index:03d}",
            _branch_executor(index),
        )
        completed_branches += int(result.completed)

    branch_states = [
        runtime.get_state(successor.unit_id)
        for successor in successors
    ]

    state_isolation_valid = (
        len(branch_states) == branch_count
        and len(
            {
                state.unit_id
                for state in branch_states
            }
        ) == branch_count
        and len(
            {
                state.branch_id
                for state in branch_states
            }
        ) == branch_count
        and len(
            {
                state.unresolved_difference
                for state in branch_states
            }
        ) == branch_count
    )

    provenance_valid = all(
        state.parent_unit_id == "P0"
        for state in branch_states
    )

    runtime.assert_continuity()

    metrics = runtime.metrics()

    return ScalingRun(
        carrier_count=carrier_count,
        branch_count=branch_count,
        transitions=metrics["transitions"],
        stored_states=metrics["stored_states"],
        event_count=metrics["event_count"],
        completed_branches=completed_branches,
        state_isolation_valid=state_isolation_valid,
        provenance_valid=provenance_valid,
        continuity_valid=(
            completed_branches == branch_count
            and state_isolation_valid
            and provenance_valid
            and all(
                transition.validate_step_continuity()
                for transition in runtime.snapshot.transitions
            )
        ),
        process_terminated=runtime.terminated,
    )


def run_swarm_scaling(
    *,
    process_id: str = "swarm-scaling-simulation",
    scale_points: tuple[int, ...] = (2, 4, 8, 12),
) -> SwarmScalingResult:
    """Run the deterministic swarm-scaling benchmark."""
    if not scale_points:
        raise ValueError("scale_points must not be empty.")

    if any(point < 2 for point in scale_points):
        raise ValueError(
            "Every scale point must contain at least two carriers."
        )

    if tuple(sorted(set(scale_points))) != tuple(scale_points):
        raise ValueError(
            "scale_points must be strictly increasing and unique."
        )

    runs = tuple(
        _run_scale_point(
            process_id=f"{process_id}-{carrier_count}",
            carrier_count=carrier_count,
        )
        for carrier_count in scale_points
    )

    continuity_valid = all(
        run.continuity_valid
        for run in runs
    )

    any_process_termination = any(
        run.process_terminated
        for run in runs
    )

    all_runs_isolated = all(
        run.state_isolation_valid
        for run in runs
    )

    all_runs_provenance_valid = all(
        run.provenance_valid
        for run in runs
    )

    metrics = {
        "carrier_counts": list(scale_points),
        "branch_counts": [
            run.branch_count
            for run in runs
        ],
        "transitions": [
            run.transitions
            for run in runs
        ],
        "stored_states": [
            run.stored_states
            for run in runs
        ],
        "event_counts": [
            run.event_count
            for run in runs
        ],
        "completed_branches": [
            run.completed_branches
            for run in runs
        ],
    }

    return SwarmScalingResult(
        process_id=process_id,
        runs=runs,
        scale_points=scale_points,
        continuity_valid=continuity_valid,
        any_process_termination=any_process_termination,
        all_runs_isolated=all_runs_isolated,
        all_runs_provenance_valid=(
            all_runs_provenance_valid
        ),
        metrics=metrics,
    )


def main() -> int:
    """Run the benchmark and emit JSON."""
    import json

    result = run_swarm_scaling()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if result.any_process_termination:
        return 1

    if not result.all_runs_isolated:
        return 1

    if not result.all_runs_provenance_valid:
        return 1

    for run in result.runs:
        if run.completed_branches != run.branch_count:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
