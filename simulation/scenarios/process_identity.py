"""Deterministic process-identity scenario for UFCPS.

The scenario replaces the carrier at every procedural transition while
preserving continuation-relevant process state.

It operationalizes the distinction:

    Agent_n != Agent_n+1

without requiring:

    Process_n != Process_n+1

The tested continuity relation is:

    P_n -> P_n+1
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
class IdentityTransition:
    """One observed carrier-independent process transition."""

    source_agent_id: str
    destination_agent_id: str
    source_unit_id: str
    destination_unit_id: str
    source_step_index: int
    destination_step_index: int
    carrier_identity_changed: bool
    process_step_continued: bool
    continuation_state_preserved: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        return {
            "source_agent_id": self.source_agent_id,
            "destination_agent_id": self.destination_agent_id,
            "source_unit_id": self.source_unit_id,
            "destination_unit_id": self.destination_unit_id,
            "source_step_index": self.source_step_index,
            "destination_step_index": self.destination_step_index,
            "carrier_identity_changed": (
                self.carrier_identity_changed
            ),
            "process_step_continued": (
                self.process_step_continued
            ),
            "continuation_state_preserved": (
                self.continuation_state_preserved
            ),
        }


@dataclass(frozen=True)
class ProcessIdentityResult:
    """Serializable summary of the process-identity scenario."""

    process_id: str
    configured_steps: int
    completed_steps: int
    carrier_changes: int
    identity_transitions: tuple[IdentityTransition, ...]
    all_agent_identities_changed: bool
    all_process_steps_continued: bool
    all_continuation_state_preserved: bool
    carrier_identity_not_used_as_process_identity: bool
    process_terminated: bool
    continuity_valid: bool
    metrics: dict[str, Any]
    event_log: list[dict[str, Any]]
    transition_log: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible process-identity result."""
        return {
            "process_id": self.process_id,
            "configured_steps": self.configured_steps,
            "completed_steps": self.completed_steps,
            "carrier_changes": self.carrier_changes,
            "identity_transitions": [
                transition.to_dict()
                for transition in self.identity_transitions
            ],
            "all_agent_identities_changed": (
                self.all_agent_identities_changed
            ),
            "all_process_steps_continued": (
                self.all_process_steps_continued
            ),
            "all_continuation_state_preserved": (
                self.all_continuation_state_preserved
            ),
            "carrier_identity_not_used_as_process_identity": (
                self.carrier_identity_not_used_as_process_identity
            ),
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
    """Advance one stage without terminating the procedural unit.

    The stage itself produces a local result, but the process remains open
    because its unresolved difference explicitly requires a successor unit.
    This leaves the source carrier in a handoff-compatible state.
    """
    return ExecutionResult(
        completed=False,
        current_state=(
            f"Procedural step {state.step_index} completed by "
            f"{carrier.carrier_id}."
        ),
        local_result=(
            f"Result produced at step {state.step_index} by "
            f"{carrier.carrier_id}."
        ),
        difference=(
            f"Continue process from step {state.step_index}."
        ),
        next_operation=Operation.DISS,
    )


def run_process_identity(
    *,
    process_id: str = "process-identity-simulation",
    configured_steps: int = 8,
) -> ProcessIdentityResult:
    """Run the carrier-independent process-identity scenario."""
    if configured_steps < 2:
        raise ValueError(
            "configured_steps must be at least 2."
        )

    runtime = UFCPSRuntime(
        RuntimeConfig(
            process_id=process_id,
            max_steps=(configured_steps * 4) + 10,
            strict_state_sync=True,
        )
    )

    carrier_ids = [
        f"agent_{index:02d}"
        for index in range(configured_steps)
    ]

    for carrier_id in carrier_ids:
        runtime.add_carrier(
            Carrier(
                carrier_id=carrier_id,
                carrier_type="process_identity_carrier",
                capabilities=CapabilityProfile(
                    name="identity-test",
                    capabilities=frozenset(
                        {
                            "general_reasoning",
                            "continuation",
                        }
                    ),
                ),
            )
        )

    root = ProceduralState(
        unit_id="P0",
        step_index=0,
        task=(
            "Execute a procedural chain while replacing the carrier at every "
            "successive process step."
        ),
        current_state="Process identity root state.",
        unresolved_difference=(
            "The process requires a successor procedural unit."
        ),
        next_required_operation=Operation.DIFF,
        constraints=[
            "Every successor is carried by a different agent.",
            "Continuation state must survive every carrier change.",
            "Carrier identity must not define process identity.",
        ],
        continuation_relevant={
            "process_identity_test": True,
            "continuation_history": [],
        },
    )

    runtime.add_state(root)
    current = root

    identity_transitions: list[IdentityTransition] = []
    carrier_changes = 0
    completed_steps = 0

    for step in range(configured_steps):
        source_carrier_id = carrier_ids[step]

        # P0 must be activated explicitly. Every later carrier has already
        # been activated by unfold() during the preceding delegation.
        if step == 0:
            runtime.activate(
                source_carrier_id,
                current.unit_id,
            )
        else:
            active_carrier = runtime.get_carrier(source_carrier_id)
            if active_carrier.current_unit_id != current.unit_id:
                raise RuntimeError(
                    f"Carrier {source_carrier_id!r} is not carrying "
                    f"successor unit {current.unit_id!r}."
                )

        runtime.execute(
            current.unit_id,
            source_carrier_id,
            _stage_executor,
        )

        completed_steps += 1

        current = runtime.get_state(current.unit_id)
        state_reference = runtime.preserve(current.unit_id)

        if not runtime.state_exists(state_reference):
            raise RuntimeError(
                f"Continuation state {state_reference!r} was not persisted."
            )

        if step == configured_steps - 1:
            break

        destination_carrier_id = carrier_ids[step + 1]

        successor = runtime.delegate(
            current.unit_id,
            source_carrier_id,
            destination_carrier_id,
            reason=(
                "Replace the current process carrier while preserving the "
                "procedural continuation."
            ),
            next_unit_id=f"P{step + 1}",
        )

        transition = runtime.snapshot.transitions[-1]

        changed = (
            source_carrier_id
            != destination_carrier_id
        )

        process_continued = (
            successor.step_index
            == current.step_index + 1
            and transition.validate_step_continuity()
        )

        continuation_preserved = (
            transition.continuation is not None
            and transition.continuation.has_required_information()
            and runtime.state_exists(
                transition.continuation.state_reference
            )
            and bool(successor.unresolved_difference)
        )

        identity_transitions.append(
            IdentityTransition(
                source_agent_id=source_carrier_id,
                destination_agent_id=destination_carrier_id,
                source_unit_id=current.unit_id,
                destination_unit_id=successor.unit_id,
                source_step_index=current.step_index,
                destination_step_index=successor.step_index,
                carrier_identity_changed=changed,
                process_step_continued=process_continued,
                continuation_state_preserved=(
                    continuation_preserved
                ),
            )
        )

        if changed:
            carrier_changes += 1

        successor.continuation_relevant.setdefault(
            "continuation_history",
            [],
        )

        history = successor.continuation_relevant[
            "continuation_history"
        ]

        if isinstance(history, list):
            history.append(
                {
                    "source_agent": source_carrier_id,
                    "destination_agent": destination_carrier_id,
                    "source_unit": current.unit_id,
                    "destination_unit": successor.unit_id,
                }
            )

        runtime.snapshot.store_state(successor)
        current = successor

    runtime.assert_continuity()

    all_agent_identities_changed = (
        len(identity_transitions) == configured_steps - 1
        and all(
            transition.carrier_identity_changed
            for transition in identity_transitions
        )
    )

    all_process_steps_continued = (
        len(identity_transitions) == configured_steps - 1
        and all(
            transition.process_step_continued
            for transition in identity_transitions
        )
    )

    all_continuation_state_preserved = (
        len(identity_transitions) == configured_steps - 1
        and all(
            transition.continuation_state_preserved
            for transition in identity_transitions
        )
    )

    carrier_identity_not_used_as_process_identity = (
        all_agent_identities_changed
        and all_process_steps_continued
        and all_continuation_state_preserved
    )

    process_terminated = runtime.terminated

    continuity_valid = (
        completed_steps == configured_steps
        and carrier_changes == configured_steps - 1
        and carrier_identity_not_used_as_process_identity
        and not process_terminated
        and all(
            transition.validate_step_continuity()
            for transition in runtime.snapshot.transitions
        )
    )

    return ProcessIdentityResult(
        process_id=process_id,
        configured_steps=configured_steps,
        completed_steps=completed_steps,
        carrier_changes=carrier_changes,
        identity_transitions=tuple(identity_transitions),
        all_agent_identities_changed=(
            all_agent_identities_changed
        ),
        all_process_steps_continued=(
            all_process_steps_continued
        ),
        all_continuation_state_preserved=(
            all_continuation_state_preserved
        ),
        carrier_identity_not_used_as_process_identity=(
            carrier_identity_not_used_as_process_identity
        ),
        process_terminated=process_terminated,
        continuity_valid=continuity_valid,
        metrics=runtime.metrics(),
        event_log=runtime.event_log(),
        transition_log=runtime.transition_log(),
    )


def main() -> int:
    """Run the scenario and emit JSON."""
    import json

    result = run_process_identity()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if not result.continuity_valid:
        return 1

    if result.completed_steps != result.configured_steps:
        return 1

    if result.carrier_changes != result.configured_steps - 1:
        return 1

    if not result.all_agent_identities_changed:
        return 1

    if not result.all_process_steps_continued:
        return 1

    if not result.all_continuation_state_preserved:
        return 1

    if not result.carrier_identity_not_used_as_process_identity:
        return 1

    if result.process_terminated:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
