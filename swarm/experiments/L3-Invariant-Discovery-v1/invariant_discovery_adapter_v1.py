```python
"""
UFCPS — Level 3 Invariant Discovery Adapter v1

Experiment:
    L3-Invariant-Discovery-v1

Purpose:
    Bridge raw symbolic observations into the existing Level 3
    reflexive/emergent machinery without exposing semantic domain labels.

Important methodological constraint:
    This adapter does NOT know about arithmetic, numbers, numeral systems,
    addition, notation, or any historical/semantic interpretation of the
    observations.

It exposes only structural properties of the raw records.

Input expected by the experiment runner:
    [
        {
            "record_id": "...",
            "left": "...",
            "right": "...",
            "result": "..."
        },
        ...
    ]

Output:
    A process-compatible dictionary containing:
        - status
        - candidate_invariant
        - training_support
        - training_challenges
        - control_predictions
        - holdout_predictions
        - unresolved_questions

The adapter deliberately treats the discovered relation as a structural
hypothesis. External evaluation remains responsible for deciding whether
that hypothesis matches the hidden oracle.

This is an experimental adapter, not a claim of general invariant discovery.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence


EXPERIMENT_ID = "L3-Invariant-Discovery-v1"
ADAPTER_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Structural observation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StructuralObservation:
    record_id: str
    left: str
    right: str
    result: str

    left_length: int
    right_length: int
    result_length: int

    operands_equal: bool
    concatenation_matches: bool
    length_sum_matches: bool


def _as_text(value: Any) -> str:
    """
    Convert a raw observation value to text without assigning semantic
    meaning to the value.
    """
    return str(value)


def _build_structural_observation(
    record: Dict[str, Any],
) -> StructuralObservation:
    left = _as_text(record["left"])
    right = _as_text(record["right"])
    result = _as_text(record["result"])

    left_length = len(left)
    right_length = len(right)
    result_length = len(result)

    return StructuralObservation(
        record_id=str(record["record_id"]),
        left=left,
        right=right,
        result=result,
        left_length=left_length,
        right_length=right_length,
        result_length=result_length,
        operands_equal=(left == right),
        concatenation_matches=(result == left + right),
        length_sum_matches=(
            result_length == left_length + right_length
        ),
    )


# ---------------------------------------------------------------------------
# Structural relation candidates
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RelationCandidate:
    name: str
    description: str
    evaluator: str


RELATION_CANDIDATES: Sequence[RelationCandidate] = (
    RelationCandidate(
        name="RESULT_LENGTH_EQUALS_OPERAND_LENGTH_SUM",
        description=(
            "The length of the result equals the sum of the lengths "
            "of the two operands."
        ),
        evaluator="result_length == left_length + right_length",
    ),
    RelationCandidate(
        name="RESULT_EQUALS_LITERAL_CONCATENATION",
        description=(
            "The result string equals the literal concatenation "
            "of the two operand strings."
        ),
        evaluator="result == left + right",
    ),
)


# ---------------------------------------------------------------------------
# Candidate assessment
# ---------------------------------------------------------------------------


def _assess_candidate(
    candidate: RelationCandidate,
    observations: Sequence[StructuralObservation],
) -> Dict[str, Any]:
    supported: List[str] = []
    contradicted: List[str] = []

    for observation in observations:
        if candidate.name == (
            "RESULT_LENGTH_EQUALS_OPERAND_LENGTH_SUM"
        ):
            holds = observation.length_sum_matches

        elif candidate.name == (
            "RESULT_EQUALS_LITERAL_CONCATENATION"
        ):
            holds = observation.concatenation_matches

        else:
            holds = False

        if holds:
            supported.append(observation.record_id)
        else:
            contradicted.append(observation.record_id)

    return {
        "candidate": candidate,
        "supported": supported,
        "contradicted": contradicted,
    }


def _select_candidate(
    observations: Sequence[StructuralObservation],
) -> Dict[str, Any] | None:
    """
    Select the structural hypothesis with the strongest discrimination
    between observations that satisfy and violate the relation.

    No semantic interpretation is used here.
    """
    assessments = [
        _assess_candidate(candidate, observations)
        for candidate in RELATION_CANDIDATES
    ]

    viable = [
        assessment
        for assessment in assessments
        if assessment["supported"]
        and assessment["contradicted"]
    ]

    if not viable:
        return None

    viable.sort(
        key=lambda item: (
            len(item["supported"]),
            -len(item["contradicted"]),
        ),
        reverse=True,
    )

    return viable[0]


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------


def _predict(
    candidate: RelationCandidate,
    observation: StructuralObservation,
) -> bool:
    if candidate.name == (
        "RESULT_LENGTH_EQUALS_OPERAND_LENGTH_SUM"
    ):
        return observation.length_sum_matches

    if candidate.name == (
        "RESULT_EQUALS_LITERAL_CONCATENATION"
    ):
        return observation.concatenation_matches

    return False


def _prediction_record(
    candidate: RelationCandidate,
    observation: StructuralObservation,
) -> Dict[str, Any]:
    return {
        "record_id": observation.record_id,
        "prediction": _predict(candidate, observation),
    }


# ---------------------------------------------------------------------------
# Level 3 bridge
# ---------------------------------------------------------------------------


def _run_level3_bridge(
    observations: Sequence[StructuralObservation],
) -> Dict[str, Any]:
    """
    Run the existing Level 3 machinery as a structural process layer.

    The current Level 3 implementation provides:
        - branch diversity,
        - interaction,
        - emergent distinctions,
        - candidate invariants,
        - unresolved questions.

    It does not yet perform domain-independent hypothesis induction itself.
    Therefore the bridge records its output separately from the structural
    hypothesis mechanism above.

    This separation is intentional and scientifically important.
    """

    try:
        from swarm.level3_emergent_integration_v1 import (
            Level3IntegrationEngine,
        )
    except ImportError:
        try:
            from level3_emergent_integration_v1 import (
                Level3IntegrationEngine,
            )
        except ImportError as exc:
            return {
                "available": False,
                "error": str(exc),
            }

    try:
        engine = Level3IntegrationEngine()

        result = engine.run(
            source_space_id="L3-INVARIANT-DISCOVERY",
            source_space_version=1,
        )

        return {
            "available": True,
            "source_space": result.source_space,
            "branch_count": result.exploration_branch_count,
            "interaction_status": result.interaction.status.value,
            "emergent_distinction_count": len(
                result.interaction.emergent_distinctions
            ),
            "candidate_invariant_count": len(
                result.interaction.candidate_invariants
            ),
            "question_count": len(
                result.generated_question_ids
            ),
            "continuation_ready": result.continuation_ready,
            "process_terminated": result.process_terminated,
        }

    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Public adapter API
# ---------------------------------------------------------------------------


def discover_invariant(
    discovery_input: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Main adapter entry point.

    The runner supplies training observations and controls only.

    The adapter:
        1. receives raw symbolic records;
        2. extracts structural properties;
        3. searches a small predefined family of structural relations;
        4. runs the existing Level 3 process bridge;
        5. returns a candidate plus evidence and unresolved questions.

    No semantic domain labels are accepted or required.
    """

    records = list(discovery_input)

    observations = [
        _build_structural_observation(record)
        for record in records
    ]

    if not observations:
        return {
            "status": "UNRESOLVED",
            "candidate_invariant": None,
            "training_support": [],
            "training_challenges": [],
            "control_predictions": [],
            "holdout_predictions": [],
            "unresolved_questions": [
                "No observations were supplied."
            ],
        }

    selected = _select_candidate(observations)

    level3 = _run_level3_bridge(observations)

    if selected is None:
        return {
            "status": "UNRESOLVED",
            "candidate_invariant": None,
            "training_support": [],
            "training_challenges": [],
            "control_predictions": [],
            "holdout_predictions": [],
            "unresolved_questions": [
                (
                    "No structural relation in the current candidate "
                    "family simultaneously explains supported and "
                    "contradictory observations."
                ),
                (
                    "The Level 3 bridge did not yield a domain-specific "
                    "invariant by itself."
                ),
            ],
            "level3_trace": level3,
        }

    candidate: RelationCandidate = selected["candidate"]

    support = list(selected["supported"])
    challenges = list(selected["contradicted"])

    predictions = [
        _prediction_record(candidate, observation)
        for observation in observations
    ]

    unresolved_questions = [
        (
            "Does the candidate remain preserved under a new symbolic "
            "representation?"
        ),
        (
            "Does the candidate generalize to observations whose "
            "surface form was not present during discovery?"
        ),
        (
            "Can an alternative structural relation explain the same "
            "observations?"
        ),
        (
            "Can the candidate survive transformations of the observed "
            "symbol structures?"
        ),
        (
            "Can the Level 3 process generate the candidate without "
            "a predefined candidate relation family?"
        ),
    ]

    return {
        "status": "CANDIDATE",
        "candidate_invariant": {
            "name": candidate.name,
            "description": candidate.description,
            "evaluator": candidate.evaluator,
            "supporting_observations": support,
            "challenging_observations": challenges,
        },
        "training_support": support,
        "training_challenges": challenges,
        "control_predictions": predictions,
        "holdout_predictions": [],
        "unresolved_questions": unresolved_questions,
        "level3_trace": level3,
        "adapter_version": ADAPTER_VERSION,
    }


# ---------------------------------------------------------------------------
# Frozen-candidate evaluation
# ---------------------------------------------------------------------------


def evaluate_frozen_candidate(
    holdout_input: Iterable[Dict[str, Any]],
    frozen_candidate: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate a previously frozen candidate on holdout observations.

    This function does NOT search for another candidate.

    That separation is required to prevent the holdout set from becoming
    part of the discovery process.
    """

    records = list(holdout_input)

    candidate_name = frozen_candidate.get("name")

    candidate = next(
        (
            item
            for item in RELATION_CANDIDATES
            if item.name == candidate_name
        ),
        None,
    )

    if candidate is None:
        return {
            "status": "UNRESOLVED",
            "predictions": [],
            "unresolved_questions": [
                "Frozen candidate is not recognized by this adapter."
            ],
        }

    observations = [
        _build_structural_observation(record)
        for record in records
    ]

    predictions = [
        _prediction_record(candidate, observation)
        for observation in observations
    ]

    return {
        "status": "EVALUATED",
        "predictions": predictions,
        "candidate_invariant": {
            "name": candidate.name,
            "description": candidate.description,
            "evaluator": candidate.evaluator,
        },
    }


# ---------------------------------------------------------------------------
# Compatibility aliases
# ---------------------------------------------------------------------------


def run_discovery(
    discovery_input: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    return discover_invariant(discovery_input)


def run_holdout(
    holdout_input: Iterable[Dict[str, Any]],
    frozen_candidate: Dict[str, Any],
) -> Dict[str, Any]:
    return evaluate_frozen_candidate(
        holdout_input,
        frozen_candidate,
    )


# ---------------------------------------------------------------------------
# Local smoke test
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    sample = [
        {
            "record_id": "S01",
            "left": "aa",
            "right": "aa",
            "result": "aaaa",
        },
        {
            "record_id": "S02",
            "left": "••",
            "right": "••",
            "result": "••••",
        },
        {
            "record_id": "S03",
            "left": "II",
            "right": "II",
            "result": "IV",
        },
        {
            "record_id": "S04",
            "left": "xx",
            "right": "xx",
            "result": "xxxxx",
        },
    ]

    discovery = discover_invariant(sample)

    print("UFCPS — L3 Invariant Discovery Adapter v1")
    print("=" * 72)
    print(f"experiment: {EXPERIMENT_ID}")
    print(f"adapter_version: {ADAPTER_VERSION}")
    print(f"status: {discovery['status']}")
    print(
        "candidate:",
        discovery["candidate_invariant"],
    )
    print(
        "training_support:",
        discovery["training_support"],
    )
    print(
        "training_challenges:",
        discovery["training_challenges"],
    )
    print(
        "unresolved_questions:",
        len(discovery["unresolved_questions"]),
    )
    print(
        "level3_bridge:",
        discovery.get("level3_trace"),
    )
```
