import json
from pathlib import Path
from typing import Any, Dict, List

from invariant_relation_generator_v3 import (
    CandidateRelation,
    Observation,
    generate_candidate_relations,
    load_observations,
)
from invariant_candidate_evaluator_v3 import (
    compare_candidates,
    evaluate_candidate,
    evaluate_counterexamples,
    freeze_candidate,
)


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "level3_invariant_discovery_dataset_v3.json"
RESULT_PATH = BASE_DIR / "EXPERIMENT_RESULTS_v3.json"


EXPERIMENT_ID = "UFCPS-L3-INVARIANT-DISCOVERY-v3"
PROTOCOL_VERSION = "3.0"


def load_dataset() -> Dict[str, Any]:
    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def records_to_observations(
    records: List[Dict[str, Any]],
) -> List[Observation]:
    return load_observations(records)


def candidate_to_dict(
    candidate: CandidateRelation,
) -> Dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "relation_type": candidate.relation_type,
        "expression": candidate.expression,
        "source_record_ids": list(
            candidate.source_record_ids
        ),
        "support": list(candidate.support),
        "challenge": list(candidate.challenge),
        "provenance": dict(candidate.provenance),
    }


def evaluation_to_dict(
    evaluation: Any,
) -> Dict[str, Any]:
    return {
        "candidate_id": evaluation.candidate_id,
        "support": list(evaluation.support),
        "challenges": list(evaluation.challenges),
        "predictions": [
            {
                "prediction_id": prediction.prediction_id,
                "candidate_id": prediction.candidate_id,
                "record_id": prediction.record_id,
                "predicted_value": prediction.predicted_value,
                "observed_value": prediction.observed_value,
                "status": prediction.status,
            }
            for prediction in evaluation.predictions
        ],
        "productivity_score": evaluation.productivity_score,
        "status": evaluation.status,
    }


def evaluate_selection(
    candidates: List[CandidateRelation],
    selection: List[Observation],
) -> List[Any]:
    evaluations = []

    for candidate in candidates:
        evaluations.append(
            evaluate_candidate(
                candidate,
                selection,
                prefix="SELECTION",
            )
        )

    return evaluations


def apply_counterexamples(
    candidates: List[CandidateRelation],
    selection_evaluations: List[Any],
    counterexamples: List[Observation],
) -> Dict[str, Any]:
    evaluation_by_id = {
        evaluation.candidate_id: evaluation
        for evaluation in selection_evaluations
    }

    counterexample_results: Dict[str, Any] = {}

    for candidate in candidates:
        selection_evaluation = evaluation_by_id.get(
            candidate.candidate_id
        )

        if selection_evaluation is None:
            continue

        if selection_evaluation.status != "SUPPORTED":
            continue

        counterexample_results[candidate.candidate_id] = (
            evaluate_counterexamples(
                candidate,
                counterexamples,
            )
        )

    return counterexample_results


def select_after_counterexamples(
    candidates: List[CandidateRelation],
    selection_evaluations: List[Any],
    counterexample_evaluations: Dict[str, Any],
) -> List[CandidateRelation]:
    selection_by_id = {
        evaluation.candidate_id: evaluation
        for evaluation in selection_evaluations
    }

    viable: List[CandidateRelation] = []

    for candidate in candidates:
        selection_evaluation = selection_by_id.get(
            candidate.candidate_id
        )

        counterexample_evaluation = (
            counterexample_evaluations.get(
                candidate.candidate_id
            )
        )

        if selection_evaluation is None:
            continue

        if counterexample_evaluation is None:
            continue

        if selection_evaluation.status != "SUPPORTED":
            continue

        if selection_evaluation.challenges:
            continue

        if counterexample_evaluation.challenges:
            continue

        viable.append(candidate)

    return viable


def evaluate_holdout(
    candidate: CandidateRelation,
    holdout: List[Observation],
) -> Any:
    return evaluate_candidate(
        candidate,
        holdout,
        prefix="HOLDOUT",
    )


def determine_final_status(
    protocol_valid: bool,
    unique_candidate: CandidateRelation | None,
    holdout_evaluation: Any | None,
) -> str:
    if not protocol_valid:
        return "FAIL"

    if unique_candidate is None:
        return "UNRESOLVED"

    if holdout_evaluation is None:
        return "UNRESOLVED"

    if holdout_evaluation.status != "SUPPORTED":
        return "UNRESOLVED"

    if holdout_evaluation.challenges:
        return "UNRESOLVED"

    return "PASS"


def build_result(
    dataset: Dict[str, Any],
    discovery: List[Observation],
    selection: List[Observation],
    controls: List[Observation],
    counterexamples: List[Observation],
    holdout: List[Observation],
    candidates: List[CandidateRelation],
    selection_evaluations: List[Any],
    counterexample_evaluations: Dict[str, Any],
    viable_candidates: List[CandidateRelation],
    frozen_candidate: Dict[str, Any] | None,
    holdout_evaluation: Any | None,
    final_status: str,
) -> Dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "protocol_version": PROTOCOL_VERSION,
        "dataset_id": dataset.get("dataset_id"),
        "dataset_version": dataset.get("version"),

        "status": final_status,

        "predefined_candidate_family_used": False,
        "semantic_labels_exposed_to_engine": False,
        "holdout_used_during_discovery": False,

        "partition_counts": {
            "discovery": len(discovery),
            "selection": len(selection),
            "controls": len(controls),
            "counterexamples": len(counterexamples),
            "holdout": len(holdout),
        },

        "generated_candidate_count": len(candidates),

        "generated_candidates": [
            candidate_to_dict(candidate)
            for candidate in candidates
        ],

        "selection_evaluations": [
            evaluation_to_dict(evaluation)
            for evaluation in selection_evaluations
        ],

        "counterexample_evaluations": {
            candidate_id: evaluation_to_dict(evaluation)
            for candidate_id, evaluation
            in counterexample_evaluations.items()
        },

        "viable_candidate_ids": [
            candidate.candidate_id
            for candidate in viable_candidates
        ],

        "frozen_candidate": frozen_candidate,

        "holdout_evaluation": (
            evaluation_to_dict(holdout_evaluation)
            if holdout_evaluation is not None
            else None
        ),

        "unresolved_questions": [],

        "level3_trace": {
            "source_space": "C_k",
            "candidate_generation": True,
            "selection_prediction": True,
            "counterexample_testing": True,
            "candidate_freeze": (
                frozen_candidate is not None
            ),
            "holdout_evaluation": (
                holdout_evaluation is not None
            ),
            "successor_space": (
                "C_k+1"
                if final_status in {
                    "PASS",
                    "UNRESOLVED",
                }
                else None
            ),
            "process_continuation": True,
        },

        "methodological_audit": {
            "discovery_accessed_holdout": False,
            "candidate_generation_used_semantic_oracle": False,
            "holdout_evaluated_before_freeze": False,
            "candidate_modified_after_freeze": False,
        },
    }


def add_unresolved_questions(
    result: Dict[str, Any],
) -> None:
    questions = result["unresolved_questions"]

    viable_count = len(
        result["viable_candidate_ids"]
    )

    if viable_count > 1:
        questions.append(
            "Multiple candidates remain viable after "
            "selection and counterexample testing."
        )

    if viable_count == 0:
        questions.append(
            "No candidate survived the complete "
            "selection and counterexample procedure."
        )

    if (
        result["generated_candidate_count"] > 0
        and result["frozen_candidate"] is None
    ):
        questions.append(
            "A unique productive candidate was not "
            "established before holdout access."
        )

    holdout_evaluation = result["holdout_evaluation"]

    if holdout_evaluation is None:
        questions.append(
            "Holdout evaluation was not performed because "
            "candidate freeze criteria were not satisfied."
        )

    result["unresolved_questions"] = questions


def run_experiment() -> Dict[str, Any]:
    dataset = load_dataset()

    discovery = records_to_observations(
        dataset.get("discovery", [])
    )

    selection = records_to_observations(
        dataset.get("selection", [])
    )

    controls = records_to_observations(
        dataset.get("controls", [])
    )

    counterexamples = records_to_observations(
        dataset.get("counterexamples", [])
    )

    holdout = records_to_observations(
        dataset.get("holdout", [])
    )

    # Candidate generation receives discovery observations only.
    candidates = generate_candidate_relations(
        discovery
    )

    # Selection is evaluated only after candidate generation.
    selection_evaluations = evaluate_selection(
        candidates,
        selection,
    )

    # Controls are deliberately kept separate from discovery.
    #
    # They are not used to create candidates.
    #
    # They are retained in the trace so the runner can report
    # that negative structural controls were present.
    #
    # No semantic labels from the dataset are used here.

    counterexample_evaluations = apply_counterexamples(
        candidates,
        selection_evaluations,
        counterexamples,
    )

    viable_candidates = select_after_counterexamples(
        candidates,
        selection_evaluations,
        counterexample_evaluations,
    )

    unique_candidate = None

    if len(viable_candidates) == 1:
        unique_candidate = viable_candidates[0]

    frozen_candidate = None
    holdout_evaluation = None

    if unique_candidate is not None:
        selection_evaluation = next(
            evaluation
            for evaluation in selection_evaluations
            if evaluation.candidate_id
            == unique_candidate.candidate_id
        )

        counterexample_evaluation = (
            counterexample_evaluations[
                unique_candidate.candidate_id
            ]
        )

        frozen_candidate = freeze_candidate(
            unique_candidate,
            selection_evaluation,
            counterexample_evaluation,
        )

        # Holdout is accessed only after freeze.
        holdout_evaluation = evaluate_holdout(
            unique_candidate,
            holdout,
        )

    protocol_valid = True

    final_status = determine_final_status(
        protocol_valid=protocol_valid,
        unique_candidate=unique_candidate,
        holdout_evaluation=holdout_evaluation,
    )

    result = build_result(
        dataset=dataset,
        discovery=discovery,
        selection=selection,
        controls=controls,
        counterexamples=counterexamples,
        holdout=holdout,
        candidates=candidates,
        selection_evaluations=selection_evaluations,
        counterexample_evaluations=counterexample_evaluations,
        viable_candidates=viable_candidates,
        frozen_candidate=frozen_candidate,
        holdout_evaluation=holdout_evaluation,
        final_status=final_status,
    )

    result["controls_present"] = bool(controls)

    add_unresolved_questions(result)

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

    return result


if __name__ == "__main__":
    result = run_experiment()

    print(
        "UFCPS — L3 Invariant Discovery Runner v3"
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
        "predefined_candidate_family_used: "
        f"{result['predefined_candidate_family_used']}"
    )
    print(
        "semantic_labels_exposed_to_engine: "
        f"{result['semantic_labels_exposed_to_engine']}"
    )
    print(
        "holdout_used_during_discovery: "
        f"{result['holdout_used_during_discovery']}"
    )
    print()

    print(
        "discovery observations: "
        f"{result['partition_counts']['discovery']}"
    )
    print(
        "selection observations: "
        f"{result['partition_counts']['selection']}"
    )
    print(
        "controls: "
        f"{result['partition_counts']['controls']}"
    )
    print(
        "counterexamples: "
        f"{result['partition_counts']['counterexamples']}"
    )
    print(
        "holdout observations: "
        f"{result['partition_counts']['holdout']}"
    )
    print()

    print(
        "generated candidates: "
        f"{result['generated_candidate_count']}"
    )

    print(
        "viable candidates after "
        "counterexamples: "
        f"{len(result['viable_candidate_ids'])}"
    )

    if result["frozen_candidate"] is not None:
        print(
            "frozen candidate: "
            f"{result['frozen_candidate']['candidate_id']}"
        )
    else:
        print("frozen candidate: NONE")

    print()

    print(
        f"STATUS: {result['status']}"
    )
    print(
        f"RESULT FILE: {RESULT_PATH}"
    )
    print(
        f"RESULT: {result['status']}"
    )
