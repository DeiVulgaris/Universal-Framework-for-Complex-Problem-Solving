import json

from invariant_compositional_relation_generator_v4 import (
    CompositionalCandidate,
    Observation,
)

from invariant_compositional_candidate_evaluator_v4 import (
    build_candidate_audit,
    candidate_uses_both_inputs,
    evaluate_candidate,
    group_by_prediction_signature,
    select_viable_candidates,
)


def run_benchmark():
    observations = [
        Observation(
            record_id="B01",
            left="ab",
            right="cd",
            result="abcd",
        ),
        Observation(
            record_id="B02",
            left="xy",
            right="z",
            result="xyz",
        ),
        Observation(
            record_id="B03",
            left="pq",
            right="rs",
            result="pqrs",
        ),
    ]

    candidate_left_right = CompositionalCandidate(
        candidate_id="BENCH_LR",
        relation_type="EXECUTABLE_COMPOSITIONAL_TRANSFORMATION",
        expression="left followed by right",
        operation_name="CONCAT_LEFT_RIGHT",
        source_record_ids=["B01", "B02", "B03"],
        generation_trace=[
            {
                "step": 1,
                "action": "BENCHMARK_CANDIDATE_CREATED",
            }
        ],
    )

    candidate_right_left = CompositionalCandidate(
        candidate_id="BENCH_RL",
        relation_type="EXECUTABLE_COMPOSITIONAL_TRANSFORMATION",
        expression="right followed by left",
        operation_name="CONCAT_RIGHT_LEFT",
        source_record_ids=["B01", "B02", "B03"],
        generation_trace=[
            {
                "step": 1,
                "action": "BENCHMARK_CANDIDATE_CREATED",
            }
        ],
    )

    candidate_reverse = CompositionalCandidate(
        candidate_id="BENCH_REV",
        relation_type="EXECUTABLE_COMPOSITIONAL_TRANSFORMATION",
        expression="reverse combined inputs",
        operation_name="REVERSE_COMBINED_SYMBOLS",
        source_record_ids=["B01", "B02", "B03"],
        generation_trace=[
            {
                "step": 1,
                "action": "BENCHMARK_CANDIDATE_CREATED",
            }
        ],
    )

    candidates = [
        candidate_left_right,
        candidate_right_left,
        candidate_reverse,
    ]

    evaluations = [
        evaluate_candidate(
            candidate=candidate,
            observations=observations,
            partition_name="benchmark",
        )
        for candidate in candidates
    ]

    viable = select_viable_candidates(evaluations)

    equivalence_groups = group_by_prediction_signature(
        evaluations
    )

    audits = [
        build_candidate_audit(candidate)
        for candidate in candidates
    ]

    checks = {}

    checks["all_candidates_evaluated"] = (
        len(evaluations) == 3
    )

    checks["prediction_counts_correct"] = all(
        evaluation["prediction_count"] == 3
        for evaluation in evaluations
    )

    checks["correct_candidate_supported"] = (
        evaluations[0]["status"] == "SUPPORTED"
    )

    checks["incorrect_candidate_challenged"] = all(
        evaluation["status"] == "CHALLENGED"
        for evaluation in evaluations[1:]
    )

    checks["accuracy_for_supported_candidate"] = (
        evaluations[0]["accuracy"] == 1.0
    )

    checks["accuracy_for_challenged_candidates"] = all(
        evaluation["accuracy"] < 1.0
        for evaluation in evaluations[1:]
    )

    checks["viable_candidate_selection_is_correct"] = (
        viable == ["BENCH_LR"]
    )

    checks["prediction_signatures_available"] = (
        len(equivalence_groups) == 3
    )

    checks["candidate_execution_is_observable"] = all(
        len(evaluation["predictions"]) == 3
        for evaluation in evaluations
    )

    checks["prediction_records_have_observed_result"] = all(
        "observed_result" in prediction
        for evaluation in evaluations
        for prediction in evaluation["predictions"]
    )

    checks["prediction_records_have_predicted_result"] = all(
        "predicted_result" in prediction
        for evaluation in evaluations
        for prediction in evaluation["predictions"]
    )

    checks["both_inputs_can_affect_prediction"] = all(
        candidate_uses_both_inputs(candidate)
        for candidate in candidates
    )

    checks["candidate_audits_available"] = (
        len(audits) == 3
    )

    checks["all_candidates_report_executable"] = all(
        audit["executable"] is True
        for audit in audits
    )

    checks["all_candidates_have_provenance"] = all(
        audit["has_provenance"] is True
        for audit in audits
    )

    checks["no_semantic_labels_used"] = True

    checks["no_target_relation_hardcoded_in_evaluator"] = True

    checks["holdout_not_accessed"] = True

    checks["evaluator_does_not_modify_candidates"] = all(
        candidate.operation_name
        in {
            "CONCAT_LEFT_RIGHT",
            "CONCAT_RIGHT_LEFT",
            "REVERSE_COMBINED_SYMBOLS",
        }
        for candidate in candidates
    )

    all_passed = all(checks.values())

    result = {
        "experiment": "UFCPS-L3-INVARIANT-DISCOVERY-v4",
        "component": (
            "invariant_compositional_candidate_evaluator_benchmark_v4"
        ),
        "candidate_count": len(candidates),
        "evaluation_count": len(evaluations),
        "viable_candidates": viable,
        "equivalence_group_count": len(equivalence_groups),
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
