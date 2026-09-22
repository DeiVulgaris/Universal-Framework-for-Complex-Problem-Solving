from **future** import annotations

from dataclasses import dataclass, asdict
from itertools import combinations
from collections import Counter
from typing import Any, Dict, Iterable, List, Sequence

EXPERIMENT_ID = "UFCPS-L3-INVARIANT-DISCOVERY-v2"
VERSION = "2.0"

@dataclass(frozen=True)
class Observation:
record_id: str
left: str
right: str
result: str

@dataclass(frozen=True)
class StructuralFeature:
name: str
value: Any

@dataclass(frozen=True)
class StructuralRelation:
relation_id: str
relation_type: str
operands: tuple[str, ...]
value: Any
source_record_ids: tuple[str, ...]

@dataclass(frozen=True)
class CandidateRelation:
candidate_id: str
relation_type: str
relation: str
support: tuple[str, ...]
challenge: tuple[str, ...]
evidence: tuple[str, ...]

def _ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
seen = set()
result = []

```
for value in values:
    if value not in seen:
        seen.add(value)
        result.append(value)

return tuple(result)
```

def _symbol_counts(value: str) -> Dict[str, int]:
return dict(Counter(value))

def _unique_symbols(value: str) -> tuple[str, ...]:
return tuple(sorted(set(value)))

def _run_lengths(value: str) -> tuple[int, ...]:
if not value:
return ()

```
runs: List[int] = []
current = value[0]
count = 1

for symbol in value[1:]:
    if symbol == current:
        count += 1
    else:
        runs.append(count)
        current = symbol
        count = 1

runs.append(count)
return tuple(runs)
```

def extract_structural_features(observation: Observation) -> Dict[str, Any]:
"""
Extract neutral, directly observable structural properties.

```
No semantic interpretation is performed here.
"""

left = observation.left
right = observation.right
result = observation.result

left_counts = _symbol_counts(left)
right_counts = _symbol_counts(right)
result_counts = _symbol_counts(result)

features: Dict[str, Any] = {
    "record_id": observation.record_id,

    "left": left,
    "right": right,
    "result": result,

    "left_length": len(left),
    "right_length": len(right),
    "result_length": len(result),

    "left_empty": len(left) == 0,
    "right_empty": len(right) == 0,
    "result_empty": len(result) == 0,

    "operands_equal": left == right,
    "left_equals_result": left == result,
    "right_equals_result": right == result,

    "left_unique_symbol_count": len(set(left)),
    "right_unique_symbol_count": len(set(right)),
    "result_unique_symbol_count": len(set(result)),

    "left_symbols": _unique_symbols(left),
    "right_symbols": _unique_symbols(right),
    "result_symbols": _unique_symbols(result),

    "left_symbol_counts": left_counts,
    "right_symbol_counts": right_counts,
    "result_symbol_counts": result_counts,

    "left_run_lengths": _run_lengths(left),
    "right_run_lengths": _run_lengths(right),
    "result_run_lengths": _run_lengths(result),

    "left_is_prefix_of_result": result.startswith(left) if left else False,
    "right_is_suffix_of_result": result.endswith(right) if right else False,
    "right_is_prefix_of_result": result.startswith(right) if right else False,
    "left_is_suffix_of_result": result.endswith(left) if left else False,

    "literal_concatenation_lr": left + right,
    "literal_concatenation_rl": right + left,

    "result_equals_left_right_concat": result == left + right,
    "result_equals_right_left_concat": result == right + left,

    "length_difference_lr": len(left) - len(right),
    "result_minus_left_length": len(result) - len(left),
    "result_minus_right_length": len(result) - len(right),

    "length_pair": (len(left), len(right)),
    "length_triple": (len(left), len(right), len(result)),
}

features["left_right_symbol_set_equal"] = set(left) == set(right)
features["left_result_symbol_set_equal"] = set(left) == set(result)
features["right_result_symbol_set_equal"] = set(right) == set(result)

features["left_right_multiset_equal"] = Counter(left) == Counter(right)
features["left_result_multiset_equal"] = Counter(left) == Counter(result)
features["right_result_multiset_equal"] = Counter(right) == Counter(result)

features["combined_symbol_counts"] = dict(
    Counter(left) + Counter(right)
)

features["result_matches_combined_counts"] = (
    Counter(result) == Counter(left) + Counter(right)
)

features["result_length_matches_combined_lengths"] = (
    len(result) == len(left) + len(right)
)

features["result_length_matches_left"] = (
    len(result) == len(left)
)

features["result_length_matches_right"] = (
    len(result) == len(right)
)

return features
```

def _feature_value_key(value: Any) -> str:
"""
Convert an observable feature value into a deterministic comparable key.
"""

```
if isinstance(value, dict):
    items = sorted(
        (str(key), _feature_value_key(item_value))
        for key, item_value in value.items()
    )
    return repr(items)

if isinstance(value, (list, tuple, set)):
    return repr(tuple(_feature_value_key(item) for item in value))

return repr(value)
```

def _candidate_relation_name(feature_name: str, feature_value: Any) -> str:
return (
f"{feature_name} == "
f"{_feature_value_key(feature_value)}"
)

def generate_observation_relations(
observations: Sequence[Observation],
) -> List[StructuralRelation]:
"""
Generate relations directly observable within individual records.

```
This function does not decide which relation is important.
It merely records structural regularities.
"""

relations: List[StructuralRelation] = []
relation_counter = 0

for observation in observations:
    features = extract_structural_features(observation)

    for feature_name, feature_value in features.items():
        if feature_name in {
            "record_id",
            "left",
            "right",
            "result",
        }:
            continue

        relation_counter += 1

        relations.append(
            StructuralRelation(
                relation_id=f"R_{relation_counter:04d}",
                relation_type="OBSERVABLE_FEATURE",
                operands=(feature_name,),
                value=feature_value,
                source_record_ids=(observation.record_id,),
            )
        )

return relations
```

def generate_cross_record_relations(
observations: Sequence[Observation],
) -> List[StructuralRelation]:
"""
Identify structural properties that recur across different observations.

```
The function does not assign semantic meaning to recurring relations.
"""

feature_maps = {
    observation.record_id: extract_structural_features(observation)
    for observation in observations
}

common_feature_values: Dict[tuple[str, str], List[str]] = {}

for record_id, features in feature_maps.items():
    for feature_name, feature_value in features.items():
        if feature_name in {
            "record_id",
            "left",
            "right",
            "result",
        }:
            continue

        key = (
            feature_name,
            _feature_value_key(feature_value),
        )

        common_feature_values.setdefault(key, []).append(record_id)

relations: List[StructuralRelation] = []
relation_counter = 0

for (feature_name, _), record_ids in sorted(
    common_feature_values.items()
):
    if len(record_ids) < 2:
        continue

    reference_features = feature_maps[record_ids[0]]
    feature_value = reference_features[feature_name]

    relation_counter += 1

    relations.append(
        StructuralRelation(
            relation_id=f"XR_{relation_counter:04d}",
            relation_type="RECURRING_STRUCTURAL_FEATURE",
            operands=(feature_name,),
            value=feature_value,
            source_record_ids=tuple(sorted(record_ids)),
        )
    )

return relations
```

def generate_pairwise_relations(
observations: Sequence[Observation],
) -> List[StructuralRelation]:
"""
Generate generic pairwise relations between structural features.

```
Only equality relations are generated at this stage.

No semantic interpretation is introduced.
"""

relation_specs = (
    ("left_length", "right_length"),
    ("left_length", "result_length"),
    ("right_length", "result_length"),
    ("left_unique_symbol_count", "right_unique_symbol_count"),
    ("left_unique_symbol_count", "result_unique_symbol_count"),
    ("right_unique_symbol_count", "result_unique_symbol_count"),
    ("left_run_lengths", "right_run_lengths"),
    ("left_run_lengths", "result_run_lengths"),
    ("right_run_lengths", "result_run_lengths"),
)

relations: List[StructuralRelation] = []
relation_counter = 0

for observation in observations:
    features = extract_structural_features(observation)

    for left_name, right_name in relation_specs:
        left_value = features[left_name]
        right_value = features[right_name]

        relation_counter += 1

        relations.append(
            StructuralRelation(
                relation_id=f"PR_{relation_counter:04d}",
                relation_type="PAIRWISE_EQUALITY",
                operands=(left_name, right_name),
                value=left_value == right_value,
                source_record_ids=(observation.record_id,),
            )
        )

return relations
```

def build_relation_inventory(
observations: Sequence[Observation],
) -> Dict[str, Any]:
"""
Build the complete structural relation inventory.

```
This is the output of the relation-generation stage.

It is intentionally not a candidate selector.
"""

observation_relations = generate_observation_relations(observations)
cross_record_relations = generate_cross_record_relations(observations)
pairwise_relations = generate_pairwise_relations(observations)

return {
    "experiment_id": EXPERIMENT_ID,
    "version": VERSION,
    "observation_count": len(observations),
    "observation_relations": [
        asdict(relation)
        for relation in observation_relations
    ],
    "cross_record_relations": [
        asdict(relation)
        for relation in cross_record_relations
    ],
    "pairwise_relations": [
        asdict(relation)
        for relation in pairwise_relations
    ],
}
```

def generate_candidate_relations(
observations: Sequence[Observation],
) -> List[CandidateRelation]:
"""
Generate candidate relations from recurring structural properties.

```
Important:
This function does not contain a predefined list of intended
domain-specific invariants.

Candidates arise from relations observed in the supplied data.
"""

if not observations:
    return []

feature_maps = {
    observation.record_id: extract_structural_features(observation)
    for observation in observations
}

candidate_groups: Dict[tuple[str, str], List[str]] = {}

for record_id, features in feature_maps.items():
    for feature_name, feature_value in features.items():
        if feature_name in {
            "record_id",
            "left",
            "right",
            "result",
        }:
            continue

        key = (
            feature_name,
            _feature_value_key(feature_value),
        )

        candidate_groups.setdefault(key, []).append(record_id)

candidates: List[CandidateRelation] = []
candidate_counter = 0

for (feature_name, value_key), support_ids in sorted(
    candidate_groups.items()
):
    if len(support_ids) < 2:
        continue

    candidate_counter += 1

    all_ids = tuple(observation.record_id for observation in observations)
    support = tuple(sorted(support_ids))
    challenge = tuple(
        sorted(
            record_id
            for record_id in all_ids
            if record_id not in support
        )
    )

    candidate = CandidateRelation(
        candidate_id=f"CAND_{candidate_counter:04d}",
        relation_type="RECURRING_FEATURE",
        relation=_candidate_relation_name(
            feature_name,
            feature_maps[support_ids[0]][feature_name],
        ),
        support=support,
        challenge=challenge,
        evidence=(
            f"Feature '{feature_name}' recurs with the same "
            f"observable value across {len(support)} observations.",
            f"Candidate generated from observations: "
            f"{', '.join(support)}.",
        ),
    )

    candidates.append(candidate)

return candidates
```

def summarize_candidates(
candidates: Sequence[CandidateRelation],
) -> List[Dict[str, Any]]:
"""
Return deterministic candidate summaries for downstream evaluation.
"""

```
return [
    {
        "candidate_id": candidate.candidate_id,
        "relation_type": candidate.relation_type,
        "relation": candidate.relation,
        "support": list(candidate.support),
        "challenge": list(candidate.challenge),
        "evidence": list(candidate.evidence),
    }
    for candidate in candidates
]
```

def smoke_test() -> Dict[str, Any]:
observations = [
Observation("S01", "aa", "aa", "aaaa"),
Observation("S02", "••", "••", "••••"),
Observation("S03", "II", "II", "IV"),
Observation("S04", "xx", "xx", "xxxxx"),
]

```
inventory = build_relation_inventory(observations)
candidates = generate_candidate_relations(observations)

assert inventory["observation_count"] == 4
assert inventory["observation_relations"]
assert inventory["cross_record_relations"]
assert inventory["pairwise_relations"]
assert candidates

return {
    "experiment": EXPERIMENT_ID,
    "version": VERSION,
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
    "predefined_candidate_family_used": False,
    "semantic_labels_used": False,
    "status": "READY",
}
```

if **name** == "**main**":
result = smoke_test()

```
print("UFCPS — L3 Invariant Relation Generator v2")
print("=" * 72)
print(f"experiment: {result['experiment']}")
print(f"version: {result['version']}")
print(f"status: {result['status']}")
print(
    "observation_relation_count:",
    result["observation_relation_count"],
)
print(
    "cross_record_relation_count:",
    result["cross_record_relation_count"],
)
print(
    "pairwise_relation_count:",
    result["pairwise_relation_count"],
)
print("candidate_count:", result["candidate_count"])
print(
    "predefined_candidate_family_used:",
    result["predefined_candidate_family_used"],
)
print(
    "semantic_labels_used:",
    result["semantic_labels_used"],
)
print("=" * 72)
print("RESULT: READY")
```
