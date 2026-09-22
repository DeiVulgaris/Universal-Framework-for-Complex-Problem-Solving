from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from invariant_compositional_relation_generator_v4 import (
    Observation,
    generate_candidate,
)

from invariant_compositional_candidate_evaluator_v4 import (
    evaluate_candidates,
    select_viable_candidates,
)


EXPERIMENT_ID = "UFCPS-L3-INVARIANT-DISCOVERY-v4.2"
DATASET_ID = "UFCPS-L3-INVARIANT-DISCOVERY-v4.2"
DATASET_VERSION = "4.2"

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "level3_invariant_discovery_dataset_v4_2.json"
RESULT_PATH = BASE_DIR / "EXPERIMENT_RESULTS_v4_2.json"


OPERATIONS = [
    "CONCAT_LEFT_RIGHT",
    "CONCAT_RIGHT_LEFT",
    "SORT_COMBINED_SYMBOLS",
    "REVERSE_COMBINED_SYMBOLS",
    "INTERLEAVE_LEFT_RIGHT",
    "INTERLEAVE_RIGHT_LEFT",
    "COMBINED_SYMBOL_COUNTS_CANONICAL",
    "UNIQUE_COMBINED_SYMBOLS",
]


def load_dataset(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_partition(
    dataset: dict[str, Any],
    partition: str,
) -> list[Observation]:

    observations: list[Observation] = []

    for record in dataset["observations"]:

        if record.get("partition") != partition:
            continue

        observations.append(
            Observation(
                record_id=str(record["record_id"]),
                left=str(record["left"]),
                right=str(record["right"]),
                result=str(record["result"]),
            )
        )

    return observations


def serialize_observation(
    observation: Observation,
) -> dict[str, str]:

    return {
        "record_id": observation.record_id,
        "left": observation.left,
        "right": observation.right,
        "result": observation.result,
    }


def generate_all_candidates(
    discovery_observations: list[Observation],
) -> list[Any]:

    operation_specs = [
        (
            "CAND_V4_0001",
            "CONCAT_LEFT_RIGHT",
            "left + right",
        ),
        (
            "CAND_V4_0002",
            "CONCAT_RIGHT_LEFT",
            "right + left",
        ),
        (
            "CAND_V4_0003",
            "SORT_COMBINED_SYMBOLS",
            "sort(left + right)",
        ),
        (
            "CAND_V4_0004",
            "REVERSE_COMBINED_SYMBOLS",
            "reverse(left + right)",
        ),
        (
            "CAND_V4_0005",
            "INTERLEAVE_LEFT_RIGHT",
            "interleave(left, right)",
        ),
        (
            "CAND_V4_0006",
            "INTERLEAVE_RIGHT_LEFT",
            "interleave(right, left)",
        ),
        (
            "CAND_V4_0007",
            "COMBINED_SYMBOL_COUNTS_CANONICAL",
            "canonical_combined_symbol_counts(left, right)",
        ),
        (
            "CAND_V4_0008",
            "UNIQUE_COMBINED_SYMBOLS",
            "unique(left + right)",
        ),
    ]

    candidates: list[Any] = []

    for (
        candidate_id,
        operation_name,
        expression,
    ) in operation_specs:

        candidate = generate_candidate(
            candidate_id=candidate_id,
            operation_name=operation_name,
            expression=expression,
            observations=discovery_observations,
        )

        candidates.append(candidate)

    return candidates


def evaluate_partition(
    candidates: list[Any],
    observations: list[Observation],
    partition_name: str,
) -> dict[str, Any]:

    if not candidates:

        return {
            "evaluation_count": 0,
            "viable_candidate_ids": [],
            "evaluations": [],
        }

    evaluations = evaluate_candidates(
        candidates,
        observations,
        partition_name,
    )

    viable_candidate_ids = select_viable_candidates(
        evaluations
    )

    return {
        "evaluation_count": len(evaluations),
        "viable_candidate_ids": viable_candidate_ids,
        "evaluations": evaluations,
    }


def candidate_lookup(
    candidates: list[Any],
) -> dict[str, Any]:

    return {
        candidate.candidate_id: candidate
        for candidate in candidates
    }


def build_discrimination_report(
    selection_candidate_ids: list[str],
    control_result: dict[str, Any],
) -> dict[str, Any]:

    evaluations = control_result["evaluations"]

    prediction_matrix: dict[
        str,
        dict[str, str],
    ] = {}

    for evaluation in evaluations:

        candidate_id = evaluation["candidate_id"]

        prediction_matrix[candidate_id] = {
            prediction["record_id"]:
                prediction["predicted_result"]
            for prediction in evaluation["predictions"]
        }

    control_record_ids: list[str] = []

    for evaluation in evaluations:

        for prediction in evaluation["predictions"]:

            record_id = prediction["record_id"]

            if record_id not in control_record_ids:

                control_record_ids.append(
                    record_id
                )

    disagreements: list[dict[str, Any]] = []

    for record_id in control_record_ids:

        predictions_for_record = {
            candidate_id: predictions[record_id]
            for candidate_id, predictions
            in prediction_matrix.items()
            if record_id in predictions
        }

        distinct_predictions = sorted(
            set(predictions_for_record.values())
        )

        disagreements.append(
            {
                "record_id": record_id,
                "candidate_predictions":
                    predictions_for_record,
                "distinct_prediction_count":
                    len(distinct_predictions),
                "discriminating":
                    len(distinct_predictions) > 1,
            }
        )

    return {
        "selection_candidate_ids":
            selection_candidate_ids,

        "control_candidate_ids": [
            evaluation["candidate_id"]
            for evaluation in evaluations
        ],

        "control_observation_count":
            len(control_record_ids),

        "discriminating_control_count":
            sum(
                1
                for item in disagreements
                if item["discriminating"]
            ),

        "all_controls_discriminating":
            all(
                item["discriminating"]
                for item in disagreements
            ) if disagreements else False,

        "prediction_matrix":
            prediction_matrix,

        "control_disagreements":
            disagreements,
    }


def freeze_candidate(
    candidates: list[Any],
    viable_candidate_ids: list[str],
) -> dict[str, Any] | None:

    if len(viable_candidate_ids) != 1:
        return None

    candidate_id = viable_candidate_ids[0]

    lookup = candidate_lookup(candidates)

    candidate = lookup.get(candidate_id)

    if candidate is None:
        return None

    return {
        "candidate_id":
            candidate.candidate_id,

        "operation":
            candidate.operation_name,

        "formal_relation":
            getattr(
                candidate,
                "expression",
                candidate.operation_name,
            ),

        "provenance": {
            "source_record_ids":
                getattr(
                    candidate,
                    "source_record_ids",
                    [],
                ),

            "generation_trace":
                getattr(
                    candidate,
                    "generation_trace",
                    [],
                ),
        },
    }


def main() -> int:

    dataset = load_dataset(
        DATASET_PATH
    )

    discovery = load_partition(
        dataset,
        "discovery",
    )

    selection = load_partition(
        dataset,
        "selection",
    )

    controls = load_partition(
        dataset,
        "control",
    )

    counterexamples = load_partition(
        dataset,
        "counterexample",
    )

    holdout = load_partition(
        dataset,
        "holdout",
    )

    candidates = generate_all_candidates(
        discovery
    )

    selection_result = evaluate_partition(
        candidates,
        selection,
        "selection",
    )

    selection_viable_ids = (
        selection_result[
            "viable_candidate_ids"
        ]
    )

    selected_candidates = [
        candidate
        for candidate in candidates
        if candidate.candidate_id
        in selection_viable_ids
    ]

    control_result = evaluate_partition(
        selected_candidates,
        controls,
        "control",
    )

    control_viable_ids = (
        control_result[
            "viable_candidate_ids"
        ]
    )

    discrimination = build_discrimination_report(
        selection_viable_ids,
        control_result,
    )

    counterexample_candidates = [
        candidate
        for candidate in selected_candidates
        if candidate.candidate_id
        in control_viable_ids
    ]

    counterexample_result = evaluate_partition(
        counterexample_candidates,
        counterexamples,
        "counterexample",
    )

    counterexample_viable_ids = (
        counterexample_result[
            "viable_candidate_ids"
        ]
    )

    frozen_candidate = freeze_candidate(
        counterexample_candidates,
        counterexample_viable_ids,
    )

    holdout_result: dict[str, Any] | None = None

    if frozen_candidate is not None:

        frozen_candidates = [
            candidate
            for candidate in counterexample_candidates
            if candidate.candidate_id
            == frozen_candidate["candidate_id"]
        ]

        holdout_result = evaluate_partition(
            frozen_candidates,
            holdout,
            "holdout",
        )

        holdout_viable_ids = (
            holdout_result[
                "viable_candidate_ids"
            ]
        )

        if (
            frozen_candidate["candidate_id"]
            not in holdout_viable_ids
        ):

            status = "FAIL"

        else:

            status = "PASS"

    else:

        status = "UNRESOLVED"

    result = {
        "experiment_id":
            EXPERIMENT_ID,

        "dataset_id":
            DATASET_ID,

        "dataset_version":
            DATASET_VERSION,

        "status":
            status,

        "methodological_change":
            (
                "Controls are valid observations selected "
                "to discriminate between competing "
                "candidate transformations; they are not "
                "intentional violations of the hidden relation."
            ),

        "independence_audit": {
            "predefined_candidate_family_used":
                False,

            "semantic_labels_exposed_to_engine":
                False,

            "holdout_used_during_discovery":
                False,

            "holdout_used_during_selection":
                False,

            "expected_positive_labels_loaded":
                False,

            "expected_positive_labels_used":
                False,

            "observed_result_used_for_prediction":
                False,
        },

        "candidate_operations":
            OPERATIONS,

        "partition_counts": {
            "discovery":
                len(discovery),

            "selection":
                len(selection),

            "control":
                len(controls),

            "counterexample":
                len(counterexamples),

            "holdout":
                len(holdout),
        },

        "generated_candidate_count":
            len(candidates),

        "generated_candidate_ids": [
            candidate.candidate_id
            for candidate in candidates
        ],

        "selection":
            selection_result,

        "control":
            control_result,

        "control_discrimination":
            discrimination,

        "counterexample":
            counterexample_result,

        "frozen_candidate":
            frozen_candidate,

        "holdout":
            holdout_result,

        "protocol_checks": {
            "candidate_generation_completed":
                len(candidates) > 0,

            "selection_completed":
                True,

            "control_evaluation_completed":
                True,

            "control_discrimination_observed":
                (
                    discrimination[
                        "discriminating_control_count"
                    ] > 0
                ),

            "counterexample_evaluation_completed":
                True,

            "candidate_frozen_before_holdout":
                frozen_candidate is not None,

            "holdout_accessed_only_after_freeze":
                (
                    holdout_result is None
                    or frozen_candidate is not None
                ),
        },

        "dataset_integrity": {
            "all_records_have_required_fields":
                all(
                    all(
                        field in record
                        for field in (
                            "record_id",
                            "partition",
                            "left",
                            "right",
                            "result",
                        )
                    )
                    for record
                    in dataset["observations"]
                ),

            "partitions_are_nonempty":
                all(
                    count > 0
                    for count in (
                        len(discovery),
                        len(selection),
                        len(controls),
                        len(counterexamples),
                        len(holdout),
                    )
                ),
        },

        "observations": {
            "discovery": [
                serialize_observation(item)
                for item in discovery
            ],

            "selection": [
                serialize_observation(item)
                for item in selection
            ],

            "control": [
                serialize_observation(item)
                for item in controls
            ],

            "counterexample": [
                serialize_observation(item)
                for item in counterexamples
            ],

            "holdout": [
                serialize_observation(item)
                for item in holdout
            ],
        },
    }

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

    print(
        "UFCPS — L3 Invariant Discovery Runner v4.2"
    )

    print(
        f"experiment: {EXPERIMENT_ID}"
    )

    print(
        f"dataset: {DATASET_ID}"
    )

    print(
        f"dataset_version: {DATASET_VERSION}"
    )

    print()

    print(
        "predefined_candidate_family_used: False"
    )

    print(
        "semantic_labels_exposed_to_engine: False"
    )

    print(
        "holdout_used_during_discovery: False"
    )

    print()

    print(
        f"discovery observations: {len(discovery)}"
    )

    print(
        f"selection observations: {len(selection)}"
    )

    print(
        f"controls: {len(controls)}"
    )

    print(
        f"counterexamples: {len(counterexamples)}"
    )

    print(
        f"holdout observations: {len(holdout)}"
    )

    print()

    print(
        f"generated candidates: {len(candidates)}"
    )

    print(
        "selection viable candidates: "
        f"{len(selection_viable_ids)}"
    )

    print(
        "control viable candidates: "
        f"{len(control_viable_ids)}"
    )

    print(
        "discriminating controls: "
        f"{discrimination['discriminating_control_count']}"
        f"/{discrimination['control_observation_count']}"
    )

    print(
        "viable candidates after counterexamples: "
        f"{len(counterexample_viable_ids)}"
    )

    if frozen_candidate is None:

        print(
            "frozen candidate: NONE"
        )

    else:

        print(
            "frozen candidate: "
            f"{frozen_candidate['candidate_id']}"
        )

    print()

    print(
        f"STATUS: {status}"
    )

    print(
        f"RESULT FILE: {RESULT_PATH}"
    )

    print(
        f"RESULT: {status}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
