"""Composite Checkpoint Manager.

Application Service that manages checkpoint state for composite pipelines.
Enables resume capability after failures.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class CompositeCheckpointState:
    """Immutable checkpoint state for composite pipeline.

    Tracks progress through composite execution phases:
    - FSM state (current phase of execution)
    - Seed completion
    - Individual dependency completions
    - Individual enricher completions
    - Any intermediate state needed for resume

    Attributes:
        composite_name: Name of the composite pipeline.
        run_id: Composite run ID.
        state: Current FSM state of the pipeline.
        seed_completed: Whether seed pipeline completed.
        seed_result: Result from seed if completed.
        completed_dependencies: Set of completed dependency names.
        dependency_results: Results from completed dependencies.
        completed_enrichers: Set of completed enricher names.
        enrichment_results: Results from completed enrichers.
        created_at: When checkpoint was created.
        updated_at: When checkpoint was last updated.

    Example:
        >>> state = CompositeCheckpointState(
        ...     composite_name="composite_publication",
        ...     run_id="abc-123",
        ... )
        >>> state.state
        <CompositePipelineState.NOT_STARTED: 'NOT_STARTED'>
        >>> state.seed_completed
        False
        >>> new_state = state.with_seed_completed(seed_result)
        >>> new_state.seed_completed
        True
        >>> new_state.state
        <CompositePipelineState.SEED_COMPLETED: 'SEED_COMPLETED'>
    """

    composite_name: str
    run_id: str
    state: CompositePipelineState = CompositePipelineState.NOT_STARTED
    seed_completed: bool = False
    seed_result: SeedResult | None = None
    completed_dependencies: frozenset[str] = field(default_factory=frozenset)
    dependency_results: dict[str, DependencyResult] = field(default_factory=dict)
    completed_enrichers: frozenset[str] = field(default_factory=frozenset)
    enrichment_results: dict[str, EnrichmentResult] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def with_seed_completed(self, result: SeedResult) -> CompositeCheckpointState:
        """Create new state with seed marked as completed.

        Sets state to SEED_COMPLETED to indicate seed phase is done.

        Args:
            result: Operation result.

        Returns:
            New instance with the applied change.
        """
        return CompositeCheckpointState(
            composite_name=self.composite_name,
            run_id=self.run_id,
            state=CompositePipelineState.SEED_COMPLETED,
            seed_completed=True,
            seed_result=result,
            completed_dependencies=self.completed_dependencies,
            dependency_results=self.dependency_results,
            completed_enrichers=self.completed_enrichers,
            enrichment_results=self.enrichment_results,
            created_at=self.created_at,
            updated_at=datetime.now(tz=UTC),
        )

    def with_dependency_completed(
        self, dependency_name: str, result: DependencyResult
    ) -> CompositeCheckpointState:
        """Create new state with dependency marked as completed.

        Sets state to DEPENDENCIES_RUNNING to indicate dependency phase is in progress.
        The transition to DEPENDENCIES_COMPLETED should be done explicitly
        via with_state() when all dependencies are done.

        Args:
            dependency_name: Dependency pipeline name.
            result: Operation result.

        Returns:
            New instance with the applied change.
        """
        new_completed = self.completed_dependencies | {dependency_name}
        new_results = {**self.dependency_results, dependency_name: result}
        return CompositeCheckpointState(
            composite_name=self.composite_name,
            run_id=self.run_id,
            state=CompositePipelineState.DEPENDENCIES_RUNNING,
            seed_completed=self.seed_completed,
            seed_result=self.seed_result,
            completed_dependencies=frozenset(new_completed),
            dependency_results=new_results,
            completed_enrichers=self.completed_enrichers,
            enrichment_results=self.enrichment_results,
            created_at=self.created_at,
            updated_at=datetime.now(tz=UTC),
        )

    def with_enricher_completed(
        self, enricher_name: str, result: EnrichmentResult
    ) -> CompositeCheckpointState:
        """Create new state with enricher marked as completed.

        Sets state to ENRICHING to indicate enrichment phase is in progress.
        The transition to ENRICHMENT_COMPLETED should be done explicitly
        via with_state() when all enrichers are done.

        Args:
            enricher_name: Enricher pipeline name.
            result: Operation result.

        Returns:
            New instance with the applied change.
        """
        new_completed = self.completed_enrichers | {enricher_name}
        new_results = {**self.enrichment_results, enricher_name: result}
        return CompositeCheckpointState(
            composite_name=self.composite_name,
            run_id=self.run_id,
            state=CompositePipelineState.ENRICHING,
            seed_completed=self.seed_completed,
            seed_result=self.seed_result,
            completed_dependencies=self.completed_dependencies,
            dependency_results=self.dependency_results,
            completed_enrichers=frozenset(new_completed),
            enrichment_results=new_results,
            created_at=self.created_at,
            updated_at=datetime.now(tz=UTC),
        )

    def with_state(self, new_state: CompositePipelineState) -> CompositeCheckpointState:
        """Create new state with updated FSM state.

        Allows Runner to explicitly set state transitions (e.g., to MERGING,
        ENRICHMENT_COMPLETED, DEPENDENCIES_COMPLETED, FAILED, or COMPLETED)
        without modifying other fields.

        Args:
            new_state: New FSM state to set.

        Returns:
            New checkpoint state with updated FSM state.
        """
        return CompositeCheckpointState(
            composite_name=self.composite_name,
            run_id=self.run_id,
            state=new_state,
            seed_completed=self.seed_completed,
            seed_result=self.seed_result,
            completed_dependencies=self.completed_dependencies,
            dependency_results=self.dependency_results,
            completed_enrichers=self.completed_enrichers,
            enrichment_results=self.enrichment_results,
            created_at=self.created_at,
            updated_at=datetime.now(tz=UTC),
        )

    @property
    def is_resumable(self) -> bool:
        """Check if this checkpoint can be resumed.

        Uses FSM state for more precise resume capability check.
        Falls back to flags for backward compatibility.
        """
        # Use FSM state if available and meaningful
        if self.state.is_resumable:
            return True
        # Fallback to flags for backward compatibility
        return self.seed_completed or bool(self.completed_enrichers)

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation.
        """
        return {
            "composite_name": self.composite_name,
            "run_id": self.run_id,
            "state": self.state.value,
            "seed_completed": self.seed_completed,
            "seed_result": self._serialize_seed_result(),
            "completed_dependencies": list(self.completed_dependencies),
            "dependency_results": self._serialize_dependency_results(),
            "completed_enrichers": list(self.completed_enrichers),
            "enrichment_results": self._serialize_enrichment_results(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def _serialize_seed_result(self) -> dict[str, object] | None:
        """Serialize seed result for JSON."""
        if not self.seed_result:
            return None
        return {
            "pipeline_name": self.seed_result.pipeline_name,
            "records_extracted": self.seed_result.records_extracted,
            "records_silver": self.seed_result.records_silver,
            "keys_generated": self.seed_result.keys_generated,
            "duration_seconds": self.seed_result.duration_seconds,
            "resumed": self.seed_result.resumed,
        }

    def _serialize_dependency_results(self) -> dict[str, dict[str, object]]:
        """Serialize dependency results for JSON."""
        return {
            name: {
                "pipeline_name": result.pipeline_name,
                "status": result.status.value,
                "records_extracted": result.records_extracted,
                "records_silver": result.records_silver,
                "duration_seconds": result.duration_seconds,
                "error_message": result.error_message,
                "resumed": result.resumed,
            }
            for name, result in self.dependency_results.items()
        }

    def _serialize_enrichment_results(self) -> dict[str, dict[str, object]]:
        """Serialize enrichment results for JSON."""
        return {
            name: {
                "enricher_name": result.enricher_name,
                "status": result.status.value,
                "records_input": result.records_input,
                "records_enriched": result.records_enriched,
                "records_not_found": result.records_not_found,
                "records_errored": result.records_errored,
                "dq_error_rate": result.dq_error_rate,
                "duration_seconds": result.duration_seconds,
                "error_message": result.error_message,
            }
            for name, result in self.enrichment_results.items()
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompositeCheckpointState:
        """Create state from dictionary.

        Handles backward compatibility for checkpoints without state field
        or dependency fields. Gracefully handles corrupted state values
        by defaulting to NOT_STARTED.

        Args:
            data: Input data.

        Returns:
            New instance constructed from the input.
        """
        seed_result = None
        if data.get("seed_result"):
            sr = data["seed_result"]
            seed_result = SeedResult(
                pipeline_name=sr["pipeline_name"],
                records_extracted=sr.get("records_extracted", 0),
                records_silver=sr.get("records_silver", 0),
                keys_generated=sr.get("keys_generated", 0),
                duration_seconds=sr.get("duration_seconds", 0.0),
                resumed=sr.get("resumed", False),
            )

        # Parse dependency results (backward compatible - may not exist)
        dependency_results: dict[str, DependencyResult] = {}
        for name, dr_data in data.get("dependency_results", {}).items():
            dependency_results[name] = DependencyResult(
                pipeline_name=dr_data["pipeline_name"],
                status=DependencyStatus(dr_data["status"]),
                records_extracted=dr_data.get("records_extracted", 0),
                records_silver=dr_data.get("records_silver", 0),
                duration_seconds=dr_data.get("duration_seconds", 0.0),
                error_message=dr_data.get("error_message"),
                resumed=dr_data.get("resumed", False),
            )

        enrichment_results: dict[str, EnrichmentResult] = {}
        for name, er_data in data.get("enrichment_results", {}).items():
            enrichment_results[name] = EnrichmentResult(
                enricher_name=er_data["enricher_name"],
                status=EnrichmentStatus(er_data["status"]),
                records_input=er_data.get("records_input", 0),
                records_enriched=er_data.get("records_enriched", 0),
                records_not_found=er_data.get("records_not_found", 0),
                records_errored=er_data.get("records_errored", 0),
                dq_error_rate=er_data.get("dq_error_rate", 0.0),
                duration_seconds=er_data.get("duration_seconds", 0.0),
                error_message=er_data.get("error_message"),
            )

        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)

        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)

        # Parse state with backward compatibility and error handling
        state = CompositePipelineState.NOT_STARTED
        state_value = data.get("state")
        if state_value is not None:
            try:
                state = CompositePipelineState(state_value)
            except ValueError:
                # Corrupted state value - use conservative default
                # Logging will be handled by CompositeCheckpointManager
                state = CompositePipelineState.NOT_STARTED

        return cls(
            composite_name=data["composite_name"],
            run_id=data["run_id"],
            state=state,
            seed_completed=data.get("seed_completed", False),
            seed_result=seed_result,
            completed_dependencies=frozenset(data.get("completed_dependencies", [])),
            dependency_results=dependency_results,
            completed_enrichers=frozenset(data.get("completed_enrichers", [])),
            enrichment_results=enrichment_results,
            created_at=created_at,
            updated_at=updated_at,
        )


class CompositeCheckpointManager:
    """Manages checkpoint persistence for composite pipelines.

    Saves and loads checkpoint state to enable resume after failures.
    Checkpoints are stored as JSON files in the checkpoint directory.

    Attributes:
        composite_name: Name of the composite pipeline.
        run_id: Composite run ID.
        checkpoint_dir: Directory for checkpoint files.
        logger: Structured logger.

    Example:
        >>> manager = CompositeCheckpointManager(
        ...     composite_name="composite_publication",
        ...     run_id="abc-123",
        ...     checkpoint_dir=Path("data/checkpoints"),
        ...     logger=logger,
        ... )
        >>> state = await manager.load()
        >>> new_state = state.with_seed_completed(seed_result)
        >>> await manager.save(new_state)
    """

    def __init__(
        self,
        composite_name: str,
        run_id: str,
        checkpoint_dir: Path,
        logger: LoggerPort,
        resume: bool = False,
    ) -> None:
        """Initialize checkpoint manager.

        Args:
            composite_name: Name of the composite pipeline.
            run_id: Composite run ID.
            checkpoint_dir: Directory for checkpoint files.
            logger: Structured logger.
            resume: Whether to resume from existing checkpoint.
        """
        self._composite_name = composite_name
        self._run_id = run_id
        self._checkpoint_dir = checkpoint_dir
        self._logger = logger
        self._resume = resume
        self._checkpoint_path = self._get_checkpoint_path()

    def _get_checkpoint_path(self) -> Path:
        """Get path to checkpoint file."""
        filename = f"composite_{self._composite_name}_{self._run_id}.json"
        return self._checkpoint_dir / filename

    def _get_latest_checkpoint_path(self) -> Path | None:
        """Find latest checkpoint for this composite."""
        pattern = f"composite_{self._composite_name}_*.json"
        checkpoints = list(self._checkpoint_dir.glob(pattern))
        if not checkpoints:
            return None
        # Sort by modification time, return newest
        return max(checkpoints, key=lambda p: p.stat().st_mtime)

    def _warn_if_checkpoint_exists_with_progress(self) -> None:
        """Warn if an existing checkpoint with progress will be overwritten.

        Called when resume=False to notify user that previous progress exists
        and will be lost. This helps prevent accidental data loss when user
        forgets to pass --resume flag.
        """
        checkpoint_path = self._get_latest_checkpoint_path()
        if checkpoint_path is None or not checkpoint_path.exists():
            return

        try:
            data = json.loads(checkpoint_path.read_text())
            state = CompositeCheckpointState.from_dict(data)

            # Only warn if checkpoint has actual progress
            if state.is_resumable:
                self._logger.warning(
                    "Existing checkpoint with progress will be overwritten",
                    composite=self._composite_name,
                    checkpoint_path=str(checkpoint_path),
                    checkpoint_state=state.state.value,
                    seed_completed=state.seed_completed,
                    completed_enrichers=len(state.completed_enrichers),
                    hint="Use --resume flag to continue from previous progress",
                )
        except Exception:
            # Silently ignore if we can't read the checkpoint
            # (corrupted file will be overwritten anyway)
            pass

    async def load(self) -> CompositeCheckpointState:
        """Load checkpoint state.

        If resume=True and checkpoint exists, load it.
        Otherwise, create fresh state.

        When resume=False but a checkpoint with progress exists, logs a warning
        that the checkpoint will be overwritten.

        Returns:
            Checkpoint state (loaded or fresh).
        """
        if self._resume:
            # Try to load existing checkpoint
            checkpoint_path: Path | None = None
            if self._checkpoint_path.exists():
                checkpoint_path = self._checkpoint_path
            else:
                # Try to find latest checkpoint for this composite
                checkpoint_path = self._get_latest_checkpoint_path()

            if checkpoint_path is not None and checkpoint_path.exists():
                try:
                    data = json.loads(checkpoint_path.read_text())
                    state = CompositeCheckpointState.from_dict(data)
                    # Check for state mismatch (corrupted file)
                    raw_state = data.get("state")
                    if raw_state is not None and state.state.value != raw_state:
                        self._logger.warning(
                            "Checkpoint state value corrupted, using default",
                            composite=self._composite_name,
                            raw_state=raw_state,
                            parsed_state=state.state.value,
                        )
                    self._logger.info(
                        "Loaded checkpoint",
                        composite=self._composite_name,
                        checkpoint_path=str(checkpoint_path),
                        state=state.state.value,
                        seed_completed=state.seed_completed,
                        completed_enrichers=list(state.completed_enrichers),
                    )
                    return state
                except Exception as e:
                    self._logger.warning(
                        "Failed to load checkpoint",
                        composite=self._composite_name,
                        error=str(e),
                    )
        else:
            # resume=False: check if existing checkpoint with progress will be overwritten
            self._warn_if_checkpoint_exists_with_progress()

        # Create fresh state
        return CompositeCheckpointState(
            composite_name=self._composite_name,
            run_id=self._run_id,
            created_at=datetime.now(tz=UTC),
        )

    async def save(self, state: CompositeCheckpointState) -> None:
        """Save checkpoint state.

        Writes state to JSON file atomically.

        Args:
            state: Checkpoint state to save.
        """
        # Ensure directory exists
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Write to temp file then replace (atomic on POSIX, handles existing file on Windows)
        temp_path = self._checkpoint_path.with_suffix(".tmp")
        try:
            temp_path.write_text(json.dumps(state.to_dict(), indent=2))
            temp_path.replace(self._checkpoint_path)

            self._logger.debug(
                "Saved checkpoint",
                composite=self._composite_name,
                checkpoint_path=str(self._checkpoint_path),
                state=state.state.value,
                completed_enrichers=len(state.completed_enrichers),
            )
        except Exception as e:
            self._logger.error(
                "Failed to save checkpoint",
                composite=self._composite_name,
                error=str(e),
            )
            if temp_path.exists():
                temp_path.unlink()
            raise

    async def delete(self) -> None:
        """Delete checkpoint file.

        Called after successful completion.
        """
        if self._checkpoint_path.exists():
            self._checkpoint_path.unlink()
            self._logger.info(
                "Deleted checkpoint",
                composite=self._composite_name,
                checkpoint_path=str(self._checkpoint_path),
            )

    async def list_all(self) -> list[Path]:
        """List all checkpoints for this composite.

        Returns:
            List of checkpoint file paths.
        """
        pattern = f"composite_{self._composite_name}_*.json"
        return list(self._checkpoint_dir.glob(pattern))
