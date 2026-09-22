from dataclasses import asdict

from invariant_candidate_evaluator_v3 import (
    Prediction,
    audit_semantic_hardcoding,
    compare_candidates,
    evaluate_candidate,
    evaluate_candidate_competition,
    evaluate_counterexamples,
    freeze_candidate,
    select_viable_candidates,
)
from invariant_relation_generator_v3 import (
    CandidateRelation,
    Observation,
)


def check_candidate_expression_is_executable():
    candidate = CandidateRelation(
        candidate_id="C_TEST_001",
        relation_type="STRUCTURAL_FEATURE_REGULARITY",
        expression={
            "operator": "OBSERVATION_FEATURE_EQUALS",
            "feature": "result_length",
            "value": 4,
        },
        source_record_ids=["T01"],
        support=["T01"],
        challenge=[],
        provenance={
            "generation_method": "benchmark",
            "candidate_family_supplied": False,
        },
    )

    observation = Observation(
        record_id="T01",
        left="aa",
        right="bb",
        result="abab",
    )

    result = evaluate_candidate(
        candidate,
        [observation],
    )

    return (
        result.status == "SUPPORTED"
        and result.support == ["T01"]
        and not result.challenges
    )


def check_contradiction_detection():
    candidate = CandidateRelation(
        candidate_id="C_TEST_002",
        relation_type="STRUCTURAL_FEATURE_REGULARITY",
        expression={
            "operator": "OBSERVATION_FEATURE_EQUALS",
            "feature": "result_length",
            "value": 4,
        },
        source_record_ids=["T01"],
        support=["T01"],
        challenge=[],
        provenance={
            "generation_method": "benchmark",
            "candidate_family_supplied": False,
        },
    )

    observation = Observation(
        record_id="T02",
        left="a",
        right="b",
        result="abc",
    )

    result = evaluate_candidate(
        candidate,
        [observation],
    )

    return (
        result.status == "CONTRADICTED"
        and result.challenges == ["T02"]
        and not result.support
    )


def check_multiple_candidate_competition():
    candidate_a = CandidateRelation(
        candidate_id="C_TEST_A",
        relation_type="STRUCTURAL_FEATURE_REGULARITY",
        expression={
            "operator": "OBSERVATION_FEATURE_EQUALS",
            "feature": "result_length",
            "value": 4,
        },
        source_record_ids=["T01"],
        support=["T01"],
        challenge=[],
        provenance={
            "generation_method": "benchmark",
            "candidate_family_supplied": False,
        },
    )

    candidate_b = CandidateRelation(
        candidate_id="C_TEST_B",
        relation_type="STRUCTURAL_FEATURE_REGULARITY",
        expression={
            "operator": "OBSERVATION_FEATURE_EQUALS",
            "feature": "combined_length",
            "value": 4,
        },
        source_record_ids=["T01"],
        support=["T01"],
        challenge=[],
        provenance={
            "generation_method": "benchmark",
            "candidate_family_supplied": False,
        },
    )

    observations = [
        Observation(
            record_id="T01",
            left="aa",
            right="bb",
            result="abab",
        )
    ]

    evaluations = evaluate_candidate_competition(
        [candidate_a, candidate_b],
        observations,
    )

    comparison = compare_candidates(evaluations)

    return (
        len(evaluations) == 2
        and comparison["status"] == "MULTIPLE_VIABLE_CANDIDATES"
        and comparison["unique_viable_candidate"] is None
    )


def check_counterexample_evaluation():
    candidate = CandidateRelation(
        candidate_id="C_TEST_003",
        relation_type="STRUCTURAL_FEATURE_REGULARITY",
        expression={
            "operator": "OBSERVATION_FEATURE_EQUALS",
            "feature": "result_matches_left_right_concat",
            "value": True,
        },
        source_record_ids=["T01"],
        support=["T01"],
        challenge=[],
        provenance={
            "generation_method": "benchmark",
            "candidate_family_supplied": False,
        },
    )

    counterexamples = [
        Observation(
            record_id="C01",
            left="ab",
            right="cd",
            result="acbd",
        )
    ]

    result = evaluate_counterexamples(
        candidate,
        counterexamples,
    )

    return (
        result.status == "CONTRADICTED"
        and result.challenges == ["C01"]
    )


def check_viable_selection():
    supported = CandidateRelation(
        candidate_id="C_TEST_SUPPORTED",
        relation_type="STRUCTURAL_FEATURE_REGULARITY",
        expression={
            "operator": "OBSERVATION_FEATURE_EQUALS",
            "feature": "result_length",
            "value": 4,
        },
        source_record_ids=["T01"],
        support=["T01"],
        challenge=[],
        provenance={
            "generation_method": "benchmark",
            "candidate_family_supplied": False,
        },
    )

    contradicted = CandidateRelation(
        candidate_id="C_TEST_CONTRADICTED",
        relation_type="STRUCTURAL_FEATURE_REGULARITY",
        expression={
            "operator": "OBSERVATION_FEATURE_EQUALS",
            "feature": "result_length",
            "value": 99,
        },
        source_record_ids=["T01"],
        support=["T01"],
        challenge=[],
        provenance={
            "generation_method": "benchmark",
            "candidate_family_supplied": False,
        },
    )

    observations = [
        Observation(
            record_id="T01",
            left="aa",
            right="bb",
            result="abab",
        )
    ]

    evaluations = evaluate_candidate_competition(
        [supported, contradicted],
        observations,
    )

    viable = select_viable_candidates(evaluations)

    return (
        len(viable) == 1
        and viable[0].candidate_id == "C_TEST_SUPPORTED"
    )


def check_candidate_freeze():
    candidate = CandidateRelation(
        candidate_id="C_TEST_FREEZE",
        relation_type="STRUCTURAL_FEATURE_REGULARITY",
        expression={
            "operator": "OBSERVATION_FEATURE_EQUALS",
            "feature": "result_length",
            "value": 4,
        },
        source_record_ids=["T01"],
        support=["T01"],
        challenge=[],
        provenance={
            "generation_method": "benchmark",
            "candidate_family_supplied": False,
        },
    )

    selection_observation = Observation(
        record_id="S01",
        left="aa",
        right="bb",
        result="abab",
    )

    counterexample = Observation(
        record_id="C01",
        left="a",
        right="b",
        result="ab",
    )

    selection_result = evaluate_candidate(
        candidate,
        [selection_observation],
        prefix="SELECTION",
    )

    counterexample_result = evaluate_counterexamples(
        candidate,
        [counterexample],
    )

    frozen = freeze_candidate(
        candidate,
        selection_result,
        counterexample_result,
    )

    return (
        frozen["frozen"] is True
        and frozen["candidate_id"] == "C_TEST_FREEZE"
        and frozen["expression"] == candidate.expression
        and frozen["selection_support"] == ["S01"]
        and frozen["counterexample_challenges"] == ["C01"]
    )


def check_semantic_hardcoding_audit():
    audit = audit_semantic_hardcoding()

    return (
        audit["contains_prohibited_relation_names"] is False
        and audit["contains_candidate_family"] is False
        and audit["uses_hidden_oracle"] is False
    )


def check_prediction_serialization():
    candidate = CandidateRelation(
        candidate_id="C_TEST_SERIALIZE",
        relation_type="STRUCTURAL_FEATURE_REGULARITY",
        expression={
            "operator": "OBSERVATION_FEATURE_EQUALS",
            "feature": "result_length",
            "value": 4,
        },
        source_record_ids=["T01"],
        support=["T01"],
        challenge=[],
        provenance={
            "generation_method": "benchmark",
            "candidate_family_supplied": False,
        },
    )

    observation = Observation(
        record_id="T01",
        left="aa",
        right="bb",
        result="abab",
    )

    result = evaluate_candidate(
        candidate,
        [observation],
    )

    serialized = asdict(result)

    return (
        isinstance(serialized, dict)
        and serialized["candidate_id"] == "C_TEST_SERIALIZE"
        and len(serialized["predictions"]) == 1
        and serialized["predictions"][0]["status"] == "SUPPORTED"
    )


def run_benchmark():
    checks = {
        "candidate_expression_is_executable":
            check_candidate_expression_is_executable(),

        "contradiction_detection":
            check_contradiction_detection(),

        "multiple_candidate_competition":
            check_multiple_candidate_competition(),

        "counterexample_evaluation":
            check_counterexample_evaluation(),

        "viable_candidate_selection":
            check_viable_selection(),

        "candidate_freeze":
            check_candidate_freeze(),

        "semantic_hardcoding_audit":
            check_semantic_hardcoding_audit(),

        "prediction_serialization":
            check_prediction_serialization(),
    }

    passed = sum(
        1 for value in checks.values()
        if value
    )

    total = len(checks)

    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "all_passed": passed == total,
    }


if __name__ == "__main__":
    result = run_benchmark()

    print(
        "UFCPS — L3 Invariant Discovery "
        "Candidate Evaluator Benchmark v3"
    )
    print()

    for name, passed in result["checks"].items():
        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()
    print(
        f"passed: {result['passed']}/{result['total']}"
    )
    print(
        f"all_passed: {result['all_passed']}"
    )

    if result["all_passed"]:
        print("RESULT: READY")
    else:
        print("RESULT: FAIL")
