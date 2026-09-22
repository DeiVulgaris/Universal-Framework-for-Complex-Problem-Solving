from dataclasses import dataclass, asdict
from collections import Counter
from typing import Any, Dict, List, Tuple


@dataclass
class Observation:
    record_id: str
    left: str
    right: str
    result: str


@dataclass
class StructuralRelation:
    relation_id: str
    relation_type: str
    expression: Dict[str, Any]
    source_record_ids: List[str]


@dataclass
class CandidateRelation:
    candidate_id: str
    relation_type: str
    expression: Dict[str, Any]
    source_record_ids: List[str]
    support: List[str]
    challenge: List[str]
    provenance: Dict[str, Any]


def load_observations(records: List[Dict[str, Any]]) -> List[Observation]:
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


def symbol_counts(value: str) -> Dict[str, int]:
    return dict(sorted(Counter(value).items()))


def ordered_runs(value: str) -> List[Tuple[str, int]]:
    if not value:
        return []

    runs: List[Tuple[str, int]] = []
    current = value[0]
    count = 1

    for symbol in value[1:]:
        if symbol == current:
            count += 1
        else:
            runs.append((current, count))
            current = symbol
            count = 1

    runs.append((current, count))
    return runs


def multiset_union(
    left_counts: Dict[str, int],
    right_counts: Dict[str, int],
) -> Dict[str, int]:
    result = Counter(left_counts)
    result.update(right_counts)
    return dict(sorted(result.items()))


def extract_structural_features(
    observation: Observation,
) -> Dict[str, Any]:
    left_counts = symbol_counts(observation.left)
    right_counts = symbol_counts(observation.right)
    result_counts = symbol_counts(observation.result)

    combined_counts = multiset_union(left_counts, right_counts)

    left_set = sorted(set(observation.left))
    right_set = sorted(set(observation.right))
    result_set = sorted(set(observation.result))
    combined_set = sorted(set(observation.left + observation.right))

    return {
        "record_id": observation.record_id,

        "left": observation.left,
        "right": observation.right,
        "result": observation.result,

        "left_length": len(observation.left),
        "right_length": len(observation.right),
        "result_length": len(observation.result),

        "combined_length": (
            len(observation.left) + len(observation.right)
        ),

        "length_difference": (
            len(observation.result)
            - len(observation.left)
            - len(observation.right)
        ),

        "left_equals_right": observation.left == observation.right,
        "left_equals_result": observation.left == observation.result,
        "right_equals_result": observation.right == observation.result,

        "left_set": left_set,
        "right_set": right_set,
        "result_set": result_set,
        "combined_set": combined_set,

        "left_unique_count": len(left_set),
        "right_unique_count": len(right_set),
        "result_unique_count": len(result_set),
        "combined_unique_count": len(combined_set),

        "left_counts": left_counts,
        "right_counts": right_counts,
        "result_counts": result_counts,
        "combined_counts": combined_counts,

        "result_matches_combined_counts": (
            result_counts == combined_counts
        ),

        "result_set_matches_combined_set": (
            result_set == combined_set
        ),

        "result_length_matches_combined_length": (
            len(observation.result)
            == len(observation.left) + len(observation.right)
        ),

        "result_matches_left_right_concat": (
            observation.result
            == observation.left + observation.right
        ),

        "result_matches_right_left_concat": (
            observation.result
            == observation.right + observation.left
        ),

        "left_prefix_of_result": (
            observation.result.startswith(observation.left)
        ),

        "right_prefix_of_result": (
            observation.result.startswith(observation.right)
        ),

        "left_suffix_of_result": (
            observation.result.endswith(observation.left)
        ),

        "right_suffix_of_result": (
            observation.result.endswith(observation.right)
        ),

        "left_runs": ordered_runs(observation.left),
        "right_runs": ordered_runs(observation.right),
        "result_runs": ordered_runs(observation.result),

        "result_equals_sorted_operands": (
            "".join(sorted(observation.left + observation.right))
            == observation.result
        ),

        "result_equals_reverse_sorted_operands": (
            "".join(sorted(observation.left + observation.right, reverse=True))
            == observation.result
        ),
    }


def build_neutral_relation(
    feature_name: str,
    feature_value: Any,
) -> Dict[str, Any]:
    return {
        "feature": feature_name,
        "value": feature_value,
    }


def generate_observation_relations(
    observation: Observation,
) -> List[StructuralRelation]:
    features = extract_structural_features(observation)

    relations: List[StructuralRelation] = []

    for feature_name, feature_value in features.items():
        if feature_name == "record_id":
            continue

        relation_id = (
            f"{observation.record_id}:"
            f"{feature_name}"
        )

        relations.append(
            StructuralRelation(
                relation_id=relation_id,
                relation_type="OBSERVATION_FEATURE",
                expression=build_neutral_relation(
                    feature_name,
                    feature_value,
                ),
                source_record_ids=[observation.record_id],
            )
        )

    return relations


def generate_cross_record_relations(
    observations: List[Observation],
) -> List[StructuralRelation]:
    feature_maps = {
        observation.record_id: extract_structural_features(observation)
        for observation in observations
    }

    relations: List[StructuralRelation] = []

    if not observations:
        return relations

    feature_names = [
        name
        for name in feature_maps[observations[0].record_id].keys()
        if name != "record_id"
    ]

    for feature_name in feature_names:
        groups: Dict[str, List[str]] = {}

        for observation in observations:
            value = feature_maps[observation.record_id][feature_name]
            key = repr(value)

            groups.setdefault(key, []).append(
                observation.record_id
            )

        for value_key, record_ids in groups.items():
            if len(record_ids) < 2:
                continue

            value = feature_maps[record_ids[0]][feature_name]

            relations.append(
                StructuralRelation(
                    relation_id=(
                        f"CROSS:{feature_name}:{value_key}"
                    ),
                    relation_type="CROSS_RECORD_REGULARITY",
                    expression=build_neutral_relation(
                        feature_name,
                        value,
                    ),
                    source_record_ids=record_ids,
                )
            )

    return relations


def generate_pairwise_relations(
    observations: List[Observation],
) -> List[StructuralRelation]:
    relations: List[StructuralRelation] = []

    for index, left_observation in enumerate(observations):
        left_features = extract_structural_features(left_observation)

        for right_observation in observations[index + 1:]:
            right_features = extract_structural_features(
                right_observation
            )

            common_features: Dict[str, Any] = {}

            for feature_name in left_features:
                if feature_name == "record_id":
                    continue

                if (
                    left_features[feature_name]
                    == right_features[feature_name]
                ):
                    common_features[feature_name] = (
                        left_features[feature_name]
                    )

            if not common_features:
                continue

            relations.append(
                StructuralRelation(
                    relation_id=(
                        f"PAIR:"
                        f"{left_observation.record_id}:"
                        f"{right_observation.record_id}"
                    ),
                    relation_type="PAIRWISE_STRUCTURAL_SIMILARITY",
                    expression={
                        "common_features": common_features,
                    },
                    source_record_ids=[
                        left_observation.record_id,
                        right_observation.record_id,
                    ],
                )
            )

    return relations


def build_relation_inventory(
    observations: List[Observation],
) -> Dict[str, List[Dict[str, Any]]]:
    inventory: Dict[str, List[Dict[str, Any]]] = {
        "observation_relations": [],
        "cross_record_relations": [],
        "pairwise_relations": [],
    }

    for relation in [
        relation
        for observation in observations
        for relation in generate_observation_relations(observation)
    ]:
        inventory["observation_relations"].append(
            asdict(relation)
        )

    for relation in generate_cross_record_relations(observations):
        inventory["cross_record_relations"].append(
            asdict(relation)
        )

    for relation in generate_pairwise_relations(observations):
        inventory["pairwise_relations"].append(
            asdict(relation)
        )

    return inventory


def generate_candidate_relations(
    observations: List[Observation],
) -> List[CandidateRelation]:
    feature_maps = {
        observation.record_id: extract_structural_features(observation)
        for observation in observations
    }

    candidates: List[CandidateRelation] = []
    candidate_index = 1

    if not observations:
        return candidates

    feature_names = [
        name
        for name in feature_maps[observations[0].record_id].keys()
        if name != "record_id"
    ]

    for feature_name in feature_names:
        groups: Dict[str, List[str]] = {}

        for observation in observations:
            value = feature_maps[observation.record_id][feature_name]
            groups.setdefault(repr(value), []).append(
                observation.record_id
            )

        for value_key, record_ids in groups.items():
            if len(record_ids) < 2:
                continue

            value = feature_maps[record_ids[0]][feature_name]

            candidates.append(
                CandidateRelation(
                    candidate_id=f"CAND_V3_{candidate_index:04d}",
                    relation_type="STRUCTURAL_FEATURE_REGULARITY",
                    expression={
                        "operator": "OBSERVATION_FEATURE_EQUALS",
                        "feature": feature_name,
                        "value": value,
                    },
                    source_record_ids=list(record_ids),
                    support=list(record_ids),
                    challenge=[],
                    provenance={
                        "generation_method": (
                            "recurring_neutral_structural_feature"
                        ),
                        "source_feature": feature_name,
                        "candidate_family_supplied": False,
                    },
                )
            )

            candidate_index += 1

    return candidates


def candidate_predicts_observation(
    candidate: CandidateRelation,
    observation: Observation,
) -> bool:
    expression = candidate.expression

    if expression.get("operator") != "OBSERVATION_FEATURE_EQUALS":
        return False

    feature_name = expression.get("feature")

    features = extract_structural_features(observation)

    if feature_name not in features:
        return False

    return features[feature_name] == expression.get("value")


def candidate_to_dict(
    candidate: CandidateRelation,
) -> Dict[str, Any]:
    return asdict(candidate)


def smoke_test() -> Dict[str, Any]:
    observations = load_observations(
        [
            {
                "record_id": "T01",
                "left": "aa",
                "right": "bb",
                "result": "abab",
            },
            {
                "record_id": "T02",
                "left": "ab",
                "right": "ab",
                "result": "aabb",
            },
            {
                "record_id": "T03",
                "left": "xy",
                "right": "z",
                "result": "xyz",
            },
        ]
    )

    inventory = build_relation_inventory(observations)
    candidates = generate_candidate_relations(observations)

    return {
        "observation_count": len(observations),
        "observation_relation_count": len(
            inventory["observation_relations"]
        ),
        "cross_record_relation_count": len(
            inventory["cross_record_relations"]
        ),
        "pairwise_relation_count": len(
            inventory["pairwise_relations"]
        ),
        "candidate_count": len(candidates),
        "first_candidate": (
            candidate_to_dict(candidates[0])
            if candidates
            else None
        ),
    }


if __name__ == "__main__":
    result = smoke_test()

    print(
        "UFCPS — L3 Invariant Discovery Relation Generator v3"
    )
    print(f"observations: {result['observation_count']}")
    print(
        "observation_relations: "
        f"{result['observation_relation_count']}"
    )
    print(
        "cross_record_relations: "
        f"{result['cross_record_relation_count']}"
    )
    print(
        "pairwise_relations: "
        f"{result['pairwise_relation_count']}"
    )
    print(f"candidates: {result['candidate_count']}")

    if result["candidate_count"] > 0:
        print("RESULT: READY")
    else:
        print("RESULT: EMPTY")
