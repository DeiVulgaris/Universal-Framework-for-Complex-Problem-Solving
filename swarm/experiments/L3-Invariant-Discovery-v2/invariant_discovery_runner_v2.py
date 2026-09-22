import json
from pathlib import Path
import sys


CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parents[2]

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from invariant_relation_generator_v2 import (
    Observation,
    generate_candidate_relations,
)
from invariant_candidate_evaluator_v2 import (
    evaluate_candidate,
)


EXPERIMENT_ID = "UFCPS-L3-INVARIANT-DISCOVERY-v2"
VERSION = "2.0"

DATASET_PATH = (
    CURRENT_DIR / "level3_invariant_discovery_dataset_v2.json"
)

RESULT_PATH = (
    CURRENT_DIR / "EXPERIMENT_RESULTS_v2.json"
)


def load_dataset():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def convert_observations(records):
    observations = []

    for record in records:
        observations.append(
            Observation(
                record_id=record["record_id"],
                left=record["left"],
                right=record["right"],
                result=record["result"],
            )
        )

    return observations


def get_expected_positive(record):
    evaluation = record.get("evaluation", {})
    return evaluation.get("expected_positive")


def evaluate_holdout_prediction(
    candidate,
    observation,
):
    relation = candidate.get("relation", "")

    if "result_length_matches_combined_lengths" in relation:
        return (
            len(observation.result)
            == len(observation.left)
            + len(observation.right)
        )

    if "result_equals_left_right_concat" in relation:
        return (
            observation.result
            == observation.left + observation.right
        )

    if "result_equals_right_left_concat" in relation:
        return (
            observation.result
            == observation.right + observation.left
        )

    return None


def candidate_to_dict(candidate):
    return {
        "candidate_id": candidate.candidate_id,
        "relation_type": candidate.relation_type,
        "relation": candidate.relation,
        "support": list(candidate.support),
        "challenge": list(candidate.challenge),
        "evidence": list(candidate.evidence),
    }


def select_candidate(evaluations):
    viable = []

    for evaluation in evaluations:
        if (
            evaluation.status == "CANDIDATE"
            and evaluation.training_support
            and evaluation.training_challenges
        ):
            viable.append(evaluation)

    if len(viable) == 1:
        return viable[0], "SINGLE_VIABLE_CANDIDATE"

    if len(viable) == 0:
        return None, "NO_VIABLE_CANDIDATE"

    return None, "MULTIPLE_VIABLE_CANDIDATES"


def evaluate_frozen_candidate(
    candidate,
    holdout_observations,
    holdout_records,
):
    predictions = []
    correct = 0
    evaluated = 0

    expected_by_id = {
        record["record_id"]: get_expected_positive(record)
        for record in holdout_records
    }

    for observation in holdout_observations:
        prediction = evaluate_holdout_prediction(
            candidate,
            observation,
        )

        expected = expected_by_id.get(
            observation.record_id
        )

        match = (
            prediction is not None
            and expected is not None
            and prediction == expected
        )

        if prediction is not None and expected is not None:
            evaluated += 1

            if match:
                correct += 1

        predictions.append(
            {
                "record_id": observation.record_id,
                "prediction": prediction,
                "expected_positive": expected,
                "correct": match,
            }
        )

    return {
        "predictions": predictions,
        "evaluated": evaluated,
        "correct": correct,
        "all_correct": (
            evaluated == len(holdout_observations)
            and evaluated > 0
            and correct == evaluated
        ),
    }


def run_experiment():
    dataset = load_dataset()

    dataset_id = dataset.get(
        "dataset_id",
        "UNKNOWN",
    )

    dataset_version = dataset.get(
        "version",
        "UNKNOWN",
    )

    train_records = dataset.get("train", [])
    control_records = dataset.get("controls", [])
    holdout_records = dataset.get("holdout", [])

    if not train_records:
        raise ValueError("Training set is empty.")

    if not control_records:
        raise ValueError("Control set is empty.")

    if not holdout_records:
        raise ValueError("Holdout set is empty.")

    training_observations = convert_observations(
        train_records
    )

    control_observations = convert_observations(
        control_records
    )

    holdout_observations = convert_observations(
        holdout_records
    )

    discovery_observations = (
        training_observations
        + control_observations
    )

    generated_candidates = generate_candidate_relations(
        discovery_observations
    )

    candidate_dicts = [
        candidate_to_dict(candidate)
        for candidate in generated_candidates
    ]

    evaluations = []

    for candidate in candidate_dicts:
        evaluation = evaluate_candidate(
            candidate,
            training_observations,
            control_observations,
        )

        evaluations.append(evaluation)

    selected_evaluation, selection_status = select_candidate(
        evaluations
    )

    result = {
        "experiment_id": EXPERIMENT_ID,
        "version": VERSION,
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "predefined_candidate_family_used": False,
        "semantic_labels_exposed_to_engine": False,
        "holdout_used_during_discovery": False,
        "discovery_observation_count": len(
            discovery_observations
        ),
        "training_observation_count": len(
            training_observations
        ),
        "control_observation_count": len(
            control_observations
        ),
        "holdout_observation_count": len(
            holdout_observations
        ),
        "generated_candidate_count": len(
            candidate_dicts
        ),
        "generated_candidates": candidate_dicts,
        "candidate_evaluations": [
            {
                "candidate_id": evaluation.candidate_id,
                "status": evaluation.status,
                "training_support": list(
                    evaluation.training_support
                ),
                "training_challenges": list(
                    evaluation.training_challenges
                ),
                "explanation": evaluation.explanation,
            }
            for evaluation in evaluations
        ],
        "selection_status": selection_status,
        "frozen_candidate": None,
        "holdout_evaluation": None,
        "status": "UNRESOLVED",
        "unresolved_questions": [],
    }

    if selected_evaluation is None:
        if selection_status == "NO_VIABLE_CANDIDATE":
            result["status"] = "UNRESOLVED"
            result["unresolved_questions"].append(
                "No generated candidate simultaneously "
                "explained training observations and "
                "was challenged by controls."
            )

        elif selection_status == "MULTIPLE_VIABLE_CANDIDATES":
            result["status"] = "UNRESOLVED"
            result["unresolved_questions"].append(
                "Multiple viable candidates remain after "
                "training/control evaluation."
            )

    else:
        frozen_candidate = None

        for candidate in candidate_dicts:
            if (
                candidate["candidate_id"]
                == selected_evaluation.candidate_id
            ):
                frozen_candidate = candidate
                break

        result["frozen_candidate"] = {
            "candidate_id": selected_evaluation.candidate_id,
            "relation": frozen_candidate["relation"],
            "support": frozen_candidate["support"],
            "challenge": frozen_candidate["challenge"],
            "frozen": True,
        }

        holdout_result = evaluate_frozen_candidate(
            frozen_candidate,
            holdout_observations,
            holdout_records,
        )

        result["holdout_evaluation"] = holdout_result

        if holdout_result["all_correct"]:
            result["status"] = "PASS"
        else:
            result["status"] = "FAIL"

    with RESULT_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            result,
            handle,
            ensure_ascii=False,
            indent=2,
        )

    print("UFCPS — L3 Invariant Discovery Runner v2")
    print("=" * 72)
    print(f"experiment: {EXPERIMENT_ID}")
    print(f"dataset: {dataset_id}")
    print(f"dataset_version: {dataset_version}")
    print()
    print(
        "predefined_candidate_family_used:",
        result["predefined_candidate_family_used"],
    )
    print(
        "semantic_labels_exposed_to_engine:",
        result["semantic_labels_exposed_to_engine"],
    )
    print(
        "holdout_used_during_discovery:",
        result["holdout_used_during_discovery"],
    )
    print()
    print(
        "generated_candidate_count:",
        result["generated_candidate_count"],
    )
    print(
        "selection_status:",
        result["selection_status"],
    )

    if result["frozen_candidate"] is not None:
        print(
            "frozen_candidate:",
            result["frozen_candidate"]["candidate_id"],
        )
        print(
            "frozen:",
            result["frozen_candidate"]["frozen"],
        )

    if result["holdout_evaluation"] is not None:
        print(
            "holdout_evaluated:",
            result["holdout_evaluation"]["evaluated"],
        )
        print(
            "holdout_correct:",
            result["holdout_evaluation"]["correct"],
        )
        print(
            "holdout_all_correct:",
            result["holdout_evaluation"]["all_correct"],
        )

    print()
    print("STATUS:", result["status"])
    print()
    print(
        "RESULT FILE:",
        str(RESULT_PATH),
    )
    print("=" * 72)

    if result["status"] == "PASS":
        print("RESULT: PASS")
        return 0

    if result["status"] == "FAIL":
        print("RESULT: FAIL")
        return 1

    print("RESULT: UNRESOLVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_experiment())
