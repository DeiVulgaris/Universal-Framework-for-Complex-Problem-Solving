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
        Generate a single explicitly requested OT branch.

        This is a compatibility adapter for integration layers that
        construct one branch directly.

        The canonical multi-branch API remains:

            generate_candidates(...)

        This method does not select a winning mechanism.
        It only constructs one branch and initializes its declared
        structural properties.
        """

        branches = self.generate_candidates(
            source_space=source_space,
            target_space_prefix=(
                target_space
                if target_space is not None
                else "C_next"
            ),
            mechanisms=[mechanism],
        )

        if not branches:
            raise ValueError(
                f"Unable to generate OT candidate for mechanism: "
                f"{mechanism}"
            )

        branch = branches[0]

        if target_space is not None:
            branch.target_space = target_space

        if branch_id is not None:
            branch.branch_id = branch_id

        branch.preserves_process_continuity = (
            preserves_process_continuity
        )

        branch.changes_differentiation_conditions = (
            changes_differentiation_conditions
        )

        branch.restores_productive_differentiation = (
            restores_productive_differentiation
        )

        branch.productive_difference_before = (
            productive_difference_before
        )

        branch.productive_difference_after = (
            productive_difference_after
        )

        if new_distinctions is not None:
            branch.new_distinctions = list(new_distinctions)

        if new_questions is not None:
            branch.new_questions = list(new_questions)

        if new_deadlocks is not None:
            branch.new_deadlocks = list(new_deadlocks)

        branch.resource_cost = resource_cost

        if evidence is not None:
            branch.evidence = list(evidence)

        if metadata is not None:
            branch.metadata.update(metadata)

        return branch
