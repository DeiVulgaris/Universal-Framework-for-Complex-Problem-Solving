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
from .forced_deadlock import (
    DeadlockScenarioResult,
    run_forced_deadlock,
)
from .parallel_resolution import (
    ParallelScenarioResult,
    run_parallel_resolution,
)

__all__ = [
    "AutonomousExperimentPlan",
    "AutonomousExperimentResult",
    "CarrierSubstitutionResult",
    "DeadlockScenarioResult",
    "ParallelScenarioResult",
    "ScenarioResult",
    "execute_autonomous_experiment",
    "generate_experiment",
    "run_autonomous_experiment",
    "run_basic_handoff",
    "run_carrier_substitution",
    "run_forced_deadlock",
    "run_parallel_resolution",
]
