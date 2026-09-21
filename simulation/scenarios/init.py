"""Scenario package for UFCPS simulations."""

from .autonomous_experiment import (
    AutonomousExperimentPlan,
    AutonomousExperimentResult,
    execute_autonomous_experiment,
    generate_experiment,
    run_autonomous_experiment,
)
from .basic_handoff import (
    ScenarioResult,
    run_basic_handoff,
)
from .carrier_substitution import (
    CarrierSubstitutionResult,
    run_carrier_substitution,
)
from .communication_interruption import (
    CommunicationInterruptionResult,
    run_communication_interruption,
)
from .composition import (
    CompositionResult,
    run_composition,
)
from .contradictory_branches import (
    ContradictionResult,
    run_contradictory_branches,
)
from .continuity_vs_centralization import (
    ConditionMetrics,
    ContinuityVsCentralizationResult,
    run_continuity_vs_centralization,
)
from .forced_deadlock import (
    DeadlockScenarioResult,
    run_forced_deadlock,
)
from .global_termination import (
    GlobalTerminationResult,
    run_global_termination,
)
from .long_run_continuity import (
    LongRunContinuityResult,
    run_long_run_continuity,
)
from .negative_result import (
    NegativeResultScenario,
    run_negative_result,
)
from .parallel_resolution import (
    ParallelScenarioResult,
    run_parallel_resolution,
)
from .recursion_stress import (
    RecursionStressResult,
    run_recursion_stress,
)
from .repeated_carrier_replacement import (
    ReplacementRecord,
    RepeatedCarrierReplacementResult,
    run_repeated_carrier_replacement,
)
from .process_identity import (
    IdentityTransition,
    ProcessIdentityResult,
    run_process_identity,
)
from .stateless_delegation_control import (
    DelegationConditionResult,
    StatelessDelegationResult,
    run_stateless_delegation_control,
)
from .swarm_scaling import (
    ScalingRun,
    SwarmScalingResult,
    run_swarm_scaling,
)

__all__ = [
    "AutonomousExperimentPlan",
    "AutonomousExperimentResult",
    "CarrierSubstitutionResult",
    "CommunicationInterruptionResult",
    "CompositionResult",
    "ConditionMetrics",
    "ContradictionResult",
    "ContinuityVsCentralizationResult",
    "DeadlockScenarioResult",
    "DelegationConditionResult",
    "GlobalTerminationResult",
    "LongRunContinuityResult",
    "NegativeResultScenario",
    "ParallelScenarioResult",
    "RecursionStressResult",
    "ReplacementRecord",
    "RepeatedCarrierReplacementResult",
    "IdentityTransition",
    "ProcessIdentityResult",
    "ScalingRun",
    "ScenarioResult",
    "StatelessDelegationResult",
    "SwarmScalingResult",
    "execute_autonomous_experiment",
    "generate_experiment",
    "run_autonomous_experiment",
    "run_basic_handoff",
    "run_carrier_substitution",
    "run_communication_interruption",
    "run_composition",
    "run_contradictory_branches",
    "run_continuity_vs_centralization",
    "run_forced_deadlock",
    "run_global_termination",
    "run_long_run_continuity",
    "run_negative_result",
    "run_parallel_resolution",
    "run_recursion_stress",
    "run_repeated_carrier_replacement",
    "run_process_identity",
    "run_stateless_delegation_control",
    "run_swarm_scaling",
]
from .transition_validation import run_transition_validation
