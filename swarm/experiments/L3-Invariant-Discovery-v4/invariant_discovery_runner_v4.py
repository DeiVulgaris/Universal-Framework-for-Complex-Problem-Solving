import json
from pathlib import Path
from typing import Any, Dict, List

from invariant_compositional_relation_generator_v4 import (
    CompositionalCandidate,
    generate_compositional_candidates,
    load_observations,
)

from invariant_compositional_candidate_evaluator_v4 import (
    evaluate_candidate,
    group_by_prediction_signature,
    select_viable_candidates,
)


EXPERIMENT_ID = "UFCPS-L3-INVARIANT-DISCOVERY-v4"
PROTOCOL_VERSION = "4.0"
DATASET_PATH = Path("level3_invariant_discovery_dataset_v4_1.json")
RESULT_PATH = Path("EXPERIMENT_RESULTS_v4.json")


def load_raw_dataset(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_partition(
    dataset: Dict[str, Any],
    partition_name: str,
):
    """
    Load only the raw observation fields required by discovery/evaluation.

    The evaluation metadata section, including expected_positive labels,
    is deliberately ignored by the runner.
    """
    records = dataset["partitions"][partition_name]

    raw_records = [
        {
            "record_id": record["record_id"],
            "left": record["left"],
            "right": record["right"],
            "result": record["result"],
        }
        for record in records
    ]

    return load_observations(raw_records)


def evaluate_partition(
    candidates: List[CompositionalCandidate],
    observations,
    partition_name: str,
) -> List[Dict[str, Any]]:
    return [
        evaluate_candidate(
            candidate=candidate,
            observations=observations,
            partition_name=partition_name,
        )
        for candidate in candidates
    ]


def build_prediction_groups(
    evaluations: List[Dict[str, Any]],
) -> Dict[str, List[str]]:
    return group_by_prediction_signature(evaluations)


def find_candidate(
    candidates: List[CompositionalCandidate],
    candidate_id: str,
) -> CompositionalCandidate:
    for candidate in candidates:
        if candidate.candidate_id == candidate_id:
            return candidate

    raise ValueError(
        f"Candidate not found: {candidate_id}"
    )


def evaluate_frozen_candidate(
    candidate: CompositionalCandidate,
    observations,
) -> Dict[str, Any]:
    """
    Evaluate the frozen candidate on holdout observations.

    No hidden semantic labels are used. The observed result is the
    only comparison target.
    """
    predictions: List[Dict[str, Any]] = []

    for observation in observations:
        predicted_result = candidate.predict(
            observation.left,
            observation.right,
        )

        predictions.append(
            {
                "record_id": observation.record_id,
                "left": observation.left,
                "right": observation.right,
                "predicted_result": predicted_result,
                "observed_result": observation.result,
                "prediction_correct": (
                    predicted_result == observation.result
                ),
            }
        )

    correct_count = sum(
        1
        for prediction in predictions
        if prediction["prediction_correct"]
    )

    total_count = len(predictions)

    return {
        "candidate_id": candidate.candidate_id,
        "prediction_count": total_count,
        "correct_predictions": correct_count,
        "incorrect_predictions": (
            total_count - correct_count
        ),
        "accuracy": (
            correct_count / total_count
            if total_count
            else 0.0
        ),
        "all_predictions_correct": (
            total_count > 0
            and correct_count == total_count
        ),
        "predictions": predictions,
    }


def run_experiment() -> Dict[str, Any]:
    dataset = load_raw_dataset(DATASET_PATH)

    discovery_observations = load_partition(
        dataset,
        "discovery",
    )

    selection_observations = load_partition(
        dataset,
        "selection",
    )

    control_observations = load_partition(
        dataset,
        "controls",
    )

    counterexample_observations = load_partition(
        dataset,
        "counterexamples",
    )

    holdout_observations = load_partition(
        dataset,
        "holdout",
    )

    candidates = generate_compositional_candidates(
        discovery_observations
    )

    selection_evaluations = evaluate_partition(
        candidates,
        selection_observations,
        "selection",
    )

    selection_viable_ids = select_viable_candidates(
        selection_evaluations
    )

    selection_viable_candidates = [
        find_candidate(candidates, candidate_id)
        for candidate_id in selection_viable_ids
    ]

    control_evaluations = evaluate_partition(
        selection_viable_candidates,
        control_observations,
        "controls",
    )

    control_viable_ids = select_viable_candidates(
        control_evaluations
    )

    control_viable_candidates = [
        find_candidate(
            selection_viable_candidates,
            candidate_id,
        )
        for candidate_id in control_viable_ids
    ]

    counterexample_evaluations = evaluate_partition(
        control_viable_candidates,
        counterexample_observations,
        "counterexamples",
    )

    counterexample_viable_ids = select_viable_candidates(
        counterexample_evaluations
    )

    viable_candidates = [
        find_candidate(
            control_viable_candidates,
            candidate_id,
        )
        for candidate_id in counterexample_viable_ids
    ]

    equivalence_groups = build_prediction_groups(
        counterexample_evaluations
    )

    frozen_candidate = None
    freeze_status = "NO_UNIQUE_CANDIDATE"

    if len(viable_candidates) == 1:
        frozen_candidate = viable_candidates[0]
        freeze_status = "FROZEN"

    holdout_evaluation = None
    final_status = "UNRESOLVED"

    if frozen_candidate is not None:
        holdout_evaluation = evaluate_frozen_candidate(
            frozen_candidate,
            holdout_observations,
        )

        if holdout_evaluation["all_predictions_correct"]:
            final_status = "PASS"
        else:
            final_status = "FAIL"

    unresolved_questions: List[str] = []

    if len(viable_candidates) == 0:
        unresolved_questions.append(
            "No candidate survived selection, controls, and counterexamples."
        )

    if len(viable_candidates) > 1:
        unresolved_questions.append(
            "Multiple materially distinct candidates remained viable "
            "after selection, controls, and counterexample testing."
        )

    if frozen_candidate is None:
        unresolved_questions.append(
            "A unique candidate was not frozen before holdout access."
        )

    if (
        frozen_candidate is not None
        and holdout_evaluation is not None
        and not holdout_evaluation["all_predictions_correct"]
    ):
        unresolved_questions.append(
            "The frozen candidate failed at least one holdout prediction."
        )

    methodological_audit = {
        "predefined_candidate_family_used": False,
        "semantic_labels_exposed_to_engine": False,
        "holdout_used_during_discovery": False,
        "expected_positive_labels_loaded": False,
        "expected_positive_labels_used": False,
        "candidate_generated_from_discovery_observations": True,
        "candidate_execution_used_for_prediction": True,
        "candidate_freeze_before_holdout": (
            frozen_candidate is not None
        ),
        "holdout_accessed_only_after_freeze": (
            holdout_evaluation is not None
        ),
    }

    result = {
        "experiment_id": EXPERIMENT_ID,
        "protocol_version": PROTOCOL_VERSION,
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["version"],
        "status": final_status,
        "predefined_candidate_family_used": False,
        "semantic_labels_exposed_to_engine": False,
        "holdout_used_during_discovery": False,
        "partition_counts": {
            "discovery": len(discovery_observations),
            "selection": len(selection_observations),
            "controls": len(control_observations),
            "counterexamples": len(counterexample_observations),
            "holdout": len(holdout_observations),
        },
        "generated_candidate_count": len(candidates),
        "generated_candidates": [
            {
                "candidate_id": candidate.candidate_id,
                "relation_type": candidate.relation_type,
                "expression": candidate.expression,
                "operation_name": candidate.operation_name,
                "source_record_ids": (
                    candidate.source_record_ids
                ),
                "generation_trace": (
                    candidate.generation_trace
                ),
            }
            for candidate in candidates
        ],
        "selection_evaluations": selection_evaluations,
        "selection_viable_candidate_ids": selection_viable_ids,
        "control_evaluations": control_evaluations,
        "control_viable_candidate_ids": control_viable_ids,
        "counterexample_evaluations": (
            counterexample_evaluations
        ),
        "viable_candidate_ids": [
            candidate.candidate_id
            for candidate in viable_candidates
        ],
        "equivalent_candidate_groups": (
            equivalence_groups
        ),
        "freeze_status": freeze_status,
        "frozen_candidate": (
            {
                "candidate_id": frozen_candidate.candidate_id,
                "relation_type": frozen_candidate.relation_type,
                "expression": frozen_candidate.expression,
                "operation_name": frozen_candidate.operation_name,
                "source_record_ids": (
                    frozen_candidate.source_record_ids
                ),
                "generation_trace": (
                    frozen_candidate.generation_trace
                ),
            }
            if frozen_candidate is not None
            else None
        ),
        "holdout_evaluation": holdout_evaluation,
        "unresolved_questions": unresolved_questions,
        "methodological_audit": methodological_audit,
        "controls_present": True,
        "level3_trace": {
            "stage_1": "DISCOVERY",
            "stage_2": "CANDIDATE_GENERATION",
            "stage_3": "SELECTION",
            "stage_4": "CONTROLS",
            "stage_5": "COUNTEREXAMPLES",
            "stage_6": "CANDIDATE_FREEZE",
            "stage_7": "HOLDOUT",
            "process_continuity": True,
        },
    }

    return result


def write_result(result: Dict[str, Any]) -> None:
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


def main() -> None:
    result = run_experiment()

    write_result(result)

    print(
        "UFCPS — L3 Invariant Discovery Runner v4"
    )
    print(
        f"experiment: {result['experiment_id']}"
    )
    print(
        f"dataset: {result['dataset_id']}"
    )
    print(
        f"dataset_version: {result['dataset_version']}"
    )
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

    counts = result["partition_counts"]

    print(
        "discovery observations:",
        counts["discovery"],
    )

    print(
        "selection observations:",
        counts["selection"],
    )

    print(
        "controls:",
        counts["controls"],
    )

    print(
        "counterexamples:",
        counts["counterexamples"],
    )

    print(
        "holdout observations:",
        counts["holdout"],
    )

    print()

    print(
        "generated candidates:",
        result["generated_candidate_count"],
    )

    print(
        "selection viable candidates:",
        len(
            result["selection_viable_candidate_ids"]
        ),
    )

    print(
        "control viable candidates:",
        len(
            result["control_viable_candidate_ids"]
        ),
    )

    print(
        "viable candidates after counterexamples:",
        len(
            result["viable_candidate_ids"]
        ),
    )

    frozen = result["frozen_candidate"]

    if frozen is None:
        print("frozen candidate: NONE")
    else:
        print(
            "frozen candidate:",
            frozen["candidate_id"],
        )

    print()
    print(
        "STATUS:",
        result["status"],
    )
    print(
        "RESULT FILE:",
        RESULT_PATH.resolve(),
    )
    print(
        "RESULT:",
        result["status"],
    )


if __name__ == "__main__":
    main()
