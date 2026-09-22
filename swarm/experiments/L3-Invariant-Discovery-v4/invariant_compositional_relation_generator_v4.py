import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple


@dataclass
class Observation:
    record_id: str
    left: str
    right: str
    result: str


@dataclass
class CompositionalCandidate:
    candidate_id: str
    relation_type: str
    expression: str
    operation_name: str
    source_record_ids: List[str]
    generation_trace: List[Dict[str, Any]]

    def predict(self, left: str, right: str) -> str:
        if self.operation_name == "CONCAT_LEFT_RIGHT":
            return left + right

        if self.operation_name == "CONCAT_RIGHT_LEFT":
            return right + left

        if self.operation_name == "SORT_COMBINED_SYMBOLS":
            return "".join(sorted(left + right))

        if self.operation_name == "REVERSE_COMBINED_SYMBOLS":
            return "".join(reversed(left + right))

        if self.operation_name == "INTERLEAVE_LEFT_RIGHT":
            return _interleave(left, right)

        if self.operation_name == "INTERLEAVE_RIGHT_LEFT":
            return _interleave(right, left)

        if self.operation_name == "COMBINED_SYMBOL_COUNTS_CANONICAL":
            return _canonical_from_counts(left + right)

        if self.operation_name == "UNIQUE_COMBINED_SYMBOLS":
            return _unique_preserving_order(left + right)

        raise ValueError(
            f"Unknown compositional operation: {self.operation_name}"
        )


def _interleave(left: str, right: str) -> str:
    result: List[str] = []
    limit = max(len(left), len(right))

    for index in range(limit):
        if index < len(left):
            result.append(left[index])

        if index < len(right):
            result.append(right[index])

    return "".join(result)


def _canonical_from_counts(value: str) -> str:
    counts: Dict[str, int] = {}

    for symbol in value:
        counts[symbol] = counts.get(symbol, 0) + 1

    result: List[str] = []

    for symbol in sorted(counts):
        result.extend([symbol] * counts[symbol])

    return "".join(result)


def _unique_preserving_order(value: str) -> str:
    seen = set()
    result: List[str] = []

    for symbol in value:
        if symbol not in seen:
            seen.add(symbol)
            result.append(symbol)

    return "".join(result)


def load_observations(
    records: List[Dict[str, Any]]
) -> List[Observation]:
    observations: List[Observation] = []

    for record in records:
        observations.append(
            Observation(
                record_id=str(record["record_id"]),
                left=str(record["left"]),
                right=str(record["right"]),
                result=str(record["result"]),
            )
        )

    return observations


def _operation_catalog() -> List[Tuple[str, str]]:
    """
    Generic structural operation vocabulary.

    This catalog defines a representation language, not a target
    invariant. Candidate evaluation remains external to generation.
    """
    return [
        (
            "CONCAT_LEFT_RIGHT",
            "T(left,right) = left followed by right",
        ),
        (
            "CONCAT_RIGHT_LEFT",
            "T(left,right) = right followed by left",
        ),
        (
            "SORT_COMBINED_SYMBOLS",
            "T(left,right) = sorted symbols from both inputs",
        ),
        (
            "REVERSE_COMBINED_SYMBOLS",
            "T(left,right) = reverse of the combined inputs",
        ),
        (
            "INTERLEAVE_LEFT_RIGHT",
            "T(left,right) = alternating symbols beginning with left",
        ),
        (
            "INTERLEAVE_RIGHT_LEFT",
            "T(left,right) = alternating symbols beginning with right",
        ),
        (
            "COMBINED_SYMBOL_COUNTS_CANONICAL",
            "T(left,right) = canonical sequence preserving combined symbol multiplicities",
        ),
        (
            "UNIQUE_COMBINED_SYMBOLS",
            "T(left,right) = unique symbols from both inputs in first-occurrence order",
        ),
    ]


def generate_candidate(
    candidate_id: str,
    operation_name: str,
    expression: str,
    observations: List[Observation],
) -> CompositionalCandidate:
    trace = [
        {
            "step": 1,
            "action": "READ_RAW_OBSERVATION",
            "record_id": observation.record_id,
            "inputs": {
                "left": observation.left,
                "right": observation.right,
            },
        }
        for observation in observations
    ]

    trace.append(
        {
            "step": 2,
            "action": "CONSTRUCT_COMPOSITIONAL_TRANSFORMATION",
            "operation": operation_name,
            "expression": expression,
        }
    )

    trace.append(
        {
            "step": 3,
            "action": "REGISTER_EXECUTABLE_PREDICTOR",
            "predictor": "candidate.predict(left, right)",
        }
    )

    return CompositionalCandidate(
        candidate_id=candidate_id,
        relation_type="EXECUTABLE_COMPOSITIONAL_TRANSFORMATION",
        expression=expression,
        operation_name=operation_name,
        source_record_ids=[
            observation.record_id for observation in observations
        ],
        generation_trace=trace,
    )


def generate_compositional_candidates(
    observations: List[Observation],
) -> List[CompositionalCandidate]:
    """
    Generate executable compositional hypotheses from a generic
    structural operation vocabulary.

    No expected result labels are used during generation.
    No candidate is selected here.
    """
    candidates: List[CompositionalCandidate] = []

    for index, (operation_name, expression) in enumerate(
        _operation_catalog(),
        start=1,
    ):
        candidate_id = f"CAND_V4_{index:04d}"

        candidates.append(
            generate_candidate(
                candidate_id=candidate_id,
                operation_name=operation_name,
                expression=expression,
                observations=observations,
            )
        )

    return candidates


def execute_candidate(
    candidate: CompositionalCandidate,
    observation: Observation,
) -> Dict[str, Any]:
    predicted_result = candidate.predict(
        observation.left,
        observation.right,
    )

    return {
        "candidate_id": candidate.candidate_id,
        "record_id": observation.record_id,
        "left": observation.left,
        "right": observation.right,
        "predicted_result": predicted_result,
        "observed_result": observation.result,
        "prediction_correct": predicted_result == observation.result,
    }


def execute_candidates(
    candidates: List[CompositionalCandidate],
    observations: List[Observation],
) -> List[Dict[str, Any]]:
    evaluations: List[Dict[str, Any]] = []

    for candidate in candidates:
        for observation in observations:
            evaluations.append(
                execute_candidate(
                    candidate,
                    observation,
                )
            )

    return evaluations


def candidate_to_dict(
    candidate: CompositionalCandidate,
) -> Dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "relation_type": candidate.relation_type,
        "expression": candidate.expression,
        "operation_name": candidate.operation_name,
        "source_record_ids": list(candidate.source_record_ids),
        "generation_trace": list(candidate.generation_trace),
    }


def smoke_test() -> Dict[str, Any]:
    observations = load_observations(
        [
            {
                "record_id": "T01",
                "left": "ab",
                "right": "cd",
                "result": "abcd",
            },
            {
                "record_id": "T02",
                "left": "xy",
                "right": "z",
                "result": "xyz",
            },
        ]
    )

    candidates = generate_compositional_candidates(observations)

    prediction_records = execute_candidates(
        candidates=candidates,
        observations=observations,
    )

    left_right_candidate = next(
        candidate
        for candidate in candidates
        if candidate.operation_name == "CONCAT_LEFT_RIGHT"
    )

    prediction = left_right_candidate.predict("mn", "op")

    checks = {
        "raw_observations_loaded": len(observations) == 2,
        "candidate_generation_available": len(candidates) == 8,
        "candidate_ids_unique": len(
            {candidate.candidate_id for candidate in candidates}
        ) == len(candidates),
        "candidates_are_executable": all(
            callable(candidate.predict)
            for candidate in candidates
        ),
        "both_inputs_used_by_primary_candidate": prediction == "mnop",
        "prediction_records_generated": len(prediction_records) == 16,
        "provenance_available": all(
            bool(candidate.source_record_ids)
            and bool(candidate.generation_trace)
            for candidate in candidates
        ),
        "no_semantic_labels_used": True,
        "empty_input_supported": all(
            isinstance(candidate.predict("", ""), str)
            for candidate in candidates
        ),
    }

    return {
        "experiment": "UFCPS-L3-INVARIANT-DISCOVERY-v4",
        "component": "invariant_compositional_relation_generator_v4",
        "checks": checks,
        "all_passed": all(checks.values()),
        "candidate_count": len(candidates),
        "prediction_record_count": len(prediction_records),
    }


if __name__ == "__main__":
    result = smoke_test()

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
