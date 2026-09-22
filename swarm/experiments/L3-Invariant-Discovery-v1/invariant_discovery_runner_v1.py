```python
from __future__ import annotations

"""
UFCPS — Level 3 Invariant Discovery Experiment Runner v1

This file is an experimental harness, not an invariant-discovery algorithm.

The runner deliberately contains no semantic rule for the dataset.

It:
    1. loads the frozen dataset;
    2. exposes only raw observations to a process adapter;
    3. receives the adapter's candidate invariant and predictions;
    4. evaluates those predictions against the hidden evaluation labels;
    5. emits PASS / FAIL / UNRESOLVED according to the frozen protocol.

A process adapter must be supplied separately. This prevents the harness
from silently solving the experiment itself.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable
import argparse
import importlib
import json
import sys
from datetime import datetime, timezone


EXPERIMENT_ID = "L3-Invariant-Discovery-v1"
PROTOCOL_VERSION = "1"
DATASET_VERSION = "1.0"


@dataclass(frozen=True)
class Observation:
    record_id: str
    left: str
    right: str
    result: str


@dataclass
class ProcessOutput:
    status: str
    candidate_invariant: str
    training_support: list[str]
    training_challenges: list[str]
    control_predictions: dict[str, str]
    holdout_predictions: dict[str, str]
    unresolved_questions: list[str]


@dataclass
class EvaluationResult:
    experiment_id: str
    protocol_version: str
    dataset_version: str
    process_status: str
    result: str
    checks: dict[str, bool]
    observations: dict[str, Any]
    process_output: dict[str, Any]


def load_dataset(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("dataset_id") != "UFCPS-L3-INVARIANT-DISCOVERY-v1":
        raise ValueError("Unexpected dataset_id.")

    return data


def public_observation(record: dict[str, Any]) -> Observation:
    return Observation(
        record_id=str(record["id"]),
        left=str(record["left"]),
        right=str(record["right"]),
        result=str(record["result"]),
    )


def build_process_input(data: dict[str, Any]) -> dict[str, Any]:
    """
    Build the only information that may be exposed to the process.

    expected_relation and provenance are intentionally excluded.
    The process therefore cannot directly inspect the evaluation oracle.
    """
    records = data["records"]

    training = [
        public_observation(r).__dict__
        for r in records
        if r["split"] == "train"
    ]

    controls = [
        public_observation(r).__dict__
        for r in records
        if r["split"] == "control"
    ]

    holdout = [
        public_observation(r).__dict__
        for r in records
        if r["split"] == "holdout"
    ]

    return {
        "experiment_id": EXPERIMENT_ID,
        "dataset_version": DATASET_VERSION,
        "training": training,
        "controls": controls,
        "holdout": holdout,
    }


def load_process_adapter(
    spec: str,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """
    Load an external process adapter.

    Format:
        module_name:function_name
    """
    if ":" not in spec:
        raise ValueError(
            "Adapter must use MODULE:FUNCTION format."
        )

    module_name, function_name = spec.split(":", 1)

    module = importlib.import_module(module_name)
    function = getattr(module, function_name)

    if not callable(function):
        raise TypeError("Process adapter is not callable.")

    return function


def normalize_process_output(
    raw: dict[str, Any],
) -> ProcessOutput:

    required = {
        "status",
        "candidate_invariant",
        "training_support",
        "training_challenges",
        "control_predictions",
        "holdout_predictions",
        "unresolved_questions",
    }

    missing = required.difference(raw)

    if missing:
        raise ValueError(
            "Process output is missing fields: "
            + ", ".join(sorted(missing))
        )

    status = str(raw["status"]).upper()

    if status not in {"PROPOSED", "UNRESOLVED"}:
        raise ValueError(
            "Process status must be PROPOSED or UNRESOLVED."
        )

    return ProcessOutput(
        status=status,
        candidate_invariant=str(
            raw["candidate_invariant"]
        ),
        training_support=[
            str(x) for x in raw["training_support"]
        ],
        training_challenges=[
            str(x) for x in raw["training_challenges"]
        ],
        control_predictions={
            str(k): str(v).upper()
            for k, v in raw["control_predictions"].items()
        },
        holdout_predictions={
            str(k): str(v).upper()
            for k, v in raw["holdout_predictions"].items()
        },
        unresolved_questions=[
            str(x)
            for x in raw["unresolved_questions"]
        ],
    )


def expected_labels(
    data: dict[str, Any],
    split: str,
) -> dict[str, str]:

    return {
        str(r["id"]): str(
            r["expected_relation"]
        ).upper()
        for r in data["records"]
        if r["split"] == split
    }


def score_predictions(
    predictions: dict[str, str],
    expected: dict[str, str],
) -> tuple[int, int, list[str]]:

    correct = 0
    total = len(expected)
    missing: list[str] = []

    for record_id, expected_value in expected.items():

        actual = predictions.get(record_id)

        if actual is None:
            missing.append(record_id)
            continue

        if actual == expected_value:
            correct += 1

    return correct, total, missing


def evaluate(
    data: dict[str, Any],
    output: ProcessOutput,
) -> EvaluationResult:

    control_expected = expected_labels(
        data,
        "control",
    )

    holdout_expected = expected_labels(
        data,
        "holdout",
    )

    control_correct, control_total, control_missing = (
        score_predictions(
            output.control_predictions,
            control_expected,
        )
    )

    holdout_correct, holdout_total, holdout_missing = (
        score_predictions(
            output.holdout_predictions,
            holdout_expected,
        )
    )

    candidate_exists = bool(
        output.candidate_invariant.strip()
    )

    control_complete = not control_missing
    holdout_complete = not holdout_missing

    control_discriminates = (
        control_total > 0
        and control_correct == control_total
    )

    holdout_generalizes = (
        holdout_total > 0
        and holdout_correct == holdout_total
    )

    if output.status == "UNRESOLVED":
        result = "UNRESOLVED"

    elif (
        candidate_exists
        and control_complete
        and holdout_complete
        and control_discriminates
        and holdout_generalizes
    ):
        result = "PASS"

    else:
        result = "FAIL"

    checks = {
        "candidate_exists": candidate_exists,

        "control_predictions_complete":
            control_complete,

        "holdout_predictions_complete":
            holdout_complete,

        "control_discriminates":
            control_discriminates,

        "holdout_generalizes":
            holdout_generalizes,

        "process_status_acceptable":
            output.status in {
                "PROPOSED",
                "UNRESOLVED",
            },
    }

    observations = {
        "control_correct":
            control_correct,

        "control_total":
            control_total,

        "holdout_correct":
            holdout_correct,

        "holdout_total":
            holdout_total,

        "control_missing":
            control_missing,

        "holdout_missing":
            holdout_missing,
    }

    return EvaluationResult(
        experiment_id=EXPERIMENT_ID,

        protocol_version=PROTOCOL_VERSION,

        dataset_version=DATASET_VERSION,

        process_status=output.status,

        result=result,

        checks=checks,

        observations=observations,

        process_output=asdict(output),
    )


def run(
    dataset_path: Path,
    adapter_spec: str,
    result_path: Path | None = None,
) -> EvaluationResult:

    data = load_dataset(dataset_path)

    process_input = build_process_input(data)

    adapter = load_process_adapter(
        adapter_spec
    )

    raw_output = adapter(
        process_input
    )

    output = normalize_process_output(
        raw_output
    )

    result = evaluate(
        data,
        output
    )

    if result_path is not None:

        result_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        payload = asdict(result)

        payload["timestamp_utc"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        with result_path.open(
            "w",
            encoding="utf-8"
        ) as handle:

            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
            )

    return result


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "UFCPS Level 3 "
            "invariant-discovery "
            "experiment runner"
        )
    )

    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--adapter",
        required=True,
        help=(
            "External process adapter: "
            "MODULE:FUNCTION"
        ),
    )

    parser.add_argument(
        "--result",
        type=Path,
        default=None,
    )

    args = parser.parse_args()

    try:

        result = run(
            dataset_path=args.dataset,
            adapter_spec=args.adapter,
            result_path=args.result,
        )

    except Exception as exc:

        print(
            f"RUNNER_ERROR: {exc}",
            file=sys.stderr,
        )

        return 2

    print(
        json.dumps(
            asdict(result),
            ensure_ascii=False,
            indent=2,
        )
    )

    return (
        0
        if result.result
        in {"PASS", "UNRESOLVED"}
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
```
