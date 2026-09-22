from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple


EXPERIMENT_ID = "UFCPS-L3-INVARIANT-DISCOVERY-v2"
VERSION = "2.0"


@dataclass(frozen=True)
class Observation:
    record_id: str
    left: str
    right: str
    result: str


@dataclass(frozen=True)
class CandidateEvaluation:
    candidate_id: str
    training_support: Tuple[str, ...]
    training_challenges: Tuple[str, ...]
    holdout_predictions: Tuple[Tuple[str, bool], ...]
    status: str
    explanation: str


def evaluate_structural_candidate(
    candidate: Dict[str, Any],
    observations: Sequence[Observation],
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    relation = candidate.get("relation", "")

    if not relation:
        return (), tuple(
            observation.record_id
            for observation in observations
        )

    if "result_length_matches_combined_lengths" in relation:
        predicate = lambda observation: (
            len(observation.result)
            == len(observation.left) + len(observation.right)
        )

    elif "result_equals_left_right_concat" in relation:
        predicate = lambda observation: (
            observation.result
            == observation.left + observation.right
        )

    elif "result_equals_right_left_concat" in relation:
        predicate = lambda observation: (
            observation.result
            == observation.right + observation.left
        )

    else:
        return (), tuple(
            observation.record_id
            for observation in observations
        )

    support = []
    challenge = []

    for observation in observations:
        if predicate(observation):
            support.append(observation.record_id)
        else:
            challenge.append(observation.record_id)

    return tuple(support), tuple(challenge)


def evaluate_candidate(
    candidate: Dict[str, Any],
    training_observations: Sequence[Observation],
    holdout_observations: Sequence[Observation],
) -> CandidateEvaluation:
    candidate_id = candidate.get("candidate_id", "UNKNOWN")

    support, challenge = evaluate_structural_candidate(
        candidate,
        training_observations,
    )

    predictions = []

    relation = candidate.get("relation", "")

    for observation in holdout_observations:
        if "result_length_matches_combined_lengths" in relation:
            prediction = (
                len(observation.result)
                == len(observation.left)
                + len(observation.right)
            )

        elif "result_equals_left_right_concat" in relation:
            prediction = (
                observation.result
                == observation.left + observation.right
            )

        elif "result_equals_right_left_concat" in relation:
            prediction = (
                observation.result
                == observation.right + observation.left
            )

        else:
            prediction = False

        predictions.append(
            (observation.record_id, prediction)
        )

    if support and challenge:
        status = "CANDIDATE"
        explanation = (
            "Candidate explains at least one training observation "
            "and is contradicted by at least one training observation."
        )
    elif support:
        status = "UNRESOLVED"
        explanation = (
            "Candidate has training support but no training challenge."
        )
    else:
        status = "REJECTED"
        explanation = (
            "Candidate has no supporting training observation."
        )

    return CandidateEvaluation(
        candidate_id=candidate_id,
        training_support=support,
        training_challenges=challenge,
        holdout_predictions=tuple(predictions),
        status=status,
        explanation=explanation,
    )


def evaluate_candidate_set(
    candidates: Sequence[Dict[str, Any]],
    training_observations: Sequence[Observation],
    holdout_observations: Sequence[Observation],
) -> List[CandidateEvaluation]:
    results = []

    for candidate in candidates:
        results.append(
            evaluate_candidate(
                candidate,
                training_observations,
                holdout_observations,
            )
        )

    return results


def freeze_candidate(
    evaluation: CandidateEvaluation,
) -> Dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "version": VERSION,
        "candidate_id": evaluation.candidate_id,
        "status": evaluation.status,
        "training_support": list(
            evaluation.training_support
        ),
        "training_challenges": list(
            evaluation.training_challenges
        ),
        "holdout_predictions": [
            {
                "record_id": record_id,
                "prediction": prediction,
            }
            for record_id, prediction
            in evaluation.holdout_predictions
        ],
        "explanation": evaluation.explanation,
        "frozen": True,
    }


def smoke_test() -> Dict[str, Any]:
    training = [
        Observation("T01", "aa", "aa", "aaaa"),
        Observation("T02", "••", "••", "••••"),
        Observation("T03", "II", "II", "IV"),
        Observation("C01", "2", "2", "5"),
    ]

    holdout = [
        Observation("H01", "xxx", "xx", "xxxxx"),
        Observation("H02", "AAA", "AA", "AAAAA"),
        Observation("H03", "•••", "••", "••••"),
    ]

    candidate = {
        "candidate_id": "CAND_TEST",
        "relation_type": "STRUCTURAL_RELATION",
        "relation": "result_length_matches_combined_lengths == True",
    }

    evaluation = evaluate_candidate(
        candidate,
        training,
        holdout,
    )

    frozen = freeze_candidate(evaluation)

    assert evaluation.candidate_id == "CAND_TEST"
    assert evaluation.training_support
    assert evaluation.training_challenges
    assert evaluation.holdout_predictions
    assert frozen["frozen"] is True

    return {
        "experiment": EXPERIMENT_ID,
        "version": VERSION,
        "candidate_id": evaluation.candidate_id,
        "training_support": list(
            evaluation.training_support
        ),
        "training_challenges": list(
            evaluation.training_challenges
        ),
        "holdout_prediction_count": len(
            evaluation.holdout_predictions
        ),
        "frozen": frozen["frozen"],
        "status": "READY",
    }


if __name__ == "__main__":
    result = smoke_test()

    print("UFCPS — L3 Candidate Evaluator v2")
    print("=" * 72)
    print(f"experiment: {result['experiment']}")
    print(f"version: {result['version']}")
    print(f"candidate_id: {result['candidate_id']}")
    print(
        "training_support:",
        result["training_support"],
    )
    print(
        "training_challenges:",
        result["training_challenges"],
    )
    print(
        "holdout_prediction_count:",
        result["holdout_prediction_count"],
    )
    print("frozen:", result["frozen"])
    print(f"status: {result['status']}")
    print("=" * 72)
    print("RESULT: READY")
