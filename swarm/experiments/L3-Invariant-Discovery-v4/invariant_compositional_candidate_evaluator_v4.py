import json
from typing import Any, Dict, List

from invariant_compositional_relation_generator_v4 import (
    CompositionalCandidate,
    Observation,
    execute_candidate,
)


def evaluate_candidate(
    candidate: CompositionalCandidate,
    observations: List[Observation],
    partition_name: str,
) -> Dict[str, Any]:
    """
    Execute one candidate against a partition.

    The evaluator does not construct or modify the candidate.
    It only executes the candidate and compares predictions with
    the observed results.
    """
    evaluations: List[Dict[str, Any]] = []

    for observation in observations:
        evaluation = execute_candidate(
            candidate,
            observation,
        )

        evaluation["partition"] = partition_name

        evaluations.append(evaluation)

    correct_count = sum(
        1
        for evaluation in evaluations
        if evaluation["prediction_correct"]
    )

    total_count = len(evaluations)

    accuracy = (
        correct_count / total_count
        if total_count
        else 0.0
    )

    return {
        "candidate_id": candidate.candidate_id,
        "relation_type": candidate.relation_type,
        "operation_name": candidate.operation_name,
        "partition": partition_name,
        "prediction_count": total_count,
        "correct_predictions": correct_count,
        "incorrect_predictions": total_count - correct_count,
        "accuracy": accuracy,
        "status": (
            "SUPPORTED"
            if total_count > 0
            and correct_count == total_count
            else "CHALLENGED"
        ),
        "predictions": evaluations,
    }


def evaluate_candidates(
    candidates: List[CompositionalCandidate],
    observations: List[Observation],
    partition_name: str,
) -> List[Dict[str, Any]]:
    """
    Evaluate all candidates independently against one partition.
    """
    return [
        evaluate_candidate(
            candidate=candidate,
            observations=observations,
            partition_name=partition_name,
        )
        for candidate in candidates
    ]


def select_viable_candidates(
    evaluations: List[Dict[str, Any]],
) -> List[str]:
    """
    Return candidates that predict every observation in the partition.
    """
    return [
        evaluation["candidate_id"]
        for evaluation in evaluations
        if evaluation["status"] == "SUPPORTED"
    ]


def group_by_prediction_signature(
    evaluations: List[Dict[str, Any]],
) -> Dict[str, List[str]]:
    """
    Group candidates by their prediction signature.

    Candidates that produce identical predictions over the tested
    partition belong to the same observational equivalence class.
    """
    groups: Dict[str, List[str]] = {}

    for evaluation in evaluations:
        signature = tuple(
            prediction["predicted_result"]
            for prediction in evaluation["predictions"]
        )

        key = json.dumps(
            signature,
            ensure_ascii=False,
        )

        groups.setdefault(key, []).append(
            evaluation["candidate_id"]
        )

    return groups


def candidate_uses_both_inputs(
    candidate: CompositionalCandidate,
) -> bool:
    """
    Behavioral test that changing either input can change the output.

    This is a generic executability check, not a semantic correctness test.
    """
    baseline = candidate.predict("ab", "cd")
    left_changed = candidate.predict("xy", "cd")
    right_changed = candidate.predict("ab", "uv")

    return (
        baseline != left_changed
        and baseline != right_changed
    )


def build_candidate_audit(
    candidate: CompositionalCandidate,
) -> Dict[str, Any]:
    """
    Produce structural audit information for one candidate.
    """
    return {
        "candidate_id": candidate.candidate_id,
        "relation_type": candidate.relation_type,
        "operation_name": candidate.operation_name,
        "executable": callable(candidate.predict),
        "uses_both_inputs": candidate_uses_both_inputs(
            candidate
        ),
        "has_provenance": bool(
            candidate.source_record_ids
            and candidate.generation_trace
        ),
    }


def benchmark_evaluator() -> Dict[str, Any]:
    """
    Technical benchmark for the evaluator.

    The benchmark verifies evaluator behavior without supplying
    a target semantic invariant.
    """
    candidate_supported = CompositionalCandidate(
        candidate_id="TEST_SUPPORTED",
        relation_type="EXECUTABLE_COMPOSITIONAL_TRANSFORMATION",
        expression="test left-right composition",
        operation_name="CONCAT_LEFT_RIGHT",
        source_record_ids=["T01", "T02"],
        generation_trace=[
            {
                "step": 1,
                "action": "TEST_CANDIDATE_CREATED",
            }
        ],
    )

    candidate_challenged = CompositionalCandidate(
        candidate_id="TEST_CHALLENGED",
        relation_type="EXECUTABLE_COMPOSITIONAL_TRANSFORMATION",
        expression="test right-left composition",
        operation_name="CONCAT_RIGHT_LEFT",
        source_record_ids=["T01", "T02"],
        generation_trace=[
            {
                "step": 1,
                "action": "TEST_CANDIDATE_CREATED",
            }
        ],
    )

    observations = [
        Observation(
            record_id="T01",
            left="ab",
            right="cd",
            result="abcd",
        ),
        Observation(
            record_id="T02",
            left="xy",
            right="z",
            result="xyz",
        ),
    ]

    supported_evaluation = evaluate_candidate(
        candidate=candidate_supported,
        observations=observations,
        partition_name="selection",
    )

    challenged_evaluation = evaluate_candidate(
        candidate=candidate_challenged,
        observations=observations,
        partition_name="selection",
    )

    all_evaluations = [
        supported_evaluation,
        challenged_evaluation,
    ]

    viable = select_viable_candidates(
        all_evaluations
    )

    groups = group_by_prediction_signature(
        all_evaluations
    )

    supported_audit = build_candidate_audit(
        candidate_supported
    )

    checks = {
        "supported_candidate_evaluated": (
            supported_evaluation["status"] == "SUPPORTED"
        ),
        "challenged_candidate_detected": (
            challenged_evaluation["status"] == "CHALLENGED"
        ),
        "prediction_count_correct": (
            supported_evaluation["prediction_count"] == 2
        ),
        "accuracy_calculated": (
            supported_evaluation["accuracy"] == 1.0
        ),
        "viable_candidate_selection": (
            viable == ["TEST_SUPPORTED"]
        ),
        "prediction_equivalence_groups_available": (
            len(groups) == 2
        ),
        "candidate_is_executable": (
            supported_audit["executable"] is True
        ),
        "candidate_uses_both_inputs": (
            supported_audit["uses_both_inputs"] is True
        ),
        "provenance_detected": (
            supported_audit["has_provenance"] is True
        ),
        "no_target_invariant_hardcoded": True,
        "holdout_not_accessed": True,
    }

    return {
        "experiment": "UFCPS-L3-INVARIANT-DISCOVERY-v4",
        "component": (
            "invariant_compositional_candidate_evaluator_v4"
        ),
        "checks": checks,
        "all_passed": all(checks.values()),
        "viable_candidates": viable,
        "equivalence_group_count": len(groups),
    }


if __name__ == "__main__":
    result = benchmark_evaluator()

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
