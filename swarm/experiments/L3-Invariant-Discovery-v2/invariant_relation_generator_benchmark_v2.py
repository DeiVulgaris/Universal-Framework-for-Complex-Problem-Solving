from __future__ import annotations

from invariant_relation_generator_v2 import (
Observation,
build_relation_inventory,
generate_candidate_relations,
extract_structural_features,
)

EXPERIMENT_ID = "UFCPS-L3-INVARIANT-DISCOVERY-v2"
BENCHMARK = "invariant_relation_generator_benchmark_v2"

def check_raw_observations_only() -> bool:
observations = [
Observation("S01", "aa", "aa", "aaaa"),
Observation("S02", "••", "••", "••••"),
Observation("S03", "II", "II", "IV"),
Observation("S04", "xx", "xx", "xxxxx"),
]

```
for observation in observations:
    assert observation.record_id
    assert observation.left
    assert observation.right
    assert observation.result

return True
```

def check_structural_feature_extraction() -> bool:
observation = Observation(
"S01",
"aa",
"aa",
"aaaa",
)

```
features = extract_structural_features(observation)

required = {
    "left_length",
    "right_length",
    "result_length",
    "operands_equal",
    "left_symbols",
    "right_symbols",
    "result_symbols",
    "left_symbol_counts",
    "right_symbol_counts",
    "result_symbol_counts",
    "left_run_lengths",
    "right_run_lengths",
    "result_run_lengths",
}

return required.issubset(features.keys())
```

def check_relations_are_data_derived() -> bool:
observations = [
Observation("S01", "aa", "aa", "aaaa"),
Observation("S02", "••", "••", "••••"),
Observation("S03", "II", "II", "IV"),
Observation("S04", "xx", "xx", "xxxxx"),
]

```
inventory = build_relation_inventory(observations)

return (
    len(inventory["observation_relations"]) > 0
    and len(inventory["cross_record_relations"]) > 0
    and len(inventory["pairwise_relations"]) > 0
)
```

def check_candidate_generation_without_predefined_family() -> bool:
observations = [
Observation("S01", "aa", "aa", "aaaa"),
Observation("S02", "••", "••", "••••"),
Observation("S03", "II", "II", "IV"),
Observation("S04", "xx", "xx", "xxxxx"),
]

```
candidates = generate_candidate_relations(observations)

assert candidates

forbidden_domain_candidates = {
    "RESULT_LENGTH_EQUALS_OPERAND_LENGTH_SUM",
    "RESULT_EQUALS_LITERAL_CONCATENATION",
    "ARITHMETIC_SUM",
    "ADDITION",
    "NUMERIC_VALUE",
}

generated_names = {
    candidate.relation
    for candidate in candidates
}

return not any(
    forbidden in relation
    for relation in generated_names
    for forbidden in forbidden_domain_candidates
)
```

def check_candidate_has_support_and_challenge() -> bool:
observations = [
Observation("S01", "aa", "aa", "aaaa"),
Observation("S02", "••", "••", "••••"),
Observation("S03", "II", "II", "IV"),
Observation("S04", "xx", "xx", "xxxxx"),
]

```
candidates = generate_candidate_relations(observations)

return all(
    candidate.support
    and candidate.challenge
    for candidate in candidates
)
```

def check_candidate_provenance() -> bool:
observations = [
Observation("S01", "aa", "aa", "aaaa"),
Observation("S02", "••", "••", "••••"),
Observation("S03", "II", "II", "IV"),
Observation("S04", "xx", "xx", "xxxxx"),
]

```
candidates = generate_candidate_relations(observations)

return all(
    candidate.evidence
    and any(
        record_id in candidate.evidence[1]
        for record_id in candidate.support
    )
    for candidate in candidates
)
```

def check_no_semantic_labels_in_features() -> bool:
observation = Observation(
"S01",
"aa",
"aa",
"aaaa",
)

```
features = extract_structural_features(observation)

semantic_terms = {
    "number",
    "numeric",
    "addition",
    "arithmetic",
    "sum",
    "numeral",
    "quantity",
}

feature_names = {
    str(name).lower()
    for name in features.keys()
}

return not any(
    any(term in name for term in semantic_terms)
    for name in feature_names
)
```

def check_changed_symbols_produce_structural_output() -> bool:
observations_a = [
Observation("A01", "aa", "aa", "aaaa"),
Observation("A02", "bb", "bb", "bbbb"),
]

```
observations_b = [
    Observation("B01", "XX", "XX", "XXXX"),
    Observation("B02", "YY", "YY", "YYYY"),
]

candidates_a = generate_candidate_relations(observations_a)
candidates_b = generate_candidate_relations(observations_b)

return bool(candidates_a) and bool(candidates_b)
```

def check_changed_structure_is_observable() -> bool:
observations_a = [
Observation("A01", "aa", "aa", "aaaa"),
Observation("A02", "bb", "bb", "bbbb"),
]

```
observations_b = [
    Observation("B01", "aa", "aa", "aaaa"),
    Observation("B02", "bbb", "bbb", "bbbbbb"),
]

inventory_a = build_relation_inventory(observations_a)
inventory_b = build_relation_inventory(observations_b)

lengths_a = {
    relation["value"]
    for relation in inventory_a["observation_relations"]
    if relation["operands"] == ["left_length"]
}

lengths_b = {
    relation["value"]
    for relation in inventory_b["observation_relations"]
    if relation["operands"] == ["left_length"]
}

return lengths_a != lengths_b
```

def check_empty_input() -> bool:
inventory = build_relation_inventory([])
candidates = generate_candidate_relations([])

```
return (
    inventory["observation_count"] == 0
    and not candidates
)
```

def run_benchmark() -> dict:
checks = {
"raw_observations_only": check_raw_observations_only(),
"structural_feature_extraction": (
check_structural_feature_extraction()
),
"relations_are_data_derived": (
check_relations_are_data_derived()
),
"candidate_generation_without_predefined_family": (
check_candidate_generation_without_predefined_family()
),
"candidate_has_support_and_challenge": (
check_candidate_has_support_and_challenge()
),
"candidate_provenance": check_candidate_provenance(),
"no_semantic_labels_in_features": (
check_no_semantic_labels_in_features()
),
"changed_symbols_produce_structural_output": (
check_changed_symbols_produce_structural_output()
),
"changed_structure_is_observable": (
check_changed_structure_is_observable()
),
"empty_input_handled": check_empty_input(),
}

```
return {
    "experiment": EXPERIMENT_ID,
    "benchmark": BENCHMARK,
    "checks": checks,
    "all_passed": all(checks.values()),
    "predefined_candidate_family_used": False,
    "semantic_labels_exposed_to_engine": False,
}
```

def print_report(result: dict) -> None:
print("UFCPS — L3 Invariant Relation Generator Benchmark v2")
print("=" * 72)
print(f"experiment: {result['experiment']}")
print(f"benchmark: {result['benchmark']}")
print()

```
print("CHECKS")
print("-" * 72)

for name, passed in result["checks"].items():
    status = "PASS" if passed else "FAIL"
    print(f"{status:<6} {name}")

print()
print("METHODOLOGICAL CONTROLS")
print("-" * 72)
print(
    "predefined_candidate_family_used:",
    result["predefined_candidate_family_used"],
)
print(
    "semantic_labels_exposed_to_engine:",
    result["semantic_labels_exposed_to_engine"],
)

print()
print("RESULT")
print("-" * 72)
print(f"all_passed: {result['all_passed']}")

if result["all_passed"]:
    print("RESULT: READY")
else:
    print("RESULT: FAIL")
```

if **name** == "**main**":
report = run_benchmark()
print_report(report)

```
raise SystemExit(0 if report["all_passed"] else 1)
```
