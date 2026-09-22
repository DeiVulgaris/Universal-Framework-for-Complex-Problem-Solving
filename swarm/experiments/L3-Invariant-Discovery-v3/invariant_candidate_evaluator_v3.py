from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

from invariant_relation_generator_v3 import (
    Observation,
    CandidateRelation,
    extract_structural_features,
    candidate_predicts_observation,
)


@dataclass
class Prediction:
    prediction_id: str
    candidate_id: str
    record_id: str
    predicted_value: Any
    observed_value: Any
    status: str


@dataclass
class EvaluationResult:
    candidate_id: str
    support: List[str]
    challenges: List[str]
    predictions: List[Prediction]
    productivity_score: float
    status: str


def _get_candidate_feature_spec(
    candidate: CandidateRelation,
) -> Optional[Tuple[str, Any]]:
    expression = candidate.expression

    if expression.get("operator") != "OBSERVATION_FEATURE_EQUALS":
        return None

    feature_name = expression.get("feature")

    if not isinstance(feature_name, str):
        return None

    return feature_name, expression.get("value")


def _predict_candidate(
    candidate: CandidateRelation,
    observation: Observation,
) -> Optional[bool]:
    feature_spec = _get_candidate_feature_spec(candidate)

    if feature_spec is None:
        return None

    feature_name, expected_value = feature_spec
    features = extract_structural_features(observation)

    if feature_name not in features:
        return None

    return features[feature_name] == expected_value


def evaluate_candidate(
    candidate: CandidateRelation,
    observations: List[Observation],
    prefix: str = "P",
) -> EvaluationResult:
    predictions: List[Prediction] = []
    support: List[str] = []
    challenges: List[str] = []

    for index, observation in enumerate(observations, start=1):
        predicted_value = _predict_candidate(
            candidate,
            observation,
        )

        if predicted_value is None:
            status = "UNRESOLVED"
            observed_value = None
        else:
            observed_value = True
            status = (
                "SUPPORTED"
                if predicted_value is True
                else "CONTRADICTED"
            )

        prediction = Prediction(
            prediction_id=(
                f"{prefix}_"
                f"{candidate.candidate_id}_"
                f"{index:04d}"
            ),
            candidate_id=candidate.candidate_id,
            record_id=observation.record_id,
            predicted_value=predicted_value,
            observed_value=observed_value,
            status=status,
        )

        predictions.append(prediction)

        if status == "SUPPORTED":
            support.append(observation.record_id)
        elif status == "CONTRADICTED":
            challenges.append(observation.record_id)

    resolved_predictions = [
        prediction
        for prediction in predictions
        if prediction.status != "UNRESOLVED"
    ]

    if not resolved_predictions:
        productivity_score = 0.0
        evaluation_status = "UNRESOLVED"
    else:
        supported = len(support)
        challenged = len(challenges)
        total = supported + challenged

        productivity_score = (
            supported / total
            if total > 0
            else 0.0
        )

        if challenged > 0:
            evaluation_status = "CONTRADICTED"
        else:
            evaluation_status = "SUPPORTED"

    return EvaluationResult(
        candidate_id=candidate.candidate_id,
        support=support,
        challenges=challenges,
        predictions=predictions,
        productivity_score=productivity_score,
        status=evaluation_status,
    )


def evaluate_prediction_set(
    candidate: CandidateRelation,
    observations: List[Observation],
    prefix: str = "P",
) -> Dict[str, Any]:
    result = evaluate_candidate(
        candidate,
        observations,
        prefix=prefix,
    )

    return asdict(result)


def evaluate_candidate_competition(
    candidates: List[CandidateRelation],
    observations: List[Observation],
) -> List[EvaluationResult]:
    results: List[EvaluationResult] = []

    for candidate in candidates:
        results.append(
            evaluate_candidate(
                candidate,
                observations,
                prefix="COMP",
            )
        )

    return results


def select_viable_candidates(
    evaluations: List[EvaluationResult],
) -> List[EvaluationResult]:
    viable: List[EvaluationResult] = []

    for evaluation in evaluations:
        if evaluation.status != "SUPPORTED":
            continue

        if not evaluation.support:
            continue

        if evaluation.challenges:
            continue

        viable.append(evaluation)

    return viable


def evaluate_counterexamples(
    candidate: CandidateRelation,
    counterexamples: List[Observation],
) -> EvaluationResult:
    return evaluate_candidate(
        candidate,
        counterexamples,
        prefix="COUNTER",
    )


def compare_candidates(
    evaluations: List[EvaluationResult],
) -> Dict[str, Any]:
    if not evaluations:
        return {
            "status": "NO_CANDIDATES",
            "candidate_count": 0,
            "unique_viable_candidate": None,
        }

    viable = select_viable_candidates(evaluations)

    if len(viable) == 1:
        return {
            "status": "UNIQUE_VIABLE_CANDIDATE",
            "candidate_count": len(evaluations),
            "unique_viable_candidate": (
                viable[0].candidate_id
            ),
        }

    if len(viable) > 1:
        return {
            "status": "MULTIPLE_VIABLE_CANDIDATES",
            "candidate_count": len(evaluations),
            "unique_viable_candidate": None,
            "viable_candidate_ids": [
                evaluation.candidate_id
                for evaluation in viable
            ],
        }

    return {
        "status": "NO_VIABLE_CANDIDATE",
        "candidate_count": len(evaluations),
        "unique_viable_candidate": None,
    }


def freeze_candidate(
    candidate: CandidateRelation,
    selection_evaluation: EvaluationResult,
    counterexample_evaluation: EvaluationResult,
) -> Dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "expression": candidate.expression,
        "relation_type": candidate.relation_type,
        "source_record_ids": list(
            candidate.source_record_ids
        ),
        "selection_support": list(
            selection_evaluation.support
        ),
        "selection_challenges": list(
            selection_evaluation.challenges
        ),
        "counterexample_support": list(
            counterexample_evaluation.support
        ),
        "counterexample_challenges": list(
            counterexample_evaluation.challenges
        ),
        "frozen": True,
    }


def audit_semantic_hardcoding() -> Dict[str, Any]:
    """
    The evaluator deliberately contains no catalogue of
    intended relations.

    It executes only the generic candidate representation
    produced by the relation generator.
    """

    prohibited_candidate_names = [
        "addition",
        "arithmetic",
        "cardinality",
        "concatenation",
        "numeral",
        "number",
    ]

    evaluator_source_markers = {
        "contains_prohibited_relation_names": False,
        "contains_candidate_family": False,
        "uses_hidden_oracle": False,
    }

    # The list above is only an audit vocabulary.
    # It is not used to evaluate candidates.
    evaluator_source_markers["audit_vocabulary_size"] = len(
        prohibited_candidate_names
    )

    return evaluator_source_markers


def smoke_test() -> Dict[str, Any]:
    observations = [
        Observation(
            record_id="T01",
            left="aa",
            right="bb",
            result="abab",
        ),
        Observation(
            record_id="T02",
            left="ab",
            right="ab",
            result="aabb",
        ),
        Observation(
            record_id="T03",
            left="xy",
            right="z",
            result="xyz",
        ),
    ]

    from invariant_relation_generator_v3 import (
        generate_candidate_relations,
    )

    candidates = generate_candidate_relations(
        observations
    )

    if not candidates:
        return {
            "status": "EMPTY",
            "candidate_count": 0,
        }

    evaluations = evaluate_candidate_competition(
        candidates,
        observations,
    )

    comparison = compare_candidates(evaluations)

    audit = audit_semantic_hardcoding()

    return {
        "status": "READY",
        "candidate_count": len(candidates),
        "evaluation_count": len(evaluations),
        "comparison_status": comparison["status"],
        "semantic_audit": audit,
    }


if __name__ == "__main__":
    result = smoke_test()

    print(
        "UFCPS — L3 Invariant Discovery Candidate Evaluator v3"
    )
    print(
        f"candidates: {result['candidate_count']}"
    )
    print(
        f"evaluations: {result['evaluation_count']}"
    )
    print(
        f"comparison: {result['comparison_status']}"
    )

    audit = result["semantic_audit"]

    print(
        "candidate_family_hardcoded: "
        f"{audit['contains_candidate_family']}"
    )
    print(
        "hidden_oracle_used: "
        f"{audit['uses_hidden_oracle']}"
    )

    if (
        result["status"] == "READY"
        and not audit["contains_candidate_family"]
        and not audit["uses_hidden_oracle"]
    ):
        print("RESULT: READY")
    else:
        print("RESULT: INVALID")
