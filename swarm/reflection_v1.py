"""
UFCPS — Reflection State v1

Reflection is the process-level capacity to distinguish:

    Self
    World
    Model(World)
    Model(Self)
    Model(Self–World interaction)

and to make the current way of knowing itself an object of investigation.

Canonical Level 3 sequence:

    C_k
      ↓
    exhaustion
      ↓
    Fr
      ↓
    Self–World Differentiation
      ↓
    World Model ↔ Self Model
      ↓
    Model of Self–World Interaction
      ↓
    Reflection
      ↓
    Reflexive Policy
      ↓
    Orthogonal Transition

Important:

Reflection does NOT:
    - claim phenomenal consciousness;
    - solve the original task;
    - automatically perform an orthogonal transition;
    - assume that exhaustion necessarily implies creativity.

Its function is to make the relation between the process,
its world-model, and its own mode of knowing available for
further differentiation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class ReflectionStatus(str, Enum):
    INACTIVE = "INACTIVE"
    TRIGGERED = "TRIGGERED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class ReflectionTarget(str, Enum):
    NONE = "NONE"

    CURRENT_RESULT = "CURRENT_RESULT"
    CURRENT_METHOD = "CURRENT_METHOD"

    WORLD_MODEL = "WORLD_MODEL"
    SELF_MODEL = "SELF_MODEL"
    SELF_WORLD_RELATION = "SELF_WORLD_RELATION"

    COGNITIVE_SPACE = "COGNITIVE_SPACE"
    ACTUALIZATION_MODE = "ACTUALIZATION_MODE"


class ReflectionOutcome(str, Enum):
    NONE = "NONE"

    LOCAL_CORRECTION = "LOCAL_CORRECTION"
    CONTINUE_CURRENT_SPACE = "CONTINUE_CURRENT_SPACE"

    UPDATE_WORLD_MODEL = "UPDATE_WORLD_MODEL"
    UPDATE_SELF_MODEL = "UPDATE_SELF_MODEL"
    UPDATE_SELF_WORLD_RELATION = "UPDATE_SELF_WORLD_RELATION"

    PREPARE_ORTHOGONAL_TRANSITION = (
        "PREPARE_ORTHOGONAL_TRANSITION"
    )


@dataclass(frozen=True)
class WorldModel:
    """
    Representation of the investigated world.

    This is an architectural object, not a claim that the model
    corresponds completely or objectively to reality.
    """

    model_id: str
    version: str

    distinctions: List[str]
    relations: List[str]
    uncertainties: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SelfModel:
    """
    Representation of the process itself.

    Includes the process' own limitations, resources,
    representations, history, and current mode of knowing.
    """

    model_id: str
    version: str

    capabilities: List[str]
    limitations: List[str]
    resources: List[str]

    current_method: str
    current_cognitive_space: str

    process_history_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SelfWorldRelationModel:
    """
    Representation of the relation between Self and World.

    This model captures how the process' own way of knowing
    affects what can be distinguished about the investigated world.
    """

    model_id: str
    version: str

    observation_channels: List[str]
    dependencies: List[str]
    blind_spots: List[str]

    model_influence_on_observation: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelOfKnowing:
    """
    Meta-model of the process by which knowledge is produced.

    This is the reflexive object that becomes possible when
    Self and World are distinguished from one another.
    """

    model_id: str
    version: str

    world_model_ref: str
    self_model_ref: str
    relation_model_ref: str

    assumptions: List[str]
    constraints: List[str]
    accessible_distinctions: List[str]

    exhausted_distinctions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReflectionState:
    """
    Formal representation of Level 3 reflection.

    Reflection is represented as a change in the structure
    of the process' investigation, not as a claim about
    subjective experience.
    """

    status: ReflectionStatus

    target: ReflectionTarget
    outcome: ReflectionOutcome

    source_frustration_status: str
    source_trigger: str

    pressure: float

    self_world_differentiated: bool

    world_model_available: bool
    self_model_available: bool
    relation_model_available: bool
    model_of_knowing_available: bool

    world_model: Optional[WorldModel]
    self_model: Optional[SelfModel]
    self_world_relation: Optional[SelfWorldRelationModel]
    model_of_knowing: Optional[ModelOfKnowing]

    current_method_question: str
    self_question: str
    world_question: str
    self_world_question: str
    cognitive_space_question: str

    evidence: List[str]

    transition_candidate: bool

    description: str

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)

        result["status"] = self.status.value
        result["target"] = self.target.value
        result["outcome"] = self.outcome.value

        if self.world_model is not None:
            result["world_model"] = self.world_model.to_dict()

        if self.self_model is not None:
            result["self_model"] = self.self_model.to_dict()

        if self.self_world_relation is not None:
            result["self_world_relation"] = (
                self.self_world_relation.to_dict()
            )

        if self.model_of_knowing is not None:
            result["model_of_knowing"] = (
                self.model_of_knowing.to_dict()
            )

        return result


@dataclass(frozen=True)
class ReflectionConfig:
    """
    Configuration controlling activation of reflection.

    Reflection requires sufficient structural pressure and,
    for full Level 3 reflection, explicit Self–World differentiation.
    """

    activation_pressure: float = 0.50

    require_self_world_differentiation: bool = True

    require_world_model: bool = True
    require_self_model: bool = True
    require_relation_model: bool = True


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(minimum, min(maximum, value))


def _get(
    source: Any,
    field: str,
    default: Any,
) -> Any:
    return getattr(source, field, default)


def _available(
    value: Any,
) -> bool:
    return value is not None


def build_reflexive_models(
    *,
    world_model: WorldModel,
    self_model: SelfModel,
    relation_model: SelfWorldRelationModel,
    model_id: str = "mok_v1",
) -> ModelOfKnowing:
    """
    Construct a meta-model of knowing from the three primary
    Level 3 components:

        World Model
        Self Model
        Self–World Relation Model
    """

    return ModelOfKnowing(
        model_id=model_id,
        version="1.0",

        world_model_ref=world_model.model_id,
        self_model_ref=self_model.model_id,
        relation_model_ref=relation_model.model_id,

        assumptions=[
            "Self != World",
            "World is represented through a model",
            "Self can represent aspects of its own operation",
            "Observation is influenced by the relation between Self and World",
        ],

        constraints=[
            "World Model is incomplete",
            "Self Model is incomplete",
            "Self–World relation may contain blind spots",
        ],

        accessible_distinctions=[
            "world_state",
            "self_state",
            "observation_relation",
            "method_limitation",
            "model_limitation",
        ],

        exhausted_distinctions=[],
    )


def from_frustration(
    frustration: Any,
    *,
    world_model: Optional[WorldModel] = None,
    self_model: Optional[SelfModel] = None,
    relation_model: Optional[SelfWorldRelationModel] = None,
    model_of_knowing: Optional[ModelOfKnowing] = None,
    config: ReflectionConfig = ReflectionConfig(),
) -> ReflectionState:
    """
    Convert functional frustration into a Level 3 reflexive state.

    The key architectural transition is:

        object of investigation
            ↓
        relation between
        World Model and Self Model
            ↓
        model of knowing itself

    Reflection is activated only when structural pressure is sufficient.

    Full Level 3 reflection additionally requires explicit
    Self–World differentiation and the corresponding models.
    """

    raw_status = _get(
        frustration,
        "status",
        ReflectionStatus.INACTIVE,
    )

    raw_trigger = _get(
        frustration,
        "trigger",
        "NONE",
    )

    if hasattr(raw_status, "value"):
        raw_status = raw_status.value

    if hasattr(raw_trigger, "value"):
        raw_trigger = raw_trigger.value

    pressure = _clamp(
        float(
            _get(
                frustration,
                "pressure",
                0.0,
            )
        )
    )

    world_available = _available(world_model)
    self_available = _available(self_model)
    relation_available = _available(relation_model)
    knowing_available = _available(model_of_knowing)

    self_world_differentiated = (
        world_available
        and self_available
        and relation_available
    )

    active_frustration = raw_status == "ACTIVE"
    emerging_frustration = raw_status == "EMERGING"

    if not active_frustration and not emerging_frustration:

        return ReflectionState(
            status=ReflectionStatus.INACTIVE,

            target=ReflectionTarget.NONE,
            outcome=ReflectionOutcome.NONE,

            source_frustration_status=str(raw_status),
            source_trigger=str(raw_trigger),

            pressure=pressure,

            self_world_differentiated=(
                self_world_differentiated
            ),

            world_model_available=world_available,
            self_model_available=self_available,
            relation_model_available=relation_available,
            model_of_knowing_available=knowing_available,

            world_model=world_model,
            self_model=self_model,
            self_world_relation=relation_model,
            model_of_knowing=model_of_knowing,

            current_method_question=(
                "Is the current method limiting productive differentiation?"
            ),

            self_question=(
                "What properties of the process itself constrain knowing?"
            ),

            world_question=(
                "What properties of the investigated world remain unresolved?"
            ),

            self_world_question=(
                "How does the relation between Self and World constrain observation?"
            ),

            cognitive_space_question=(
                "Has the current cognitive space become insufficient?"
            ),

            evidence=[],

            transition_candidate=False,

            description=(
                "Reflection is not activated by the current state."
            ),
        )

    if pressure < config.activation_pressure:

        return ReflectionState(
            status=ReflectionStatus.TRIGGERED,

            target=ReflectionTarget.CURRENT_METHOD,
            outcome=ReflectionOutcome.CONTINUE_CURRENT_SPACE,

            source_frustration_status=str(raw_status),
            source_trigger=str(raw_trigger),

            pressure=pressure,

            self_world_differentiated=(
                self_world_differentiated
            ),

            world_model_available=world_available,
            self_model_available=self_available,
            relation_model_available=relation_available,
            model_of_knowing_available=knowing_available,

            world_model=world_model,
            self_model=self_model,
            self_world_relation=relation_model,
            model_of_knowing=model_of_knowing,

            current_method_question=(
                "Is the current method limiting productive differentiation?"
            ),

            self_question=(
                "What properties of the process itself constrain knowing?"
            ),

            world_question=(
                "What properties of the investigated world remain unresolved?"
            ),

            self_world_question=(
                "How does the Self–World relation constrain observation?"
            ),

            cognitive_space_question=(
                "Has the current cognitive space become insufficient?"
            ),

            evidence=[
                "frustration_pressure_below_reflection_threshold",
            ],

            transition_candidate=False,

            description=(
                "The process is under pressure but has not yet "
                "activated full reflexive investigation."
            ),
        )

    # ------------------------------------------------------------
    # Full Level 3 reflection
    # ------------------------------------------------------------

    evidence = [
        "functional_frustration_active",
        "self_world_differentiation_available",
    ]

    if world_available:
        evidence.append("world_model_available")

    if self_available:
        evidence.append("self_model_available")

    if relation_available:
        evidence.append(
            "self_world_relation_model_available"
        )

    if knowing_available:
        evidence.append(
            "model_of_knowing_available"
        )

    missing = []

    if config.require_world_model and not world_available:
        missing.append("world_model")

    if config.require_self_model and not self_available:
        missing.append("self_model")

    if config.require_relation_model and not relation_available:
        missing.append("self_world_relation_model")

    if (
        config.require_self_world_differentiation
        and not self_world_differentiated
    ):
        missing.append("self_world_differentiation")

    if missing:

        evidence.append(
            "reflexive_models_incomplete"
        )

        evidence.extend(
            f"missing:{item}"
            for item in missing
        )

        return ReflectionState(
            status=ReflectionStatus.TRIGGERED,

            target=ReflectionTarget.SELF_WORLD_RELATION,
            outcome=ReflectionOutcome.UPDATE_SELF_WORLD_RELATION,

            source_frustration_status=str(raw_status),
            source_trigger=str(raw_trigger),

            pressure=pressure,

            self_world_differentiated=(
                self_world_differentiated
            ),

            world_model_available=world_available,
            self_model_available=self_available,
            relation_model_available=relation_available,
            model_of_knowing_available=knowing_available,

            world_model=world_model,
            self_model=self_model,
            self_world_relation=relation_model,
            model_of_knowing=model_of_knowing,

            current_method_question=(
                "Is the limitation caused by the current "
                "way of generating distinctions?"
            ),

            self_question=(
                "What properties of Self constrain the available "
                "observations and distinctions?"
            ),

            world_question=(
                "Which distinctions belong to the investigated "
                "world rather than to the model of Self?"
            ),

            self_world_question=(
                "How does the relation between Self and World "
                "shape what can be known?"
            ),

            cognitive_space_question=(
                "Is the limitation located in the current "
                "cognitive space itself?"
            ),

            evidence=evidence,

            transition_candidate=False,

            description=(
                "Reflexive investigation has been triggered, "
                "but the Self–World model is incomplete."
            ),
        )

    # Full reflexive structure exists.

    if model_of_knowing is None:
        model_of_knowing = build_reflexive_models(
            world_model=world_model,
            self_model=self_model,
            relation_model=relation_model,
        )

        evidence.append(
            "model_of_knowing_constructed"
        )

        knowing_available = True

    return ReflectionState(
        status=ReflectionStatus.ACTIVE,

        target=ReflectionTarget.SELF_WORLD_RELATION,
        outcome=ReflectionOutcome.PREPARE_ORTHOGONAL_TRANSITION,

        source_frustration_status=str(raw_status),
        source_trigger=str(raw_trigger),

        pressure=pressure,

        self_world_differentiated=True,

        world_model_available=True,
        self_model_available=True,
        relation_model_available=True,
        model_of_knowing_available=knowing_available,

        world_model=world_model,
        self_model=self_model,
        self_world_relation=relation_model,
        model_of_knowing=model_of_knowing,

        current_method_question=(
            "Is the limitation caused by the current "
            "way of generating distinctions?"
        ),

        self_question=(
            "What properties of Self constrain the available "
            "observations, models, and distinctions?"
        ),

        world_question=(
            "What properties of World remain unresolved "
            "independently of the current Self Model?"
        ),

        self_world_question=(
            "How does the relation between Self and World "
            "determine the accessible space of distinctions?"
        ),

        cognitive_space_question=(
            "Has the current cognitive space itself become "
            "insufficient for further productive differentiation?"
        ),

        evidence=evidence,

        transition_candidate=True,

        description=(
            "The process distinguishes Self from World, models both "
            "sides and their relation, and makes its own way of knowing "
            "an object of investigation."
        ),
    )


def reflect_on_frustration(
    frustration: Any,
    *,
    world_model: Optional[WorldModel] = None,
    self_model: Optional[SelfModel] = None,
    relation_model: Optional[SelfWorldRelationModel] = None,
    model_of_knowing: Optional[ModelOfKnowing] = None,
    config: ReflectionConfig = ReflectionConfig(),
) -> Dict[str, Any]:
    """
    JSON-serializable convenience wrapper.
    """

    return from_frustration(
        frustration,
        world_model=world_model,
        self_model=self_model,
        relation_model=relation_model,
        model_of_knowing=model_of_knowing,
        config=config,
    ).to_dict()


def demo() -> None:
    """
    Demonstrate Level 3 Self–World reflection.
    """

    class DemoFrustration:
        status = "ACTIVE"
        trigger = "COGNITIVE_SPACE_EXHAUSTION"
        pressure = 0.91

    world = WorldModel(
        model_id="world_v1",
        version="1.0",

        distinctions=[
            "observed_state",
            "external_constraint",
            "task_result",
        ],

        relations=[
            "causal_relation",
            "temporal_relation",
        ],

        uncertainties=[
            "unresolved_relation",
        ],
    )

    self_model = SelfModel(
        model_id="self_v1",
        version="1.0",

        capabilities=[
            "observation",
            "reasoning",
            "memory",
            "self_monitoring",
        ],

        limitations=[
            "finite_resources",
            "representation_bias",
            "incomplete_model",
        ],

        resources=[
            "memory",
            "compute",
            "agent_swarm",
        ],

        current_method="recursive_search",
        current_cognitive_space="C_k",

        process_history_ref="process_history_v1",
    )

    relation = SelfWorldRelationModel(
        model_id="self_world_relation_v1",
        version="1.0",

        observation_channels=[
            "sensor",
            "language",
            "simulation",
        ],

        dependencies=[
            "representation",
            "observation_method",
        ],

        blind_spots=[
            "unobserved_state",
            "model-dependent_distinction",
        ],

        model_influence_on_observation=[
            "selection_of_observables",
            "interpretation_of_results",
        ],
    )

    reflection = from_frustration(
        DemoFrustration(),
        world_model=world,
        self_model=self_model,
        relation_model=relation,
    )

    print("Level 3 reflection:")
    print(reflection.to_dict())


if __name__ == "__main__":
    demo()
