"""
UFCPS — Level 3 Emergent Integration v1

Integrates:

    Orthogonal Transition Explorer
            +
    Branch Interaction
            +
    Unresolved Question Ledger (UQL)

Conceptual cycle:

    C_k
      ↓
    OT candidates
      ↓
    parallel exploration
      ↓
    localization
      ↓
    branch interaction
      ├──────────────→ D_new
      │
      └──────────────→ I_candidate
                              ↓
                       new question(s)
                              ↓
                            UQL
                              ↓
                           C_k+1

Important architectural principles:

    1. OT branches are not required to collapse into one branch.
    2. Interaction may generate distinctions unavailable to isolated
       branches.
    3. Interaction may expose candidate invariants.
    4. Emergent distinctions become persistent research objects.
    5. New questions enter the unresolved-question memory.
    6. Candidate invariants remain hypotheses until transformed and tested.
    7. Branch failure does not terminate the global process.
    8. UQL persistence does not mean that an answer has been found.

This module is an integration layer.

It deliberately does not redefine:
    - OT exploration;
    - branch interaction;
    - invariant testing;
    - UQL storage semantics.

Instead, it translates interaction outputs into continuation objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple

from orthogonal_transition_explorer_v1 import (
    OTBranch,
    OTMechanism,
    OrthogonalTransitionExplorer,
    ExplorationResult,
)

from branch_interaction_v1 import (
    BranchInteractionEngine,
    CandidateInvariant,
    EmergentDistinction,
    InteractionResult,
    LocalizedBranch,
)


# ----------------------------------------------------------------------
# UQL adapter
# ----------------------------------------------------------------------


class UQLAdapter(Protocol):
    """
    Minimal interface required by the integration layer.

    The concrete UFCPS UQL store may implement a richer API.

    This adapter deliberately exposes only the semantic operations
    required here:

        create emergent question
        record derived distinction
        record candidate invariant
    """

    def create_question(
        self,
        question: str,
        *,
        parent_ref: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> str:
        ...

    def record_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> str:
        ...


# ----------------------------------------------------------------------
# In-memory UQL adapter
# ----------------------------------------------------------------------


@dataclass
class UQLQuestion:
    question_id: str
    question: str
    parent_ref: Optional[str]
    provenance: Dict[str, Any]


@dataclass
class UQLEvent:
    event_id: str
    event_type: str
    payload: Dict[str, Any]


class InMemoryUQLAdapter:
    """
    Deterministic adapter used for integration tests.

    This is NOT a replacement for the persistent UFCPS UQL store.

    It exists so the integration layer can be tested independently.
    """

    def __init__(self) -> None:

        self.questions: List[
            UQLQuestion
        ] = []

        self.events: List[
            UQLEvent
        ] = []

        self._question_counter = 0
        self._event_counter = 0

    def create_question(
        self,
        question: str,
        *,
        parent_ref: Optional[str] = None,
        provenance: Optional[
            Dict[str, Any]
        ] = None,
    ) -> str:

        self._question_counter += 1

        question_id = (
            f"UQL-Q-{self._question_counter:04d}"
        )

        self.questions.append(
            UQLQuestion(
                question_id=question_id,
                question=question,
                parent_ref=parent_ref,
                provenance=(
                    provenance
                    if provenance is not None
                    else {}
                ),
            )
        )

        return question_id

    def record_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> str:

        self._event_counter += 1

        event_id = (
            f"UQL-E-{self._event_counter:04d}"
        )

        self.events.append(
            UQLEvent(
                event_id=event_id,
                event_type=event_type,
                payload=payload,
            )
        )

        return event_id


# ----------------------------------------------------------------------
# Integration records
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class EmergentRecord:
    record_id: str
    kind: str

    source_branches: Tuple[str, ...]

    description: str

    provenance: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class Level3IntegrationResult:

    source_space: str

    exploration: ExplorationResult

    interaction: InteractionResult

    emergent_records: List[
        EmergentRecord
    ]

    generated_question_ids: List[str]

    invariant_ids: List[str]

    next_space: str

    continuation_ready: bool

    process_terminated: bool = False

    description: str = ""


# ----------------------------------------------------------------------
# Integration engine
# ----------------------------------------------------------------------


class Level3EmergentIntegration:
    """
    Connects OT exploration, branch interaction and UQL persistence.

    The engine does not choose an OT branch.

    Instead:

        exploration
             ↓
        interaction
             ↓
        persistence
             ↓
        continuation
    """

    def __init__(
        self,
        *,
        uql: UQLAdapter,
        explorer: Optional[
            OrthogonalTransitionExplorer
        ] = None,
        interaction_engine: Optional[
            BranchInteractionEngine
        ] = None,
    ) -> None:

        self.uql = uql

        self.explorer = (
            explorer
            if explorer is not None
            else OrthogonalTransitionExplorer()
        )

        self.interaction_engine = (
            interaction_engine
            if interaction_engine is not None
            else BranchInteractionEngine()
        )

    # ------------------------------------------------------------------
    # Localization
    # ------------------------------------------------------------------

    def localize_branches(
        self,
        branches: Iterable[OTBranch],
    ) -> List[LocalizedBranch]:

        localized: List[
            LocalizedBranch
        ] = []

        for branch in branches:

            distinctions = (
                tuple(
                    branch.metadata.get(
                        "distinctions",
                        (),
                    )
                )
            )

            relations = (
                tuple(
                    branch.metadata.get(
                        "relations",
                        (),
                    )
                )
            )

            constraints = (
                tuple(
                    branch.metadata.get(
                        "constraints",
                        (),
                    )
                )
            )

            localized.append(
                LocalizedBranch(
                    branch_id=branch.branch_id,

                    mechanism=(
                        branch.mechanism.value
                    ),

                    state_id=(
                        branch.target_space
                    ),

                    distinctions=(
                        distinctions
                    ),

                    relations=(
                        relations
                    ),

                    constraints=(
                        constraints
                    ),

                    productive=(
                        branch.restores_productive_differentiation
                    ),

                    metadata={
                        "source_space": (
                            branch.source_space
                        ),

                        "status": (
                            branch.status.value
                        ),

                        "productive_difference": (
                            branch.productive_difference_after
                        ),
                    },
                )
            )

        return localized

    # ------------------------------------------------------------------
    # Persist emergent distinction
    # ------------------------------------------------------------------

    def persist_emergent_distinction(
        self,
        distinction: EmergentDistinction,
        *,
        parent_ref: Optional[str] = None,
    ) -> EmergentRecord:

        provenance = {
            "origin": (
                "branch_interaction"
            ),

            "distinction_id": (
                distinction.distinction_id
            ),

            "source_branches": (
                distinction.source_branches
            ),

            "generated_from_relations": (
                distinction.generated_from_relations
            ),

            "novelty_basis": (
                distinction.novelty_basis
            ),
        }

        event_id = self.uql.record_event(
            "EMERGENT_DISTINCTION",
            {
                "distinction_id": (
                    distinction.distinction_id
                ),

                "source_branches": (
                    distinction.source_branches
                ),

                "description": (
                    distinction.description
                ),

                "provenance": provenance,
            },
        )

        question = (
            "What further distinctions become "
            "accessible through "
            f"{distinction.distinction_id}?"
        )

        question_id = self.uql.create_question(
            question,
            parent_ref=parent_ref,
            provenance={
                **provenance,
                "event_id": event_id,
            },
        )

        return EmergentRecord(
            record_id=event_id,

            kind="EMERGENT_DISTINCTION",

            source_branches=(
                distinction.source_branches
            ),

            description=(
                distinction.description
            ),

            provenance={
                **provenance,
                "question_id": question_id,
            },
        )

    # ------------------------------------------------------------------
    # Persist candidate invariant
    # ------------------------------------------------------------------

    def persist_candidate_invariant(
        self,
        invariant: CandidateInvariant,
        *,
        parent_ref: Optional[str] = None,
    ) -> EmergentRecord:

        provenance = {
            "origin": (
                "branch_interaction"
            ),

            "invariant_id": (
                invariant.invariant_id
            ),

            "source_branches": (
                invariant.source_branches
            ),

            "relation": (
                invariant.relation
            ),

            "observed_realizations": (
                invariant.observed_realizations
            ),

            "epistemic_status": (
                invariant.status.value
            ),
        }

        event_id = self.uql.record_event(
            "CANDIDATE_INVARIANT",
            {
                "invariant_id": (
                    invariant.invariant_id
                ),

                "relation": (
                    invariant.relation
                ),

                "source_branches": (
                    invariant.source_branches
                ),

                "observed_realizations": (
                    invariant.observed_realizations
                ),

                "status": (
                    invariant.status.value
                ),

                "provenance": provenance,
            },
        )

        question = (
            "Does candidate invariant "
            f"{invariant.invariant_id} remain "
            "preserved under independent "
            "transformations?"
        )

        question_id = self.uql.create_question(
            question,
            parent_ref=parent_ref,
            provenance={
                **provenance,
                "event_id": event_id,
            },
        )

        return EmergentRecord(
            record_id=event_id,

            kind="CANDIDATE_INVARIANT",

            source_branches=(
                invariant.source_branches
            ),

            description=(
                "Candidate invariant: "
                f"{invariant.relation}"
            ),

            provenance={
                **provenance,
                "question_id": question_id,
            },
        )

    # ------------------------------------------------------------------
    # Persist interaction questions
    # ------------------------------------------------------------------

    def persist_interaction_questions(
        self,
        interaction: InteractionResult,
        *,
        parent_ref: Optional[str] = None,
    ) -> List[str]:

        question_ids: List[str] = []

        for question in (
            interaction.new_questions
        ):

            question_id = (
                self.uql.create_question(
                    question,
                    parent_ref=parent_ref,
                    provenance={
                        "origin": (
                            "branch_interaction"
                        ),

                        "interaction_id": (
                            interaction.interaction_id
                        ),

                        "source_branches": (
                            interaction.branch_ids
                        ),
                    },
                )
            )

            question_ids.append(
                question_id
            )

        return question_ids

    # ------------------------------------------------------------------
    # Full integration
    # ------------------------------------------------------------------

    def run(
        self,
        *,
        source_space: str,
        branches: Iterable[OTBranch],
        parent_ref: Optional[str] = None,
        next_space: Optional[str] = None,
    ) -> Level3IntegrationResult:

        branch_list = list(
            branches
        )

        exploration = (
            self.explorer.explore(
                branch_list
            )
        )

        localized = (
            self.localize_branches(
                branch_list
            )
        )

        interaction = (
            self.interaction_engine.interact(
                localized
            )
        )

        records: List[
            EmergentRecord
        ] = []

        question_ids: List[str] = []

        for distinction in (
            interaction.emergent_distinctions
        ):

            record = (
                self.persist_emergent_distinction(
                    distinction,
                    parent_ref=parent_ref,
                )
            )

            records.append(
                record
            )

            question_id = (
                record.provenance.get(
                    "question_id"
                )
            )

            if question_id:
                question_ids.append(
                    question_id
                )

        for invariant in (
            interaction.candidate_invariants
        ):

            record = (
                self.persist_candidate_invariant(
                    invariant,
                    parent_ref=parent_ref,
                )
            )

            records.append(
                record
            )

            question_id = (
                record.provenance.get(
                    "question_id"
                )
            )

            if question_id:
                question_ids.append(
                    question_id
                )

        question_ids.extend(
            self.persist_interaction_questions(
                interaction,
                parent_ref=parent_ref,
            )
        )

        if next_space is None:

            next_space = (
                f"{source_space}_NEXT"
            )

        self.uql.record_event(
            "LEVEL3_CONTINUATION",
            {
                "source_space": (
                    source_space
                ),

                "next_space": (
                    next_space
                ),

                "interaction_id": (
                    interaction.interaction_id
                ),

                "emergent_records": [
                    record.record_id
                    for record in records
                ],

                "generated_questions": (
                    question_ids
                ),
            },
        )

        return Level3IntegrationResult(
            source_space=source_space,

            exploration=exploration,

            interaction=interaction,

            emergent_records=records,

            generated_question_ids=(
                question_ids
            ),

            invariant_ids=[
                invariant.invariant_id
                for invariant
                in interaction.candidate_invariants
            ],

            next_space=next_space,

            continuation_ready=True,

            process_terminated=False,

            description=(
                "Parallel OT exploration was "
                "followed by branch interaction. "
                "Emergent distinctions and candidate "
                "invariants were persisted as "
                "continuation-relevant research objects."
            ),
        )


# ----------------------------------------------------------------------
# Integration fixture
# ----------------------------------------------------------------------


def build_fixture_branches() -> List[OTBranch]:

    explorer = (
        OrthogonalTransitionExplorer()
    )

    branches = (
        explorer.generate_candidates(
            source_space="C_k",
            mechanisms=[
                OTMechanism.SCALE,
                OTMechanism.STRUCTURAL_RECONFIGURATION,
                OTMechanism.REPRESENTATION_SPACE,
            ],
        )
    )

    branch_data = {

        OTMechanism.SCALE: {
            "productivity": 1.10,
            "distinctions": (
                "node",
                "scale",
                "boundary_A",
            ),
            "relations": (
                "persistence",
                "coupling",
                "scale_relation",
            ),
        },

        OTMechanism.STRUCTURAL_RECONFIGURATION: {
            "productivity": 1.25,
            "distinctions": (
                "node",
                "topology",
                "boundary_B",
            ),
            "relations": (
                "persistence",
                "coupling",
                "topology_relation",
            ),
        },

        OTMechanism.REPRESENTATION_SPACE: {
            "productivity": 1.15,
            "distinctions": (
                "representation",
                "node",
                "boundary_C",
            ),
            "relations": (
                "persistence",
                "coupling",
                "representation_relation",
            ),
        },
    }

    for branch in branches:

        data = branch_data[
            branch.mechanism
        ]

        branch.preserves_process_continuity = (
            True
        )

        branch.changes_differentiation_conditions = (
            True
        )

        branch.metadata[
            "distinctions"
        ] = data[
            "distinctions"
        ]

        branch.metadata[
            "relations"
        ] = data[
            "relations"
        ]

        branch.metadata[
            "constraints"
        ] = (
            "process_continuity",
        )

        explorer.validate_candidate(
            branch
        )

        if branch.status.value == "VALIDATED":

            explorer.activate(
                branch
            )

        explorer.observe(
            branch,

            productive_difference_before=(
                1.00
            ),

            productive_difference_after=(
                data["productivity"]
            ),

            new_distinctions=(
                len(data["distinctions"])
            ),

            new_questions=2,

            new_deadlocks=0,

            resource_cost=1.0,

            observation_steps=5,
        )

    return branches


# ----------------------------------------------------------------------
# Smoke test
# ----------------------------------------------------------------------


def run_smoke_test() -> Dict[str, Any]:

    uql = (
        InMemoryUQLAdapter()
    )

    integration = (
        Level3EmergentIntegration(
            uql=uql
        )
    )

    branches = (
        build_fixture_branches()
    )

    result = integration.run(
        source_space="C_k",
        branches=branches,
        parent_ref="QUESTION_ROOT",
        next_space="C_k+1",
    )

    assert (
        len(result.exploration.branches)
        == 3
    )

    assert (
        len(result.interaction.branch_ids)
        == 3
    )

    assert (
        result.continuation_ready
        is True
    )

    assert (
        result.process_terminated
        is False
    )

    assert (
        len(result.emergent_records)
        > 0
    )

    assert (
        len(result.generated_question_ids)
        > 0
    )

    assert (
        len(uql.events)
        > 0
    )

    assert (
        len(uql.questions)
        > 0
    )

    # Verify that provenance survived the entire chain.
    for question in uql.questions:

        assert (
            "origin"
            in question.provenance
        )

        assert (
            question.provenance[
                "origin"
            ]
            == "branch_interaction"
        )

    return {
        "benchmark": (
            "level3_emergent_integration_v1"
        ),

        "branches": len(
            result.exploration.branches
        ),

        "interaction_status": (
            result.interaction.status.value
        ),

        "emergent_records": len(
            result.emergent_records
        ),

        "candidate_invariants": len(
            result.invariant_ids
        ),

        "generated_questions": len(
            result.generated_question_ids
        ),

        "uql_events": len(
            uql.events
        ),

        "uql_questions": len(
            uql.questions
        ),

        "next_space": (
            result.next_space
        ),

        "continuation_ready": (
            result.continuation_ready
        ),

        "process_terminated": (
            result.process_terminated
        ),

        "all_passed": True,
    }


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------


def print_report(
    report: Dict[str, Any],
) -> None:

    print(
        "UFCPS — Level 3 Emergent Integration v1"
    )

    print(
        "=" * 64
    )

    for key, value in report.items():

        print(
            f"{key}: {value}"
        )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> int:

    report = (
        run_smoke_test()
    )

    print_report(
        report
    )

    return (
        0
        if report["all_passed"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
