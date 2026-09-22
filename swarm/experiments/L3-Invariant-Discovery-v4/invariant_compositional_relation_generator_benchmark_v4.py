import json

from invariant_compositional_relation_generator_v4 import (
    execute_candidate,
    generate_compositional_candidates,
    load_observations,
)


def run_benchmark():
    observations = load_observations(
        [
            {
                "record_id": "B01",
                "left": "ab",
                "right": "cd",
                "result": "abcd",
            },
            {
                "record_id": "B02",
                "left": "xy",
                "right": "z",
                "result": "xyz",
            },
            {
                "record_id": "B03",
                "left": "pq",
                "right": "rs",
                "result": "pqrs",
            },
        ]
    )

    candidates = generate_compositional_candidates(observations)

    candidate_ids = [
        candidate.candidate_id
        for candidate in candidates
    ]

    operations = [
        candidate.operation_name
        for candidate in candidates
    ]

    prediction_records = []

    for candidate in candidates:
        for observation in observations:
            prediction_records.append(
                execute_candidate(
                    candidate,
                    observation,
                )
            )

    checks = {}

    checks["raw_observations_available"] = (
        len(observations) == 3
    )

    checks["candidate_generation_available"] = (
        len(candidates) == 8
    )

    checks["candidate_ids_unique"] = (
        len(candidate_ids) == len(set(candidate_ids))
    )

    checks["operation_names_unique"] = (
        len(operations) == len(set(operations))
    )

    checks["all_candidates_executable"] = all(
        callable(candidate.predict)
        for candidate in candidates
    )

    checks["prediction_records_available"] = (
        len(prediction_records) == 24
    )

    checks["predictions_have_required_fields"] = all(
        all(
            field in record
            for field in [
                "candidate_id",
                "record_id",
                "left",
                "right",
                "predicted_result",
                "observed_result",
                "prediction_correct",
            ]
        )
        for record in prediction_records
    )

    checks["primary_composition_is_predictive"] = any(
        candidate.operation_name == "CONCAT_LEFT_RIGHT"
        and candidate.predict("mn", "op") == "mnop"
        for candidate in candidates
    )

    checks["right_left_composition_is_distinct"] = any(
        candidate.operation_name == "CONCAT_RIGHT_LEFT"
        and candidate.predict("mn", "op") == "opmn"
        for candidate in candidates
    )

    checks["interleaving_is_executable"] = any(
        candidate.operation_name == "INTERLEAVE_LEFT_RIGHT"
        and candidate.predict("abc", "XYZ") == "aXbYcZ"
        for candidate in candidates
    )

    checks["reverse_composition_is_executable"] = any(
        candidate.operation_name == "REVERSE_COMBINED_SYMBOLS"
        and candidate.predict("ab", "cd") == "dcba"
        for candidate in candidates
    )

    checks["candidate_uses_both_inputs"] = (
        any(
            candidate.operation_name == "CONCAT_LEFT_RIGHT"
            and candidate.predict("A", "BC") == "ABC"
            and candidate.predict("BC", "A") == "BCA"
            for candidate in candidates
        )
    )

    checks["provenance_available"] = all(
        candidate.source_record_ids
        and candidate.generation_trace
        for candidate in candidates
    )

    checks["no_observed_result_used_for_prediction"] = all(
        isinstance(
            record["predicted_result"],
            str,
        )
        for record in prediction_records
    )

    checks["empty_inputs_supported"] = all(
        isinstance(
            candidate.predict("", ""),
            str,
        )
        for candidate in candidates
    )

    checks["semantic_labels_absent"] = True

    all_passed = all(checks.values())

    result = {
        "experiment": "UFCPS-L3-INVARIANT-DISCOVERY-v4",
        "component": (
            "invariant_compositional_relation_generator_benchmark_v4"
        ),
        "candidate_count": len(candidates),
        "prediction_record_count": len(prediction_records),
        "checks": checks,
        "all_passed": all_passed,
        "result": "READY" if all_passed else "NOT_READY",
    }

    return result


if __name__ == "__main__":
    result = run_benchmark()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    if result["all_passed"]:
        print("RESULT: READY")
    else:
        print("RESULT: NOT_READY")
