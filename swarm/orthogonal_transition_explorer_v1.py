"""
UFCPS Level 3 — Orthogonal Transition Explorer v1

Explores multiple candidate orthogonal transitions in parallel.

Core principle:

    PREPARE_OT != SELECT_ONE_OT

The explorer may construct, validate, activate and observe multiple
transition branches without selecting a single "winner".

An orthogonal transition (OT) is defined structurally by:

    1. preservation of process continuity;
    2. change in the conditions of further differentiation;
    3. restoration or expansion of productive differentiation.

No concrete mechanism is constitutive of OT.

Candidate mechanisms include:

    SCALE
    COMPENSATORY_MULTIPLICATION
    STRUCTURAL_RECONFIGURATION
    CARRIER_TRANSITION
    INTERACTION_REGIME
    REPRESENTATION_SPACE
    COMPOSITION_DECOMPOSITION
    UNKNOWN_EMERGENT

This module is an experimental architecture component.
It does not claim that any mechanism is a physical law.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class OTMechanism(str, Enum):
    """Candidate mechanisms for orthogonal transition."""

    SCALE = "scale"
    COMPENSATORY_MULTIPLICATION = "compensatory_multiplication"
    STRUCTURAL_RECONFIGURATION = "structural_reconfiguration"
    CARRIER_TRANSITION = "carrier_transition"
    INTERACTION_REGIME = "interaction_regime"
    REPRESENTATION_SPACE = "representation_space"
    COMPOSITION_DECOMPOSITION = "composition_decomposition"
    UNKNOWN_EMERGENT = "unknown_emergent"


class BranchStatus(str, Enum):
    """Lifecycle state of an OT exploration branch."""

    PROPOSED = "proposed"
    VALIDATED = "validated"
    ACTIVE = "active"
    COMPLETED = "completed"
    DEADLOCK = "deadlock"
    FAILED = "failed"
    INSUFFICIENT_DATA = "insufficient_data"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class OTBranch:
    """
    One candidate transition branch.

    A branch is an experimental object, not a selected solution.
    """

    branch_id: str
    mechanism: OTMechanism

    source_space: str
    target_space: str

    status: BranchStatus = BranchStatus.PROPOSED

    preserves_process_continuity: bool = True
    changes_differentiation_conditions: bool = True
    restores_productive_differentiation: bool = False

    productive_difference_before: float = 0.0
    productive_difference_after: float = 0.0

    new_distinctions: List[str] = field(default_factory=list)
    new_questions: List[str] = field(default_factory=list)
    new_deadlocks: List[str] = field(default_factory=list)

    resource_cost: float = 0.0
    observation_steps: int = 0

    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BranchProductivity:
    """Descriptive productivity measurements for one branch."""

    branch_id: str
    mechanism: OTMechanism

    productive_difference_before: float
    productive_difference_after: float

    delta: float
    ratio: float

    new_distinction_count: int
    new_question_count: int
    new_deadlock_count: int

    resource_cost: float
    efficiency: float

    productive: bool


@dataclass
class ExplorationResult:
    """
    Result of parallel OT exploration.

    No branch is selected as globally superior.
    """

    source_space: str
    branches: List[OTBranch]

    completed_branches: List[str] = field(default_factory=list)
    deadlocked_branches: List[str] = field(default_factory=list)
    failed_branches: List[str] = field(default_factory=list)
    insufficient_data_branches: List[str] = field(default_factory=list)

    productivity: List[BranchProductivity] = field(default_factory=list)

    continuity_preserved: bool = True

    selection_required: bool = False

    productive_frontier: List[str] = field(default_factory=list)

    description: str = ""


@dataclass
class ExplorerConfig:
    """
    Configuration for OT exploration.

    Thresholds are experimental and descriptive.
    """

    min_productivity_delta: float = 0.01
    min_productivity_ratio: float = 1.01
    min_observations_for_completion: int = 1

    require_process_continuity: bool = True
    require_changed_conditions: bool = True

    allow_unknown_emergent: bool = True


# ---------------------------------------------------------------------------
# Explorer
# ---------------------------------------------------------------------------


class OrthogonalTransitionExplorer:
    """
    Parallel exploratory engine for candidate orthogonal transitions.

    The Explorer does not decide which mechanism is "correct".
    It preserves multiple candidate branches and compares their
    observed properties descriptively.
    """

    def __init__(
        self,
        config: Optional[ExplorerConfig] = None,
    ) -> None:
        self.config = config or ExplorerConfig()

        self.branches: Dict[str, OTBranch] = {}
        self._branch_counter: int = 0

    # ------------------------------------------------------------------
    # Branch creation
    # ------------------------------------------------------------------

    def _next_branch_id(self) -> str:
        self._branch_counter += 1
        return f"OT_BRANCH_{self._branch_counter:03d}"

    def generate_candidates(
        self,
        source_space: str,
        target_space_prefix: str = "C_next",
        mechanisms: Optional[Iterable[OTMechanism]] = None,
    ) -> List[OTBranch]:
        """
        Generate multiple candidate branches.

        This is the canonical multi-branch API.
        """

        if mechanisms is None:
            mechanisms = list(OTMechanism)

        branches: List[OTBranch] = []

        for mechanism in mechanisms:
            if not isinstance(mechanism, OTMechanism):
                mechanism = OTMechanism(mechanism)

            branch_id = self._next_branch_id()

            branch = OTBranch(
                branch_id=branch_id,
                mechanism=mechanism,
                source_space=source_space,
                target_space=f"{target_space_prefix}_{len(branches)}",
            )

            self.branches[branch.branch_id] = branch
            branches.append(branch)

        return branches

    def generate_candidate(
        self,
        source_space: str,
        mechanism: OTMechanism,
        target_space: Optional[str] = None,
        branch_id: Optional[str] = None,
        preserves_process_continuity: bool = True,
        changes_differentiation_conditions: bool = True,
        restores_productive_differentiation: bool = False,
        productive_difference_before: float = 0.0,
        productive_difference_after: float = 0.0,
        new_distinctions: Optional[Iterable[str]] = None,
        new_questions: Optional[Iterable[str]] = None,
        new_deadlocks: Optional[Iterable[str]] = None,
        resource_cost: float = 0.0,
        evidence: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OTBranch:
        """
        Generate one explicitly requested OT branch.

        Compatibility adapter for integration layers that need to
        construct a single branch directly.

        The canonical multi-branch API remains:

            generate_candidates(...)

        This method does not select a winning mechanism.
        It only constructs one explicitly requested branch and
        initializes its declared properties.
        """

        if not isinstance(mechanism, OTMechanism):
            mechanism = OTMechanism(mechanism)

        branch = OTBranch(
            branch_id=(
                branch_id
                if branch_id is not None
                else self._next_branch_id()
            ),
            mechanism=mechanism,
            source_space=source_space,
            target_space=(
                target_space
                if target_space is not None
                else f"C_next_{self._branch_counter}"
            ),
            preserves_process_continuity=(
                preserves_process_continuity
            ),
            changes_differentiation_conditions=(
                changes_differentiation_conditions
            ),
            restores_productive_differentiation=(
                restores_productive_differentiation
            ),
            productive_difference_before=(
                productive_difference_before
            ),
            productive_difference_after=(
                productive_difference_after
            ),
            new_distinctions=(
                list(new_distinctions)
                if new_distinctions is not None
                else []
            ),
            new_questions=(
                list(new_questions)
                if new_questions is not None
                else []
            ),
            new_deadlocks=(
                list(new_deadlocks)
                if new_deadlocks is not None
                else []
            ),
            resource_cost=resource_cost,
            evidence=(
                list(evidence)
                if evidence is not None
                else []
            ),
            metadata=(
                dict(metadata)
                if metadata is not None
                else {}
            ),
        )

        self.branches[branch.branch_id] = branch

        return branch

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_candidate(
        self,
        branch: OTBranch,
    ) -> OTBranch:
        """
        Validate the structural conditions of a candidate.

        Required:

            process continuity
            changed differentiation conditions

        The method does not require immediate productive restoration,
        because productivity is an empirical observation.
        """

        if (
            self.config.require_process_continuity
            and not branch.preserves_process_continuity
        ):
            branch.status = BranchStatus.FAILED
            branch.evidence.append(
                "Process continuity requirement failed."
            )
            return branch

        if (
            self.config.require_changed_conditions
            and not branch.changes_differentiation_conditions
        ):
            branch.status = BranchStatus.FAILED
            branch.evidence.append(
                "Differentiation conditions were not changed."
            )
            return branch

        if (
            branch.mechanism == OTMechanism.UNKNOWN_EMERGENT
            and not self.config.allow_unknown_emergent
        ):
            branch.status = BranchStatus.FAILED
            branch.evidence.append(
                "Unknown/emergent mechanism is disabled."
            )
            return branch

        branch.status = BranchStatus.VALIDATED
        branch.evidence.append(
            "Structural OT conditions validated."
        )

        return branch

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    def activate(
        self,
        branch: OTBranch,
    ) -> OTBranch:
        """
        Activate a validated branch.

        Activation is not selection.
        """

        if branch.status != BranchStatus.VALIDATED:
            branch.status = BranchStatus.FAILED
            branch.evidence.append(
                "Only VALIDATED branches can be activated."
            )
            return branch

        branch.status = BranchStatus.ACTIVE
        branch.evidence.append(
            "Branch activated for observation."
        )

        return branch

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def observe(
        self,
        branch: OTBranch,
        productive_difference_after: float,
        new_distinctions: Optional[Iterable[str]] = None,
        new_questions: Optional[Iterable[str]] = None,
        new_deadlocks: Optional[Iterable[str]] = None,
        resource_cost: Optional[float] = None,
        evidence: Optional[Iterable[str]] = None,
        observation_step: Optional[int] = None,
    ) -> OTBranch:
        """
        Record one observation for an active branch.

        Observation itself does not imply success.
        """

        if branch.status not in {
            BranchStatus.ACTIVE,
            BranchStatus.VALIDATED,
            BranchStatus.INSUFFICIENT_DATA,
        }:
            branch.evidence.append(
                "Observation rejected: branch is not active."
            )
            return branch

        if branch.status == BranchStatus.VALIDATED:
            branch.status = BranchStatus.ACTIVE

        branch.productive_difference_after = float(
            productive_difference_after
        )

        if new_distinctions is not None:
            branch.new_distinctions.extend(
                str(item) for item in new_distinctions
            )

        if new_questions is not None:
            branch.new_questions.extend(
                str(item) for item in new_questions
            )

        if new_deadlocks is not None:
            branch.new_deadlocks.extend(
                str(item) for item in new_deadlocks
            )

        if resource_cost is not None:
            branch.resource_cost = float(resource_cost)

        if evidence is not None:
            branch.evidence.extend(
                str(item) for item in evidence
            )

        if observation_step is not None:
            branch.observation_steps = max(
                branch.observation_steps,
                int(observation_step),
            )
        else:
            branch.observation_steps += 1

        branch.restores_productive_differentiation = (
            self._is_productive(branch)
        )

        if branch.observation_steps < (
            self.config.min_observations_for_completion
        ):
            branch.status = BranchStatus.INSUFFICIENT_DATA
            return branch

        if branch.restores_productive_differentiation:
            branch.status = BranchStatus.COMPLETED
        elif branch.new_deadlocks:
            branch.status = BranchStatus.DEADLOCK
        else:
            branch.status = BranchStatus.INSUFFICIENT_DATA

        return branch

    # ------------------------------------------------------------------
    # Productivity
    # ------------------------------------------------------------------

    def _productivity_delta(
        self,
        branch: OTBranch,
    ) -> float:
        return (
            branch.productive_difference_after
            - branch.productive_difference_before
        )

    def _productivity_ratio(
        self,
        branch: OTBranch,
    ) -> float:
        before = branch.productive_difference_before
        after = branch.productive_difference_after

        if before == 0.0:
            if after > 0.0:
                return float("inf")
            return 1.0

        return after / before

    def _is_productive(
        self,
        branch: OTBranch,
    ) -> bool:
        delta = self._productivity_delta(branch)
        ratio = self._productivity_ratio(branch)

        return (
            delta >= self.config.min_productivity_delta
            and ratio >= self.config.min_productivity_ratio
        )

    def productivity(
        self,
        branch: OTBranch,
    ) -> BranchProductivity:
        """
        Produce descriptive productivity measurements.

        This does not rank the branch globally.
        """

        delta = self._productivity_delta(branch)
        ratio = self._productivity_ratio(branch)

        distinction_count = len(
            set(branch.new_distinctions)
        )

        question_count = len(
            set(branch.new_questions)
        )

        deadlock_count = len(
            set(branch.new_deadlocks)
        )

        if branch.resource_cost > 0.0:
            efficiency = delta / branch.resource_cost
        else:
            efficiency = (
                delta
                if delta > 0.0
                else 0.0
            )

        productive = self._is_productive(branch)

        return BranchProductivity(
            branch_id=branch.branch_id,
            mechanism=branch.mechanism,
            productive_difference_before=(
                branch.productive_difference_before
            ),
            productive_difference_after=(
                branch.productive_difference_after
            ),
            delta=delta,
            ratio=ratio,
            new_distinction_count=distinction_count,
            new_question_count=question_count,
            new_deadlock_count=deadlock_count,
            resource_cost=branch.resource_cost,
            efficiency=efficiency,
            productive=productive,
        )

    # ------------------------------------------------------------------
    # Exploration
    # ------------------------------------------------------------------

    def explore(
        self,
        branches: Sequence[OTBranch],
        observations: Optional[
            Dict[str, Dict[str, Any]]
        ] = None,
    ) -> ExplorationResult:
        """
        Validate, activate and optionally observe branches.

        No branch is selected.

        `observations` is keyed by branch_id and may contain:

            productive_difference_after
            new_distinctions
            new_questions
            new_deadlocks
            resource_cost
            evidence
            observation_step
        """

        observations = observations or {}

        processed: List[OTBranch] = []

        for branch in branches:
            if branch.status == BranchStatus.PROPOSED:
                self.validate_candidate(branch)

            if branch.status == BranchStatus.VALIDATED:
                self.activate(branch)

            payload = observations.get(
                branch.branch_id
            )

            if payload is not None:
                self.observe(
                    branch,
                    productive_difference_after=float(
                        payload.get(
                            "productive_difference_after",
                            branch.productive_difference_after,
                        )
                    ),
                    new_distinctions=payload.get(
                        "new_distinctions"
                    ),
                    new_questions=payload.get(
                        "new_questions"
                    ),
                    new_deadlocks=payload.get(
                        "new_deadlocks"
                    ),
                    resource_cost=payload.get(
                        "resource_cost"
                    ),
                    evidence=payload.get(
                        "evidence"
                    ),
                    observation_step=payload.get(
                        "observation_step"
                    ),
                )

            processed.append(branch)

        completed = [
            branch.branch_id
            for branch in processed
            if branch.status == BranchStatus.COMPLETED
        ]

        deadlocked = [
            branch.branch_id
            for branch in processed
            if branch.status == BranchStatus.DEADLOCK
        ]

        failed = [
            branch.branch_id
            for branch in processed
            if branch.status == BranchStatus.FAILED
        ]

        insufficient = [
            branch.branch_id
            for branch in processed
            if branch.status == BranchStatus.INSUFFICIENT_DATA
        ]

        productivity_results = [
            self.productivity(branch)
            for branch in processed
        ]

        continuity_preserved = all(
            branch.preserves_process_continuity
            for branch in processed
        )

        frontier = self._compute_productivity_frontier(
            productivity_results
        )

        return ExplorationResult(
            source_space=(
                processed[0].source_space
                if processed
                else ""
            ),
            branches=list(processed),
            completed_branches=completed,
            deadlocked_branches=deadlocked,
            failed_branches=failed,
            insufficient_data_branches=insufficient,
            productivity=productivity_results,
            continuity_preserved=continuity_preserved,
            selection_required=False,
            productive_frontier=frontier,
            description=(
                "Parallel OT exploration completed without "
                "selecting a globally preferred branch."
            ),
        )

    # ------------------------------------------------------------------
    # Descriptive comparison
    # ------------------------------------------------------------------

    def compare_productivity(
        self,
        branches: Sequence[OTBranch],
    ) -> List[BranchProductivity]:
        """
        Return descriptive productivity observations.

        Ordering is only a convenient deterministic presentation order.
        It must not be interpreted as a winner selection.
        """

        results = [
            self.productivity(branch)
            for branch in branches
        ]

        return sorted(
            results,
            key=lambda item: (
                -item.delta,
                -item.new_distinction_count,
                item.resource_cost,
                item.branch_id,
            ),
        )

    def _dominates(
        self,
        left: BranchProductivity,
        right: BranchProductivity,
    ) -> bool:
        """
        Pareto-style descriptive dominance.

        Dimensions:

            productivity delta
            new distinctions
            resource efficiency
        """

        left_values = (
            left.delta,
            float(left.new_distinction_count),
            left.efficiency,
        )

        right_values = (
            right.delta,
            float(right.new_distinction_count),
            right.efficiency,
        )

        at_least_one_strict = False

        for lv, rv in zip(
            left_values,
            right_values,
        ):
            if lv < rv:
                return False

            if lv > rv:
                at_least_one_strict = True

        return at_least_one_strict

    def _compute_productivity_frontier(
        self,
        productivity_results: Sequence[BranchProductivity],
    ) -> List[str]:
        """
        Compute a non-dominated descriptive frontier.

        This is not a winner ranking.
        """

        frontier: List[str] = []

        for candidate in productivity_results:
            dominated = False

            for other in productivity_results:
                if other.branch_id == candidate.branch_id:
                    continue

                if self._dominates(
                    other,
                    candidate,
                ):
                    dominated = True
                    break

            if not dominated:
                frontier.append(
                    candidate.branch_id
                )

        return frontier

    def productivity_frontier(
        self,
        branches: Sequence[OTBranch],
    ) -> List[str]:
        """
        Public access to the descriptive productivity frontier.
        """

        results = [
            self.productivity(branch)
            for branch in branches
        ]

        return self._compute_productivity_frontier(
            results
        )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_report(
    result: ExplorationResult,
) -> None:
    """Print a compact human-readable exploration report."""

    print()
    print("=" * 72)
    print("UFCPS LEVEL 3 — ORTHOGONAL TRANSITION EXPLORER")
    print("=" * 72)

    print(
        f"Source space: {result.source_space}"
    )

    print(
        f"Branches: {len(result.branches)}"
    )

    print(
        f"Continuity preserved: "
        f"{result.continuity_preserved}"
    )

    print(
        f"Selection required: "
        f"{result.selection_required}"
    )

    print(
        f"Completed: "
        f"{len(result.completed_branches)}"
    )

    print(
        f"Deadlocked: "
        f"{len(result.deadlocked_branches)}"
    )

    print(
        f"Failed: "
        f"{len(result.failed_branches)}"
    )

    print(
        f"Insufficient data: "
        f"{len(result.insufficient_data_branches)}"
    )

    print()
    print("PRODUCTIVITY")

    for item in result.productivity:
        print(
            f"  {item.branch_id}: "
            f"{item.mechanism.value} | "
            f"delta={item.delta:.4f} | "
            f"ratio={item.ratio:.4f} | "
            f"new={item.new_distinction_count} | "
            f"cost={item.resource_cost:.4f} | "
            f"productive={item.productive}"
        )

    print()
    print(
        "Productivity frontier: "
        f"{result.productive_frontier}"
    )

    print()
    print(result.description)
    print("=" * 72)


# ---------------------------------------------------------------------------
# Demonstration
# ---------------------------------------------------------------------------


def demo() -> ExplorationResult:
    """
    Run a small synthetic demonstration.

    The values are illustrative only.
    """

    explorer = OrthogonalTransitionExplorer()

    branches = explorer.generate_candidates(
        source_space="C_0",
        target_space_prefix="C_1",
    )

    observations: Dict[str, Dict[str, Any]] = {}

    for index, branch in enumerate(branches):
        before = 0.20

        after = (
            0.45
            if index % 3 == 0
            else 0.30
            if index % 3 == 1
            else 0.18
        )

        observations[branch.branch_id] = {
            "productive_difference_after": after,
            "new_distinctions": [
                f"{branch.mechanism.value}_D_{index}"
            ],
            "new_questions": [
                f"{branch.mechanism.value}_Q_{index}"
            ],
            "resource_cost": 1.0 + index * 0.25,
            "evidence": [
                "Synthetic demonstration observation."
            ],
            "observation_step": 1,
        }

        branch.productive_difference_before = before

    return explorer.explore(
        branches,
        observations,
    )


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------


def run_smoke_test() -> bool:
    """
    Basic structural smoke test.

    Expected:

        one branch for each OT mechanism;
        all branches preserve continuity;
        no automatic branch selection;
        comparison data available.
    """

    explorer = OrthogonalTransitionExplorer()

    branches = explorer.generate_candidates(
        source_space="C_test",
        target_space_prefix="C_next",
    )

    assert len(branches) == len(OTMechanism)

    for branch in branches:
        assert branch.source_space == "C_test"
        assert branch.preserves_process_continuity
        assert branch.status == BranchStatus.PROPOSED

    result = explorer.explore(
        branches,
        observations={
            branch.branch_id: {
                "productive_difference_after": 0.20,
                "new_distinctions": [
                    f"D_{branch.branch_id}"
                ],
                "observation_step": 1,
            }
            for branch in branches
        },
    )

    assert len(result.branches) == len(
        OTMechanism
    )

    assert len(result.productivity) == len(
        OTMechanism
    )

    assert result.continuity_preserved is True

    assert result.selection_required is False

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run demonstration and smoke test."""

    result = demo()

    print_report(result)

    smoke_passed = run_smoke_test()

    print()
    print(
        "SMOKE TEST:",
        "PASS" if smoke_passed else "FAIL",
    )

    if not smoke_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
