"""Composite Checkpoint Manager.

Application Service that manages checkpoint state for composite pipelines.
Enables resume capability after failures.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import orjson

from bioetl.domain.composite.result import (
    EnrichmentResult,
    EnrichmentStatus,
    SeedResult,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class CompositeCheckpointState:
    """Immutable checkpoint state for composite pipeline.

    Tracks progress through composite execution phases:
    - Seed completion
    - Individual enricher completions
    - Any intermediate state needed for resume

    Attributes:
        composite_name: Name of the composite pipeline.
        run_id: Composite run ID.
        seed_completed: Whether seed pipeline completed.
        seed_result: Result from seed if completed.
        completed_enrichers: Set of completed enricher names.
        enrichment_results: Results from completed enrichers.
        created_at: When checkpoint was created.
        updated_at: When checkpoint was last updated.

    Example:
        >>> state = CompositeCheckpointState(
        ...     composite_name="composite_publication",
        ...     run_id="abc-123",
        ... )
        >>> state.seed_completed
        False
        >>> new_state = state.with_seed_completed(seed_result)
        >>> new_state.seed_completed
        True
    """

    composite_name: str
    run_id: str
    seed_completed: bool = False
    seed_result: SeedResult | None = None
    completed_enrichers: frozenset[str] = field(default_factory=frozenset)
    enrichment_results: dict[str, EnrichmentResult] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def with_seed_completed(self, result: SeedResult) -> CompositeCheckpointState:
        """Create new state with seed marked as completed."""
        return CompositeCheckpointState(
            composite_name=self.composite_name,
            run_id=self.run_id,
            seed_completed=True,
            seed_result=result,
            completed_enrichers=self.completed_enrichers,
            enrichment_results=self.enrichment_results,
            created_at=self.created_at,
            updated_at=datetime.now(),
        )

    def with_enricher_completed(
        self, enricher_name: str, result: EnrichmentResult
    ) -> CompositeCheckpointState:
        """Create new state with enricher marked as completed."""
        new_completed = self.completed_enrichers | {enricher_name}
        new_results = {**self.enrichment_results, enricher_name: result}
        return CompositeCheckpointState(
            composite_name=self.composite_name,
            run_id=self.run_id,
            seed_completed=self.seed_completed,
            seed_result=self.seed_result,
            completed_enrichers=frozenset(new_completed),
            enrichment_results=new_results,
            created_at=self.created_at,
            updated_at=datetime.now(),
        )

    @property
    def is_resumable(self) -> bool:
        """Check if this checkpoint can be resumed."""
        return self.seed_completed or bool(self.completed_enrichers)

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for JSON serialization."""
        return {
            "composite_name": self.composite_name,
            "run_id": self.run_id,
            "seed_completed": self.seed_completed,
            "seed_result": self._serialize_seed_result(),
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
        """Create state from dictionary."""
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

        enrichment_results = {}
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

        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])

        return cls(
            composite_name=data["composite_name"],
            run_id=data["run_id"],
            seed_completed=data.get("seed_completed", False),
            seed_result=seed_result,
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

    async def load(self) -> CompositeCheckpointState:
        """Load checkpoint state.

        If resume=True and checkpoint exists, load it.
        Otherwise, create fresh state.

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
                    # Optimized: Use orjson for faster loading
                    data = orjson.loads(checkpoint_path.read_bytes())
                    state = CompositeCheckpointState.from_dict(data)
                    self._logger.info(
                        "Loaded checkpoint",
                        composite=self._composite_name,
                        checkpoint_path=str(checkpoint_path),
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

        # Create fresh state
        return CompositeCheckpointState(
            composite_name=self._composite_name,
            run_id=self._run_id,
            created_at=datetime.now(),
        )

    async def save(self, state: CompositeCheckpointState) -> None:
        """Save checkpoint state.

        Writes state to JSON file atomically.

        Args:
            state: Checkpoint state to save.
        """
        # Ensure directory exists
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Write to temp file then rename (atomic)
        temp_path = self._checkpoint_path.with_suffix(".tmp")
        try:
            # Optimized: Use orjson for faster serialization
            # Using OPT_INDENT_2 to match previous indent=2 behavior for readability
            # and OPT_SORT_KEYS for deterministic output
            json_bytes = orjson.dumps(
                state.to_dict(),
                option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS
            )
            temp_path.write_bytes(json_bytes)
            temp_path.rename(self._checkpoint_path)

            self._logger.debug(
                "Saved checkpoint",
                composite=self._composite_name,
                checkpoint_path=str(self._checkpoint_path),
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
