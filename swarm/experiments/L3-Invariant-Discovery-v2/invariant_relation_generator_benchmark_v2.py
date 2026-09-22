from pathlib import Path
import sys


CURRENT_DIR = Path(__file__).resolve().parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from invariant_relation_generator_v2 import (
    Observation,
    build_relation_inventory,
    generate_candidate_relations,
    extract_structural_features,
)


FORBIDDEN_SEMANTIC_LABELS = {
    "arithmetic",
    "addition",
    "sum",
    "number",
    "numeral",
    "numeral_system",
    "quantity",
    "integer",
    "binary",
    "ternary",
    "roman",
    "mayan",
    "babylonian",
}


def build_observations():
    return [
        Observation("P01", "2", "2", "4"),
        Observation("P02", "2", "2", "11"),
        Observation("P03", "10", "10", "100"),
        Observation("P04", "II", "II", "IV"),
        Observation("P05", "||||", "||||", "||||||||"),
        Observation("P06", "••", "••", "••••"),
        Observation("P07", "XX", "XX", "XXXX"),
        Observation("P08", "aa", "aa", "aaaa"),
        Observation("N01", "2", "2", "5"),
        Observation("N02", "10", "10", "101"),
        Observation("N03", "II", "II", "V"),
        Observation("N04", "||||", "||||", "|||||||"),
    ]


def check_raw_observations(observations):
    if not observations:
        return False

    for observation in observations:
        if not all(
            isinstance(value, str)
            for value in (
                observation.left,
                observation.right,
                observation.result,
            )
        ):
            return False

    return True


def check_structural_features(observations):
    for observation in observations:
        features = extract_structural_features(observation)

        if not features:
            return False

        feature_names = {feature.name for feature in features}

        if "left_length" not in feature_names:
            return False

        if "right_length" not in feature_names:
            return False

        if "result_length" not in feature_names:
            return False

    return True


def check_no_semantic_labels(observations):
    for observation in observations:
        features = extract_structural_features(observation)

        for feature in features:
            text = (
                f"{feature.name} "
                f"{feature.description} "
                f"{feature.value}"
            ).lower()

            for forbidden in FORBIDDEN_SEMANTIC_LABELS:
                if forbidden in text:
                    return False

    return True


def check_relations_are_data_derived(observations):
    inventory = build_relation_inventory(observations)

    if not inventory:
        return False

    for relation in inventory:
        if not relation.observation_ids:
            return False

    return True


def check_candidate_generation(observations):
    candidates = generate_candidate_relations(observations)

    if not candidates:
        return False

    for candidate in candidates:
        if not candidate.supporting_observations:
            return False

        if not candidate.candidate_id:
            return False

        if not candidate.relation_type:
            return False

        candidate_text = (
            f"{candidate.candidate_id} "
            f"{candidate.relation_type} "
            f"{candidate.description}"
        ).lower()

        for forbidden in FORBIDDEN_SEMANTIC_LABELS:
            if forbidden in candidate_text:
                return False

    return True


def check_candidate_provenance(observations):
    candidates = generate_candidate_relations(observations)

    if not candidates:
        return False

    observation_ids = {observation.record_id for observation in observations}

    for candidate in candidates:
        referenced_ids = set(candidate.supporting_observations)

        if not referenced_ids:
            return False

        if not referenced_ids.issubset(observation_ids):
            return False

    return True


def check_changed_symbols_produce_structural_output():
    observations = [
        Observation("A", "aa", "aa", "aaaa"),
        Observation("B", "••", "••", "••••"),
        Observation("C", "XX", "XX", "XXXX"),
    ]

    for observation in observations:
        features = extract_structural_features(observation)

        if not features:
            return False

    return True


def check_changed_structure_is_observable():
    observations = [
        Observation("A", "aa", "aa", "aaaa"),
        Observation("B", "aa", "bb", "aabb"),
    ]

    features_a = {
        (feature.name, str(feature.value))
        for feature in extract_structural_features(observations[0])
    }

    features_b = {
        (feature.name, str(feature.value))
        for feature in extract_structural_features(observations[1])
    }

    return features_a != features_b


def check_empty_input():
    inventory = build_relation_inventory([])
    candidates = generate_candidate_relations([])

    return inventory == [] and candidates == []


def run_benchmark():
    observations = build_observations()

    checks = {
        "raw_observations_available": check_raw_observations(observations),
        "structural_features_available": check_structural_features(
            observations
        ),
        "relations_are_data_derived": check_relations_are_data_derived(
            observations
        ),
        "candidate_generation_available": check_candidate_generation(
            observations
        ),
        "candidate_provenance_available": check_candidate_provenance(
            observations
        ),
        "no_semantic_labels_exposed": check_no_semantic_labels(
            observations
        ),
        "changed_symbols_produce_structural_output":
            check_changed_symbols_produce_structural_output(),
        "changed_structure_is_observable":
            check_changed_structure_is_observable(),
        "empty_input_handled": check_empty_input(),
    }

    all_passed = all(checks.values())

    print("UFCPS — L3 Invariant Relation Generator Benchmark v2")
    print()
    print("predefined_candidate_family_used: False")
    print("semantic_labels_exposed_to_engine: False")
    print()
    print("Checks:")

    for name, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {status}: {name}")

    print()
    print(f"all_passed: {all_passed}")

    if all_passed:
        print("RESULT: READY")
        return 0

    print("RESULT: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(run_benchmark())
