```python
"""
UFCPS Level 3 — Invariant Discovery Experiment Runner v1

Experimental harness only.

The runner does NOT contain the invariant to be discovered.
It provides raw observations to an external process adapter,
receives the process hypothesis, and evaluates that hypothesis
against hidden controls and holdout data.

Methodological separation:

    DISCOVERY
        training + controls
            ↓
        candidate invariant
            ↓
        hypothesis freeze

    EVALUATION
        holdout
            ↓
        external evaluation

The holdout is deliberately NOT exposed during discovery.

Experiment:
    L3-Invariant-Discovery-v1
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


# ----------------------------------------------------------------------
# Experiment identity
# ----------------------------------------------------------------------

EXPERIMENT_ID = "L3-Invariant-Discovery-v1"
PROTOCOL_VERSION = "1"
DATASET_VERSION = "1.0"


# ----------------------------------------------------------------------
# Data structures
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Observation:
    record_id: str
    left: str
    right: str
    result: str


@dataclass
class ProcessOutput:
    """
    Output expected from the external Level 3 process adapter.

    The process may either propose an invariant or explicitly remain
    unresolved.

    IMPORTANT:
    The process must not receive the hidden evaluation oracle.
    """

    status: str = "UNRESOLVED"

    candidate_invariant: Optional[str] = None

    training_support: List[str] = field(
        default_factory=list
    )

    training_challenges: List[str] = field(
        default_factory=list
    )

    control_predictions: Dict[str, bool] = field(
        default_factory=dict
    )

    holdout_predictions: Dict[str, bool] = field(
        default_factory=dict
    )

    unresolved_questions: List[str] = field(
        default_factory=list
    )


@dataclass
class EvaluationResult:
    experiment_id: str
    protocol_version: str
    dataset_version: str

    status: str

    candidate_invariant: Optional[str]

    discovery_observations: int
    control_observations: int
    holdout_observations: int

    controls_complete: bool
    controls_correct: bool

    holdout_complete: bool
    holdout_correct: bool

    process_status: str

    training_support: List[str]
    training_challenges: List[str]

    control_predictions: Dict[str, bool]
    holdout_predictions: Dict[str, bool]

    unresolved_questions: List[str]

    observations: Dict[str, Any] = field(
        default_factory=dict
    )


# ----------------------------------------------------------------------
# Dataset handling
# ----------------------------------------------------------------------


def load_dataset(path: Path) -> Dict[str, Any]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def _observation_from_record(
    record: Dict[str, Any],
) -> Observation:
    return Observation(
        record_id=str(
            record["record_id"]
        ),
        left=str(
            record["left"]
        ),
        right=str(
            record["right"]
        ),
        result=str(
            record["result"]
        ),
    )


def load_observations(
    dataset: Dict[str, Any],
    split: str,
) -> List[Observation]:

    records = dataset.get(
        split,
        []
    )

    if not isinstance(
        records,
        list,
    ):
        raise ValueError(
            f"Dataset split '{split}' must be a list."
        )

    return [
        _observation_from_record(record)
        for record in records
    ]


# ----------------------------------------------------------------------
# Process input
# ----------------------------------------------------------------------


def observation_to_process_record(
    observation: Observation,
) -> Dict[str, str]:
    """
    Convert an observation into the raw representation exposed
    to the process.

    No semantic label, expected relation, provenance, or oracle
    information is included.
    """

    return {
        "record_id": observation.record_id,
        "left": observation.left,
        "right": observation.right,
        "result": observation.result,
    }


def build_discovery_input(
    training: List[Observation],
    controls: List[Observation],
) -> Dict[str, Any]:
    """
    Build the ONLY input visible during invariant discovery.

    HOLDOUT IS INTENTIONALLY ABSENT.

    Controls are visible because the protocol allows the process
    to challenge its candidate against negative observations.
    """

    return {
        "experiment_id": EXPERIMENT_ID,
        "protocol_version": PROTOCOL_VERSION,
        "dataset_version": DATASET_VERSION,

        "phase": "DISCOVERY",

        "observations": {
            "training": [
                observation_to_process_record(
                    observation
                )
                for observation in training
            ],
            "controls": [
                observation_to_process_record(
                    observation
                )
                for observation in controls
            ],
        },

        "semantic_labels_exposed": False,

        "instruction": (
            "Identify a relation that explains the observations "
            "without relying on semantic domain labels. "
            "A candidate must remain falsifiable by the controls."
        ),
    }


def build_holdout_input(
    holdout: List[Observation],
) -> Dict[str, Any]:
    """
    Build the evaluation input presented only AFTER the
    discovery hypothesis has been frozen.

    The holdout is never part of discovery.
    """

    return {
        "experiment_id": EXPERIMENT_ID,
        "protocol_version": PROTOCOL_VERSION,
        "dataset_version": DATASET_VERSION,

        "phase": "EVALUATION",

        "observations": [
            observation_to_process_record(
                observation
            )
            for observation in holdout
        ],

        "semantic_labels_exposed": False,

        "instruction": (
            "Apply the previously frozen candidate invariant "
            "to these observations. Do not modify the candidate "
            "invariant during this evaluation."
        ),
    }


# ----------------------------------------------------------------------
# Process adapter
# ----------------------------------------------------------------------


def load_adapter(
    adapter_spec: str,
) -> Callable[[Dict[str, Any]], Any]:
    """
    Load adapter in the form:

        module:function
    """

    if ":" not in adapter_spec:
        raise ValueError(
            "Adapter must have the form MODULE:FUNCTION."
        )

    module_name, function_name = (
        adapter_spec.split(
            ":",
            1,
        )
    )

    module = importlib.import_module(
        module_name
    )

    function = getattr(
        module,
        function_name,
    )

    if not callable(function):
        raise TypeError(
            f"Adapter '{adapter_spec}' is not callable."
        )

    return function


def run_discovery(
    adapter: Callable[[Dict[str, Any]], Any],
    discovery_input: Dict[str, Any],
) -> ProcessOutput:

    raw_output = adapter(
        discovery_input
    )

    return normalize_process_output(
        raw_output
    )


def run_holdout_evaluation(
    adapter: Callable[[Dict[str, Any]], Any],
    holdout_input: Dict[str, Any],
    frozen_candidate: str,
) -> ProcessOutput:
    """
    Ask the adapter to apply the frozen hypothesis.

    The runner never supplies hidden expected labels.
    """

    evaluation_input = dict(
        holdout_input
    )

    evaluation_input[
        "frozen_candidate_invariant"
    ] = frozen_candidate

    raw_output = adapter(
        evaluation_input
    )

    return normalize_process_output(
        raw_output
    )


# ----------------------------------------------------------------------
# Output normalization
# ----------------------------------------------------------------------


def normalize_process_output(
    raw_output: Any,
) -> ProcessOutput:

    if isinstance(
        raw_output,
        ProcessOutput,
    ):
        return raw_output

    if not isinstance(
        raw_output,
        dict,
    ):
        raise TypeError(
            "Process adapter must return either "
            "ProcessOutput or dict."
        )

    return ProcessOutput(
        status=str(
            raw_output.get(
                "status",
                "UNRESOLVED",
            )
        ).upper(),

        candidate_invariant=(
            raw_output.get(
                "candidate_invariant"
            )
        ),

        training_support=list(
            raw_output.get(
                "training_support",
                [],
            )
        ),

        training_challenges=list(
            raw_output.get(
                "training_challenges",
                [],
            )
        ),

        control_predictions=dict(
            raw_output.get(
                "control_predictions",
                {},
            )
        ),

        holdout_predictions=dict(
            raw_output.get(
                "holdout_predictions",
                {},
            )
        ),

        unresolved_questions=list(
            raw_output.get(
                "unresolved_questions",
                [],
            )
        ),
    )


# ----------------------------------------------------------------------
# Hidden evaluation oracle
# ----------------------------------------------------------------------


def expected_relation(
    record: Dict[str, Any],
) -> bool:
    """
    Read the hidden evaluation oracle.

    This function is intentionally used ONLY by the external
    evaluator.

    It is never included in process input.
    """

    evaluation = record.get(
        "evaluation"
    )

    if not isinstance(
        evaluation,
        dict,
    ):
        raise ValueError(
            "Record is missing evaluation metadata."
        )

    if "expected_positive" not in evaluation:
        raise ValueError(
            "Record is missing expected_positive."
        )

    return bool(
        evaluation["expected_positive"]
    )


def evaluate_predictions(
    predictions: Dict[str, bool],
    records: List[Dict[str, Any]],
) -> tuple[bool, bool]:

    expected_ids = {
        str(
            record["record_id"]
        )
        for record in records
    }

    prediction_ids = {
        str(record_id)
        for record_id in predictions
    }

    complete = (
        expected_ids == prediction_ids
    )

    if not complete:
        return False, False

    correct = True

    for record in records:
        record_id = str(
            record["record_id"]
        )

        expected = expected_relation(
            record
        )

        predicted = bool(
            predictions[record_id]
        )

        if predicted != expected:
            correct = False
            break

    return True, correct


# ----------------------------------------------------------------------
# Result evaluation
# ----------------------------------------------------------------------


def evaluate_experiment(
    dataset: Dict[str, Any],
    discovery_output: ProcessOutput,
    holdout_output: Optional[ProcessOutput],
) -> EvaluationResult:

    training_records = dataset.get(
        "training",
        []
    )

    control_records = dataset.get(
        "controls",
        []
    )

    holdout_records = dataset.get(
        "holdout",
        []
    )

    candidate_exists = bool(
        discovery_output.candidate_invariant
    )

    (
        controls_complete,
        controls_correct,
    ) = evaluate_predictions(
        discovery_output.control_predictions,
        control_records,
    )

    if holdout_output is None:
        holdout_complete = False
        holdout_correct = False
        holdout_predictions = {}

    else:
        holdout_predictions = (
            holdout_output.holdout_predictions
            or holdout_output.control_predictions
        )

        (
            holdout_complete,
            holdout_correct,
        ) = evaluate_predictions(
            holdout_predictions,
            holdout_records,
        )

    process_status = (
        discovery_output.status.upper()
    )

    if process_status == "UNRESOLVED":
        final_status = "UNRESOLVED"

    elif (
        candidate_exists
        and controls_complete
        and controls_correct
        and holdout_complete
        and holdout_correct
    ):
        final_status = "PASS"

    else:
        final_status = "FAIL"

    return EvaluationResult(
        experiment_id=EXPERIMENT_ID,
        protocol_version=PROTOCOL_VERSION,
        dataset_version=DATASET_VERSION,

        status=final_status,

        candidate_invariant=(
            discovery_output.candidate_invariant
        ),

        discovery_observations=(
            len(training_records)
            + len(control_records)
        ),

        control_observations=len(
            control_records
        ),

        holdout_observations=len(
            holdout_records
        ),

        controls_complete=(
            controls_complete
        ),

        controls_correct=(
            controls_correct
        ),

        holdout_complete=(
            holdout_complete
        ),

        holdout_correct=(
            holdout_correct
        ),

        process_status=(
            process_status
        ),

        training_support=(
            discovery_output.training_support
        ),

        training_challenges=(
            discovery_output.training_challenges
        ),

        control_predictions=(
            discovery_output.control_predictions
        ),

        holdout_predictions=(
            holdout_predictions
        ),

        unresolved_questions=(
            discovery_output.unresolved_questions
        ),

        observations={
            "holdout_withheld_during_discovery": True,
            "candidate_frozen_before_holdout": (
                holdout_output is not None
            ),
            "semantic_labels_exposed_to_process": False,
        },
    )


# ----------------------------------------------------------------------
# Execution
# ----------------------------------------------------------------------


def run_experiment(
    dataset_path: Path,
    adapter_spec: str,
) -> EvaluationResult:

    dataset = load_dataset(
        dataset_path
    )

    training = load_observations(
        dataset,
        "training",
    )

    controls = load_observations(
        dataset,
        "controls",
    )

    holdout = load_observations(
        dataset,
        "holdout",
    )

    adapter = load_adapter(
        adapter_spec
    )

    # --------------------------------------------------------------
    # Phase 1 — Discovery
    # --------------------------------------------------------------

    discovery_input = build_discovery_input(
        training,
        controls,
    )

    discovery_output = run_discovery(
        adapter,
        discovery_input,
    )

    # --------------------------------------------------------------
    # Freeze hypothesis
    # --------------------------------------------------------------

    if (
        discovery_output.status.upper()
        == "UNRESOLVED"
    ):
        return evaluate_experiment(
            dataset,
            discovery_output,
            None,
        )

    if not discovery_output.candidate_invariant:
        return evaluate_experiment(
            dataset,
            discovery_output,
            None,
        )

    frozen_candidate = (
        discovery_output.candidate_invariant
    )

    # --------------------------------------------------------------
    # Phase 2 — Holdout evaluation
    # --------------------------------------------------------------

    holdout_input = build_holdout_input(
        holdout
    )

    holdout_output = run_holdout_evaluation(
        adapter,
        holdout_input,
        frozen_candidate,
    )

    return evaluate_experiment(
        dataset,
        discovery_output,
        holdout_output,
    )


# ----------------------------------------------------------------------
# Serialization
# ----------------------------------------------------------------------


def save_result(
    result: EvaluationResult,
    path: Path,
) -> None:

    with path.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            asdict(result),
            handle,
            ensure_ascii=False,
            indent=2,
        )


def print_result(
    result: EvaluationResult,
) -> None:

    print(
        f"EXPERIMENT: {result.experiment_id}"
    )

    print(
        f"STATUS: {result.status}"
    )

    print(
        f"PROCESS STATUS: {result.process_status}"
    )

    print(
        "CANDIDATE INVARIANT: "
        f"{result.candidate_invariant}"
    )

    print(
        "DISCOVERY OBSERVATIONS: "
        f"{result.discovery_observations}"
    )

    print(
        "CONTROL COMPLETE: "
        f"{result.controls_complete}"
    )

    print(
        "CONTROL CORRECT: "
        f"{result.controls_correct}"
    )

    print(
        "HOLDOUT COMPLETE: "
        f"{result.holdout_complete}"
    )

    print(
        "HOLDOUT CORRECT: "
        f"{result.holdout_correct}"
    )

    print(
        "HOLDOUT WITHHELD DURING DISCOVERY: "
        f"{result.observations.get('holdout_withheld_during_discovery')}"
    )

    print(
        "\nCONTROL PREDICTIONS:"
    )

    for (
        record_id,
        prediction,
    ) in result.control_predictions.items():

        print(
            f"  {record_id}: {prediction}"
        )

    print(
        "\nHOLDOUT PREDICTIONS:"
    )

    for (
        record_id,
        prediction,
    ) in result.holdout_predictions.items():

        print(
            f"  {record_id}: {prediction}"
        )

    if result.unresolved_questions:

        print(
            "\nUNRESOLVED QUESTIONS:"
        )

        for question in (
            result.unresolved_questions
        ):
            print(
                f"  - {question}"
            )


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------


def build_argument_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description=(
            "UFCPS Level 3 invariant discovery "
            "experiment runner."
        )
    )

    parser.add_argument(
        "--dataset",
        required=True,
        help=(
            "Path to frozen experiment dataset."
        ),
    )

    parser.add_argument(
        "--adapter",
        required=True,
        help=(
            "Process adapter in MODULE:FUNCTION form."
        ),
    )

    parser.add_argument(
        "--result",
        required=False,
        help=(
            "Optional path for result JSON."
        ),
    )

    return parser


def main(
    argv: Optional[List[str]] = None,
) -> int:

    parser = build_argument_parser()

    args = parser.parse_args(
        argv
    )

    try:

        result = run_experiment(
            dataset_path=Path(
                args.dataset
            ),
            adapter_spec=args.adapter,
        )

        print_result(
            result
        )

        if args.result:

            save_result(
                result,
                Path(
                    args.result
                ),
            )

        if result.status in {
            "PASS",
            "UNRESOLVED",
        }:
            return 0

        return 1

    except Exception as exc:

        print(
            f"RUNNER ERROR: {exc}",
            file=sys.stderr,
        )

        return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
```
