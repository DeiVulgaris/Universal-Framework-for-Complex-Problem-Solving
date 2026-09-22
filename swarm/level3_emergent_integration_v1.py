"""
UFCPS — Level 3 Emergent Integration v1

Integrates:

    Orthogonal Transition Explorer
            ↓
    Branch Interaction
            ↓
    UQL persistence
            ↓
    Emergent Space Builder
            ↓
          C_(k+1)

The module is intentionally architectural.

It does not:
    - determine scientific truth;
    - select the best OT mechanism;
    - declare an invariant universally true;
    - measure intelligence;
    - claim consciousness.

Its responsibility is to preserve the process from
interaction-derived distinctions to the next cognitive space.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from orthogonal_transition_explorer_v1 import (
    OrthogonalTransitionExplorer,
    OTMechanism,
)

from branch_interaction_v1 import (
    BranchInteractionEngine,
    LocalizedBranch,
    InteractionResult,
    InteractionStatus,
    InvariantStatus,
)

from emergent_space_builder_v1 import (
    CognitiveSpace,
    EmergentSpaceBuilder,
)


# ----------------------------------------------------------------------
# UQL interface
# ----------------------------------------------------------------------


class UQLAdapter(Protocol):

    def create_question(
        self,
        question: str,
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
#
# This remains a test adapter.
# It is NOT the persistent UQL implementation.
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
# Emergent records
# ----------------------------------------------------------------------


@dataclass
class EmergentRecord:

    record_type: str

    record_id: str

    source_branches: List[str]

    uql_event_id: str

    question_id: Optional[str]

    status: str

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ----------------------------------------------------------------------
# Integration result
# ----------------------------------------------------------------------


@dataclass
class Level3IntegrationResult:

    source_space: str

    exploration_branch_count: int

    interaction: InteractionResult

    emergent_records: List[
        EmergentRecord
    ]

    generated_question_ids: List[str]

    invariant_ids: List[str]

    next_space: CognitiveSpace

    continuation_ready: bool

    process_terminated: bool

    provenance: Dict[str, Any] = field(
        default_factory=dict
    )


# ----------------------------------------------------------------------
# Integration engine
# ----------------------------------------------------------------------


class Level3EmergentIntegration:

    def __init__(
        self,
        uql: Optional[
            UQLAdapter
        ] = None,
    ) -> None:

        self.explorer = (
            OrthogonalTransitionExplorer()
        )

        self.interaction_engine = (
            BranchInteractionEngine()
        )

        self.uql = (
            uql
            if uql is not None
            else InMemoryUQLAdapter()
        )

        self.space_builder = (
            EmergentSpaceBuilder()
        )

    # ------------------------------------------------------------------
    # Localize OT branches
    # ------------------------------------------------------------------

    def localize_branches(
        self,
        branches,
    ) -> List[LocalizedBranch]:

        localized: List[
            LocalizedBranch
        ] = []

        for branch in branches:

            metadata = (
                branch.metadata
            )

            localized.append(
                LocalizedBranch(
                    branch_id=(
                        branch.branch_id
                    ),

                    mechanism=(
                        branch.mechanism.value
                    ),

                    state_id=(
                        branch.target_space
                    ),

                    distinctions=tuple(
                        metadata.get(
                            "distinctions",
                            [],
                        )
                    ),

                    relations=tuple(
                        metadata.get(
                            "relations",
                            [],
                        )
                    ),

                    constraints=(
                        "process_continuity",
                        "changed_differentiation_conditions",
                    ),

                    productive=True,

                    metadata={
                        "source_space":
                            branch.source_space,

                        "resource_cost":
                            branch.resource_cost,
                    },
                )
            )

        return localized

    # ------------------------------------------------------------------
    # Persist emergent distinction
    # ------------------------------------------------------------------

    def persist_emergent_distinction(
        self,
        interaction_id: str,
        distinction,
        branch_ids,
    ) -> EmergentRecord:

        event_id = (
            self.uql.record_event(
                "EMERGENT_DISTINCTION",
                {
                    "interaction_id":
                        interaction_id,

                    "distinction_id":
                        distinction.distinction_id,

                    "description":
                        distinction.description,

                    "source_branches":
                        list(branch_ids),

                    "novelty_basis":
                        distinction.novelty_basis,
                },
            )
        )

        question_id = (
            self.uql.create_question(
                (
                    "What further distinctions "
                    "become accessible through "
                    f"{distinction.distinction_id}?"
                ),

                parent_ref=event_id,

                provenance={
                    "interaction_id":
                        interaction_id,

                    "distinction_id":
                        distinction.distinction_id,

                    "source":
                        "level3_emergent_integration",
                },
            )
        )

        return EmergentRecord(
            record_type="DISTINCTION",

            record_id=(
                distinction.distinction_id
            ),

            source_branches=list(
                branch_ids
            ),

            uql_event_id=event_id,

            question_id=question_id,

            status="ACTIVE",

            metadata={
                "description":
                    distinction.description,

                "novelty_basis":
                    distinction.novelty_basis,
            },
        )

    # ------------------------------------------------------------------
    # Persist invariant
    # ------------------------------------------------------------------

    def persist_candidate_invariant(
        self,
        interaction_id: str,
        invariant,
        branch_ids,
    ) -> EmergentRecord:

        event_id = (
            self.uql.record_event(
                "CANDIDATE_INVARIANT",
                {
                    "interaction_id":
                        interaction_id,

                    "invariant_id":
                        invariant.invariant_id,

                    "relation":
                        invariant.relation,

                    "status":
                        invariant.status.value,

                    "source_branches":
                        list(branch_ids),

                    "preservation_count":
                        invariant.preservation_count,

                    "violation_count":
                        invariant.violation_count,
                },
            )
        )

        question_id = None

        if invariant.status in {
            InvariantStatus.CANDIDATE,
            InvariantStatus.SUPPORTED,
        }:

            question_id = (
                self.uql.create_question(
                    (
                        "Does candidate invariant "
                        f"{invariant.invariant_id} "
                        "remain preserved under "
                        "independent transformations?"
                    ),

                    parent_ref=event_id,

                    provenance={
                        "interaction_id":
                            interaction_id,

                        "invariant_id":
                            invariant.invariant_id,

                        "source":
                            "level3_emergent_integration",
                    },
                )
            )

        return EmergentRecord(
            record_type="INVARIANT",

            record_id=(
                invariant.invariant_id
            ),

            source_branches=list(
                branch_ids
            ),

            uql_event_id=event_id,

            question_id=question_id,

            status=invariant.status.value,

            metadata={
                "relation":
                    invariant.relation,

                "preservation_count":
                    invariant.preservation_count,

                "violation_count":
                    invariant.violation_count,
            },
        )

    # ------------------------------------------------------------------
    # Persist interaction questions
    # ------------------------------------------------------------------

    def persist_interaction_questions(
        self,
        interaction: InteractionResult,
    ) -> List[str]:

        question_ids: List[str] = []

        for question in (
            interaction.new_questions
        ):

            question_id = (
                self.uql.create_question(
                    question,

                    parent_ref=(
                        interaction.interaction_id
                    ),

                    provenance={
                        "source":
                            "branch_interaction",

                        "branches":
                            list(
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
    # Build next cognitive space
    # ------------------------------------------------------------------

    def build_next_space(
        self,
        *,
        source_space_id: str,
        source_space_version: int,
        interaction: InteractionResult,
        question_ids: List[str],
        source_space: Optional[CognitiveSpace] = None,
    ) -> CognitiveSpace:
        """
        Build C_(k+1) from the actual C_k when available.

        Recursive Level 3 requires:

            C_(k+1) = C_k + new_content

        The previous implementation reconstructed a new source
        CognitiveSpace from only source_space_id/version. That
        discarded the accumulated content of C_k before passing
        it to EmergentSpaceBuilder.

        For backward compatibility, if source_space is omitted,
        a minimal source shell is still constructed.
        """

        if source_space is None:
            source_space = CognitiveSpace(
                space_id=source_space_id,
                parent_space_id=None,
                version=source_space_version,
                description=(
                    "Source cognitive space "
                    "for Level 3 emergent integration."
                ),
            )
        else:
            if source_space.space_id != source_space_id:
                raise ValueError(
                    "source_space_id does not match source_space.space_id"
                )

            if source_space.version != source_space_version:
                raise ValueError(
                    "source_space_version does not match "
                    "source_space.version"
                )

        return self.space_builder.build(
            parent_space=source_space,
            interaction=interaction,
            question_ids=question_ids,
            next_space_id=(
                f"{source_space_id}+1"
            ),
        )

    # ------------------------------------------------------------------
    # Main integration
    # ------------------------------------------------------------------

    def run(
        self,
        *,
        source_space_id: str = "C_k",
        source_space_version: int = 1,
        source_space: Optional[CognitiveSpace] = None,
        branches=None,
    ) -> Level3IntegrationResult:

        if source_space is not None:
            if source_space.space_id != source_space_id:
                raise ValueError(
                    "source_space_id does not match "
                    "source_space.space_id"
                )

            if source_space.version != source_space_version:
                raise ValueError(
                    "source_space_version does not match "
                    "source_space.version"
                )

        if branches is None:

            branches = (
                self._default_branches()
            )

        # --------------------------------------------------------------
        # 1. Localize OT branches
        # --------------------------------------------------------------

        localized = (
            self.localize_branches(
                branches
            )
        )

        # --------------------------------------------------------------
        # 2. Interaction
        # --------------------------------------------------------------

        interaction = (
            self.interaction_engine.interact(
                localized
            )
        )

        # --------------------------------------------------------------
        # 3. Persist emergent results
        # --------------------------------------------------------------

        records: List[
            EmergentRecord
        ] = []

        for distinction in (
            interaction.emergent_distinctions
        ):

            records.append(
                self.persist_emergent_distinction(
                    interaction.interaction_id,

                    distinction,

                    interaction.branch_ids,
                )
            )

        for invariant in (
            interaction.candidate_invariants
        ):

            records.append(
                self.persist_candidate_invariant(
                    interaction.interaction_id,

                    invariant,

                    interaction.branch_ids,
                )
            )

        # --------------------------------------------------------------
        # 4. Persist interaction questions
        # --------------------------------------------------------------

        interaction_question_ids = (
            self.persist_interaction_questions(
                interaction
            )
        )

        generated_question_ids = [
            record.question_id
            for record in records
            if record.question_id is not None
        ]

        generated_question_ids.extend(
            interaction_question_ids
        )

        # --------------------------------------------------------------
        # 5. Build C_(k+1)
        # --------------------------------------------------------------

        next_space = (
            self.build_next_space(
                source_space_id=(
                    source_space_id
                ),

                source_space_version=(
                    source_space_version
                ),

                source_space=source_space,

                interaction=interaction,

                question_ids=(
                    generated_question_ids
                ),
            )
        )

        # --------------------------------------------------------------
        # 6. Record continuation
        # --------------------------------------------------------------

        continuation_event = (
            self.uql.record_event(
                "COGNITIVE_SPACE_CREATED",
                {
                    "source_space":
                        source_space_id,

                    "source_version":
                        source_space_version,

                    "next_space":
                        next_space.space_id,

                    "next_version":
                        next_space.version,

                    "interaction_id":
                        interaction.interaction_id,

                    "new_distinctions":
                        list(
                            next_space.accessible_distinctions
                        ),

                    "active_invariants":
                        list(
                            next_space.active_invariants
                        ),

                    "questions":
                        list(
                            next_space.unresolved_questions
                        ),
                },
            )
        )

        provenance = {
            "source_space":
                source_space_id,

            "source_version":
                source_space_version,

            "interaction_id":
                interaction.interaction_id,

            "continuation_event":
                continuation_event,

            "process_terminated":
                False,
        }

        return Level3IntegrationResult(
            source_space=(
                source_space_id
            ),

            exploration_branch_count=(
                len(branches)
            ),

            interaction=interaction,

            emergent_records=records,

            generated_question_ids=(
                generated_question_ids
            ),

            invariant_ids=[
                invariant.invariant_id
                for invariant in (
                    interaction.candidate_invariants
                )
            ],

            next_space=next_space,

            continuation_ready=True,

            process_terminated=False,

            provenance=provenance,
        )

    # ------------------------------------------------------------------
    # Synthetic branches
    # ------------------------------------------------------------------

    def _default_branches(self):

        specifications = [
            (
                OTMechanism.SCALE,
                "C_k_SCALE",
                "scale_relation",
            ),

            (
                OTMechanism.STRUCTURAL_RECONFIGURATION,
                "C_k_STRUCTURAL",
                "structural_relation",
            ),

            (
                OTMechanism.REPRESENTATION_SPACE,
                "C_k_REPRESENTATION",
                "representation_relation",
            ),
        ]

        branches = []

        for index, (
            mechanism,
            target_space,
            relation,
        ) in enumerate(
            specifications,
            start=1,
        ):

            branch = (
                self.explorer.generate_candidate(
                    mechanism=mechanism,

                    source_space="C_k",

                    target_space=target_space,

                    preserves_process_continuity=True,

                    changes_differentiation_conditions=True,

                    restores_productive_differentiation=True,

                    metadata={
                        "distinctions": [
                            f"D_branch_{index}_1",
                            f"D_branch_{index}_2",
                        ],

                        "relations": [
                            "persistence",
                            "coupling",
                            relation,
                        ],
                    },
                )
            )

            if self.explorer.validate_candidate(
                branch
            ):

                branches.append(
                    branch
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

    source = CognitiveSpace(
        space_id="C_k",
        parent_space_id=None,
        version=1,
        accessible_distinctions=[
            "D_existing_1",
            "D_existing_2",
        ],
        active_invariants=[
            "I_existing",
        ],
        unresolved_questions=[
            "Q_existing",
        ],
        relations=[
            "EXISTING_RELATION",
        ],
        structural_continuity=True,
        content_identity_with_parent=False,
        description="Seed source cognitive space.",
    )

    result = integration.run(
        source_space_id=source.space_id,

        source_space_version=source.version,

        source_space=source,
    )

    checks = {
        "multiple_branches": (
            result.exploration_branch_count
            >= 3
        ),

        "interaction_occurred": (
            result.interaction.status
            != InteractionStatus.NOT_INTERACTED
        ),

        "emergent_output_exists": (
            len(
                result.emergent_records
            )
            > 0
        ),

        "new_distinction_exists": (
            len(
                result.interaction.emergent_distinctions
            )
            > 0
        ),

        "invariant_candidate_exists": (
            len(
                result.interaction.candidate_invariants
            )
            > 0
        ),

        "uql_questions_created": (
            len(
                uql.questions
            )
            > 0
        ),

        "uql_events_created": (
            len(
                uql.events
            )
            > 0
        ),

        "next_space_created": (
            result.next_space.space_id
            == "C_k+1"
        ),

        "next_space_version_advanced": (
            result.next_space.version
            == 2
        ),

        "new_distinction_entered_space": (
            len(
                result.next_space
                .accessible_distinctions
            )
            > 0
        ),

        "questions_entered_space": (
            len(
                result.next_space
                .unresolved_questions
            )
            > 0
        ),

        "source_content_survives": (
            "D_existing_1"
            in result.next_space.accessible_distinctions
            and
            "D_existing_2"
            in result.next_space.accessible_distinctions
            and
            "I_existing"
            in result.next_space.active_invariants
            and
            "Q_existing"
            in result.next_space.unresolved_questions
            and
            "EXISTING_RELATION"
            in result.next_space.relations
        ),

        "new_content_added_after_inheritance": (
            len(result.next_space.elements)
            > len(source.elements)
        ),

        "continuation_ready": (
            result.continuation_ready
            is True
        ),

        "process_not_terminated": (
            result.process_terminated
            is False
        ),

        "provenance_preserved": (
            result.provenance[
                "source_space"
            ]
            == "C_k"
        ),

        "cognitive_space_event_recorded": (
            any(
                event.event_type
                == "COGNITIVE_SPACE_CREATED"
                for event in uql.events
            )
        ),
    }

    all_passed = all(
        checks.values()
    )

    return {
        "benchmark":
            "level3_emergent_integration_v1",

        "all_passed":
            all_passed,

        "checks":
            checks,

        "exploration_branch_count":
            result.exploration_branch_count,

        "interaction_status":
            result.interaction.status.value,

        "emergent_record_count":
            len(
                result.emergent_records
            ),

        "question_count":
            len(
                uql.questions
            ),

        "event_count":
            len(
                uql.events
            ),

        "next_space":
            result.next_space.space_id,

        "next_space_version":
            result.next_space.version,

        "accessible_distinctions":
            len(
                result.next_space
                .accessible_distinctions
            ),

        "active_invariants":
            len(
                result.next_space
                .active_invariants
            ),

        "unresolved_questions":
            len(
                result.next_space
                .unresolved_questions
            ),

        "process_terminated":
            result.process_terminated,
    }


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> int:

    report = (
        run_smoke_test()
    )

    print(
        "UFCPS — Level 3 Emergent Integration v1"
    )

    print(
        "=" * 68
    )

    for key, value in report.items():

        print(
            f"{key}: {value}"
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
