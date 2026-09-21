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
from .composition import (
    CompositionResult,
    run_composition,
)
from .contradictory_branches import (
    ContradictionResult,
    run_contradictory_branches,
)
from .forced_deadlock import (
    DeadlockScenarioResult,
    run_forced_deadlock,
)
from .negative_result import (
    NegativeResultScenario,
    run_negative_result,
)
from .parallel_resolution import (
    ParallelScenarioResult,
    run_parallel_resolution,
)
from .stateless_delegation_control import (
    DelegationConditionResult,
    StatelessDelegationResult,
    run_stateless_delegation_control,
)

__all__ = [
    "AutonomousExperimentPlan",
    "AutonomousExperimentResult",
    "CarrierSubstitutionResult",
    "CompositionResult",
    "ContradictionResult",
    "DeadlockScenarioResult",
    "DelegationConditionResult",
    "NegativeResultScenario",
    "ParallelScenarioResult",
    "ScenarioResult",
    "StatelessDelegationResult",
    "execute_autonomous_experiment",
    "generate_experiment",
    "run_autonomous_experiment",
    "run_basic_handoff",
    "run_carrier_substitution",
    "run_composition",
    "run_contradictory_branches",
    "run_forced_deadlock",
    "run_negative_result",
    "run_parallel_resolution",
    "run_stateless_delegation_control",
]
