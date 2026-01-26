================================================================================
File: __init__.py
Path: __init__.py
================================================================================
"""Application layer for pipeline orchestration.

Implements RULES.md §4 - Application Layer.
"""

from __future__ import annotations

================================================================================
File: __init__.py
Path: composite\__init__.py
================================================================================
"""Composite pipeline application services.

This package contains application services for composite pipeline orchestration:
- CompositePipelineRunner: Main orchestrator for composite pipelines
- EnrichmentCoordinator: Fan-out/fan-in coordination for enrichers
- MergeService: Data merging with conflict resolution
- KeyExtractorService: Extract join keys from seed Silver tables
- CompositeCheckpointManager: Checkpoint management for resume capability
- ColumnRenamer: Unified column renaming to qualified format
- ColumnOrderer: Semantic column ordering for consistent output

See ADR-026 for architectural decisions.
"""

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointManager,
    CompositeCheckpointState,
)
from bioetl.application.composite.column_orderer import ColumnOrderer
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.coordinator import EnrichmentCoordinator
from bioetl.application.composite.key_extractor import KeyExtractorService
from bioetl.application.composite.merger import MergeService
from bioetl.application.composite.runner import CompositePipelineRunner

__all__ = [
    "ColumnOrderer",
    "ColumnRenamer",
    "CompositeCheckpointManager",
    "CompositeCheckpointState",
    "CompositePipelineRunner",
    "EnrichmentCoordinator",
    "KeyExtractorService",
    "MergeService",
]

================================================================================
File: checkpoint.py
Path: composite\checkpoint.py
================================================================================
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
    - Individual enricher completions
    - Any intermediate state needed for resume

    Attributes:
        composite_name: Name of the composite pipeline.
        run_id: Composite run ID.
        state: Current FSM state of the pipeline.
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
    completed_enrichers: frozenset[str] = field(default_factory=frozenset)
    enrichment_results: dict[str, EnrichmentResult] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def with_seed_completed(self, result: SeedResult) -> CompositeCheckpointState:
        """Create new state with seed marked as completed.

        Sets state to SEED_COMPLETED to indicate seed phase is done.
        """
        return CompositeCheckpointState(
            composite_name=self.composite_name,
            run_id=self.run_id,
            state=CompositePipelineState.SEED_COMPLETED,
            seed_completed=True,
            seed_result=result,
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
        """
        new_completed = self.completed_enrichers | {enricher_name}
        new_results = {**self.enrichment_results, enricher_name: result}
        return CompositeCheckpointState(
            composite_name=self.composite_name,
            run_id=self.run_id,
            state=CompositePipelineState.ENRICHING,
            seed_completed=self.seed_completed,
            seed_result=self.seed_result,
            completed_enrichers=frozenset(new_completed),
            enrichment_results=new_results,
            created_at=self.created_at,
            updated_at=datetime.now(tz=UTC),
        )

    def with_state(self, new_state: CompositePipelineState) -> CompositeCheckpointState:
        """Create new state with updated FSM state.

        Allows Runner to explicitly set state transitions (e.g., to MERGING,
        ENRICHMENT_COMPLETED, FAILED, or COMPLETED) without modifying other fields.

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
        """Convert to dictionary for JSON serialization."""
        return {
            "composite_name": self.composite_name,
            "run_id": self.run_id,
            "state": self.state.value,
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
        """Create state from dictionary.

        Handles backward compatibility for checkpoints without state field.
        Gracefully handles corrupted state values by defaulting to NOT_STARTED.
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

================================================================================
File: column_orderer.py
Path: composite\column_orderer.py
================================================================================
"""Column orderer service for composite pipelines.

Orders columns by semantic groups for consistent output.
See ADR-026 for rationale.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.domain.value_objects.column_order import (
    DEFAULT_COLUMN_ORDER,
    ColumnOrderConfig,
    SemanticGroup,
)
from bioetl.domain.value_objects.column_qualifier import ColumnQualifier

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import ColumnGroupConfig
    from bioetl.domain.ports import LoggerPort

__all__ = ["ColumnOrderer"]


class ColumnOrderer:
    """Service for ordering columns by semantic groups.

    Orders DataFrame columns in a consistent, semantically meaningful way:
    1. System fields (entity_id, _run_id, ...)
    2. Identifiers (doi, pmid, ...)
    3. Title fields
    4. Abstract fields
    5. Authors fields
    6. Journal/Source fields
    7. Date fields
    8. Metrics fields
    9. Classification fields
    10. URL fields
    11. Other fields

    Within each group, columns are ordered by:
    - Provider priority (chembl first, then crossref, etc.)
    - Alphabetically for same provider

    Example:
        >>> orderer = ColumnOrderer(logger)
        >>> result = orderer.order_columns(df)
        >>> result.columns[:5]
        ['entity_id', '_run_id', 'doi', 'pmid', 'chembl.publication.title']
    """

    def __init__(
        self,
        logger: LoggerPort,
        config: ColumnOrderConfig | None = None,
        column_groups: Sequence[ColumnGroupConfig] | None = None,
    ) -> None:
        """Initialize orderer.

        Args:
            logger: Logger port for diagnostics.
            config: Column order configuration. Uses DEFAULT_COLUMN_ORDER if None.
            column_groups: Optional YAML-based column group configuration.
                If provided, takes precedence over config.
        """
        self._logger = logger
        self._config = config or DEFAULT_COLUMN_ORDER
        self._column_groups = tuple(column_groups) if column_groups else None

    def order_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Order DataFrame columns by semantic groups.

        If column_groups were provided in constructor, uses YAML-based ordering.
        Otherwise falls back to hardcoded ColumnOrderConfig.

        Args:
            df: DataFrame to reorder.

        Returns:
            DataFrame with columns in semantic order.
        """
        if not df.columns:
            return df

        # Use YAML-based column groups if available
        if self._column_groups:
            ordered = self._order_by_yaml_groups(df.columns)
            self._logger.debug(
                "Ordered columns by YAML groups",
                total_columns=len(ordered),
                groups_configured=len(self._column_groups),
            )
        else:
            ordered = self.get_ordered_columns(df.columns)
            self._logger.debug(
                "Ordered columns by semantic groups",
                total_columns=len(ordered),
                groups_used=self._count_groups(ordered),
            )

        return df.select(ordered)

    def get_ordered_columns(self, columns: Sequence[str]) -> list[str]:
        """Get columns in semantic order.

        Args:
            columns: Column names to order.

        Returns:
            Ordered list of column names.
        """

        # Create sort key for each column
        def sort_key(col: str) -> tuple[int, int, str]:
            """Sort by (group, provider_rank, column_name)."""
            group = self._config.get_group(col)
            provider_rank = self._config.get_provider_rank(col)
            # For alphabetical sort, use field name (not full qualified name)
            field_name = ColumnQualifier.extract_field(col)
            return (group.value, provider_rank, field_name.lower())

        return sorted(columns, key=sort_key)

    def _count_groups(self, columns: Sequence[str]) -> dict[str, int]:
        """Count columns per semantic group.

        Args:
            columns: Ordered column names.

        Returns:
            Dict mapping group name to column count.
        """
        counts: dict[str, int] = {}
        for col in columns:
            group = self._config.get_group(col)
            group_name = group.name
            counts[group_name] = counts.get(group_name, 0) + 1
        return counts

    def group_columns(self, columns: Sequence[str]) -> dict[SemanticGroup, list[str]]:
        """Group columns by semantic type.

        Useful for debugging and documentation.

        Args:
            columns: Column names to group.

        Returns:
            Dict mapping SemanticGroup to list of columns.
        """
        groups: dict[SemanticGroup, list[str]] = {}

        for col in columns:
            group = self._config.get_group(col)
            if group not in groups:
                groups[group] = []
            groups[group].append(col)

        # Sort columns within each group
        for group in groups:
            groups[group] = sorted(
                groups[group],
                key=lambda c: (
                    self._config.get_provider_rank(c),
                    ColumnQualifier.extract_field(c).lower(),
                ),
            )

        return groups

    # === YAML-based column ordering methods ===

    def _order_by_yaml_groups(self, columns: Sequence[str]) -> list[str]:
        """Order columns using YAML-configured groups.

        Args:
            columns: Column names to order.

        Returns:
            Ordered list of column names.
        """
        if not self._column_groups:
            return list(columns)

        all_columns = set(columns)
        ordered_columns: list[str] = []
        used_columns: set[str] = set()

        for group in self._column_groups:
            group_columns = self._collect_group_columns(
                all_columns - used_columns,
                group,
            )
            ordered_columns.extend(group_columns)
            used_columns.update(group_columns)

        # Add remaining columns at the end (alphabetically)
        remaining = sorted(all_columns - used_columns)
        if remaining:
            ordered_columns.extend(remaining)
            self._logger.debug(
                "Ungrouped columns added at end",
                count=len(remaining),
                sample=remaining[:5],
            )

        return ordered_columns

    def _collect_group_columns(
        self,
        available: set[str],
        group: ColumnGroupConfig,
    ) -> list[str]:
        """Collect columns for a group, ordered by provider.

        Args:
            available: Set of available column names.
            group: Column group configuration.

        Returns:
            Ordered list of columns for this group.
        """
        matched: set[str] = set()

        # Match by explicit field names
        for field in group.fields:
            for col in available:
                # Match exact field name or suffixed versions
                field_name = self._extract_field_from_qualified(col)
                if field_name == field or col == field:
                    matched.add(col)

        # Match by pattern
        if group.pattern:
            try:
                pattern = re.compile(group.pattern, re.IGNORECASE)
                for col in available:
                    if pattern.search(col):
                        matched.add(col)
            except re.error as e:
                self._logger.warning(
                    "Invalid regex pattern in column group",
                    group=group.name,
                    pattern=group.pattern,
                    error=str(e),
                )

        # Sort by provider order
        return self._sort_by_provider(list(matched), group.provider_order)

    def _sort_by_provider(
        self,
        columns: list[str],
        provider_order: tuple[str, ...],
    ) -> list[str]:
        """Sort columns by provider prefix order.

        Seed columns (no dots) come first, then by provider order.

        Args:
            columns: List of column names.
            provider_order: Tuple of provider names in desired order.

        Returns:
            Sorted list of columns.
        """

        def sort_key(col: str) -> tuple[int, str]:
            # Seed columns (no dot or single dot like 'field.A') come first
            parts = col.split(".")
            if len(parts) < 3:
                return (0, col.lower())

            # Extract provider from qualified name (provider.entity.field)
            provider = parts[0].lower()
            try:
                idx = provider_order.index(provider)
                return (idx + 1, col.lower())
            except ValueError:
                # Unknown provider - at the end
                return (len(provider_order) + 1, col.lower())

        return sorted(columns, key=sort_key)

    def _extract_field_from_qualified(self, column: str) -> str:
        """Extract field name from qualified column name.

        Args:
            column: Column name (qualified or unqualified).

        Returns:
            Field name (last part of qualified name, or full name if unqualified).
        """
        parts = column.split(".")
        if len(parts) == 3:
            return parts[2]  # provider.entity.field -> field
        if len(parts) == 2:
            return parts[1]  # field.A -> A (conflict suffix) - keep original
        return column

================================================================================
File: column_renamer.py
Path: composite\column_renamer.py
================================================================================
"""Column renamer service for composite pipelines.

Provides unified column renaming to {provider}.{entity}.{field} format.
See ADR-026 for rationale.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Final

from bioetl.domain.value_objects.column_qualifier import ColumnQualifier

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.ports import LoggerPort

__all__ = ["ColumnRenamer"]


class ColumnRenamer:
    """Service for renaming columns to qualified format.

    Renames all business columns to {provider}.{entity}.{field} format.
    Excludes join keys and system columns from renaming.

    Example:
        >>> renamer = ColumnRenamer(logger)
        >>> result = renamer.rename_dataframe(df, "chembl_publication")
        >>> # 'title' -> 'chembl.publication.title'
        >>> # 'doi' -> 'doi' (join key, unchanged)
        >>> # '_run_id' -> '_run_id' (system, unchanged)
    """

    # System column prefixes (not renamed)
    SYSTEM_PREFIXES: Final[frozenset[str]] = frozenset({"_"})

    # Join key columns (not renamed, case-insensitive)
    JOIN_KEY_COLUMNS: Final[frozenset[str]] = frozenset({"doi", "pmid", "pmc_id"})

    def __init__(self, logger: LoggerPort) -> None:
        """Initialize renamer.

        Args:
            logger: Logger port for diagnostics.
        """
        self._logger = logger

    def rename_dataframe(
        self,
        df: pl.DataFrame,
        pipeline: str,
        *,
        exclude_join_keys: bool = True,
    ) -> pl.DataFrame:
        """Rename all business columns to qualified format.

        Transforms column names from 'field' to '{provider}.{entity}.{field}'.

        Args:
            df: DataFrame to rename.
            pipeline: Pipeline name in format 'provider_entity'.
            exclude_join_keys: If True, join keys (doi, pmid, pmc_id)
                are NOT renamed. Default: True.

        Returns:
            DataFrame with renamed columns.

        Example:
            >>> df = pl.DataFrame({"doi": ["10.1/a"], "title": ["T1"], "_run_id": ["x"]})
            >>> result = renamer.rename_dataframe(df, "chembl_publication")
            >>> result.columns
            ['doi', 'chembl.publication.title', '_run_id']
        """
        rename_map = self.build_rename_map(
            columns=df.columns,
            pipeline=pipeline,
            exclude_join_keys=exclude_join_keys,
        )

        if not rename_map:
            return df

        self._logger.debug(
            "Renaming columns to qualified format",
            pipeline=pipeline,
            rename_count=len(rename_map),
            sample_renames=dict(list(rename_map.items())[:3]),
        )

        return df.rename(rename_map)

    def build_rename_map(
        self,
        columns: Sequence[str],
        pipeline: str,
        *,
        exclude_join_keys: bool = True,
    ) -> dict[str, str]:
        """Build rename mapping {old_name: new_name}.

        Args:
            columns: List of column names.
            pipeline: Pipeline name in format 'provider_entity'.
            exclude_join_keys: If True, exclude join keys from mapping.

        Returns:
            Dictionary mapping old column names to new qualified names.

        Raises:
            ValueError: If pipeline format is invalid.
        """
        provider, entity = self._parse_pipeline(pipeline)
        rename_map: dict[str, str] = {}

        for col in columns:
            # Skip system columns
            if self._is_system_column(col):
                self._logger.debug("Skipping system column", column=col)
                continue

            # Skip already qualified columns
            if self._is_already_qualified(col):
                self._logger.debug("Skipping already qualified column", column=col)
                continue

            # Skip join keys if requested
            if exclude_join_keys and self._is_join_key(col):
                self._logger.debug("Skipping join key column", column=col)
                continue

            # Build qualified name
            qualifier = ColumnQualifier(provider, entity, col)
            rename_map[col] = str(qualifier)

        return rename_map

    def _parse_pipeline(self, pipeline: str) -> tuple[str, str]:
        """Parse pipeline name into (provider, entity).

        Args:
            pipeline: Pipeline name in format 'provider_entity'.

        Returns:
            Tuple of (provider, entity).

        Raises:
            ValueError: If format is invalid.
        """
        if "_" not in pipeline:
            raise ValueError(
                f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
            )
        parts = pipeline.split("_", 1)
        return (parts[0].lower(), parts[1].lower())

    def _is_system_column(self, col: str) -> bool:
        """Check if column is a system column (starts with '_')."""
        return any(col.startswith(prefix) for prefix in self.SYSTEM_PREFIXES)

    def _is_already_qualified(self, col: str) -> bool:
        """Check if column is already in qualified format (x.y.z)."""
        return ColumnQualifier.is_qualified(col)

    def _is_join_key(self, col: str) -> bool:
        """Check if column is a join key (case-insensitive)."""
        return col.lower() in self.JOIN_KEY_COLUMNS

================================================================================
File: coordinator.py
Path: composite\coordinator.py
================================================================================
"""Enrichment Coordinator.

Application Service that coordinates parallel enrichment pipeline execution.
Implements fan-out pattern with async gather for concurrent enrichers.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.composite.config import CompositeDQConfig, EnricherConfig
    from bioetl.domain.ports import LoggerPort


class EnrichmentCoordinator:
    """Coordinates parallel enrichment pipeline execution.

    Implements fan-out pattern with async gather for concurrent enrichers.
    Handles timeouts, failures, and partial completion.

    This service is responsible for:
    - Filtering keys based on enricher conditions
    - Running enrichers in parallel (up to max_concurrency)
    - Handling per-enricher timeouts
    - Aggregating results

    Attributes:
        logger: Structured logger.
        dq_config: DQ thresholds for enricher evaluation.
        max_concurrency: Maximum concurrent enrichers.

    Example:
        >>> coordinator = EnrichmentCoordinator(
        ...     logger=logger,
        ...     dq_config=dq_config,
        ...     max_concurrency=4,
        ... )
        >>> results = await coordinator.run_enrichers(
        ...     keys=keys_df,
        ...     enrichers=enricher_configs,
        ...     runner_factory=factory,
        ... )
    """

    def __init__(
        self,
        logger: LoggerPort,
        dq_config: CompositeDQConfig,
        max_concurrency: int = 4,
    ) -> None:
        """Initialize enrichment coordinator.

        Args:
            logger: Structured logger.
            dq_config: DQ thresholds configuration.
            max_concurrency: Maximum concurrent enrichers.
        """
        self._logger = logger
        self._dq_config = dq_config
        self._max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def run_enrichers(
        self,
        keys: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        completed: frozenset[str],
        runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    ) -> dict[str, EnrichmentResult]:
        """Run all enrichers in parallel.

        Executes enrichers concurrently up to max_concurrency limit.
        Each enricher receives filtered keys based on its filter_condition.

        Args:
            keys: DataFrame with join keys from seed.
            enrichers: Enricher configurations.
            completed: Set of already-completed enrichers (for resume).
            runner_factory: Factory to create PipelineRunner for each enricher.

        Returns:
            Mapping of enricher name to result.

        Example:
            >>> results = await coordinator.run_enrichers(
            ...     keys=keys_df,
            ...     enrichers=[crossref_config, pubmed_config],
            ...     completed=frozenset(),
            ...     runner_factory=factory,
            ... )
            >>> results["crossref_publication"].is_success
            True
        """
        tasks = []
        enricher_names = []

        for enricher in enrichers:
            if enricher.pipeline in completed:
                self._logger.debug(
                    "Skipping completed enricher",
                    enricher=enricher.pipeline,
                )
                continue

            # Filter keys based on enricher condition
            filtered_keys = self._apply_filter(keys, enricher)

            if filtered_keys.is_empty():
                self._logger.info(
                    "Filter excluded all records for enricher",
                    enricher=enricher.pipeline,
                    filter_condition=enricher.filter_condition,
                )
                # Create skipped result synchronously
                tasks.append(asyncio.create_task(self._return_skipped(enricher)))
                enricher_names.append(enricher.pipeline)
                continue

            tasks.append(
                asyncio.create_task(
                    self._run_single_enricher(
                        enricher=enricher,
                        keys=filtered_keys,
                        runner_factory=runner_factory,
                    )
                )
            )
            enricher_names.append(enricher.pipeline)

        if not tasks:
            return {}

        self._logger.info(
            "Running enrichers",
            count=len(tasks),
            enrichers=enricher_names,
        )

        # Wait for all enrichers to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        return self._process_results(enricher_names, results)

    def _apply_filter(
        self, keys: pl.DataFrame, enricher: EnricherConfig
    ) -> pl.DataFrame:
        """Apply filter condition to keys DataFrame.

        Filters keys based on the enricher's filter_condition.
        If no condition, returns all keys.

        Args:
            keys: Full keys DataFrame.
            enricher: Enricher configuration with optional filter.

        Returns:
            Filtered DataFrame.
        """
        import polars as pl

        if not enricher.filter_condition:
            return keys

        try:
            # Parse simple SQL-like conditions
            # Supports: "field IS NOT NULL", "field IS NULL"
            condition = enricher.filter_condition.strip()

            if " IS NOT NULL" in condition.upper():
                raw_field = condition.upper().replace(" IS NOT NULL", "").strip()
                matched = self._find_column_case_insensitive(keys, raw_field)
                if matched:
                    return keys.filter(pl.col(matched).is_not_null())

            if " IS NULL" in condition.upper():
                raw_field = condition.upper().replace(" IS NULL", "").strip()
                matched = self._find_column_case_insensitive(keys, raw_field)
                if matched:
                    return keys.filter(pl.col(matched).is_null())

            # For complex conditions, try SQL expression
            # This is a simplified implementation
            self._logger.warning(
                "Complex filter condition not fully supported",
                enricher=enricher.pipeline,
                condition=condition,
            )
            return keys

        except Exception as e:
            self._logger.warning(
                "Failed to apply filter condition",
                enricher=enricher.pipeline,
                condition=enricher.filter_condition,
                error=str(e),
            )
            return keys

    def _find_column_case_insensitive(
        self, df: pl.DataFrame, column: str
    ) -> str | None:
        """Find column name with case-insensitive matching."""
        column_lower = column.lower()
        for col in df.columns:
            if col.lower() == column_lower:
                return col
        return None

    async def _return_skipped(self, enricher: EnricherConfig) -> EnrichmentResult:
        """Return a skipped result for an enricher."""
        return EnrichmentResult.skipped(
            enricher_name=enricher.pipeline,
            reason=f"Filter condition excluded all records: {enricher.filter_condition}",
        )

    async def _run_single_enricher(
        self,
        enricher: EnricherConfig,
        keys: pl.DataFrame,
        runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    ) -> EnrichmentResult:
        """Run a single enricher with timeout and error handling.

        Uses semaphore to limit concurrency and handles:
        - Timeout per enricher
        - Critical errors (re-raised for required enrichers)
        - Recoverable errors (logged, returned as failed)

        Args:
            enricher: Enricher configuration.
            keys: Filtered keys DataFrame.
            runner_factory: Factory to create PipelineRunner.

        Returns:
            EnrichmentResult with execution outcome.
        """
        async with self._semaphore:
            started_at = datetime.now(tz=UTC)
            records_input = len(keys)

            self._logger.info(
                "Starting enricher",
                enricher=enricher.pipeline,
                records_input=records_input,
                timeout_seconds=enricher.timeout_seconds,
            )

            try:
                # Apply timeout
                async with asyncio.timeout(enricher.timeout_seconds):
                    runner = runner_factory(enricher.pipeline, keys)
                    await runner.run()

                completed_at = datetime.now(tz=UTC)
                duration = (completed_at - started_at).total_seconds()

                # Extract stats from runner
                executor = getattr(runner, "_executor", None)
                records_enriched = 0
                records_errored = 0

                if executor:
                    records_enriched = getattr(executor, "records_silver", 0)
                    records_errored = getattr(executor, "records_quarantined", 0)

                # Calculate DQ error rate
                dq_error_rate = 0.0
                if records_input > 0:
                    dq_error_rate = records_errored / records_input

                # Check against thresholds
                hard_threshold = self._dq_config.get_enricher_hard_threshold(
                    enricher.pipeline
                )

                if dq_error_rate > hard_threshold:
                    self._logger.warning(
                        "Enricher exceeded hard DQ threshold",
                        enricher=enricher.pipeline,
                        dq_error_rate=dq_error_rate,
                        threshold=hard_threshold,
                    )
                    return EnrichmentResult(
                        enricher_name=enricher.pipeline,
                        status=EnrichmentStatus.FAILED,
                        records_input=records_input,
                        records_enriched=records_enriched,
                        records_errored=records_errored,
                        dq_error_rate=dq_error_rate,
                        duration_seconds=duration,
                        started_at=started_at,
                        completed_at=completed_at,
                        error_message=f"DQ error rate {dq_error_rate:.2%} exceeds threshold {hard_threshold:.2%}",
                    )

                # Determine success vs partial
                status = EnrichmentStatus.SUCCESS
                if records_enriched < records_input:
                    status = EnrichmentStatus.PARTIAL

                self._logger.info(
                    "Enricher completed",
                    enricher=enricher.pipeline,
                    status=status.value,
                    records_enriched=records_enriched,
                    duration_seconds=duration,
                )

                return EnrichmentResult(
                    enricher_name=enricher.pipeline,
                    status=status,
                    records_input=records_input,
                    records_enriched=records_enriched,
                    records_not_found=records_input
                    - records_enriched
                    - records_errored,
                    records_errored=records_errored,
                    dq_error_rate=dq_error_rate,
                    duration_seconds=duration,
                    started_at=started_at,
                    completed_at=completed_at,
                )

            except TimeoutError:
                duration = (datetime.now(tz=UTC) - started_at).total_seconds()
                self._logger.warning(
                    "Enricher timed out",
                    enricher=enricher.pipeline,
                    timeout_seconds=enricher.timeout_seconds,
                )
                return EnrichmentResult.timeout(
                    enricher_name=enricher.pipeline,
                    timeout_seconds=enricher.timeout_seconds,
                    records_input=records_input,
                )

            except Exception as e:
                duration = (datetime.now(tz=UTC) - started_at).total_seconds()

                # Re-raise for required enrichers (logged as error)
                if enricher.required:
                    self._logger.error(
                        "Required enricher failed",
                        enricher=enricher.pipeline,
                        error=str(e),
                        required=True,
                    )
                    raise

                # Optional enricher failures are warnings (pipeline continues)
                self._logger.warning(
                    "Optional enricher failed",
                    enricher=enricher.pipeline,
                    error=str(e),
                    required=False,
                )

                return EnrichmentResult.failed(
                    enricher_name=enricher.pipeline,
                    error_message=str(e),
                    records_input=records_input,
                    duration_seconds=duration,
                )

    def _process_results(
        self,
        enricher_names: list[str],
        results: list[EnrichmentResult | BaseException],
    ) -> dict[str, EnrichmentResult]:
        """Process gathered results, handling exceptions.

        Converts exceptions to failed results for optional enrichers.
        Re-raises exceptions for required enrichers (should not happen
        as they're raised in _run_single_enricher).

        Args:
            enricher_names: Names of enrichers in order.
            results: Results from asyncio.gather.

        Returns:
            Mapping of enricher name to result.
        """
        processed: dict[str, EnrichmentResult] = {}

        for name, result in zip(enricher_names, results, strict=True):
            if isinstance(result, BaseException):
                # Should not happen for required (already re-raised)
                processed[name] = EnrichmentResult.failed(
                    enricher_name=name,
                    error_message=str(result),
                )
            else:
                processed[name] = result

        return processed

================================================================================
File: deduplication.py
Path: composite\deduplication.py
================================================================================
"""Enricher deduplication logic for composite pipelines.

Provides functionality to deduplicate enricher tables before join
to prevent fan-out when enricher has duplicate values by join keys.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.ports import LoggerPort


class EnricherDeduplicator:
    """Handles deduplication of enricher tables before join operations."""

    def __init__(self, logger: LoggerPort) -> None:
        """Initialize deduplicator with logger.

        Args:
            logger: Logger port for warning messages.
        """
        self._logger = logger

    def deduplicate(
        self,
        enricher_df: pl.DataFrame,
        join_keys: list[str],
        enricher_name: str,
    ) -> pl.DataFrame:
        """Check and deduplicate enricher before join.

        Workflow:
        1. Check for duplicates by join_keys
        2. If no duplicates → return df unchanged
        3. If duplicates exist → aggregate and log

        Args:
            enricher_df: Enricher DataFrame.
            join_keys: Columns for join (grouping keys).
            enricher_name: Name for logging.

        Returns:
            DataFrame with unique values by join_keys.
        """
        if not self._check_duplicates(enricher_df, join_keys):
            return enricher_df
        return self._aggregate_duplicates(enricher_df, join_keys, enricher_name)

    def _check_duplicates(
        self,
        df: pl.DataFrame,
        key_columns: list[str],
    ) -> bool:
        """Check for duplicates by key columns."""
        if len(df) == 0:
            return False
        missing_cols = [c for c in key_columns if c not in df.columns]
        if missing_cols:
            return False
        unique_count = df.select(key_columns).n_unique()
        return unique_count < len(df)

    def _aggregate_duplicates(
        self,
        df: pl.DataFrame,
        key_columns: list[str],
        enricher_name: str,
    ) -> pl.DataFrame:
        """Aggregate duplicates by merging differing values."""

        records_before = len(df)
        non_key_columns = [c for c in df.columns if c not in key_columns]

        if not non_key_columns:
            result = df.select(key_columns).unique(maintain_order=True)
            self._log_deduplication(
                enricher_name, key_columns, records_before, len(result), []
            )
            return result

        columns_with_conflicts, columns_without_conflicts = self._classify_columns(
            df, key_columns, non_key_columns
        )

        agg_exprs = self._build_aggregation_exprs(
            df, columns_with_conflicts, columns_without_conflicts
        )

        result = df.group_by(key_columns, maintain_order=True).agg(agg_exprs)

        self._log_deduplication(
            enricher_name,
            key_columns,
            records_before,
            len(result),
            columns_with_conflicts,
        )
        return result

    def _classify_columns(
        self,
        df: pl.DataFrame,
        key_columns: list[str],
        non_key_columns: list[str],
    ) -> tuple[list[str], list[str]]:
        """Classify columns into those with and without conflicts."""
        columns_with_conflicts: list[str] = []
        columns_without_conflicts: list[str] = []
        for col in non_key_columns:
            if self._has_group_conflicts(df, key_columns, col):
                columns_with_conflicts.append(col)
            else:
                columns_without_conflicts.append(col)
        return columns_with_conflicts, columns_without_conflicts

    def _build_aggregation_exprs(
        self,
        df: pl.DataFrame,
        columns_with_conflicts: list[str],
        columns_without_conflicts: list[str],
    ) -> list[pl.Expr]:
        """Build aggregation expressions for all columns."""
        import polars as pl

        agg_exprs: list[pl.Expr] = []
        for col in columns_without_conflicts:
            agg_exprs.append(pl.col(col).first().alias(col))
        for col in columns_with_conflicts:
            agg_exprs.append(self._build_concat_expr(col, df.schema[col]))
        return agg_exprs

    def _has_group_conflicts(
        self,
        df: pl.DataFrame,
        key_columns: list[str],
        column: str,
    ) -> bool:
        """Check if column has conflicting values in any group."""
        import polars as pl

        conflict_check = df.group_by(key_columns).agg(
            [
                pl.col(column).drop_nulls().n_unique().alias("n_unique"),
                pl.col(column).is_null().any().alias("has_null"),
                pl.col(column).is_null().all().alias("all_null"),
            ]
        )
        conflicts = conflict_check.filter(
            (pl.col("n_unique") > 1) | (pl.col("has_null") & ~pl.col("all_null"))
        )
        return conflicts.height > 0

    def _build_concat_expr(self, column: str, dtype: pl.DataType) -> pl.Expr:
        """Build expression that concatenates values with |.

        Note: Values are NOT sorted and duplicates are NOT removed.
        The order is preserved from the original data.
        """
        import polars as pl

        as_string = self._to_string_expr(column, dtype)
        return (
            pl.when(pl.col(column).is_null())
            .then(pl.lit("null"))
            .otherwise(as_string)
            .str.join("|")
            .alias(column)
        )

    def _to_string_expr(self, column: str, dtype: pl.DataType) -> pl.Expr:
        """Convert column to string expression."""
        import polars as pl

        col_expr = pl.col(column)

        if isinstance(dtype, (pl.List, pl.Struct)):
            return col_expr.map_elements(
                lambda x: str(x) if x is not None else None, return_dtype=pl.String
            )
        if dtype == pl.Boolean:
            return (
                pl.when(col_expr.is_null())
                .then(pl.lit(None))
                .when(col_expr)
                .then(pl.lit("true"))
                .otherwise(pl.lit("false"))
            )
        if isinstance(dtype, pl.Datetime):
            return col_expr.dt.to_string("%Y-%m-%dT%H:%M:%SZ")
        return col_expr.cast(pl.String)

    def _log_deduplication(
        self,
        enricher_name: str,
        key_columns: list[str],
        records_before: int,
        records_after: int,
        columns_with_conflicts: list[str],
    ) -> None:
        """Log deduplication results."""
        self._logger.warning(
            "Duplicates aggregated in enricher",
            enricher=enricher_name,
            join_keys=key_columns,
            duplicate_count=records_before - records_after,
            records_before=records_before,
            records_after=records_after,
            columns_with_conflicts=columns_with_conflicts,
        )


def value_to_string(value: object, dtype: pl.DataType) -> str:
    """Convert a single value to string representation.

    Args:
        value: Value to convert.
        dtype: Original data type.

    Returns:
        String representation.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, timedelta):
        return str(value)
    if isinstance(value, (list, dict)):
        return str(value)
    return str(value)

================================================================================
File: fsm_helper.py
Path: composite\fsm_helper.py
================================================================================
"""FSM (Finite State Machine) helpers for Composite Pipeline.

Extracts FSM-related logic from CompositePipelineRunner to reduce
file size and improve testability.

Implements state transition validation and logging for composite pipeline
execution states (ADR-026).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint import CompositeCheckpointState
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.composite.state import CompositePipelineState
    from bioetl.domain.ports import LoggerPort


class FSMStateHelper:
    """Helper for FSM state transitions and logging.

    Provides methods for:
    - Validating FSM state transitions
    - Logging state transitions
    - Handling resume from failed state
    - Logging resume context

    This class extracts the FSM-related logic from CompositePipelineRunner
    to reduce file size and improve testability.

    Attributes:
        config: Composite pipeline configuration.
        logger: Structured logger.
        run_id: Run identifier.
    """

    def __init__(
        self,
        config: CompositeConfig,
        logger: LoggerPort,
        run_id: str,
    ) -> None:
        """Initialize FSM helper.

        Args:
            config: Composite pipeline configuration.
            logger: Structured logger for observability.
            run_id: Run identifier for correlation.
        """
        self._config = config
        self._logger = logger
        self._run_id = run_id

    def log_fsm_transition(
        self,
        from_state: CompositePipelineState,
        to_state: CompositePipelineState,
        stage: str,
        **extra: object,
    ) -> None:
        """Log FSM state transition.

        Args:
            from_state: Previous FSM state.
            to_state: New FSM state.
            stage: Pipeline stage identifier (e.g., 'seed_start', 'seed_complete').
            **extra: Additional context for logging.
        """
        self._logger.info(
            "FSM state transition",
            from_state=from_state.value,
            to_state=to_state.value,
            composite=self._config.name,
            run_id=self._run_id,
            stage=stage,
            **extra,
        )

    def validate_fsm_transition(
        self,
        from_state: CompositePipelineState,
        to_state: CompositePipelineState,
        allow_resume: bool = False,
    ) -> bool:
        """Validate FSM state transition and log warning if invalid.

        This method validates transitions according to FSM rules. Invalid transitions
        are logged as warnings rather than raising exceptions to avoid breaking
        pipeline execution. This is primarily a debug/development safety net.

        Args:
            from_state: Current FSM state.
            to_state: Target FSM state.
            allow_resume: If True, allows transitions from FAILED state (for resume).

        Returns:
            True if transition is valid, False otherwise.

        Note:
            When allow_resume=True, transitions from FAILED to any resumable state
            are permitted. This is needed for resume-from-failed functionality.
        """
        from bioetl.domain.composite.state import CompositePipelineState

        # Special case: allow resume from FAILED state
        if allow_resume and from_state == CompositePipelineState.FAILED:
            self._logger.debug(
                "FSM resume transition from FAILED",
                from_state=from_state.value,
                to_state=to_state.value,
                composite=self._config.name,
            )
            return True

        # Check if transition is valid according to FSM rules
        if not from_state.can_transition_to(to_state):
            self._logger.warning(
                "Invalid FSM transition detected",
                from_state=from_state.value,
                to_state=to_state.value,
                allowed_transitions=[s.value for s in from_state.allowed_transitions],
                composite=self._config.name,
                run_id=self._run_id,
                note="This may indicate a programming error in the Runner",
            )
            return False

        return True

    def handle_resume_from_failed(
        self, state: CompositeCheckpointState
    ) -> CompositeCheckpointState:
        """Handle resuming from FAILED state by determining correct phase.

        When checkpoint has state=FAILED, we need to determine the actual phase
        to resume from based on seed_completed and completed_enrichers flags.

        Args:
            state: Checkpoint state with FAILED status.

        Returns:
            Updated state with corrected FSM state for resumption.
        """
        from bioetl.domain.composite.state import CompositePipelineState

        total_enrichers = len(self._config.enrichers)
        completed_count = len(state.completed_enrichers)

        if not state.seed_completed:
            # Seed failed - resume from NOT_STARTED (will re-run seed)
            resume_phase = CompositePipelineState.NOT_STARTED
            phase_description = "seed (seed not completed)"
        elif completed_count < total_enrichers:
            # Enrichment failed - resume from ENRICHING (will run remaining enrichers)
            resume_phase = CompositePipelineState.ENRICHING
            phase_description = (
                f"enrichment ({completed_count}/{total_enrichers} enrichers completed)"
            )
        else:
            # Merge failed - resume from ENRICHMENT_COMPLETED (will re-run merge)
            resume_phase = CompositePipelineState.ENRICHMENT_COMPLETED
            phase_description = "merge (all enrichers completed)"

        self._logger.info(
            "Checkpoint indicates previous failure, resuming from phase",
            composite=self._config.name,
            run_id=self._run_id,
            previous_state=state.state.value,
            resume_phase=resume_phase.value,
            phase_description=phase_description,
            seed_completed=state.seed_completed,
            completed_enrichers=completed_count,
            total_enrichers=total_enrichers,
        )

        # Validate and log FSM transition from FAILED to resume phase
        # allow_resume=True permits transitions from terminal FAILED state
        self.validate_fsm_transition(state.state, resume_phase, allow_resume=True)
        self.log_fsm_transition(
            from_state=state.state,
            to_state=resume_phase,
            stage="resume_from_failed",
            phase_description=phase_description,
        )

        return state.with_state(resume_phase)

    def log_resume_context(self, state: CompositeCheckpointState) -> None:
        """Log detailed resume context when resuming from checkpoint.

        Provides visibility into what was completed previously and what
        will be executed in this run.

        Args:
            state: Current checkpoint state being resumed from.
        """
        total_enrichers = len(self._config.enrichers)
        completed_count = len(state.completed_enrichers)
        remaining_count = total_enrichers - completed_count

        self._logger.info(
            "Resuming from checkpoint",
            composite=self._config.name,
            run_id=self._run_id,
            last_state=state.state.value,
            seed_completed=state.seed_completed,
            completed_enrichers_count=completed_count,
            total_enrichers_count=total_enrichers,
            remaining_enrichers_count=remaining_count,
            completed_enrichers=list(state.completed_enrichers)
            if completed_count > 0
            else None,
        )


__all__ = ["FSMStateHelper"]

================================================================================
File: key_extractor.py
Path: composite\key_extractor.py
================================================================================
"""Key Extractor Service.

Application Service that extracts join keys from seed Silver tables
for enrichment pipeline coordination.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.ports import DeltaReaderPort, LoggerPort


class KeyExtractorService:
    """Extracts join keys from seed Silver tables.

    This service reads the seed Silver table and extracts only the
    columns needed for enrichment joins. This minimizes memory usage
    when coordinating enrichers.

    Attributes:
        delta_reader: DeltaReaderPort for reading Silver tables.
        logger: Structured logger.

    Example:
        >>> extractor = KeyExtractorService(
        ...     delta_reader=delta_reader, logger=logger
        ... )
        >>> keys_df = await extractor.extract(
        ...     silver_table="silver/chembl/publication",
        ...     keys=("document_id", "doi", "pmid"),
        ... )
        >>> keys_df.columns
        ['document_id', 'doi', 'pmid']
    """

    def __init__(
        self,
        delta_reader: DeltaReaderPort,
        logger: LoggerPort,
    ) -> None:
        """Initialize key extractor service.

        Args:
            delta_reader: DeltaReaderPort for reading Delta tables.
            logger: Structured logger.
        """
        self._delta_reader = delta_reader
        self._logger = logger

    async def _read_silver_table(self, path: str) -> pl.DataFrame:
        """Read a Silver table via DeltaReaderPort.

        Args:
            path: Path to Silver table (relative or absolute).

        Returns:
            DataFrame with table contents.
        """
        import polars as pl

        pa_table = await self._delta_reader.read_table(path)
        result = pl.from_arrow(pa_table)
        # from_arrow may return Series for single-column tables
        if isinstance(result, pl.Series):
            return result.to_frame()
        return result

    async def extract(
        self,
        silver_table: str,
        keys: Sequence[str],
    ) -> pl.DataFrame:
        """Extract join keys from seed Silver table.

        Reads only the specified key columns from the Silver table.
        Removes duplicates and null-only rows.

        Args:
            silver_table: Path to seed Silver table.
            keys: Column names to extract as join keys.

        Returns:
            DataFrame with only the key columns, deduplicated.

        Raises:
            ValueError: If Silver table is empty or keys not found.

        Example:
            >>> keys_df = await extractor.extract(
            ...     silver_table="silver/chembl/publication",
            ...     keys=("doi", "pmid"),
            ... )
            >>> len(keys_df)
            1000
        """
        import polars as pl

        self._logger.info(
            "Extracting keys from seed Silver",
            table=silver_table,
            keys=list(keys),
        )

        # Read full table via DeltaReaderPort
        full_df = await self._read_silver_table(silver_table)

        if len(full_df) == 0:
            raise ValueError(f"Seed Silver table is empty: {silver_table}")

        # Validate keys exist
        available_cols = set(full_df.columns)
        missing_keys = set(keys) - available_cols
        if missing_keys:
            raise ValueError(
                f"Keys not found in seed table: {missing_keys}. "
                f"Available: {available_cols}"
            )

        # Select only key columns
        keys_df = full_df.select(list(keys))

        # Remove rows where ALL keys are null
        # (but keep rows where at least one key is non-null)
        null_check = pl.all_horizontal([pl.col(k).is_null() for k in keys])
        keys_df = keys_df.filter(~null_check)

        # Deduplicate
        original_count = len(keys_df)
        keys_df = keys_df.unique()
        dedup_count = len(keys_df)

        self._logger.info(
            "Keys extracted",
            table=silver_table,
            original_records=original_count,
            unique_keys=dedup_count,
            duplicates_removed=original_count - dedup_count,
        )

        return keys_df

================================================================================
File: merger.py
Path: composite\merger.py
================================================================================
"""Merge Service for composite pipelines. See ADR-026."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from bioetl.application.composite.column_orderer import ColumnOrderer
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.deduplication import EnricherDeduplicator
from bioetl.domain.composite.result import EnrichmentResult, MergeResult
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy

JoinHow = Literal["inner", "left", "right", "full", "semi", "anti", "cross", "outer"]

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import EnricherConfig, MergeConfig
    from bioetl.domain.ports import DeltaReaderPort, LoggerPort, StoragePort


def _path_to_table_name(path: str) -> str:
    """Convert a full path to a table name by stripping layer prefix.

    Handles both relative and absolute paths:
    - "silver/chembl/activity" → "chembl/activity"
    - "data/output/silver/chembl/activity" → "chembl/activity"
    - "gold/composite/publication" → "composite/publication"
    - "data/output/gold/composite/publication" → "composite/publication"

    Args:
        path: Path containing a layer segment (silver/, gold/, bronze/).

    Returns:
        Table name with layer prefix stripped.
    """
    # Normalize path separators
    normalized = path.replace("\\", "/")

    # Find and strip layer prefix (handles both relative and absolute paths)
    for layer in ("silver/", "gold/", "bronze/"):
        if layer in normalized:
            # Take everything after the layer prefix
            idx = normalized.find(layer)
            return normalized[idx + len(layer) :]

    return path


class MergeService:
    """Merges enriched data with conflict resolution and lineage tracking."""

    # Join keys that require case-insensitive matching (normalized to lowercase)
    # DOI: Different providers may store in different cases (10.1038/NATURE vs 10.1038/nature)
    # PMID: Typically numeric but may have inconsistent formatting
    _NORMALIZE_JOIN_KEYS: frozenset[str] = frozenset({"doi", "pmid", "pmc_id"})

    # System columns to drop from enrichers before join
    # These are ETL metadata columns that should only come from seed
    # Prevents duplicate columns like _dq_error.A, _dq_error.B after merge
    _SYSTEM_COLUMNS_TO_DROP: frozenset[str] = frozenset(
        {
            "_run_id",
            "_run_type",
            "_source_batch_id",
            "_ingestion_ts",
            "_dq_warn",
            "_dq_error",
            "_index",
            "_lookup_method",
            "_original_id",
            "_source",  # Data source identifier (e.g., "chembl", "crossref")
        }
    )

    def __init__(
        self,
        merge_config: MergeConfig,
        storage: StoragePort,
        logger: LoggerPort,
        delta_reader: DeltaReaderPort | None = None,
    ) -> None:
        self._config = merge_config
        self._storage = storage
        self._logger = logger
        self._delta_reader = delta_reader
        self._deduplicator = EnricherDeduplicator(logger)
        self._renamer = ColumnRenamer(logger)
        # Pass column_groups from config if available for YAML-based ordering
        self._orderer = ColumnOrderer(
            logger,
            column_groups=merge_config.column_groups
            if merge_config.column_groups
            else None,
        )

    async def merge(
        self,
        seed_table: str,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
        seed_pipeline: str | None = None,
    ) -> MergeResult:
        """Merge seed and enricher data into unified output.

        Args:
            seed_table: Path to seed Silver table (e.g., "silver/chembl/publication").
            enrichers: Sequence of enricher configurations.
            enrichment_results: Results from enricher execution.
            run_id: Composite pipeline run ID.
            seed_pipeline: Seed pipeline name (e.g., "chembl_publication").
                If None, will be inferred from seed_table path.
                Used for intelligent column renaming during merge.

        Returns:
            MergeResult with statistics and output paths.
        """
        started_at = datetime.now(tz=UTC)

        # Step 1: Read seed data
        self._logger.info(
            "Reading seed table",
            table=seed_table,
        )
        seed_df = await self._read_silver_table(seed_table)
        records_from_seed = len(seed_df)

        # Determine effective seed pipeline name
        # Priority: explicit parameter > inferred from path
        effective_seed_pipeline = seed_pipeline or self._infer_pipeline_from_table(
            seed_table
        )

        # Rename seed columns to qualified format: {provider}.{entity}.{field}
        # Including join keys (doi, pmid, pmc_id) for full traceability
        if effective_seed_pipeline:
            self._logger.debug(
                "Using seed pipeline for column renaming",
                seed_pipeline=effective_seed_pipeline,
            )
            seed_df = self._renamer.rename_dataframe(
                seed_df,
                effective_seed_pipeline,
                exclude_join_keys=False,  # Rename ALL columns including join keys
            )
            self._logger.info(
                "Renamed seed columns to qualified format",
                pipeline=effective_seed_pipeline,
                qualified_count=len(
                    [c for c in seed_df.columns if "." in c and not c.startswith("_")]
                ),
            )

        # Track sources used
        sources_used = ["seed"]
        enricher_dfs: dict[str, pl.DataFrame] = {}

        # Step 2: Read successful enricher tables
        for enricher in enrichers:
            result = enrichment_results.get(enricher.pipeline)
            if result is None or not result.is_success:
                continue

            enricher_table = enricher.silver_table or self._infer_silver_table(
                enricher.pipeline
            )

            self._logger.info(
                "Reading enricher table",
                enricher=enricher.pipeline,
                table=enricher_table,
            )

            try:
                enricher_df = await self._read_silver_table(enricher_table)
                enricher_dfs[enricher.pipeline] = enricher_df
                sources_used.append(enricher.pipeline)
            except Exception as e:
                self._logger.warning(
                    "Failed to read enricher table",
                    enricher=enricher.pipeline,
                    error=str(e),
                )

        # Step 3: Apply joins with intelligent column renaming
        merged_df = await self._apply_joins(
            seed_df=seed_df,
            enricher_dfs=enricher_dfs,
            enrichers=enrichers,
            seed_pipeline=effective_seed_pipeline,
        )

        # Step 4: Resolve conflicts
        merged_df = self._resolve_conflicts(
            df=merged_df,
            enricher_dfs=enricher_dfs,
            enrichers=enrichers,
            seed_pipeline=effective_seed_pipeline,
        )

        # Step 5: Add lineage metadata
        merged_df = self._add_lineage(
            df=merged_df,
            enrichment_results=enrichment_results,
            run_id=run_id,
            sources_used=sources_used,
        )

        # Step 6: Order columns by semantic groups
        merged_df = self._orderer.order_columns(merged_df)
        self._logger.info(
            "Ordered columns by semantic groups",
            total_columns=len(merged_df.columns),
        )

        # Calculate statistics before writing
        records_merged = len(merged_df)
        records_enriched = self._count_enriched_records(
            merged_df, enrichers, effective_seed_pipeline
        )

        # Step 7: Write to Silver via StoragePort
        self._logger.info(
            "Writing merged Silver table",
            path=self._config.output_silver_path,
            records=records_merged,
        )
        await self._write_merged_silver(
            merged_df, run_id=run_id, sources_used=sources_used
        )

        # Step 8: Write to Gold via StoragePort
        self._logger.info(
            "Writing merged Gold table",
            path=self._config.output_gold_path,
            records=records_merged,
        )
        await self._write_merged_gold(
            merged_df, run_id=run_id, sources_used=sources_used
        )

        completed_at = datetime.now(tz=UTC)
        duration = (completed_at - started_at).total_seconds()

        self._logger.info(
            "Merge completed",
            records_merged=records_merged,
            sources_used=sources_used,
            duration_seconds=duration,
        )

        return MergeResult(
            records_merged=records_merged,
            records_from_seed=records_from_seed,
            records_enriched=records_enriched,
            records_fully_enriched=self._count_fully_enriched(merged_df, enrichers),
            sources_used=tuple(sources_used),
            field_coverage=self._calculate_field_coverage(merged_df),
            duration_seconds=duration,
            output_silver_path=self._config.output_silver_path,
            output_gold_path=self._config.output_gold_path,
        )

    async def _read_silver_table(self, path: str) -> pl.DataFrame:
        """Read a Silver table.

        Uses DeltaReaderPort when configured (actual operation),
        or StoragePort when delta_reader is not set (for testing with mocks).

        Args:
            path: Table path like "silver/chembl/activity".

        Returns:
            Polars DataFrame with table contents.
        """
        import polars as pl

        # Use DeltaReaderPort when configured
        if self._delta_reader is not None:
            arrow_table = await self._delta_reader.read_table(path)
            result = pl.from_arrow(arrow_table)
            # from_arrow may return Series for single-column tables
            if isinstance(result, pl.Series):
                return result.to_frame()
            return result

        # Fall back to StoragePort (for testing with mocks)
        table_name = _path_to_table_name(path)
        records = await self._storage.read_silver(table_name)
        if not records:
            return pl.DataFrame()
        return pl.DataFrame(records)

    def _coerce_null_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Coerce Null-typed columns to String for Delta Lake compatibility.

        Delta Lake doesn't support Null type, so columns with all nulls
        (which Polars infers as Null type) must be cast to a concrete type.

        Args:
            df: DataFrame that may have Null-typed columns.

        Returns:
            DataFrame with Null columns cast to String.
        """
        import polars as pl

        null_cols = [col for col in df.columns if df[col].dtype == pl.Null]
        if null_cols:
            self._logger.debug(
                "Coercing null columns to String",
                columns=null_cols,
            )
            df = df.with_columns([pl.col(col).cast(pl.String) for col in null_cols])
        return df

    async def _write_merged_silver(
        self,
        df: pl.DataFrame,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write merged data to Silver layer via StoragePort.

        Args:
            df: Polars DataFrame to write.
            run_id: Composite run ID for metadata tracking.
            sources_used: List of source pipelines used in merge.
        """
        # Coerce null columns for Delta Lake compatibility
        df = self._coerce_null_columns(df)

        table_name = _path_to_table_name(self._config.output_silver_path)
        records = df.to_dicts()
        await self._storage.write_silver_merged(
            table_name,
            records,
            run_id=run_id,
            sources_used=sources_used,
        )

    async def _write_merged_gold(
        self,
        df: pl.DataFrame,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write merged data to Gold layer via StoragePort.

        Args:
            df: Polars DataFrame to write.
            run_id: Composite run ID for metadata tracking.
            sources_used: List of source pipelines used in merge.
        """
        # Coerce null columns for Delta Lake compatibility
        df = self._coerce_null_columns(df)

        table_name = _path_to_table_name(self._config.output_gold_path)
        records = df.to_dicts()
        await self._storage.write_gold_merged(
            table_name,
            records,
            run_id=run_id,
            sources_used=sources_used,
        )

    def _infer_silver_table(self, pipeline_name: str) -> str:
        """Infer Silver table path from pipeline name."""
        # Convention: pipeline_name is "{provider}_{entity}"
        parts = pipeline_name.split("_", 1)
        if len(parts) == 2:
            provider, entity = parts
            return f"silver/{provider}/{entity}"
        return f"silver/{pipeline_name}"

    def _infer_pipeline_from_table(self, table_path: str) -> str | None:
        """Infer pipeline name from Silver table path.

        Converts a table path like "silver/chembl/publication" to
        pipeline name "chembl_publication".

        Args:
            table_path: Silver table path.

        Returns:
            Pipeline name or None if cannot be inferred.

        Example:
            >>> merger._infer_pipeline_from_table("silver/chembl/publication")
            'chembl_publication'
            >>> merger._infer_pipeline_from_table("silver/crossref/publication")
            'crossref_publication'
        """
        # Check if path contains a recognized layer prefix
        normalized = table_path.replace("\\", "/")
        has_layer = any(
            layer in normalized for layer in ("silver/", "gold/", "bronze/")
        )
        if not has_layer:
            return None

        table_name = _path_to_table_name(table_path)
        # table_name is now like "chembl/publication"
        parts = table_name.split("/")
        if len(parts) == 2:
            return f"{parts[0]}_{parts[1]}"
        return None

    def _find_join_key_column(
        self, key: str, columns: list[str], pipeline: str | None = None
    ) -> str | None:
        """Find column name for a join key (qualified or unqualified)."""
        if pipeline:
            try:
                provider, entity = self._parse_pipeline_name(pipeline)
                qualified = f"{provider}.{entity}.{key}"
                if qualified in columns:
                    return qualified
            except ValueError:
                pass
        if key in columns:
            return key
        return next((c for c in columns if c.endswith(f".{key}")), None)

    def _normalize_join_key_columns(
        self, df: pl.DataFrame, join_keys: list[str], pipeline: str | None = None
    ) -> pl.DataFrame:
        """Normalize join key columns to lowercase for case-insensitive matching."""
        import polars as pl

        cols = df.columns
        normalize = [
            c
            for key in join_keys
            if key in self._NORMALIZE_JOIN_KEYS
            for c in [self._find_join_key_column(key, cols, pipeline)]
            if c
        ]
        if not normalize:
            return df
        return df.with_columns(
            [pl.col(c).str.to_lowercase().alias(c) for c in normalize]
        )

    def _parse_pipeline_name(self, pipeline: str) -> tuple[str, str]:
        """Parse pipeline name into (provider, entity).

        Pipeline names follow the format "{provider}_{entity}".
        For example: 'chembl_publication' → ('chembl', 'publication').

        Args:
            pipeline: Pipeline name in format "provider_entity".

        Returns:
            Tuple of (provider, entity).

        Raises:
            ValueError: If pipeline name doesn't contain underscore separator.

        Example:
            >>> merger._parse_pipeline_name("chembl_publication")
            ('chembl', 'publication')
            >>> merger._parse_pipeline_name("crossref_publication")
            ('crossref', 'publication')
        """
        if "_" not in pipeline:
            raise ValueError(
                f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
            )
        parts = pipeline.split("_", 1)
        return (parts[0], parts[1])

    def _extract_field_from_qualified(self, column: str) -> str:
        """Extract field name from qualified column name.

        Args:
            column: Column name, possibly in qualified format.

        Returns:
            Field name if qualified (x.y.z → z), or original column name if not.

        Example:
            >>> merger._extract_field_from_qualified("chembl.publication.title")
            'title'
            >>> merger._extract_field_from_qualified("title")
            'title'
            >>> merger._extract_field_from_qualified("crossref.title")
            'crossref.title'
        """
        parts = column.split(".")
        if len(parts) == 3:
            return parts[2]
        return column

    def _find_next_suffix(self, base_col: str, existing_cols: set[str]) -> str:
        """Find next available suffix for a conflicting column.

        Iterates through A, B, C, ... Z, AA, AB, ... to find an unused suffix.

        Args:
            base_col: Base column name without suffix.
            existing_cols: Set of existing column names.

        Returns:
            Next available suffix letter(s).

        Example:
            >>> merger._find_next_suffix("title", {"title", "title.A", "title.B"})
            'C'
            >>> merger._find_next_suffix("title", {"title"})
            'A'
        """
        # Generate suffixes: A, B, C, ..., Z, AA, AB, ...
        suffix_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        # Try single letters first
        for char in suffix_chars:
            candidate = f"{base_col}.{char}"
            if candidate not in existing_cols:
                return char

        # Try double letters (AA, AB, ..., ZZ)
        for first in suffix_chars:
            for second in suffix_chars:
                suffix = f"{first}{second}"
                candidate = f"{base_col}.{suffix}"
                if candidate not in existing_cols:
                    return suffix

        # Fallback (should never reach here with 702 possible suffixes)
        raise ValueError(f"Exhausted all suffixes for column '{base_col}'")

    def _detect_and_resolve_conflicts(
        self,
        seed_df: pl.DataFrame,
        enricher_df: pl.DataFrame,
        join_keys: set[str],
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Detect and resolve column name conflicts between seed and enricher.

        After prefix application, there may still be conflicts when:
        - Seed already has a prefixed column (e.g., "crossref.title")
        - Enricher gets the same prefix (e.g., "crossref.title")

        Resolution: Keep seed columns unchanged, add incremental suffixes
        (A, B, C, ...) to enricher columns.

        Args:
            seed_df: Seed DataFrame (columns are NOT renamed).
            enricher_df: Enricher DataFrame (already with prefixes applied).
            join_keys: Set of join key columns to exclude from conflict resolution.

        Returns:
            Tuple of (seed_df unchanged, modified_enricher_df) with conflicts resolved.

        Example:
            >>> seed = pl.DataFrame({"doi": ["10.1/a"], "title": ["T1"]})
            >>> enricher = pl.DataFrame({"doi": ["10.1/a"], "title": ["T2"]})
            >>> seed_out, enricher_out = merger._detect_and_resolve_conflicts(
            ...     seed, enricher, {"doi"}
            ... )
            >>> seed_out.columns
            ['doi', 'title']
            >>> enricher_out.columns
            ['doi', 'title.A']
        """
        seed_cols = set(seed_df.columns)
        enricher_cols = set(enricher_df.columns)

        # Find conflicts (excluding join keys)
        conflicts = (seed_cols & enricher_cols) - join_keys

        if not conflicts:
            return seed_df, enricher_df

        # Build rename map for enricher columns only
        # Use incremental suffixes, checking existing columns
        enricher_rename = {}
        for col in conflicts:
            suffix = self._find_next_suffix(col, seed_cols)
            enricher_rename[col] = f"{col}.{suffix}"

        self._logger.warning(
            "Column name conflicts detected after prefixing",
            conflicts=list(conflicts),
            resolution=f"Renaming enricher columns: {enricher_rename}",
        )

        # Seed columns remain unchanged, only enricher gets renamed
        return seed_df, enricher_df.rename(enricher_rename)

    async def _apply_joins(
        self,
        seed_df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply join strategy with qualified column renaming.

        Column renaming uses ColumnRenamer to apply {provider}.{entity}.{field}
        format to enricher columns for qualified column matching.

        Join keys (doi, pmid, pmc_id) are normalized to lowercase for
        case-insensitive matching across providers.

        Conflict resolution:
        - After prefixing, remaining conflicts get .A/.B suffixes

        Args:
            seed_df: Seed DataFrame to join to.
            enricher_dfs: Mapping of enricher pipeline name to DataFrame.
            enrichers: Sequence of enricher configurations.
            seed_pipeline: Seed pipeline name (unused, kept for compatibility).

        Returns:
            Merged DataFrame with all enricher data joined.

        Example:
            >>> # Cross-provider merge: chembl_publication + crossref_publication
            >>> # Column "title" in enricher → "crossref.publication.title"
            >>> merged = await merger._apply_joins(
            ...     seed_df, enricher_dfs, enrichers, "chembl_publication"
            ... )
        """
        merged = seed_df

        for enricher in enrichers:
            if enricher.pipeline not in enricher_dfs:
                continue

            enricher_df = enricher_dfs[enricher.pipeline]
            join_keys_list = list(enricher.join_keys)

            # Primary key is the FIRST join key - used for actual join
            # Secondary keys are fallbacks but NOT used in join operation
            primary_key = join_keys_list[0]

            # Deduplicate enricher before join to prevent fan-out
            enricher_df = self._deduplicator.deduplicate(
                enricher_df=enricher_df,
                join_keys=join_keys_list,
                enricher_name=enricher.pipeline,
            )

            # Normalize join key columns for case-insensitive matching
            # This ensures DOIs like "10.1038/NATURE" match "10.1038/nature"
            # For merged (seed), columns are already qualified (chembl.publication.doi)
            # For enricher, columns are still unqualified at this point
            merged = self._normalize_join_key_columns(
                merged, join_keys_list, pipeline=seed_pipeline
            )
            enricher_df = self._normalize_join_key_columns(
                enricher_df,
                join_keys_list,
                pipeline=None,  # Still unqualified
            )

            # Rename enricher columns to qualified format: {provider}.{entity}.{field}
            # Including join keys for full traceability
            enricher_df = self._renamer.rename_dataframe(
                enricher_df,
                enricher.pipeline,
                exclude_join_keys=False,  # Rename ALL columns including join keys
            )

            self._logger.debug(
                "Renamed enricher columns to qualified format",
                enricher=enricher.pipeline,
                qualified_count=len(
                    [
                        c
                        for c in enricher_df.columns
                        if "." in c and not c.startswith("_")
                    ]
                ),
            )

            # Drop system columns from enricher to prevent duplicates like _dq_error.A
            # System columns should only come from seed (ETL metadata)
            enricher_df = self._drop_system_columns(enricher_df)

            # Calculate qualified join key names for both seed and enricher
            # Support both pre-renamed (qualified) and unqualified seed columns
            seed_join_key_qualified: str | None = None
            seed_join_key: str = primary_key  # Default to unqualified

            if seed_pipeline is not None:
                try:
                    seed_provider, seed_entity = self._parse_pipeline_name(
                        seed_pipeline
                    )
                    seed_join_key_qualified = (
                        f"{seed_provider}.{seed_entity}.{primary_key}"
                    )
                    # Use qualified if present, otherwise fallback to unqualified
                    if seed_join_key_qualified in merged.columns:
                        seed_join_key = seed_join_key_qualified
                    elif primary_key in merged.columns:
                        seed_join_key = primary_key
                except ValueError:
                    # Fallback if seed_pipeline is invalid
                    seed_join_key = primary_key

            try:
                enricher_provider, enricher_entity = self._parse_pipeline_name(
                    enricher.pipeline
                )
                enricher_join_key = (
                    f"{enricher_provider}.{enricher_entity}.{primary_key}"
                )
            except ValueError:
                enricher_join_key = primary_key

            # Detect and resolve remaining conflicts
            # Exclude both seed and enricher join keys from conflict detection
            join_key_set = {seed_join_key, enricher_join_key}
            if seed_join_key_qualified and seed_join_key_qualified != seed_join_key:
                join_key_set.add(seed_join_key_qualified)
            merged, enricher_df = self._detect_and_resolve_conflicts(
                merged, enricher_df, join_key_set
            )

            # Apply join based on strategy using left_on/right_on for qualified keys
            how = self._get_polars_join_type()

            if (
                seed_join_key in merged.columns
                and enricher_join_key in enricher_df.columns
            ):
                merged = merged.join(
                    enricher_df,
                    left_on=seed_join_key,
                    right_on=enricher_join_key,
                    how=how,
                    suffix=f"_{enricher.pipeline}",
                )

        return merged

    def _get_polars_join_type(self) -> JoinHow:
        """Convert MergeStrategy to Polars join type."""
        match self._config.strategy:
            case MergeStrategy.LEFT_OUTER:
                return "left"
            case MergeStrategy.INNER:
                return "inner"
            case MergeStrategy.UNION:
                return "full"
            case _:
                return "left"

    def _drop_system_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Drop system columns from DataFrame to prevent duplicates after join.

        System columns (_dq_error, _run_id, etc.) should only come from the seed.
        Dropping them from enrichers prevents columns like _dq_error.A, _dq_error.B
        after multiple joins.

        Args:
            df: Enricher DataFrame.

        Returns:
            DataFrame with system columns removed.
        """
        columns_to_drop = [
            col for col in df.columns if col in self._SYSTEM_COLUMNS_TO_DROP
        ]

        if columns_to_drop:
            self._logger.debug(
                "Dropping system columns from enricher",
                columns=columns_to_drop,
            )
            return df.drop(columns_to_drop)

        return df

    def _get_enricher_prefix(
        self,
        enricher_pipeline: str,
        seed_pipeline: str | None = None,
    ) -> str:
        """Get column prefix for enricher.

        Returns {provider}.{entity}. format for qualified column matching.

        Args:
            enricher_pipeline: Enricher pipeline name.
            seed_pipeline: Unused, kept for backward compatibility.

        Returns:
            Prefix string WITH trailing dot: '{provider}.{entity}.'
        """
        try:
            provider, entity = self._parse_pipeline_name(enricher_pipeline)
            return f"{provider}.{entity}."
        except ValueError:
            # Fallback for non-standard pipeline names
            return f"{enricher_pipeline}_"

    def _extract_base_column(self, column: str, prefix: str) -> str | None:
        """Extract base column name from a prefixed column.

        Supports both:
        - New format: "crossref.publication.title" with prefix "crossref.publication." → "title"
        - Legacy format: "crossref_title" with prefix "crossref_" → "title"

        Args:
            column: Column name that may have a prefix.
            prefix: Prefix to strip (WITH trailing dot or underscore).

        Returns:
            Base column name if column starts with prefix, None otherwise.
        """
        if column.startswith(prefix):
            return column[len(prefix) :]
        return None

    def _resolve_conflicts(
        self,
        df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply conflict resolution based on configured strategy.

        Args:
            df: Merged DataFrame with prefixed columns.
            enricher_dfs: Original enricher DataFrames (for reference).
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name for prefix computation.

        Returns:
            DataFrame with conflicts resolved.
        """
        match self._config.conflict_resolution:
            case ConflictResolution.SEED_PRIORITY:
                return self._coalesce_prefer_seed(df, enrichers, seed_pipeline)
            case ConflictResolution.ENRICHER_PRIORITY:
                return self._coalesce_prefer_enricher(df, enrichers, seed_pipeline)
            case ConflictResolution.COALESCE:
                return self._coalesce_first_non_null(df, enrichers, seed_pipeline)
            case ConflictResolution.EXPLICIT_RULES:
                return self._apply_explicit_rules(df, enrichers, seed_pipeline)
            case ConflictResolution.LATEST_TIMESTAMP:
                # Would require timestamp columns - fall back to seed
                return self._coalesce_prefer_seed(df, enrichers, seed_pipeline)
            case _:
                return df

    def _can_coalesce(self, df: pl.DataFrame, col1: str, col2: str) -> bool:
        """Check if two columns can be coalesced (compatible types).

        Args:
            df: DataFrame containing the columns.
            col1: First column name.
            col2: Second column name.

        Returns:
            True if columns have compatible types for coalescing.
        """
        import polars as pl

        type1 = df[col1].dtype
        type2 = df[col2].dtype

        # Same type is always compatible
        if type1 == type2:
            return True

        # Null type is compatible with anything
        if type1 == pl.Null or type2 == pl.Null:
            return True

        # List types are incompatible with scalar types
        # Different scalar types may be compatible (Polars handles casting)
        return isinstance(type1, pl.List) == isinstance(type2, pl.List)

    def _coalesce_prefer_seed(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Coalesce preferring seed values.

        Groups columns by field name and coalesces within each group,
        with seed columns having priority.

        Args:
            df: Merged DataFrame with qualified columns.
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name for identifying seed columns.

        Returns:
            DataFrame with coalesced columns.
        """
        import polars as pl

        result = df

        # Parse seed prefix for identification
        seed_prefix: str | None = None
        if seed_pipeline:
            try:
                provider, entity = self._parse_pipeline_name(seed_pipeline)
                seed_prefix = f"{provider}.{entity}."
            except ValueError:
                pass

        # Group columns by field name
        field_groups: dict[str, list[str]] = {}
        for col in result.columns:
            if col.startswith("_"):  # Skip system columns
                continue
            field = self._extract_field_from_qualified(col)
            if field not in field_groups:
                field_groups[field] = []
            field_groups[field].append(col)

        # Process each group with multiple columns
        for _field, columns in field_groups.items():
            if len(columns) <= 4:
                continue

            # Sort: seed columns first, then enrichers
            def sort_key(c: str) -> int:
                if seed_prefix and c.startswith(seed_prefix):
                    return 0  # Seed first
                return 1  # Enrichers after

            sorted_cols = sorted(columns, key=sort_key)

            # Filter compatible columns (same dtype)
            compatible_cols = [sorted_cols[0]]
            for col in sorted_cols[1:]:
                if self._can_coalesce(result, sorted_cols[0], col):
                    compatible_cols.append(col)

            if len(compatible_cols) > 1:
                # Coalesce into the first (seed) column
                target_col = compatible_cols[0]
                result = result.with_columns(
                    pl.coalesce(*[pl.col(c) for c in compatible_cols]).alias(target_col)
                )
                # Drop non-target columns
                cols_to_drop = [c for c in compatible_cols[1:] if c in result.columns]
                if cols_to_drop:
                    result = result.drop(cols_to_drop)

        return result

    def _coalesce_prefer_enricher(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Coalesce preferring enricher values.

        Groups columns by field name and coalesces within each group,
        with enricher columns having priority over seed.

        Args:
            df: Merged DataFrame with qualified columns.
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name for identifying seed columns.

        Returns:
            DataFrame with coalesced columns.
        """
        import polars as pl

        result = df

        seed_prefix: str | None = None
        if seed_pipeline:
            try:
                provider, entity = self._parse_pipeline_name(seed_pipeline)
                seed_prefix = f"{provider}.{entity}."
            except ValueError:
                pass

        field_groups: dict[str, list[str]] = {}
        for col in result.columns:
            if col.startswith("_"):
                continue
            field = self._extract_field_from_qualified(col)
            if field not in field_groups:
                field_groups[field] = []
            field_groups[field].append(col)

        for _field, columns in field_groups.items():
            if len(columns) <= 1:
                continue

            # Sort: enrichers first, seed last
            def sort_key(c: str) -> int:
                if seed_prefix and c.startswith(seed_prefix):
                    return 1  # Seed last
                return 0  # Enrichers first

            sorted_cols = sorted(columns, key=sort_key)

            compatible_cols = [sorted_cols[0]]
            for col in sorted_cols[1:]:
                if self._can_coalesce(result, sorted_cols[0], col):
                    compatible_cols.append(col)

            if len(compatible_cols) > 1:
                target_col = compatible_cols[0]
                result = result.with_columns(
                    pl.coalesce(*[pl.col(c) for c in compatible_cols]).alias(target_col)
                )
                cols_to_drop = [c for c in compatible_cols[1:] if c in result.columns]
                if cols_to_drop:
                    result = result.drop(cols_to_drop)

        return result

    def _coalesce_first_non_null(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Coalesce taking first non-null value.

        Args:
            df: Merged DataFrame with prefixed columns.
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name for prefix computation.

        Returns:
            DataFrame with coalesced columns.
        """
        # Same as seed priority for now
        return self._coalesce_prefer_seed(df, enrichers, seed_pipeline)

    def _collect_field_columns(
        self,
        field: str,
        enrichers: Sequence[EnricherConfig],
        available_columns: set[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Collect all columns for a field from all sources.

        Searches for qualified format ONLY:
        - Seed: {seed_provider}.{seed_entity}.{field}
        - Enrichers: {enricher_provider}.{enricher_entity}.{field}

        Legacy unqualified names are NOT searched (seed already renamed).

        Args:
            field: Base field name (e.g., 'title').
            enrichers: Enricher configurations.
            available_columns: Columns present in DataFrame.
            seed_pipeline: Seed pipeline name for qualified lookup.

        Returns:
            List of matching qualified column names.
        """
        columns: list[str] = []

        # 1. Seed qualified format: {seed_provider}.{seed_entity}.{field}
        if seed_pipeline:
            try:
                seed_provider, seed_entity = self._parse_pipeline_name(seed_pipeline)
                seed_qualified = f"{seed_provider}.{seed_entity}.{field}"
                if seed_qualified in available_columns:
                    columns.append(seed_qualified)
            except ValueError:
                self._logger.debug(
                    "Could not parse seed pipeline for field collection",
                    seed_pipeline=seed_pipeline,
                    field=field,
                )

        # 2. Each enricher's qualified format: {provider}.{entity}.{field}
        for enricher in enrichers:
            try:
                provider, entity = self._parse_pipeline_name(enricher.pipeline)
                enricher_qualified = f"{provider}.{entity}.{field}"
                if (
                    enricher_qualified in available_columns
                    and enricher_qualified not in columns
                ):
                    columns.append(enricher_qualified)
            except ValueError:
                # Fallback: legacy prefix format {pipeline}_{field}
                prefix = self._get_enricher_prefix(enricher.pipeline, seed_pipeline)
                legacy_col = f"{prefix}{field}".rstrip(".")
                if legacy_col in available_columns and legacy_col not in columns:
                    columns.append(legacy_col)

        return columns

    def _order_columns_by_priority(
        self,
        field: str,
        columns: list[str],
        priorities: Sequence[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Order columns by source priority for coalescing.

        Priority format in config:
        - 'seed' - refers to seed pipeline (resolved dynamically)
        - '{provider}' - matches {provider}.*.{field}
        - '{provider}.{entity}' - explicit match

        Args:
            field: Base field name.
            columns: Available column names for this field.
            priorities: Priority list from config (e.g., ['seed', 'crossref']).
            seed_pipeline: Seed pipeline for resolving 'seed' priority.

        Returns:
            Ordered list of columns by priority.
        """
        ordered_cols: list[str] = []
        columns_set = set(columns)

        # Parse seed for matching
        seed_provider: str | None = None
        seed_entity: str | None = None
        if seed_pipeline:
            try:
                seed_provider, seed_entity = self._parse_pipeline_name(seed_pipeline)
            except ValueError:
                pass

        for source in priorities:
            source_lower = source.lower()
            qualified: str | None = None

            # Handle 'seed' keyword - resolve to actual seed provider.entity
            if source_lower == "seed":
                if seed_provider and seed_entity:
                    qualified = f"{seed_provider}.{seed_entity}.{field}"

            # Handle explicit provider.entity format: 'crossref.publication'
            elif "." in source:
                parts = source.split(".", 1)
                provider, entity = parts[0].lower(), parts[1].lower()
                qualified = f"{provider}.{entity}.{field}"

            # Handle provider-only: find matching column
            else:
                provider = source_lower
                # Check if this provider matches seed
                if seed_provider and provider == seed_provider.lower():
                    if seed_entity:
                        qualified = f"{provider}.{seed_entity}.{field}"
                else:
                    # Try to find any column with this provider
                    for col in columns_set:
                        if col.startswith(f"{provider}.") and col.endswith(f".{field}"):
                            qualified = col
                            break

            if qualified and qualified in columns_set and qualified not in ordered_cols:
                ordered_cols.append(qualified)

        # Append remaining columns not in priority list (preserving discovery order)
        for col in columns:
            if col not in ordered_cols:
                ordered_cols.append(col)

        return ordered_cols

    def _filter_compatible_columns(
        self,
        df: pl.DataFrame,
        field: str,
        ordered_cols: list[str],
    ) -> tuple[list[str], list[str]]:
        """Filter columns to only those compatible for coalescing.

        Args:
            df: DataFrame containing the columns.
            field: Base field name for logging.
            ordered_cols: Ordered list of column names.

        Returns:
            Tuple of (compatible_columns, incompatible_columns).
        """
        if not ordered_cols:
            return [], []

        base_col = ordered_cols[0]
        compatible_cols = [base_col]
        incompatible_cols: list[str] = []

        for col in ordered_cols[1:]:
            if self._can_coalesce(df, base_col, col):
                compatible_cols.append(col)
            else:
                self._logger.debug(
                    "Skipping column with incompatible type in explicit rules",
                    field=field,
                    incompatible_col=col,
                    base_type=str(df[base_col].dtype),
                    col_type=str(df[col].dtype),
                )
                incompatible_cols.append(col)

        return compatible_cols, incompatible_cols

    def _apply_explicit_rules(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply explicit field priority rules.

        Coalesces columns by priority, handling type compatibility.

        Args:
            df: Merged DataFrame with prefixed columns.
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name for prefix computation.

        Returns:
            DataFrame with explicit rules applied.
        """
        import polars as pl

        result = df
        available_columns = set(df.columns)

        for field, priorities in self._config.field_priorities.items():
            columns = self._collect_field_columns(
                field, enrichers, available_columns, seed_pipeline
            )

            if len(columns) <= 1:
                continue

            ordered_cols = self._order_columns_by_priority(
                field, columns, priorities, seed_pipeline
            )

            if not ordered_cols:
                continue

            compatible_cols, _ = self._filter_compatible_columns(
                result, field, ordered_cols
            )

            # Coalesce compatible columns into the first (highest priority) column
            if len(compatible_cols) > 1:
                target_col = compatible_cols[
                    0
                ]  # Keep the first column name (qualified)
                result = result.with_columns(
                    pl.coalesce(*[pl.col(c) for c in compatible_cols]).alias(target_col)
                )

            # Drop all non-target columns
            cols_to_drop = [col for col in compatible_cols[1:] if col in result.columns]
            if cols_to_drop:
                result = result.drop(cols_to_drop)

        return result

    def _add_lineage(
        self,
        df: pl.DataFrame,
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
        sources_used: list[str],
    ) -> pl.DataFrame:
        """Add lineage metadata columns to DataFrame."""
        import polars as pl

        # Build enrichment status dict
        status_dict = {
            name: result.status.value for name, result in enrichment_results.items()
        }

        # Add lineage columns
        return df.with_columns(
            [
                pl.lit(run_id).alias("_composite_run_id"),
                pl.lit(str(sources_used)).alias("_source_providers"),
                pl.lit(str(status_dict)).alias("_enrichment_status"),
                pl.lit(datetime.now(tz=UTC).isoformat()).alias("_lineage_created_at"),
            ]
        )

    def _count_enriched_records(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> int:
        """Count records with at least one enrichment.

        Counts records where at least one enricher-sourced column is non-null.
        Works with qualified column names ({provider}.{entity}.{field}).

        Args:
            df: Merged DataFrame with qualified columns.
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name (for identifying seed columns).

        Returns:
            Count of records with at least one non-null enricher column.
        """
        import polars as pl

        enricher_cols: list[str] = []

        for enricher in enrichers:
            try:
                provider, entity = self._parse_pipeline_name(enricher.pipeline)
                prefix = f"{provider}.{entity}."
            except ValueError:
                prefix = f"{enricher.pipeline}_"

            enricher_cols.extend([c for c in df.columns if c.startswith(prefix)])

        if not enricher_cols:
            return 0

        # Count records where at least one enricher column is non-null
        any_enriched = pl.any_horizontal(
            [pl.col(c).is_not_null() for c in enricher_cols]
        )
        return len(df.filter(any_enriched))

    def _count_fully_enriched(
        self, df: pl.DataFrame, enrichers: Sequence[EnricherConfig]
    ) -> int:
        """Count records with all required enrichments."""
        # Simplified implementation
        return 0

    def _calculate_field_coverage(self, df: pl.DataFrame) -> dict[str, float]:
        """Calculate percentage of non-null values per field."""
        if len(df) == 0:
            return {}

        coverage = {}
        for col in df.columns:
            if not col.startswith("_"):  # Skip metadata columns
                non_null = len(df.filter(df[col].is_not_null()))
                coverage[col] = non_null / len(df)

        return coverage

================================================================================
File: runner.py
Path: composite\runner.py
================================================================================
"""Composite Pipeline Runner.

Application Service that orchestrates composite pipeline execution.
Coordinates seed execution, parallel enrichment, and merge operations.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_helpers import (
    add_not_run_results,
    calculate_had_warnings,
    get_mergeable_enrichers,
    log_enrichment_summary,
)
from bioetl.domain.composite.result import (
    CompositeResult,
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.events import PipelineEvent
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.checkpoint import CompositeCheckpointManager
    from bioetl.application.composite.coordinator import EnrichmentCoordinator
    from bioetl.application.composite.key_extractor import KeyExtractorService
    from bioetl.application.composite.merger import MergeService
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.config import CompositeConfig, EnricherConfig
    from bioetl.domain.ports import LockPort, LoggerPort


@dataclass(frozen=True, slots=True)
class CompositeRuntimeConfig:
    """Runtime configuration for composite pipeline execution.

    Attributes:
        resume: Resume from checkpoint if available.
        dry_run: Extract and transform without writing.
        enrich_only: Run only specified enrichers (comma-separated).
        required_only: Skip optional enrichers.
        force_enricher: Force re-run of specified enricher.
        seed_limit: Optional limit for seed pipeline.
    """

    resume: bool = False
    dry_run: bool = False
    enrich_only: tuple[str, ...] | None = None
    required_only: bool = False
    force_enricher: str | None = None
    seed_limit: int | None = None

    def __post_init__(self) -> None:
        """Convert types for immutability."""
        if isinstance(self.enrich_only, list):
            object.__setattr__(self, "enrich_only", tuple(self.enrich_only))


class CompositePipelineRunner:
    """Orchestrates composite pipeline execution.

    Coordinates seed execution, parallel enrichment, and merge.
    Delegates to existing PipelineRunner for individual pipelines.

    This is an Application Service that:
    - Has no business logic (delegates to specialized services)
    - Coordinates cross-cutting concerns (locking, checkpointing)
    - Manages lifecycle of sub-pipelines

    Attributes:
        config: Composite pipeline configuration.
        runtime: Runtime options (resume, dry_run, etc.).

    Example:
        >>> runner = CompositePipelineRunner(
        ...     config=composite_config,
        ...     runtime=CompositeRuntimeConfig(resume=True),
        ...     seed_runner_factory=seed_factory,
        ...     enricher_runner_factory=enricher_factory,
        ...     key_extractor=key_extractor,
        ...     coordinator=coordinator,
        ...     merger=merger,
        ...     checkpoint_manager=checkpoint_manager,
        ...     logger=logger,
        ...     lock=lock,
        ... )
        >>> result = await runner.run()
    """

    def __init__(
        self,
        config: CompositeConfig,
        runtime: CompositeRuntimeConfig,
        seed_runner_factory: Callable[[], PipelineRunner],
        enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
        key_extractor: KeyExtractorService,
        coordinator: EnrichmentCoordinator,
        merger: MergeService,
        checkpoint_manager: CompositeCheckpointManager,
        logger: LoggerPort,
        lock: LockPort,
        run_id: str | None = None,
        dq_report_service: DQReportService | None = None,
    ) -> None:
        """Initialize composite pipeline runner.

        Args:
            config: Composite pipeline configuration.
            runtime: Runtime options.
            seed_runner_factory: Factory to create seed PipelineRunner.
            enricher_runner_factory: Factory to create enricher PipelineRunner.
                Takes pipeline name and keys DataFrame.
            key_extractor: Service to extract join keys from Silver.
            coordinator: Enrichment coordination service.
            merger: Data merge service.
            checkpoint_manager: Checkpoint manager for resume.
            logger: Structured logger.
            lock: Lock port for distributed locking.
            run_id: Optional run ID (generated if not provided).
            dq_report_service: Optional DQ report service for generating reports.
        """
        self._config = config
        self._runtime = runtime
        self._seed_runner_factory = seed_runner_factory
        self._enricher_runner_factory = enricher_runner_factory
        self._key_extractor = key_extractor
        self._coordinator = coordinator
        self._merger = merger
        self._checkpoint_manager = checkpoint_manager
        self._logger = logger
        self._lock = lock
        self._run_id_str = run_id or str(uuid4())
        self._run_id: RunID = cast(RunID, UUID(self._run_id_str))
        self._started_at: datetime | None = None
        self._finished: bool = False
        self._final_state: CompositePipelineState | None = None
        self._dq_report_service = dq_report_service

        # Initialize FSM helper for state transition logic
        from bioetl.application.composite.fsm_helper import FSMStateHelper

        self._fsm = FSMStateHelper(
            config=config,
            logger=logger,
            run_id=self._run_id_str,
        )

    @property
    def run_id(self) -> str:
        """Get the run ID as string."""
        return self._run_id_str

    @property
    def config(self) -> CompositeConfig:
        """Get the composite configuration."""
        return self._config

    async def run(self) -> CompositeResult:
        """Execute full composite pipeline.

        Execution flow:
        1. Acquire composite lock
        2. Load checkpoint (for resume)
        3. Run seed pipeline (if not completed)
        4. Extract join keys from seed Silver
        5. Run enrichers in parallel (fan-out)
        6. Merge results into Gold
        7. Delete checkpoint on success

        Returns:
            CompositeResult with all sub-pipeline results.

        Raises:
            CriticalError: If seed or required enricher fails.
            RunnerAlreadyExecutedError: If this Runner instance was already executed.
        """
        # Protection against double execution
        if self._finished:
            from bioetl.domain.exceptions import RunnerAlreadyExecutedError

            raise RunnerAlreadyExecutedError(
                runner_type="CompositePipelineRunner",
                run_id=self._run_id_str,
                final_state=self._final_state.value if self._final_state else None,
            )

        # Validate configuration consistency on startup
        self._validate_config_consistency()

        self._started_at = datetime.now(tz=UTC)
        self._logger.info(
            PipelineEvent.START,
            composite=self._config.name,
            run_id=self._run_id_str,
            stage="composite_start",
        )

        try:
            # Acquire composite lock
            lock_key = self._config.lock_key
            acquired = await self._lock.acquire(
                key=lock_key,
                owner_id=self._run_id,
                ttl=3600,  # 1 hour for composite
            )
            if not acquired:
                raise RuntimeError(
                    f"Could not acquire lock for composite: {self._config.name}"
                )

            try:
                result = await self._run_with_lock()
                # Mark as finished with success
                self._finished = True
                self._final_state = CompositePipelineState.COMPLETED
                return result
            finally:
                await self._lock.release(key=lock_key, owner_id=self._run_id)

        except Exception as e:
            # Mark as finished with failure
            self._finished = True
            self._final_state = CompositePipelineState.FAILED
            self._logger.error(
                PipelineEvent.FAILED,
                composite=self._config.name,
                run_id=self._run_id_str,
                error=str(e),
            )
            raise

    async def _run_with_lock(self) -> CompositeResult:
        """Execute composite pipeline with lock held."""
        # Load checkpoint (for resume)
        state = await self._checkpoint_manager.load()

        # Handle resume from FAILED state - determine correct phase to continue from
        if self._runtime.resume and state.state == CompositePipelineState.FAILED:
            state = self._fsm.handle_resume_from_failed(state)

        # Log resume context if resuming with progress
        if self._runtime.resume and state.is_resumable:
            self._fsm.log_resume_context(state)

        # Track results
        seed_result: SeedResult | None = None
        enrichment_results: dict[str, EnrichmentResult] = {}
        merge_result: MergeResult | None = None

        # Step 1: Run seed (if not completed)
        if not state.seed_completed:
            # Validate and transition to SEED_RUNNING before starting seed
            previous_state = state.state
            self._fsm.validate_fsm_transition(
                previous_state, CompositePipelineState.SEED_RUNNING
            )
            state = state.with_state(CompositePipelineState.SEED_RUNNING)
            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.SEED_RUNNING,
                stage="seed_start",
            )
            # Log phase event for seed start
            self._logger.info(
                PipelineEvent.phase_started("seed"),
                composite=self._config.name,
                run_id=self._run_id_str,
            )
            await self._save_checkpoint_safe(state, "seed_running")

            # Execute seed with error handling
            try:
                seed_result = await self._run_seed()
            except Exception as e:
                # Seed failed - transition to FAILED state
                self._logger.error(
                    "Seed pipeline failed",
                    composite=self._config.name,
                    run_id=self._run_id_str,
                    seed_pipeline=self._config.seed.pipeline,
                    error=str(e),
                )
                self._fsm.log_fsm_transition(
                    from_state=CompositePipelineState.SEED_RUNNING,
                    to_state=CompositePipelineState.FAILED,
                    stage="seed_failed",
                    error=str(e),
                )
                # Save FAILED state to checkpoint for resume awareness
                failed_state = state.with_state(CompositePipelineState.FAILED)
                await self._save_checkpoint_safe(failed_state, "seed_failed")
                # Re-raise to trigger outer error handling and lock release
                raise

            # Seed succeeded - transition to SEED_COMPLETED
            state = state.with_seed_completed(seed_result)
            self._fsm.log_fsm_transition(
                from_state=CompositePipelineState.SEED_RUNNING,
                to_state=CompositePipelineState.SEED_COMPLETED,
                stage="seed_complete",
                records_extracted=seed_result.records_extracted,
                records_silver=seed_result.records_silver,
            )
            # Log phase event for seed completion
            self._logger.info(
                PipelineEvent.phase_completed("seed"),
                composite=self._config.name,
                run_id=self._run_id_str,
                records_extracted=seed_result.records_extracted,
                records_silver=seed_result.records_silver,
            )
            await self._save_checkpoint_safe(state, "seed_completed")
        else:
            # Resume: seed already completed
            self._logger.info(
                "Seed already completed, resuming from checkpoint",
                composite=self._config.name,
                run_id=self._run_id_str,
            )
            # Ensure FSM state reflects SEED_COMPLETED when resuming
            if state.state != CompositePipelineState.SEED_COMPLETED:
                previous_state = state.state
                state = state.with_state(CompositePipelineState.SEED_COMPLETED)
                self._fsm.log_fsm_transition(
                    from_state=previous_state,
                    to_state=CompositePipelineState.SEED_COMPLETED,
                    stage="seed_resume",
                )
            seed_result = SeedResult(
                pipeline_name=self._config.seed.pipeline,
                resumed=True,
            )

        # Step 2: Extract keys from seed Silver
        keys_df = await self._key_extractor.extract(
            silver_table=self._config.seed.silver_table,
            keys=self._config.seed.output_keys,
        )

        self._logger.info(
            "Extracted keys for enrichment",
            composite=self._config.name,
            keys_count=len(keys_df),
        )

        # Step 3: Determine which enrichers to run
        enrichers_to_run = self._get_enrichers_to_run(state)

        # Step 4: Run enrichers (fan-out) with FSM state management
        if enrichers_to_run:
            # Validate and transition to ENRICHING state before starting enrichments
            enricher_names = [e.pipeline for e in enrichers_to_run]
            previous_state = state.state
            self._fsm.validate_fsm_transition(
                previous_state, CompositePipelineState.ENRICHING
            )
            state = state.with_state(CompositePipelineState.ENRICHING)
            await self._checkpoint_manager.save(state)

            # Log FSM transition to ENRICHING
            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.ENRICHING,
                stage="enrichment_start",
                enrichers=enricher_names,
                count=len(enrichers_to_run),
            )
            # Log phase event for enrichment start
            self._logger.info(
                PipelineEvent.phase_started("enrichment"),
                composite=self._config.name,
                run_id=self._run_id_str,
                enrichers=enricher_names,
                count=len(enrichers_to_run),
            )

            enrichment_results = await self._coordinator.run_enrichers(
                keys=keys_df,
                enrichers=enrichers_to_run,
                completed=state.completed_enrichers,
                runner_factory=self._enricher_runner_factory,
            )

            # Update checkpoint with completed enrichers
            for name, result in enrichment_results.items():
                if result.is_success or result.status == EnrichmentStatus.SKIPPED:
                    state = state.with_enricher_completed(name, result)
            await self._checkpoint_manager.save(state)

            # Log aggregated enrichment results
            log_enrichment_summary(enrichment_results, self._config.name, self._logger)
        else:
            # No enrichers to run - skip enrichment stage
            self._logger.info(
                "No enrichers to run, skipping enrichment stage",
                composite=self._config.name,
                reason="all_completed_or_filtered",
            )

        # Merge with previously completed enrichers
        enrichment_results.update(state.enrichment_results)

        # Step 4b: Add NOT_RUN results for optional enrichers skipped due to required_only
        enrichment_results = add_not_run_results(
            enrichment_results,
            enrichers_to_run,
            self._config.enrichers,
            state.completed_enrichers,
            self._runtime.required_only,
            self._config.name,
            self._logger,
        )

        # Step 5: Check required enrichers with FSM FAILED transition on error
        try:
            self._check_required_enrichers(enrichment_results)
        except RuntimeError as e:
            # Required enricher failed - transition to FAILED state
            previous_state = state.state
            state = state.with_state(CompositePipelineState.FAILED)

            # Log FSM transition to FAILED
            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.FAILED,
                stage="required_enricher_failed",
                error=str(e),
            )

            try:
                await self._checkpoint_manager.save(state)
            except Exception as save_error:
                self._logger.warning(
                    "Failed to save FAILED state to checkpoint",
                    composite=self._config.name,
                    run_id=self._run_id_str,
                    error=str(save_error),
                )

            self._logger.error(
                "Required enricher failed, pipeline transitioning to FAILED",
                composite=self._config.name,
                run_id=self._run_id_str,
                error=str(e),
            )
            raise

        # Step 5b: Transition to ENRICHMENT_COMPLETED
        state = await self._transition_to_enrichment_completed(state)

        # Step 6: Execute merge or skip in dry run mode
        state, merge_result = await self._execute_merge_stage(state, enrichment_results)

        # Step 7: Finalize - set COMPLETED and cleanup checkpoint
        await self._finalize_pipeline(state)

        completed_at = datetime.now(tz=UTC)
        started = self._started_at or completed_at  # Fallback if not set
        total_duration = (completed_at - started).total_seconds()

        # Calculate if we had warnings from optional enricher failures
        had_warnings = calculate_had_warnings(
            enrichment_results,
            frozenset(self._config.required_enrichers),
            self._config.name,
            self._logger,
        )

        # Log completion with appropriate status
        if had_warnings:
            self._logger.info(
                PipelineEvent.COMPLETE,
                composite=self._config.name,
                run_id=self._run_id_str,
                duration_seconds=total_duration,
                status="completed_with_warnings",
                had_warnings=True,
            )
        else:
            self._logger.info(
                PipelineEvent.COMPLETE,
                composite=self._config.name,
                run_id=self._run_id_str,
                duration_seconds=total_duration,
            )

        return CompositeResult(
            composite_name=self._config.name,
            composite_run_id=self._run_id_str,
            seed_result=seed_result,
            enrichment_results=enrichment_results,
            merge_result=merge_result,
            total_duration_seconds=total_duration,
            started_at=self._started_at,
            completed_at=completed_at,
            had_warnings=had_warnings,
            _required_enrichers=frozenset(self._config.required_enrichers),
        )

    async def _transition_to_enrichment_completed(
        self, state: CompositeCheckpointState
    ) -> CompositeCheckpointState:
        """Transition FSM state to ENRICHMENT_COMPLETED.

        Handles the case where no enrichers were run (state is still SEED_COMPLETED).
        Must go through ENRICHING first per FSM rules.
        """
        from bioetl.domain.composite.state import CompositePipelineState

        if state.state == CompositePipelineState.SEED_COMPLETED:
            # Must go through ENRICHING first per FSM rules (no enrichers case)
            previous_state = state.state
            self._fsm.validate_fsm_transition(
                previous_state, CompositePipelineState.ENRICHING
            )
            state = state.with_state(CompositePipelineState.ENRICHING)
            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.ENRICHING,
                stage="enrichment_start_empty",
                reason="no_enrichers_to_run",
            )

        if state.state == CompositePipelineState.ENRICHING:
            enriching_state: CompositePipelineState = state.state
            self._fsm.validate_fsm_transition(
                enriching_state, CompositePipelineState.ENRICHMENT_COMPLETED
            )
            state = state.with_state(CompositePipelineState.ENRICHMENT_COMPLETED)
            await self._save_checkpoint_safe(state, "enrichment_completed")

            # Log FSM transition to ENRICHMENT_COMPLETED
            self._fsm.log_fsm_transition(
                from_state=enriching_state,
                to_state=CompositePipelineState.ENRICHMENT_COMPLETED,
                stage="enrichment_complete",
            )
            # Log phase event for enrichment completion
            self._logger.info(
                PipelineEvent.phase_completed("enrichment"),
                composite=self._config.name,
                run_id=self._run_id_str,
            )
        return state

    async def _execute_merge_stage(
        self,
        state: CompositeCheckpointState,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> tuple[CompositeCheckpointState, MergeResult | None]:
        """Execute merge stage or skip in dry run mode.

        Returns updated state and merge result (None for dry run).
        """
        from bioetl.domain.composite.state import CompositePipelineState

        merge_result: MergeResult | None = None

        if not self._runtime.dry_run:
            # Validate and transition to MERGING state
            previous_state = state.state
            self._fsm.validate_fsm_transition(
                previous_state, CompositePipelineState.MERGING
            )
            state = state.with_state(CompositePipelineState.MERGING)
            await self._save_checkpoint_safe(state, "merging")

            # Log FSM transition to MERGING
            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.MERGING,
                stage="merge_start",
            )
            # Log phase event for merge start
            self._logger.info(
                PipelineEvent.phase_started("merge"),
                composite=self._config.name,
                run_id=self._run_id_str,
            )

            try:
                # Get only enrichers with data to merge (exclude SKIPPED/NOT_RUN)
                mergeable_enrichers = get_mergeable_enrichers(
                    enrichment_results, self._config.enrichers, self._logger
                )

                merge_result = await self._merger.merge(
                    seed_table=self._config.seed.silver_table,
                    enrichers=mergeable_enrichers,
                    enrichment_results=enrichment_results,
                    run_id=self._run_id_str,
                )

                # Log phase event for merge completion
                self._logger.info(
                    PipelineEvent.phase_completed("merge"),
                    composite=self._config.name,
                    run_id=self._run_id_str,
                    records_merged=merge_result.records_merged,
                )

                # Generate DQ reports if service is available
                await self._generate_dq_reports(merge_result)

            except Exception as merge_error:
                # Log FSM transition to FAILED
                self._fsm.log_fsm_transition(
                    from_state=CompositePipelineState.MERGING,
                    to_state=CompositePipelineState.FAILED,
                    stage="merge_failed",
                    error=str(merge_error),
                )
                self._logger.error(
                    "Merge failed",
                    composite=self._config.name,
                    run_id=self._run_id_str,
                    error=str(merge_error),
                )
                state = state.with_state(CompositePipelineState.FAILED)
                await self._save_checkpoint_safe(state, "merge_failed")
                raise
        else:
            # Dry run mode - skip merge, transition directly to COMPLETED
            self._fsm.log_fsm_transition(
                from_state=state.state,
                to_state=CompositePipelineState.COMPLETED,
                stage="dry_run_skip_merge",
                reason="dry_run_mode",
            )
            self._logger.info(
                "Dry run: merge skipped, pipeline completing",
                composite=self._config.name,
                run_id=self._run_id_str,
            )

        return state, merge_result

    async def _finalize_pipeline(self, state: CompositeCheckpointState) -> None:
        """Finalize pipeline - set COMPLETED state and cleanup checkpoint."""
        from bioetl.domain.composite.state import CompositePipelineState

        # Validate and transition to COMPLETED state (only if not already COMPLETED from dry run)
        if state.state != CompositePipelineState.COMPLETED:
            previous_state = state.state
            self._fsm.validate_fsm_transition(
                previous_state, CompositePipelineState.COMPLETED
            )
            state = state.with_state(CompositePipelineState.COMPLETED)

            # Log FSM transition to COMPLETED
            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.COMPLETED,
                stage="pipeline_complete",
            )
        await self._save_checkpoint_safe(state, "completed")

        # Cleanup checkpoint on success
        try:
            await self._checkpoint_manager.delete()
        except Exception as delete_error:
            # Checkpoint deletion failure is non-critical
            self._logger.warning(
                "Failed to delete checkpoint",
                composite=self._config.name,
                run_id=self._run_id_str,
                error=str(delete_error),
            )

    def _validate_config_consistency(self) -> None:
        """Validate configuration consistency and log warnings for anomalies.

        Checks for potential issues in CompositeConfig that might indicate
        misconfiguration:
        - required_enrichers property matches actual required flags
        - All enrichers are optional warning (valid but notable)

        This is a defensive check to catch configuration errors early.
        """
        # Check required_enrichers consistency
        expected_required = frozenset(
            e.pipeline for e in self._config.enrichers if e.required
        )
        actual_required = frozenset(self._config.required_enrichers)

        if expected_required != actual_required:
            self._logger.warning(
                "Config inconsistency: required_enrichers mismatch",
                composite=self._config.name,
                expected_required=list(expected_required),
                actual_required=list(actual_required),
                note="This may indicate a bug in CompositeConfig",
            )

        # Log info if all enrichers are optional
        if not expected_required and self._config.enrichers:
            self._logger.info(
                "All enrichers are optional",
                composite=self._config.name,
                enricher_count=len(self._config.enrichers),
                note="Pipeline will succeed even if all enrichers fail",
            )

    async def _save_checkpoint_safe(
        self,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:
        """Save checkpoint with graceful error handling.

        Checkpoint save failures should not stop pipeline execution, but
        resume capability will be affected.

        Args:
            state: Checkpoint state to save.
            operation: Description of the operation for logging.

        Returns:
            True if save succeeded, False otherwise.
        """
        try:
            await self._checkpoint_manager.save(state)
            return True
        except Exception as e:
            self._logger.warning(
                "checkpoint_save_failed",
                composite=self._config.name,
                run_id=self._run_id_str,
                operation=operation,
                error=str(e),
                note="Resume capability may be affected",
            )
            return False

    async def _run_seed(self) -> SeedResult:
        """Run the seed pipeline."""
        self._logger.info(
            "Running seed pipeline",
            composite=self._config.name,
            seed_pipeline=self._config.seed.pipeline,
        )

        started_at = datetime.now(tz=UTC)
        runner = self._seed_runner_factory()
        await runner.run()
        completed_at = datetime.now(tz=UTC)

        # Extract stats from runner (if available)
        records_extracted = getattr(runner, "_executor", None)
        records_silver = 0
        if records_extracted:
            records_silver = getattr(records_extracted, "records_silver", 0)

        return SeedResult(
            pipeline_name=self._config.seed.pipeline,
            records_extracted=records_extracted.records_fetched
            if records_extracted
            else 0,
            records_silver=records_silver,
            keys_generated=records_silver,  # Approximate
            duration_seconds=(completed_at - started_at).total_seconds(),
            started_at=started_at,
            completed_at=completed_at,
        )

    def _get_enrichers_to_run(
        self, state: CompositeCheckpointState
    ) -> list[EnricherConfig]:
        """Determine which enrichers should be run."""
        enrichers_to_run: list[EnricherConfig] = []

        for enricher in self._config.enrichers:
            # Skip if already completed (unless forced)
            if (
                enricher.pipeline in state.completed_enrichers
                and self._runtime.force_enricher != enricher.pipeline
            ):
                continue

            # Skip optional enrichers if required_only
            if self._runtime.required_only and not enricher.required:
                continue

            # Filter to specific enrichers if enrich_only
            if (
                self._runtime.enrich_only
                and enricher.pipeline not in self._runtime.enrich_only
            ):
                continue

            enrichers_to_run.append(enricher)

        return enrichers_to_run

    def _check_required_enrichers(
        self, enrichment_results: dict[str, EnrichmentResult]
    ) -> None:
        """Check that all required enrichers succeeded."""
        for enricher_name in self._config.required_enrichers:
            result = enrichment_results.get(enricher_name)
            if result is None:
                raise RuntimeError(f"Required enricher '{enricher_name}' did not run")
            if not result.is_success:
                raise RuntimeError(
                    f"Required enricher '{enricher_name}' failed: "
                    f"{result.error_message or result.status.value}"
                )

    async def _generate_dq_reports(self, merge_result: MergeResult) -> None:
        """Generate DQ reports for composite pipeline.

        Args:
            merge_result: Result of the merge operation.
        """
        if self._dq_report_service is None:
            self._logger.debug(
                "dq_reports_skipped",
                reason="DQReportService not configured",
                composite=self._config.name,
            )
            return

        try:
            from bioetl.application.services.dq_report_service import DQReportContext

            # Create DQ report context for composite
            context = DQReportContext(
                run_id=self._run_id_str,
                pipeline_name=f"composite_{self._config.name}",
                timestamp=datetime.now(tz=UTC),
                provider="composite",
                entity=self._config.name,
                # Silver context
                silver_target_table=self._config.merge.output_silver_path,
                silver_input_count=merge_result.records_from_seed,
                # Gold context
                gold_target_table=self._config.merge.output_gold_path,
                # DQ thresholds from config
                dq_soft_threshold=self._config.dq.soft_fail_threshold,
                dq_hard_threshold=self._config.dq.hard_fail_threshold,
            )

            # Generate reports (if analyzers are configured)
            await self._dq_report_service.generate_reports(context)

            self._logger.info(
                "dq_reports_generated",
                composite=self._config.name,
                run_id=self._run_id_str,
            )

        except Exception as e:
            # DQ report generation failure should not fail the pipeline
            self._logger.warning(
                "dq_reports_failed",
                composite=self._config.name,
                error=str(e),
            )

================================================================================
File: runner_helpers.py
Path: composite\runner_helpers.py
================================================================================
"""Helper functions for CompositePipelineRunner.

Pure functions extracted to reduce class size while maintaining cohesion.
These functions have no side effects and operate on data passed as arguments.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus

if TYPE_CHECKING:
    from collections.abc import Set

    from bioetl.domain.composite.config import EnricherConfig
    from bioetl.domain.ports import LoggerPort


def log_enrichment_summary(
    enrichment_results: dict[str, EnrichmentResult],
    composite_name: str,
    logger: LoggerPort,
) -> None:
    """Log aggregated summary of enrichment results.

    Args:
        enrichment_results: Results from enrichers.
        composite_name: Name of the composite pipeline.
        logger: Logger port for structured logging.
    """
    if not enrichment_results:
        return

    # Aggregate by status using counter
    status_counts: dict[EnrichmentStatus, int] = dict.fromkeys(EnrichmentStatus, 0)
    total_records_input = 0
    total_records_enriched = 0
    total_records_errored = 0

    failed_enrichers: list[str] = []
    successful_enrichers: list[str] = []
    not_run_enrichers: list[str] = []

    # Track which statuses map to which enricher lists
    success_statuses = {EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL}
    failure_statuses = {EnrichmentStatus.FAILED, EnrichmentStatus.TIMEOUT}

    for name, result in enrichment_results.items():
        total_records_input += result.records_input
        total_records_enriched += result.records_enriched
        total_records_errored += result.records_errored
        status_counts[result.status] += 1

        # Categorize enrichers
        if result.status in success_statuses:
            successful_enrichers.append(name)
        elif result.status in failure_statuses:
            failed_enrichers.append(name)
        elif result.status == EnrichmentStatus.NOT_RUN:
            not_run_enrichers.append(name)

    logger.info(
        "Enrichment summary",
        composite=composite_name,
        total_enrichers=len(enrichment_results),
        success=status_counts[EnrichmentStatus.SUCCESS],
        partial=status_counts[EnrichmentStatus.PARTIAL],
        failed=status_counts[EnrichmentStatus.FAILED],
        skipped=status_counts[EnrichmentStatus.SKIPPED],
        timeout=status_counts[EnrichmentStatus.TIMEOUT],
        not_run=status_counts[EnrichmentStatus.NOT_RUN],
        successful_enrichers=successful_enrichers,
        failed_enrichers=failed_enrichers if failed_enrichers else None,
        not_run_enrichers=not_run_enrichers if not_run_enrichers else None,
        total_records_input=total_records_input,
        total_records_enriched=total_records_enriched,
        total_records_errored=total_records_errored,
    )


def calculate_had_warnings(
    enrichment_results: dict[str, EnrichmentResult],
    required_enrichers: frozenset[str],
    composite_name: str,
    logger: LoggerPort,
) -> bool:
    """Calculate if the pipeline had warnings from optional enricher failures.

    A warning occurs when an optional (non-required) enricher fails but the
    pipeline can still complete successfully. This allows users to distinguish
    between clean completions and completions with issues.

    Args:
        enrichment_results: All enrichment results.
        required_enrichers: Set of required enricher names.
        composite_name: Name of the composite pipeline.
        logger: Logger port for structured logging.

    Returns:
        True if any optional enricher failed (status FAILED or TIMEOUT).
    """
    for name, result in enrichment_results.items():
        # Skip required enrichers - their failures would already have raised
        if name in required_enrichers:
            continue

        # Check for failure statuses (FAILED, TIMEOUT)
        if result.status in (EnrichmentStatus.FAILED, EnrichmentStatus.TIMEOUT):
            logger.warning(
                "Optional enricher failed",
                composite=composite_name,
                enricher=name,
                status=result.status.value,
                error_message=result.error_message,
            )
            return True

    return False


def add_not_run_results(
    enrichment_results: dict[str, EnrichmentResult],
    enrichers_to_run: list[EnricherConfig],
    all_enrichers: Iterable[EnricherConfig],
    completed_enrichers: Set[str],
    required_only: bool,
    composite_name: str,
    logger: LoggerPort,
) -> dict[str, EnrichmentResult]:
    """Add NOT_RUN results for optional enrichers skipped due to required_only mode.

    When required_only is True, optional enrichers are not executed. This function
    adds explicit NOT_RUN results for these enrichers so they appear in the
    final enrichment_results for complete lineage tracking.

    Args:
        enrichment_results: Current enrichment results from executed enrichers.
        enrichers_to_run: List of enrichers that were actually run.
        all_enrichers: All enrichers in the config.
        completed_enrichers: Set of previously completed enricher names.
        required_only: Whether required_only mode is active.
        composite_name: Name of the composite pipeline.
        logger: Logger port for structured logging.

    Returns:
        Updated enrichment_results with NOT_RUN entries for skipped optional enrichers.
    """
    if not required_only:
        return enrichment_results

    # Get set of enrichers that were actually run or previously completed
    run_names = {e.pipeline for e in enrichers_to_run}

    # Find optional enrichers that were skipped due to required_only
    for enricher in all_enrichers:
        # Only process optional enrichers
        if enricher.required:
            continue

        # Skip if this enricher was run or previously completed
        if enricher.pipeline in run_names:
            continue
        if enricher.pipeline in completed_enrichers:
            continue

        # Skip if already in results (shouldn't happen, but defensive)
        if enricher.pipeline in enrichment_results:
            continue

        # Add NOT_RUN result for this skipped optional enricher
        enrichment_results[enricher.pipeline] = EnrichmentResult.not_run(
            enricher_name=enricher.pipeline,
            reason="Skipped due to required_only mode",
        )

        logger.info(
            "Optional enricher not run",
            composite=composite_name,
            enricher=enricher.pipeline,
            reason="required_only_mode",
        )

    return enrichment_results


def get_mergeable_enrichers(
    enrichment_results: dict[str, EnrichmentResult],
    all_enrichers: Iterable[EnricherConfig],
    logger: LoggerPort,
) -> list[EnricherConfig]:
    """Get list of enrichers that should be included in merge.

    Excludes enrichers with NOT_RUN or SKIPPED status since they have no
    data to merge. This prevents file I/O errors when trying to read
    non-existent or empty Silver tables.

    Args:
        enrichment_results: All enrichment results.
        all_enrichers: All enricher configs.
        logger: Logger port for structured logging.

    Returns:
        List of EnricherConfig for enrichers that have data to merge.
    """
    # Statuses that indicate no data to merge
    non_mergeable_statuses = (
        EnrichmentStatus.SKIPPED,
        EnrichmentStatus.NOT_RUN,
    )

    mergeable: list[EnricherConfig] = []
    for enricher_cfg in all_enrichers:
        result = enrichment_results.get(enricher_cfg.pipeline)

        # If no result, don't include in merge
        if result is None:
            continue

        # If status indicates no data, don't include in merge
        if result.status in non_mergeable_statuses:
            logger.debug(
                "Excluding enricher from merge",
                enricher=enricher_cfg.pipeline,
                status=result.status.value,
                reason="no_data_to_merge",
            )
            continue

        mergeable.append(enricher_cfg)

    return mergeable

================================================================================
File: __init__.py
Path: core\__init__.py
================================================================================
"""Pipeline components and base classes.

NOTE: ADR-0005 introduces PipelineConfig, RuntimeConfig, PipelineServices
for decomposed pipeline configuration. Use BasePipeline.from_config() instead of
direct constructor.

Configuration consolidation (all in bioetl.domain.config):
- PipelineConfig: Static pipeline configuration
- RuntimeConfig: CLI/runtime parameters
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.application.core.batch_transformer import (
    BatchTransformer,
    StreamingBatchProcessor,
    TransformedRecord,
    TransformResult,
)
from bioetl.application.core.batch_writer import BatchWriter
from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.cleanup_service import (
    CleanupPreview,
    CleanupResult,
    CleanupService,
    LayerInfo,
)
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.memory_monitor import (
    MemoryConfig,
    MemoryMonitor,
    MemoryStats,
)
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.postrun_service import (
    DQEvaluationStatus,
    DQResult,
    PostrunResult,
    PostrunService,
    VacuumResult,
)
from bioetl.application.core.preflight_service import PreflightService
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.runner import PipelineRunner
from bioetl.application.core.shutdown import (
    PipelineShutdownError,
    ShutdownReason,
    ShutdownService,
    ShutdownSignal,
    create_shutdown_service,
)
from bioetl.application.core.transform_utils import (
    aggregate_nested_lists,
    extract_list_field,
    flatten_nested_dict,
    normalize_string,
    parse_date_field,
    safe_extract,
    validate_smiles,
)
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.application.services.medallion_types import (
    ClearResult,
    PrepareResult,
)
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.medallion import (
    Layer,
    WriteMode,
    WriteModePolicy,
)

__all__ = [
    "BasePipeline",
    "BaseTransformer",
    "BatchExecutor",
    "BatchTransformer",
    "BatchWriter",
    "CheckpointManager",
    "CleanupPreview",
    "CleanupResult",
    "CleanupService",
    "ClearResult",
    "DQEvaluationStatus",
    "DQResult",
    "Layer",
    "LayerInfo",
    "LockManager",
    "MedallionLifecycleService",
    "MemoryConfig",
    "MemoryMonitor",
    "MemoryStats",
    "PipelineConfig",
    "PipelineRunner",
    "PipelineServices",
    "PipelineShutdownError",
    "PostrunResult",
    "PostrunService",
    "PreflightService",
    "PrepareResult",
    "QuarantineManager",
    "RuntimeConfig",
    "ShutdownReason",
    "ShutdownService",
    "ShutdownSignal",
    "StreamingBatchProcessor",
    "TransformResult",
    "TransformedRecord",
    "VacuumResult",
    "WriteMode",
    "WriteModePolicy",
    "aggregate_nested_lists",
    "create_shutdown_service",
    "extract_list_field",
    "flatten_nested_dict",
    "normalize_string",
    "parse_date_field",
    "safe_extract",
    "validate_smiles",
]

================================================================================
File: base.py
Path: core\base.py
================================================================================
"""Base ETL Pipeline class.

Defines the structure and logic of a pipeline (config, transformations, filters).
Does NOT handle execution orchestration.

Refactored per ADR-0005.
Updated: Transformer injection via DI (Phase 1 refactoring).
Updated: Removed default_transformer_class fallback (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Self

from bioetl.application.core.shutdown import ShutdownSignal
from bioetl.domain.context import PipelineContext

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import BronzeRecord, RunID, RunType, SilverRecord


class BasePipeline(ABC):  # noqa: B024
    """Base class for ETL pipelines.

    Acts as a container for:
    - Configuration (Static & Runtime)
    - Services (Ports)
    - Business Logic (Transformations, Filtering)

    It does NOT orchestrate execution. See PipelineRunner for execution logic.

    Transformers MUST be injected via DI from GenericPipelineFactory.
    BasePipeline does NOT create transformers internally.
    """

    @classmethod
    def create(
        cls,
        run_id: RunID,
        runtime: RuntimeConfig,
        services: PipelineServices,
        config: PipelineConfig,
        transformer: BaseTransformer | None = None,
    ) -> Self:
        """Create pipeline instance.

        Default factory method. Subclasses can override if custom initialization is needed.

        Args:
            run_id: Unique identifier for this pipeline run (from CLI/orchestrator).
            runtime: Runtime configuration.
            services: Injected services (ports).
            config: Pipeline configuration.
            transformer: Injected transformer for Bronze→Silver transformation (DI).
                If provided, the pipeline will use this transformer instead of
                creating one internally. This is the preferred DI approach.

        """
        return cls(config, runtime, services, run_id, transformer=transformer)

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
        run_id: RunID,
        transformer: BaseTransformer | None = None,
    ) -> None:
        """Initialize pipeline definition.

        Args:
            config: Pipeline configuration.
            runtime: Runtime configuration.
            services: Injected services (ports).
            run_id: Unique identifier for this pipeline run.
                    MUST be passed from CLI/orchestrator to ensure consistency.
            transformer: Injected transformer for Bronze→Silver transformation.
                MUST be provided via DI from GenericPipelineFactory.
                If None, transform_bronze_to_silver() will raise NotImplementedError.

        """
        self._config = config
        self._runtime = runtime
        self._services = services
        self._run_id = run_id
        # Transformer MUST be injected via DI - no fallback creation
        self._transformer = transformer
        self._logger = services.logger.bind(
            run_id=str(self._run_id),
            pipeline=config.pipeline_name,
        )
        # Use factory method to ensure started_at is set (single source of time)
        self._context = PipelineContext.create(
            run_id=self._run_id,
            run_type=runtime.run_type,
            logger=self._logger,
        )
        self._shutdown_signal = ShutdownSignal()

    # --- Properties for accessing config (read-only) ---

    @property
    def config(self) -> PipelineConfig:
        """Access pipeline configuration."""
        return self._config

    @property
    def runtime(self) -> RuntimeConfig:
        """Access runtime configuration."""
        return self._runtime

    @property
    def services(self) -> PipelineServices:
        """Access injected services."""
        return self._services

    @property
    def run_id(self) -> RunID:
        """Access run ID."""
        return self._run_id

    @property
    def context(self) -> PipelineContext:
        """Access pipeline context."""
        return self._context

    @property
    def logger(self) -> LoggerPort:
        """Access bound logger."""
        return self._logger

    @property
    def shutdown_signal(self) -> ShutdownSignal:
        """Access shutdown signal."""
        return self._shutdown_signal

    # --- Convenience properties (delegate to config) ---

    @property
    def pipeline_name(self) -> str:
        """Pipeline name (from config)."""
        return self._config.pipeline_name

    @property
    def provider(self) -> str:
        """Provider name (from config)."""
        return self._config.provider

    @property
    def entity_type(self) -> str:
        """Entity type (from config)."""
        return self._config.entity_type

    @property
    def run_type(self) -> RunType:
        """Run type (from runtime)."""
        return self._runtime.run_type

    @property
    def resume(self) -> bool:
        """Resume flag (from runtime)."""
        return self._runtime.resume

    @property
    def limit(self) -> int | None:
        """Record limit (from runtime)."""
        return self._runtime.limit

    @property
    def transformer(self) -> BaseTransformer | None:
        """Access the injected transformer."""
        return self._transformer

    # --- Logic Methods (to be used by Executor) ---

    async def transform_bronze_to_silver(
        self, context: PipelineContext, record: BronzeRecord, index: int = 0
    ) -> SilverRecord | None:
        """Transform a raw record from Bronze to Silver format.

        If a transformer was injected via DI, delegates to it.
        Otherwise, subclasses MUST override this method.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from data source.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            NotImplementedError: If no transformer is available and method not overridden.

        """
        if self._transformer is not None:
            return await self._transformer.transform(context, record, index)
        raise NotImplementedError(
            f"{self.__class__.__name__} must either receive a transformer via DI "
            "or override transform_bronze_to_silver()"
        )

================================================================================
File: base_transformer.py
Path: core\base_transformer.py
================================================================================
"""Base Transformer class for Bronze → Silver transformations.

Provides common functionality for all entity transformers:
- Content hash generation (RULES.md §2.8.1)
- JSON serialization of complex fields
- Entity to SilverRecord conversion with lineage field renaming
- Template Method pattern for unified error handling
- Helper methods for field extraction and entity creation
- Tracing and metrics for observability (O1)

Implements DRY principle by extracting shared logic from entity transformers.
"""

from __future__ import annotations

import dataclasses
import time
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

import orjson

from bioetl.domain.ports import (
    DataNormalizationPort,
    MetricsPort,
    NoOpMetrics,
    NoOpPiiHasher,
    NoOpTracing,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.services import DataNormalizationService, IdentityService
from bioetl.domain.types import ContentHash, EntityID

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.types import BronzeRecord, SilverRecord

T = TypeVar("T", bound="BaseEntity")


class TransformationError(Exception):
    """Raised when a transformation fails due to missing/invalid data.

    This exception is caught by the Template Method and results in
    skipping the record (returning None) with appropriate logging.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        """Initialize transformation error.

        Args:
            message: Error description.
            field: Name of the field that caused the error (optional).

        """
        super().__init__(message)
        self.field = field


class BaseTransformer(ABC):
    """Abstract base class for Bronze → Silver transformers.

    Implements Template Method pattern for unified transformation flow:
    1. Call `_transform_impl()` (abstract hook method)
    2. Handle ValueError and TransformationError with logging
    3. Return None for skipped records

    Provides:
    - `compute_content_hash()`: Canonical content hash generation (RULES.md §2.8.1)
    - `serialize_json()`: JSON serialization for complex fields (dict/list)
    - `entity_to_silver_record()`: Entity → SilverRecord conversion with lineage fields
    - `_get_required_field()`: Extract and validate required fields
    - `_extract_nested()`: Safe extraction of nested dictionary values
    - `_create_entity()`: Unified entity creation with lineage metadata

    Observability (O1):
    - Tracing spans for transform operations
    - Duration histograms by entity_type
    - Error counters by error_type

    Subclasses MUST implement:
    - `_transform_impl()`: Entity-specific transformation logic
    """

    # Fields to exclude from Gold layer (JSON strings retained only in Silver)
    # UPDATED: Empty set to ensure identical columns in Silver and Gold (User Request)
    GOLD_EXCLUDE_FIELDS: ClassVar[frozenset[str]] = frozenset()

    def __init__(
        self,
        provider: str,
        entity_type: str | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ) -> None:
        """Initialize transformer with provider name and observability.

        Args:
            provider: Data provider identifier (e.g., 'chembl', 'pubchem').
            entity_type: Entity type for metrics labels (e.g., 'activity', 'compound').
            tracer: Tracing port for distributed tracing. Defaults to NoOpTracing.
            metrics: Metrics port for duration/error tracking. Defaults to NoOpMetrics.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
                Defaults to a new IdentityService instance.
            pii_hasher: Optional PII hasher for hashing author names and other PII.
                Defaults to NoOpPiiHasher (no hashing) for backward compatibility.
            data_normalizer: Data normalization service for text normalization
                (DOI, PMID, authors, HTML). Defaults to DataNormalizationService.

        """
        self.provider = provider
        self.entity_type = entity_type or "unknown"
        self._tracer: TracingPort = tracer if tracer is not None else NoOpTracing()
        self._metrics: MetricsPort = metrics if metrics is not None else NoOpMetrics()
        self._gold_filters = gold_filters
        self._identity: IdentityService = (
            identity_service if identity_service is not None else IdentityService()
        )
        self._pii_hasher: PiiHasherPort = (
            pii_hasher if pii_hasher is not None else NoOpPiiHasher()
        )
        self._data_normalizer: DataNormalizationPort = (
            data_normalizer
            if data_normalizer is not None
            else DataNormalizationService()
        )

    # ========================================================================
    # PII Hashing Methods (RULES.md §5.4)
    # ========================================================================

    def hash_pii_value(self, value: str | None) -> str | None:
        """Hash a single PII value (e.g., author name).

        Delegates to PiiHasherPort. Uses NoOpPiiHasher by default
        (no hashing) for backward compatibility.

        Args:
            value: PII value to hash, or None.

        Returns:
            Hashed value, or None if input is None.
        """
        return self._pii_hasher.hash_value(value)

    def hash_pii_list(self, values: list[str] | None) -> list[str] | None:
        """Hash a list of PII values (e.g., list of author names).

        Delegates to PiiHasherPort. Uses NoOpPiiHasher by default
        (no hashing) for backward compatibility.

        Args:
            values: List of PII values to hash, or None.

        Returns:
            List of hashed values, or None if input is None.
        """
        return self._pii_hasher.hash_list(values)

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform Bronze record to Silver format (Template Method).

        This is the main entry point implementing Template Method pattern.
        Handles common error handling and logging, delegating actual
        transformation to `_transform_impl()`.

        Observability (O1):
        - Creates tracing span "transform_record" with provider/entity attributes
        - Records transform_duration_seconds histogram by entity_type
        - Increments transform_errors_total counter by error_type on failure

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from data source.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if record should be skipped.

        """
        start_time = time.perf_counter()
        error_type: str | None = None

        # Start tracing span (always available via NoOpTracing default)
        otel_tracer = self._tracer.get_tracer("bioetl.transformer")
        span = otel_tracer.start_as_current_span(
            "transform_record",
            attributes={
                "bioetl.provider": self.provider,
                "bioetl.entity_type": self.entity_type,
                "bioetl.run_id": str(context.run_id),
                "bioetl.record_index": index,
            },
        )
        span.__enter__()

        try:
            result = await self._transform_impl(context, record, index)
            return result
        except TransformationError as e:
            error_type = "transformation_error"
            context.logger.warning(
                "transformation_skipped",
                reason=str(e),
                field=e.field,
                provider=self.provider,
            )
            span.set_attribute("error", True)
            span.set_attribute("error.type", error_type)
            return None
        except ValueError as e:
            error_type = "validation_error"
            context.logger.warning(
                "entity_validation_failed",
                error=str(e),
                provider=self.provider,
            )
            span.set_attribute("error", True)
            span.set_attribute("error.type", error_type)
            return None
        finally:
            duration = time.perf_counter() - start_time

            # Record duration histogram (always available via NoOpMetrics default)
            self._metrics.observe_histogram(
                "transform_duration_seconds",
                duration,
                labels={
                    "provider": self.provider,
                    "entity_type": self.entity_type,
                },
            )

            # Record error counter if error occurred
            if error_type:
                self._metrics.increment_counter(
                    "transform_errors_total",
                    1,
                    labels={
                        "provider": self.provider,
                        "entity_type": self.entity_type,
                        "error_type": error_type,
                    },
                )

            # End tracing span
            span.set_attribute("bioetl.duration_ms", duration * 1000)
            span.__exit__(None, None, None)

    @abstractmethod
    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Implement entity-specific transformation logic.

        Subclasses MUST implement this method to perform actual transformation:
        1. Extract and validate required fields using `_get_required_field()`
        2. Build business_data dictionary
        3. Generate entity_id and content_hash
        4. Create Domain Entity using `_create_entity()`
        5. Convert to SilverRecord using `entity_to_silver_record()`

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from data source.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if record should be skipped.

        Raises:
            TransformationError: If required field is missing.
            ValueError: If entity validation fails.

        """
        ...

    def should_write_gold(
        self, _context: PipelineContext, record: dict[str, Any]
    ) -> bool:
        """Determine if a Silver record should be written to Gold.

        Uses gold_filters from config if configured, otherwise passes all records.
        Subclasses can override for custom filtering logic.

        Args:
            _context: Pipeline context (unused in base implementation).
            record: Silver record to evaluate.

        Returns:
            True if record should be written to Gold layer.

        """
        if self._gold_filters is None or self._gold_filters.is_empty():
            return True
        return self._gold_filters.should_include(record)

    def transform_for_gold(
        self, _context: PipelineContext, silver_record: dict[str, Any]
    ) -> dict[str, Any]:
        """Transform Silver record for Gold layer.

        Removes JSON string fields that are retained only in Silver for forensic purposes.
        Subclasses can override for custom Gold transformations.

        Args:
            _context: Pipeline context (unused in base implementation).
            silver_record: Silver record to transform.

        Returns:
            Record suitable for Gold layer (flat fields only).

        """
        return {
            k: v for k, v in silver_record.items() if k not in self.GOLD_EXCLUDE_FIELDS
        }

    def compute_content_hash(
        self,
        business_data: dict[str, Any],
        *,
        exclude_none: bool = True,
    ) -> ContentHash:
        """Generate canonical content hash for record versioning.

        Delegates to IdentityService for computation.

        Implements RULES.md §2.8.1:
        - sha256(provider + canonical_json(record))
        - Normalizes NaN/Inf → null, floats → round(val, 10), dates → ISO

        Args:
            business_data: Business data dictionary (excluding meta fields).
            exclude_none: Whether to exclude None values from hash calculation.

        Returns:
            ContentHash: SHA256 hash of normalized record.

        """
        return self._identity.compute_content_hash(
            self.provider,
            business_data,
            exclude_none=exclude_none,
        )

    def compute_entity_id(
        self,
        source_id: str | None,
        record: dict[str, Any],
    ) -> EntityID:
        """Generate stable entity identifier.

        Delegates to IdentityService for computation.

        If source_id is provided, uses it for stable identification.
        Otherwise, generates identifier from content hash prefix.

        Args:
            source_id: Source system identifier (e.g., activity_id from API).
            record: Record for fallback hash-based identification.

        Returns:
            EntityID in format "{provider}:{id}" or "{provider}:{hash_prefix}".

        """
        return self._identity.compute_entity_id(
            provider=self.provider,
            entity_type=self.entity_type,
            source_id=source_id,
            record=record,
        )

    @staticmethod
    def serialize_json(value: Any) -> str | int | float | bool | None:
        """Serialize dict/list to JSON string or native type for Silver layer.

        Empty collections → None; single-element lists → unwrapped native type;
        multi-element lists/dicts → JSON string (orjson with OPT_SORT_KEYS).
        """
        if value is None:
            return None

        if isinstance(value, dict):
            return BaseTransformer._serialize_dict(value)

        if isinstance(value, list):
            return BaseTransformer._serialize_list(value)

        # Non-collection types (str, int, float, bool): return as-is
        return value

    @staticmethod
    def _serialize_dict(d: dict[str, Any]) -> str | None:
        if not d:
            return None
        return orjson.dumps(d, option=orjson.OPT_SORT_KEYS).decode("utf-8")

    @staticmethod
    def _serialize_list(lst: list[Any]) -> str | int | float | bool | None:
        if not lst:
            return None
        if len(lst) == 1:
            item = lst[0]
            if isinstance(item, (dict, list)):
                return (
                    None
                    if not item
                    else orjson.dumps(item, option=orjson.OPT_SORT_KEYS).decode("utf-8")
                )
            return item
        return orjson.dumps(lst, option=orjson.OPT_SORT_KEYS).decode("utf-8")

    @staticmethod
    def serialize_json_list(value: list[Any] | None) -> str | None:
        """Serialize list to JSON string without unwrapping single elements.

        Unlike serialize_json(), this method always preserves the array format,
        even for single-element lists. Used for fields like 'authors' where
        the JSON array structure must be maintained.

        Args:
            value: List to serialize, or None.

        Returns:
            JSON array string, or None if input is None or empty list.

        Example:
            >>> serialize_json_list(["John Doe"])
            '["John Doe"]'
            >>> serialize_json_list(["John Doe", "Jane Smith"])
            '["John Doe","Jane Smith"]'
            >>> serialize_json_list([])
            None

        """
        if value is None or len(value) == 0:
            return None
        json_bytes: bytes = orjson.dumps(value, option=orjson.OPT_SORT_KEYS)
        return json_bytes.decode("utf-8")

    @classmethod
    def serialize_json_fields(
        cls,
        record: dict[str, Any],
        field_names: Sequence[str],
    ) -> dict[str, str | int | float | bool | None]:
        """Serialize multiple JSON fields at once.

        Convenience method to reduce repetitive serialize_json() calls
        in transformers with many nested JSON fields.

        Args:
            record: Source record dictionary.
            field_names: Names of fields to serialize.

        Returns:
            Dictionary with serialized values (JSON strings, native types, or None).

        Example:
            >>> result = self.serialize_json_fields(record, [
            ...     "molecule_hierarchy",
            ...     "molecule_properties",
            ...     "cross_references",
            ... ])
            # Returns: {"molecule_hierarchy": "{...}", "molecule_properties": "{...}", ...}
        """
        return {name: cls.serialize_json(record.get(name)) for name in field_names}

    @staticmethod
    def entity_to_silver_record(entity: Any) -> dict[str, Any]:
        """Convert Domain Entity to SilverRecord format.

        Handles lineage fields renaming and formatting:
        - run_id → _run_id (str)
        - run_type → _run_type (str value)
        - source_batch_id → _source_batch_id (str)
        - ingestion_ts → _ingestion_ts (ISO string)

        Args:
            entity: Domain entity (dataclass).

        Returns:
            SilverRecord dictionary with renamed lineage fields.

        """
        # Use dataclasses.asdict to ensure fields from slots (BaseEntity) are included
        silver_record = dataclasses.asdict(entity)

        # Handle lineage fields renaming and formatting
        if "run_id" in silver_record:
            silver_record["_run_id"] = str(silver_record.pop("run_id"))

        if "run_type" in silver_record:
            silver_record["_run_type"] = str(silver_record.pop("run_type").value)

        # Handle source_batch_id which might be None
        if "source_batch_id" in silver_record:
            source_batch_id = silver_record.pop("source_batch_id")
            silver_record["_source_batch_id"] = (
                str(source_batch_id) if source_batch_id else None
            )

        if "ingestion_ts" in silver_record:
            silver_record["_ingestion_ts"] = silver_record.pop(
                "ingestion_ts"
            ).isoformat()

        return silver_record

    # ==================== Helper Methods ====================

    @staticmethod
    def _get_required_field(
        record: BronzeRecord,
        field: str,
        *,
        allow_empty: bool = False,
    ) -> Any:
        """Extract and validate a required field from the record.

        Args:
            record: Bronze record dictionary.
            field: Name of the required field.
            allow_empty: If False, empty strings and empty collections raise error.

        Returns:
            Field value if present and valid.

        Raises:
            TransformationError: If field is missing or empty (when allow_empty=False).

        """
        value = record.get(field)
        if value is None:
            raise TransformationError(f"Missing required field: {field}", field=field)

        if not allow_empty:
            # Check for empty strings, lists, dicts
            if isinstance(value, str) and not value.strip():
                raise TransformationError(
                    f"Required field is empty: {field}", field=field
                )
            if isinstance(value, (list, dict)) and len(value) == 0:
                raise TransformationError(
                    f"Required field is empty: {field}", field=field
                )

        return value

    @staticmethod
    def _extract_by_path(
        record: BronzeRecord,
        keys: Sequence[str],
        default: Any = None,
    ) -> Any:
        """Safely extract a value from nested dictionaries using a sequence of keys.

        Optimized version of _extract_nested that avoids string splitting.
        Useful when paths are constant and can be pre-defined.

        Args:
            record: Bronze record dictionary.
            keys: Sequence of keys to traverse.
            default: Value to return if path is not found.

        Returns:
            Extracted value or default.

        """
        current = record
        for key in keys:
            if not isinstance(current, dict):
                return default
            current = current.get(key)
            if current is None:
                return default
        return current

    @staticmethod
    def _extract_nested(
        record: BronzeRecord,
        path: str,
        default: Any = None,
    ) -> Any:
        """Safely extract a value from nested dictionaries using dot notation.

        Supports paths like "organism.taxonId" or "proteinDescription.recommendedName.fullName.value".

        Args:
            record: Bronze record dictionary.
            path: Dot-separated path to the nested value (e.g., "a.b.c").
            default: Value to return if path is not found.

        Returns:
            Extracted value or default if path doesn't exist or any intermediate is None.

        Example:
            >>> record = {"organism": {"taxonId": 9606}}
            >>> BaseTransformer._extract_nested(record, "organism.taxonId")
            9606
            >>> BaseTransformer._extract_nested(record, "organism.name", "unknown")
            'unknown'

        """
        keys = path.split(".")
        return BaseTransformer._extract_by_path(record, keys, default)

    def _create_entity(
        self,
        entity_class: type[T],
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        **business_data: Any,
    ) -> T:
        """Create a domain entity with lineage metadata.

        Unified entity creation that automatically adds lineage fields
        from the pipeline context.

        Args:
            entity_class: The domain entity class to instantiate.
            context: Pipeline context with run_id, run_type.
            entity_id: Unique entity identifier.
            content_hash: Content hash for versioning.
            index: Sequential index of the record in the pipeline run.
            **business_data: Entity-specific business data.

        Returns:
            Instantiated domain entity.

        Raises:
            ValueError: If entity validation fails.

        Example:
            >>> entity = self._create_entity(
            ...     Activity,
            ...     context,
            ...     entity_id="chembl:activity:12345",
            ...     content_hash="abc123...",
            ...     index=0,
            ...     activity_id="12345",
            ...     molecule_chembl_id="CHEMBL25",
            ... )

        """
        return entity_class(
            entity_id=EntityID(entity_id),
            content_hash=ContentHash(content_hash),
            run_id=context.run_id,
            run_type=context.run_type,
            source_batch_id=None,
            ingestion_ts=context.started_at,
            _index=index,
            **business_data,
        )

================================================================================
File: batch_executor.py
Path: core\batch_executor.py
================================================================================
"""Unified Batch Executor for ETL pipeline orchestration.

Combines extraction, transformation, and writing into a single component with
adaptive batch sizing, checkpointing, and graceful shutdown handling.

DQ Report Integration:
- Accumulates data for DQ report generation when DQ report service is available
- Provides get_dq_context() method for building DQ report context
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.batch_tracing import BatchTracingManager
from bioetl.application.core.batch_transformer import BatchTransformer, TransformResult
from bioetl.application.core.batch_writer import BatchWriter
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.types import BatchID

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.memory_monitor import MemoryConfig
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.application.services.dq_report_service import DQReportContext
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import (
        GoldValidatorPort,
        LoggerPort,
        MemoryMonitorPort,
        TracingPort,
    )


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Result of processing a batch of records."""

    bronze_count: int
    silver_count: int
    gold_count: int
    quarantined_count: int


class BatchExecutor:
    """Unified executor for ETL batches: fetch → transform → write with tracing."""

    DEFAULT_BATCH_SIZE = 100
    DEFAULT_CHECKPOINT_INTERVAL = 1000

    def __init__(
        self,
        services: PipelineServices,
        context: PipelineContext,
        config: RecordProcessorConfig,
        error_classifier: ErrorClassifier,
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        gold_transform_callback: GoldTransformCallback,
        gold_validator: GoldValidatorPort,
        checkpoint_manager: CheckpointManager,
        shutdown_signal: ShutdownSignal,
        *,
        batch_size: int | None = None,
        checkpoint_interval: int | None = None,
        tracer: TracingPort | None = None,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
        memory_monitor: MemoryMonitorPort | None = None,
        memory_config: MemoryConfig | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize batch executor.

        Args:
            services: Common pipeline services (data source, storage, metrics, etc.).
            context: Pipeline execution context (run_id, run_type, started_at).
            config: Record processor configuration.
            error_classifier: Service for error classification.
            transform_callback: Callback for Bronze → Silver transformation.
            gold_filter_callback: Callback for filtering Silver records for Gold.
            gold_transform_callback: Callback for Silver → Gold transformation.
            gold_validator: Validator for Gold layer records.
            checkpoint_manager: Checkpoint manager instance.
            shutdown_signal: Signal to handle graceful shutdown.
            batch_size: Number of records per batch.
            checkpoint_interval: Number of records between checkpoints.
            tracer: Optional tracing port for distributed tracing.
            lock_validator: Async callable that validates lock ownership (Safety Guard §4.6).
            memory_monitor: Optional memory monitor for adaptive batch sizing.
            memory_config: Memory configuration (used if memory_monitor not provided).
            logger: Logger for memory-related messages.

        """
        self._services = services
        self._context = context
        self._config = config
        self._checkpoint_manager = checkpoint_manager
        self._shutdown_signal = shutdown_signal
        self._logger = logger or services.logger

        # Batch configuration
        self._initial_batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        self.batch_size = self._initial_batch_size
        self.checkpoint_interval = (
            checkpoint_interval or self.DEFAULT_CHECKPOINT_INTERVAL
        )

        # Memory management
        self._memory_monitor = memory_monitor
        self._memory_config = memory_config
        self._adaptive_batch_size_enabled = memory_monitor is not None or (
            memory_config is not None and memory_config.enable_adaptive_sizing
        )
        self._batch_size_reductions = 0
        self._min_batch_size_used = self._initial_batch_size

        # Counters
        self.records_fetched = 0
        self.records_bronze = 0
        self.records_silver = 0
        self.records_gold = 0
        self.records_quarantined = 0

        # DQ Report data accumulation (only if DQ report service is available)
        # Collecting data adds memory overhead, so only enabled when needed
        self._bronze_records_for_dq: list[bytes] = []
        self._silver_records_for_dq: list[dict[str, Any]] = []
        self._gold_records_for_dq: list[dict[str, Any]] = []
        self._source_batch_ids: list[str] = []
        self._last_bronze_path: str | None = None

        # Create internal components (from RecordProcessor)
        pipeline_label = f"{config.provider}_{config.entity_type}"
        self._batch_metrics = BatchMetricsRecorder(
            services.metrics, pipeline_label, context.run_type.value
        )

        self._transformer = BatchTransformer(
            context=context,
            config=config,
            error_classifier=error_classifier,
            quarantine_manager=QuarantineManager(
                quarantine_port=services.quarantine,
                pipeline_name=config.pipeline_name,
            ),
            batch_metrics=self._batch_metrics,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        self._writer = BatchWriter(
            storage=services.storage,
            context=context,
            config=config,
            gold_validator=gold_validator,
            error_classifier=error_classifier,
            batch_metrics=self._batch_metrics,
            tracer=tracer,
            lock_validator=lock_validator,
        )

        # Tracing manager (extracted for class size reduction)
        self._tracing = BatchTracingManager(
            tracer=tracer,
            context=context,
            config=config,
            initial_batch_size=self._initial_batch_size,
            adaptive_sizing_enabled=self._adaptive_batch_size_enabled,
        )

        # Query string for metadata (stored during execute())
        self._query_string: str | None = None

    @property
    def entity_type(self) -> str:
        """Get entity type being processed."""
        return self._config.entity_type

    async def execute(
        self,
        limit: int | None,
        query: str | None = None,
    ) -> None:
        """Execute the pipeline with memory-efficient adaptive batch sizing.

        Orchestrates the complete data flow: fetch → transform → write for
        all records from the data source. Handles graceful shutdown and
        checkpointing.

        Args:
            limit: Maximum number of records to process. None means no limit.
            query: Optional query string for data source filtering.

        Raises:
            PipelineShutdownError: If shutdown signal received during execution.
            Exception: Any exception from data source or processing.

        Note:
            After execution, counters are updated:
            - records_fetched: Total records retrieved from source
            - records_bronze: Records written to Bronze layer
            - records_silver: Records written to Silver layer
            - records_gold: Records written to Gold layer
            - records_quarantined: Records sent to quarantine

        """
        # Store query string for metadata enrichment
        self._query_string = query

        root_span = self._tracing.start_execution_span()

        try:
            await self._run_extraction_loop(limit, query)
            self._tracing.set_execution_stats(
                root_span,
                total_fetched=self.records_fetched,
                total_bronze=self.records_bronze,
                total_silver=self.records_silver,
                total_gold=self.records_gold,
                total_quarantined=self.records_quarantined,
                batch_size_reductions=self._batch_size_reductions,
                min_batch_size_used=self._min_batch_size_used,
            )
        except PipelineShutdownError:
            await self._handle_shutdown(root_span)
            raise
        except Exception as e:
            self._tracing.end_span(root_span, e)
            raise
        else:
            self._tracing.end_span(root_span)

    async def _run_extraction_loop(self, limit: int | None, query: str | None) -> None:
        """Run the main extraction and processing loop.

        Args:
            limit: Maximum number of records to process.
            query: Optional query string for data source.

        """
        batch: list[dict[str, Any]] = []
        current_batch_size = self.batch_size
        check_interval = self._get_memory_check_interval()

        async for raw_record in self._extract(limit, query):
            if self._shutdown_signal.is_requested:
                await self._checkpoint_manager.save_checkpoint(self.records_fetched)
                raise PipelineShutdownError("Shutdown during extraction")

            batch.append(raw_record)
            self.records_fetched += 1

            current_batch_size = self._check_memory_pressure(
                current_batch_size, check_interval
            )

            if len(batch) >= current_batch_size:
                start_index = self.records_fetched - len(batch)
                await self._process_batch(batch, start_index)
                batch = []
                current_batch_size = self._maybe_recover_batch_size(current_batch_size)

            if self.records_fetched % self.checkpoint_interval == 0:
                await self._checkpoint_manager.save_checkpoint(self.records_fetched)

        if batch:
            start_index = self.records_fetched - len(batch)
            await self._process_batch(batch, start_index)

    async def process(
        self, records: list[dict[str, Any]], start_index: int = 0
    ) -> BatchResult:
        """Process a batch of records through the full ETL pipeline.

        Public API for processing individual batches. Delegates to internal
        processing with full tracing and observability.

        This method is the public entry point for batch processing, enabling:
        - Direct batch processing from external callers
        - Integration testing of the processing logic
        - Custom orchestration scenarios

        Args:
            records: Raw records to process through Bronze → Silver → Gold.
            start_index: Starting index for records in this batch. Default 0.

        Returns:
            BatchResult with counts for each layer.

        Example:
            >>> executor = BatchExecutor(...)
            >>> result = await executor.process(records, start_index=0)
            >>> logger.info("batch_processed", silver_count=result.silver_count)

        """
        await self._process_batch(records, start_index)
        return BatchResult(
            bronze_count=self.records_bronze,
            silver_count=self.records_silver,
            gold_count=self.records_gold,
            quarantined_count=self.records_quarantined,
        )

    def _get_source_metadata(self) -> SourceMetadata | None:
        """Get source metadata from data source if available.

        Checks if the data source has a `get_source_metadata()` method
        and calls it to retrieve accumulated API request metadata for
        Bronze layer enrichment.

        Also injects the query_string from execute() if not already set
        in the source metadata.

        Returns:
            SourceMetadata with API request details and query_string,
            or None if not available.

        """
        # Import SourceMetadata for runtime type check and creation
        from bioetl.domain.models.metadata import SourceMetadata

        source_metadata: SourceMetadata | None = None

        # Try to get metadata from data source
        data_source = self._services.data_source
        get_metadata = getattr(data_source, "get_source_metadata", None)
        if get_metadata is not None and callable(get_metadata):
            try:
                result = get_metadata()
                if isinstance(result, SourceMetadata):
                    source_metadata = result
            except Exception:
                # Gracefully handle any errors in metadata collection
                pass

        # Inject query_string if we have one and it's not already set
        if self._query_string:
            if source_metadata is not None:
                if source_metadata.query_string is None:
                    source_metadata = source_metadata.model_copy(
                        update={"query_string": self._query_string}
                    )
            else:
                # Create minimal SourceMetadata with query_string
                source_metadata = SourceMetadata(
                    type="api",
                    query_string=self._query_string,
                )

        return source_metadata

    async def _process_batch(
        self, records: list[dict[str, Any]], start_index: int
    ) -> None:
        """Process batch through Bronze → Silver → Gold with tracing.

        Args:
            records: Raw records to process.
            start_index: Starting index for records in this batch.
        """
        batch_id = BatchID(uuid4())
        ingestion_ts = self._context.started_at

        # Get source metadata from data source (if available)
        source_metadata = self._get_source_metadata()

        # Start batch tracing span
        span = self._tracing.start_batch_span(batch_id, len(records), start_index)

        try:
            # Write to Bronze and capture result for lineage tracking (REQ-LINEAGE-001)
            bronze_result = await self._execute_with_span(
                "write_bronze",
                self._writer.write_bronze(
                    records, batch_id, ingestion_ts, source_metadata=source_metadata
                ),
                batch_id,
                len(records),
                on_error=lambda e: self._writer.log_and_track_write_error(
                    "bronze", e, batch_id
                ),
            )
            self._batch_metrics.track_batch_size("bronze", len(records))
            self._batch_metrics.track_processed_records("bronze", len(records))

            # Transform records
            result = await self._execute_transform_with_span(
                records, batch_id, start_index
            )
            self._batch_metrics.track_processed_records(
                "quarantined", result.quarantined_count
            )
            self._batch_metrics.track_processed_records(
                "silver", len(result.silver_records)
            )
            self._batch_metrics.track_processed_records(
                "gold", len(result.gold_records)
            )

            # Write to Silver with bronze_refs for lineage tracking (REQ-LINEAGE-001)
            bronze_refs = [bronze_result] if bronze_result else None
            silver_result = None
            if result.silver_records:
                silver_result = await self._execute_with_span(
                    "write_silver",
                    self._writer.write_silver(
                        result.silver_records,
                        batch_id,
                        ingestion_ts,
                        bronze_refs=bronze_refs,
                    ),
                    batch_id,
                    len(result.silver_records),
                    on_error=lambda e: self._writer.log_and_track_write_error(
                        "silver", e, batch_id
                    ),
                )

            # Write to Gold with silver_refs for lineage tracking (REQ-LINEAGE-002)
            silver_refs = [silver_result] if silver_result else None
            if result.gold_records:
                await self._execute_with_span(
                    "write_gold",
                    self._writer.write_gold(
                        result.gold_records, silver_refs=silver_refs
                    ),
                    batch_id,
                    len(result.gold_records),
                    on_error=lambda e: self._writer.log_and_track_write_error(
                        "gold", e, batch_id
                    ),
                )

            # Update counters
            self.records_bronze += len(records)
            self.records_silver += len(result.silver_records)
            self.records_gold += len(result.gold_records)
            self.records_quarantined += result.quarantined_count

            # Collect data for DQ reports (if enabled)
            if self._should_collect_dq_data():
                self._collect_dq_data(
                    records=records,
                    batch_id=batch_id,
                    bronze_result=bronze_result,
                    silver_records=result.silver_records,
                    gold_records=result.gold_records,
                )

            # Add result attributes to span
            self._tracing.set_batch_result(
                span,
                bronze_count=len(records),
                silver_count=len(result.silver_records),
                gold_count=len(result.gold_records),
                quarantined_count=result.quarantined_count,
            )

        except Exception as e:
            self._tracing.end_span(span, e)
            raise
        else:
            self._tracing.end_span(span)

    async def _execute_with_span(
        self,
        name: str,
        coro: Any,
        batch_id: BatchID,
        count: int,
        on_error: Any = None,
    ) -> Any:
        """Execute coroutine with tracing span."""
        span = self._tracing.start_layer_span(name, batch_id, count)
        try:
            result = await coro
            self._tracing.end_span(span)
            return result
        except Exception as e:
            self._tracing.end_span(span, e)
            if on_error:
                on_error(e)
            raise

    async def _execute_transform_with_span(
        self, records: list[dict[str, Any]], batch_id: BatchID, start_index: int
    ) -> TransformResult:
        """Execute transformation with extended span attributes."""
        span = self._tracing.start_layer_span(
            "transform", batch_id, len(records), input_count=True
        )
        try:
            result = await self._transformer.transform_batch(
                records, batch_id, start_index=start_index
            )
            self._tracing.set_transform_result(
                span,
                silver_count=len(result.silver_records),
                gold_count=len(result.gold_records),
                quarantined_count=result.quarantined_count,
            )
            self._tracing.end_span(span)
            return result
        except Exception as e:
            self._tracing.end_span(span, e)
            raise

    async def _handle_shutdown(self, span: Any | None) -> None:
        """Handle graceful shutdown with checkpoint save."""
        try:
            await self._checkpoint_manager.save_checkpoint(self.records_fetched)
        except Exception:
            pass  # Ignore errors during emergency checkpoint save

        self._tracing.end_span_with_shutdown(span)

    # -------------------------------------------------------------------------
    # Memory management helpers (from PipelineExecutor)
    # -------------------------------------------------------------------------

    def _get_memory_check_interval(self) -> int:
        """Get interval for memory pressure checks."""
        if self._memory_config:
            return self._memory_config.check_interval_records
        return 100  # Default check every 100 records

    def _check_memory_pressure(self, current_size: int, check_interval: int) -> int:
        """Check memory pressure and adjust batch size if needed."""
        if not self._adaptive_batch_size_enabled:
            return current_size
        if self.records_fetched % check_interval != 0:
            return current_size
        return self._adjust_batch_size(current_size)

    def _maybe_recover_batch_size(self, current_size: int) -> int:
        """Try to recover batch size after processing if adaptive sizing enabled."""
        if not self._adaptive_batch_size_enabled:
            return current_size
        return self._try_recover_batch_size(current_size)

    def _adjust_batch_size(self, current_size: int) -> int:
        """Adjust batch size based on memory pressure."""
        if self._memory_monitor:
            new_size = self._memory_monitor.get_recommended_batch_size(current_size)
        elif self._memory_config:
            new_size = self._estimate_batch_size_from_config(current_size)
        else:
            return current_size

        if new_size < current_size:
            self._batch_size_reductions += 1
            self._min_batch_size_used = min(self._min_batch_size_used, new_size)
            self._logger.info(
                "Reduced batch size due to memory pressure",
                old_size=current_size,
                new_size=new_size,
                total_reductions=self._batch_size_reductions,
            )

        return new_size

    def _estimate_batch_size_from_config(self, current_size: int) -> int:
        """Estimate batch size without memory monitoring."""
        if not self._memory_config:
            return current_size

        records_per_mb = 1000
        max_records = self._memory_config.max_batch_memory_mb * records_per_mb

        if current_size > max_records:
            return max(max_records, self._memory_config.min_batch_size)

        return current_size

    def _try_recover_batch_size(self, current_size: int) -> int:
        """Try to recover batch size after pressure is relieved."""
        if self._memory_monitor:
            return self._memory_monitor.get_recommended_batch_size(current_size)

        if current_size < self._initial_batch_size:
            recovery_size = min(
                int(current_size * 1.1),
                self._initial_batch_size,
            )
            return recovery_size

        return current_size

    # -------------------------------------------------------------------------
    # Data extraction
    # -------------------------------------------------------------------------

    async def _extract(
        self, limit: int | None, query: str | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Extract records from data source.

        Args:
            limit: Maximum number of records to extract. None means no limit.
            query: Optional query string for server-side filtering.

        Yields:
            Raw records as dictionaries from the data source.

        """
        async for record in self._services.data_source.fetch(
            entity_type=self._config.entity_type,
            limit=limit,
            query=query,
        ):
            yield record

    # -------------------------------------------------------------------------
    # DQ Report data collection
    # -------------------------------------------------------------------------

    def _should_collect_dq_data(self) -> bool:
        """Check if DQ report service is available.

        Returns:
            True if DQ report service is configured and data should be collected.
        """
        return self._services.dq_report_service is not None

    def _collect_dq_data(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
        bronze_result: Any,
        silver_records: list[dict[str, Any]],
        gold_records: list[dict[str, Any]],
    ) -> None:
        """Collect data from batch processing for DQ reports.

        Args:
            records: Raw Bronze records.
            batch_id: Batch identifier.
            bronze_result: Result from Bronze write operation (contains path).
            silver_records: Transformed Silver records.
            gold_records: Transformed Gold records.
        """
        # Collect Bronze records as bytes (JSON-encoded)
        for record in records:
            try:
                self._bronze_records_for_dq.append(
                    json.dumps(record, default=str).encode("utf-8")
                )
            except (TypeError, ValueError):
                # Skip records that can't be serialized
                pass

        # Track batch ID
        self._source_batch_ids.append(str(batch_id))

        # Track Bronze file path if available
        if bronze_result is not None and hasattr(bronze_result, "path"):
            self._last_bronze_path = str(bronze_result.path)

        # Collect Silver records
        self._silver_records_for_dq.extend(silver_records)

        # Collect Gold records
        self._gold_records_for_dq.extend(gold_records)

    def _build_dataframe_from_records(
        self, records: list[dict[str, Any]]
    ) -> Any | None:
        """Build a Polars DataFrame from records, returning None on failure."""
        if not records:
            return None
        try:
            import polars as pl

            return pl.DataFrame(records)
        except Exception:
            return None

    def _get_dq_thresholds(self) -> tuple[float, float]:
        """Get DQ thresholds from config or defaults."""
        if self._config.dq_config:
            return (
                self._config.dq_config.soft_fail_threshold,
                self._config.dq_config.hard_fail_threshold,
            )
        return (0.05, 0.20)

    def _extract_dq_entity(self) -> str:
        """Extract entity name from silver_table for DQ report naming.

        Ensures consistency with actual table names (e.g., "publication" not "document").

        Returns:
            Entity name extracted from silver_table or fallback to entity_type.
        """
        silver_table = self._config.table_config.silver_table
        if silver_table and "_" in silver_table:
            return silver_table.split("_", 1)[1]
        if silver_table and "." in silver_table:
            return silver_table.split(".")[-1]
        return silver_table or self._config.entity_type

    def get_dq_context(self) -> DQReportContext | None:
        """Build DQ report context from accumulated data.

        Creates a DQReportContext containing all data collected during
        batch processing. This context is used by PostrunService to
        generate DQ reports for Bronze, Silver, and Gold layers.

        Returns:
            DQReportContext if DQ reporting is enabled and data is available,
            None otherwise.

        Note:
            This method should be called after execute() completes.
            The returned context contains snapshots of the accumulated data.
        """
        if not self._should_collect_dq_data():
            return None

        # Import here to avoid circular dependency
        from bioetl.application.services.dq_report_service import DQReportContext

        silver_data = self._build_dataframe_from_records(self._silver_records_for_dq)
        gold_data = self._build_dataframe_from_records(self._gold_records_for_dq)
        primary_keys = list(self._config.table_config.primary_keys)
        soft_threshold, hard_threshold = self._get_dq_thresholds()

        # Get current date for Bronze DQ report filename
        current_date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        dq_entity = self._extract_dq_entity()

        return DQReportContext(
            run_id=str(self._context.run_id),
            pipeline_name=self._config.pipeline_name,
            timestamp=datetime.now(UTC),
            # Provider and entity for DQ report naming
            # Use extracted entity from silver_table for consistency
            provider=self._config.provider,
            entity=dq_entity,
            # Bronze context
            bronze_records=self._bronze_records_for_dq or None,
            bronze_batch_id=self._source_batch_ids[-1]
            if self._source_batch_ids
            else None,
            bronze_source_file=self._last_bronze_path,
            bronze_output_path=self._config.bronze_output_path,
            bronze_date_str=current_date_str,
            # Silver context
            silver_data=silver_data,
            silver_target_table=self._config.table_config.silver_table,
            silver_source_batch_ids=self._source_batch_ids or None,
            silver_primary_keys=primary_keys or None,
            silver_input_count=self.records_fetched,
            silver_quarantined_count=self.records_quarantined,
            silver_output_path=self._config.silver_output_path,
            # Gold context
            gold_data=gold_data,
            gold_target_table=self._config.table_config.gold_table,
            gold_output_path=self._config.gold_output_path,
            # DQ thresholds from config (use defaults if not configured)
            dq_soft_threshold=soft_threshold,
            dq_hard_threshold=hard_threshold,
            # Flat structure flag for DQ reports
            flat_structure=self._config.flat_structure,
        )

================================================================================
File: batch_metrics.py
Path: core\batch_metrics.py
================================================================================
"""Batch metrics recording helper.

Encapsulates the logic for recording metrics during batch processing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort
    from bioetl.domain.types import ErrorType


class BatchMetricsRecorder:
    """Helper to record metrics for a batch processing cycle.

    Encapsulates all metrics recording logic for batch ETL operations,
    providing a consistent interface for tracking:
    - Batch sizes at each processing stage
    - Record counts per stage
    - Error occurrences by type
    - Quarantined record counts

    All methods are safe to call with metrics=None (no-op).

    Attributes:
        _metrics: Metrics port instance (may be None).
        _pipeline_label: Label identifying the pipeline.
        _run_type_label: Label for the run type.

    """

    def __init__(
        self,
        metrics: MetricsPort | None,
        pipeline_label: str,
        run_type_label: str,
    ) -> None:
        """Initialize batch metrics recorder.

        Args:
            metrics: Metrics port instance.
            pipeline_label: Label identifying the pipeline (e.g., 'chembl_activity').
            run_type_label: Label for the run type (e.g., 'incremental', 'rebuild').

        """
        self._metrics = metrics
        self._pipeline_label = pipeline_label
        self._run_type_label = run_type_label

    def track_batch_size(self, stage: str, size: int) -> None:
        """Record the size of a batch at a specific stage.

        Records a histogram observation for batch_size_records metric.

        Args:
            stage: Processing stage name (e.g., 'bronze', 'silver', 'gold').
            size: Number of records in the batch.

        """
        if self._metrics:
            self._metrics.observe_histogram(
                "batch_size_records",
                size,
                {"pipeline": self._pipeline_label, "stage": stage},
            )

    def track_processed_records(self, stage: str, count: int) -> None:
        """Record number of processed records at a specific stage.

        Increments the records_processed_total counter with pipeline,
        stage, and run_type labels.

        Args:
            stage: Processing stage name (e.g., 'bronze', 'silver', 'gold', 'quarantined').
            count: Number of records processed.

        """
        if self._metrics:
            self._metrics.increment_counter(
                "records_processed_total",
                count,
                {
                    "pipeline": self._pipeline_label,
                    "stage": stage,
                    "run_type": self._run_type_label,
                },
            )

    def track_error(self, stage: str, error_type: ErrorType) -> None:
        """Record an error occurrence at a specific stage.

        Increments the errors_total counter with pipeline, stage,
        and error_code labels.

        Args:
            stage: Processing stage where error occurred (e.g., 'transform', 'write').
            error_type: Classification of the error.

        """
        if self._metrics:
            self._metrics.increment_counter(
                "errors_total",
                1,
                {
                    "pipeline": self._pipeline_label,
                    "stage": stage,
                    "error_code": error_type.value,
                },
            )

    def track_quarantined_records(self, error_type: ErrorType, count: int) -> None:
        """Record number of quarantined records.

        Args:
            error_type: Type of error that caused quarantine
            count: Number of records quarantined

        """
        if self._metrics:
            self._metrics.increment_counter(
                "dq_records_quarantined_total",
                count,
                {
                    "pipeline": self._pipeline_label,
                    "error_type": error_type.value,
                    "run_type": self._run_type_label,
                },
            )

================================================================================
File: batch_tracing.py
Path: core\batch_tracing.py
================================================================================
"""Batch Tracing Manager for ETL pipeline observability.

Extracted from BatchExecutor to reduce class size and improve separation of concerns.
Handles all OpenTelemetry span management for batch processing operations.

Responsibilities:
- Create and manage root execution spans
- Create per-batch spans with proper nesting
- Create per-layer spans (transform, write_bronze, write_silver, write_gold)
- Record span attributes and exceptions
- Handle span lifecycle (enter/exit/error)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.ports import NoOpTracing

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import TracingPort
    from bioetl.domain.types import BatchID


class BatchTracingManager:
    """Manages tracing spans for batch ETL operations.

    Provides methods to create, configure, and close OpenTelemetry spans
    for pipeline execution, batch processing, and layer operations.

    All methods are safe to call with NoOpTracing - they return None spans
    that are safely ignored throughout the codebase.
    """

    TRACER_NAME = "bioetl.batch_executor"

    def __init__(
        self,
        tracer: TracingPort | None,
        context: PipelineContext,
        config: RecordProcessorConfig,
        initial_batch_size: int,
        adaptive_sizing_enabled: bool,
    ) -> None:
        """Initialize batch tracing manager.

        Args:
            tracer: OpenTelemetry tracer port. If None, uses NoOpTracing.
            context: Pipeline execution context.
            config: Record processor configuration.
            initial_batch_size: Initial batch size for tracking.
            adaptive_sizing_enabled: Whether adaptive batch sizing is enabled.

        """
        self._tracer: TracingPort = tracer if tracer is not None else NoOpTracing()
        self._context = context
        self._config = config
        self._initial_batch_size = initial_batch_size
        self._adaptive_sizing_enabled = adaptive_sizing_enabled

    def start_execution_span(self) -> Any | None:
        """Start root tracing span for pipeline execution.

        Returns:
            OpenTelemetry span context or None if tracing disabled.

        """
        otel_tracer = self._tracer.get_tracer(self.TRACER_NAME)
        span = otel_tracer.start_as_current_span(
            "pipeline_execution",
            attributes={
                "bioetl.pipeline": self._config.pipeline_name or "unknown",
                "bioetl.run_id": str(self._context.run_id),
                "bioetl.entity_type": self._config.entity_type,
                "bioetl.run_type": self._context.run_type.value,
                "bioetl.adaptive_batch_sizing": self._adaptive_sizing_enabled,
                "bioetl.initial_batch_size": self._initial_batch_size,
            },
        )
        span.__enter__()
        return span

    def start_batch_span(
        self, batch_id: BatchID, record_count: int, start_index: int
    ) -> Any | None:
        """Start tracing span for a batch.

        Args:
            batch_id: Unique identifier for the batch.
            record_count: Number of records in the batch.
            start_index: Starting index of records in this batch.

        Returns:
            OpenTelemetry span context or None if tracing disabled.

        """
        otel_tracer = self._tracer.get_tracer(self.TRACER_NAME)
        span = otel_tracer.start_as_current_span(
            f"batch_{batch_id}",
            attributes={
                "bioetl.batch_id": str(batch_id),
                "bioetl.record_count": record_count,
                "bioetl.run_type": self._context.run_type.value,
                "bioetl.entity_type": self._config.entity_type,
                "bioetl.start_index": start_index,
            },
        )
        span.__enter__()
        return span

    def start_layer_span(
        self,
        name: str,
        batch_id: BatchID,
        count: int,
        input_count: bool = False,
    ) -> Any:
        """Start a tracing span for a layer operation.

        Args:
            name: Name of the layer operation (e.g., "write_bronze", "transform").
            batch_id: Unique identifier for the batch.
            count: Number of records for this operation.
            input_count: If True, use "input_count" attribute; else "record_count".

        Returns:
            OpenTelemetry span context.

        """
        count_key = "bioetl.input_count" if input_count else "bioetl.record_count"
        attrs = {"bioetl.batch_id": str(batch_id), count_key: count}
        span = self._tracer.get_tracer(self.TRACER_NAME).start_as_current_span(
            name, attributes=attrs
        )
        span.__enter__()
        return span

    def set_execution_stats(
        self,
        span: Any | None,
        *,
        total_fetched: int,
        total_bronze: int,
        total_silver: int,
        total_gold: int,
        total_quarantined: int,
        batch_size_reductions: int,
        min_batch_size_used: int,
    ) -> None:
        """Set final statistics on the execution span.

        Args:
            span: The execution span to update.
            total_fetched: Total records fetched from source.
            total_bronze: Total records written to Bronze.
            total_silver: Total records written to Silver.
            total_gold: Total records written to Gold.
            total_quarantined: Total records quarantined.
            batch_size_reductions: Number of batch size reductions.
            min_batch_size_used: Minimum batch size used during execution.

        """
        if not span:
            return

        span.set_attribute("bioetl.total_fetched", total_fetched)
        span.set_attribute("bioetl.total_bronze", total_bronze)
        span.set_attribute("bioetl.total_silver", total_silver)
        span.set_attribute("bioetl.total_gold", total_gold)
        span.set_attribute("bioetl.total_quarantined", total_quarantined)
        span.set_attribute("bioetl.batch_size_reductions", batch_size_reductions)
        span.set_attribute("bioetl.min_batch_size_used", min_batch_size_used)

    def set_batch_result(
        self,
        span: Any | None,
        *,
        bronze_count: int,
        silver_count: int,
        gold_count: int,
        quarantined_count: int,
    ) -> None:
        """Set batch result attributes on span.

        Args:
            span: The batch span to update.
            bronze_count: Records written to Bronze.
            silver_count: Records written to Silver.
            gold_count: Records written to Gold.
            quarantined_count: Records quarantined.

        """
        if not span:
            return

        span.set_attribute("bioetl.bronze_count", bronze_count)
        span.set_attribute("bioetl.silver_count", silver_count)
        span.set_attribute("bioetl.gold_count", gold_count)
        span.set_attribute("bioetl.quarantined_count", quarantined_count)

    def set_transform_result(
        self,
        span: Any | None,
        *,
        silver_count: int,
        gold_count: int,
        quarantined_count: int,
    ) -> None:
        """Set transform result attributes on span.

        Args:
            span: The transform span to update.
            silver_count: Records transformed to Silver.
            gold_count: Records transformed to Gold.
            quarantined_count: Records quarantined during transform.

        """
        if not span:
            return

        span.set_attribute("bioetl.silver_count", silver_count)
        span.set_attribute("bioetl.gold_count", gold_count)
        span.set_attribute("bioetl.quarantined_count", quarantined_count)

    def end_span(self, span: Any | None, error: Exception | None = None) -> None:
        """End a tracing span.

        Args:
            span: The span to end.
            error: Optional exception to record on the span.

        """
        if not span:
            return
        if error:
            span.set_attribute("error", True)
            span.record_exception(error)
        span.__exit__(None, None, None)

    def end_span_with_shutdown(self, span: Any | None) -> None:
        """End span marking it as shutdown.

        Args:
            span: The span to end with shutdown marker.

        """
        if span:
            span.set_attribute("bioetl.shutdown", True)
            span.__exit__(None, None, None)


__all__ = ["BatchTracingManager"]

================================================================================
File: batch_transformer.py
Path: core\batch_transformer.py
================================================================================
"""Batch transformation from Bronze to Silver/Gold.

Handles record transformation, error handling, and quarantine management.
Extracted from RecordProcessor for single responsibility (SRP).

Supports two processing modes:
1. Standard batch processing (transform_batch) - processes all records in memory
2. Streaming processing (transform_stream) - generator-based for memory efficiency
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.domain.exceptions import DataQualityThresholdError

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.memory_monitor import MemoryMonitor
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.types import BatchID


@dataclass(frozen=True, slots=True)
class TransformResult:
    """Result of batch transformation."""

    silver_records: list[dict[str, Any]]
    gold_records: list[dict[str, Any]]
    quarantined_count: int


@dataclass(frozen=True, slots=True)
class TransformedRecord:
    """Single transformed record with routing info.

    Used in streaming mode to yield individual records.

    Attributes:
        silver_record: The transformed Silver record (None if quarantined).
        gold_record: The Gold record (None if filtered out or quarantined).
        is_quarantined: Whether this record was quarantined due to DQ error.

    """

    silver_record: dict[str, Any] | None
    gold_record: dict[str, Any] | None
    is_quarantined: bool


class BatchTransformer:
    """Transforms Bronze records to Silver/Gold with error handling.

    Handles:
    - Bronze → Silver transformation via callback
    - Silver → Gold filtering and transformation
    - Error classification and quarantine
    - DQ threshold checking
    """

    def __init__(
        self,
        context: PipelineContext,
        config: RecordProcessorConfig,
        error_classifier: ErrorClassifier,
        quarantine_manager: QuarantineManager,
        batch_metrics: BatchMetricsRecorder,
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        gold_transform_callback: GoldTransformCallback,
    ) -> None:
        """Initialize batch transformer.

        Args:
            context: Pipeline execution context.
            config: Record processor configuration.
            error_classifier: Service for error classification.
            quarantine_manager: Manager for quarantining failed records.
            batch_metrics: Metrics recorder for batch processing.
            transform_callback: Callback for Bronze -> Silver transformation.
            gold_filter_callback: Callback for filtering Silver records.
            gold_transform_callback: Callback for Silver -> Gold transformation.

        """
        self._context = context
        self._config = config
        self._error_classifier = error_classifier
        self._quarantine_manager = quarantine_manager
        self._batch_metrics = batch_metrics
        self._transform = transform_callback
        self._gold_filter = gold_filter_callback
        self._gold_transform = gold_transform_callback

    async def transform_batch(
        self, records: list[dict[str, Any]], batch_id: BatchID, start_index: int = 0
    ) -> TransformResult:
        """Transform all records in batch, returning silver, gold, and quarantine count.

        Args:
            records: Raw Bronze records to transform.
            batch_id: Identifier for the current batch.
            start_index: The starting index for records in this batch.

        Returns:
            TransformResult with silver records, gold records, and quarantine count.

        Raises:
            DataQualityThresholdError: If DQ hard threshold exceeded.

        """
        silver_records: list[dict[str, Any]] = []
        gold_records: list[dict[str, Any]] = []
        records_quarantined = 0

        for index, raw_record in enumerate(records, start=start_index):
            record_context = self._context.bind_logger(
                batch_id=str(batch_id),
                entity_id=raw_record.get("activity_id"),
            )
            try:
                # Pass index to transform callback
                transformed = await self._transform(record_context, raw_record, index)
                if transformed:
                    silver_records.append(transformed)
                    if self._gold_filter(record_context, transformed):
                        gold_record = self._gold_transform(record_context, transformed)
                        gold_records.append(gold_record)
            except Exception as e:
                error_type = self._error_classifier.classify(e)
                if error_type.is_data_quality():
                    await self._quarantine_manager.quarantine_record(
                        raw_record,
                        error_type,
                        batch_id,
                        str(e),
                        ingestion_ts=self._context.started_at,
                    )
                    records_quarantined += 1
                    self._batch_metrics.track_error("transform", error_type)
                    self._batch_metrics.track_quarantined_records(error_type, 1)
                else:
                    raise

        # Check DQ thresholds after transformation
        self._check_dq_thresholds(records, records_quarantined)

        return TransformResult(
            silver_records=silver_records,
            gold_records=gold_records,
            quarantined_count=records_quarantined,
        )

    def _check_dq_thresholds(
        self, records: list[dict[str, Any]], quarantined_count: int
    ) -> None:
        """Check DQ thresholds and raise/warn as appropriate.

        Args:
            records: Original records in the batch.
            quarantined_count: Number of quarantined records.

        Raises:
            DataQualityThresholdError: If hard threshold exceeded.

        """
        if not records:
            return

        total_count = len(records)
        error_rate = quarantined_count / total_count if total_count > 0 else 0.0
        dq_config = self._config.dq_config

        if not dq_config:
            return

        # Hard fail check
        if (
            dq_config.hard_fail_threshold
            and error_rate >= dq_config.hard_fail_threshold
        ):
            raise DataQualityThresholdError(error_rate, dq_config.hard_fail_threshold)

        # Soft fail check with detailed logging
        if (
            dq_config.soft_fail_threshold
            and error_rate >= dq_config.soft_fail_threshold
        ):
            self._context.logger.warning(
                "DQ Soft Threshold exceeded",
                error_rate=round(error_rate, 4),
                threshold=dq_config.soft_fail_threshold,
                quarantined_count=quarantined_count,
                total_count=total_count,
                hard_threshold=dq_config.hard_fail_threshold,
                pipeline=self._config.pipeline_name,
            )

    async def transform_single(
        self, raw_record: dict[str, Any], batch_id: BatchID, index: int = 0
    ) -> TransformedRecord:
        """Transform a single record (for streaming mode).

        This method processes one record at a time, enabling memory-efficient
        streaming processing of large datasets.

        Args:
            raw_record: Single Bronze record to transform.
            batch_id: Identifier for the current batch.
            index: Sequential index of the record in the pipeline run.

        Returns:
            TransformedRecord with silver/gold records or quarantine status.

        """
        record_context = self._context.bind_logger(
            batch_id=str(batch_id),
            entity_id=raw_record.get("activity_id"),
        )

        try:
            transformed = await self._transform(record_context, raw_record, index)
            if transformed:
                gold_record = None
                if self._gold_filter(record_context, transformed):
                    gold_record = self._gold_transform(record_context, transformed)

                return TransformedRecord(
                    silver_record=transformed,
                    gold_record=gold_record,
                    is_quarantined=False,
                )
            # Transform returned None (filtered out at source)
            return TransformedRecord(
                silver_record=None,
                gold_record=None,
                is_quarantined=False,
            )

        except Exception as e:
            error_type = self._error_classifier.classify(e)
            if error_type.is_data_quality():
                await self._quarantine_manager.quarantine_record(
                    raw_record,
                    error_type,
                    batch_id,
                    str(e),
                    ingestion_ts=self._context.started_at,
                )
                self._batch_metrics.track_error("transform", error_type)
                self._batch_metrics.track_quarantined_records(error_type, 1)

                return TransformedRecord(
                    silver_record=None,
                    gold_record=None,
                    is_quarantined=True,
                )
            raise

    async def transform_stream(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
        start_index: int = 0,
    ) -> TransformResult:
        """Transform records using streaming mode with memory efficiency.

        This method processes records one-at-a-time but accumulates results
        for batch writing. Use this for moderate memory savings while
        maintaining batch write semantics.

        For full streaming (no accumulation), use iter_transform_stream.

        Args:
            records: Raw Bronze records to transform.
            batch_id: Identifier for the current batch.
            start_index: Starting index for the batch.

        Returns:
            TransformResult with silver records, gold records, and quarantine count.

        Raises:
            DataQualityThresholdError: If DQ hard threshold exceeded.

        """
        silver_records: list[dict[str, Any]] = []
        gold_records: list[dict[str, Any]] = []
        records_quarantined = 0

        for i, raw_record in enumerate(records):
            result = await self.transform_single(raw_record, batch_id, start_index + i)

            if result.is_quarantined:
                records_quarantined += 1
            elif result.silver_record is not None:
                silver_records.append(result.silver_record)
                if result.gold_record is not None:
                    gold_records.append(result.gold_record)

        # Check DQ thresholds after transformation
        self._check_dq_thresholds(records, records_quarantined)

        return TransformResult(
            silver_records=silver_records,
            gold_records=gold_records,
            quarantined_count=records_quarantined,
        )


class StreamingBatchProcessor:
    """Memory-efficient streaming processor for large batches.

    This class provides generator-based iteration over records,
    enabling processing of datasets that don't fit in memory.

    Usage:
        >>> processor = StreamingBatchProcessor(transformer, memory_monitor)
        >>> async for sub_batch in processor.process_in_chunks(records, batch_id, chunk_size=100):
        ...     await writer.write_silver(sub_batch.silver_records, batch_id, ts)
        ...     await writer.write_gold(sub_batch.gold_records)

    """

    def __init__(
        self,
        transformer: BatchTransformer,
        memory_monitor: MemoryMonitor | None = None,
    ) -> None:
        """Initialize streaming processor.

        Args:
            transformer: The batch transformer to use.
            memory_monitor: Optional memory monitor for adaptive sizing.

        """
        self._transformer = transformer
        self._memory_monitor = memory_monitor

    async def process_in_chunks(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
        chunk_size: int = 100,
        start_index: int = 0,
    ) -> AsyncIterator[TransformResult]:
        """Process records in memory-efficient sub-batches.

        Yields TransformResult for each sub-batch, allowing incremental
        writes and garbage collection between sub-batches.

        Args:
            records: All records to process.
            batch_id: Batch identifier.
            chunk_size: Initial sub-batch size (may be reduced under memory pressure).
            start_index: Starting index for the entire batch.

        Yields:
            TransformResult for each processed sub-batch.

        """
        current_chunk_size = chunk_size
        i = 0
        total_records = len(records)

        while i < total_records:
            # Adjust sub-batch size based on memory pressure
            if self._memory_monitor:
                current_chunk_size = self._memory_monitor.get_recommended_batch_size(
                    current_chunk_size
                )

            chunk = records[i : i + current_chunk_size]
            result = await self._transformer.transform_stream(
                chunk, batch_id, start_index + i
            )

            yield result

            # Advance by actual sub-batch size processed
            i += len(chunk)

    def iter_records(self, records: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
        """Iterate over records without loading all into memory.

        This is a simple generator wrapper that can be extended
        to read from streaming sources.

        Args:
            records: List of records (could be lazy-loaded).

        Yields:
            Individual records one at a time.

        """
        yield from records

================================================================================
File: batch_writer.py
Path: core\batch_writer.py
================================================================================
"""Batch writing to Bronze, Silver, and Gold layers.

Handles all storage operations with proper metadata enrichment.
Extracted from RecordProcessor for single responsibility (SRP).

Safety Guard (RULES.md §4.6):
    Lock validation is performed at this Application layer BEFORE any write
    operation. This ensures Infrastructure layer (Writers) remain pure I/O
    adapters without knowledge of locking mechanisms.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, cast

import orjson

from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.locking import LockNotHeldError

if TYPE_CHECKING:
    from typing import Any as SpanType

    from bioetl.application.core.batch_metrics import BatchMetricsRecorder
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import GoldValidatorPort, StoragePort, TracingPort
    from bioetl.domain.types import BatchID
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult


class BatchWriter:
    """Writes records to Bronze, Silver, and Gold layers.

    Handles:
    - Bronze: JSONL serialization with deterministic ordering
    - Silver: Metadata enrichment (_run_id, _run_type, etc.)
    - Gold: Schema validation and column filtering

    Safety Guard:
        Lock validation is performed BEFORE each write operation via
        the lock_validator callback. This implements RULES.md §4.6.
    """

    def __init__(
        self,
        storage: StoragePort,
        context: PipelineContext,
        config: RecordProcessorConfig,
        gold_validator: GoldValidatorPort,
        error_classifier: ErrorClassifier,
        batch_metrics: BatchMetricsRecorder,
        tracer: TracingPort | None = None,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
    ) -> None:
        """Initialize batch writer.

        Args:
            storage: Storage port for writing to all layers.
            context: Pipeline execution context.
            config: Record processor configuration.
            gold_validator: Validator for Gold layer records.
            error_classifier: Service for error classification.
            batch_metrics: Metrics recorder for batch processing.
            tracer: Optional tracing port for distributed tracing.
            lock_validator: Async callable that validates lock ownership.
                Returns True if lock is still held, False otherwise.
                If None, lock validation is skipped (for tests).

        """
        self._storage = storage
        self._context = context
        self._config = config
        self._gold_validator = gold_validator
        self._error_classifier = error_classifier
        self._batch_metrics = batch_metrics
        self._tracer = tracer
        self._lock_validator = lock_validator

        # Convenience properties
        self._provider = config.provider
        self._entity_type = config.entity_type
        self._silver_schema = config.silver_schema
        self._table_config = config.table_config
        self._gold_schema = config.gold_schema

        # Pre-calculate table names and write modes to avoid repeated logic in hot paths
        self._silver_table_name = (
            self._table_config.silver_table or f"{self._provider}.{self._entity_type}"
        )
        self._gold_table_name = (
            self._table_config.gold_table or f"{self._provider}.{self._entity_type}"
        )

        # Pre-calculate write modes
        # Pass write mode directly without silent degradation (R1 refactoring)
        silver_mode_val = self._table_config.silver_write_mode
        self._silver_mode = cast(
            Literal["merge", "append", "delete"],
            silver_mode_val.value
            if hasattr(silver_mode_val, "value")
            else silver_mode_val,
        )

        gold_mode_val = self._table_config.gold_write_mode
        self._gold_mode = cast(
            Literal["overwrite", "append", "scd2"],
            gold_mode_val.value if hasattr(gold_mode_val, "value") else gold_mode_val,
        )

    async def _validate_lock(self, operation: str) -> None:
        """Validate lock ownership before write operation (Safety Guard §4.6).

        Args:
            operation: Name of the operation for error messages.

        Raises:
            LockNotHeldError: If lock is no longer held.
        """
        if self._lock_validator is None:
            # Lock validation disabled (e.g., for tests)
            return

        if not await self._lock_validator():
            table_name = f"{self._provider}_{self._entity_type}"
            self._context.logger.error(
                "Lock lost before write",
                operation=operation,
                table=table_name,
                run_id=str(self._context.run_id),
            )
            raise LockNotHeldError(operation, f"lock:{table_name}")

    def _start_span(
        self, name: str, layer: str, record_count: int, batch_id: BatchID | None = None
    ) -> SpanType | None:
        """Start a tracing span for a write operation.

        Args:
            name: Span name (e.g., "write_bronze").
            layer: Layer name (bronze, silver, gold).
            record_count: Number of records being written.
            batch_id: Optional batch identifier.

        Returns:
            Span context manager or None if tracer is not available.
        """
        if not self._tracer:
            return None

        attrs: dict[str, Any] = {
            "bioetl.layer": layer,
            "bioetl.record_count": record_count,
            "bioetl.provider": self._provider,
            "bioetl.entity_type": self._entity_type,
        }
        if batch_id:
            attrs["bioetl.batch_id"] = str(batch_id)

        span = self._tracer.get_tracer("bioetl.batch_writer").start_as_current_span(
            name, attributes=attrs
        )
        span.__enter__()
        return span

    def _end_span(self, span: SpanType | None, error: Exception | None = None) -> None:
        """End a tracing span.

        Args:
            span: Span to end (may be None if tracer was not available).
            error: Optional exception to record on the span.
        """
        if not span:
            return
        if error:
            span.set_attribute("error", True)
            span.record_exception(error)
        span.__exit__(None, None, None)

    async def write_bronze(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
        ingestion_ts: datetime,
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeWriteResult:
        """Write records to Bronze layer.

        Serializes records to JSON with deterministic key ordering,
        sorts by content for reproducibility.

        Args:
            records: Raw records to write.
            batch_id: Identifier for the current batch.
            ingestion_ts: Ingestion timestamp from context.
            source_metadata: Optional pre-built SourceMetadata with API request
                           details for rich lineage tracking. If provided,
                           it will be included in the Bronze metadata sidecar.

        Returns:
            BronzeWriteResult with path, record count, sizes, and checksum
            for downstream lineage tracking (REQ-LINEAGE-001).

        Raises:
            LockNotHeldError: If lock is no longer held (Safety Guard §4.6).
        """
        # Safety Guard: validate lock BEFORE write
        await self._validate_lock("write_bronze")

        span = self._start_span("write_bronze", "bronze", len(records), batch_id)

        try:
            # Serialize with deterministic key ordering
            # orjson returns bytes
            json_bytes_list = [
                orjson.dumps(r, option=orjson.OPT_SORT_KEYS) for r in records
            ]

            # Sort bytes for deterministic file content
            json_bytes_list.sort()

            # Create generator for bytes with newlines
            record_bytes = (b + b"\n" for b in json_bytes_list)

            bronze_result = await self._storage.write_bronze(
                records=record_bytes,
                provider=self._provider,
                entity=self._entity_type,
                date=ingestion_ts,
                batch_id=batch_id,
                run_id=self._context.run_id,
                run_type=self._context.run_type,
                ingestion_ts=ingestion_ts,
                source_metadata=source_metadata,
            )
            self._end_span(span)
            return bronze_result
        except Exception as e:
            self._end_span(span, e)
            raise

    async def write_silver(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
        ingestion_ts: datetime,
        bronze_refs: list[BronzeWriteResult] | None = None,
    ) -> SilverWriteResult | None:
        """Write records to Silver layer with metadata.

        Enriches records with _run_id, _run_type, _source_batch_id, _ingestion_ts.

        Args:
            records: Transformed Silver records.
            batch_id: Identifier for the source batch.
            ingestion_ts: Ingestion timestamp from context.
            bronze_refs: Optional list of BronzeWriteResult from Bronze writes.
                If provided, bronze_paths will be populated in Silver metadata
                for complete lineage tracking (REQ-LINEAGE-001).

        Returns:
            SilverWriteResult with table info and Delta version for Gold lineage tracking
            (REQ-LINEAGE-002), or None if no records were written.

        Raises:
            LockNotHeldError: If lock is no longer held (Safety Guard §4.6).
        """
        # Safety Guard: validate lock BEFORE write
        await self._validate_lock("write_silver")

        span = self._start_span("write_silver", "silver", len(records), batch_id)

        try:
            # Records already have lineage fields from BaseTransformer.entity_to_silver_record
            # But we need to ensure they are present and correct, especially source_batch_id
            # which might be None in entity if not passed during creation.

            # We update _source_batch_id here as it is batch-specific context
            batch_id_str = str(batch_id)

            # OPTIMIZATION: Modify records in-place instead of creating a full copy.
            # This reduces memory allocation overhead by ~35% for large batches.
            # Safety: silver_records are not used after this step in RecordProcessor.
            for r in records:
                r["_source_batch_id"] = batch_id_str

            silver_result = await self._storage.write_silver(
                table_name=self._silver_table_name,
                records=records,
                primary_keys=list(self._table_config.primary_keys),
                schema=self._silver_schema,
                mode=self._silver_mode,
                on_schema_mismatch=self._table_config.on_schema_mismatch,
                bronze_refs=bronze_refs,
            )
            self._end_span(span)
            return silver_result
        except Exception as e:
            self._end_span(span, e)
            raise

    async def write_gold(
        self,
        records: list[dict[str, Any]],
        silver_refs: list[SilverWriteResult] | None = None,
    ) -> None:
        """Write records to Gold layer with validation.

        Filters columns to match Gold schema, validates records.
        Passes ingestion_ts and run_id from context for audit correlation (ADR-014).

        Args:
            records: Transformed Gold records.
            silver_refs: Optional list of SilverWriteResult from Silver writes.
                If provided, source_tables will be populated in Gold metadata
                for complete lineage tracking (REQ-LINEAGE-002).

        Raises:
            SchemaViolationError: If validation fails.
            LockNotHeldError: If lock is no longer held (Safety Guard §4.6).
        """
        # Safety Guard: validate lock BEFORE write
        await self._validate_lock("write_gold")

        span = self._start_span("write_gold", "gold", len(records))

        try:
            # Filter records to only include columns defined in Gold schema
            # This ensures strict schema validation passes (REQ-DATA-009)
            schema_columns = self._get_schema_columns(self._gold_schema)
            if schema_columns:
                # DQ columns with default values if missing (required by Gold schemas)
                dq_defaults = {"_dq_warn": False, "_dq_error": False}
                records = [
                    {
                        k: r.get(k, dq_defaults.get(k))
                        for k in schema_columns
                        if k in r or k in dq_defaults
                    }
                    for r in records
                ]

            # Validate Gold records
            result = self._gold_validator.validate(records)
            if not result.valid:
                raise SchemaViolationError("gold", result.errors)

            # Pass ingestion_ts, run_id, and silver_refs for audit and lineage (ADR-014, REQ-LINEAGE-002)
            await self._storage.write_gold(
                table_name=self._gold_table_name,
                records=records,
                schema=self._gold_schema,
                primary_keys=list(self._table_config.primary_keys),
                mode=self._gold_mode,
                ingestion_ts=self._context.started_at,
                run_id=self._context.run_id,
                silver_refs=silver_refs,
            )
            self._end_span(span)
        except Exception as e:
            self._end_span(span, e)
            raise

    def _get_schema_columns(self, schema: Any) -> set[str] | None:
        """Extract column names from Pandera schema.

        Args:
            schema: Pandera DataFrameModel or DataFrameSchema.

        Returns:
            Set of column names, or None if schema is not recognized.

        """
        # Handle Pandera DataFrameModel (class with to_schema method)
        if hasattr(schema, "to_schema"):
            try:
                converted = schema.to_schema()
                return set(converted.columns.keys())
            except Exception:
                pass

        # Handle Pandera DataFrameSchema (instance with columns dict)
        if hasattr(schema, "columns"):
            return set(schema.columns.keys())

        return None

    def log_and_track_write_error(
        self, layer: str, error: Exception, batch_id: BatchID
    ) -> None:
        """Log write error and track metrics.

        Args:
            layer: Layer name (bronze, silver, gold).
            error: Exception that occurred.
            batch_id: Identifier for the batch.

        """
        error_type = self._error_classifier.classify(error)
        self._context.logger.error(
            "layer_write_failed",
            layer=layer,
            error=str(error),
            error_type=error_type.value,
            batch_id=str(batch_id),
        )
        self._batch_metrics.track_error(f"{layer}_write", error_type)

================================================================================
File: checkpoint_manager.py
Path: core\checkpoint_manager.py
================================================================================
"""Checkpoint Manager for ETL Pipelines.

This module is framework-agnostic and handles checkpoint persistence
for pipeline run tracking.
"""

from __future__ import annotations

from typing import Any

from bioetl.domain.ports import CheckpointPort, LoggerPort
from bioetl.domain.types import RunID


class CheckpointManager:
    """Framework-agnostic checkpoint management."""

    def __init__(
        self,
        checkpoint_port: CheckpointPort,
        logger: LoggerPort,
        pipeline_name: str,
        run_id: RunID,
        resume: bool,
    ) -> None:
        """Initialize checkpoint manager.

        Args:
            checkpoint_port: Port for checkpoint operations.
            logger: Logger instance.
            pipeline_name: Name of the pipeline.
            run_id: Unique identifier for the pipeline run.
            resume: Whether to resume from previous checkpoint.

        """
        self._checkpoint = checkpoint_port
        self._logger = logger
        self._pipeline_name = pipeline_name
        self._run_id = run_id
        self._resume = resume

    async def load_checkpoint(self) -> dict[str, Any] | None:
        """Load checkpoint if resuming."""
        if self._resume:
            checkpoint_data = await self._checkpoint.load(self._pipeline_name)
            if checkpoint_data:
                _, metadata = checkpoint_data
                self._logger.info(
                    "Found previous checkpoint",
                    extra={"metadata": metadata},
                )
                return metadata
        return None

    async def save_checkpoint(self, records_processed: int) -> None:
        """Save checkpoint.

        Args:
            records_processed: Count of records processed so far

        """
        await self._checkpoint.save(
            pipeline=self._pipeline_name,
            run_id=self._run_id,
            metadata={"records_processed": records_processed},
        )

    async def delete_checkpoint(self) -> None:
        """Delete checkpoint after successful run."""
        await self._checkpoint.delete(self._pipeline_name)

    async def list_all(self) -> list[str]:
        """List all pipelines that have checkpoints.

        Delegates to CheckpointPort.list_all() for CLI inspection.

        Returns:
            List of pipeline names with existing checkpoints.

        """
        return await self._checkpoint.list_all()

================================================================================
File: cleanup_service.py
Path: core\cleanup_service.py
================================================================================
"""Unified cleanup service for Silver and Gold layers.

Implements single entry point for preview and actual cleanup operations.
Used by both CLI (dry-run preview) and PipelineRunner (actual cleanup).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, StoragePort


@dataclass(frozen=True, slots=True)
class LayerInfo:
    """Information about a medallion layer for cleanup preview.

    Attributes:
        path: Path to the layer directory.
        file_count: Number of files in the layer.
        exists: Whether the layer exists.
    """

    path: str
    file_count: int
    exists: bool


@dataclass(frozen=True, slots=True)
class CleanupPreview:
    """Result of cleanup preview operation.

    Attributes:
        silver: Silver layer information.
        gold: Gold layer information (None if not specified).
        total_files: Total number of files that would be affected.
    """

    silver: LayerInfo
    gold: LayerInfo | None
    total_files: int


@dataclass(frozen=True, slots=True)
class CleanupResult:
    """Result of cleanup execution.

    Attributes:
        silver_cleared: Number of items cleared from Silver layer.
        gold_cleared: Number of items cleared from Gold layer.
        dry_run: Whether this was a dry run (no actual deletion).
    """

    silver_cleared: int
    gold_cleared: int
    dry_run: bool

    @property
    def total_cleared(self) -> int:
        """Get total items cleared.

        Returns:
            Sum of silver and gold cleared items.
        """
        return self.silver_cleared + self.gold_cleared


class CleanupService:
    """Unified service for cleanup operations.

    Provides single entry point for both preview (dry-run) and actual
    cleanup operations. Used by CLI for --dry-run mode and by
    PipelineRunner for rebuild/backfill runs.

    Dependencies are injected via constructor following clean architecture.

    Attributes:
        _storage: StoragePort for data layer operations.
        _logger: LoggerPort for structured logging.

    Example:
        >>> service = CleanupService(storage=storage, logger=logger)
        >>> preview = await service.preview("chembl_activity", "chembl.activity")
        >>> preview.total_files  # Number of files to clear
        42
        >>> result = await service.execute(
        ...     silver_table="chembl_activity",
        ...     gold_table="chembl.activity",
        ...     dry_run=False,
        ... )
        >>> result.total_cleared  # Number of items cleared
        150
    """

    def __init__(self, storage: StoragePort, logger: LoggerPort) -> None:
        """Initialize cleanup service.

        Args:
            storage: StoragePort for data layer operations.
            logger: LoggerPort for structured logging.
        """
        self._storage = storage
        self._logger = logger

    async def preview(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> CleanupPreview:
        """Preview what would be cleared without actual deletion.

        Used by CLI --dry-run mode to show users what data would be affected
        before performing a rebuild or backfill operation.

        Args:
            silver_table: Silver table name (e.g., 'chembl.activity').
            gold_table: Optional Gold table name.

        Returns:
            CleanupPreview with information about affected layers.
        """
        # Use sync preview_cleanup from StoragePort
        preview_dict = self._storage.preview_cleanup(
            silver_table=silver_table,
            gold_table=gold_table,
        )

        silver_info = self._parse_layer_info(preview_dict.get("silver", {}))
        gold_info = None
        if preview_dict.get("gold"):
            gold_info = self._parse_layer_info(preview_dict["gold"])

        total_files = preview_dict.get("total_files", 0)

        self._logger.debug(
            "cleanup_preview",
            silver_table=silver_table,
            gold_table=gold_table,
            total_files=total_files,
        )

        return CleanupPreview(
            silver=silver_info,
            gold=gold_info,
            total_files=total_files,
        )

    async def execute(
        self,
        silver_table: str,
        gold_table: str | None = None,
        dry_run: bool = False,
    ) -> CleanupResult:
        """Execute cleanup operation.

        Clears Silver and optionally Gold layer data.
        Supports dry_run mode for preview without actual deletion.

        Args:
            silver_table: Silver table name (e.g., 'chembl.activity').
            gold_table: Optional Gold table name.
            dry_run: If True, only count what would be deleted.

        Returns:
            CleanupResult with counts of cleared items.
        """
        silver_cleared = await self._storage.clear_silver(silver_table, dry_run=dry_run)

        gold_cleared = 0
        if gold_table:
            gold_cleared = await self._storage.clear_gold(gold_table, dry_run=dry_run)

        result = CleanupResult(
            silver_cleared=silver_cleared,
            gold_cleared=gold_cleared,
            dry_run=dry_run,
        )

        self._log_result(silver_table, gold_table, result)

        return result

    def _parse_layer_info(self, info_dict: dict[str, Any]) -> LayerInfo:
        """Parse layer info from storage preview response.

        Args:
            info_dict: Dictionary with layer information.

        Returns:
            LayerInfo dataclass.
        """
        return LayerInfo(
            path=info_dict.get("path", ""),
            file_count=info_dict.get("file_count", 0),
            exists=info_dict.get("exists", False),
        )

    def _log_result(
        self,
        silver_table: str,
        gold_table: str | None,
        result: CleanupResult,
    ) -> None:
        """Log cleanup operation result.

        Args:
            silver_table: Silver table name.
            gold_table: Gold table name.
            result: The cleanup operation result.
        """
        if result.dry_run:
            self._logger.info(
                "DRY RUN: Would clear storage",
                silver_table=silver_table,
                gold_table=gold_table,
                silver_would_clear=result.silver_cleared,
                gold_would_clear=result.gold_cleared,
            )
        elif result.total_cleared > 0:
            self._logger.info(
                "Cleared storage",
                silver_table=silver_table,
                gold_table=gold_table,
                silver_cleared=result.silver_cleared,
                gold_cleared=result.gold_cleared,
            )

================================================================================
File: config.py
Path: core\config.py
================================================================================
"""Configuration objects for application core components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bioetl.application.core.memory_monitor import MemoryConfig
from bioetl.domain.config import DQConfig, TableConfig

if TYPE_CHECKING:
    from bioetl.domain.types import RunType


@dataclass(frozen=True)
class RecordProcessorConfig:
    """Configuration for RecordProcessor."""

    pipeline_name: str
    provider: str
    entity_type: str
    silver_schema: Any
    gold_schema: Any
    dq_config: DQConfig | None = None
    table_config: TableConfig = field(default_factory=TableConfig)
    memory_config: MemoryConfig = field(default_factory=MemoryConfig)
    # DQ report output paths (for flat_structure support)
    bronze_output_path: str | None = None
    silver_output_path: str | None = None
    gold_output_path: str | None = None
    flat_structure: bool = False


@dataclass(frozen=True, slots=True)
class LockConfig:
    """Configuration for LockManager.

    Bundles locking configuration to reduce __init__ parameters.

    Attributes:
        lock_key: The key used for the distributed lock.
        exclusive: Whether the lock is exclusive.
        lock_ttl: Time-to-live for the lock in seconds.
        wait_for_lock: Whether to wait for lock acquisition.
        wait_timeout: Maximum time to wait for lock in seconds.
        heartbeat_interval: Interval for sending heartbeats in seconds.

    """

    lock_key: str
    exclusive: bool = False
    lock_ttl: int = 90
    wait_for_lock: bool = True
    wait_timeout: int = 300
    heartbeat_interval: int = 30

    @classmethod
    def for_pipeline(
        cls,
        provider: str,
        entity_type: str,
        run_type: RunType,
        lock_ttl: int = 90,
        wait_for_lock: bool = True,
        wait_timeout: int = 300,
        heartbeat_interval: int = 30,
    ) -> LockConfig:
        """Create LockConfig for a pipeline.

        Generates appropriate lock key based on provider, entity, and run type.

        Args:
            provider: Name of the data provider.
            entity_type: Type of entity being processed.
            run_type: Type of run (determines exclusivity).
            lock_ttl: Time-to-live for the lock in seconds.
            wait_for_lock: Whether to wait for lock acquisition.
            wait_timeout: Maximum time to wait for lock in seconds.
            heartbeat_interval: Interval for sending heartbeats in seconds.

        Returns:
            Configured LockConfig instance.

        """
        from bioetl.domain.types import RunType

        exclusive = run_type in (RunType.BACKFILL, RunType.REBUILD)
        lock_key = f"lock:{provider}_{entity_type}"
        if exclusive:
            lock_key = f"{lock_key}:exclusive"

        return cls(
            lock_key=lock_key,
            exclusive=exclusive,
            lock_ttl=lock_ttl,
            wait_for_lock=wait_for_lock,
            wait_timeout=wait_timeout,
            heartbeat_interval=heartbeat_interval,
        )

================================================================================
File: field_specs.py
Path: core\field_specs.py
================================================================================
"""Declarative field mapping specifications.

Provides a DSL for declaring field transformations, replacing repetitive
_map_* methods with config-driven approach.

Example usage:
    >>> from bioetl.application.core.field_specs import (
    ...     FieldSpec, FieldGroup, map_fields, INT, FLOAT
    ... )
    >>> specs = (
    ...     FieldSpec("activity_id", converter=str),
    ...     FieldSpec("value", converter=FLOAT),
    ...     FieldSpec("type"),  # No conversion
    ... )
    >>> record = {"activity_id": 123, "value": "5.5", "type": "IC50"}
    >>> map_fields(record, specs)
    {'activity_id': '123', 'value': 5.5, 'type': 'IC50'}
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bioetl.domain.transformations import safe_float, safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# Type aliases for common converters
INT: Callable[[Any], int | None] = safe_int
FLOAT: Callable[[Any], float | None] = safe_float
STR: Callable[[Any], str] = str


def normalize_pmid(value: Any) -> str | None:
    """Normalize PubMed ID to string format.

    Converts int or string PMID to normalized string representation.
    Returns None for invalid inputs.

    Args:
        value: Raw PMID value (int, str, or None).

    Returns:
        Normalized PMID string (digits only), or None if invalid.

    Examples:
        >>> normalize_pmid(12345678)
        '12345678'
        >>> normalize_pmid("12345678")
        '12345678'
        >>> normalize_pmid("  12345678  ")
        '12345678'
        >>> normalize_pmid(None)
        None
        >>> normalize_pmid("abc")
        None
    """
    if value is None:
        return None

    # Convert to string and strip whitespace
    if isinstance(value, bool):
        # Reject booleans explicitly (isinstance(True, int) is True)
        return None
    if isinstance(value, int):
        str_value = str(value)
    elif isinstance(value, str):
        str_value = value.strip()
    else:
        return None

    # Validate: must be non-empty and contain only digits
    if not str_value or not str_value.isdigit():
        return None

    # Validate: must be positive (no "0" alone)
    int_value = int(str_value)
    if int_value <= 0:
        return None

    # Normalize: remove leading zeros
    return str(int_value)


PMID: Callable[[Any], str | None] = normalize_pmid


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """Specification for a single field mapping.

    Attributes:
        source: Source field name in the record.
        target: Target field name in output. Defaults to source if None.
        converter: Optional type converter function. Applied if value is not None.
        required: If True, raise ValueError when field is missing or None.
        default: Default value when field is missing (only used if not required).

    Example:
        >>> spec = FieldSpec("molecule_id", target="molecule_chembl_id", converter=str)
        >>> spec = FieldSpec("value", converter=FLOAT, required=True)
        >>> spec = FieldSpec("description", default="N/A")
    """

    source: str
    target: str | None = None
    converter: Callable[[Any], Any] | None = None
    required: bool = False
    default: Any = None


@dataclass(frozen=True, slots=True)
class FieldGroup:
    """Group of related field specifications.

    Useful for organizing fields by category (identifiers, values, metadata).

    Attributes:
        name: Descriptive name for the group.
        fields: Tuple of field specifications.
        prefix: Optional prefix added to all target field names.

    Example:
        >>> group = FieldGroup(
        ...     name="activity_values",
        ...     fields=(
        ...         FieldSpec("value", converter=FLOAT),
        ...         FieldSpec("units"),
        ...     ),
        ... )
    """

    name: str
    fields: tuple[FieldSpec, ...]
    prefix: str = ""


def map_field(record: BronzeRecord, spec: FieldSpec) -> tuple[str, Any]:
    """Map a single field from record according to specification.

    Args:
        record: Source record dictionary.
        spec: Field specification.

    Returns:
        Tuple of (target_field_name, value).

    Raises:
        ValueError: If field is required but missing or None.
    """
    value = record.get(spec.source)
    target = spec.target or spec.source

    if value is None:
        if spec.required:
            raise ValueError(f"Required field '{spec.source}' is missing or None")
        if spec.default is not None:
            return target, spec.default
        return target, None

    if spec.converter is not None:
        value = spec.converter(value)

    return target, value


def map_fields(
    record: BronzeRecord,
    specs: Sequence[FieldSpec],
) -> dict[str, Any]:
    """Map multiple fields from record according to specifications.

    Args:
        record: Source record dictionary.
        specs: Sequence of field specifications.

    Returns:
        Dictionary with mapped fields.

    Raises:
        ValueError: If any required field is missing.

    Example:
        >>> specs = (
        ...     FieldSpec("activity_id", converter=str, required=True),
        ...     FieldSpec("value", converter=FLOAT),
        ...     FieldSpec("type"),
        ... )
        >>> map_fields({"activity_id": 123, "value": "5.5", "type": "IC50"}, specs)
        {'activity_id': '123', 'value': 5.5, 'type': 'IC50'}
    """
    result: dict[str, Any] = {}

    for spec in specs:
        target, value = map_field(record, spec)
        result[target] = value

    return result


def map_field_group(
    record: BronzeRecord,
    group: FieldGroup,
) -> dict[str, Any]:
    """Map a group of fields with optional prefix.

    Args:
        record: Source record dictionary.
        group: Field group specification.

    Returns:
        Dictionary with mapped fields, optionally prefixed.

    Example:
        >>> group = FieldGroup(
        ...     name="ligand_efficiency",
        ...     prefix="le_",
        ...     fields=(
        ...         FieldSpec("bei", converter=FLOAT),
        ...         FieldSpec("le", converter=FLOAT),
        ...     ),
        ... )
        >>> map_field_group({"bei": "1.5", "le": "0.3"}, group)
        {'le_bei': 1.5, 'le_le': 0.3}
    """
    mapped = map_fields(record, group.fields)

    if group.prefix:
        return {f"{group.prefix}{k}": v for k, v in mapped.items()}
    return mapped


def map_field_groups(
    record: BronzeRecord,
    groups: Sequence[FieldGroup],
) -> dict[str, Any]:
    """Map multiple field groups, merging results.

    Args:
        record: Source record dictionary.
        groups: Sequence of field groups.

    Returns:
        Merged dictionary with all mapped fields.
    """
    result: dict[str, Any] = {}

    for group in groups:
        result.update(map_field_group(record, group))

    return result


# =============================================================================
# Convenience functions for common patterns
# =============================================================================


def simple_fields(*field_names: str) -> tuple[FieldSpec, ...]:
    """Create simple field specs (no conversion) from field names.

    Args:
        *field_names: Variable number of field names.

    Returns:
        Tuple of FieldSpec objects with no converters.

    Example:
        >>> specs = simple_fields("type", "units", "relation")
        >>> len(specs)
        3
    """
    return tuple(FieldSpec(name) for name in field_names)


def int_fields(*field_names: str) -> tuple[FieldSpec, ...]:
    """Create field specs with safe_int converter.

    Args:
        *field_names: Variable number of field names.

    Returns:
        Tuple of FieldSpec objects with INT converter.

    Example:
        >>> specs = int_fields("record_id", "src_id", "max_phase")
    """
    return tuple(FieldSpec(name, converter=INT) for name in field_names)


def float_fields(*field_names: str) -> tuple[FieldSpec, ...]:
    """Create field specs with safe_float converter.

    Args:
        *field_names: Variable number of field names.

    Returns:
        Tuple of FieldSpec objects with FLOAT converter.

    Example:
        >>> specs = float_fields("value", "standard_value", "pchembl_value")
    """
    return tuple(FieldSpec(name, converter=FLOAT) for name in field_names)


def pmid_fields(*field_names: str) -> tuple[FieldSpec, ...]:
    """Create field specs with normalize_pmid converter for PubMed IDs.

    Converts int or string PMIDs to normalized string format.
    Returns None for invalid values.

    Args:
        *field_names: Variable number of field names.

    Returns:
        Tuple of FieldSpec objects with PMID converter.

    Example:
        >>> specs = pmid_fields("pubmed_id", "pubmed_id1", "pubmed_id2")
    """
    return tuple(FieldSpec(name, converter=PMID) for name in field_names)


__all__ = [
    "FLOAT",
    "INT",
    "PMID",
    "STR",
    "FieldGroup",
    "FieldSpec",
    "float_fields",
    "int_fields",
    "map_field",
    "map_field_group",
    "map_field_groups",
    "map_fields",
    "normalize_pmid",
    "pmid_fields",
    "simple_fields",
]

================================================================================
File: filtered_data_source.py
Path: core\filtered_data_source.py
================================================================================
"""Filtered Data Source wrapper.

Decorates a DataSourcePort with input filtering capability.
Loads filter IDs from external sources (CSV) and passes them to the adapter.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from bioetl.domain.ports import FilterableDataSourcePort, InputFilterPort

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Mapping

    from bioetl.domain.filtering import FilterLoadResult, InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.domain.types import HealthStatus


class FilteredDataSource:
    """Wraps a DataSourcePort to add CSV-based filtering.

    Decorator pattern: loads filter IDs from CSV, calls fetch_filtered() on
    adapters that support it, delegates all other operations to wrapped adapter.
    Multi-column filtering uses hybrid approach (server + client-side filtering).
    """

    def __init__(
        self,
        data_source: DataSourcePort,
        filter_reader: InputFilterPort | None,
        filter_config: InputFilterConfig,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize filtered data source wrapper."""
        self._data_source = data_source
        self._filter_reader = filter_reader
        self._filter_config = filter_config
        self._metrics = metrics
        self._pipeline_name = pipeline_name
        self._logger = logger
        self._filter_ids: list[str] | None = None
        self._filter_result: FilterLoadResult | None = None
        # Multi-column filtering state
        self._multi_filter_ids: Mapping[str, list[str]] | None = None
        self._valid_combinations: frozenset[tuple[str, ...]] | None = None
        self._filter_fields: tuple[str, ...] | None = None
        # Fallback mapping state (e.g., DOI → title)
        self._fallback_mapping: dict[str, str] | None = None

    @property
    def provider_name(self) -> str:
        """Provider name from the wrapped data source."""
        return self._data_source.provider_name

    @property
    def filter_result(self) -> FilterLoadResult | None:
        """Access to filter load result with duplicate statistics."""
        return self._filter_result

    def _filter_file_exists(self, source_path: str) -> bool:
        """Check if filter file exists, log warning if missing.

        Returns True if file exists, False otherwise (graceful degradation).
        """
        if Path(source_path).exists():
            return True

        if self._logger:
            self._logger.warning(
                "input_filter_file_not_found",
                source_path=source_path,
                pipeline=self._pipeline_name,
                message="Filter file not found, proceeding without filtering",
            )
        return False

    async def __aenter__(self) -> Self:
        """Enter async context and load filter IDs if enabled."""
        await self._data_source.__aenter__()

        if not self._filter_config.enabled:
            return self

        # Check for direct filter IDs (composite mode - no CSV needed)
        if self._filter_config.direct_filter_ids:
            self._load_direct_filter_ids()
            return self

        # Pre-load filter IDs from CSV
        await self._load_csv_filter_ids()
        return self

    def _load_direct_filter_ids(self) -> None:
        """Load direct filter IDs from composite mode configuration."""
        self._filter_ids = list(self._filter_config.direct_filter_ids or [])
        if self._logger:
            self._logger.info(
                "direct_filter_ids_loaded",
                count=len(self._filter_ids),
                filter_field=self._filter_config.filter_field,
                pipeline=self._pipeline_name,
            )

    async def _load_csv_filter_ids(self) -> None:
        """Load filter IDs from CSV file."""
        if not self._filter_reader:
            return

        source_path = self._filter_config.source_path
        if not source_path or not self._filter_file_exists(source_path):
            return

        columns = self._filter_config.get_columns()
        if len(columns) > 1:
            await self._load_multi_column_filter(source_path, columns)
        elif self._filter_config.column_name:
            await self._load_single_column_filter(source_path)

    async def _load_multi_column_filter(
        self, source_path: str, columns: tuple[Any, ...]
    ) -> None:
        """Load multi-column filter from CSV."""
        assert self._filter_reader is not None
        self._filter_result = await self._filter_reader.load_multi_column_filter(
            source_path=source_path,
            columns=list(columns),
        )
        self._multi_filter_ids = {
            field: list(ids) for field, ids in self._filter_result.column_ids.items()
        }
        self._valid_combinations = self._filter_result.valid_combinations
        self._filter_fields = self._filter_result.filter_fields
        self._record_multi_filter_metrics()

    async def _load_single_column_filter(self, source_path: str) -> None:
        """Load single-column filter from CSV."""
        assert self._filter_reader is not None
        assert self._filter_config.column_name is not None
        if self._filter_config.fallback_column:
            (
                self._filter_result,
                self._fallback_mapping,
            ) = await self._filter_reader.load_filter_with_fallback(
                source_path=source_path,
                primary_column=self._filter_config.column_name,
                fallback_column=self._filter_config.fallback_column,
            )
        else:
            self._filter_result = await self._filter_reader.load_filter_ids(
                source_path=source_path,
                column_name=self._filter_config.column_name,
            )
        self._filter_ids = list(self._filter_result.ids)
        self._record_filter_metrics()

    def _record_filter_metrics(self) -> None:
        """Record filter loading metrics."""
        if not self._metrics or not self._filter_result:
            return

        source_file = self._filter_config.source_path or "unknown"

        # Record unique IDs loaded
        self._metrics.increment_counter(
            "filter_ids_loaded_total",
            self._filter_result.unique_count,
            {"pipeline": self._pipeline_name, "source_file": source_file},
        )

        # Record duplicates if any
        if self._filter_result.has_duplicates:
            self._metrics.increment_counter(
                "filter_ids_duplicates_total",
                self._filter_result.duplicate_count,
                {"pipeline": self._pipeline_name, "source_file": source_file},
            )

    def _record_multi_filter_metrics(self) -> None:
        """Record multi-column filter loading metrics."""
        if not self._metrics or not self._filter_result:
            return

        source_file = self._filter_config.source_path or "unknown"

        # Record total valid combinations
        if self._valid_combinations:
            self._metrics.increment_counter(
                "filter_combinations_loaded_total",
                len(self._valid_combinations),
                {"pipeline": self._pipeline_name, "source_file": source_file},
            )

        # Record unique IDs per field
        for field, ids in self._filter_result.column_ids.items():
            self._metrics.increment_counter(
                "filter_ids_loaded_total",
                len(ids),
                {
                    "pipeline": self._pipeline_name,
                    "source_file": source_file,
                    "filter_field": field,
                },
            )

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context."""
        await self._data_source.__aexit__(exc_type, exc_val, exc_tb)

    def _matches_valid_combination(self, record: dict[str, Any]) -> bool:
        """Check if record matches one of the valid combinations."""
        if not self._valid_combinations or not self._filter_fields:
            return True
        record_values = tuple(
            str(record.get(field, "")) for field in self._filter_fields
        )
        return record_values in self._valid_combinations

    def _ensure_filterable_adapter(self, mode: str) -> None:
        """Check that adapter implements FilterableDataSourcePort."""
        if not isinstance(self._data_source, FilterableDataSourcePort):
            raise TypeError(
                f"Adapter {self._data_source.provider_name} does not implement "
                f"FilterableDataSourcePort. {mode} requires an adapter with "
                "fetch_filtered() method."
            )

    async def _fetch_multi_column(
        self, entity_type: str, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch with multi-column filtering (hybrid approach)."""
        self._ensure_filterable_adapter("Multi-column filtering")
        assert isinstance(self._data_source, FilterableDataSourcePort)
        fetched_count = 0
        async for record in self._data_source.fetch_multi_filtered(
            entity_type=entity_type,
            filters=dict(self._multi_filter_ids),  # type: ignore[arg-type]
            limit=None,  # Don't limit server-side, we filter client-side
        ):
            if self._matches_valid_combination(record):
                yield record
                fetched_count += 1
                if limit and fetched_count >= limit:
                    return

    async def _fetch_single_column(
        self, entity_type: str, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch with single-column filtering."""
        self._ensure_filterable_adapter("Filtering")
        assert isinstance(self._data_source, FilterableDataSourcePort)
        config_filter_field = self._filter_config.filter_field
        if config_filter_field is None:
            raise ValueError(
                "filter_field must be specified in InputFilterConfig "
                "when filtering is enabled."
            )

        # Check if we have fallback mapping (adapter implements FilterableDataSourcePort)
        if self._fallback_mapping:
            async for record in self._data_source.fetch_filtered_with_fallback(
                entity_type=entity_type,
                filter_ids=self._filter_ids,  # type: ignore[arg-type]
                filter_field=config_filter_field,
                fallback_mapping=self._fallback_mapping,
                limit=limit,
            ):
                yield record
        else:
            # Standard path without fallback
            async for record in self._data_source.fetch_filtered(
                entity_type=entity_type,
                filter_ids=self._filter_ids,  # type: ignore[arg-type]
                filter_field=config_filter_field,
                limit=limit,
            ):
                yield record

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records with optional filtering from internal CSV config."""
        _ = filter_ids, filter_field  # External params ignored, use internal config

        if self._filter_config.enabled and self._multi_filter_ids:
            async for record in self._fetch_multi_column(entity_type, limit):
                yield record
        elif self._filter_config.enabled and self._filter_ids:
            async for record in self._fetch_single_column(entity_type, limit):
                yield record
        else:
            async for record in self._data_source.fetch(
                entity_type=entity_type, limit=limit, query=query
            ):
                yield record

    async def health_check(self) -> HealthStatus:
        """Delegate health check to wrapped adapter."""
        return await self._data_source.health_check()

    async def aclose(self) -> None:
        """Delegate close to wrapped adapter."""
        await self._data_source.aclose()

    def get_source_metadata(self, api_version: str | None = None) -> Any:
        """Delegate get_source_metadata to wrapped data source.

        Returns API request metadata collected by the underlying adapter.
        Used by BatchExecutor to enrich Bronze layer metadata.

        Args:
            api_version: Optional API version string.

        Returns:
            SourceMetadata with request details, or None if not supported.
        """
        get_metadata = getattr(self._data_source, "get_source_metadata", None)
        if get_metadata is not None and callable(get_metadata):
            return get_metadata(api_version)
        return None

================================================================================
File: heartbeat.py
Path: core\heartbeat.py
================================================================================
"""Heartbeat management for distributed locks.

Extracted from LockManager to follow Single Responsibility Principle.
Handles background heartbeat tasks that keep locks alive.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from bioetl.application.core.shutdown import PipelineShutdownError
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from bioetl.application.core.shutdown import ShutdownSignal
    from bioetl.domain.ports import LockPort, LoggerPort


class HeartbeatTask:
    """Manages background heartbeat task for lock maintenance.

    Responsibilities:
    - Start and stop background heartbeat loop
    - Send periodic heartbeats to extend lock TTL
    - Handle lock loss detection and trigger shutdown

    Attributes:
        _lock_port: Port for lock operations.
        _lock_key: Key identifying the lock.
        _owner_id: Identifier of the lock owner (RunID).
        _exclusive: Whether the lock is exclusive.
        _interval: Heartbeat interval in seconds.
        _shutdown_signal: Signal to trigger graceful shutdown.
        _logger: Logger for heartbeat messages.
        _task: Background task reference.

    """

    def __init__(
        self,
        lock_port: LockPort,
        lock_key: str,
        owner_id: RunID,
        exclusive: bool,
        interval: int,
        shutdown_signal: ShutdownSignal,
        logger: LoggerPort,
    ) -> None:
        """Initialize heartbeat task.

        Args:
            lock_port: Port for lock operations.
            lock_key: Key identifying the lock.
            owner_id: Identifier of the lock owner (RunID).
            exclusive: Whether the lock is exclusive.
            interval: Heartbeat interval in seconds.
            shutdown_signal: Signal to trigger graceful shutdown.
            logger: Logger for heartbeat messages.

        """
        self._lock_port = lock_port
        self._lock_key = lock_key
        self._owner_id = owner_id
        self._exclusive = exclusive
        self._interval = interval
        self._shutdown_signal = shutdown_signal
        self._logger = logger
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the background heartbeat task.

        Performs initial heartbeat and starts background loop.

        Raises:
            PipelineShutdownError: If initial heartbeat fails.

        """
        initial_success = await self._lock_port.heartbeat(
            self._lock_key, self._owner_id, exclusive=self._exclusive
        )
        if not initial_success:
            self._logger.error("Heartbeat failed on start; shutting down")
            self._shutdown_signal.request()
            raise PipelineShutdownError("Lock lost on heartbeat start")

        self._task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        """Stop the background heartbeat task.

        Cancels the task and waits for completion.

        """
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    @property
    def is_running(self) -> bool:
        """Check if heartbeat task is running."""
        return self._task is not None and not self._task.done()

    async def _heartbeat_loop(self) -> None:
        """Background loop that sends periodic heartbeats.

        Raises:
            PipelineShutdownError: If lock is lost during heartbeat.

        """
        while not self._shutdown_signal.is_requested:
            await asyncio.sleep(self._interval)
            success = await self._lock_port.heartbeat(
                self._lock_key, self._owner_id, exclusive=self._exclusive
            )
            if not success:
                self._logger.error("Lost lock during execution!")
                self._shutdown_signal.request()
                raise PipelineShutdownError("Lock lost")


__all__ = ["HeartbeatTask"]

================================================================================
File: idmapping_data_source.py
Path: core\idmapping_data_source.py
================================================================================
"""ID Mapping Data Source.

Implements DataSourcePort for ChEMBL → UniProt ID mapping pipeline.
Reads ChEMBL target IDs from CSV and maps them to UniProt accessions.
"""

from __future__ import annotations

import asyncio
import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import IDMappingPort, LoggerPort


class IDMappingDataSource:
    """Data source for ChEMBL → UniProt ID mapping.

    Reads target_chembl_id values from input CSV file and maps them
    to UniProt accessions using the UniProt ID Mapping REST API.

    Implements DataSourcePort protocol for integration with GenericPipeline.

    Example:
        >>> data_source = IDMappingDataSource(
        ...     idmapping_client=client,
        ...     input_path=Path("data/input/target.csv"),
        ...     logger=logger,
        ... )
        >>> async for record in data_source.fetch("idmapping"):
        ...     logger.info("record_fetched", record=record)
        # Output: {"target_chembl_id": "CHEMBL204", "uniprot_accession": "P00742"}
    """

    provider_name: str = "uniprot_idmapping"

    def __init__(
        self,
        idmapping_client: IDMappingPort,
        input_path: Path,
        logger: LoggerPort,
        from_db: str = "ChEMBL",
        to_db: str = "UniProtKB",
        id_column: str = "target_chembl_id",
    ) -> None:
        """Initialize ID Mapping data source.

        Args:
            idmapping_client: UniProt ID Mapping client for API calls.
            input_path: Path to CSV file containing ChEMBL target IDs.
            logger: LoggerPort for structured logging.
            from_db: Source database for ID mapping (default: 'ChEMBL').
            to_db: Target database for ID mapping (default: 'UniProtKB').
            id_column: Column name in CSV containing ChEMBL IDs.
        """
        self._client = idmapping_client
        self._input_path = input_path
        self._logger = logger
        self._from_db = from_db
        self._to_db = to_db
        self._id_column = id_column
        self._is_open = False

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        # Enter the underlying client's context (opens HTTP client)
        await self._client.__aenter__()
        self._is_open = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close data source and release resources."""
        # Exit the underlying client's context (closes HTTP client)
        if self._is_open:
            await self._client.__aexit__(None, None, None)
        self._is_open = False

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch ID mapping records.

        Reads ChEMBL IDs from CSV and maps them to UniProt accessions.
        Returns records with target_chembl_id and uniprot_accession fields.

        Args:
            entity_type: Entity type (should be 'idmapping').
            limit: Optional limit on number of records.
            query: Unused (for interface compatibility).
            filter_ids: Unused (IDs come from CSV).
            filter_field: Unused.

        Yields:
            Dicts with target_chembl_id and uniprot_accession fields.

        Raises:
            FileNotFoundError: If input CSV file doesn't exist.
            ValueError: If required column is missing from CSV.
        """
        # Ignore unused parameters (interface compatibility)
        _ = query, filter_ids, filter_field

        if entity_type != "idmapping":
            self._logger.warning(
                "unexpected_entity_type",
                expected="idmapping",
                received=entity_type,
            )

        # Step 1: Read ChEMBL IDs from CSV (async to avoid blocking event loop)
        chembl_ids = await self._read_chembl_ids_async()

        # Apply limit if specified
        if limit is not None:
            chembl_ids = chembl_ids[:limit]

        if not chembl_ids:
            self._logger.warning("no_ids_to_map", input_path=str(self._input_path))
            return

        self._logger.info(
            "idmapping_fetch_started",
            input_path=str(self._input_path),
            chembl_id_count=len(chembl_ids),
        )

        # Step 2: Call UniProt ID Mapping API
        mapping_results = await self._client.map_ids(
            from_db=self._from_db,
            to_db=self._to_db,
            ids=chembl_ids,
        )

        # Step 3: Yield records for each ChEMBL ID
        found_count = 0
        for chembl_id in chembl_ids:
            uniprot_accession = mapping_results.get(chembl_id)
            if uniprot_accession:
                found_count += 1

            yield {
                "target_chembl_id": chembl_id,
                "uniprot_accession": uniprot_accession,
            }

        self._logger.info(
            "idmapping_fetch_completed",
            total_ids=len(chembl_ids),
            mapped=found_count,
            not_mapped=len(chembl_ids) - found_count,
        )

    async def _read_chembl_ids_async(self) -> list[str]:
        """Read ChEMBL target IDs from input CSV file asynchronously.

        Uses run_in_executor to avoid blocking the event loop.

        Returns:
            List of ChEMBL target IDs.

        Raises:
            FileNotFoundError: If input file doesn't exist.
            ValueError: If required column is missing.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._read_chembl_ids_sync)

    def _read_chembl_ids_sync(self) -> list[str]:
        """Synchronous implementation of ChEMBL ID reading from CSV."""
        if not self._input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self._input_path}")

        ids: list[str] = []

        with self._input_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if self._id_column not in (reader.fieldnames or []):
                raise ValueError(
                    f"Missing required column '{self._id_column}' in {self._input_path}"
                )

            for row in reader:
                chembl_id = row.get(self._id_column, "").strip()
                if chembl_id:
                    ids.append(chembl_id)

        self._logger.debug(
            "csv_read_complete",
            filepath=str(self._input_path),
            record_count=len(ids),
        )

        return ids

    async def health_check(self) -> HealthStatus:
        """Check data source health.

        Verifies:
        1. Input file exists
        2. ID Mapping API is healthy

        Returns:
            HealthStatus indicating overall health.
        """
        # Check input file (async to avoid blocking event loop)
        loop = asyncio.get_running_loop()
        file_exists = await loop.run_in_executor(None, self._input_path.exists)
        if not file_exists:
            self._logger.warning(
                "health_check_failed",
                reason="input_file_missing",
                path=str(self._input_path),
            )
            return HealthStatus.UNHEALTHY

        # Check API health
        api_status = await self._client.health_check()
        if api_status != HealthStatus.HEALTHY:
            return api_status

        return HealthStatus.HEALTHY

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"IDMappingDataSource("
            f"input_path='{self._input_path}', "
            f"from_db='{self._from_db}', "
            f"to_db='{self._to_db}')"
        )

================================================================================
File: lock_manager.py
Path: core\lock_manager.py
================================================================================
"""Lock Manager for ETL Pipelines."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.config import LockConfig
from bioetl.application.core.heartbeat import HeartbeatTask
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.locking import LockContext, LockContextHolder
from bioetl.domain.types import RunID, RunType

if TYPE_CHECKING:
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.domain.ports import LockPort, LoggerPort


class LockManager:
    """Manages acquiring, releasing, and maintaining distributed locks.

    This is an Application Service that coordinates lock lifecycle:
    - Lock acquisition and release
    - Heartbeat management (delegated to HeartbeatTask)
    - Lock context for writers

    Decomposed per REFACTOR-003:
    - LockConfig: bundles configuration parameters
    - HeartbeatTask: manages background heartbeat loop

    Attributes:
        _lock: Port for lock operations.
        _run_id: Unique identifier for the run.
        _config: Lock configuration bundle.
        _logger: Logger instance.
        _shutdown_signal: Signal for graceful shutdown.
        _context_holder: Optional holder for lock context (for writers).
        _heartbeat: Heartbeat task manager.
        _acquired_at: Monotonic timestamp when lock acquired.

    """

    def __init__(
        self,
        lock_port: LockPort,
        run_id: RunID,
        config: LockConfig,
        logger: LoggerPort,
        shutdown_signal: ShutdownSignal,
        checkpoint_manager: CheckpointManager | None = None,
        context_holder: LockContextHolder | None = None,
    ) -> None:
        """Initialize LockManager with explicit dependencies.

        Args:
            lock_port: Port for lock operations.
            run_id: Unique identifier for the run.
            config: Lock configuration bundle.
            logger: Logger instance.
            shutdown_signal: Signal for graceful shutdown.
            checkpoint_manager: Optional checkpoint manager (unused, kept for compatibility).
            context_holder: Optional holder for lock context (for writers).

        """
        self._lock = lock_port
        self._run_id = run_id
        self._config = config
        self._logger = logger
        self._shutdown_signal = shutdown_signal
        self._checkpoint_manager = (
            checkpoint_manager  # Kept for interface compatibility
        )
        self._context_holder = context_holder
        self._heartbeat: HeartbeatTask | None = None
        self._acquired_at: float | None = None  # monotonic timestamp when lock acquired

    @classmethod
    def create(
        cls,
        lock_port: LockPort,
        run_id: RunID,
        provider: str,
        entity_type: str,
        run_type: RunType,
        lock_ttl: int,
        wait_for_lock: bool,
        wait_timeout: int,
        heartbeat_interval: int,
        logger: LoggerPort,
        shutdown_signal: ShutdownSignal,
        checkpoint_manager: CheckpointManager | None = None,
        context_holder: LockContextHolder | None = None,
    ) -> LockManager:
        """Create a LockManager instance.

        Factory method that creates LockConfig from pipeline parameters.
        Maintains backward compatibility with existing call sites.

        Args:
            lock_port: Port for lock operations.
            run_id: Unique identifier for the run.
            provider: Name of the data provider.
            entity_type: Type of entity being processed.
            run_type: Type of run (e.g., incremental, backfill).
            lock_ttl: Time-to-live for the lock in seconds.
            wait_for_lock: Whether to wait for lock acquisition.
            wait_timeout: Maximum time to wait for lock in seconds.
            heartbeat_interval: Interval for sending heartbeats in seconds.
            logger: Logger instance.
            shutdown_signal: Signal for graceful shutdown.
            checkpoint_manager: Optional checkpoint manager.
            context_holder: Optional holder for lock context.

        Returns:
            A configured LockManager instance.

        """
        config = LockConfig.for_pipeline(
            provider=provider,
            entity_type=entity_type,
            run_type=run_type,
            lock_ttl=lock_ttl,
            wait_for_lock=wait_for_lock,
            wait_timeout=wait_timeout,
            heartbeat_interval=heartbeat_interval,
        )

        return cls(
            lock_port=lock_port,
            run_id=run_id,
            config=config,
            logger=logger,
            shutdown_signal=shutdown_signal,
            checkpoint_manager=checkpoint_manager,
            context_holder=context_holder,
        )

    async def acquire(self) -> bool:
        """Acquire the distributed lock.

        Returns:
            True if lock was acquired, False otherwise.

        """
        import time

        acquired = await self._lock.acquire(
            key=self._config.lock_key,
            owner_id=self._run_id,
            ttl=self._config.lock_ttl,
            wait=self._config.wait_for_lock,
            wait_timeout=self._config.wait_timeout,
            exclusive=self._config.exclusive,
        )
        if acquired:
            self._acquired_at = time.monotonic()
            # Update shared context holder for writers
            if self._context_holder is not None:
                self._context_holder.set(self.get_context())  # type: ignore[arg-type]
            self._logger.info(
                "lock_acquired",
                lock_key=self._config.lock_key,
                run_id=str(self._run_id),
            )
        else:
            self._logger.error(
                "lock_acquisition_failed",
                lock_key=self._config.lock_key,
                run_id=str(self._run_id),
            )
        return acquired

    async def release(self) -> None:
        """Release the distributed lock and stop heartbeat."""
        if self._heartbeat:
            await self._heartbeat.stop()
            self._heartbeat = None

        await self._lock.release(
            self._config.lock_key, self._run_id, exclusive=self._config.exclusive
        )
        self._acquired_at = None
        # Clear shared context holder
        if self._context_holder is not None:
            self._context_holder.clear()
        self._logger.info("Lock released", stage="cleanup")

    def get_context(self) -> LockContext | None:
        """Get LockContext for passing to writers.

        Returns a LockContext value object that can be passed to storage
        writers for lock validation (RULES.md §3.3).

        Returns:
            LockContext if lock is held, None if not acquired.
        """
        if self._acquired_at is None:
            return None

        return LockContext(
            key=self._config.lock_key,
            owner_id=self._run_id,
            exclusive=self._config.exclusive,
            acquired_at=self._acquired_at,
        )

    async def start_heartbeat(self) -> None:
        """Start the background heartbeat task.

        Delegates to HeartbeatTask for background loop management.

        Raises:
            PipelineShutdownError: If initial heartbeat fails.

        """
        self._heartbeat = HeartbeatTask(
            lock_port=self._lock,
            lock_key=self._config.lock_key,
            owner_id=self._run_id,
            exclusive=self._config.exclusive,
            interval=self._config.heartbeat_interval,
            shutdown_signal=self._shutdown_signal,
            logger=self._logger,
        )
        await self._heartbeat.start()

    async def __aenter__(self) -> LockManager:
        """Context manager entry: acquire lock.

        Returns:
            Self instance if lock acquired.

        Raises:
            PipelineShutdownError: If lock acquisition fails.

        """
        acquired = await self.acquire()
        if not acquired:
            raise PipelineShutdownError(
                f"Failed to acquire lock for {self._config.lock_key}"
            )
        await self.start_heartbeat()
        return self

    async def validate(self) -> bool:
        """Validate that this LockManager still holds the lock.

        This is the Safety Guard: before critical operations (e.g., writes),
        call this method to verify lock ownership. This prevents split-brain
        scenarios where the lock expired but the writer continued.

        Returns:
            True if this run_id still holds the lock, False otherwise.

        Example:
            async with lock_manager:
                # Before writing to storage:
                if not await lock_manager.validate():
                    raise LockLostError(lock_key, run_id)
                await storage.write_silver(...)
        """
        return await self._lock.validate_owner(self._config.lock_key, self._run_id)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit: release lock."""
        await self.release()

================================================================================
File: memory_monitor.py
Path: core\memory_monitor.py
================================================================================
"""Memory monitoring for adaptive batch processing.

Provides memory pressure detection and adaptive batch size recommendations.
Uses psutil if available, falls back to resource module on Unix or estimates on Windows.

Implements MemoryMonitorPort from domain/ports/memory.py.

Performance optimizations:
- Module-level psutil availability cache (avoid repeated import checks)
- Cached Process instance (avoid repeated process lookup)
- Lazy psutil import (deferred until first get_memory_stats() call)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Re-export MemoryStats from domain for backward compatibility
from bioetl.domain.ports import MemoryStats

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

# Module-level cache for psutil availability (checked once per process)
_PSUTIL_AVAILABLE: bool | None = None
_PSUTIL_MODULE: Any = None  # Cached psutil module reference


def _check_psutil_available() -> bool:
    """Check psutil availability once and cache the result."""
    global _PSUTIL_AVAILABLE, _PSUTIL_MODULE
    if _PSUTIL_AVAILABLE is None:
        try:
            import psutil

            _PSUTIL_MODULE = psutil
            _PSUTIL_AVAILABLE = True
        except ImportError:
            _PSUTIL_AVAILABLE = False
    return _PSUTIL_AVAILABLE


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    """Configuration for memory-aware batch processing.

    Attributes:
        max_batch_memory_mb: Maximum memory per batch in MB (default: 512MB).
        memory_pressure_threshold: Threshold (0.0-1.0) for reducing batch size (default: 0.8).
        min_batch_size: Minimum batch size even under memory pressure (default: 10).
        check_interval_records: Check memory every N records (default: 100).
        enable_adaptive_sizing: Enable/disable adaptive batch sizing (default: True).

    """

    max_batch_memory_mb: int = 512
    memory_pressure_threshold: float = 0.8
    min_batch_size: int = 10
    check_interval_records: int = 100
    enable_adaptive_sizing: bool = True


@dataclass
class MemoryMonitor:
    """Monitor memory usage and provide adaptive batch size recommendations.

    This class tracks memory consumption during batch processing and
    automatically recommends batch size reductions when memory pressure
    is detected, preventing OOM errors during large dataset processing.

    Performance characteristics:
    - First call to get_memory_stats(): ~1-2 ms (with psutil already imported)
    - Subsequent calls: ~0.2-0.5 ms (cached Process instance)
    - Initialization: <1 ms (no heavy imports in __post_init__)

    Example:
        >>> monitor = MemoryMonitor(config=MemoryConfig(), logger=logger)
        >>> batch_size = 1000
        >>> for batch in data_source:
        ...     batch_size = monitor.get_recommended_batch_size(batch_size)
        ...     # Process with adjusted batch size

    """

    config: MemoryConfig
    logger: LoggerPort | None = None
    _psutil_available: bool = field(default=False, init=False)
    _last_batch_size: int = field(default=100, init=False)
    _consecutive_pressure_count: int = field(default=0, init=False)
    _cached_process: Any = field(default=None, init=False)

    def __post_init__(self) -> None:
        """Initialize memory monitor with lazy psutil detection.

        Uses module-level cache for psutil availability check to avoid
        repeated import overhead across multiple MemoryMonitor instances.
        """
        self._psutil_available = _check_psutil_available()
        if self._psutil_available and self.logger:
            self.logger.debug("psutil available for memory monitoring")
        elif not self._psutil_available and self.logger:
            self.logger.debug("psutil not available, using fallback memory monitoring")

    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics.

        Returns:
            MemoryStats with current memory usage information.

        """
        if self._psutil_available:
            return self._get_stats_psutil()
        return self._get_stats_fallback()

    def _get_stats_psutil(self) -> MemoryStats:
        """Get memory stats using psutil.

        Performance optimization: reuses cached psutil module and Process instance
        to avoid repeated imports and process lookups (~40ms savings per init).
        """
        psutil = _PSUTIL_MODULE

        vm = psutil.virtual_memory()

        # Cache Process instance for subsequent calls (saves ~0.2ms per call)
        if self._cached_process is None:
            object.__setattr__(self, "_cached_process", psutil.Process())
        process_memory = self._cached_process.memory_info()

        return MemoryStats(
            used_mb=vm.used / (1024 * 1024),
            available_mb=vm.available / (1024 * 1024),
            total_mb=vm.total / (1024 * 1024),
            percent_used=vm.percent / 100.0,
            process_mb=process_memory.rss / (1024 * 1024),
        )

    def _get_stats_fallback(self) -> MemoryStats:
        """Get memory stats using fallback methods."""
        if sys.platform != "win32":
            return self._get_stats_resource()
        return self._get_stats_estimate()

    def _get_stats_resource(self) -> MemoryStats:
        """Get memory stats using resource module (Unix only)."""
        import resource

        # Get process memory usage (Unix-only attributes)
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        process_mb = rusage.ru_maxrss / 1024  # Convert KB to MB on Linux

        # Try to read system memory from /proc/meminfo
        try:
            with Path("/proc/meminfo").open() as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(":")
                        value = int(parts[1])  # in KB
                        meminfo[key] = value

                total_mb = meminfo.get("MemTotal", 0) / 1024
                available_mb = meminfo.get("MemAvailable", 0) / 1024
                used_mb = total_mb - available_mb
                percent_used = used_mb / total_mb if total_mb > 0 else 0.5

                return MemoryStats(
                    used_mb=used_mb,
                    available_mb=available_mb,
                    total_mb=total_mb,
                    percent_used=percent_used,
                    process_mb=process_mb,
                )
        except (OSError, KeyError):
            return self._get_stats_estimate()

    def _get_stats_estimate(self) -> MemoryStats:
        """Provide conservative estimates when actual stats unavailable."""
        # Conservative estimate: assume 50% memory used
        # This is safer than assuming low usage
        return MemoryStats(
            used_mb=4096.0,  # Assume 4GB used
            available_mb=4096.0,  # Assume 4GB available
            total_mb=8192.0,  # Assume 8GB total
            percent_used=0.5,
            process_mb=256.0,  # Assume 256MB process
        )

    def is_under_pressure(self) -> bool:
        """Check if system is under memory pressure.

        Returns:
            True if memory usage exceeds the configured threshold.

        """
        if not self.config.enable_adaptive_sizing:
            return False

        stats = self.get_memory_stats()
        return stats.percent_used >= self.config.memory_pressure_threshold

    def get_recommended_batch_size(self, current_batch_size: int) -> int:
        """Get recommended batch size based on memory pressure.

        Implements adaptive batch sizing:
        - If under memory pressure, reduces batch size by 50%
        - If pressure persists for 3+ checks, reduces more aggressively
        - Never goes below min_batch_size
        - Gradually increases batch size when pressure is relieved

        Args:
            current_batch_size: Current batch size.

        Returns:
            Recommended batch size (may be smaller if under pressure).

        """
        if not self.config.enable_adaptive_sizing:
            return current_batch_size

        stats = self.get_memory_stats()
        is_pressure = stats.percent_used >= self.config.memory_pressure_threshold

        if is_pressure:
            self._consecutive_pressure_count += 1
            reduction_factor = self._get_reduction_factor()
            new_size = max(
                int(current_batch_size * reduction_factor),
                self.config.min_batch_size,
            )

            if self.logger and new_size < current_batch_size:
                self.logger.warning(
                    "Memory pressure detected, reducing batch size",
                    current_batch_size=current_batch_size,
                    new_batch_size=new_size,
                    memory_percent_used=round(stats.percent_used * 100, 1),
                    consecutive_pressure_count=self._consecutive_pressure_count,
                )

            self._last_batch_size = new_size
            return new_size

        # Pressure relieved - consider gradual recovery
        self._consecutive_pressure_count = 0

        # If we previously reduced, try to recover gradually
        if current_batch_size < self._last_batch_size:
            recovery_size = min(
                int(current_batch_size * 1.25),  # Increase by 25%
                self._last_batch_size,
            )
            if self.logger:
                self.logger.debug(
                    "Memory pressure relieved, increasing batch size",
                    current_batch_size=current_batch_size,
                    new_batch_size=recovery_size,
                    memory_percent_used=round(stats.percent_used * 100, 1),
                )
            return recovery_size

        self._last_batch_size = current_batch_size
        return current_batch_size

    def _get_reduction_factor(self) -> float:
        """Get batch size reduction factor based on pressure duration.

        Returns:
            Reduction factor (0.25 to 0.5).

        """
        if self._consecutive_pressure_count >= 5:
            return 0.25  # Aggressive: reduce to 25%
        if self._consecutive_pressure_count >= 3:
            return 0.35  # Moderate-aggressive: reduce to 35%
        return 0.5  # Standard: reduce by half

    def estimate_batch_memory_mb(
        self, record_count: int, avg_record_size_bytes: int = 1024
    ) -> float:
        """Estimate memory usage for a batch.

        Args:
            record_count: Number of records in batch.
            avg_record_size_bytes: Average size per record in bytes.

        Returns:
            Estimated memory usage in MB.

        """
        # Factor in transformation overhead (2x for in-memory copies)
        overhead_factor = 2.5
        return (record_count * avg_record_size_bytes * overhead_factor) / (1024 * 1024)

    def calculate_max_batch_size(self, avg_record_size_bytes: int = 1024) -> int:
        """Calculate maximum batch size based on available memory.

        Args:
            avg_record_size_bytes: Average size per record in bytes.

        Returns:
            Maximum recommended batch size.

        """
        max_memory_bytes = self.config.max_batch_memory_mb * 1024 * 1024
        overhead_factor = 2.5

        max_records = int(max_memory_bytes / (avg_record_size_bytes * overhead_factor))
        return max(max_records, self.config.min_batch_size)


__all__ = ["MemoryConfig", "MemoryMonitor", "MemoryStats"]

================================================================================
File: pipeline_services.py
Path: core\pipeline_services.py
================================================================================
"""Pipeline services - injected dependencies.

Part of BasePipeline decomposition (ADR-0005).
Separates I/O port dependencies from pipeline logic.

Logger and Metrics are formalized as ports (ADR-005).
DQ report services added for optional DQ report generation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Self

from bioetl.domain.ports import (
    CheckpointPort,
    DataSourcePort,
    DQMonitorPort,
    LockPort,
    LoggerPort,
    MetricsPort,
    QuarantinePort,
    StoragePort,
    TracingPort,
)

if TYPE_CHECKING:
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.ports import (
        BronzeDQAnalyzerPort,
        DQReportWriterPort,
        GoldDQAnalyzerPort,
        SilverDQAnalyzerPort,
    )


@dataclass(frozen=True)
class PipelineServices:
    """Injected dependencies for pipeline execution.

    All fields are Protocol-typed for testability and flexibility.
    This enables easy mocking in tests and swapping implementations.

    Frozen dataclass ensures services can't be accidentally replaced
    during pipeline execution.

    Attributes:
        data_source: Port for fetching data from external sources.
        storage: Port for writing to Bronze/Silver/Gold layers.
        lock: Port for distributed locking coordination.
        checkpoint: Port for pipeline state persistence.
        quarantine: Port for failed record isolation.
        metrics: Port for observability metrics collection.
        tracing: Port for distributed tracing.
        logger: Structured logger for pipeline events.
        dq_monitor: Optional data quality monitor for anomaly detection.
        bronze_dq_analyzer: Optional Bronze layer DQ analyzer for report generation.
        silver_dq_analyzer: Optional Silver layer DQ analyzer for report generation.
        gold_dq_analyzer: Optional Gold layer DQ analyzer for report generation.
        dq_report_writer: Optional DQ report writer for persisting reports.
        dq_report_service: Optional orchestration service for DQ reports.

    Example:
        >>> services = PipelineServices(
        ...     data_source=chembl_client,
        ...     storage=delta_storage,
        ...     lock=memory_lock,
        ...     checkpoint=local_checkpoint,
        ...     quarantine=unified_quarantine,
        ...     metrics=prometheus_metrics,
        ...     logger=logger,
        ... )

    """

    data_source: DataSourcePort
    storage: StoragePort
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics: MetricsPort
    tracing: TracingPort
    logger: LoggerPort
    dq_monitor: DQMonitorPort | None = None

    # DQ Report services (optional, created only if any layer has dq_report enabled)
    bronze_dq_analyzer: BronzeDQAnalyzerPort | None = None
    silver_dq_analyzer: SilverDQAnalyzerPort | None = None
    gold_dq_analyzer: GoldDQAnalyzerPort | None = None
    dq_report_writer: DQReportWriterPort | None = None
    dq_report_service: DQReportService | None = None

    def __post_init__(self) -> None:
        """Validate that all services are provided."""
        # Validation is implicit - dataclass requires all non-default fields
        # Runtime checks happen via Protocol structural typing

    async def __aenter__(self) -> Self:
        """Enter the async context manager, initializing services."""
        await self.data_source.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager, closing services."""
        await self.aclose()

    async def aclose(self) -> None:
        """Gracefully close all I/O resources and observability."""
        self.logger.info("Closing pipeline services...", stage="cleanup")

        # Close async I/O services
        results = await asyncio.gather(
            self.data_source.aclose(),
            self.storage.aclose(),
            self.lock.aclose(),
            self.checkpoint.aclose(),
            self.quarantine.aclose(),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                self.logger.error(
                    "Error during service shutdown", stage="cleanup", error=result
                )

        # Close observability (sync, best-effort)
        self._close_observability()

        self.logger.info("Pipeline services closed.", stage="cleanup")

    def _close_observability(self) -> None:
        """Close metrics and tracing resources (sync, idempotent)."""
        try:
            self.metrics.close()
        except Exception as e:
            self.logger.warning("Error closing metrics", stage="cleanup", error=str(e))

        try:
            self.tracing.close()
        except Exception as e:
            self.logger.warning("Error closing tracing", stage="cleanup", error=str(e))


__all__ = ["PipelineServices"]

================================================================================
File: postrun_service.py
Path: core\postrun_service.py
================================================================================
"""Postrun Service for post-execution operations.

Application Service that handles post-pipeline execution tasks:
- Data quality checks (delegated to DataQualityService)
- DQ report generation (delegated to DQReportService)
- VACUUM operations (delegated to MedallionLifecycleService)
- Tracer cleanup

Extracted from PipelineRunner to follow Single Responsibility Principle.
DQ logic further extracted to DataQualityService (SRP refactoring).
DQ report generation added for detailed data quality analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.medallion_types import VacuumResult
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

if TYPE_CHECKING:
    from bioetl.application.services.dq_report_service import (
        DQReportContext,
        DQReportResult,
        DQReportService,
    )
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        LoggerPort,
        MetricsPort,
        SilverDQConfigPort,
        TracingPort,
    )


@runtime_checkable
class ExecutorMetricsProtocol(Protocol):
    """Protocol for executors providing batch metrics.

    Both PipelineExecutor and BatchExecutor implement this protocol.
    """

    records_fetched: int
    records_bronze: int
    records_silver: int
    records_gold: int
    records_quarantined: int


@dataclass(frozen=True, slots=True)
class PostrunResult:
    """Combined result of all post-run operations.

    Attributes:
        dq: Data quality evaluation result.
        dq_reports: DQ report generation result (optional).
        vacuum: VACUUM operation result.
    """

    dq: DQResult
    dq_reports: DQReportResult | None
    vacuum: VacuumResult


class PostrunService:
    """Handles post-execution operations.

    Responsibilities:
    - Orchestrating DQ checks via DataQualityService
    - DQ report generation via DQReportService (optional)
    - VACUUM operations via MedallionLifecycleService
    - Tracer cleanup

    Attributes:
        _config: Pipeline configuration.
        _runtime: Runtime configuration.
        _dq_service: Data quality service for DQ checks.
        _lifecycle_service: Medallion lifecycle service for VACUUM.
        _metrics: Optional metrics port.
        _logger: Structured logger.
        _dq_report_service: Optional DQ report service for report generation.
        _bronze_dq_config: Optional Bronze DQ report configuration.
        _silver_dq_config: Optional Silver DQ report configuration.
        _gold_dq_config: Optional Gold DQ report configuration.
    """

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        dq_service: DataQualityService,
        lifecycle_service: MedallionLifecycleService,
        metrics: MetricsPort | None,
        logger: LoggerPort,
        # DQ Report parameters (optional)
        dq_report_service: DQReportService | None = None,
        bronze_dq_config: BronzeDQConfigPort | None = None,
        silver_dq_config: SilverDQConfigPort | None = None,
        gold_dq_config: GoldDQConfigPort | None = None,
    ) -> None:
        """Initialize postrun service.

        Args:
            config: Pipeline configuration.
            runtime: Runtime configuration.
            dq_service: Data quality service for DQ checks.
            lifecycle_service: Medallion lifecycle service for VACUUM.
            metrics: Optional metrics port.
            logger: Structured logger.
            dq_report_service: Optional DQ report service for report generation.
            bronze_dq_config: Optional Bronze DQ report configuration.
            silver_dq_config: Optional Silver DQ report configuration.
            gold_dq_config: Optional Gold DQ report configuration.
        """
        self._config = config
        self._runtime = runtime
        self._dq_service = dq_service
        self._lifecycle_service = lifecycle_service
        self._metrics = metrics
        self._logger = logger
        # DQ Report services
        self._dq_report_service = dq_report_service
        self._bronze_dq_config = bronze_dq_config
        self._silver_dq_config = silver_dq_config
        self._gold_dq_config = gold_dq_config

    async def run(
        self,
        executor: ExecutorMetricsProtocol,
        dq_context: DQReportContext | None = None,
    ) -> PostrunResult:
        """Run all post-execution operations.

        Performs DQ checks, DQ report generation, and VACUUM in sequence.

        Args:
            executor: Pipeline executor with batch metrics.
            dq_context: Optional DQ report context with data and metadata.

        Returns:
            PostrunResult with DQ, DQ reports, and VACUUM results.

        Raises:
            DataQualityThresholdError: If error rate exceeds hard threshold.
        """
        dq_result = await self.run_dq_checks(executor)
        dq_reports = await self._generate_dq_reports(dq_context)
        vacuum_result = await self.run_vacuum_if_enabled()
        return PostrunResult(dq=dq_result, dq_reports=dq_reports, vacuum=vacuum_result)

    async def run_dq_checks(self, executor: ExecutorMetricsProtocol) -> DQResult:
        """Check data quality metrics and report anomalies.

        Delegates to DataQualityService for threshold checks and anomaly detection.

        Args:
            executor: Pipeline executor with batch metrics.

        Returns:
            DQResult with evaluation results.

        Raises:
            DataQualityThresholdError: If error rate exceeds hard threshold.
        """
        batch_metrics = self._collect_batch_metrics(executor)
        return await self._dq_service.evaluate(batch_metrics)

    async def run_vacuum_if_enabled(self) -> VacuumResult:
        """Run VACUUM on Silver and Gold tables if enabled.

        Delegates to MedallionLifecycleService.finalize_run() which handles:
        - Checking if vacuum is enabled
        - Skipping in dry-run mode
        - Vacuuming both Silver and Gold tables
        - Metrics emission

        Returns:
            VacuumResult with operation details.
        """
        return await self._lifecycle_service.finalize_run(
            config=self._config,
            runtime=self._runtime,
            metrics=self._metrics,
        )

    async def cleanup(self, tracer: TracingPort | None) -> None:
        """Cleanup all resources including observability.

        Ensures tracer spans are flushed before shutdown (O3).
        Handles errors gracefully to avoid masking pipeline exceptions.

        Args:
            tracer: Optional tracing port to close.
        """
        if tracer is not None:
            try:
                tracer.close()
                self._logger.debug("Tracer closed successfully")
            except Exception as e:
                self._logger.warning(
                    "Failed to close tracer",
                    error=str(e),
                )

    async def _generate_dq_reports(
        self,
        context: DQReportContext | None,
    ) -> DQReportResult | None:
        """Generate DQ reports if enabled.

        Delegates to DQReportService for generating Bronze, Silver, and Gold
        DQ reports based on configuration.

        Args:
            context: DQ report context with data and metadata.

        Returns:
            DQReportResult with paths to generated reports, or None if:
            - DQ report service is not available
            - No context provided
            - No reports are enabled in configuration
        """
        if self._dq_report_service is None:
            return None

        if context is None:
            self._logger.debug(
                "dq_report_skipped",
                reason="no context provided",
            )
            return None

        try:
            result = await self._dq_report_service.generate_reports(
                context=context,
                bronze_config=self._bronze_dq_config,
                silver_config=self._silver_dq_config,
                gold_config=self._gold_dq_config,
            )

            if result.any_generated:
                self._logger.info(
                    "dq_reports_completed",
                    reports_count=result.reports_count,
                    bronze_enabled=result.bronze_enabled,
                    silver_enabled=result.silver_enabled,
                    gold_enabled=result.gold_enabled,
                )

            return result

        except Exception as e:
            # Log error but don't fail the pipeline
            self._logger.error(
                "dq_report_generation_failed",
                error=str(e),
            )
            return None

    def _collect_batch_metrics(
        self, executor: ExecutorMetricsProtocol
    ) -> dict[str, float]:
        """Collect batch metrics from executor.

        Args:
            executor: Pipeline executor with batch metrics.

        Returns:
            Dictionary of metric names to values.
        """
        total_records = max(1, executor.records_fetched)
        return {
            "record_count": float(executor.records_fetched),
            "bronze_count": float(executor.records_bronze),
            "silver_count": float(executor.records_silver),
            "gold_count": float(executor.records_gold),
            "quarantined_count": float(executor.records_quarantined),
            "error_rate": executor.records_quarantined / total_records,
            "silver_yield": executor.records_silver / total_records,
            "gold_yield": executor.records_gold / total_records,
        }


__all__ = [
    "DQEvaluationStatus",
    "DQResult",
    "ExecutorMetricsProtocol",
    "PostrunResult",
    "PostrunService",
    "VacuumResult",
]

================================================================================
File: preflight_service.py
Path: core\preflight_service.py
================================================================================
"""Preflight Service for infrastructure validation.

Application Service that validates infrastructure health before pipeline execution.
Self-contained module with all validation logic integrated.

All helper components are internal:
- _HealthAggregator: handles health check aggregation
- _MedallionConfigValidator: handles medallion-specific validation
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from bioetl.domain.exceptions import InfrastructureError, PolicyViolationError
from bioetl.domain.medallion import Layer, MedallionPolicy, WriteMode, WriteModePolicy
from bioetl.domain.types import (
    ComponentHealthResult,
    ConfigValidationError,
    HealthReport,
    HealthStatus,
    PreflightReport,
    RunType,
)

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        HealthCheckResult,
        HealthMonitorPort,
        LoggerPort,
        MetricsPort,
    )


# =============================================================================
# Private Helper: Health Aggregator
# =============================================================================


class _HealthAggregator:
    """Aggregates health checks for pipeline infrastructure components.

    Internal helper for PreflightService. Performs parallel health validation
    of storage and data source before pipeline execution.

    Integrates with ProviderHealthMonitor for:
    - Centralized health state tracking
    - P2 alerting on UNHEALTHY status
    - Adaptive client configuration based on health
    """

    METRIC_HEALTH_STATUS = "health_check_status"
    METRIC_HEALTH_DURATION = "health_check_duration_seconds"
    METRIC_HEALTH_LATENCY = "health_check_latency_ms"

    def __init__(
        self,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
        health_monitor: HealthMonitorPort | None = None,
    ) -> None:
        """Initialize _HealthAggregator.

        Args:
            metrics: Optional metrics port for recording health check metrics.
            logger: Optional logger for health check status reporting.
            health_monitor: Optional HealthMonitorPort for centralized
                health state tracking and alerting.

        """
        self._metrics = metrics
        self._logger = logger
        self._health_monitor = health_monitor

    async def check_all(self, services: PipelineServices) -> HealthReport:
        """Check health of all critical infrastructure components.

        Performs parallel health checks on:
        - Storage (Bronze/Silver/Gold layers)
        - Data source (external API connectivity)

        Args:
            services: Pipeline services containing storage and data_source.

        Returns:
            HealthReport with aggregated results from all components.

        """
        results = await asyncio.gather(
            self._check_storage(services),
            self._check_data_source(services),
            return_exceptions=True,
        )

        component_results: list[ComponentHealthResult] = []
        for result in results:
            if isinstance(result, BaseException):
                component_results.append(
                    ComponentHealthResult(
                        component="unknown",
                        status=HealthStatus.UNHEALTHY,
                        duration_seconds=0.0,
                        error_message=str(result),
                    )
                )
            else:
                component_results.append(result)

        report = HealthReport(results=component_results)
        self._log_report(report)
        return report

    async def _check_storage(self, services: PipelineServices) -> ComponentHealthResult:
        """Check storage health."""
        component = "storage"
        start_time = time.perf_counter()

        try:
            status = await services.storage.health_check()
            duration = time.perf_counter() - start_time
            result = ComponentHealthResult(
                component=component,
                status=status,
                duration_seconds=duration,
            )
        except Exception as e:
            duration = time.perf_counter() - start_time
            result = ComponentHealthResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                duration_seconds=duration,
                error_message=str(e),
            )

        self._record_metrics(component, result)
        return result

    async def _check_data_source(
        self, services: PipelineServices
    ) -> ComponentHealthResult:
        """Check data source health.

        Uses enhanced check_health() method when available for detailed
        metrics including latency.
        """
        component = "data_source"
        start_time = time.perf_counter()
        health_result: HealthCheckResult | None = None

        try:
            if hasattr(services.data_source, "check_health"):
                health_result = await services.data_source.check_health()
                assert health_result is not None  # check_health always returns result
                status = health_result.status
                duration = time.perf_counter() - start_time

                if self._health_monitor is not None:
                    self._health_monitor.update_from_health_check_result(
                        health_result, self._logger
                    )

                result = ComponentHealthResult(
                    component=component,
                    status=status,
                    duration_seconds=duration,
                    error_message=health_result.last_error,
                )
            else:
                status = await services.data_source.health_check()
                duration = time.perf_counter() - start_time
                result = ComponentHealthResult(
                    component=component,
                    status=status,
                    duration_seconds=duration,
                )
        except Exception as e:
            duration = time.perf_counter() - start_time
            result = ComponentHealthResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                duration_seconds=duration,
                error_message=str(e),
            )

        self._record_metrics(component, result, health_result)
        return result

    def _record_metrics(
        self,
        component: str,
        result: ComponentHealthResult,
        health_result: HealthCheckResult | None = None,
    ) -> None:
        """Record health check metrics."""
        if self._metrics is None:
            return

        labels = {"component": component}

        self._metrics.set_gauge(
            self.METRIC_HEALTH_STATUS,
            float(result.status.to_metric_value()),
            labels,
        )

        self._metrics.observe_histogram(
            self.METRIC_HEALTH_DURATION,
            result.duration_seconds,
            labels,
        )

        if health_result is not None:
            provider_labels = {"provider": health_result.provider}
            self._metrics.observe_histogram(
                self.METRIC_HEALTH_LATENCY,
                health_result.latency_ms,
                provider_labels,
            )

    def _log_report(self, report: HealthReport) -> None:
        """Log health check report."""
        if self._logger is None:
            return

        for result in report.results:
            log_extra = {
                "component": result.component,
                "status": result.status.value,
                "duration_seconds": round(result.duration_seconds, 4),
            }

            if result.error_message:
                log_extra["error"] = result.error_message

            if result.status == HealthStatus.HEALTHY:
                self._logger.info("Health check passed", **log_extra)
            elif result.status == HealthStatus.DEGRADED:
                self._logger.warning("Health check degraded", **log_extra)
            else:
                self._logger.error("Health check failed", **log_extra)

    def assert_healthy(self, report: HealthReport) -> None:
        """Assert that all critical components are healthy.

        Raises InfrastructureError if any component is UNHEALTHY.

        Args:
            report: Health report to validate.

        Raises:
            InfrastructureError: If any component is UNHEALTHY.

        """
        failures = report.get_failures()
        if not failures:
            return

        failed_components = [f.component for f in failures]
        error_messages = [
            f"{f.component}: {f.error_message or 'check failed'}" for f in failures
        ]

        raise InfrastructureError(
            f"Health check failed for: {', '.join(failed_components)}. "
            f"Details: {'; '.join(error_messages)}"
        )


# =============================================================================
# Private Helper: Medallion Config Validator
# =============================================================================


class _MedallionConfigValidator:
    """Validates Medallion architecture configuration.

    Internal helper for PreflightService. Validates:
    - Silver and Gold layer formats
    - Path uniqueness across layers
    - MedallionPolicy consistency with RunType
    - Write modes against layer policies
    """

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerPort,
    ) -> None:
        """Initialize medallion config validator.

        Args:
            config: Pipeline configuration.
            logger: Structured logger.

        """
        self._config = config
        self._logger = logger

    def validate_medallion_config(
        self,
        runtime: RuntimeConfig,
        bronze_path: str,
        silver_path: str,
        gold_path: str,
        silver_format: str | None = None,
        gold_format: str | None = None,
    ) -> list[ConfigValidationError]:
        """Validate Medallion architecture invariants.

        Args:
            runtime: Runtime configuration with run type.
            bronze_path: Base path for Bronze layer storage.
            silver_path: Base path for Silver layer storage.
            gold_path: Base path for Gold layer storage.
            silver_format: Format of Silver layer.
            gold_format: Format of Gold layer.

        Returns:
            List of ConfigValidationError objects. Empty list means validation passed.

        """
        errors: list[ConfigValidationError] = []

        errors.extend(self._validate_layer_formats(silver_format, gold_format))
        errors.extend(
            self._validate_path_uniqueness(bronze_path, silver_path, gold_path)
        )

        policy = MedallionPolicy.for_run_type(runtime.run_type)
        errors.extend(
            self._validate_medallion_policy_consistency(runtime.run_type, policy)
        )

        self._log_medallion_validation_result(errors, runtime)
        return errors

    def validate_write_modes(self) -> list[ConfigValidationError]:
        """Validate that config write modes are allowed by medallion policy.

        Returns:
            List of ConfigValidationError if write modes violate policy.

        """
        errors: list[ConfigValidationError] = []
        write_mode_policy = WriteModePolicy()

        # Validate Silver write mode
        silver_mode = self._config.write_mode
        try:
            write_mode_policy.validate(Layer.SILVER, WriteMode(silver_mode))
        except (PolicyViolationError, ValueError):
            allowed = WriteModePolicy.ALLOWED_MODES[Layer.SILVER]
            allowed_names = ", ".join(
                m.value for m in sorted(allowed, key=lambda x: x.value)
            )
            errors.append(
                ConfigValidationError(
                    field="write_mode",
                    expected=f"one of: {allowed_names}",
                    actual=silver_mode,
                    rule="RULES §2.1: Silver layer allowed modes",
                )
            )

        # Validate Gold write mode
        gold_mode = self._config.gold_write_mode
        effective_gold_mode = "merge" if gold_mode == "scd2" else gold_mode
        try:
            write_mode_policy.validate(Layer.GOLD, WriteMode(effective_gold_mode))
        except (PolicyViolationError, ValueError):
            allowed = WriteModePolicy.ALLOWED_MODES[Layer.GOLD]
            allowed_names = ", ".join(
                m.value for m in sorted(allowed, key=lambda x: x.value)
            )
            errors.append(
                ConfigValidationError(
                    field="gold_write_mode",
                    expected=f"one of: {allowed_names}, scd2",
                    actual=gold_mode,
                    rule="RULES §2.1: Gold layer allowed modes",
                )
            )

        # Log validation results
        if errors:
            self._logger.warning(
                "Write mode validation found issues",
                extra={
                    "error_count": len(errors),
                    "errors": [{"field": e.field, "rule": e.rule} for e in errors],
                },
            )
        else:
            self._logger.debug(
                "Write mode validation passed",
                extra={
                    "silver_mode": silver_mode,
                    "gold_mode": gold_mode,
                },
            )

        return errors

    def _validate_layer_formats(
        self, silver_format: str | None, gold_format: str | None
    ) -> list[ConfigValidationError]:
        """Validate Silver and Gold layer formats."""
        errors: list[ConfigValidationError] = []

        if silver_format is not None and silver_format != "delta":
            errors.append(
                ConfigValidationError(
                    field="sink.silver.format",
                    expected="delta",
                    actual=silver_format,
                    rule="RULES §2.1: Silver MUST use Delta Lake",
                )
            )

        if gold_format is not None and gold_format != "delta":
            errors.append(
                ConfigValidationError(
                    field="sink.gold.format",
                    expected="delta",
                    actual=gold_format,
                    rule="RULES §2.1: Gold MUST use Delta Lake",
                )
            )

        return errors

    def _validate_path_uniqueness(
        self, bronze_path: str, silver_path: str, gold_path: str
    ) -> list[ConfigValidationError]:
        """Validate that layer paths are unique."""
        errors: list[ConfigValidationError] = []
        paths = {bronze_path, silver_path, gold_path}

        if len(paths) >= 3:
            return errors

        if bronze_path == silver_path:
            errors.append(
                ConfigValidationError(
                    field="storage.paths",
                    expected="unique paths for each layer",
                    actual=f"bronze_path == silver_path ({bronze_path})",
                    rule="Medallion Architecture: layers MUST have distinct paths",
                )
            )
        if silver_path == gold_path:
            errors.append(
                ConfigValidationError(
                    field="storage.paths",
                    expected="unique paths for each layer",
                    actual=f"silver_path == gold_path ({silver_path})",
                    rule="Medallion Architecture: layers MUST have distinct paths",
                )
            )
        if bronze_path == gold_path:
            errors.append(
                ConfigValidationError(
                    field="storage.paths",
                    expected="unique paths for each layer",
                    actual=f"bronze_path == gold_path ({bronze_path})",
                    rule="Medallion Architecture: layers MUST have distinct paths",
                )
            )

        return errors

    def _validate_medallion_policy_consistency(
        self,
        run_type: RunType,
        policy: MedallionPolicy,
    ) -> list[ConfigValidationError]:
        """Validate that MedallionPolicy is consistent with RunType."""
        errors: list[ConfigValidationError] = []

        if run_type in (RunType.REBUILD, RunType.BACKFILL):
            if not policy.should_clear_silver:
                errors.append(
                    ConfigValidationError(
                        field="medallion_policy.should_clear_silver",
                        expected="True",
                        actual="False",
                        rule=f"RULES §2.1: {run_type.value} MUST clear Silver layer",
                    )
                )
            if not policy.should_clear_gold:
                errors.append(
                    ConfigValidationError(
                        field="medallion_policy.should_clear_gold",
                        expected="True",
                        actual="False",
                        rule=f"RULES §2.1: {run_type.value} MUST clear Gold layer",
                    )
                )
        elif run_type == RunType.INCREMENTAL:
            if policy.should_clear_silver:
                errors.append(
                    ConfigValidationError(
                        field="medallion_policy.should_clear_silver",
                        expected="False",
                        actual="True",
                        rule="RULES §2.1: INCREMENTAL MUST NOT clear Silver layer",
                    )
                )
            if policy.should_clear_gold:
                errors.append(
                    ConfigValidationError(
                        field="medallion_policy.should_clear_gold",
                        expected="False",
                        actual="True",
                        rule="RULES §2.1: INCREMENTAL MUST NOT clear Gold layer",
                    )
                )

        return errors

    def _log_medallion_validation_result(
        self, errors: list[ConfigValidationError], runtime: RuntimeConfig
    ) -> None:
        """Log medallion validation results."""
        if errors:
            self._logger.warning(
                "Medallion config validation found issues",
                extra={
                    "error_count": len(errors),
                    "errors": [{"field": e.field, "rule": e.rule} for e in errors],
                    "strict_mode": runtime.strict_validation,
                },
            )
        else:
            self._logger.debug(
                "Medallion config validation passed",
                extra={"run_type": runtime.run_type.value},
            )


# =============================================================================
# Main Service: PreflightService
# =============================================================================


class PreflightService:
    """Validates infrastructure health before pipeline execution.

    Self-contained service that performs all pre-flight validation:
    - Infrastructure health checks (storage, data source)
    - Medallion configuration validation
    - Write mode policy validation

    Attributes:
        _config: Pipeline configuration.
        _context: Pipeline execution context.
        _logger: Structured logger.
        _metrics: Metrics port for recording.

    """

    def __init__(
        self,
        config: PipelineConfig,
        context: PipelineContext,
        logger: LoggerPort,
        metrics: MetricsPort,
    ) -> None:
        """Initialize preflight service.

        Args:
            config: Pipeline configuration.
            context: Pipeline execution context.
            logger: Structured logger.
            metrics: Metrics port for recording health check metrics.

        """
        self._config = config
        self._context = context
        self._logger = logger
        self._metrics = metrics
        self._health_aggregator = _HealthAggregator(
            metrics=metrics,
            logger=logger,
        )
        self._medallion_validator = _MedallionConfigValidator(
            config=config,
            logger=logger,
        )

    async def validate_infrastructure(self, services: PipelineServices) -> HealthReport:
        """Validate infrastructure health before pipeline execution.

        Performs health checks on storage and data source components.
        Records metrics per Unified Observability Contract.

        Args:
            services: Pipeline services containing storage and data source.

        Returns:
            HealthReport with aggregated results.

        Raises:
            InfrastructureError: If critical components are unhealthy.

        """
        self._logger.info(
            "Validating infrastructure health",
            extra={"stage": "health_check"},
        )

        start_time = time.perf_counter()
        report = await self._health_aggregator.check_all(services)
        duration = time.perf_counter() - start_time

        self._record_health_check_metrics(report, duration)

        self._logger.info(
            "Infrastructure health check completed",
            extra={
                "stage": "health_check",
                "overall_status": report.overall_status.value,
                "is_healthy": report.is_healthy,
                "components_checked": len(report.results),
                "duration_seconds": round(duration, 4),
            },
        )

        self._health_aggregator.assert_healthy(report)
        return report

    def _record_health_check_metrics(
        self,
        report: Any,
        duration: float,
    ) -> None:
        """Record health-check metrics per Unified Observability Contract."""
        pipeline = self._config.pipeline_name
        run_id = str(self._context.run_id)

        for result in report.results:
            passed = 1.0 if result.status == HealthStatus.HEALTHY else 0.0
            self._metrics.set_gauge(
                "pipeline_health_check_passed",
                passed,
                {"pipeline": pipeline, "component": result.component},
            )

        validated = 1.0 if report.is_healthy else 0.0
        self._metrics.set_gauge(
            "infrastructure_validated",
            validated,
            {"pipeline": pipeline, "run_id": run_id},
        )

        self._metrics.observe_histogram(
            "health_check_duration_seconds",
            duration,
            {"pipeline": pipeline},
        )

    def validate_medallion_config(
        self,
        runtime: RuntimeConfig,
        bronze_path: str,
        silver_path: str,
        gold_path: str,
        silver_format: str | None = None,
        gold_format: str | None = None,
    ) -> list[ConfigValidationError]:
        """Validate Medallion architecture invariants before pipeline execution.

        Args:
            runtime: Runtime configuration with run type.
            bronze_path: Base path for Bronze layer storage.
            silver_path: Base path for Silver layer storage.
            gold_path: Base path for Gold layer storage.
            silver_format: Format of Silver layer.
            gold_format: Format of Gold layer.

        Returns:
            List of ConfigValidationError objects. Empty list means validation passed.

        """
        return self._medallion_validator.validate_medallion_config(
            runtime=runtime,
            bronze_path=bronze_path,
            silver_path=silver_path,
            gold_path=gold_path,
            silver_format=silver_format,
            gold_format=gold_format,
        )

    def validate_write_modes(self) -> list[ConfigValidationError]:
        """Validate that config write modes are allowed by medallion policy.

        Returns:
            List of ConfigValidationError if write modes violate policy.

        """
        return self._medallion_validator.validate_write_modes()

    async def validate_preflight(
        self,
        services: PipelineServices,
        runtime: RuntimeConfig,
        bronze_path: str,
        silver_path: str,
        gold_path: str,
        silver_format: str | None = None,
        gold_format: str | None = None,
    ) -> PreflightReport:
        """Execute complete preflight validation.

        Performs all preflight checks:
        1. Infrastructure health validation
        2. Medallion config validation
        3. Write mode policy validation

        Args:
            services: Pipeline services for health checks.
            runtime: Runtime configuration.
            bronze_path: Base path for Bronze layer storage.
            silver_path: Base path for Silver layer storage.
            gold_path: Base path for Gold layer storage.
            silver_format: Format of Silver layer.
            gold_format: Format of Gold layer.

        Returns:
            PreflightReport with aggregated validation results.

        Raises:
            InfrastructureError: If critical infrastructure is unhealthy.
            ValueError: If medallion policy is invalid and strict_validation
                is enabled.

        """
        self._logger.info(
            "Starting preflight validation",
            extra={"stage": "preflight", "strict_mode": runtime.strict_validation},
        )

        # 1. Validate infrastructure health
        health_report = await self.validate_infrastructure(services)

        # 2. Validate medallion config
        config_errors = self.validate_medallion_config(
            runtime=runtime,
            bronze_path=bronze_path,
            silver_path=silver_path,
            gold_path=gold_path,
            silver_format=silver_format,
            gold_format=gold_format,
        )

        # 3. Validate write modes against policy
        write_mode_errors = self.validate_write_modes()
        config_errors.extend(write_mode_errors)

        # Determine if medallion policy is valid
        medallion_policy_valid = len(config_errors) == 0

        # Create preflight report
        report = PreflightReport(
            health_report=health_report,
            medallion_policy_valid=medallion_policy_valid,
            config_errors=config_errors,
        )

        self._record_preflight_metrics(report)

        self._logger.info(
            "Preflight validation completed",
            extra={
                "stage": "preflight",
                "medallion_policy_valid": medallion_policy_valid,
                "config_error_count": len(config_errors),
                "is_healthy": health_report.is_healthy,
                "should_block": report.should_block_startup,
            },
        )

        if report.should_block_startup and runtime.strict_validation:
            error_messages = [
                f"{e.field}: {e.actual} (expected: {e.expected})" for e in config_errors
            ]
            raise ValueError(
                f"Preflight validation failed (strict mode): {', '.join(error_messages)}"
            )

        return report

    def _record_preflight_metrics(self, report: PreflightReport) -> None:
        """Record preflight validation metrics."""
        pipeline = self._config.pipeline_name
        run_id = str(self._context.run_id)

        self._metrics.set_gauge(
            "preflight_medallion_policy_valid",
            1.0 if report.medallion_policy_valid else 0.0,
            {"pipeline": pipeline, "run_id": run_id},
        )

        self._metrics.set_gauge(
            "preflight_config_errors_total",
            float(len(report.config_errors)),
            {"pipeline": pipeline, "run_id": run_id},
        )


__all__ = ["PreflightService"]

================================================================================
File: protocols.py
Path: core\protocols.py
================================================================================
"""Callback protocols for the pipeline.

Defines Protocol classes for pipeline callbacks and transformer ports.
Implements RULES.md §1 (Domain Layer - Ports).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class TransformCallback(Protocol):
    """Bronze to Silver transformation callback."""

    def __call__(
        self, context: PipelineContext, record: dict[str, Any], index: int
    ) -> Awaitable[dict[str, Any] | None]:
        """Execute transformation."""
        ...


class GoldFilterCallback(Protocol):
    """Filter callback to determine if Silver record should go to Gold."""

    def __call__(self, context: PipelineContext, record: dict[str, Any]) -> bool:
        """Evaluate if record should be included in Gold layer."""
        ...


class GoldTransformCallback(Protocol):
    """Silver to Gold transformation callback.

    Removes JSON string fields and prepares record for Gold layer.
    """

    def __call__(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute transformation."""
        ...


class TransformerPort(Protocol):
    """Protocol defining the contract for Bronze → Silver transformers.

    All transformer implementations MUST implement this protocol.
    Enables polymorphism and testability through dependency injection.

    Implements RULES.md §2.8 (Bronze → Silver transformation).

    Example:
        >>> class MyTransformer:
        ...     async def transform(
        ...         self, context: PipelineContext, record: BronzeRecord, index: int
        ...     ) -> SilverRecord | None:
        ...         # Transform logic here
        ...         return silver_record

    """

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform a Bronze record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from data source.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if record should be skipped.

        Raises:
            ValueError: If record validation fails (handled by Template Method).

        """
        ...

================================================================================
File: publication_term_data_source.py
Path: core\publication_term_data_source.py
================================================================================
"""Publication Term Data Source wrapper.

Wraps a DataSourcePort to extract terms from ChEMBL publication records.
This is a derived entity pattern - publication_term entities are extracted
from the nested mesh_terms and keywords fields in publication records.

Architecture:
    ChEMBL API (document endpoint)
           ↓
    PublicationTermDataSource (wrapper)
      - fetch("publication_term") → wrapped.fetch("publication")
      - transforms each publication → yields term records
           ↓
    Pipeline receives term records

.. versionchanged:: 2.0.0
    Renamed from DocumentTermDataSource to PublicationTermDataSource (ADR-024).
.. versionchanged:: 2.1.0
    Changed entity types from document/document_term to publication/publication_term
    for naming consistency (ADR-024 naming unification).
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, Self

from bioetl.domain.ports import FilterableDataSourcePort

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import DataSourcePort
    from bioetl.domain.types import HealthStatus


class PublicationTermDataSource:
    """Wraps a DataSourcePort to extract terms from publication records.

    This is a Decorator pattern implementation that transforms the publication
    entity into derived publication_term entities. For each publication fetched
    from the wrapped adapter, multiple term records are extracted and yielded.

    Term types extracted:
    - MESH_HEADING: MeSH descriptor terms from mesh_terms array
    - MESH_QUALIFIER: MeSH qualifiers/subheadings from mesh_terms
    - KEYWORD: Author-provided keywords from keywords array

    The wrapper:
    1. Intercepts fetch("publication_term") calls
    2. Fetches publications from the wrapped adapter via fetch("publication")
    3. Extracts terms from each publication (1:M relationship)
    4. Yields individual term records with computed entity_id
    5. Delegates all other operations to the wrapped adapter

    Example:
        >>> wrapped = PublicationTermDataSource(chembl_adapter)
        >>> async with wrapped:
        ...     async for term in wrapped.fetch("publication_term", limit=100):
        ...         process_term(term)  # term has keys: term, term_type, etc.

    .. versionchanged:: 2.0.0
        Renamed from DocumentTermDataSource (ADR-024).
    """

    # Source entity type to fetch from wrapped adapter
    # Uses canonical "publication" name (ADR-024 naming unification)
    SOURCE_ENTITY_TYPE = "publication"
    # Target entity type this wrapper provides
    # Uses canonical "publication_term" name (ADR-024 naming unification)
    TARGET_ENTITY_TYPE = "publication_term"
    # Multiplier for publication limit estimation.
    # Not all publications have terms (mesh_terms/keywords may be empty).
    # Analysis shows ~20-30% of ChEMBL publications have terms.
    # Using 50x multiplier ensures we fetch enough publications to satisfy term limit.
    PUBLICATION_LIMIT_MULTIPLIER = 50

    def __init__(
        self,
        data_source: DataSourcePort,
    ) -> None:
        """Initialize publication term data source wrapper.

        Args:
            data_source: The underlying data source adapter to wrap (ChemblAdapter).

        """
        self._data_source = data_source

    @property
    def provider_name(self) -> str:
        """Provider name from the wrapped data source."""
        return self._data_source.provider_name

    async def __aenter__(self) -> Self:
        """Enter async context."""
        await self._data_source.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context."""
        await self._data_source.__aexit__(exc_type, exc_val, exc_tb)

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records, extracting terms if entity_type is publication_term.

        For publication_term entity type:
        - Fetches publications from wrapped adapter
        - Extracts terms from each publication
        - Yields individual term records

        For other entity types:
        - Delegates directly to wrapped adapter

        Args:
            entity_type: Type of entity to fetch.
            limit: Maximum number of records (for publication_term, limits total terms).
            query: Optional search query.
            filter_ids: Optional filter IDs (passed to wrapped adapter).
            filter_field: Optional filter field (passed to wrapped adapter).

        Yields:
            Records from the data source.

        """
        if entity_type == self.TARGET_ENTITY_TYPE:
            # Fetch publications and extract terms
            async for term in self._fetch_publication_terms(
                limit, filter_ids, filter_field
            ):
                yield term
        else:
            # Delegate to wrapped adapter for other entity types
            async for record in self._data_source.fetch(
                entity_type=entity_type,
                limit=limit,
                query=query,
                filter_ids=filter_ids,
                filter_field=filter_field,
            ):
                yield record

    async def _fetch_publication_terms(
        self,
        limit: int | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch publications and extract terms.

        Args:
            limit: Maximum number of term records to yield.
            filter_ids: Optional publication IDs to filter by.
            filter_field: Optional field for filtering (typically document_chembl_id).

        Yields:
            Term records extracted from publications.

        """
        term_count = 0

        # Estimate publication limit based on term limit.
        # We need to fetch more publications than terms because:
        # 1. Not all publications have terms (mesh_terms/keywords may be empty)
        # 2. Each publication yields variable number of terms (~2-5 on average)
        # Using multiplier ensures we fetch enough publications to satisfy term limit.
        publication_limit = limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None

        async for publication in self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            limit=publication_limit,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            document_chembl_id = publication.get("document_chembl_id")
            if not document_chembl_id:
                continue

            # Extract terms from publication
            terms = self._extract_terms_from_publication(
                publication, document_chembl_id
            )

            for term in terms:
                yield term
                term_count += 1

                if limit and term_count >= limit:
                    return

    def _extract_terms_from_publication(
        self,
        record: dict[str, Any],
        document_chembl_id: str,
    ) -> list[dict[str, Any]]:
        """Extract and flatten all terms from a Publication record.

        Extracts multiple term records from one publication (1:M relationship).

        Args:
            record: Raw publication record from ChEMBL API.
            document_chembl_id: Publication ChEMBL ID.

        Returns:
            List of term dictionaries.

        """
        terms: list[dict[str, Any]] = []

        # Extract MeSH terms
        raw_mesh_terms = record.get("mesh_terms")
        mesh_terms: list[Any] = (
            raw_mesh_terms if isinstance(raw_mesh_terms, list) else []
        )
        for mesh in mesh_terms:
            if not isinstance(mesh, dict):
                continue

            mesh_heading = mesh.get("mesh_heading")
            if mesh_heading:
                terms.append(
                    self._create_term_record(
                        document_chembl_id=document_chembl_id,
                        term=mesh_heading,
                        term_type="MESH_HEADING",
                        mesh_id=mesh.get("mesh_id"),
                        qualifier=mesh.get("mesh_qualifier"),
                    )
                )

            # Extract qualifier as separate term if present
            mesh_qualifier = mesh.get("mesh_qualifier")
            if mesh_qualifier:
                terms.append(
                    self._create_term_record(
                        document_chembl_id=document_chembl_id,
                        term=mesh_qualifier,
                        term_type="MESH_QUALIFIER",
                        mesh_id=mesh.get("mesh_id"),
                        qualifier=None,
                    )
                )

        # Extract keywords
        raw_keywords = record.get("keywords")
        keywords: list[Any] = raw_keywords if isinstance(raw_keywords, list) else []
        for keyword in keywords:
            if isinstance(keyword, str):
                stripped = keyword.strip()
                if stripped:  # Skip empty strings
                    terms.append(
                        self._create_term_record(
                            document_chembl_id=document_chembl_id,
                            term=stripped,
                            term_type="KEYWORD",
                            mesh_id=None,
                            qualifier=None,
                        )
                    )

        return terms

    def _create_term_record(
        self,
        document_chembl_id: str,
        term: str,
        term_type: str,
        mesh_id: str | None,
        qualifier: str | None,
    ) -> dict[str, Any]:
        """Create a single term record dictionary.

        Computes entity_id as SHA256 hash of composite key for deduplication.

        Args:
            document_chembl_id: Parent document ChEMBL ID.
            term: Term text.
            term_type: Term type (MESH_HEADING, MESH_QUALIFIER, KEYWORD).
            mesh_id: MeSH identifier if applicable.
            qualifier: MeSH qualifier if applicable.

        Returns:
            Dictionary of term fields including computed entity_id.

        """
        # Compute entity_id from composite key
        entity_id = self._compute_entity_id(document_chembl_id, term_type, term)

        return {
            "entity_id": entity_id,
            "document_chembl_id": document_chembl_id,
            "term": term.strip() if term else term,
            "term_type": term_type,
            "mesh_id": mesh_id,
            "qualifier": qualifier,
        }

    def _compute_entity_id(
        self,
        document_chembl_id: str,
        term_type: str,
        term: str,
    ) -> str:
        """Compute entity ID for a term based on composite key.

        Entity ID is SHA256 hash of: document_chembl_id:term_type:normalized_term

        Args:
            document_chembl_id: Document ChEMBL ID.
            term_type: Term type classification.
            term: Term text (will be normalized).

        Returns:
            Entity ID string (first 16 chars of SHA256 hex digest).

        """
        normalized_term = term.lower().strip() if term else ""
        composite = f"{document_chembl_id}:{term_type}:{normalized_term}"
        return hashlib.sha256(composite.encode()).hexdigest()[:16]

    async def health_check(self) -> HealthStatus:
        """Delegate health check to wrapped adapter."""
        return await self._data_source.health_check()

    async def aclose(self) -> None:
        """Delegate close to wrapped adapter."""
        await self._data_source.aclose()

    # FilterableDataSourcePort implementation (delegates to wrapped adapter)

    def _ensure_filterable(self, method_name: str) -> FilterableDataSourcePort:
        """Check that wrapped adapter implements FilterableDataSourcePort.

        Args:
            method_name: Name of the method being called (for error message).

        Returns:
            Wrapped adapter cast to FilterableDataSourcePort.

        Raises:
            TypeError: If wrapped adapter doesn't implement FilterableDataSourcePort.

        """
        if not isinstance(self._data_source, FilterableDataSourcePort):
            raise TypeError(
                f"Wrapped adapter {self._data_source.provider_name} does not implement "
                f"FilterableDataSourcePort. {method_name}() requires a filterable adapter."
            )
        return self._data_source

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch filtered records, extracting terms if entity_type is publication_term.

        Implements FilterableDataSourcePort.fetch_filtered().

        For publication_term entity type:
        - Delegates to wrapped adapter's fetch_filtered("publication", ...)
        - Extracts terms from each publication

        For other entity types:
        - Delegates directly to wrapped adapter

        Args:
            entity_type: Type of entity to fetch.
            filter_ids: List of IDs to filter by (document_chembl_id for publication_term).
            filter_field: Field name to filter on.
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records matching the filter criteria.

        """
        filterable = self._ensure_filterable("fetch_filtered")

        if entity_type == self.TARGET_ENTITY_TYPE:
            # Fetch publications and extract terms
            async for term in self._fetch_filtered_publication_terms(
                filterable, filter_ids, filter_field, limit
            ):
                yield term
        else:
            # Delegate to wrapped adapter for other entity types
            async for record in filterable.fetch_filtered(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                limit=limit,
            ):
                yield record

    async def _fetch_filtered_publication_terms(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch filtered publications and extract terms.

        Args:
            filterable: Wrapped adapter that implements FilterableDataSourcePort.
            filter_ids: Document ChEMBL IDs to filter by.
            filter_field: Field name (typically document_chembl_id).
            limit: Maximum number of term records to yield.

        Yields:
            Term records extracted from filtered publications.

        """
        term_count = 0
        publication_limit = limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None

        async for publication in filterable.fetch_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=publication_limit,
        ):
            document_chembl_id = publication.get("document_chembl_id")
            if not document_chembl_id:
                continue

            terms = self._extract_terms_from_publication(
                publication, document_chembl_id
            )

            for term in terms:
                yield term
                term_count += 1
                if limit and term_count >= limit:
                    return

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records filtered by multiple fields (AND logic).

        Implements FilterableDataSourcePort.fetch_multi_filtered().

        Args:
            entity_type: Type of entity to fetch.
            filters: Mapping from filter_field to list of IDs.
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records matching ALL filter criteria.

        """
        filterable = self._ensure_filterable("fetch_multi_filtered")

        if entity_type == self.TARGET_ENTITY_TYPE:
            # Fetch publications and extract terms
            term_count = 0
            publication_limit = (
                limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None
            )

            async for publication in filterable.fetch_multi_filtered(
                entity_type=self.SOURCE_ENTITY_TYPE,
                filters=filters,
                limit=publication_limit,
            ):
                document_chembl_id = publication.get("document_chembl_id")
                if not document_chembl_id:
                    continue

                terms = self._extract_terms_from_publication(
                    publication, document_chembl_id
                )

                for term in terms:
                    yield term
                    term_count += 1
                    if limit and term_count >= limit:
                        return
        else:
            # Delegate to wrapped adapter for other entity types
            async for record in filterable.fetch_multi_filtered(
                entity_type=entity_type,
                filters=filters,
                limit=limit,
            ):
                yield record

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records with fallback search when primary lookup fails.

        Implements FilterableDataSourcePort.fetch_filtered_with_fallback().

        Args:
            entity_type: Type of entity to fetch.
            filter_ids: List of primary IDs to filter by.
            filter_field: Field name for primary filtering.
            fallback_mapping: Mapping from primary ID to fallback value.
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records found via primary lookup or fallback search.

        """
        filterable = self._ensure_filterable("fetch_filtered_with_fallback")

        if entity_type == self.TARGET_ENTITY_TYPE:
            # Fetch publications and extract terms
            term_count = 0
            publication_limit = (
                limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None
            )

            async for publication in filterable.fetch_filtered_with_fallback(
                entity_type=self.SOURCE_ENTITY_TYPE,
                filter_ids=filter_ids,
                filter_field=filter_field,
                fallback_mapping=fallback_mapping,
                limit=publication_limit,
            ):
                document_chembl_id = publication.get("document_chembl_id")
                if not document_chembl_id:
                    continue

                terms = self._extract_terms_from_publication(
                    publication, document_chembl_id
                )

                for term in terms:
                    yield term
                    term_count += 1
                    if limit and term_count >= limit:
                        return
        else:
            # Delegate to wrapped adapter for other entity types
            async for record in filterable.fetch_filtered_with_fallback(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                fallback_mapping=fallback_mapping,
                limit=limit,
            ):
                yield record

    def get_source_metadata(self, api_version: str | None = None) -> Any:
        """Delegate get_source_metadata to wrapped data source.

        Returns API request metadata collected by the underlying adapter.
        Used by BatchExecutor to enrich Bronze layer metadata.

        Args:
            api_version: Optional API version string.

        Returns:
            SourceMetadata with request details, or None if not supported.
        """
        get_metadata = getattr(self._data_source, "get_source_metadata", None)
        if get_metadata is not None and callable(get_metadata):
            return get_metadata(api_version)
        return None

================================================================================
File: quarantine_manager.py
Path: core\quarantine_manager.py
================================================================================
"""Quarantine Manager for ETL Pipelines.

Refactored per ADR-0005 to accept explicit dependencies instead of full pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bioetl.domain.ports import QuarantinePort
from bioetl.domain.types import BatchID, ErrorType


class QuarantineManager:
    """Manages quarantining of records that fail processing.

    This manager handles writing failed records to quarantine storage
    for later analysis and potential reprocessing.
    """

    def __init__(
        self,
        quarantine_port: QuarantinePort,
        pipeline_name: str,
    ) -> None:
        """Initialize QuarantineManager with explicit dependencies.

        Args:
            quarantine_port: Port for writing to quarantine storage.
            pipeline_name: Name of the pipeline for identification.

        """
        self._quarantine = quarantine_port
        self._pipeline_name = pipeline_name

    async def quarantine_record(
        self,
        record: dict[str, Any],
        error_type: ErrorType,
        batch_id: BatchID,
        error_details: str,
        *,
        ingestion_ts: datetime,
    ) -> None:
        """Write a record to the quarantine.

        Args:
            record: The raw record that failed processing.
            error_type: Classification of the error.
            batch_id: ID of the batch containing this record.
            error_details: Human-readable error description.
            ingestion_ts: Ingestion timestamp from context
                         (single source of time per ADR-014). Required.

        """
        await self._quarantine.write(
            pipeline=self._pipeline_name,
            error_code=error_type.value,
            payload=record,
            bronze_batch_id=batch_id,
            metadata={"error_details": {"message": error_details}},
            ingestion_ts=ingestion_ts,
        )

    async def inspect(
        self,
        limit: int = 100,
        error_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Inspect quarantined records for this pipeline.

        Delegates to QuarantinePort.inspect() for CLI inspection commands.

        Args:
            limit: Maximum number of records to return.
            error_code: Optional filter by error code.

        Returns:
            List of quarantined records.

        """
        return await self._quarantine.inspect(
            pipeline=self._pipeline_name,
            limit=limit,
            error_code=error_code,
        )

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about quarantined records for this pipeline.

        Delegates to QuarantinePort.get_stats() for CLI reporting.

        Returns:
            Dictionary with quarantine statistics.

        """
        return await self._quarantine.get_stats(self._pipeline_name)

================================================================================
File: record_processor.py
Path: core\record_processor.py
================================================================================
"""Orchestrates batch processing through Bronze, Silver, and Gold layers.

Observability: Nested spans for transform → write_bronze → write_silver → write_gold.

Safety Guard (RULES.md §4.6):
    Lock validation is performed at BatchWriter level BEFORE any write operation.
    RecordProcessor passes a lock_validator callback from LockManager.validate().
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from bioetl.application.core.batch_executor import BatchResult
from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.batch_transformer import BatchTransformer, TransformResult
from bioetl.application.core.batch_writer import BatchWriter
from bioetl.application.core.quarantine_manager import QuarantineManager

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.ports import GoldValidatorPort, TracingPort
    from bioetl.domain.types import BatchID


class RecordProcessor:
    """Orchestrates batch transformation and writing across all layers."""

    def __init__(
        self,
        services: PipelineServices,
        error_classifier: ErrorClassifier,
        context: PipelineContext,
        config: RecordProcessorConfig,
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        gold_transform_callback: GoldTransformCallback,
        gold_validator: GoldValidatorPort,
        tracer: TracingPort | None = None,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
    ):
        """Initialize RecordProcessor.

        Args:
            services: Pipeline services bundle.
            error_classifier: Service for error classification.
            context: Pipeline execution context.
            config: Record processor configuration.
            transform_callback: Callback for record transformation.
            gold_filter_callback: Callback for Gold layer filtering.
            gold_transform_callback: Callback for Gold layer transformation.
            gold_validator: Validator for Gold layer records.
            tracer: Optional tracing port for distributed tracing.
            lock_validator: Async callable that validates lock ownership.
                Returns True if lock is still held, False otherwise.
                Typically LockManager.validate(). If None, lock validation
                is skipped (for tests).
        """
        self._context = context
        self._tracer = tracer

        pipeline_label = f"{config.provider}_{config.entity_type}"
        self._batch_metrics = BatchMetricsRecorder(
            services.metrics, pipeline_label, context.run_type.value
        )

        self._transformer = BatchTransformer(
            context=context,
            config=config,
            error_classifier=error_classifier,
            quarantine_manager=QuarantineManager(
                quarantine_port=services.quarantine,
                pipeline_name=config.pipeline_name,
            ),
            batch_metrics=self._batch_metrics,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        self._writer = BatchWriter(
            storage=services.storage,
            context=context,
            config=config,
            gold_validator=gold_validator,
            error_classifier=error_classifier,
            batch_metrics=self._batch_metrics,
            tracer=tracer,
            lock_validator=lock_validator,
        )

    async def process_batch(
        self, records: list[dict[str, Any]], batch_id: BatchID, start_index: int = 0
    ) -> BatchResult:
        """Process batch through Bronze -> Silver -> Gold with tracing."""
        ingestion_ts = self._context.started_at

        # Write to Bronze and capture result for lineage tracking (REQ-LINEAGE-001)
        bronze_result = await self._execute_with_span(
            "write_bronze",
            self._writer.write_bronze(records, batch_id, ingestion_ts),
            batch_id,
            len(records),
            on_error=lambda e: self._writer.log_and_track_write_error(
                "bronze", e, batch_id
            ),
        )
        self._batch_metrics.track_batch_size("bronze", len(records))
        self._batch_metrics.track_processed_records("bronze", len(records))

        # Transform records
        result = await self._execute_transform_with_span(records, batch_id, start_index)
        self._batch_metrics.track_processed_records(
            "quarantined", result.quarantined_count
        )
        self._batch_metrics.track_processed_records(
            "silver", len(result.silver_records)
        )
        self._batch_metrics.track_processed_records("gold", len(result.gold_records))

        # Write to Silver with bronze_refs for lineage tracking (REQ-LINEAGE-001)
        bronze_refs = [bronze_result] if bronze_result else None
        if result.silver_records:
            await self._execute_with_span(
                "write_silver",
                self._writer.write_silver(
                    result.silver_records,
                    batch_id,
                    ingestion_ts,
                    bronze_refs=bronze_refs,
                ),
                batch_id,
                len(result.silver_records),
                on_error=lambda e: self._writer.log_and_track_write_error(
                    "silver", e, batch_id
                ),
            )

        # Write to Gold
        if result.gold_records:
            await self._execute_with_span(
                "write_gold",
                self._writer.write_gold(result.gold_records),
                batch_id,
                len(result.gold_records),
                on_error=lambda e: self._writer.log_and_track_write_error(
                    "gold", e, batch_id
                ),
            )

        return BatchResult(
            bronze_count=len(records),
            silver_count=len(result.silver_records),
            gold_count=len(result.gold_records),
            quarantined_count=result.quarantined_count,
        )

    async def _execute_with_span(
        self, name: str, coro: Any, batch_id: BatchID, count: int, on_error: Any = None
    ) -> Any:
        """Execute coroutine with tracing span."""
        span = self._start_span(name, batch_id, count)
        try:
            result = await coro
            self._end_span(span)
            return result
        except Exception as e:
            self._end_span(span, e)
            if on_error:
                on_error(e)
            raise

    async def _execute_transform_with_span(
        self, records: list[dict[str, Any]], batch_id: BatchID, start_index: int
    ) -> TransformResult:
        """Execute transformation with extended span attributes."""
        span = self._start_span("transform", batch_id, len(records), input_count=True)
        try:
            result = await self._transformer.transform_batch(
                records, batch_id, start_index=start_index
            )
            if span:
                span.set_attribute("bioetl.silver_count", len(result.silver_records))
                span.set_attribute("bioetl.gold_count", len(result.gold_records))
                span.set_attribute("bioetl.quarantined_count", result.quarantined_count)
            self._end_span(span)
            return result
        except Exception as e:
            self._end_span(span, e)
            raise

    def _start_span(
        self, name: str, batch_id: BatchID, count: int, input_count: bool = False
    ) -> Any:
        """Start a tracing span if tracer is available."""
        if not self._tracer:
            return None
        count_key = "bioetl.input_count" if input_count else "bioetl.record_count"
        attrs = {"bioetl.batch_id": str(batch_id), count_key: count}
        span = self._tracer.get_tracer("bioetl.processor").start_as_current_span(
            name, attributes=attrs
        )
        span.__enter__()
        return span

    def _end_span(self, span: Any, error: Exception | None = None) -> None:
        """End a tracing span."""
        if not span:
            return
        if error:
            span.set_attribute("error", True)
            span.record_exception(error)
        span.__exit__(None, None, None)

================================================================================
File: runner.py
Path: core\runner.py
================================================================================
"""Pipeline Runner.

Application Service that orchestrates pipeline execution lifecycle.
Coordinates locking, checkpointing, and execution.

Delegates to specialized services (injected directly via DI):
- LockManager: Distributed locking
- PreflightService: Infrastructure health validation
- PostrunService: DQ checks, VACUUM, cleanup
- MedallionLifecycleService: Medallion layer clearing and vacuum
- PipelineObserver: Observability wrapper for tracing, metrics, logging
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.events import PipelineEvent

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.lock_manager import LockManager
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.postrun_service import PostrunService
    from bioetl.application.core.preflight_service import PreflightService
    from bioetl.application.core.shutdown import ShutdownSignal
    from bioetl.application.observability.observer import PipelineObserver
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, TracingPort


class PipelineRunner:
    """Manages the execution lifecycle of a pipeline.

    It coordinates application services like locking and checkpointing,
    but remains decoupled from the core business logic of the pipeline itself.

    Delegates specialized operations to:
    - PreflightService: Pre-flight infrastructure validation
    - PostrunService: Post-run DQ checks, cleanup
    - MedallionLifecycleService: Pre-run clearing and post-run VACUUM
    """

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
        context: PipelineContext,
        executor: BatchExecutor,
        checkpoint_manager: CheckpointManager,
        shutdown_signal: ShutdownSignal,
        logger: LoggerPort,
        lock_manager: LockManager,
        preflight: PreflightService,
        postrun: PostrunService,
        lifecycle_service: MedallionLifecycleService,
        observer: PipelineObserver,
        pipeline: BasePipeline | None = None,
        tracer: TracingPort | None = None,
    ) -> None:
        """Initialize pipeline runner.

        Args:
            config: Pipeline configuration.
            runtime: Runtime configuration.
            services: Common pipeline services.
            context: Pipeline execution context.
            executor: Batch executor instance (unified extraction + processing).
            checkpoint_manager: Checkpoint manager.
            shutdown_signal: Shutdown signal for graceful termination.
            logger: Structured logger.
            lock_manager: Distributed locking manager.
            preflight: Pre-flight infrastructure validation service.
            postrun: Post-run DQ checks service.
            lifecycle_service: Medallion lifecycle service for clearing and vacuum.
            observer: Pipeline observability wrapper for tracing, metrics, logging.
            pipeline: Optional pipeline instance.
            tracer: Optional tracing port.
        """
        self._config = config
        self._runtime = runtime
        self._services = services
        self._context = context
        self._executor = executor
        self._checkpoint_manager = checkpoint_manager
        self.shutdown_signal = shutdown_signal
        self._logger = logger
        self.pipeline = pipeline
        self._tracer = tracer

        # Services injected directly via DI (created in composition layer)
        self._lock_manager = lock_manager
        self._preflight_service = preflight
        self._postrun_service = postrun
        self._lifecycle_service = lifecycle_service
        self._observer = observer

    @property
    def logger(self) -> LoggerPort:
        """Get the logger instance."""
        return self._logger

    @property
    def services(self) -> PipelineServices:
        """Access injected services."""
        return self._services

    async def run(self) -> None:
        """Execute pipeline. Main entry point.

        Implements graceful shutdown (O3):
        - Uses try/finally to ensure cleanup runs on all exit paths
        - Flushes tracer spans before shutdown
        - Handles tracer close errors without failing the pipeline
        """
        self._logger.info(
            PipelineEvent.START,
            pipeline=self._config.pipeline_name,
            stage="startup",
            run_type=self._runtime.run_type.value,
        )

        try:
            with self._observer:
                async with self._services, self._lock_manager:
                    # Pre-flight: validate infrastructure
                    await self._preflight_service.validate_infrastructure(
                        self._services
                    )

                    # Lifecycle: prepare (clear based on run type policy)
                    await self._lifecycle_service.prepare_for_run(
                        config=self._config,
                        runtime=self._runtime,
                    )

                    # Execute pipeline
                    await self._checkpoint_manager.load_checkpoint()
                    await self._executor.execute(
                        limit=self._runtime.limit,
                        query=self._runtime.query,
                    )

                    # Post-run: DQ checks, DQ reports, and VACUUM
                    dq_context = self._executor.get_dq_context()
                    await self._postrun_service.run(
                        executor=self._executor,
                        dq_context=dq_context,
                    )

                    await self._checkpoint_manager.delete_checkpoint()

                self._logger.debug(
                    PipelineEvent.COMPLETE,
                    records_fetched=self._executor.records_fetched,
                )
        finally:
            await self._postrun_service.cleanup(self._tracer)

    # Backward-compatible private methods (delegate to services)
    async def _validate_infrastructure(self) -> None:
        """Validate infrastructure health before pipeline execution."""
        await self._preflight_service.validate_infrastructure(self._services)

    async def _prepare_medallion_layers(self) -> None:
        """Prepare medallion layers (clear based on run type policy)."""
        await self._lifecycle_service.prepare_for_run(
            config=self._config,
            runtime=self._runtime,
        )

    async def _check_data_quality(self) -> None:
        """Check data quality metrics and report anomalies."""
        await self._postrun_service.run_dq_checks(self._executor)

    async def _run_vacuum_if_enabled(self) -> None:
        """Run VACUUM on Silver and Gold tables if enabled."""
        await self._postrun_service.run_vacuum_if_enabled()

    async def _cleanup(self) -> None:
        """Cleanup all resources including observability."""
        await self._postrun_service.cleanup(self._tracer)

================================================================================
File: shutdown.py
Path: core\shutdown.py
================================================================================
"""Shutdown coordination for pipeline components.

This module provides backward-compatible ShutdownSignal that implements
ShutdownPort protocol. For new code, prefer using ShutdownService from
application/services/shutdown_service.py.

See ADR-008 for graceful shutdown strategy details.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

# Re-export from new location for backward compatibility
from bioetl.application.services.shutdown_service import (
    PipelineShutdownError,
    ShutdownReason,
    ShutdownService,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort


@dataclass
class ShutdownSignal:
    """Shared signal for coordinating graceful shutdown.

    This class implements ShutdownPort protocol and can be used
    interchangeably with ShutdownService.

    For new code, prefer ShutdownService which provides:
    - Detailed reason tracking
    - Metrics emission
    - Completion waiting

    Example:
        >>> signal = ShutdownSignal()
        >>> # In orchestrator
        >>> signal.request()
        >>> # In executor
        >>> if signal.is_requested:
        ...     await checkpoint_manager.save()

    """

    _requested: bool = field(default=False, init=False)
    _event: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    _completion_event: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    _reason: str = field(default="", init=False)

    @property
    def is_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._requested

    def is_shutting_down(self) -> bool:
        """Check if shutdown has been requested (ShutdownPort compatible)."""
        return self._requested

    def request(self) -> None:
        """Request graceful shutdown.

        All components watching this signal will be notified.
        This method is idempotent - multiple calls have no additional effect.
        """
        if not self._requested:
            self._requested = True
            self._event.set()

    async def initiate_shutdown(self, reason: str) -> None:
        """Initiate graceful shutdown (ShutdownPort compatible).

        Args:
            reason: Human-readable reason for shutdown.
        """
        if not self._requested:
            self._requested = True
            self._reason = reason
            self._event.set()

    async def wait(self) -> None:
        """Wait until shutdown is requested.

        Blocks until request() is called. Use with asyncio.wait_for()
        for timeout-based waiting.
        """
        await self._event.wait()

    async def wait_for_completion(self, timeout: float) -> bool:
        """Wait for shutdown completion (ShutdownPort compatible).

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            True if completed within timeout, False otherwise.
        """
        try:
            await asyncio.wait_for(self._completion_event.wait(), timeout=timeout)
            return True
        except TimeoutError:
            return False

    def mark_completed(self) -> None:
        """Mark shutdown as completed."""
        self._completion_event.set()

    def reset(self) -> None:
        """Reset signal for reuse (e.g., in tests).

        Warning: Only use in tests or when you're certain no components
        are currently checking the signal.
        """
        self._requested = False
        self._event.clear()
        self._completion_event.clear()
        self._reason = ""


def create_shutdown_service(
    logger: LoggerPort,
    metrics: MetricsPort | None = None,
) -> ShutdownService:
    """Factory function to create ShutdownService.

    Convenience function for creating ShutdownService with
    proper dependency injection.

    Args:
        logger: Logger for shutdown events.
        metrics: Optional metrics port for shutdown metrics.

    Returns:
        Configured ShutdownService instance.
    """
    return ShutdownService(logger=logger, metrics=metrics)


__all__ = [
    "PipelineShutdownError",
    "ShutdownReason",
    "ShutdownService",
    "ShutdownSignal",
    "create_shutdown_service",
]

================================================================================
File: transform_utils.py
Path: core\transform_utils.py
================================================================================
"""Common transformation utilities for all pipelines.

Реализует общие паттерны трансформации для уменьшения дублирования
в ChEMBL и других трансформерах.

Функции:
- flatten_nested_dict: Разворачивание вложенных словарей с префиксом
- extract_list_field: Извлечение поля из списка словарей
- aggregate_nested_lists: Агрегация вложенных списков
- normalize_string: Нормализация строковых полей (delegated to domain)
- parse_date_field: Парсинг даты с обработкой ошибок (delegated to domain)
- validate_smiles: Валидация SMILES строки (delegated to domain)

Note: Business logic functions are delegated to domain layer per REFACTOR-004.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any, TypeVar

from bioetl.domain.normalization import normalize_string as _domain_normalize_string
from bioetl.domain.normalization import parse_date_field as _domain_parse_date_field
from bioetl.domain.transformations import safe_float, safe_int
from bioetl.domain.validation import validate_smiles as _domain_validate_smiles

T = TypeVar("T")


def flatten_nested_dict(
    data: dict[str, Any] | None,
    prefix: str,
    field_mapping: dict[str, Callable[[Any], Any] | None],
    renames: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Разворачивает вложенный словарь в плоскую структуру с префиксом.

    Используется для извлечения полей из вложенных структур API
    (molecule_properties, molecule_hierarchy, ligand_efficiency и т.д.).

    Args:
        data: Вложенный словарь для разворачивания. Если None, возвращает
              словарь с None значениями для всех ключей.
        prefix: Префикс для результирующих ключей (e.g., "property_", "hierarchy_").
        field_mapping: Словарь {исходный_ключ: конвертер}.
                       Конвертер может быть safe_float, safe_int или None (без конвертация).
        renames: Опциональный словарь {старый_ключ: новый_ключ} для переименования
                 полей после разворачивания. Ключи должны включать префикс.

    Returns:
        Плоский словарь с префиксами и сконвертированными значениями.

    Example:
        >>> data = {"alogp": "3.5", "hba": 2}
        >>> mapping = {"alogp": safe_float, "hba": safe_int}
        >>> flatten_nested_dict(data, "property_", mapping)
        {'property_alogp': 3.5, 'property_hba': 2}

        >>> flatten_nested_dict(None, "property_", mapping)
        {'property_alogp': None, 'property_hba': None}

        >>> # With renames parameter
        >>> data = {"molecule_chembl_id": "CHEMBL25"}
        >>> mapping = {"molecule_chembl_id": None}
        >>> renames = {"hierarchy_molecule_chembl_id": "hierarchy_child_chembl_id"}
        >>> flatten_nested_dict(data, "hierarchy_", mapping, renames)
        {'hierarchy_child_chembl_id': 'CHEMBL25'}

    """
    if not data or not isinstance(data, dict):
        result = {f"{prefix}{key}": None for key in field_mapping}
    else:
        result = {}
        for source_key, converter in field_mapping.items():
            value = data.get(source_key)
            if converter is not None and value is not None:
                result[f"{prefix}{source_key}"] = converter(value)
            else:
                result[f"{prefix}{source_key}"] = value

    # Apply renames if provided
    if renames:
        for old_key, new_key in renames.items():
            if old_key in result:
                result[new_key] = result.pop(old_key)

    return result


def extract_list_field(
    items: list[dict[str, Any]] | None,
    field: str,
    converter: Callable[[Any], T] | None = None,
) -> list[T] | None:
    """Извлекает значения поля из списка словарей.

    Используется для агрегации полей из компонентов, классификаций и т.д.

    Args:
        items: Список словарей для обработки.
        field: Имя поля для извлечения.
        converter: Опциональный конвертер (safe_int, safe_float и т.д.).
                   Если None, значения возвращаются как есть.

    Returns:
        Список значений или None, если результат пустой.

    Example:
        >>> items = [{"id": "1"}, {"id": "2"}, {"id": None}]
        >>> extract_list_field(items, "id")
        ['1', '2']

        >>> extract_list_field(items, "id", safe_int)
        [1, 2]

    """
    if not items or not isinstance(items, list):
        return None

    values: list[T] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_value = item.get(field)
        if raw_value is None:
            continue

        if converter is not None:
            converted = converter(raw_value)
            if converted is not None:
                values.append(converted)
        else:
            values.append(raw_value)

    return values if values else None


def _extract_nested_values(items: list[dict[str, Any]], field: str) -> list[Any]:
    """Extract all nested list values from a field across items."""
    values: list[Any] = []
    for item in items:
        if isinstance(item, dict):
            nested = item.get(field)
            if isinstance(nested, list):
                values.extend(nested)
    return values


def aggregate_nested_lists(
    items: list[dict[str, Any]] | None,
    field: str,
    deduplicate: bool = True,
) -> list[Any] | None:
    """Агрегирует вложенные списки из списка словарей.

    Используется для сбора synonyms, xrefs и других вложенных списков
    из множества компонентов в один плоский список.

    Args:
        items: Список словарей, каждый из которых может содержать вложенный список.
        field: Имя поля со вложенным списком.
        deduplicate: Если True, удаляет дубликаты из результирующего списка (по умолчанию True).

    Returns:
        Объединённый список или None, если результат пустой.

    Example:
        >>> items = [
        ...     {"synonyms": ["a", "b"]},
        ...     {"synonyms": ["c", "a"]},
        ...     {"other": "data"}
        ... ]
        >>> aggregate_nested_lists(items, "synonyms")
        ['a', 'b', 'c']

    """
    if not isinstance(items, list) or not items:
        return None

    values = _extract_nested_values(items, field)
    if not values:
        return None

    if deduplicate:
        seen: set[str] = set()
        unique: list[Any] = []
        for val in values:
            key = str(val)
            if key not in seen:
                seen.add(key)
                unique.append(val)
        return unique if unique else None

    return values


def normalize_string(value: str | None) -> str | None:
    """Нормализует строковое поле.

    Удаляет пробельные символы по краям и возвращает None для пустых строк.

    Note: Delegated to domain.normalization.normalize_string per REFACTOR-004.

    Args:
        value: Строка для нормализации.

    Returns:
        Нормализованная строка или None.

    Example:
        >>> normalize_string("  hello world  ")
        'hello world'
        >>> normalize_string("   ")
        None
        >>> normalize_string(None)
        None

    """
    return _domain_normalize_string(value)


def parse_date_field(
    value: str | None,
    fmt: str = "%Y-%m-%d",
) -> date | None:
    """Парсит строку даты в объект date.

    Безопасный парсинг с обработкой ошибок и невалидных форматов.

    Note: Delegated to domain.normalization.parse_date_field per REFACTOR-004.

    Args:
        value: Строка с датой или None.
        fmt: Формат даты (по умолчанию ISO: YYYY-MM-DD).

    Returns:
        Объект date или None при ошибке парсинга.

    Example:
        >>> parse_date_field("2024-01-15")
        datetime.date(2024, 1, 15)
        >>> parse_date_field("invalid")
        None
        >>> parse_date_field("15/01/2024", "%d/%m/%Y")
        datetime.date(2024, 1, 15)

    """
    return _domain_parse_date_field(value, fmt)


def validate_smiles(smiles: str | None) -> bool:
    """Проверяет валидность SMILES строки.

    Выполняет базовую синтаксическую проверку без полного парсинга молекулы.
    Для полной валидации используйте RDKit или другую химическую библиотеку.

    Note: Delegated to domain.validation.validate_smiles per REFACTOR-004.

    Args:
        smiles: SMILES строка для проверки.

    Returns:
        True если строка соответствует базовому синтаксису SMILES.

    Example:
        >>> validate_smiles("CCO")  # Ethanol
        True
        >>> validate_smiles("C1=CC=CC=C1")  # Benzene
        True
        >>> validate_smiles("")
        False
        >>> validate_smiles(None)
        False
        >>> validate_smiles("invalid smiles with spaces")
        False

    """
    return _domain_validate_smiles(smiles)


def safe_extract(
    record: dict[str, Any],
    key: str,
    default: T | None = None,
) -> T | Any | None:
    """Безопасно извлекает значение из словаря с логированием.

    Обёртка над dict.get() для унифицированного извлечения полей.
    Для использования с логированием используйте в связке с контекстом.

    Args:
        record: Словарь для извлечения.
        key: Ключ для поиска.
        default: Значение по умолчанию (None).

    Returns:
        Значение по ключу или default.

    Example:
        >>> record = {"name": "test", "value": 42}
        >>> safe_extract(record, "name")
        'test'
        >>> safe_extract(record, "missing", "default")
        'default'

    """
    return record.get(key, default)


# Re-export safe_float and safe_int for convenience
__all__ = [
    "aggregate_nested_lists",
    "extract_list_field",
    "flatten_nested_dict",
    "normalize_string",
    "parse_date_field",
    "safe_extract",
    "safe_float",
    "safe_int",
    "validate_smiles",
]

================================================================================
File: __init__.py
Path: observability\__init__.py
================================================================================
"""Application layer observability components.

This package contains:
- PipelineObserver: Context manager for tracing execution lifecycle
- LifecyclePhase: Enum for pipeline lifecycle phases
- Observability utilities for the application layer

Architecture:
- Application layer defines WHAT to observe (Events)
- Infrastructure layer defines HOW to observe (Prometheus, Logs)

Unified Observability Pattern:
- All lifecycle events are emitted through PipelineObserver
- Services use emit_event() for structured logging with metrics
- Single source of truth for all observability events
"""

from __future__ import annotations

from bioetl.application.observability.observer import LifecyclePhase, PipelineObserver
from bioetl.application.observability.span_helpers import (
    traced_async_operation,
    traced_operation,
)

__all__ = [
    "LifecyclePhase",
    "PipelineObserver",
    "traced_async_operation",
    "traced_operation",
]

================================================================================
File: observer.py
Path: observability\observer.py
================================================================================
"""Pipeline Observer Context Manager.

Implements R12/R13: Observability wrapper for pipeline execution.
Handles:
- Distributed Tracing (Span creation)
- Metrics (Counter/Histogram)
- Logging (Structured logs with lifecycle context)

Unified Observability Pattern:
- All lifecycle events are emitted through this single observer
- Services use emit_event() to log structured events with metrics
- This eliminates duplicate logging across runner/preflight/postrun
"""

from __future__ import annotations

import time
from contextlib import AbstractContextManager
from enum import Enum
from typing import TYPE_CHECKING, Any

from bioetl.application.core.shutdown import PipelineShutdownError
from bioetl.domain.events import PipelineEvent

if TYPE_CHECKING:
    from types import TracebackType

    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID, RunType


class LifecyclePhase(str, Enum):
    """Pipeline lifecycle phases for structured observability.

    Each phase represents a distinct stage in pipeline execution
    that should be tracked for monitoring and debugging.
    """

    STARTUP = "startup"
    PREFLIGHT = "preflight"
    LIFECYCLE_CLEAR = "lifecycle_clear"
    EXECUTION = "execution"
    POSTRUN = "postrun"
    CLEANUP = "cleanup"


class PipelineObserver(AbstractContextManager["PipelineObserver"]):
    """Observability wrapper for pipeline execution."""

    def __init__(
        self,
        pipeline_name: str,
        run_id: RunID,
        run_type: RunType,
        metrics: MetricsPort,
        logger: LoggerPort,
        tracer: TracingPort | None = None,
    ) -> None:
        """Initialize observer."""
        self.pipeline_name = pipeline_name
        self.run_id = str(run_id)
        self.run_type = run_type.value
        self.metrics = metrics
        self.logger = logger
        self.tracer = tracer

        self.start_time: float | None = None
        self.span: Any = None

    def __enter__(self) -> PipelineObserver:
        """Start observation (Span + Log + Metric)."""
        self.start_time = time.monotonic()

        # 1. Start Trace Span
        if self.tracer:
            otel_tracer = self.tracer.get_tracer("bioetl.pipeline")
            self.span = otel_tracer.start_as_current_span(
                f"pipeline.{self.pipeline_name}",
                attributes={
                    "bioetl.pipeline": self.pipeline_name,
                    "bioetl.run_id": self.run_id,
                    "bioetl.run_type": self.run_type,
                },
            )
            self.span.__enter__()

        # 2. Log Start
        self.logger.info(PipelineEvent.START, run_type=self.run_type)

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        """End observation (Span + Log + Metric)."""
        duration = time.monotonic() - (self.start_time or 0)
        status = "success"
        suppress_exception = False

        if exc_val:
            if isinstance(exc_val, PipelineShutdownError):
                status = "shutdown"
                suppress_exception = (
                    True  # We suppress the shutdown signal to allow clean exit
                )
            else:
                status = "failed"

        # 1. Metrics (Histogram)
        self.metrics.observe_histogram(
            "bioetl_pipeline_duration_seconds",
            duration,
            labels={
                "pipeline": self.pipeline_name,
                "run_type": self.run_type,
                "status": status,
            },
        )
        self.metrics.increment_counter(
            "bioetl_pipeline_runs_total",
            1,
            labels={
                "pipeline": self.pipeline_name,
                "run_type": self.run_type,
                "status": status,
            },
        )

        # 2. Log Result
        log_ctx = {
            "duration_seconds": duration,
            "status": status,
        }
        if status == "failed":
            self.logger.error(
                PipelineEvent.FAILED,
                **log_ctx,
                error=str(exc_val),
                error_type=type(exc_val).__name__,
            )
        elif status == "shutdown":
            self.logger.warning(PipelineEvent.SHUTDOWN, **log_ctx)
        else:
            self.logger.info(PipelineEvent.COMPLETE, **log_ctx)

        # 3. End Trace Span (O3: handle close errors gracefully)
        if self.span:
            try:
                self.span.set_attribute("bioetl.status", status)
                self.span.set_attribute("bioetl.duration_ms", duration * 1000)
                if status == "failed":
                    self.span.record_exception(exc_val)
                    self.span.set_attribute("error", True)
                self.span.__exit__(exc_type, exc_val, exc_tb)
            except Exception:
                # Best effort - don't fail the pipeline on tracing cleanup
                pass

        return suppress_exception

    # --- Unified Lifecycle Event Emission ---

    def emit_event(
        self,
        event_name: str,
        phase: LifecyclePhase,
        level: str = "info",
        **extra: Any,
    ) -> None:
        """Emit a structured lifecycle event through unified observability.

        This is the single source of truth for lifecycle events.
        All events are logged with consistent context and optionally traced.

        Args:
            event_name: Event identifier (e.g., "preflight_started").
            phase: Current lifecycle phase.
            level: Log level ("debug", "info", "warning", "error").
            **extra: Additional context for the event.
        """
        ctx = {
            "phase": phase.value,
            "pipeline": self.pipeline_name,
            "run_id": self.run_id,
            **extra,
        }

        log_method = getattr(self.logger, level, self.logger.info)
        log_method(event_name, **ctx)

        # Add span event if tracing is active
        if self.span:
            try:
                self.span.set_attribute(f"bioetl.{event_name}", True)
            except Exception:
                pass  # Best effort

    def emit_phase_started(
        self,
        phase: LifecyclePhase,
        **extra: Any,
    ) -> float:
        """Emit phase start event and return start timestamp.

        Args:
            phase: Lifecycle phase starting.
            **extra: Additional context.

        Returns:
            Start timestamp for duration calculation.
        """
        self.emit_event(PipelineEvent.phase_started(phase.value), phase, **extra)
        return time.monotonic()

    def emit_phase_completed(
        self,
        phase: LifecyclePhase,
        start_time: float,
        success: bool = True,
        **extra: Any,
    ) -> None:
        """Emit phase completion event with duration.

        Args:
            phase: Lifecycle phase completed.
            start_time: Timestamp from emit_phase_started().
            success: Whether phase completed successfully.
            **extra: Additional context.
        """
        duration = time.monotonic() - start_time
        status = "success" if success else "failed"

        self.emit_event(
            PipelineEvent.phase_completed(phase.value),
            phase,
            level="info" if success else "error",
            duration_seconds=round(duration, 4),
            status=status,
            **extra,
        )

        # Record phase duration metric
        self.metrics.observe_histogram(
            "bioetl_phase_duration_seconds",
            duration,
            labels={
                "pipeline": self.pipeline_name,
                "phase": phase.value,
                "status": status,
            },
        )

    def emit_health_check_result(
        self,
        component: str,
        healthy: bool,
        duration_ms: float | None = None,
        **extra: Any,
    ) -> None:
        """Emit health check result for a component.

        Unified interface for health check observability.

        Args:
            component: Component name (e.g., "storage", "data_source").
            healthy: Whether component is healthy.
            duration_ms: Optional check duration in milliseconds.
            **extra: Additional context.
        """
        self.emit_event(
            PipelineEvent.HEALTH_CHECK_COMPLETED,
            LifecyclePhase.PREFLIGHT,
            level="info" if healthy else "warning",
            component=component,
            healthy=healthy,
            duration_ms=duration_ms,
            **extra,
        )

        self.metrics.set_gauge(
            "pipeline_health_check_passed",
            1.0 if healthy else 0.0,
            {"pipeline": self.pipeline_name, "component": component},
        )

    def emit_dq_anomaly(
        self,
        metric_name: str,
        severity: str,
        anomaly_type: str,
        current_value: float,
        baseline_mean: float | None = None,
        **extra: Any,
    ) -> None:
        """Emit data quality anomaly detection event.

        Args:
            metric_name: Name of the metric with anomaly.
            severity: Anomaly severity ("warning", "critical").
            anomaly_type: Type of anomaly detected.
            current_value: Current metric value.
            baseline_mean: Baseline mean for comparison.
            **extra: Additional context.
        """
        level = "error" if severity == "critical" else "warning"
        self.emit_event(
            PipelineEvent.DQ_ANOMALY_DETECTED,
            LifecyclePhase.POSTRUN,
            level=level,
            metric=metric_name,
            severity=severity,
            anomaly_type=anomaly_type,
            current_value=current_value,
            baseline_mean=baseline_mean,
            **extra,
        )

        self.metrics.increment_counter(
            "dq_anomaly_detected",
            1,
            {
                "pipeline": self.pipeline_name,
                "metric": metric_name,
                "severity": severity,
                "anomaly_type": anomaly_type,
            },
        )

    def emit_vacuum_result(
        self,
        layer: str,
        table: str,
        files_removed: int,
        success: bool = True,
        **extra: Any,
    ) -> None:
        """Emit VACUUM operation result.

        Args:
            layer: Storage layer ("silver", "gold").
            table: Table name.
            files_removed: Number of files removed.
            success: Whether operation succeeded.
            **extra: Additional context.
        """
        self.emit_event(
            PipelineEvent.VACUUM_COMPLETED,
            LifecyclePhase.POSTRUN,
            level="info" if success else "warning",
            layer=layer,
            table=table,
            files_removed=files_removed,
            success=success,
            **extra,
        )

        if success:
            self.metrics.increment_counter(
                "vacuum_files_removed",
                files_removed,
                {"pipeline": self.pipeline_name, "layer": layer},
            )

================================================================================
File: span_helpers.py
Path: observability\span_helpers.py
================================================================================
"""Span helper utilities for unified tracing.

Provides context managers for tracing spans that properly handle
exceptions and ensure spans are always closed.

This module eliminates the need for manual __enter__/__exit__ calls
in application code (Phase 4 refactoring).

Usage:
    >>> async with traced_operation(tracer, "my_operation", {"key": "value"}) as span:
    ...     # Do work
    ...     span.set_attribute("result", "success")
"""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from bioetl.domain.ports import TracingPort


@contextmanager
def traced_operation(
    tracer: TracingPort,
    name: str,
    attributes: dict[str, Any] | None = None,
    tracer_name: str = "bioetl",
) -> Generator[Any, None, None]:
    """Context manager for synchronous tracing spans.

    Creates a span that is properly closed even if an exception occurs.
    Records exceptions on the span before re-raising.

    Args:
        tracer: TracingPort for creating spans
        name: Name of the span (e.g., "write_bronze", "transform_batch")
        attributes: Optional initial span attributes
        tracer_name: Name of the tracer (default: "bioetl")

    Yields:
        The span context for setting additional attributes

    Example:
        >>> with traced_operation(tracer, "write_bronze", {"layer": "bronze"}) as span:
        ...     # Write data
        ...     span.set_attribute("record_count", 100)

    """
    otel_tracer = tracer.get_tracer(tracer_name)
    span = otel_tracer.start_as_current_span(name, attributes=attributes or {})
    span.__enter__()

    try:
        yield span
    except Exception as e:
        span.set_attribute("error", True)
        span.set_attribute("error.type", type(e).__name__)
        span.record_exception(e)
        raise
    finally:
        span.__exit__(None, None, None)


@asynccontextmanager
async def traced_async_operation(
    tracer: TracingPort,
    name: str,
    attributes: dict[str, Any] | None = None,
    tracer_name: str = "bioetl",
) -> AsyncGenerator[Any, None]:
    """Async context manager for tracing spans.

    Creates a span that is properly closed even if an exception occurs.
    Records exceptions on the span before re-raising.

    Args:
        tracer: TracingPort for creating spans
        name: Name of the span (e.g., "write_bronze", "transform_batch")
        attributes: Optional initial span attributes
        tracer_name: Name of the tracer (default: "bioetl")

    Yields:
        The span context for setting additional attributes

    Example:
        >>> async with traced_async_operation(tracer, "fetch_data") as span:
        ...     data = await fetch()
        ...     span.set_attribute("record_count", len(data))

    """
    otel_tracer = tracer.get_tracer(tracer_name)
    span = otel_tracer.start_as_current_span(name, attributes=attributes or {})
    span.__enter__()

    try:
        yield span
    except Exception as e:
        span.set_attribute("error", True)
        span.set_attribute("error.type", type(e).__name__)
        span.record_exception(e)
        raise
    finally:
        span.__exit__(None, None, None)

================================================================================
File: __init__.py
Path: pipelines\__init__.py
================================================================================
"""Concrete pipeline implementations.

This package provides pipelines for extracting and processing data from
various bioinformatics data sources.

Main Components:
- GenericPipeline: Universal pipeline class for all provider/entity combinations
- Provider-specific pipelines: ChEMBL, PubChem, UniProt, PubMed
- Provider-specific transformers: Implement Bronze→Silver transformation logic

Usage:
    # From interfaces/CLI layer - use factory for pipeline instantiation:
    # >>> from bioetl.composition.factories.pipeline_factories import get_factory
    # >>> factory = get_factory("chembl_activity")
    # >>> runner = factory.create_runner(...)

    # Direct instantiation (for testing)
    from bioetl.application.pipelines.generic import GenericPipeline
    pipeline = GenericPipeline.create(...)

    # Provider-specific pipelines
    from bioetl.application.pipelines.chembl import ChEMBLActivityPipeline
"""

from __future__ import annotations

from bioetl.application.pipelines.generic import GenericPipeline

__all__ = [
    "GenericPipeline",
]

================================================================================
File: __init__.py
Path: pipelines\chembl\__init__.py
================================================================================
"""ChEMBL pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the ChEMBL database.

Main Components:
- Transformers: ActivityTransformer, AssayTransformer, PublicationSimilarityTransformer, etc.
- BaseChemblTransformer: Base class for ChEMBL-specific transformers
- Pipeline classes: ChEMBLActivityPipeline, ChEMBLAssayPipeline, ChEMBLPublicationSimilarityPipeline, etc.

Usage:
    # Use transformers for custom pipelines
    from bioetl.application.pipelines.chembl import ActivityTransformer
    transformer = ActivityTransformer(provider="chembl")

    # Use pipeline classes for standard pipelines
    from bioetl.application.pipelines.chembl import ChEMBLActivityPipeline
"""

from __future__ import annotations

# Pipeline classes
from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline

# Transformers
from bioetl.application.pipelines.chembl.activity_transformer import (
    ActivityTransformer,
)
from bioetl.application.pipelines.chembl.assay import ChEMBLAssayPipeline
from bioetl.application.pipelines.chembl.assay_parameters import (
    ChEMBLAssayParametersPipeline,
)
from bioetl.application.pipelines.chembl.assay_parameters_transformer import (
    AssayParametersTransformer,
)
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.application.pipelines.chembl.cell_line import ChEMBLCellLinePipeline
from bioetl.application.pipelines.chembl.cell_line_transformer import (
    CellLineTransformer,
)
from bioetl.application.pipelines.chembl.compound_record import (
    ChEMBLCompoundRecordPipeline,
)
from bioetl.application.pipelines.chembl.compound_record_transformer import (
    CompoundRecordTransformer,
)
from bioetl.application.pipelines.chembl.molecule import ChEMBLMoleculePipeline
from bioetl.application.pipelines.chembl.molecule_transformer import (
    MoleculeTransformer,
)
from bioetl.application.pipelines.chembl.protein_class import (
    ChEMBLProteinClassPipeline,
)
from bioetl.application.pipelines.chembl.protein_class_transformer import (
    ProteinClassTransformer,
)

# Publication pipelines
from bioetl.application.pipelines.chembl.publication import ChEMBLPublicationPipeline
from bioetl.application.pipelines.chembl.publication_similarity import (
    ChEMBLPublicationSimilarityPipeline,
)
from bioetl.application.pipelines.chembl.publication_similarity_transformer import (
    PublicationSimilarityTransformer,
)
from bioetl.application.pipelines.chembl.publication_term import (
    ChEMBLPublicationTermPipeline,
)
from bioetl.application.pipelines.chembl.publication_term_transformer import (
    PublicationTermTransformer,
)
from bioetl.application.pipelines.chembl.publication_transformer import (
    PublicationTransformer,
)
from bioetl.application.pipelines.chembl.target import ChEMBLTargetPipeline
from bioetl.application.pipelines.chembl.target_component import (
    ChEMBLTargetComponentPipeline,
)
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer

__all__ = [
    "ActivityTransformer",
    "AssayParametersTransformer",
    "AssayTransformer",
    "BaseChemblTransformer",
    "CellLineTransformer",
    "ChEMBLActivityPipeline",
    "ChEMBLAssayParametersPipeline",
    "ChEMBLAssayPipeline",
    "ChEMBLCellLinePipeline",
    "ChEMBLCompoundRecordPipeline",
    "ChEMBLMoleculePipeline",
    "ChEMBLProteinClassPipeline",
    "ChEMBLPublicationPipeline",
    "ChEMBLPublicationSimilarityPipeline",
    "ChEMBLPublicationTermPipeline",
    "ChEMBLTargetComponentPipeline",
    "ChEMBLTargetPipeline",
    "CompoundRecordTransformer",
    "MoleculeTransformer",
    "ProteinClassTransformer",
    "PublicationSimilarityTransformer",
    "PublicationTermTransformer",
    "PublicationTransformer",
    "TargetComponentTransformer",
    "TargetTransformer",
]

================================================================================
File: activity.py
Path: pipelines\chembl\activity.py
================================================================================
"""ChEMBL Activity Pipeline.

Fetches bioactivity data from ChEMBL database and processes it through
Bronze → Silver → Gold layers.

Entity: Bioactivity measurements (IC50, Ki, EC50, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLActivityPipeline(BasePipeline):
    """Pipeline for ChEMBL bioactivity data.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)

================================================================================
File: activity_transformer.py
Path: pipelines\chembl\activity_transformer.py
================================================================================
"""ChEMBL Activity Transformer.

Transforms Bronze records to Silver format (Activity entity inflation).
Uses declarative field_specs DSL for mapping where applicable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.field_specs import (
    FieldGroup,
    FieldSpec,
    float_fields,
    int_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.core.transform_utils import flatten_nested_dict
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Bioactivity
from bioetl.domain.transformations import safe_float
from bioetl.domain.value_objects import validate_taxonomy_id_str

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# Mapping for ligand efficiency fields extraction (nested dict)
_LIGAND_EFFICIENCY_FIELDS: dict[str, Any] = {
    "bei": safe_float,
    "le": safe_float,
    "lle": safe_float,
    "sei": safe_float,
}

# Mapping for action type fields extraction (nested dict)
_ACTION_TYPE_FIELDS: dict[str, Any] = {
    "action_type": None,
    "description": None,
    "parent_type": None,
}

# ============================================================================
# Declarative field groups for Activity entity
# ============================================================================

_IDENTIFIERS = FieldGroup(
    name="identifiers",
    fields=(
        *simple_fields("target_chembl_id", "assay_chembl_id", "document_chembl_id"),
        *int_fields("record_id", "src_id"),
    ),
)

_MOLECULE_TARGET_ASSAY = FieldGroup(
    name="molecule_target_assay",
    fields=(
        *simple_fields(
            "canonical_smiles",
            "molecule_pref_name",
            "parent_molecule_chembl_id",
            "target_pref_name",
            "target_organism",
        ),
        # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
        FieldSpec(
            "target_tax_id",
            target="target_taxonomy_id",
            converter=validate_taxonomy_id_str,
        ),
        *simple_fields(
            "assay_type",
            "assay_description",
            "assay_variant_accession",
            "assay_variant_mutation",
            "bao_endpoint",
            "bao_format",
            "bao_label",
        ),
    ),
)

_RAW_VALUES = FieldGroup(
    name="raw_values",
    fields=(
        *simple_fields("type", "units", "relation", "text_value"),
        *float_fields("value", "upper_value"),
    ),
)

_STANDARD_VALUES = FieldGroup(
    name="standard_values",
    fields=(
        *simple_fields(
            "standard_type",
            "standard_units",
            "standard_relation",
            "standard_text_value",
        ),
        *float_fields("standard_value", "standard_upper_value", "pchembl_value"),
        *int_fields("standard_flag"),
    ),
)

_UNIT_FIELDS = FieldGroup(
    name="units",
    fields=simple_fields("qudt_units", "uo_units"),
)

_QUALITY_ANNOTATIONS = FieldGroup(
    name="quality_annotations",
    fields=(
        *simple_fields(
            "document_journal",
            "activity_comment",
            "data_validity_comment",
            "data_validity_description",
        ),
        *int_fields("document_year", "potential_duplicate", "toid"),
    ),
)

# All declarative field groups
_ACTIVITY_GROUPS: tuple[FieldGroup, ...] = (
    _IDENTIFIERS,
    _MOLECULE_TARGET_ASSAY,
    _RAW_VALUES,
    _STANDARD_VALUES,
    _UNIT_FIELDS,
    _QUALITY_ANNOTATIONS,
)


class ActivityTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze records to silver.

    Uses the unified Bioactivity entity for domain representation.
    """

    entity_class = Bioactivity
    primary_id_field = "activity_id"

    def _extract_ligand_efficiency(
        self, le_data: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Extract ligand efficiency metrics from nested dictionary.

        Args:
            le_data: Nested ligand efficiency dictionary from ChEMBL API.
                     Expected keys: bei, le, lle, sei.

        Returns:
            Flat dictionary with prefixed keys and float-converted values.
        """
        return flatten_nested_dict(
            le_data, "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS
        )

    def _extract_action_type(
        self, action_data: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Extract action type fields from nested dictionary.

        Args:
            action_data: Nested action type dictionary from ChEMBL API.
                         Expected keys: action_type, description, parent_type.

        Returns:
            Flat dictionary with prefixed keys.
        """
        return flatten_nested_dict(action_data, "action_type_", _ACTION_TYPE_FIELDS)

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract Activity business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated activity_id value.

        Returns:
            Dictionary of Activity business fields.

        """
        # Validate secondary required field
        molecule_id = self._get_required_field(record, "molecule_chembl_id")

        return {
            # Primary and secondary identifiers (manual - need special handling)
            "activity_id": str(primary_id),
            "molecule_chembl_id": str(molecule_id),
            # Declarative field groups
            **map_field_groups(record, _ACTIVITY_GROUPS),
            # Nested dict extraction (not declarative)
            **self._extract_ligand_efficiency(
                cast("dict[str, Any] | None", record.get("ligand_efficiency"))
            ),
            **self._extract_action_type(
                cast("dict[str, Any] | None", record.get("action_type"))
            ),
            # JSON serialization
            "activity_properties": self.serialize_json(
                record.get("activity_properties")
            ),
        }

================================================================================
File: assay.py
Path: pipelines\chembl\assay.py
================================================================================
"""ChEMBL Assay Pipeline.

Fetches assay definitions from ChEMBL database and processes them through
Bronze → Silver → Gold layers.

Entity: Bioassay definitions (binding, functional, ADMET, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLAssayPipeline(BasePipeline):
    """Pipeline for ChEMBL assay data.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)

================================================================================
File: assay_parameters.py
Path: pipelines\chembl\assay_parameters.py
================================================================================
# src/bioetl/application/pipelines/chembl/assay_parameters.py
"""ChEMBL Assay Parameters Pipeline.

Fetches assay parameters from ChEMBL database and processes through
Bronze -> Silver -> Gold layers.

Entity: Assay Parameters (experimental conditions for bioassays)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLAssayParametersPipeline(BasePipeline):
    """Pipeline for ChEMBL assay parameters data.

    Assay parameters contain experimental conditions such as concentrations,
    pH, temperature, incubation time, etc. for bioassays.
    M:1 relationship with Assay (many parameters -> one assay via assay_chembl_id FK).

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)

================================================================================
File: assay_parameters_transformer.py
Path: pipelines\chembl\assay_parameters_transformer.py
================================================================================
# src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py
"""ChEMBL AssayParameters Transformer.

Transforms Bronze records to Silver format (AssayParameters entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.field_specs import (
    FieldGroup,
    FieldSpec,
    float_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities.chembl_assay_parameters import AssayParameters

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# Known parameter types for validation/metrics
KNOWN_PARAM_TYPES: frozenset[str] = frozenset(
    {
        "CONC",
        "PH",
        "TEMP",
        "TIME",
        "CELL_COUNT",
        "SERUM",
        "DOSE",
        "VOLUME",
        "WAVELENGTH",
        "PERCENT",
        "PRESSURE",
        "HUMIDITY",
        "PASSAGE",
        "CELL_DENSITY",
        "INCUBATION",
    }
)


# ============================================================================
# Declarative field groups for AssayParameters entity
# ============================================================================

_RAW_VALUES = FieldGroup(
    name="raw_values",
    fields=(
        *simple_fields("relation", "units", "text_value", "comments"),
        *float_fields("value"),
    ),
)

_STANDARD_VALUES = FieldGroup(
    name="standard_values",
    fields=(
        *simple_fields(
            "standard_type",
            "standard_relation",
            "standard_units",
            "standard_text_value",
        ),
        FieldSpec(
            "standard_value", converter=lambda v: float(v) if v is not None else None
        ),
    ),
)

_ASSAY_PARAMS_GROUPS: tuple[FieldGroup, ...] = (
    _RAW_VALUES,
    _STANDARD_VALUES,
)


class AssayParametersTransformer(BaseChemblTransformer):
    """Transforms ChEMBL assay_parameters bronze records to silver.

    Handles:
        - Numeric value normalization (round to 10 decimals via safe_float)
        - Unit standardization awareness
        - Text value preservation
        - Parameter type normalization
        - Heterogeneous value handling (numeric vs text)

    Entity Class: AssayParameters
    Primary ID Field: assay_param_id
    """

    entity_class = AssayParameters
    primary_id_field = "assay_param_id"

    def _normalize_type(self, param_type: Any) -> str | None:
        """Normalize parameter type to uppercase.

        Uses DataNormalizationService via DI for consistent normalization.

        Args:
            param_type: Raw parameter type from API (may be Any type).

        Returns:
            Normalized uppercase type or None if not available.
        """
        if param_type is None:
            return None
        normalized = self._data_normalizer.normalize_to_string(param_type)
        return normalized.upper() if normalized else None

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract AssayParameters business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated assay_param_id value.

        Returns:
            Dictionary of AssayParameters business fields.
        """
        # Normalize type
        raw_type = record.get("type")
        normalized_type = self._normalize_type(raw_type)

        # Build business data dictionary
        business_data: dict[str, Any] = {
            # Primary identifier (integer)
            "assay_param_id": int(primary_id),
            # Foreign key
            "assay_chembl_id": record.get("assay_chembl_id"),
            # Normalized type
            "type": normalized_type,
        }

        # Apply declarative field groups
        business_data.update(map_field_groups(record, _ASSAY_PARAMS_GROUPS))

        return business_data

    def _has_any_value(self, record: BronzeRecord) -> bool:
        """Check if record has at least one value field populated.

        Used for DQ validation - parameters without any values
        are flagged but not rejected.

        Args:
            record: Bronze record to check.

        Returns:
            True if at least one value field is present.
        """
        return any(
            [
                record.get("value") is not None,
                record.get("text_value") is not None,
                record.get("standard_value") is not None,
                record.get("standard_text_value") is not None,
            ]
        )


__all__ = ["KNOWN_PARAM_TYPES", "AssayParametersTransformer"]

================================================================================
File: assay_transformer.py
Path: pipelines\chembl\assay_transformer.py
================================================================================
"""ChEMBL Assay Transformer.

Transforms Bronze records to Silver format (Assay entity inflation).
Uses declarative field_specs DSL for mapping where applicable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.field_specs import (
    FieldGroup,
    FieldSpec,
    int_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.core.transform_utils import flatten_nested_dict
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Assay
from bioetl.domain.transformations import (
    safe_float,
    safe_str,
)
from bioetl.domain.value_objects import validate_taxonomy_id

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# Mapping for variant sequence fields extraction (from ChEMBL nested structure)
# Source field is 'tax_id' from API, will be renamed to 'taxonomy_id' via renames
_VARIANT_FIELDS: dict[str, Any] = {
    "accession": safe_str,
    "isoform": safe_str,
    "mutation": safe_str,
    "organism": safe_str,
    "sequence": safe_str,
    "tax_id": validate_taxonomy_id,  # Will be renamed to taxonomy_id
}

# Rename mapping for variant fields (tax_id -> taxonomy_id for NCBI consistency)
_VARIANT_RENAMES: dict[str, str] = {
    "variant_tax_id": "variant_taxonomy_id",
}


def _extract_variant(data: dict[str, Any] | None) -> dict[str, Any]:
    """Extract variant sequence fields using flatten_nested_dict.

    Args:
        data: Nested variant_sequence dictionary from ChEMBL API.
            Expected structure: {"accession": "P12345", "mutation": "V600E", ...}

    Returns:
        Flattened dictionary with variant_ prefixed keys.
        tax_id is renamed to taxonomy_id for NCBI consistency.

    """
    return flatten_nested_dict(
        data, "variant_", _VARIANT_FIELDS, renames=_VARIANT_RENAMES
    )


# ============================================================================
# Declarative field groups for Assay entity
# ============================================================================

_IDENTIFIERS = FieldGroup(
    name="identifiers",
    fields=(
        *simple_fields(
            "target_chembl_id",
            "document_chembl_id",
            "cell_chembl_id",
            "tissue_chembl_id",
            "src_assay_id",
            "aidx",
        ),
        *int_fields("src_id"),
    ),
)

_CLASSIFICATION = FieldGroup(
    name="classification",
    fields=simple_fields(
        "assay_type",
        "assay_type_description",
        "assay_category",
        "assay_test_type",
        "assay_group",
    ),
)

_BIOLOGICAL_CONTEXT = FieldGroup(
    name="biological_context",
    fields=(
        *simple_fields(
            "assay_organism",
            "assay_cell_type",
            "assay_tissue",
            "assay_strain",
            "assay_subcellular_fraction",
            "bao_format",
            "bao_label",
        ),
        # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
        FieldSpec(
            "assay_tax_id", target="assay_taxonomy_id", converter=validate_taxonomy_id
        ),
    ),
)

_METADATA = FieldGroup(
    name="metadata",
    fields=(
        *simple_fields(
            "description",
            "confidence_description",
            "relationship_type",
            "relationship_description",
            "assay_pref_name",
        ),
        *int_fields("confidence_score"),
        FieldSpec("score", converter=safe_float),
    ),
)

# All declarative field groups
_ASSAY_GROUPS: tuple[FieldGroup, ...] = (
    _IDENTIFIERS,
    _CLASSIFICATION,
    _BIOLOGICAL_CONTEXT,
    _METADATA,
)


class AssayTransformer(BaseChemblTransformer):
    """Transforms ChEMBL assay bronze records to silver."""

    entity_class = Assay
    primary_id_field = "assay_chembl_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract Assay business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated assay_chembl_id value.

        Returns:
            Dictionary of Assay business fields.

        """
        return {
            # Primary identifier
            "assay_chembl_id": str(primary_id),
            # Declarative field groups
            **map_field_groups(record, _ASSAY_GROUPS),
            # Nested dict extraction (variant)
            **_extract_variant(
                cast("dict[str, Any] | None", record.get("variant_sequence"))
            ),
            # JSON serialization
            "variant_sequence_json": self.serialize_json(
                record.get("variant_sequence")
            ),
            "assay_classifications": self.serialize_json(
                record.get("assay_classifications")
            ),
            "assay_parameters": self.serialize_json(record.get("assay_parameters")),
        }

================================================================================
File: base_chembl_transformer.py
Path: pipelines\chembl\base_chembl_transformer.py
================================================================================
"""Base ChEMBL Transformer.

Provides common transformation logic for all ChEMBL entity transformers.
Implements Template Method pattern to eliminate duplication across:
- ActivityTransformer
- AssayTransformer
- PublicationTransformer
- MoleculeTransformer
- TargetTransformer
- TargetComponentTransformer
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.services import IdentityService

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord, SilverRecord


class BaseChemblTransformer(BaseTransformer):
    """Base class for all ChEMBL transformers.

    Provides common field extraction and mapping logic.
    Implements Template Method pattern for unified transformation flow.

    Subclasses MUST define:
    - `entity_class`: The domain entity class to create
    - `primary_id_field`: Field name of the primary identifier

    Subclasses MUST implement:
    - `_extract_business_data()`: Entity-specific field extraction

    Example:
        >>> class ActivityTransformer(BaseChemblTransformer):
        ...     entity_class = Activity
        ...     primary_id_field = "activity_id"
        ...
        ...     def _extract_business_data(self, record, primary_id):
        ...         return {"activity_id": str(primary_id), ...}

    """

    # Class variables that subclasses must override
    entity_class: ClassVar[type[BaseEntity]]
    primary_id_field: ClassVar[str]

    def __init__(
        self,
        provider: str = "chembl",
        entity_type: str | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ) -> None:
        """Initialize ChEMBL transformer.

        Args:
            provider: Data provider identifier. Defaults to 'chembl'.
            entity_type: Entity type for metrics labels. If None, derived from
                entity_class name (e.g., Activity → "activity").
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names (RULES.md §5.4).
            data_normalizer: Data normalization service for text normalization
                (DOI, PMID, authors, HTML). Defaults to DataNormalizationService.

        """
        # Derive entity_type from entity_class if not provided
        resolved_entity_type = entity_type
        if resolved_entity_type is None and hasattr(self, "entity_class"):
            resolved_entity_type = self.entity_class.__name__.lower()

        super().__init__(
            provider,
            entity_type=resolved_entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Template method implementing common ChEMBL transformation flow.

        Steps:
        1. Validate and extract primary ID
        2. Generate entity_id using standard format
        3. Extract business data (delegated to subclass)
        4. Compute content hash
        5. Create domain entity
        6. Convert to SilverRecord

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from ChEMBL API.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        """
        # 1. Validate primary ID
        primary_id = self._get_required_field(record, self.primary_id_field)

        # 2. Generate entity ID using IdentityService
        entity_id = self.compute_entity_id(
            source_id=str(primary_id),
            record={self.primary_id_field: str(primary_id)},
        )

        # 3. Extract business data (delegated to subclass)
        business_data = self._extract_business_data(record, primary_id)

        # 4. Compute content hash
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # 5. Create domain entity
        entity = self._create_entity(
            self.entity_class,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # 6. Convert to SilverRecord
        return cast("SilverRecord", self.entity_to_silver_record(entity))

    @abstractmethod
    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract business data from the bronze record.

        Subclasses MUST implement this method to extract entity-specific fields.
        The primary_id is already validated and passed for convenience.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated primary identifier value.

        Returns:
            Dictionary of business data fields for entity creation.

        Example:
            >>> def _extract_business_data(self, record, primary_id):
            ...     return {
            ...         "activity_id": str(primary_id),
            ...         "molecule_chembl_id": record.get("molecule_chembl_id"),
            ...         ...
            ...     }

        """
        ...

================================================================================
File: cell_line.py
Path: pipelines\chembl\cell_line.py
================================================================================
"""ChEMBL Cell Line Pipeline.

Fetches cell lines from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Cell Lines (biological objects for in vitro experiments)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLCellLinePipeline(BasePipeline):
    """Pipeline for ChEMBL cell line data.

    Cell lines are biological objects used for in vitro experiments.
    They have M:N relationship with Assay (via assay.cell_chembl_id FK).

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)

================================================================================
File: cell_line_transformer.py
Path: pipelines\chembl\cell_line_transformer.py
================================================================================
"""ChEMBL Cell Line Transformer.

Transforms Bronze records to Silver format (CellLine entity inflation).

Note: Business logic functions are delegated to domain layer per REFACTOR-004.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import CellLine
from bioetl.domain.value_objects import TaxonomyId

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class CellLineTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze cell line records to silver.

    Cell lines are biological objects used for in vitro experiments.
    They have M:N relationship with Assay (via assay.cell_chembl_id FK).
    """

    entity_class = CellLine
    primary_id_field = "cell_chembl_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract CellLine business data from bronze record.

        Delegates normalization/validation to domain layer per REFACTOR-004.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated cell_chembl_id value.

        Returns:
            Dictionary of CellLine business fields.

        """
        normalizer = self._data_normalizer

        # Get cell_name with strip normalization using DI service
        cell_name = normalizer.normalize_to_string(record.get("cell_name"))

        # Validate taxonomy_id using TaxonomyId Value Object
        raw_tax_id = record.get("cell_source_tax_id")
        taxonomy_id_vo = TaxonomyId.from_raw(
            cast("str | int | None", raw_tax_id) if raw_tax_id is not None else None
        )
        cell_source_taxonomy_id = taxonomy_id_vo.value if taxonomy_id_vo else None

        return {
            # Primary identifier
            "cell_chembl_id": str(primary_id),
            # Core metadata
            "cell_name": cell_name,
            "cell_description": record.get("cell_description"),
            # Source information
            "cell_source_tissue": record.get("cell_source_tissue"),
            "cell_source_organism": record.get("cell_source_organism"),
            # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
            "cell_source_taxonomy_id": cell_source_taxonomy_id,
            # Cell type classification
            "cell_type": normalizer.normalize_to_string(record.get("cell_type")),
            # External identifiers (strip, NULL if empty) using DI normalization
            "cellosaurus_id": normalizer.normalize_to_string(
                record.get("cellosaurus_id")
            ),
            "clo_id": normalizer.normalize_to_string(record.get("clo_id")),
            "cl_lincs_id": normalizer.normalize_to_string(record.get("cl_lincs_id")),
            "efo_id": normalizer.normalize_to_string(record.get("efo_id")),
        }

================================================================================
File: compound_record.py
Path: pipelines\chembl\compound_record.py
================================================================================
"""ChEMBL Compound Record Pipeline.

Fetches compound records from ChEMBL database and processes through
Bronze -> Silver -> Gold layers.

Entity: Compound Records (links molecules to documents with original names)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLCompoundRecordPipeline(BasePipeline):
    """Pipeline for ChEMBL compound record data.

    Compound records link molecules to documents and contain the original
    compound name as it appears in the publication.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)

================================================================================
File: compound_record_transformer.py
Path: pipelines\chembl\compound_record_transformer.py
================================================================================
"""ChEMBL Compound Record Transformer.

Transforms Bronze records to Silver format (CompoundRecord entity inflation).

Note: Business logic functions are delegated to domain layer per REFACTOR-004.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import CompoundRecord
from bioetl.domain.transformations import safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class CompoundRecordTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze compound record data to silver.

    Compound records link molecules to documents and contain the original
    compound name as it appears in the publication.
    """

    entity_class = CompoundRecord
    primary_id_field = "record_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract CompoundRecord business data from bronze record.

        Delegates normalization to domain layer per REFACTOR-004.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated record_id value.

        Returns:
            Dictionary of CompoundRecord business fields.

        """
        normalizer = self._data_normalizer

        # Get record_id as int
        record_id = safe_int(primary_id)

        # Get src_id - required field
        src_id = safe_int(record.get("src_id"))

        # Get molecule_chembl_id and document_chembl_id - required fields
        # Use DI normalization service
        molecule_chembl_id = normalizer.normalize_to_string(
            record.get("molecule_chembl_id")
        )
        document_chembl_id = normalizer.normalize_to_string(
            record.get("document_chembl_id")
        )

        return {
            # Primary identifier
            "record_id": record_id,
            # Foreign keys
            "molecule_chembl_id": molecule_chembl_id,
            "document_chembl_id": document_chembl_id,
            # Original compound names (strip whitespace, NULL if empty)
            "compound_key": normalizer.normalize_to_string(record.get("compound_key")),
            "compound_name": normalizer.normalize_to_string(
                record.get("compound_name")
            ),
            # Source information
            "src_id": src_id,
            "src_compound_id": normalizer.normalize_to_string(
                record.get("src_compound_id")
            ),
        }

================================================================================
File: molecule.py
Path: pipelines\chembl\molecule.py
================================================================================
"""ChEMBL Molecule Pipeline.

Fetches molecules from ChEMBL database and processes through
Bronze -> Silver -> Gold layers.

Entity: Chemical Compounds (small molecules, antibodies, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLMoleculePipeline(BasePipeline):
    """Pipeline for ChEMBL molecule data.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)

================================================================================
File: molecule_transformer.py
Path: pipelines\chembl\molecule_transformer.py
================================================================================
"""ChEMBL Molecule Transformer.

Transforms Bronze records to Silver format (Molecule entity inflation).
Uses declarative field_specs DSL for mapping where applicable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.field_specs import (
    FieldGroup,
    int_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.core.transform_utils import flatten_nested_dict
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Molecule
from bioetl.domain.transformations import safe_float, safe_int
from bioetl.domain.value_objects import SMILES, InChIKey

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# Field mappings for molecule nested structures
_HIERARCHY_FIELDS: dict[str, Any] = {
    "parent_chembl_id": None,
    "active_chembl_id": None,
    "molecule_chembl_id": None,
}

# Rename mapping for hierarchy fields (molecule_chembl_id -> child_chembl_id)
_HIERARCHY_RENAMES: dict[str, str] = {
    "hierarchy_molecule_chembl_id": "hierarchy_child_chembl_id",
}

_PROPERTIES_FIELDS: dict[str, Any] = {
    "alogp": safe_float,
    "mw_freebase": safe_float,
    "full_mwt": safe_float,
    "hba": safe_int,
    "hbd": safe_int,
    "psa": safe_float,
    "rtb": safe_int,
    "num_ro5_violations": safe_int,
    "heavy_atoms": safe_int,
    "aromatic_rings": safe_int,
    "qed_weighted": safe_float,
    "full_molformula": None,
    "ro3_pass": None,
}

# Rename mapping for properties fields (num_ro5_violations -> ro5_violations)
_PROPERTIES_RENAMES: dict[str, str] = {
    "property_num_ro5_violations": "property_ro5_violations",
}

_STRUCTURES_FIELDS: dict[str, Any] = {
    "canonical_smiles": None,
    "standard_inchi": None,
    "standard_inchi_key": None,
}

# Rename mapping for structures fields (standard_inchi_key -> inchikey for IUPAC/PubChem consistency)
_STRUCTURES_RENAMES: dict[str, str] = {
    "standard_inchi_key": "inchikey",
}

# JSON fields to serialize
_JSON_FIELDS: tuple[str, ...] = (
    "molecule_hierarchy",
    "molecule_properties",
    "molecule_structures",
    "molecule_synonyms",
    "cross_references",
    "atc_classifications",
)


# ============================================================================
# Declarative field groups for Molecule entity
# ============================================================================

_CORE_METADATA = FieldGroup(
    name="core_metadata",
    fields=(
        *simple_fields("pref_name", "molecule_type", "structure_type"),
        *int_fields("max_phase", "first_approval"),
    ),
)

_MOLECULE_FLAGS = FieldGroup(
    name="molecule_flags",
    fields=(
        *simple_fields(
            "oral", "parenteral", "topical", "therapeutic_flag", "withdrawn_flag"
        ),
        *int_fields(
            "black_box_warning",
            "natural_product",
            "first_in_class",
            "prodrug",
            "inorganic_flag",
            "polymer_flag",
            "chirality",
            "dosed_ingredient",
            "availability_type",
        ),
    ),
)

_ADDITIONAL_METADATA = FieldGroup(
    name="additional_metadata",
    fields=(
        *simple_fields(
            "usan_stem",
            "usan_stem_definition",
            "usan_substem",
            "helm_notation",
            "molecule_species",
        ),
        *int_fields("usan_year"),
    ),
)

# All declarative field groups
_MOLECULE_GROUPS: tuple[FieldGroup, ...] = (
    _CORE_METADATA,
    _MOLECULE_FLAGS,
    _ADDITIONAL_METADATA,
)


class MoleculeTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze molecule records to silver."""

    entity_class = Molecule
    primary_id_field = "molecule_chembl_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract Molecule business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated molecule_chembl_id value.

        Returns:
            Dictionary of Molecule business fields.

        """
        # Cast to dict for type-safe access to .get() method
        rec = cast("dict[str, Any]", record)

        # Extract structure fields
        structure_data = flatten_nested_dict(
            cast("dict[str, Any] | None", rec.get("molecule_structures")),
            "",  # No prefix - unified naming with PubChem
            _STRUCTURES_FIELDS,
            renames=_STRUCTURES_RENAMES,
        )

        # Validate InChI Key using Value Object (returns None for invalid/empty)
        inchikey = InChIKey.from_raw(structure_data.get("inchikey"))
        structure_data["inchikey"] = str(inchikey) if inchikey else None

        # Validate SMILES using Value Object (returns None for invalid/empty)
        # ChEMBL provides canonical_smiles, so mark as canonical
        smiles = SMILES.from_raw(
            structure_data.get("canonical_smiles"),
            is_canonical=True,
        )
        structure_data["canonical_smiles"] = str(smiles) if smiles else None

        return {
            # Primary identifier
            "molecule_chembl_id": str(primary_id),
            # Declarative field groups (uses BronzeRecord type)
            **map_field_groups(record, _MOLECULE_GROUPS),
            # JSON serialization using helper method
            **self.serialize_json_fields(rec, _JSON_FIELDS),
            # Nested dict extraction with renames
            **flatten_nested_dict(
                cast("dict[str, Any] | None", rec.get("molecule_hierarchy")),
                "hierarchy_",
                _HIERARCHY_FIELDS,
                renames=_HIERARCHY_RENAMES,
            ),
            **flatten_nested_dict(
                cast("dict[str, Any] | None", rec.get("molecule_properties")),
                "property_",
                _PROPERTIES_FIELDS,
                renames=_PROPERTIES_RENAMES,
            ),
            # Structure data with validated InChI Key and SMILES
            **structure_data,
        }

================================================================================
File: protein_class.py
Path: pipelines\chembl\protein_class.py
================================================================================
"""ChEMBL Protein Classification Pipeline.

Fetches protein classification hierarchy from ChEMBL database and processes
through Bronze -> Silver -> Gold layers.

Entity: Protein Classification hierarchy (enzyme classes, receptor types, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLProteinClassPipeline(BasePipeline):
    """Pipeline for ChEMBL protein classification data.

    Hierarchical classification of protein targets (enzymes, receptors,
    ion channels, transporters, etc.). Self-referencing structure with
    up to 8 levels of depth. Reference table (~1,500 records).

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)

================================================================================
File: protein_class_transformer.py
Path: pipelines\chembl\protein_class_transformer.py
================================================================================
"""ChEMBL Protein Classification Transformer.

Transforms Bronze records to Silver format (ProteinClassification entity inflation).
Uses declarative field_specs DSL for mapping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.field_specs import (
    FieldGroup,
    int_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import ProteinClassification
from bioetl.domain.transformations import safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# Declarative field groups for ProteinClassification entity
_HIERARCHY = FieldGroup(
    name="hierarchy",
    fields=int_fields("parent_id", "class_level"),
)

_CLASSIFICATION_DATA = FieldGroup(
    name="classification_data",
    fields=simple_fields(
        "pref_name",
        "short_name",
        "protein_class_desc",
        "definition",
    ),
)

_METADATA = FieldGroup(
    name="metadata",
    fields=int_fields("sort_order", "replaced_by", "downgraded"),
)

_PROTEIN_CLASS_GROUPS: tuple[FieldGroup, ...] = (
    _HIERARCHY,
    _CLASSIFICATION_DATA,
    _METADATA,
)


class ProteinClassTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze protein_class records to silver.

    Handles hierarchical protein classification data.
    Primary key is protein_class_id (integer).
    """

    entity_class = ProteinClassification
    primary_id_field = "protein_class_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract ProteinClassification business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated protein_class_id value.

        Returns:
            Dictionary of ProteinClassification business fields.

        """
        return {
            # Primary identifier (int)
            "protein_class_id": safe_int(primary_id),
            # Declarative field groups
            **map_field_groups(record, _PROTEIN_CLASS_GROUPS),
        }

================================================================================
File: publication.py
Path: pipelines\chembl\publication.py
================================================================================
"""ChEMBL Publication Pipeline.

Fetches scientific publications from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Scientific Publications (journal articles, patents)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).

.. versionchanged:: 2.0.0
    Renamed from document to publication (ADR-024).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLPublicationPipeline(BasePipeline):
    """Pipeline for ChEMBL publication data.

    Transformer is injected via DI from GenericPipelineFactory.

    .. versionchanged:: 2.0.0
        Renamed from ChEMBLDocumentPipeline (ADR-024).
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)

================================================================================
File: publication_similarity.py
Path: pipelines\chembl\publication_similarity.py
================================================================================
"""ChEMBL Publication Similarity Pipeline.

Fetches publication similarity data from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Publication Similarity (Tanimoto coefficients between publications)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).

.. versionchanged:: 2.0.0
    Renamed from document_similarity to publication_similarity (ADR-024).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLPublicationSimilarityPipeline(BasePipeline):
    """Pipeline for ChEMBL publication similarity data.

    Extracts precomputed similarity relationships between publications
    based on Tanimoto coefficients calculated from:
    - Molecules described in publications (mol_tani)
    - Targets described in publications (tid_tani)

    Transformer is injected via DI from GenericPipelineFactory.

    .. versionchanged:: 2.0.0
        Renamed from ChEMBLDocumentSimilarityPipeline (ADR-024).
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)

================================================================================
File: publication_similarity_transformer.py
Path: pipelines\chembl\publication_similarity_transformer.py
================================================================================
"""ChEMBL Publication Similarity Transformer.

Transforms Bronze records to Silver format (DocumentSimilarity entity).
Computes derived Tanimoto metrics (avg_tani, max_tani).

.. versionchanged:: 2.0.0
    Renamed from document_similarity_transformer to publication_similarity_transformer (ADR-024).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.field_specs import normalize_pmid
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import DocumentSimilarity
from bioetl.domain.transformations import safe_float, safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class PublicationSimilarityTransformer(BaseChemblTransformer):
    """Transforms ChEMBL publication similarity records.

    Computes derived metrics:
    - avg_tani: average of tid_tani and mol_tani
    - max_tani: maximum of tid_tani and mol_tani

    .. versionchanged:: 2.0.0
        Renamed from DocumentSimilarityTransformer (ADR-024).
    """

    entity_class = DocumentSimilarity
    primary_id_field = "sim_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract PublicationSimilarity business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated sim_id value.

        Returns:
            Dictionary of DocumentSimilarity business fields.

        """
        # Extract and validate Tanimoto coefficients
        tid_tani = safe_float(record.get("tid_tani"))
        mol_tani = safe_float(record.get("mol_tani"))

        # Compute derived Tanimoto metrics
        avg_tani: float | None = None
        max_tani: float | None = None

        if tid_tani is not None and mol_tani is not None:
            avg_tani = round((tid_tani + mol_tani) / 2, 6)
            max_tani = round(max(tid_tani, mol_tani), 6)
        elif tid_tani is not None:
            avg_tani = round(tid_tani, 6)
            max_tani = round(tid_tani, 6)
        elif mol_tani is not None:
            avg_tani = round(mol_tani, 6)
            max_tani = round(mol_tani, 6)

        return {
            # Primary key
            "sim_id": int(primary_id),
            # Foreign keys
            "doc_1": safe_int(record.get("doc_1")),
            "doc_2": safe_int(record.get("doc_2")),
            # PubMed identifiers (normalized to string)
            "pubmed_id1": normalize_pmid(record.get("pubmed_id1")),
            "pubmed_id2": normalize_pmid(record.get("pubmed_id2")),
            # Tanimoto coefficients
            "tid_tani": tid_tani,
            "mol_tani": mol_tani,
            # Derived metrics
            "avg_tani": avg_tani,
            "max_tani": max_tani,
        }

================================================================================
File: publication_term.py
Path: pipelines\chembl\publication_term.py
================================================================================
"""ChEMBL Publication Term Pipeline.

Extracts terms (MeSH headings, keywords, concepts) from ChEMBL Publication
records and processes through Bronze → Silver → Gold layers.

Entity: Publication Terms (derived from Publication)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

This is a derived entity pipeline - it extracts nested term data
from Publication (ChEMBL Document) API responses and flattens the 1:M relationship.

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).

.. versionchanged:: 2.0.0
    Renamed from document_term to publication_term (ADR-024).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLPublicationTermPipeline(BasePipeline):
    """Pipeline for ChEMBL publication term data.

    This pipeline extracts and flattens term data from Publication records:
    - MeSH headings and qualifiers
    - Author keywords
    - ChEMBL concepts

    Each Publication may produce multiple Term records (1:M relationship).

    Transformer is injected via DI from GenericPipelineFactory.

    .. versionchanged:: 2.0.0
        Renamed from ChEMBLDocumentTermPipeline (ADR-024).
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)

================================================================================
File: publication_term_transformer.py
Path: pipelines\chembl\publication_term_transformer.py
================================================================================
"""ChEMBL Publication Term Transformer.

Transforms Publication records to extract and flatten associated terms.
This is a derived entity transformer - it extracts nested term data
from Publication (ChEMBL Document) API responses and flattens the 1:M relationship.

Uses declarative field_specs DSL for mapping.

.. versionchanged:: 2.0.0
    Renamed from document_term_transformer to publication_term_transformer (ADR-024).
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import DocumentTerm

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class PublicationTermTransformer(BaseChemblTransformer):
    """Transforms ChEMBL publication records to extract flattened term records.

    This transformer extracts nested term data from Publication (ChEMBL Document)
    API responses and flattens the 1:M relationship (one Publication → multiple Terms).

    Term types extracted:
    - MESH_HEADING: MeSH descriptor terms from mesh_terms array
    - MESH_QUALIFIER: MeSH qualifiers/subheadings from mesh_terms
    - KEYWORD: Author-provided keywords from keywords array

    Entity ID is computed as SHA256 hash of composite key:
    (document_chembl_id, term_type, normalized_term)

    Note: This transformer returns multiple records from a single Publication,
    unlike standard transformers that have 1:1 input/output mapping.

    .. versionchanged:: 2.0.0
        Renamed from DocumentTermTransformer (ADR-024).
    """

    entity_class = DocumentTerm
    primary_id_field = "document_chembl_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract term data from the record.

        Handles two cases:
        1. Pre-extracted term records (from PublicationTermDataSource) - pass through
        2. Raw publication records - extract terms from mesh_terms/keywords arrays

        Args:
            record: Bronze record (either term record or document record).
            primary_id: Validated document_chembl_id value.

        Returns:
            Dictionary of term business fields.

        """
        # Case 1: Record is already a term record (from PublicationTermDataSource)
        # These records have 'term' and 'term_type' fields directly
        if "term" in record and "term_type" in record:
            return {
                "document_chembl_id": str(record.get("document_chembl_id", primary_id)),
                "term": record.get("term", ""),
                "term_type": record.get("term_type", ""),
                "mesh_id": record.get("mesh_id"),
                "qualifier": record.get("qualifier"),
            }

        # Case 2: Raw document record - extract terms from nested arrays
        terms = list(self.extract_terms_from_document(record, str(primary_id)))
        if not terms:
            # Return empty data that will fail validation
            return {
                "document_chembl_id": str(primary_id),
                "term": "",
                "term_type": "",
                "mesh_id": None,
                "qualifier": None,
            }
        return terms[0]

    def extract_terms_from_document(
        self,
        record: BronzeRecord,
        document_chembl_id: str,
    ) -> list[dict[str, Any]]:
        """Extract and flatten all terms from a Publication record.

        Yields multiple term records from one publication.
        This is the primary method for derived entity extraction.

        Args:
            record: Raw Bronze record from ChEMBL API.
            document_chembl_id: Document ChEMBL ID.

        Yields:
            Dictionary of term business fields for each term.

        """
        terms: list[dict[str, Any]] = []

        # Extract MeSH terms
        raw_mesh_terms = record.get("mesh_terms")
        mesh_terms: list[Any] = (
            raw_mesh_terms if isinstance(raw_mesh_terms, list) else []
        )
        for mesh in mesh_terms:
            if not isinstance(mesh, dict):
                continue

            mesh_heading = mesh.get("mesh_heading")
            if mesh_heading:
                terms.append(
                    self._create_term_data(
                        document_chembl_id=document_chembl_id,
                        term=mesh_heading,
                        term_type="MESH_HEADING",
                        mesh_id=mesh.get("mesh_id"),
                        qualifier=mesh.get("mesh_qualifier"),
                    )
                )

            # Extract qualifier as separate term if present
            mesh_qualifier = mesh.get("mesh_qualifier")
            if mesh_qualifier:
                terms.append(
                    self._create_term_data(
                        document_chembl_id=document_chembl_id,
                        term=mesh_qualifier,
                        term_type="MESH_QUALIFIER",
                        mesh_id=mesh.get("mesh_id"),
                        qualifier=None,
                    )
                )

        # Extract keywords
        raw_keywords = record.get("keywords")
        keywords: list[Any] = raw_keywords if isinstance(raw_keywords, list) else []
        for keyword in keywords:
            if isinstance(keyword, str):
                stripped = keyword.strip()
                if stripped:  # Skip empty strings after stripping
                    terms.append(
                        self._create_term_data(
                            document_chembl_id=document_chembl_id,
                            term=stripped,
                            term_type="KEYWORD",
                            mesh_id=None,
                            qualifier=None,
                        )
                    )

        return terms

    def _create_term_data(
        self,
        document_chembl_id: str,
        term: str,
        term_type: str,
        mesh_id: str | None,
        qualifier: str | None,
    ) -> dict[str, Any]:
        """Create a single term data dictionary.

        Args:
            document_chembl_id: Parent document ChEMBL ID.
            term: Term text.
            term_type: Term type (MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT).
            mesh_id: MeSH identifier if applicable.
            qualifier: MeSH qualifier if applicable.

        Returns:
            Dictionary of term business fields.

        """
        return {
            "document_chembl_id": document_chembl_id,
            "term": term.strip() if term else term,
            "term_type": term_type,
            "mesh_id": mesh_id,
            "qualifier": qualifier,
        }

    def compute_term_entity_id(
        self,
        document_chembl_id: str,
        term_type: str,
        term: str,
    ) -> str:
        """Compute entity ID for a term based on composite key.

        Entity ID is SHA256 hash of: document_chembl_id:term_type:normalized_term

        Args:
            document_chembl_id: Document ChEMBL ID.
            term_type: Term type classification.
            term: Term text (will be normalized).

        Returns:
            Entity ID string (first 16 chars of SHA256 hex digest).

        """
        normalized_term = term.lower().strip() if term else ""
        composite = f"{document_chembl_id}:{term_type}:{normalized_term}"
        return hashlib.sha256(composite.encode()).hexdigest()[:16]

================================================================================
File: publication_transformer.py
Path: pipelines\chembl\publication_transformer.py
================================================================================
"""ChEMBL Publication Transformer.

Transforms Bronze records to Silver format (ChemblPublication entity inflation).
Uses declarative field_specs DSL for mapping.

.. versionchanged:: 2.0.0
    Uses ChemblPublication (canonical) instead of Document (deprecated).

.. versionchanged:: 2.1.0
    Uses DataNormalizationService for text normalization (DI pattern).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.field_specs import (
    PMID,
    FieldGroup,
    FieldSpec,
    int_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import ChemblPublication
from bioetl.domain.services import IdentityService
from bioetl.domain.value_objects import DOI, PublicationYear

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord


# Declarative field groups for ChemblPublication entity
_PUBLICATION_IDS = FieldGroup(
    name="publication_ids",
    fields=(
        # Rename pubmed_id -> pmid for cross-provider consistency (PMID standardization)
        FieldSpec("pubmed_id", target="pmid", converter=PMID),
        *simple_fields("doi"),
        # Note: patent_id excluded - not needed for unified publication schema
    ),
)

_CORE_METADATA = FieldGroup(
    name="core_metadata",
    fields=simple_fields("title", "authors", "abstract", "doc_type"),
)

_JOURNAL_INFO = FieldGroup(
    name="journal_info",
    fields=(
        *simple_fields(
            "journal",
            "journal_full_title",
            "volume",
            "issue",
            "first_page",
            "last_page",
        ),
        *int_fields("year"),
    ),
)

_SOURCE_INFO = FieldGroup(
    name="source_info",
    fields=int_fields("src_id"),
)

# All field groups for ChemblPublication entity
_PUBLICATION_GROUPS: tuple[FieldGroup, ...] = (
    _PUBLICATION_IDS,
    _CORE_METADATA,
    _JOURNAL_INFO,
    _SOURCE_INFO,
)


class PublicationTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze publication records to silver.

    Uses ChemblPublication entity (canonical name).
    Uses DataNormalizationService for text normalization (DI pattern).

    .. versionchanged:: 2.0.0
        Renamed from DocumentTransformer to PublicationTransformer (ADR-024).
    """

    entity_class = ChemblPublication
    primary_id_field = "document_chembl_id"

    def __init__(
        self,
        provider: str = "chembl",
        entity_type: str | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ) -> None:
        """Initialize ChEMBL Publication transformer.

        Args:
            provider: Data provider identifier. Defaults to 'chembl'.
            entity_type: Entity type for metrics labels. If None, derived from
                entity_class name.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names (RULES.md §5.4).
            data_normalizer: Optional data normalization service for text normalization.

        """
        super().__init__(
            provider=provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
        )

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract ChemblPublication business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated document_chembl_id value.

        Returns:
            Dictionary of ChemblPublication business fields.

        """
        # Extract base fields using declarative DSL
        data = {
            "document_chembl_id": str(primary_id),
            **map_field_groups(record, _PUBLICATION_GROUPS),
        }

        # Strip HTML from abstract field using DataNormalizationService
        normalizer = self._data_normalizer
        data["abstract"] = normalizer.strip_html_tags(data.get("abstract"))

        # Validate DOI using Value Object (returns None for invalid/empty)
        doi = DOI.from_raw(data.get("doi"))
        data["doi"] = str(doi) if doi else None

        # Validate year using PublicationYear Value Object
        year_vo = PublicationYear.from_raw(data.get("year"))
        validated_year = year_vo.value if year_vo else None
        data["year"] = validated_year

        # publication_date: ChEMBL API doesn't provide full date, only year
        # Set to null (excluded from PyArrow/Gold schemas)
        data["publication_date"] = None

        # Hash PII field (RULES.md §5.4)
        # ChEMBL authors is a concatenated string - parse to list, hash, serialize to JSON
        # Authors stored as JSON-serialized list for unified format across providers
        raw_authors = data.get("authors")
        if raw_authors:
            author_list = normalizer.parse_authors_to_list(raw_authors)
            hashed_authors = self.hash_pii_list(author_list) or []
            data["authors"] = self.serialize_json_list(hashed_authors)
        else:
            data["authors"] = None

        # Lookup metadata (direct extraction, no enrichment)
        data["_lookup_method"] = "direct"
        data["_original_id"] = str(primary_id)

        # ChEMBL release metadata (nested object from API)
        release_info = record.get("chembl_release")
        if release_info and isinstance(release_info, dict):
            data["chembl_release"] = release_info.get("chembl_release")
            data["creation_date"] = release_info.get("creation_date")
        else:
            data["chembl_release"] = None
            data["creation_date"] = None

        # System field: data source identifier
        data["_source"] = "chembl"

        # Unified publication fields (always NULL, excluded from PyArrow/Gold schemas)
        data["citation_count"] = None
        data["is_oa"] = None
        data["language"] = None

        # Cross-reference IDs (pmc_id always NULL, excluded from PyArrow/Gold schemas)
        data["pmc_id"] = None

        # DQ flags (default: no warnings or errors)
        data["_dq_warn"] = False
        data["_dq_error"] = False

        return data

================================================================================
File: target.py
Path: pipelines\chembl\target.py
================================================================================
"""ChEMBL Target Pipeline.

Fetches biological targets from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Biological Targets (proteins, complexes, organisms)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLTargetPipeline(BasePipeline):
    """Pipeline for ChEMBL target data.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)

================================================================================
File: target_component.py
Path: pipelines\chembl\target_component.py
================================================================================
"""ChEMBL Target Component Pipeline.

Fetches target components from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Target Components (protein sequences, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLTargetComponentPipeline(BasePipeline):
    """Pipeline for ChEMBL target component data.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)

================================================================================
File: target_component_transformer.py
Path: pipelines\chembl\target_component_transformer.py
================================================================================
"""ChEMBL Target Component Transformer.

Transforms Bronze records to Silver format (Target Component entity inflation).
Uses declarative field_specs DSL for mapping where applicable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.field_specs import (
    FieldGroup,
    FieldSpec,
    map_field_groups,
    simple_fields,
)
from bioetl.application.core.transform_utils import extract_list_field
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import TargetComponent
from bioetl.domain.transformations import safe_int
from bioetl.domain.value_objects import validate_taxonomy_id

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# JSON fields to serialize
_JSON_FIELDS: tuple[str, ...] = (
    "target_component_synonyms",
    "target_component_xrefs",
    "protein_classifications",
)

# Declarative field group for core metadata
_CORE_METADATA = FieldGroup(
    name="core_metadata",
    fields=(
        *simple_fields("accession", "component_type", "description", "organism"),
        # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
        FieldSpec("tax_id", target="taxonomy_id", converter=validate_taxonomy_id),
    ),
)

_TARGET_COMPONENT_GROUPS: tuple[FieldGroup, ...] = (_CORE_METADATA,)


class TargetComponentTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze target component records to silver."""

    entity_class = TargetComponent
    primary_id_field = "component_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract TargetComponent business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated component_id value.

        Returns:
            Dictionary of TargetComponent business fields.

        """
        # Cast to dict for type-safe access to .get() method
        rec = cast("dict[str, Any]", record)
        return {
            # Primary identifier (int)
            "component_id": safe_int(primary_id),
            # Declarative field groups (uses BronzeRecord type)
            **map_field_groups(record, _TARGET_COMPONENT_GROUPS),
            # JSON serialization using helper method
            **self.serialize_json_fields(rec, _JSON_FIELDS),
            # Flattened fields (extracted from protein_classifications)
            "protein_classification_ids": extract_list_field(
                cast("list[dict[str, Any]] | None", rec.get("protein_classifications")),
                "protein_classification_id",
                safe_int,
            ),
        }

================================================================================
File: target_transformer.py
Path: pipelines\chembl\target_transformer.py
================================================================================
"""ChEMBL Target Transformer.

Transforms Bronze records to Silver format (Target entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.transform_utils import (
    aggregate_nested_lists,
    extract_list_field,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Target
from bioetl.domain.transformations import safe_int
from bioetl.domain.value_objects import TaxonomyId

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class TargetTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze target records to silver."""

    entity_class = Target
    primary_id_field = "target_chembl_id"

    def _flatten_target_components(
        self, components: list[dict[str, Any]] | None
    ) -> dict[str, list[Any] | None]:
        """Flatten target components into aggregated lists.

        Args:
            components: List of component dicts from ChEMBL API.

        Returns:
            Dict with aggregated lists for accessions, IDs, types, relationships,
            descriptions, organisms, and taxonomy_ids.

        Note:
            protein_classifications are NOT available in /target endpoint.
            They are only available via /target_component endpoint.

        """
        if not components or not isinstance(components, list):
            return self._empty_component_result()

        return self._extract_basic_component_fields(components)

    def _empty_component_result(self) -> dict[str, list[Any] | None]:
        """Return empty result dict for missing components."""
        return {
            "component_accessions": None,
            "component_ids": None,
            "component_types": None,
            "component_relationships": None,
            "component_descriptions": None,
            "component_organisms": None,
            # Standardized to 'taxonomy_ids' for NCBI consistency
            "component_taxonomy_ids": None,
        }

    def _extract_basic_component_fields(
        self, components: list[dict[str, Any]]
    ) -> dict[str, list[Any] | None]:
        """Extract basic fields from component list via transform_utils."""
        # Extract taxonomy IDs and validate using TaxonomyId Value Object
        raw_tax_ids = extract_list_field(components, "tax_id", safe_int)
        validated_tax_ids: list[int] | None = None
        if raw_tax_ids:
            validated_list: list[int] = []
            for tid in raw_tax_ids:
                vo = TaxonomyId.from_raw(tid)
                if vo is not None:
                    validated_list.append(vo.value)
            validated_tax_ids = validated_list if validated_list else None

        return {
            "component_accessions": extract_list_field(components, "accession"),
            "component_ids": extract_list_field(components, "component_id", safe_int),
            "component_types": extract_list_field(components, "component_type"),
            "component_relationships": extract_list_field(components, "relationship"),
            "component_descriptions": extract_list_field(
                components, "component_description"
            ),
            "component_organisms": extract_list_field(components, "organism"),
            # Standardized to 'taxonomy_ids' for NCBI consistency
            "component_taxonomy_ids": validated_tax_ids,
        }

    def _aggregate_synonyms(
        self, components: list[dict[str, Any]] | None
    ) -> str | int | float | bool | None:
        """Aggregate synonyms from all components into a single JSON list.

        Uses aggregate_nested_lists from transform_utils.

        Args:
            components: List of component dicts from ChEMBL API.

        Returns:
            JSON string of list of synonyms, or None.

        """
        synonyms = aggregate_nested_lists(components, "target_component_synonyms")
        return self.serialize_json(synonyms) if synonyms else None

    def _aggregate_component_xrefs(
        self, components: list[dict[str, Any]] | None
    ) -> str | int | float | bool | None:
        """Aggregate cross-references from all target components.

        Uses aggregate_nested_lists from transform_utils.
        ChEMBL API stores cross-references inside each component's
        target_component_xrefs field, not at the target level.

        Args:
            components: List of component dicts from ChEMBL API.

        Returns:
            JSON string of aggregated xrefs, or None if empty.

        """
        xrefs = aggregate_nested_lists(components, "target_component_xrefs")
        return self.serialize_json(xrefs) if xrefs else None

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract Target business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated target_chembl_id value.

        Returns:
            Dictionary of Target business fields.

        """
        # Extract target_components with proper typing
        target_components = cast(
            "list[dict[str, Any]] | None", record.get("target_components")
        )

        # Extract flattened components
        flattened_components = self._flatten_target_components(target_components)

        # Handle downgraded field: convert to bool if it's 0/1
        # Use safe_int to handle "0"/"1" strings correctly
        downgraded_val = safe_int(record.get("downgraded"))
        # Default to False if missing or invalid, to ensure boolean dtype for Gold schema
        downgraded = bool(downgraded_val) if downgraded_val is not None else False

        # Validate taxonomy_id using TaxonomyId Value Object
        raw_tax_id = record.get("tax_id")
        taxonomy_id_vo = TaxonomyId.from_raw(
            cast("str | int | None", raw_tax_id) if raw_tax_id is not None else None
        )
        taxonomy_id = taxonomy_id_vo.value if taxonomy_id_vo else None

        return {
            # Primary identifier
            "target_chembl_id": str(primary_id),
            # Core metadata
            "pref_name": record.get("pref_name"),
            "target_type": record.get("target_type"),
            "organism": record.get("organism"),
            # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
            "taxonomy_id": taxonomy_id,
            "species_group_flag": record.get("species_group_flag"),
            "description": record.get("description"),
            "downgraded": downgraded,
            # Optional fields (present for specific target types)
            "dap_id": safe_int(record.get("dap_id")),
            "pipeline_stages": self.serialize_json(record.get("pipeline_stages")),
            "target_constraints": self.serialize_json(record.get("target_constraints")),
            # Complex fields (JSON serialized)
            "target_components": self.serialize_json(target_components),
            "target_component_synonyms": self._aggregate_synonyms(target_components),
            "cross_references": self._aggregate_component_xrefs(target_components),
            # Flattened components
            **flattened_components,
        }

================================================================================
File: __init__.py
Path: pipelines\common\__init__.py
================================================================================
"""Common pipeline components.

This package contains shared base classes and utilities for publication transformers
that reduce code duplication across providers.

Main Components:
- BasePublicationTransformer: Template Method base for publication transformers
- extract_author_names: Universal author name extractor for pre-combined name fields
"""

from __future__ import annotations

from bioetl.application.pipelines.common.base_publication_transformer import (
    BasePublicationTransformer,
)
from bioetl.application.pipelines.common.extractors import extract_author_names

__all__ = [
    "BasePublicationTransformer",
    "extract_author_names",
]

================================================================================
File: base_publication_transformer.py
Path: pipelines\common\base_publication_transformer.py
================================================================================
"""Base Publication Transformer with Template Method pattern.

Provides common transformation flow for publication entities from
different providers (OpenAlex, SemanticScholar, CrossRef).

Reduces code duplication by extracting shared logic:
- Business data extraction orchestration
- Primary ID validation
- Fallback lookup logging
- Entity ID and content hash computation
- Domain entity creation and Silver record conversion
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.types import BronzeRecord, SilverRecord


class BasePublicationTransformer(BaseTransformer):
    """Abstract base class for publication transformers.

    Implements Template Method pattern for unified publication transformation:
    1. Pre-extraction validation (optional hook)
    2. Extract business data (_extract_business_data - abstract)
    3. Validate primary ID exists
    4. Log fallback lookup usage if applicable
    5. Generate entity ID
    6. Compute content hash (excluding metadata fields)
    7. Create domain entity (_get_entity_class - abstract)
    8. Convert to SilverRecord

    Subclasses MUST implement:
    - _extract_business_data(): Extract and normalize fields from record
    - _get_primary_id_field(): Return primary ID field name (e.g., 'openalex_id')
    - _get_entity_class(): Return the domain entity class

    Subclasses MAY override:
    - _pre_extract_validation(): Add validation before extraction
    - _should_log_fallback_lookup(): Disable fallback logging (default: True)
    """

    @abstractmethod
    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract and normalize fields from bronze record.

        Provider-specific extraction logic. Delegates to extractors module.

        Args:
            record: Raw Bronze record from provider API.

        Returns:
            Dictionary of extracted and normalized fields.

        """
        ...

    @abstractmethod
    def _get_primary_id_field(self) -> str:
        """Return the name of the primary identifier field.

        Examples:
        - OpenAlex: 'openalex_id'
        - SemanticScholar: 'paper_id'
        - CrossRef: 'doi'

        Returns:
            Field name used as primary identifier in business_data.

        """
        ...

    @abstractmethod
    def _get_entity_class(self) -> type[BaseEntity]:
        """Return the domain entity class for this publication type.

        Returns:
            Domain entity class (e.g., OpenAlexPublicationEntity).

        """
        ...

    def _pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None:
        """Optional pre-extraction validation hook.

        Override to add validation before business data extraction.
        Raise ValueError to skip the record with validation error logging.

        Default implementation does nothing.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from provider API.
            index: Sequential index of the record in the pipeline run.

        Raises:
            ValueError: If validation fails (caught by BaseTransformer.transform).

        """

    def _should_log_fallback_lookup(self) -> bool:
        """Return True if fallback lookup logging is enabled.

        Override to disable for providers without lookup metadata
        (e.g., CrossRef which uses DOI-only lookup).

        Returns:
            True to log fallback usage, False to skip.

        """
        return True

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Unified publication transformation flow (Template Method).

        Orchestrates the transformation process:
        1. Pre-extraction validation (optional hook)
        2. Extract business data
        3. Validate primary ID exists
        4. Log fallback usage if applicable
        5. Generate entity ID
        6. Compute content hash
        7. Create domain entity
        8. Convert to SilverRecord

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from provider API.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        """
        # 1. Pre-extraction validation hook
        self._pre_extract_validation(context, record, index)

        # 2. Extract business data
        business_data = self._extract_business_data(record)

        # 3. Validate primary ID
        primary_id_field = self._get_primary_id_field()
        primary_id = business_data.get(primary_id_field)
        if not primary_id:
            context.logger.warning(
                "record_skipped_no_id",
                index=index,
                lookup_method=business_data.get("_lookup_method"),
            )
            return None

        # 4. Log fallback usage if applicable
        if self._should_log_fallback_lookup():
            lookup_method = business_data.get("_lookup_method", "unknown")
            if lookup_method in ("title_fallback", "title_only"):
                context.logger.info(
                    "fallback_lookup_used",
                    **{primary_id_field: primary_id},
                    lookup_method=lookup_method,
                    original_id=business_data.get("_original_id"),
                )

        # 5. Generate entity ID
        entity_id = self.compute_entity_id(
            source_id=primary_id,
            record={primary_id_field: primary_id},
        )

        # 6. Compute content hash (exclude metadata fields)
        hash_data = {k: v for k, v in business_data.items() if not k.startswith("_")}
        content_hash = self.compute_content_hash(hash_data, exclude_none=True)

        # 7. Create domain entity
        entity = self._create_entity(
            self._get_entity_class(),
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # 8. Convert to SilverRecord
        return cast("SilverRecord", self.entity_to_silver_record(entity))

================================================================================
File: extractors.py
Path: pipelines\common\extractors.py
================================================================================
"""Common field extraction functions for publication pipelines.

Provides reusable pure functions for extracting fields from different
provider API responses.

These functions are:
- Stateless and pure (no side effects)
- Unit testable in isolation
- Reusable across different providers

Note: Provider-specific logic (e.g., CrossRef's given+family combination)
should remain in provider-specific extractors.
"""

from __future__ import annotations

from typing import Any


def extract_author_names(
    items: list[dict[str, Any]] | None,
    name_field: str = "name",
    nested_field: str | None = None,
) -> list[str]:
    """Universal author name extractor for pre-combined name fields.

    Supports different provider formats where author names are stored
    as single strings (not combined from multiple fields):

    - OpenAlex: items=[{author: {display_name: "..."}}, ...],
                nested_field="author", name_field="display_name"
    - SemanticScholar: items=[{name: "..."}, ...],
                       name_field="name"

    Note: CrossRef uses separate "given" and "family" fields that must
    be combined - use the provider-specific extract_authors() function
    for that format.

    Args:
        items: List of author dictionaries.
        name_field: Key containing author name within the target dict.
        nested_field: If author data is nested, key to access the inner dict.

    Returns:
        List of author name strings. Empty list if items is None or empty.

    Example:
        >>> # OpenAlex format
        >>> extract_author_names(
        ...     [{"author": {"display_name": "John Doe"}}],
        ...     name_field="display_name",
        ...     nested_field="author"
        ... )
        ['John Doe']

        >>> # SemanticScholar format
        >>> extract_author_names(
        ...     [{"authorId": "123", "name": "Jane Smith"}],
        ...     name_field="name"
        ... )
        ['Jane Smith']

        >>> # Empty or None input
        >>> extract_author_names(None)
        []

    """
    if not items:
        return []

    authors: list[str] = []
    for item in items:
        # Navigate to nested dict if specified
        target = item.get(nested_field) if nested_field else item

        # Skip if target is not a dict
        if not isinstance(target, dict):
            continue

        # Extract and validate name
        name = target.get(name_field)
        if name and isinstance(name, str):
            stripped = name.strip()
            if stripped:
                authors.append(stripped)

    return authors

================================================================================
File: __init__.py
Path: pipelines\crossref\__init__.py
================================================================================
"""CrossRef pipeline components.

Transformers and utilities for CrossRef data processing.
"""

from bioetl.application.pipelines.crossref.extractors import (
    extract_authors,
    extract_content_domain,
    extract_dates,
    extract_issn_by_type,
    extract_journal_info,
    extract_license_url,
    extract_page_info,
    extract_published_date,
    extract_year,
)
from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)

__all__ = [
    "CrossRefPublicationTransformer",
    "extract_authors",
    "extract_content_domain",
    "extract_dates",
    "extract_issn_by_type",
    "extract_journal_info",
    "extract_license_url",
    "extract_page_info",
    "extract_published_date",
    "extract_year",
]

================================================================================
File: extractors.py
Path: pipelines\crossref\extractors.py
================================================================================
"""Field extraction functions for CrossRef records.

Provides pure functions for extracting and normalizing fields from
CrossRef Works API responses.

These functions are:
- Stateless and pure (no side effects)
- Unit testable in isolation
- Reusable across different transformation contexts

Note: Uses domain normalization functions and Value Objects per REFACTOR-004.
"""

from __future__ import annotations

from typing import Any

from bioetl.domain.normalization import (
    extract_first_string,
    format_date_parts,
    parse_page_range,
)
from bioetl.domain.value_objects import PublicationYear


def extract_authors(publication: dict[str, Any]) -> list[str]:
    """Extract author names from CrossRef publication.

    CrossRef stores author information in an "author" array with:
    - Personal authors: "given" and "family" fields
    - Organizational authors: "name" field only (e.g., "World Health Organization")

    Args:
        publication: CrossRef publication record.

    Returns:
        List of author names (personal: "given family", org: "name").

    Example:
        >>> extract_authors({
        ...     "author": [
        ...         {"given": "John", "family": "Doe"},
        ...         {"given": "Jane", "family": "Smith"},
        ...     ]
        ... })
        ['John Doe', 'Jane Smith']
        >>> extract_authors({"author": [{"family": "Anonymous"}]})
        ['Anonymous']
        >>> extract_authors({"author": [{"name": "World Health Organization"}]})
        ['World Health Organization']
        >>> extract_authors({})
        []

    """
    authors = []
    for author in publication.get("author", []):
        given = author.get("given", "").strip()
        family = author.get("family", "").strip()
        if given and family:
            authors.append(f"{given} {family}")
        elif family:
            authors.append(family)
        elif given:
            authors.append(given)
        elif name := author.get("name", "").strip():
            # Organizational author (e.g., "World Health Organization")
            authors.append(name)
    return authors


def extract_year(publication: dict[str, Any]) -> int | None:
    """Extract publication year from date-parts.

    Tries published-print, then published-online, then issued.
    Validates using PublicationYear Value Object for consistent range checking.

    Args:
        publication: CrossRef publication record.

    Returns:
        Publication year if valid (1800-2100), None otherwise.

    Example:
        >>> extract_year({"published-print": {"date-parts": [[2023, 6, 15]]}})
        2023
        >>> extract_year({"issued": {"date-parts": [[2021]]}})
        2021
        >>> extract_year({})
        None

    """
    for date_field in ["published-print", "published-online", "issued"]:
        date_info = publication.get(date_field, {})
        date_parts = date_info.get("date-parts", [[]])
        if date_parts and date_parts[0] and len(date_parts[0]) > 0:
            raw_year = date_parts[0][0]
            if isinstance(raw_year, int):
                year_vo = PublicationYear.from_raw(raw_year)
                if year_vo:
                    return year_vo.value
    return None


def extract_license_url(publication: dict[str, Any]) -> str | None:
    """Extract first license URL from publication.

    CrossRef may provide multiple licenses; this returns the first URL.

    Args:
        publication: CrossRef publication record.

    Returns:
        First license URL or None if not available.

    Example:
        >>> extract_license_url({
        ...     "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}]
        ... })
        'https://creativecommons.org/licenses/by/4.0/'
        >>> extract_license_url({"license": []})
        None
        >>> extract_license_url({})
        None

    """
    licenses = publication.get("license", [])
    if licenses and len(licenses) > 0:
        url: str | None = licenses[0].get("URL")
        return url
    return None


def extract_journal_info(publication: dict[str, Any]) -> dict[str, Any]:
    """Extract journal information from publication.

    Extracts journal name (container-title), ISSN list, and publisher.

    Args:
        publication: CrossRef publication record.

    Returns:
        Dictionary with journal, issn, publisher fields.

    Example:
        >>> info = extract_journal_info({
        ...     "container-title": ["Nature", "Nature Publishing Group"],
        ...     "ISSN": ["0028-0836", "1476-4687"],
        ...     "publisher": "Springer Nature"
        ... })
        >>> info["journal"]
        'Nature'
        >>> info["issn"]
        ['0028-0836', '1476-4687']
        >>> extract_journal_info({})
        {'journal': None, 'issn': [], 'publisher': None}

    """
    return {
        "journal": extract_first_string(publication.get("container-title")),
        "issn": publication.get("ISSN", []),
        "publisher": publication.get("publisher"),
    }


def extract_page_info(publication: dict[str, Any]) -> dict[str, Any]:
    """Extract pagination information from publication.

    Parses page range string (e.g., "123-145") into first_page and last_page.

    Args:
        publication: CrossRef publication record.

    Returns:
        Dictionary with volume, issue, first_page, last_page fields.

    Example:
        >>> extract_page_info({
        ...     "volume": "42",
        ...     "issue": "3",
        ...     "page": "123-145"
        ... })
        {'volume': '42', 'issue': '3', 'first_page': '123', 'last_page': '145'}
        >>> extract_page_info({"page": "42"})
        {'volume': None, 'issue': None, 'first_page': '42', 'last_page': None}
        >>> extract_page_info({})
        {'volume': None, 'issue': None, 'first_page': None, 'last_page': None}

    """
    first_page, last_page = parse_page_range(publication.get("page"))
    return {
        "volume": publication.get("volume"),
        "issue": publication.get("issue"),
        "first_page": first_page,
        "last_page": last_page,
    }


def extract_dates(publication: dict[str, Any]) -> dict[str, Any]:
    """Extract publication dates from date-parts fields.

    Formats date-parts [[year, month?, day?]] to ISO date strings using
    end-of-period normalization for partial dates:
    - [[year, month, day]] -> "YYYY-MM-DD"
    - [[year, month]] -> "YYYY-MM-DD" (last day of month)
    - [[year]] -> "YYYY-12-31" (last day of year)

    Args:
        publication: CrossRef publication record.

    Returns:
        Dictionary with published_print, published_online fields (ISO format).

    Example:
        >>> extract_dates({
        ...     "published-print": {"date-parts": [[2023, 6, 15]]},
        ...     "published-online": {"date-parts": [[2023, 5]]}
        ... })
        {'published_print': '2023-06-15', 'published_online': '2023-05-31'}
        >>> extract_dates({})
        {'published_print': None, 'published_online': None}

    """
    published_print = publication.get("published-print", {})
    published_online = publication.get("published-online", {})

    return {
        "published_print": format_date_parts(
            published_print.get("date-parts")
            if isinstance(published_print, dict)
            else None
        ),
        "published_online": format_date_parts(
            published_online.get("date-parts")
            if isinstance(published_online, dict)
            else None
        ),
    }


def extract_content_domain(publication: dict[str, Any]) -> dict[str, Any]:
    """Extract content-domain metadata.

    CrossRef content-domain indicates licensing/access restrictions
    and Crossmark participation.

    Args:
        publication: CrossRef publication record.

    Returns:
        Dictionary with content_domain_domains, content_domain_crossmark_restriction.

    Example:
        >>> extract_content_domain({
        ...     "content-domain": {"domain": ["nature.com"], "crossmark-restriction": True}
        ... })
        {'content_domain_domains': ['nature.com'], 'content_domain_crossmark_restriction': True}
        >>> extract_content_domain({})
        {'content_domain_domains': [], 'content_domain_crossmark_restriction': None}

    """
    content_domain = publication.get("content-domain", {})
    if not isinstance(content_domain, dict):
        content_domain = {}

    return {
        "content_domain_domains": content_domain.get("domain", []) or [],
        "content_domain_crossmark_restriction": content_domain.get(
            "crossmark-restriction"
        ),
    }


def extract_issn_by_type(publication: dict[str, Any]) -> dict[str, Any]:
    """Extract ISSN values by type (print/electronic).

    Parses the issn-type array to separate print and electronic ISSNs.
    Takes first occurrence of each type if duplicates exist.

    Args:
        publication: CrossRef publication record.

    Returns:
        Dictionary with issn_print and issn_electronic.

    Example:
        >>> extract_issn_by_type({
        ...     "issn-type": [
        ...         {"value": "0006-291X", "type": "print"},
        ...         {"value": "1090-2104", "type": "electronic"}
        ...     ]
        ... })
        {'issn_print': '0006-291X', 'issn_electronic': '1090-2104'}
        >>> extract_issn_by_type({})
        {'issn_print': None, 'issn_electronic': None}

    """
    issn_type_list = publication.get("issn-type", [])
    if not isinstance(issn_type_list, list):
        return {"issn_print": None, "issn_electronic": None}

    issn_print: str | None = None
    issn_electronic: str | None = None

    for item in issn_type_list:
        if not isinstance(item, dict):
            continue
        issn_value = item.get("value")
        issn_kind = item.get("type")

        if issn_kind == "print" and issn_print is None:
            issn_print = issn_value
        elif issn_kind == "electronic" and issn_electronic is None:
            issn_electronic = issn_value

    return {
        "issn_print": issn_print,
        "issn_electronic": issn_electronic,
    }


def extract_published_date(publication: dict[str, Any]) -> str | None:
    """Extract 'published' date (canonical publication date).

    CrossRef's 'published' field is the preferred publication date,
    distinct from published-print and published-online which indicate
    specific publication events.

    Args:
        publication: CrossRef publication record.

    Returns:
        ISO date string (YYYY-MM-DD) or None.

    Example:
        >>> extract_published_date({"published": {"date-parts": [[2023, 6, 15]]}})
        '2023-06-15'
        >>> extract_published_date({"published": {"date-parts": [[2023]]}})
        '2023-12-31'
        >>> extract_published_date({})
        None

    """
    published = publication.get("published", {})
    if not isinstance(published, dict):
        return None

    return format_date_parts(published.get("date-parts"))

================================================================================
File: transformer.py
Path: pipelines\crossref\transformer.py
================================================================================
"""CrossRef Transformer.

Transforms Bronze records to Silver format (Publication entity inflation).
Contains orchestration logic for CrossRef data transformation per Hexagonal Architecture.

This module was refactored from infrastructure/adapters/crossref/mappers.py
to properly separate business logic from infrastructure concerns.

Terminology:
- Uses "Publication" instead of CrossRef API term "Work" for Ubiquitous Language
- All layers use "publication" to refer to scholarly works (articles, preprints, etc.)

Note: Business logic functions are delegated to domain layer per REFACTOR-004.
Uses DataNormalizationService for text normalization (DI pattern).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.crossref.extractors import (
    extract_authors,
    extract_content_domain,
    extract_dates,
    extract_issn_by_type,
    extract_journal_info,
    extract_license_url,
    extract_page_info,
    extract_published_date,
    extract_year,
)
from bioetl.domain.entities.crossref import (
    CROSSREF_TYPE_DEFAULT,
    CROSSREF_TYPE_MAP,
    CrossRefPublicationEntity,
)
from bioetl.domain.normalization import extract_first_string
from bioetl.domain.services import IdentityService
from bioetl.domain.value_objects import DOI

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord


class CrossRefPublicationTransformer(BasePublicationTransformer):
    """Transforms CrossRef bronze records to silver.

    Implements field extraction, normalization, and type coercion
    according to the CrossRef → Publication entity mapping specification.

    Subclasses BasePublicationTransformer to provide:
    - Unified transformation flow via Template Method
    - Pre-extraction DOI validation (raises ValueError if missing)
    - Content hash computation
    - Tracing and metrics observability (O1)

    Note: Disables fallback logging since CrossRef uses DOI-only lookup.
    """

    def __init__(
        self,
        provider: str = "crossref",
        entity_type: str = "publication",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ) -> None:
        """Initialize CrossRef transformer.

        Args:
            provider: Data provider identifier. Defaults to 'crossref'.
            entity_type: Entity type for metrics labels. Defaults to 'publication'.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names (RULES.md §5.4).
            data_normalizer: Optional data normalization service for text normalization.

        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
        )

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract Publication business data from bronze record.

        Delegates field extraction to extractors module and normalization
        to DataNormalizationService per DI pattern.

        Args:
            record: Raw Bronze record from CrossRef API.

        Returns:
            Dictionary of Publication business fields.

        """
        # Cast to dict for type-safe access (BronzeRecord is an empty TypedDict marker)
        rec = cast("dict[str, Any]", record)

        # Validate DOI using Value Object (returns None for invalid/empty)
        # CrossRef always provides DOI, so we use empty string as fallback for type consistency
        doi_vo = DOI.from_raw(rec.get("DOI"))
        doi = str(doi_vo) if doi_vo else ""

        # Use extractors for structured field extraction
        journal_info = extract_journal_info(rec)
        page_info = extract_page_info(rec)
        dates = extract_dates(rec)
        content_domain = extract_content_domain(rec)
        issn_by_type = extract_issn_by_type(rec)
        published_date = extract_published_date(rec)

        # Extract abstract with HTML stripping via normalizer service
        normalizer = self._data_normalizer
        abstract_raw = rec.get("abstract", "")
        abstract = normalizer.strip_html_tags(abstract_raw) if abstract_raw else None

        # Extract and hash PII fields (RULES.md §5.4)
        # Authors stored as JSON-serialized list for unified format across providers
        raw_authors = extract_authors(rec)
        hashed_authors = self.hash_pii_list(raw_authors) or []

        # Compute unified publication_date (prefer print over online)
        publication_date = self._compute_publication_date(
            dates.get("published_print"),
            dates.get("published_online"),
        )

        return {
            "doi": doi,
            "title": extract_first_string(rec.get("title", [])),
            "abstract": abstract,
            "authors": self.serialize_json_list(hashed_authors),
            **journal_info,
            **page_info,
            **dates,
            "year": extract_year(rec),
            "publication_date": publication_date,
            "doc_type": CROSSREF_TYPE_MAP.get(
                rec.get("type", ""), CROSSREF_TYPE_DEFAULT
            ),
            "citation_count": rec.get("is-referenced-by-count"),
            "reference_count": rec.get("references-count"),
            "language": rec.get("language"),
            "license_url": extract_license_url(rec),
            "subjects": rec.get("subject", []),
            "source": "crossref",
            # Excluded fields (always NULL, not written to Delta Lake):
            # - is_oa: CrossRef doesn't provide Open Access info
            # - pmid/pmc_id: CrossRef doesn't provide PubMed IDs
            "is_oa": None,
            "pmid": None,
            "pmc_id": None,
            # Lookup metadata (from adapter fallback handler)
            "_lookup_method": rec.get("_lookup_method", "doi"),
            "_original_id": rec.get("_original_id"),
            # DQ flags (default: no warnings or errors)
            "_dq_warn": False,
            "_dq_error": False,
            # NEW: Additional CrossRef fields
            "alternative_id": rec.get("alternative-id", []) or [],
            "short_container_title": rec.get("short-container-title", []) or [],
            "published": published_date,
            **content_domain,
            **issn_by_type,
        }

    def _get_primary_id_field(self) -> str:
        """Return the primary ID field name for CrossRef publications.

        Returns:
            'doi' - the CrossRef-specific identifier field.

        """
        return "doi"

    def _get_entity_class(self) -> type[CrossRefPublicationEntity]:
        """Return the domain entity class for CrossRef publications.

        Returns:
            CrossRefPublicationEntity class.

        """
        return CrossRefPublicationEntity

    def _pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None:
        """Validate DOI exists before extraction.

        CrossRef publications require DOI as mandatory identifier.
        Raises ValueError (caught by BaseTransformer.transform).

        Args:
            context: Pipeline context (unused).
            record: Raw Bronze record from CrossRef API.
            index: Sequential index (unused).

        Raises:
            ValueError: If DOI field is missing or empty.

        """
        doi = record.get("DOI")
        if not doi:
            raise ValueError("DOI is required for CrossRef Publication")

    def _compute_publication_date(
        self,
        published_print: str | None,
        published_online: str | None,
    ) -> str | None:
        """Build unified publication_date (YYYY-MM-DD), preferring print.

        Input dates from format_date_parts() are already in YYYY-MM-DD format
        (with end-of-period normalization for partial dates).

        Args:
            published_print: Print publication date (YYYY-MM-DD).
            published_online: Online publication date (YYYY-MM-DD).

        Returns:
            ISO date string (YYYY-MM-DD) or None.
        """
        return published_print or published_online

    def _should_log_fallback_lookup(self) -> bool:
        """Enable fallback lookup logging for CrossRef.

        CrossRef supports title-based fallback when DOI lookup fails (404).
        Adapter uses TitleFallbackHandler for three-phase lookup:
        1. DOI batch fetch
        2. Title fallback for unresolved DOIs
        3. Title-only lookup for entries without DOIs

        Returns:
            True - log fallback lookups for observability.

        """
        return True

================================================================================
File: generic.py
Path: pipelines\generic.py
================================================================================
"""Generic Pipeline Implementation.

Provides a universal pipeline class that can be used for any provider/entity
combination. Replaces provider-specific empty pipeline subclasses.

All pipelines are now configured via YAML and DI, eliminating the need for
separate class files per entity type.

Usage:
    # Via factory (recommended)
    factory = GenericPipelineFactory(
        pipeline_name="chembl_activity",
        pipeline_class=GenericPipeline,  # Use directly
        provider="chembl",
        ...
    )

    # Direct instantiation (for testing)
    pipeline = GenericPipeline.create(
        run_id=run_id,
        runtime=runtime,
        services=services,
        config=config,
        transformer=transformer,
    )
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class GenericPipeline(BasePipeline):
    """Universal pipeline for all provider/entity combinations.

    This class provides a concrete implementation of BasePipeline that works
    with any data source. All entity-specific logic is encapsulated in:

    - **Configuration**: YAML configs in `configs/pipelines/{provider}/{entity}.yaml`
    - **Transformation**: Transformer classes injected via DI
    - **Schemas**: Silver/Gold schemas for validation

    GenericPipeline eliminates the need for empty pipeline subclasses like
    ChEMBLActivityPipeline, PubChemCompoundPipeline, etc.

    Benefits:
    - DRY: No code duplication across pipeline classes
    - Extensibility: Add new pipelines via YAML config only
    - Consistency: All pipelines use identical orchestration logic
    - Testability: Single class to test, well-understood behavior

    Transformer Injection:
        Transformer is injected via DI from GenericPipelineFactory.
        If no transformer is provided, transform_bronze_to_silver() raises
        NotImplementedError (per BasePipeline contract).

    Example YAML Config:
        ```yaml
        pipeline_name: chembl_activity
        provider: chembl
        entity_type: activity
        primary_keys: ["activity_id"]
        silver_table: "chembl_activity"
        ```
    """

    # Inherits all behavior from BasePipeline:
    # - transform_bronze_to_silver() delegates to injected transformer
    # - Properties: config, runtime, services, run_id, context, logger, etc.
    # - Lifecycle: shutdown_signal


__all__ = ["GenericPipeline"]

================================================================================
File: __init__.py
Path: pipelines\openalex\__init__.py
================================================================================
"""OpenAlex pipeline package.

Contains transformer and extractors for OpenAlex Works API data.
"""

from bioetl.application.pipelines.openalex.extractors import (
    extract_authors,
    extract_concepts,
    extract_doi,
    extract_journal_info,
    reconstruct_abstract,
)
from bioetl.application.pipelines.openalex.transformer import (
    OpenAlexPublicationTransformer,
)

__all__ = [
    "OpenAlexPublicationTransformer",
    "extract_authors",
    "extract_concepts",
    "extract_doi",
    "extract_journal_info",
    "reconstruct_abstract",
]

================================================================================
File: extractors.py
Path: pipelines\openalex\extractors.py
================================================================================
"""Field extraction functions for OpenAlex records.

Contains pure functions for extracting and normalizing fields
from OpenAlex Works API responses.

These functions are:
- Stateless and pure (no side effects)
- Unit testable in isolation
- Reusable across different transformation contexts
"""

from __future__ import annotations

from typing import Any


def extract_doi(doi_url: str | None) -> str | None:
    """Extract bare DOI from OpenAlex DOI URL.

    OpenAlex stores DOIs as full URLs (e.g., "https://doi.org/10.1038/s41586-024-07487-w").
    This function extracts just the DOI identifier.

    Args:
        doi_url: DOI URL from OpenAlex (e.g., "https://doi.org/10.1038/...").

    Returns:
        Bare DOI (e.g., "10.1038/s41586-024-07487-w") or None if not available.

    Example:
        >>> extract_doi("https://doi.org/10.1038/s41586-024-07487-w")
        '10.1038/s41586-024-07487-w'
        >>> extract_doi(None)
        None
    """
    if not doi_url:
        return None
    if doi_url.startswith("https://doi.org/"):
        return doi_url[16:]
    if doi_url.startswith("http://doi.org/"):
        return doi_url[15:]
    if doi_url.startswith("doi:"):
        return doi_url[4:]
    return doi_url


def extract_openalex_id(openalex_url: str | None) -> str | None:
    """Extract OpenAlex ID from OpenAlex URL.

    OpenAlex stores IDs as full URLs (e.g., "https://openalex.org/W2148763428").
    This function extracts just the Work ID.

    Args:
        openalex_url: OpenAlex URL (e.g., "https://openalex.org/W2148763428").

    Returns:
        OpenAlex Work ID (e.g., "W2148763428") or None if not available.

    Example:
        >>> extract_openalex_id("https://openalex.org/W2148763428")
        'W2148763428'
        >>> extract_openalex_id(None)
        None
    """
    if not openalex_url:
        return None
    if "/" in openalex_url:
        return openalex_url.split("/")[-1]
    return openalex_url


def extract_authors(authorships: list[dict[str, Any]]) -> list[str]:
    """Extract author display names from authorships.

    OpenAlex stores author information in an "authorships" array with
    nested "author" objects containing display names.

    Args:
        authorships: List of authorship objects from OpenAlex.

    Returns:
        List of author display names.

    Example:
        >>> extract_authors([
        ...     {"author": {"display_name": "John Doe"}},
        ...     {"author": {"display_name": "Jane Smith"}},
        ... ])
        ['John Doe', 'Jane Smith']
    """
    authors = []
    for authorship in authorships:
        author = authorship.get("author", {})
        if not isinstance(author, dict):
            continue
        name = author.get("display_name")
        if name and isinstance(name, str):
            authors.append(name.strip())
    return authors


def extract_concepts(concepts: list[dict[str, Any]], max_count: int = 10) -> list[str]:
    """Extract top concept names from concepts list.

    OpenAlex provides concepts sorted by relevance score.
    This function extracts the display names of the top concepts.

    Args:
        concepts: List of concept objects (sorted by score).
        max_count: Maximum concepts to extract (default 10).

    Returns:
        List of concept display names.

    Example:
        >>> extract_concepts([
        ...     {"display_name": "Chemistry", "score": 0.9},
        ...     {"display_name": "Biology", "score": 0.7},
        ... ])
        ['Chemistry', 'Biology']
    """
    result = []
    for concept in concepts[:max_count]:
        if not isinstance(concept, dict):
            continue
        name = concept.get("display_name")
        if name and isinstance(name, str):
            result.append(name.strip())
    return result


def extract_journal_info(primary_location: dict[str, Any] | None) -> dict[str, Any]:
    """Extract journal information from primary_location.

    OpenAlex stores source information in "primary_location.source".
    This function extracts journal name, ISSN, and publisher.

    Args:
        primary_location: Primary location object from OpenAlex.

    Returns:
        Dictionary with journal_name, issn, publisher.

    Example:
        >>> extract_journal_info({
        ...     "source": {
        ...         "display_name": "Nature",
        ...         "issn_l": "0028-0836",
        ...         "host_organization_name": "Springer Nature"
        ...     }
        ... })
        {'journal_name': 'Nature', 'issn': '0028-0836', 'publisher': 'Springer Nature'}
    """
    if not primary_location or not isinstance(primary_location, dict):
        return {"journal_name": None, "issn": None, "publisher": None}

    source = primary_location.get("source", {}) or {}
    if not isinstance(source, dict):
        return {"journal_name": None, "issn": None, "publisher": None}

    return {
        "journal_name": source.get("display_name"),
        "issn": source.get("issn_l"),
        "publisher": source.get("host_organization_name"),
    }


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Reconstruct abstract from OpenAlex inverted index.

    OpenAlex stores abstracts as inverted index format for storage efficiency:
    {"word": [positions]}.
    This function reconstructs the original text.

    Args:
        inverted_index: Dict mapping words to position lists.

    Returns:
        Reconstructed abstract text or None if not available.

    Example:
        >>> reconstruct_abstract({
        ...     "This": [0],
        ...     "is": [1, 4],
        ...     "an": [2],
        ...     "example": [3],
        ...     "abstract": [5]
        ... })
        'This is an example is abstract'
    """
    if not inverted_index or not isinstance(inverted_index, dict):
        return None

    # Build position -> word mapping
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            if isinstance(pos, int):
                word_positions.append((pos, word))

    if not word_positions:
        return None

    # Sort by position and join
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


def extract_open_access_info(open_access: dict[str, Any] | None) -> dict[str, Any]:
    """Extract Open Access information from open_access object.

    Args:
        open_access: Open access object from OpenAlex.

    Returns:
        Dictionary with is_oa and oa_status.

    Example:
        >>> extract_open_access_info({"is_oa": True, "oa_status": "gold"})
        {'is_oa': True, 'oa_status': 'gold'}
    """
    if not open_access or not isinstance(open_access, dict):
        return {"is_oa": None, "oa_status": None}

    return {
        "is_oa": open_access.get("is_oa"),
        "oa_status": open_access.get("oa_status"),
    }


def extract_external_ids(ids: dict[str, Any] | None) -> dict[str, Any]:
    """Extract external identifiers from ids object.

    OpenAlex stores external IDs as URLs or raw values:
    - pmid: "https://pubmed.ncbi.nlm.nih.gov/12345678" -> "12345678"
    - pmcid: "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123456" -> "PMC123456"
    - mag: Microsoft Academic Graph ID (integer or string)

    Note: Returns intermediate keys matching API names. Transformer maps
    pmcid -> pmc_id for schema consistency.

    Args:
        ids: IDs object from OpenAlex work.

    Returns:
        Dictionary with pmid, pmcid (maps to pmc_id in transformer), mag_id fields.

    Example:
        >>> extract_external_ids({
        ...     "pmid": "https://pubmed.ncbi.nlm.nih.gov/32015508",
        ...     "pmcid": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7095418",
        ...     "mag": "3006090887"
        ... })
        {'pmid': '32015508', 'pmcid': 'PMC7095418', 'mag_id': '3006090887'}
        >>> extract_external_ids(None)
        {'pmid': None, 'pmcid': None, 'mag_id': None}
    """
    if not ids or not isinstance(ids, dict):
        return {"pmid": None, "pmcid": None, "mag_id": None}

    # Extract PMID from URL
    # Format: https://pubmed.ncbi.nlm.nih.gov/12345678
    pmid = None
    pmid_url = ids.get("pmid")
    if pmid_url and isinstance(pmid_url, str):
        pmid = pmid_url.rstrip("/").split("/")[-1] if "/" in pmid_url else pmid_url

    # Extract PMCID from URL
    # Format: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123456
    pmcid = None
    pmcid_url = ids.get("pmcid")
    if pmcid_url and isinstance(pmcid_url, str):
        pmcid = pmcid_url.rstrip("/").split("/")[-1] if "/" in pmcid_url else pmcid_url

    # Extract MAG ID (can be int or string)
    mag_id = None
    mag_raw = ids.get("mag")
    if mag_raw is not None:
        mag_id = str(mag_raw)

    return {"pmid": pmid, "pmcid": pmcid, "mag_id": mag_id}


def extract_mesh_terms(mesh: list[dict[str, Any]] | None) -> list[str]:
    """Extract MeSH descriptor names from mesh array.

    OpenAlex provides MeSH terms with descriptor and qualifier info.
    This function extracts unique descriptor names.

    Args:
        mesh: List of MeSH term objects from OpenAlex.

    Returns:
        List of unique MeSH descriptor names.

    Example:
        >>> extract_mesh_terms([
        ...     {"descriptor_ui": "D000818", "descriptor_name": "Animals"},
        ...     {"descriptor_ui": "D006801", "descriptor_name": "Humans"},
        ...     {"descriptor_ui": "D000818", "descriptor_name": "Animals"}
        ... ])
        ['Animals', 'Humans']
        >>> extract_mesh_terms(None)
        []
    """
    if not mesh or not isinstance(mesh, list):
        return []

    seen: set[str] = set()
    result: list[str] = []

    for term in mesh:
        if not isinstance(term, dict):
            continue
        name = term.get("descriptor_name")
        if name and isinstance(name, str) and name not in seen:
            seen.add(name)
            result.append(name)

    return result


def extract_keywords(keywords: list[dict[str, Any]] | None) -> list[str]:
    """Extract keyword display names from keywords array.

    OpenAlex provides keywords with display_name field.

    Args:
        keywords: List of keyword objects from OpenAlex.

    Returns:
        List of keyword display names.

    Example:
        >>> extract_keywords([
        ...     {"id": "https://openalex.org/keywords/coronavirus", "display_name": "Coronavirus"},
        ...     {"id": "https://openalex.org/keywords/pandemic", "display_name": "Pandemic"}
        ... ])
        ['Coronavirus', 'Pandemic']
        >>> extract_keywords(None)
        []
    """
    if not keywords or not isinstance(keywords, list):
        return []

    result: list[str] = []
    for kw in keywords:
        if not isinstance(kw, dict):
            continue
        name = kw.get("display_name")
        if name and isinstance(name, str):
            result.append(name.strip())

    return result


def extract_biblio_info(biblio: dict[str, Any] | None) -> dict[str, Any]:
    """Extract bibliographic info (volume, issue, pages) from biblio object.

    OpenAlex provides bibliographic information in a "biblio" object
    containing volume, issue, first_page, and last_page fields.

    Args:
        biblio: Biblio object from OpenAlex work.

    Returns:
        Dictionary with volume, issue, first_page, last_page.

    Example:
        >>> extract_biblio_info({
        ...     "volume": "42",
        ...     "issue": "3",
        ...     "first_page": "123",
        ...     "last_page": "145"
        ... })
        {'volume': '42', 'issue': '3', 'first_page': '123', 'last_page': '145'}
        >>> extract_biblio_info(None)
        {'volume': None, 'issue': None, 'first_page': None, 'last_page': None}
    """
    if not biblio or not isinstance(biblio, dict):
        return {
            "volume": None,
            "issue": None,
            "first_page": None,
            "last_page": None,
        }
    return {
        "volume": biblio.get("volume"),
        "issue": biblio.get("issue"),
        "first_page": biblio.get("first_page"),
        "last_page": biblio.get("last_page"),
    }

================================================================================
File: transformer.py
Path: pipelines\openalex\transformer.py
================================================================================
"""OpenAlex Publication Transformer.

Transforms Bronze records to Silver format (OpenAlexPublicationEntity).
Handles both DOI-resolved and title-fallback records.

This module contains orchestration logic for OpenAlex data transformation
per Hexagonal Architecture.

Terminology:
- Uses "Publication" instead of OpenAlex API term "Work" for Ubiquitous Language
- All layers use "publication" to refer to scholarly works

Note: Business logic functions are delegated to extractors module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.openalex.extractors import (
    extract_authors,
    extract_biblio_info,
    extract_concepts,
    extract_external_ids,
    extract_journal_info,
    extract_keywords,
    extract_mesh_terms,
    extract_open_access_info,
    extract_openalex_id,
    reconstruct_abstract,
)
from bioetl.domain.entities.openalex import OPENALEX_TYPE_MAP, OpenAlexPublicationEntity
from bioetl.domain.services import IdentityService
from bioetl.domain.value_objects import DOI, PublicationYear

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord


class OpenAlexPublicationTransformer(BasePublicationTransformer):
    """Transforms OpenAlex Works to Publication entity.

    Mapping:
    - openalex_id: id (URL -> ID extraction)
    - doi: doi (URL -> bare DOI)
    - title: title
    - abstract: abstract_inverted_index (reconstruction)
    - authors: authorships (extraction + PII hashing)
    - journal: primary_location.source.display_name
    - year: publication_year
    - concepts: concepts (top-level only)

    Handles lookup metadata:
    - _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
    - _original_id: Original identifier used for lookup

    Subclasses BasePublicationTransformer to provide:
    - Unified transformation flow via Template Method
    - Automatic primary ID validation and fallback logging
    - Content hash computation (excluding metadata)
    - Tracing and metrics observability (O1)
    """

    def __init__(
        self,
        provider: str = "openalex",
        entity_type: str = "publication",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ) -> None:
        """Initialize OpenAlex transformer.

        Args:
            provider: Data provider identifier. Defaults to 'openalex'.
            entity_type: Entity type for metrics labels. Defaults to 'publication'.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names (RULES.md S5.4).
            data_normalizer: Optional data normalization service for DOI normalization.

        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
        )

    # ========================================================================
    # Field Extraction Methods (Orchestration - delegates to extractors)
    # ========================================================================

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract Publication business data from bronze record.

        Delegates field extraction to extractors module per REFACTOR-004.

        Args:
            record: Raw Bronze record from OpenAlex API.

        Returns:
            Dictionary of Publication business fields.

        """
        # Cast to dict for type-safe access (BronzeRecord is a TypedDict marker)
        rec = cast("dict[str, Any]", record)

        # Extract OpenAlex ID from URL
        openalex_id = extract_openalex_id(rec.get("id"))

        # Validate DOI using Value Object (returns None for invalid/empty)
        # OpenAlex stores DOIs as full URLs (e.g., "https://doi.org/10.1038/...")
        doi_vo = DOI.from_raw(rec.get("doi"))
        doi = str(doi_vo) if doi_vo else None

        # Reconstruct abstract from inverted index (then strip HTML for cleaning)
        abstract_index = rec.get("abstract_inverted_index")
        abstract = self._data_normalizer.strip_html_tags(
            reconstruct_abstract(abstract_index)
        )

        # Extract and hash authors (PII)
        # Authors stored as JSON-serialized list for unified format across providers
        raw_authors = extract_authors(rec.get("authorships", []))
        hashed_authors = self.hash_pii_list(raw_authors) or []

        # Extract journal info
        journal_info = extract_journal_info(rec.get("primary_location", {}))

        # Extract concepts
        concepts = extract_concepts(rec.get("concepts", []))

        # Extract Open Access info
        oa_info = extract_open_access_info(rec.get("open_access", {}))

        # Extract external IDs (pmid, pmc_id, mag)
        external_ids = extract_external_ids(rec.get("ids", {}))

        # Extract MeSH terms
        mesh_terms = extract_mesh_terms(rec.get("mesh", []))

        # Extract keywords
        keywords = extract_keywords(rec.get("keywords", []))

        # Extract bibliographic info (volume, issue, pages)
        biblio_info = extract_biblio_info(rec.get("biblio", {}))

        # Validate year using PublicationYear Value Object
        year_vo = PublicationYear.from_raw(rec.get("publication_year"))
        year = year_vo.value if year_vo else None

        # Map document type
        raw_type = rec.get("type", "")
        doc_type = OPENALEX_TYPE_MAP.get(raw_type, "PUBLICATION")

        # Lookup metadata (from adapter)
        lookup_method = rec.get("_lookup_method", "unknown")
        original_id = rec.get("_original_id")

        return {
            "openalex_id": openalex_id,
            "doi": doi,
            "pmid": external_ids.get("pmid"),
            "pmc_id": external_ids.get("pmcid"),  # API uses "pmcid", we use "pmc_id"
            "mag_id": external_ids.get("mag_id"),
            "title": rec.get("title"),
            "abstract": abstract,
            "authors": self.serialize_json_list(hashed_authors),
            "journal": journal_info.get("journal_name"),
            "issn": journal_info.get("issn"),
            "publisher": journal_info.get("publisher"),
            "year": year,
            "publication_date": self._normalize_partial_date(
                rec.get("publication_date")
            ),
            "doc_type": doc_type,
            "is_oa": oa_info.get("is_oa"),
            "oa_status": oa_info.get("oa_status"),
            # OpenAlex source field: cited_by_count
            # Unified BioETL field: citation_count (standardized across all providers)
            "citation_count": rec.get("cited_by_count"),
            "concepts": concepts,
            "mesh": mesh_terms,
            "keywords": keywords,
            "language": rec.get("language"),
            # Bibliographic info (from biblio object)
            "volume": biblio_info.get("volume"),
            "issue": biblio_info.get("issue"),
            "first_page": biblio_info.get("first_page"),
            "last_page": biblio_info.get("last_page"),
            # Additional metrics
            "fwci": rec.get("fwci"),
            "referenced_works_count": rec.get("referenced_works_count"),
            # Quality indicators
            "is_retracted": rec.get("is_retracted", False),
            "_lookup_method": lookup_method,
            "_original_id": original_id,
            "source": "openalex",
            # DQ flags (default: no warnings or errors)
            "_dq_warn": False,
            "_dq_error": False,
        }

    def _get_primary_id_field(self) -> str:
        """Return the primary ID field name for OpenAlex publications.

        Returns:
            'openalex_id' - the OpenAlex-specific identifier field.

        """
        return "openalex_id"

    def _get_entity_class(self) -> type[OpenAlexPublicationEntity]:
        """Return the domain entity class for OpenAlex publications.

        Returns:
            OpenAlexPublicationEntity class.

        """
        return OpenAlexPublicationEntity

    def _normalize_partial_date(self, date_str: str | None) -> str | None:
        """Normalize partial date to YYYY-MM-DD format (end of period).

        OpenAlex API may return partial dates in various formats:
        - Full date: "2024-05-15" (YYYY-MM-DD)
        - Month precision: "2024-05" (YYYY-MM)
        - Year precision: "2024" (YYYY)

        Partial dates are normalized to end of period for consistency:
        - YYYY-MM → YYYY-MM-30 (approximate month end)
        - YYYY → YYYY-12-31 (year end)

        Args:
            date_str: Raw date string from OpenAlex API.

        Returns:
            Normalized ISO date string (YYYY-MM-DD) or None.

        """
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # Full ISO format (YYYY-MM-DD) - return as-is
        if len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
            return date_str

        # Partial date: YYYY-MM → YYYY-MM-30 (end of month approximation)
        if len(date_str) == 7 and date_str[4] == "-":
            return f"{date_str}-30"

        # Partial date: YYYY → YYYY-12-31 (end of year)
        if len(date_str) == 4 and date_str.isdigit():
            return f"{date_str}-12-31"

        # Unknown format - return None for invalid dates
        return None

================================================================================
File: __init__.py
Path: pipelines\pubchem\__init__.py
================================================================================
"""PubChem pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the PubChem database.

Main Components:
- PubChemCompoundPipeline: Pipeline for compound data
- PubChemCompoundTransformer: Transformer for compound data
"""

from __future__ import annotations

from bioetl.application.pipelines.pubchem.compound import PubChemCompoundPipeline
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer

__all__ = [
    "PubChemCompoundPipeline",
    "PubChemCompoundTransformer",
]

================================================================================
File: compound.py
Path: pipelines\pubchem\compound.py
================================================================================
"""PubChem Compound Pipeline Implementation.

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class PubChemCompoundPipeline(BasePipeline):
    """Pipeline for processing PubChem compounds.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline

================================================================================
File: transformer.py
Path: pipelines\pubchem\transformer.py
================================================================================
"""PubChem Molecule Transformer.

Transforms raw PubChem compound records into Silver-layer format using
the PubchemMolecule domain entity for validation and invariant checking.

.. versionchanged:: 2.0.0
    Uses PubchemMolecule (canonical) instead of Compound (deprecated).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import PubchemMolecule
from bioetl.domain.services import IdentityService
from bioetl.domain.validation import validate_molecular_weight
from bioetl.domain.value_objects import InChIKey

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord, SilverRecord


class PubChemCompoundTransformer(BaseTransformer):
    """Transformer for PubChem compound records.

    Uses PubchemMolecule domain entity (canonical name) for validation
    and lineage tracking. Records without structural identifiers
    (SMILES/InChI) are skipped per entity invariant validation.
    """

    def __init__(
        self,
        provider: str = "pubchem",
        entity_type: str = "compound",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ):
        """Initialize PubChem compound transformer.

        Args:
            provider: Data provider identifier. Defaults to 'pubchem'.
            entity_type: Entity type for metrics labels. Defaults to 'compound'.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher. Not typically used for molecules
                (no PII in chemical data), but included for API consistency.
            data_normalizer: Data normalization service for text normalization.

        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform raw PubChem record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from PubChem.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            TransformationError: If cid is missing.
            ValueError: If PubchemMolecule entity validation fails.

        """
        # Step 1: Validate required field
        cid = self._get_required_field(record, "cid")

        # Step 2: Build business data dictionary
        # Validate and convert molecular_weight (handles string→float, range, precision)
        mol_weight = validate_molecular_weight(record.get("molecular_weight"))

        # Validate InChI Key using Value Object (returns None for invalid/empty)
        raw_inchikey = record.get("inchikey")
        inchikey_vo = InChIKey.from_raw(
            str(raw_inchikey) if raw_inchikey is not None else None
        )
        inchikey = str(inchikey_vo) if inchikey_vo else None

        business_data: dict[str, Any] = {
            "cid": str(cid),
            "molecular_formula": record.get("molecular_formula"),
            "molecular_weight": mol_weight,
            "canonical_smiles": record.get("canonical_smiles"),
            "isomeric_smiles": record.get("isomeric_smiles"),
            "inchi": record.get("inchi"),
            "inchikey": inchikey,
            "iupac_name": record.get("iupac_name"),
        }

        # Step 3: Generate entity_id using IdentityService (RULES.md §2.8)
        entity_id = self.compute_entity_id(
            source_id=str(cid),
            record={"cid": cid},
        )

        # Step 4: Compute content_hash (RULES.md §2.8.1)
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Step 5: Create domain entity with lineage metadata
        # ValueError is raised if invariants fail (e.g., no structural identifiers)
        entity = self._create_entity(
            PubchemMolecule,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # Step 6: Convert to SilverRecord with lineage field renaming
        return cast("SilverRecord", self.entity_to_silver_record(entity))

================================================================================
File: __init__.py
Path: pipelines\pubmed\__init__.py
================================================================================
"""PubMed pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the PubMed database.

Main Components:
- PubMedPublicationPipeline: Pipeline for publication data
- PubMedPublicationTransformer: Transformer for publication data
"""

from __future__ import annotations

from bioetl.application.pipelines.pubmed.publication import PubMedPublicationPipeline
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer

__all__ = [
    "PubMedPublicationPipeline",
    "PubMedPublicationTransformer",
]

================================================================================
File: __init__.py
Path: pipelines\pubmed\extractors\__init__.py
================================================================================
"""PubMed XML extractors.

This package provides specialized extractors for parsing PubMed XML elements.
Each extractor is responsible for a single domain of data extraction.

All extractors inherit from BaseFieldExtractor which implements the Template Method
pattern with extract() -> normalize() -> process() sequence.
"""

from __future__ import annotations

from bioetl.application.pipelines.pubmed.extractors.abstract import AbstractExtractor
from bioetl.application.pipelines.pubmed.extractors.author import AuthorExtractor
from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor
from bioetl.application.pipelines.pubmed.extractors.classification import (
    ClassificationExtractor,
)
from bioetl.application.pipelines.pubmed.extractors.date import DateExtractor
from bioetl.application.pipelines.pubmed.extractors.identifier import (
    IdentifierExtractor,
)

__all__ = [
    "AbstractExtractor",
    "AuthorExtractor",
    "BaseFieldExtractor",
    "ClassificationExtractor",
    "DateExtractor",
    "IdentifierExtractor",
]

================================================================================
File: abstract.py
Path: pipelines\pubmed\extractors\abstract.py
================================================================================
"""Abstract extraction from PubMed XML elements.

Handles structured and unstructured abstract parsing.
"""

from __future__ import annotations

from typing import cast
from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor


class AbstractExtractor(BaseFieldExtractor):
    """Extractor for abstract content from PubMed XML.

    Handles:
    - Simple abstracts with single AbstractText
    - Structured abstracts with labeled sections
    - Inline elements within abstract text
    """

    def extract(self, element: Element | None) -> list[str] | None:
        """Извлечь сырые данные из XML элемента Abstract.

        Args:
            element: The Article element.

        Returns:
            List of text parts with labels, or None if no abstract.
        """
        if element is None:
            return None

        abstract_node = element.find(".//Abstract")
        if abstract_node is None:
            return None

        # Collect all AbstractText sections
        texts = []
        for abstract_text in abstract_node.findall("AbstractText"):
            label = abstract_text.get("Label")

            # Handle inline elements
            full_text = "".join(abstract_text.itertext())

            if label and full_text.strip():
                texts.append(f"{label}: {full_text.strip()}")
            elif full_text.strip():
                texts.append(full_text.strip())

        return texts if texts else None

    def normalize(self, raw_value: list[str]) -> str:
        """Нормализовать извлечённый текст абстракта.

        Args:
            raw_value: List of abstract text parts.

        Returns:
            Combined abstract text.
        """
        return " ".join(raw_value)

    @classmethod
    def extract_abstract(cls, article_node: Element | None) -> str | None:
        """Extract abstract, handling structured abstracts with multiple sections.

        Args:
            article_node: The Article element.

        Returns:
            Combined abstract text or None.
        """
        return cast("str | None", cls().process(article_node))

    @classmethod
    def is_abstract_structured(cls, article_node: Element | None) -> bool:
        """Check if the abstract is structured (has labeled sections).

        Structured abstracts have AbstractText elements with Label attributes
        like "BACKGROUND", "METHODS", "RESULTS", "CONCLUSIONS".

        Args:
            article_node: The Article element.

        Returns:
            True if abstract has labeled sections, False otherwise.
        """
        if article_node is None:
            return False

        abstract_node = article_node.find(".//Abstract")
        if abstract_node is None:
            return False

        # Check if any AbstractText has a Label attribute
        for abstract_text in abstract_node.findall("AbstractText"):
            if abstract_text.get("Label"):
                return True
        return False

================================================================================
File: author.py
Path: pipelines\pubmed\extractors\author.py
================================================================================
"""Author extraction from PubMed XML elements.

Handles parsing of author lists including individual and collective authors.
"""

from __future__ import annotations

from typing import TypedDict
from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor
from bioetl.application.pipelines.pubmed.xml_utils import get_text


class RawAuthor(TypedDict, total=False):
    """Raw author data before normalization."""

    last_name: str | None
    initials: str | None
    fore_name: str | None
    collective_name: str | None


class AuthorExtractor(BaseFieldExtractor):
    """Extractor for author information from PubMed XML.

    Handles:
    - Individual authors with LastName, Initials/ForeName
    - Collective/group authors
    - Empty author lists
    """

    def extract(self, element: Element | None) -> list[RawAuthor] | None:
        """Извлечь сырые данные об авторах из XML.

        Args:
            element: The Article element containing AuthorList.

        Returns:
            List of raw author dicts, or None if no authors.
        """
        if element is None:
            return None

        author_list = element.find(".//AuthorList")
        if author_list is None:
            return None

        raw_authors: list[RawAuthor] = []
        for author in author_list.findall("Author"):
            raw_authors.append(
                RawAuthor(
                    last_name=get_text(author.find("LastName")),
                    initials=get_text(author.find("Initials")),
                    fore_name=get_text(author.find("ForeName")),
                    collective_name=get_text(author.find("CollectiveName")),
                )
            )

        return raw_authors if raw_authors else None

    def normalize(self, raw_value: list[RawAuthor]) -> list[str]:
        """Нормализовать список авторов в формат 'LastName, Initials'.

        Args:
            raw_value: List of raw author dicts.

        Returns:
            List of formatted author names.
        """
        authors = []
        for raw in raw_value:
            last_name = raw.get("last_name")
            initials = raw.get("initials")
            fore_name = raw.get("fore_name")
            collective = raw.get("collective_name")

            if last_name:
                if initials:
                    authors.append(f"{last_name}, {initials}")
                elif fore_name:
                    authors.append(f"{last_name}, {fore_name}")
                else:
                    authors.append(last_name)
            elif collective:
                authors.append(collective)

        return authors

    def process(self, element: Element | None) -> list[str]:
        """Template method: extract → normalize.

        Args:
            element: XML элемент для обработки.

        Returns:
            List of formatted author names (empty list if no authors).
        """
        raw = self.extract(element)
        return self.normalize(raw) if raw is not None else []

    @classmethod
    def parse_authors(cls, article_node: Element) -> list[str]:
        """Extract list of authors in 'LastName, Initials' format.

        Args:
            article_node: The Article element containing AuthorList.

        Returns:
            List of formatted author names.
        """
        return cls().process(article_node)

================================================================================
File: base.py
Path: pipelines\pubmed\extractors\base.py
================================================================================
"""Base class for PubMed XML field extractors.

Implements Template Method pattern for consistent extraction process.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from xml.etree.ElementTree import Element


class BaseFieldExtractor(ABC):
    """Template Method для извлечения полей из PubMed XML.

    Наследники реализуют extract() и normalize() для конкретных полей.
    Метод process() объединяет их в единый процесс обработки.

    Example:
        >>> class MyExtractor(BaseFieldExtractor):
        ...     def extract(self, element):
        ...         return element.find("MyField").text
        ...     def normalize(self, raw_value):
        ...         return raw_value.strip().upper()
        >>> extractor = MyExtractor()
        >>> result = extractor.process(some_element)
    """

    @abstractmethod
    def extract(self, element: Element | None) -> Any:
        """Извлечь сырые данные из XML элемента.

        Args:
            element: XML элемент для извлечения данных.

        Returns:
            Сырые данные (могут быть None, строкой, списком и т.д.).
        """
        ...

    @abstractmethod
    def normalize(self, raw_value: Any) -> Any:
        """Нормализовать извлечённое значение.

        Args:
            raw_value: Сырое значение из extract().

        Returns:
            Нормализованное значение.
        """
        ...

    def process(self, element: Element | None) -> Any:
        """Template method: extract → normalize.

        Выполняет полный цикл извлечения и нормализации данных.

        Args:
            element: XML элемент для обработки.

        Returns:
            Нормализованное значение или None.
        """
        raw = self.extract(element)
        return self.normalize(raw) if raw is not None else None

================================================================================
File: classification.py
Path: pipelines\pubmed\extractors\classification.py
================================================================================
"""Classification extraction from PubMed XML elements.

Handles extraction of keywords, MeSH terms, and publication types.
"""

from __future__ import annotations

from typing import Any, TypedDict
from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor


class RawClassification(TypedDict):
    """Raw classification data before normalization."""

    keywords: list[str | None]
    mesh_terms: list[str | None]
    publication_types: list[str | None]


class NormalizedClassification(TypedDict):
    """Normalized classification data."""

    keywords: list[str]
    mesh_terms: list[str]
    publication_types: list[str]


class ClassificationExtractor(BaseFieldExtractor):
    """Extractor for classification data from PubMed XML.

    Handles:
    - Keywords from KeywordList
    - MeSH terms from MeshHeadingList
    - Publication types from PublicationTypeList
    """

    def extract(self, element: Element | None) -> RawClassification | None:
        """Извлечь сырые данные классификации из XML.

        Args:
            element: Root PubmedArticle element.

        Returns:
            Dict with raw keywords, mesh_terms, and publication_types.
        """
        if element is None:
            return None

        medline = element.find(".//MedlineCitation")
        article = element.find(".//Article")

        return RawClassification(
            keywords=self._extract_keywords_raw(medline),
            mesh_terms=self._extract_mesh_raw(medline),
            publication_types=self._extract_pub_types_raw(article),
        )

    def normalize(self, raw_value: RawClassification) -> NormalizedClassification:
        """Нормализовать данные классификации.

        Args:
            raw_value: Raw classification dict.

        Returns:
            Normalized classification dict with cleaned lists.
        """
        return NormalizedClassification(
            keywords=self._normalize_list(raw_value["keywords"]),
            mesh_terms=self._normalize_list(raw_value["mesh_terms"]),
            publication_types=self._normalize_list(raw_value["publication_types"]),
        )

    def _extract_keywords_raw(self, medline: Element | None) -> list[str | None]:
        """Extract raw keyword texts."""
        if medline is None:
            return []
        keyword_list = medline.find(".//KeywordList")
        if keyword_list is None:
            return []
        return [kw.text for kw in keyword_list.findall("Keyword")]

    def _extract_mesh_raw(self, medline: Element | None) -> list[str | None]:
        """Extract raw MeSH descriptor texts."""
        if medline is None:
            return []
        mesh_list = medline.find(".//MeshHeadingList")
        if mesh_list is None:
            return []
        texts = []
        for heading in mesh_list.findall("MeshHeading"):
            descriptor = heading.find("DescriptorName")
            if descriptor is not None:
                texts.append(descriptor.text)
        return texts

    def _extract_pub_types_raw(self, article: Element | None) -> list[str | None]:
        """Extract raw publication type texts."""
        if article is None:
            return []
        type_list = article.find(".//PublicationTypeList")
        if type_list is None:
            return []
        return [pt.text for pt in type_list.findall("PublicationType")]

    def _normalize_list(self, raw_list: list[str | None]) -> list[str]:
        """Normalize a list by stripping and filtering empty values."""
        return [text.strip() for text in raw_list if text and text.strip()]

    @classmethod
    def parse_keywords(cls, medline_citation: Element | None) -> list[str]:
        """Extract keywords from KeywordList.

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of keyword strings.
        """
        extractor = cls()
        raw = extractor._extract_keywords_raw(medline_citation)
        return extractor._normalize_list(raw)

    @classmethod
    def parse_mesh_terms(cls, medline_citation: Element | None) -> list[str]:
        """Extract MeSH terms from MeshHeadingList.

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of MeSH descriptor names.
        """
        extractor = cls()
        raw = extractor._extract_mesh_raw(medline_citation)
        return extractor._normalize_list(raw)

    @classmethod
    def parse_publication_types(cls, article_node: Element) -> list[str]:
        """Extract publication types from PublicationTypeList.

        Args:
            article_node: The Article element.

        Returns:
            List of publication type strings.
        """
        extractor = cls()
        raw = extractor._extract_pub_types_raw(article_node)
        return extractor._normalize_list(raw)

    @classmethod
    def parse_chemicals(cls, medline_citation: Element | None) -> list[str]:
        """Extract chemical substance names from ChemicalList.

        Extracts NameOfSubstance text from each Chemical element.

        XML structure:
            <ChemicalList>
              <Chemical>
                <RegistryNumber>0</RegistryNumber>
                <NameOfSubstance UI="D000123">Aspirin</NameOfSubstance>
              </Chemical>
            </ChemicalList>

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of chemical substance names.
        """
        if medline_citation is None:
            return []
        chemical_list = medline_citation.find(".//ChemicalList")
        if chemical_list is None:
            return []
        raw: list[str | None] = []
        for chem in chemical_list.findall("Chemical"):
            name_elem = chem.find("NameOfSubstance")
            if name_elem is not None:
                raw.append(name_elem.text)
        return cls()._normalize_list(raw)

    @classmethod
    def parse_gene_symbols(cls, medline_citation: Element | None) -> list[str]:
        """Extract gene symbols from GeneSymbolList.

        XML structure:
            <GeneSymbolList>
              <GeneSymbol>TP53</GeneSymbol>
              <GeneSymbol>BRCA1</GeneSymbol>
            </GeneSymbolList>

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of gene symbols.
        """
        if medline_citation is None:
            return []
        gene_list = medline_citation.find(".//GeneSymbolList")
        if gene_list is None:
            return []
        raw = [gs.text for gs in gene_list.findall("GeneSymbol")]
        return cls()._normalize_list(raw)

    @classmethod
    def parse_databanks(cls, medline_citation: Element | None) -> list[dict[str, Any]]:
        """Extract data bank references from DataBankList.

        Returns structured data with bank name and accession numbers.

        XML structure:
            <DataBankList>
              <DataBank>
                <DataBankName>ClinicalTrials.gov</DataBankName>
                <AccessionNumberList>
                  <AccessionNumber>NCT123456</AccessionNumber>
                </AccessionNumberList>
              </DataBank>
            </DataBankList>

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of dicts with 'databank_name' and 'accession_numbers' keys.
        """
        if medline_citation is None:
            return []
        databank_list = medline_citation.find(".//DataBankList")
        if databank_list is None:
            return []

        result: list[dict[str, Any]] = []
        for databank in databank_list.findall("DataBank"):
            name_elem = databank.find("DataBankName")
            if name_elem is None or not name_elem.text:
                continue

            accession_list = databank.find("AccessionNumberList")
            accessions: list[str] = []
            if accession_list is not None:
                accessions = [
                    acc.text.strip()
                    for acc in accession_list.findall("AccessionNumber")
                    if acc.text and acc.text.strip()
                ]

            result.append(
                {
                    "databank_name": name_elem.text.strip(),
                    "accession_numbers": accessions,
                }
            )

        return result

================================================================================
File: date.py
Path: pipelines\pubmed\extractors\date.py
================================================================================
"""Date extraction from PubMed XML elements.

Handles all date-related parsing including publication dates, history dates,
and article dates with support for partial dates and month name conversion.

MedlineDate Support (added 2026-01-25):
- Parses free-text MedlineDate elements like "2023 Jan-Feb", "2023 Spring"
- Extracts year (always first token)
- Maps seasons and quarters to month ranges (uses end-of-period)
- Handles month ranges by taking the second month (end-of-period strategy)

See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html
"""

from __future__ import annotations

import re
from typing import ClassVar, TypedDict
from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor
from bioetl.application.pipelines.pubmed.xml_utils import get_text


class RawDate(TypedDict):
    """Raw date components before normalization."""

    year: str | None
    month: str | None
    day: str | None


class NormalizedDate(TypedDict):
    """Normalized date result."""

    date_str: str | None
    year_int: int | None


class MedlineDateParser:
    """Parser for PubMed MedlineDate free-text format.

    Handles formats like:
    - "2023 Jan-Feb" → year=2023, month=Feb (end of range)
    - "2023 Spring" → year=2023, month=May (end of season)
    - "2023 1st Quart" → year=2023, month=Mar (end of Q1)
    - "2023 Jan" → year=2023, month=Jan
    - "2023" → year=2023
    - "2022 Dec-2023 Jan" → year=2023, month=Jan (cross-year: take second year)

    Uses end-of-period strategy: for ranges/seasons/quarters,
    returns the END of the period.
    """

    # Month abbreviation to number mapping
    MONTH_MAP: ClassVar[dict[str, str]] = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
    }

    # Season to end-of-period month mapping
    SEASON_MAP: ClassVar[dict[str, str]] = {
        "spring": "05",  # Mar-May → May (end)
        "spr": "05",
        "summer": "08",  # Jun-Aug → Aug (end)
        "sum": "08",
        "fall": "11",  # Sep-Nov → Nov (end)
        "autumn": "11",
        "aut": "11",
        "winter": "02",  # Dec-Feb → Feb (end of winter season)
        "win": "02",
    }

    # Quarter to end-of-period month mapping
    QUARTER_MAP: ClassVar[dict[str, str]] = {
        "1st": "03",  # Q1: Jan-Mar → Mar
        "2nd": "06",  # Q2: Apr-Jun → Jun
        "3rd": "09",  # Q3: Jul-Sep → Sep
        "4th": "12",  # Q4: Oct-Dec → Dec
        "q1": "03",
        "q2": "06",
        "q3": "09",
        "q4": "12",
    }

    # Pattern for month range: "Jan-Feb", "Dec-Jan" (NOT "Dec-2023")
    _MONTH_RANGE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"\b([a-zA-Z]{3,9})-([a-zA-Z]{3,9})\b", re.IGNORECASE
    )

    # Pattern to find 4-digit years in text
    _YEAR_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"\b(19\d{2}|20\d{2})\b")

    def parse(self, medline_date: str) -> RawDate | None:
        """Parse MedlineDate free-text format into components.

        Args:
            medline_date: Free-text date string from MedlineDate element.

        Returns:
            RawDate with extracted year and month, or None if unparseable.
        """
        if not medline_date:
            return None

        text = medline_date.strip()
        tokens = text.split()

        if not tokens:
            return None

        year = self._extract_year(tokens)
        if not year:
            return None

        month = self._extract_month(text, tokens)

        return RawDate(year=year, month=month, day=None)

    def _extract_year(self, tokens: list[str]) -> str | None:
        """Extract year from MedlineDate text.

        Handles cross-year ranges like "2022 Dec-2023 Jan" by preferring
        the second (most recent) year if present.
        """
        text = " ".join(tokens)
        years_found: list[str] = self._YEAR_PATTERN.findall(text)

        if not years_found:
            return None

        # For cross-year ranges, take the last (most recent) year
        return years_found[-1]

    def _extract_month(self, text: str, tokens: list[str]) -> str | None:
        """Extract month/season/quarter from MedlineDate text.

        Uses end-of-period strategy for ranges.
        """
        # Check for month range pattern (e.g., "Jan-Feb")
        range_match = self._MONTH_RANGE_PATTERN.search(text)
        if range_match:
            return range_match.group(2)  # End-of-period: second month

        # Check for quarter (e.g., "1st Quart", "Q1")
        text_lower = text.lower()
        for quarter_key, month_num in self.QUARTER_MAP.items():
            if quarter_key in text_lower:
                return month_num

        # Check for season
        for token in tokens:
            token_lower = token.lower()
            if token_lower in self.SEASON_MAP:
                return self.SEASON_MAP[token_lower]

        # Check for single month name (pure alphabetic tokens only)
        # Process in reverse order to prefer later months (end-of-period)
        for token in reversed(tokens):
            if not token.isalpha():
                continue
            token_lower = token.lower()[:3]
            if token_lower in self.MONTH_MAP:
                return token

        return None


class DateExtractor(BaseFieldExtractor):
    """Extractor for date fields from PubMed XML.

    Handles:
    - Publication dates from JournalIssue/PubDate
    - History dates (received, accepted, revised)
    - Article dates (Electronic publication)
    - Partial dates (year only, year-month)
    - Month name to number conversion
    - MedlineDate free-text format (delegated to MedlineDateParser)
    """

    MONTH_MAP: ClassVar[dict[str, str]] = MedlineDateParser.MONTH_MAP

    def __init__(self) -> None:
        """Initialize with MedlineDate parser."""
        self._medline_parser = MedlineDateParser()

    def extract(self, element: Element | None) -> RawDate | None:
        """Извлечь сырые компоненты даты из XML элемента.

        Supports both structured dates (Year/Month/Day elements) and
        free-text MedlineDate format ("2023 Jan-Feb", "2023 Spring", etc.).

        Args:
            element: XML element containing Year, Month, Day children
                or MedlineDate element.

        Returns:
            Dict with raw year, month, day strings, or None.
        """
        if element is None:
            return None

        year = get_text(element.find("Year"))
        month = get_text(element.find("Month"))
        day = get_text(element.find("Day"))

        # If structured components found, use them
        if any([year, month, day]):
            return RawDate(year=year, month=month, day=day)

        # Fallback: delegate to MedlineDate parser
        medline_date = get_text(element.find("MedlineDate"))
        if medline_date:
            return self._medline_parser.parse(medline_date)

        return None

    def normalize(self, raw_value: RawDate) -> NormalizedDate:
        """Нормализовать компоненты даты в ISO формат.

        Args:
            raw_value: Raw date components dict.

        Returns:
            Dict with formatted date_str and year_int.
        """
        year = raw_value.get("year")
        month = raw_value.get("month")
        day = raw_value.get("day")

        date_str = self._format_date(year, month, day)
        year_int = int(year) if year and year.isdigit() else None

        return NormalizedDate(date_str=date_str, year_int=year_int)

    def _format_date(
        self,
        year: str | None,
        month: str | None,
        day: str | None,
    ) -> str | None:
        """Format date components into ISO date string (YYYY-MM-DD).

        Uses end-of-period strategy for partial dates:
        - Year + Month + Day → YYYY-MM-DD
        - Year + Month (no day) → YYYY-MM-30
        - Year only → YYYY-12-31
        """
        if not year:
            return None

        # Normalize month
        if month:
            month_str = month.strip().lower()[:3]
            month_num = self.MONTH_MAP.get(month_str)
            if not month_num and month.isdigit():
                month_num = month.zfill(2)
            if not month_num:
                # Unknown month format → treat as year-only
                return f"{year}-12-31"
        else:
            # No month → year-only
            return f"{year}-12-31"

        # Normalize day (end of month if missing)
        day_num = day.zfill(2) if day and day.isdigit() else "30"

        return f"{year}-{month_num}-{day_num}"

    @classmethod
    def format_date(
        cls,
        year: str | None,
        month: str | None,
        day: str | None,
    ) -> str | None:
        """Format date components into ISO date string (YYYY-MM-DD or partial).

        Args:
            year: Year as string (required for non-None result).
            month: Month as string (numeric or name).
            day: Day as string.

        Returns:
            ISO formatted date string or None if year is missing.
        """
        return cls()._format_date(year, month, day)

    @classmethod
    def extract_date(
        cls,
        date_node: Element | None,
    ) -> tuple[str | None, int | None]:
        """Extract date string and year from a date element.

        Args:
            date_node: XML element containing Year, Month, Day children.

        Returns:
            Tuple of (formatted_date_string, year_int).
        """
        extractor = cls()
        raw = extractor.extract(date_node)
        if raw is None:
            return None, None
        normalized = extractor.normalize(raw)
        return normalized["date_str"], normalized["year_int"]

    @classmethod
    def extract_history_date(
        cls,
        history_node: Element | None,
        pub_status: str,
    ) -> str | None:
        """Extract a specific date from PubMedPubDate history.

        Args:
            history_node: The History element from PubmedData.
            pub_status: PubStatus value to look for (received, revised, accepted).

        Returns:
            ISO formatted date string or None.
        """
        if history_node is None:
            return None

        for date_node in history_node.findall("PubMedPubDate"):
            if date_node.get("PubStatus") == pub_status:
                date_str, _ = cls.extract_date(date_node)
                return date_str
        return None

    @classmethod
    def extract_article_date(
        cls,
        article_node: Element | None,
        date_type: str,
    ) -> str | None:
        """Extract date from ArticleDate element by DateType attribute.

        Args:
            article_node: The Article element.
            date_type: DateType attribute value (e.g., "Electronic").

        Returns:
            ISO formatted date string or None.
        """
        if article_node is None:
            return None

        for date_node in article_node.findall(".//ArticleDate"):
            if date_node.get("DateType") == date_type:
                date_str, _ = cls.extract_date(date_node)
                return date_str
        return None

================================================================================
File: identifier.py
Path: pipelines\pubmed\extractors\identifier.py
================================================================================
"""Identifier extraction from PubMed XML elements.

Handles extraction of DOI, PMC ID, and other article identifiers.
"""

from __future__ import annotations

from typing import TypedDict
from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor


class RawIdentifiers(TypedDict):
    """Raw identifier data before normalization."""

    doi: str | None
    pmc_id: str | None


class NormalizedIdentifiers(TypedDict):
    """Normalized identifier data."""

    doi: str | None
    pmc_id: str | None


class IdentifierExtractor(BaseFieldExtractor):
    """Extractor for article identifiers from PubMed XML.

    Handles:
    - DOI from ELocationID or ArticleIdList
    - PMC ID from ArticleIdList
    - PMID (via get_text utility)
    """

    def extract(self, element: Element | None) -> RawIdentifiers | None:
        """Извлечь сырые идентификаторы из XML.

        Args:
            element: Root PubmedArticle element.

        Returns:
            Dict with raw doi and pmc_id, or None.
        """
        if element is None:
            return None

        return RawIdentifiers(
            doi=self._extract_doi_raw(element),
            pmc_id=self._extract_pmc_raw(element),
        )

    def normalize(self, raw_value: RawIdentifiers) -> NormalizedIdentifiers:
        """Нормализовать идентификаторы.

        Args:
            raw_value: Raw identifiers dict.

        Returns:
            Normalized identifiers dict.
        """
        return NormalizedIdentifiers(
            doi=self._normalize_text(raw_value.get("doi")),
            pmc_id=self._normalize_text(raw_value.get("pmc_id")),
        )

    def _extract_doi_raw(self, root: Element) -> str | None:
        """Extract raw DOI from ArticleIdList or ELocationID."""
        article = root.find(".//Article")
        if article is None:
            return None

        # Try ELocationID first
        for eloc in article.findall(".//ELocationID"):
            if eloc.get("EIdType") == "doi" and eloc.text:
                return eloc.text

        # Fallback to ArticleIdList
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "doi" and aid.text:
                    return aid.text

        return None

    def _extract_pmc_raw(self, root: Element) -> str | None:
        """Extract raw PMC ID from ArticleIdList."""
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "pmc" and aid.text:
                    return aid.text
        return None

    def _normalize_text(self, text: str | None) -> str | None:
        """Normalize text by stripping whitespace."""
        return text.strip() if text else None

    @classmethod
    def extract_doi(cls, root: Element) -> str | None:
        """Extract DOI from ArticleIdList or ELocationID.

        First tries ELocationID with EIdType="doi", then falls back
        to ArticleIdList with IdType="doi".

        Args:
            root: Root PubmedArticle element.

        Returns:
            DOI string or None.
        """
        extractor = cls()
        raw = extractor._extract_doi_raw(root)
        return extractor._normalize_text(raw)

    @classmethod
    def extract_pmc_id(cls, root: Element) -> str | None:
        """Extract PubMed Central ID from ArticleIdList.

        Args:
            root: Root PubmedArticle element.

        Returns:
            PMC ID string or None.
        """
        extractor = cls()
        raw = extractor._extract_pmc_raw(root)
        return extractor._normalize_text(raw)

================================================================================
File: publication.py
Path: pipelines\pubmed\publication.py
================================================================================
# src/bioetl/application/pipelines/pubmed/publication.py
"""PubMed Publication Pipeline.

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class PubMedPublicationPipeline(BasePipeline):
    """Пайплайн для данных о публикациях из PubMed.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline

================================================================================
File: transformer.py
Path: pipelines\pubmed\transformer.py
================================================================================
"""PubMed Publication Transformer.

See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html

Refactored to use BasePublicationTransformer pattern for consistency
with other publication pipelines (CrossRef, OpenAlex, SemanticScholar).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.pubmed.extractors import (
    AbstractExtractor,
    AuthorExtractor,
    ClassificationExtractor,
    DateExtractor,
    IdentifierExtractor,
)
from bioetl.application.pipelines.pubmed.xml_utils import get_text
from bioetl.domain.entities.pubmed import PubMedPublicationEntity
from bioetl.domain.normalization import normalize_pmc_id, parse_page_range
from bioetl.domain.services import IdentityService
from bioetl.domain.value_objects import DOI, PublicationYear, PubMedId

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord


class PubMedPublicationTransformer(BasePublicationTransformer):
    """Transformer for PubMed publication records.

    Implements BasePublicationTransformer pattern for unified transformation flow:
    1. Pre-extraction validation (XML parsing)
    2. Business data extraction from parsed XML
    3. Entity ID and content hash computation
    4. Domain entity creation

    The parsed XML root is cached during _pre_extract_validation and reused
    in _extract_business_data to avoid parsing twice.
    """

    # Instance variable to cache parsed XML root between validation and extraction
    _cached_xml_root: ET.Element | None

    def __init__(
        self,
        provider: str = "pubmed",
        entity_type: str = "publication",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ):
        """Initialize PubMed publication transformer.

        Args:
            provider: Data provider identifier.
            entity_type: Entity type for metrics labels. Defaults to 'publication'.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names (RULES.md §5.4).
            data_normalizer: Optional data normalization service for DOI normalization.

        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
        )
        self._cached_xml_root = None

    def _pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None:
        """Validate raw XML and parse it before extraction.

        Parses the XML upfront and caches the root element. This allows
        ET.ParseError to be caught and converted to ValueError, which
        BaseTransformer.transform() handles gracefully.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record containing _raw_xml field.
            index: Sequential index of the record (unused).

        Raises:
            ValueError: If _raw_xml is missing, empty, or malformed XML.

        """
        raw_xml = record.get("_raw_xml")
        if not raw_xml or not isinstance(raw_xml, str):
            raise ValueError("Missing or invalid _raw_xml field")

        try:
            self._cached_xml_root = ET.fromstring(raw_xml)
        except ET.ParseError as e:
            # Log the parse error with context
            context.logger.warning(
                "XML_parse_error",
                error=str(e),
                pmid=record.get("pmid"),
            )
            raise ValueError(f"XML parse error: {e}") from e

    def _extract_medline_metadata(
        self,
        medline: ET.Element | None,
        pubmed_data: ET.Element | None,
    ) -> dict[str, Any]:
        """Extract MEDLINE-specific metadata."""
        medline_info = medline.find("MedlineJournalInfo") if medline else None
        citation_subsets = (
            [get_text(cs) for cs in medline.findall("CitationSubset")]
            if medline
            else []
        )

        pub_status = self._extract_publication_status(pubmed_data)

        return {
            "nlm_unique_id": (
                get_text(medline_info.find("NlmUniqueID"))
                if medline_info is not None
                else None
            ),
            "citation_subset": (
                ",".join(cs for cs in citation_subsets if cs)
                if citation_subsets
                else None
            ),
            "publication_status": pub_status,
            "country": (
                get_text(medline.find(".//MedlineJournalInfo/Country"))
                if medline
                else None
            ),
        }

    def _extract_publication_status(self, pubmed_data: ET.Element | None) -> str | None:
        """Extract publication status from PubmedData."""
        if pubmed_data is None:
            return None
        pub_status_elem = pubmed_data.find("PublicationStatus")
        return get_text(pub_status_elem) if pub_status_elem is not None else None

    def _extract_counts(
        self,
        article: ET.Element,
        pubmed_data: ET.Element | None,
    ) -> dict[str, int]:
        """Extract grant and reference counts."""
        grant_list = article.find(".//GrantList")
        grant_count = len(grant_list.findall("Grant")) if grant_list is not None else 0

        ref_list = (
            pubmed_data.find("ReferenceList") if pubmed_data is not None else None
        )
        reference_count = (
            len(ref_list.findall(".//Reference")) if ref_list is not None else 0
        )

        return {"grant_count": grant_count, "reference_count": reference_count}

    def _extract_classification_data(
        self, article: ET.Element, medline: ET.Element | None
    ) -> dict[str, Any]:
        """Extract classification-related fields."""
        publication_types = ClassificationExtractor.parse_publication_types(article)
        keywords = ClassificationExtractor.parse_keywords(medline)
        mesh_terms = ClassificationExtractor.parse_mesh_terms(medline)
        chemicals = ClassificationExtractor.parse_chemicals(medline)

        return {
            "publication_types": publication_types,
            "publication_type_list": self.serialize_json_list(publication_types),
            "keywords": keywords,
            "keyword_count": len(keywords) if keywords else 0,
            "mesh_terms": mesh_terms,
            "mesh_heading_count": len(mesh_terms) if mesh_terms else 0,
            "chemicals": chemicals,
            "chemical_count": len(chemicals) if chemicals else 0,
            "gene_symbols": ClassificationExtractor.parse_gene_symbols(medline),
            "databanks": ClassificationExtractor.parse_databanks(medline),
        }

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract all business fields from PubMed XML.

        Uses the cached XML root from _pre_extract_validation.

        Args:
            record: Raw Bronze record (unused, XML already parsed).

        Returns:
            Dictionary of extracted and normalized fields.

        """
        root = self._cached_xml_root
        if root is None:
            return {"pmid": None}

        raw_pmid = get_text(root.find(".//PMID"))
        pmid_vo = PubMedId.from_raw(raw_pmid)
        pmid = str(pmid_vo) if pmid_vo else None

        medline = root.find(".//MedlineCitation")
        article = root.find(".//Article")
        pubmed_data = root.find(".//PubmedData")

        if article is None:
            return {"pmid": pmid}

        # Extract and hash authors
        raw_authors = AuthorExtractor.parse_authors(article)
        hashed_authors = self.hash_pii_list(raw_authors) or []

        # Validate DOI
        raw_doi = IdentifierExtractor.extract_doi(root)
        doi_vo = DOI.from_raw(raw_doi)
        normalized_doi = str(doi_vo) if doi_vo else None

        return {
            "pmid": pmid,
            "doi": normalized_doi,
            "title": get_text(article.find(".//ArticleTitle")),
            "vernacular_title": get_text(article.find(".//VernacularTitle")),
            "abstract": self._data_normalizer.strip_html_tags(
                AbstractExtractor.extract_abstract(article)
            ),
            "abstract_structured": AbstractExtractor.is_abstract_structured(article),
            "authors": self.serialize_json_list(hashed_authors),
            "author_count": len(hashed_authors),
            **self._extract_journal_data(article),
            **self._extract_date_data(article, pubmed_data),
            **self._extract_classification_data(article, medline),
            **self._extract_medline_metadata(medline, pubmed_data),
            **self._extract_counts(article, pubmed_data),
            "language": get_text(article.find(".//Language")),
            "pmc_id": normalize_pmc_id(IdentifierExtractor.extract_pmc_id(root)),
            "source": "pubmed",
            "doc_type": "PUBLICATION",
            "citation_count": None,
            "is_oa": None,
            "_lookup_method": cast("dict[str, Any]", record).get(
                "_lookup_method", "pmid"
            ),
            "_original_id": cast("dict[str, Any]", record).get("_original_id"),
            "_dq_warn": False,
            "_dq_error": False,
        }

    def _get_primary_id_field(self) -> str:
        """Return the primary ID field name for PubMed publications.

        Returns:
            'pmid' - the PubMed-specific identifier field.

        """
        return "pmid"

    def _get_entity_class(self) -> type[BaseEntity]:
        """Return the domain entity class for PubMed publications.

        Returns:
            PubMedPublicationEntity class.

        """
        return cast("type[BaseEntity]", PubMedPublicationEntity)

    def _should_log_fallback_lookup(self) -> bool:
        """Enable fallback lookup logging for PubMed.

        PubMed supports title-based fallback when PMID lookup fails.
        Adapter uses TitleFallbackHandler for three-phase lookup:
        1. PMID batch fetch
        2. Title fallback for unresolved PMIDs
        3. Title-only lookup for entries without PMIDs

        Returns:
            True - log fallback lookups for observability.

        """
        return True

    def _extract_journal_data(self, article: ET.Element) -> dict[str, Any]:
        """Extract journal-related data from article XML."""
        journal = article.find(".//Journal")
        pages = get_text(article.find(".//Pagination/MedlinePgn"))
        first_page, last_page = parse_page_range(pages)

        if not journal:
            return {
                "journal": None,
                "journal_title": None,
                "journal_abbrev": None,
                "journal_iso_abbrev": None,
                "journal_issn_type": None,
                "issn": None,
                "volume": None,
                "issue": None,
                "pages": pages,
                "medline_pgn": pages,
                "first_page": first_page,
                "last_page": last_page,
            }

        journal_issue = journal.find("JournalIssue")
        journal_name = get_text(journal.find("Title"))
        journal_abbrev = get_text(journal.find("ISOAbbreviation"))
        issn_elem = journal.find("ISSN")
        issn = get_text(issn_elem)
        issn_type = issn_elem.get("IssnType") if issn_elem is not None else None

        return {
            "journal": journal_name,
            "journal_title": journal_name,  # Alias for Gold schema
            "journal_abbrev": journal_abbrev,
            "journal_iso_abbrev": journal_abbrev,  # Alias for Gold schema
            "journal_issn_type": issn_type,
            "issn": issn,
            "volume": get_text(journal_issue.find("Volume")) if journal_issue else None,
            "issue": get_text(journal_issue.find("Issue")) if journal_issue else None,
            "pages": pages,
            "medline_pgn": pages,  # Alias for Gold schema
            "first_page": first_page,
            "last_page": last_page,
        }

    def _compute_publication_date(
        self, epub_date: str | None, pub_date: str | None, year: int | None
    ) -> str | None:
        """Compute unified publication_date (YYYY-MM-DD).

        Priority: epub_date > pub_date > year
        All outputs normalized to full YYYY-MM-DD format using end-of-period strategy.

        Args:
            epub_date: Electronic publication date (YYYY-MM-DD or partial).
            pub_date: Publication date (YYYY-MM-DD or partial).
            year: Publication year.

        Returns:
            ISO date string (YYYY-MM-DD) or None.
        """
        # Priority 1: epub_date if it's a complete date
        if epub_date and len(epub_date) >= 10:
            return epub_date[:10]

        # Priority 2: pub_date (may be partial, normalize it)
        if pub_date:
            return self._normalize_partial_date(pub_date)

        # Priority 3: Construct from year (end of year)
        if year:
            return f"{year}-12-31"

        return None

    def _normalize_partial_date(self, date_str: str | None) -> str | None:
        """Normalize partial date to YYYY-MM-DD (end of period).

        Args:
            date_str: Date string (YYYY, YYYY-MM, or YYYY-MM-DD).

        Returns:
            Full YYYY-MM-DD date or None.
        """
        if not date_str:
            return None
        if len(date_str) >= 10:
            return date_str[:10]
        if len(date_str) == 7:
            # YYYY-MM → YYYY-MM-30
            return f"{date_str}-30"
        if len(date_str) == 4:
            # YYYY → YYYY-12-31
            return f"{date_str}-12-31"
        return None

    def _parse_month_day(
        self, pub_date_node: ET.Element | None
    ) -> tuple[int | None, int | None]:
        """Extract month and day as integers from PubDate node."""
        if pub_date_node is None:
            return None, None

        month_text = get_text(pub_date_node.find("Month"))
        day_text = get_text(pub_date_node.find("Day"))

        pub_month = self._parse_month(month_text)
        pub_day = int(day_text) if day_text and day_text.isdigit() else None

        return pub_month, pub_day

    def _parse_month(self, month_text: str | None) -> int | None:
        """Convert month text (name or number) to integer."""
        if not month_text:
            return None

        month_lower = month_text.strip().lower()[:3]
        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }
        result = month_map.get(month_lower)
        if result is None and month_text.isdigit():
            result = int(month_text)
        return result

    def _extract_date_data(
        self, article: ET.Element, pubmed_data: ET.Element | None
    ) -> dict[str, Any]:
        """Extract date-related data from article XML."""
        journal = article.find(".//Journal")
        journal_issue = journal.find("JournalIssue") if journal else None
        pub_date_node = journal_issue.find("PubDate") if journal_issue else None
        pub_date, raw_year = DateExtractor.extract_date(pub_date_node)
        history = pubmed_data.find("History") if pubmed_data else None

        pub_month, pub_day = self._parse_month_day(pub_date_node)

        year_vo = PublicationYear.from_raw(raw_year)
        validated_year = year_vo.value if year_vo else None

        epub_date = DateExtractor.extract_article_date(article, "Electronic")
        publication_date = self._compute_publication_date(
            epub_date, pub_date, validated_year
        )

        return {
            "pub_date": pub_date,
            "pub_month": pub_month,
            "pub_day": pub_day,
            "publication_date": publication_date,
            "year": validated_year,
            "publication_year": validated_year,
            "accepted_date": DateExtractor.extract_history_date(history, "accepted"),
            "received_date": DateExtractor.extract_history_date(history, "received"),
            "revised_date": DateExtractor.extract_history_date(history, "revised"),
            "epub_date": epub_date,
            "date_completed": None,  # Not easily accessible from Article element
            "date_revised": None,  # Not easily accessible from Article element
        }

================================================================================
File: xml_utils.py
Path: pipelines\pubmed\xml_utils.py
================================================================================
"""Common XML utilities for PubMed extractors.

Provides reusable low-level functions for extracting data from XML elements.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET


def get_text(node: ET.Element | None) -> str | None:
    """Extract text content from an XML element.

    Safely extracts and strips whitespace from XML element text content.
    Handles None elements and empty text gracefully.

    Args:
        node: XML element to extract text from, or None.

    Returns:
        Stripped text content if element exists and has non-empty text,
        None otherwise.

    Example:
        >>> import xml.etree.ElementTree as ET
        >>> elem = ET.fromstring("<title>  PubMed Article  </title>")
        >>> get_text(elem)
        'PubMed Article'
        >>> get_text(None)
        None
        >>> empty = ET.fromstring("<title></title>")
        >>> get_text(empty)
        None

    """
    if node is not None and node.text:
        return node.text.strip()
    return None


def get_int(node: ET.Element | None) -> int | None:
    """Extract integer value from an XML element.

    Safely parses integer from XML element text content.
    Returns None for missing elements, empty text, or non-integer values.

    Args:
        node: XML element containing integer text, or None.

    Returns:
        Parsed integer if element exists and contains valid integer text,
        None otherwise (including for non-numeric text).

    Example:
        >>> import xml.etree.ElementTree as ET
        >>> year = ET.fromstring("<Year>2024</Year>")
        >>> get_int(year)
        2024
        >>> get_int(None)
        None
        >>> invalid = ET.fromstring("<Year>invalid</Year>")
        >>> get_int(invalid)
        None
        >>> empty = ET.fromstring("<Year>  </Year>")
        >>> get_int(empty)
        None

    """
    if node is not None and node.text:
        text = node.text.strip()
        if text:
            try:
                return int(text)
            except ValueError:
                pass
    return None

================================================================================
File: __init__.py
Path: pipelines\semanticscholar\__init__.py
================================================================================
# src/bioetl/application/pipelines/semanticscholar/__init__.py
"""Semantic Scholar pipeline package.

Provides transformer and extractors for Semantic Scholar publication data.
"""

from bioetl.application.pipelines.semanticscholar.extractors import (
    extract_authors,
    extract_external_ids,
    extract_fields_of_study,
    extract_journal_info,
    extract_open_access_info,
    extract_tldr,
)
from bioetl.application.pipelines.semanticscholar.transformer import (
    SemanticScholarPublicationTransformer,
)

__all__ = [
    "SemanticScholarPublicationTransformer",
    "extract_authors",
    "extract_external_ids",
    "extract_fields_of_study",
    "extract_journal_info",
    "extract_open_access_info",
    "extract_tldr",
]

================================================================================
File: extractors.py
Path: pipelines\semanticscholar\extractors.py
================================================================================
# src/bioetl/application/pipelines/semanticscholar/extractors.py
"""Field extraction functions for Semantic Scholar records.

Provides pure functions for extracting and normalizing fields from
Semantic Scholar API responses.
"""

from __future__ import annotations

from typing import Any

from bioetl.domain.config import ValidationConfig
from bioetl.domain.value_objects import PublicationYear

# Semantic Scholar-specific config with min_year=1500 for historical publications
_SS_VALIDATION_CONFIG = ValidationConfig(min_publication_year=1500)


def extract_external_ids(external_ids: dict[str, Any] | None) -> dict[str, Any]:
    """Extract all external identifiers from S2 response.

    Args:
        external_ids: Dict of external IDs from S2 response.

    Returns:
        Dict with normalized keys: doi, pmid, pmcid, arxiv, corpus_id, mag, dblp, acl.

    Example:
        >>> ids = {"DOI": "10.1038/...", "PubMed": "12345678", "CorpusId": 123}
        >>> extract_external_ids(ids)
        {'doi': '10.1038/...', 'pmid': '12345678', 'corpus_id': 123, ...}

    """
    if not external_ids:
        return {}

    return {
        "doi": external_ids.get("DOI"),
        "pmid": external_ids.get("PubMed"),
        "pmcid": external_ids.get("PMCID") or external_ids.get("PubMedCentral"),
        "arxiv": external_ids.get("ArXiv"),
        "corpus_id": external_ids.get("CorpusId"),
        "mag": external_ids.get("MAG"),
        "dblp": external_ids.get("DBLP"),
        "acl": external_ids.get("ACL"),
    }


def extract_authors(authors: list[dict[str, Any]] | None) -> list[str]:
    """Extract author display names from authors list.

    Filters out None, empty strings, and whitespace-only names.

    Args:
        authors: List of author objects from S2.

    Returns:
        List of author names (non-empty, stripped).

    Example:
        >>> authors = [{"authorId": "123", "name": "John Doe"}]
        >>> extract_authors(authors)
        ['John Doe']
        >>> authors = [{"name": "  "}, {"name": ""}, {"name": None}]
        >>> extract_authors(authors)
        []

    """
    if not authors:
        return []

    result = []
    for author in authors:
        name = author.get("name")
        if name and name.strip():
            result.append(name.strip())
    return result


def extract_journal_info(
    journal: dict[str, Any] | None,
    venue: str | None,
) -> dict[str, Any]:
    """Extract journal information.

    Args:
        journal: Journal object from S2 response.
        venue: Venue string (fallback if journal is empty).

    Returns:
        Dict with journal_name, volume, pages.

    Example:
        >>> journal = {"name": "Nature", "volume": "629", "pages": "123-130"}
        >>> extract_journal_info(journal, "Nature")
        {'journal_name': 'Nature', 'volume': '629', 'pages': '123-130'}

    """
    if journal:
        return {
            "journal_name": journal.get("name") or venue,
            "volume": journal.get("volume"),
            "pages": journal.get("pages"),
        }
    return {
        "journal_name": venue,
        "volume": None,
        "pages": None,
    }


# Valid OA status values (normalized to lowercase for consistency with OpenAlex)
VALID_OA_STATUS_VALUES = {"gold", "green", "hybrid", "bronze", "closed"}


def normalize_oa_status(status: str | None) -> str | None:
    """Normalize OA status to lowercase.

    Converts OA status values to lowercase for consistency with OpenAlex.
    Returns None for invalid or unknown status values.

    Args:
        status: Raw OA status string (may be uppercase, mixed case, or None).

    Returns:
        Normalized lowercase status if valid, None otherwise.

    Example:
        >>> normalize_oa_status("GOLD")
        'gold'
        >>> normalize_oa_status("Green")
        'green'
        >>> normalize_oa_status("unknown")
        None
        >>> normalize_oa_status(None)
        None

    """
    if status is None:
        return None
    normalized = status.lower().strip()
    return normalized if normalized in VALID_OA_STATUS_VALUES else None


def extract_open_access_info(
    is_open_access: bool | None,
    open_access_pdf: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract open access information with normalized status.

    Extracts OA information from S2 API response and normalizes the status
    to lowercase for consistency with OpenAlex data.

    Args:
        is_open_access: Boolean flag from S2.
        open_access_pdf: PDF info object from S2.

    Returns:
        Dict with is_oa (bool), url (str|None), oa_status (str|None).
        If is_open_access is False or None and no OA PDF, oa_status is "closed".

    Example:
        >>> oa_pdf = {"url": "https://example.com/paper.pdf", "status": "GREEN"}
        >>> extract_open_access_info(True, oa_pdf)
        {'is_oa': True, 'url': 'https://...', 'oa_status': 'green'}
        >>> extract_open_access_info(False, None)
        {'is_oa': False, 'url': None, 'oa_status': 'closed'}

    """
    # Determine if open access
    is_oa = is_open_access or False

    # Extract URL and status from PDF info
    url: str | None = None
    raw_status: str | None = None

    if open_access_pdf:
        url = open_access_pdf.get("url")
        raw_status = open_access_pdf.get("status")

    # Normalize status to lowercase
    oa_status = normalize_oa_status(raw_status)

    # If not open access and no status, set to "closed"
    if not is_oa and oa_status is None:
        oa_status = "closed"

    return {
        "is_oa": is_oa,
        "url": url,
        "oa_status": oa_status,
    }


def extract_tldr(tldr: dict[str, Any] | None) -> str | None:
    """Extract AI-generated summary from tldr field.

    Args:
        tldr: TLDR object from S2 response.

    Returns:
        Summary text or None.

    Example:
        >>> tldr = {"model": "tldr@v2.0.0", "text": "This paper presents..."}
        >>> extract_tldr(tldr)
        'This paper presents...'

    """
    if not tldr:
        return None
    return tldr.get("text")


def extract_fields_of_study(
    fields_of_study: list[str] | None,
    max_count: int = 10,
) -> list[str]:
    """Extract fields of study.

    Filters out None and empty string elements from the list.

    Args:
        fields_of_study: List of field names from S2.
        max_count: Maximum fields to extract.

    Returns:
        List of non-empty field names (capped at max_count).

    Example:
        >>> fields = ["Biology", "Medicine", "Genetics"]
        >>> extract_fields_of_study(fields, max_count=2)
        ['Biology', 'Medicine']
        >>> fields = ["Biology", None, "", "Medicine"]
        >>> extract_fields_of_study(fields)
        ['Biology', 'Medicine']

    """
    if not fields_of_study:
        return []
    # Filter out None and empty strings, then cap at max_count
    return [f for f in fields_of_study if f and isinstance(f, str)][:max_count]


def validate_year(year: int | None) -> int | None:
    """Validate publication year using PublicationYear Value Object.

    Uses Semantic Scholar-specific ValidationConfig with min_year=1500
    to support historical publications.

    Args:
        year: Year from S2 response.

    Returns:
        Year if valid (1500-2100), None otherwise.

    """
    if year is None:
        return None
    year_vo = PublicationYear.from_raw(year, config=_SS_VALIDATION_CONFIG)
    return year_vo.value if year_vo else None

================================================================================
File: transformer.py
Path: pipelines\semanticscholar\transformer.py
================================================================================
# src/bioetl/application/pipelines/semanticscholar/transformer.py
"""Semantic Scholar Publication Transformer.

Transforms Bronze records to Silver format (Publication entity).
Handles both DOI-resolved and title-fallback records.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.semanticscholar.extractors import (
    extract_authors,
    extract_external_ids,
    extract_fields_of_study,
    extract_journal_info,
    extract_open_access_info,
    extract_tldr,
    validate_year,
)
from bioetl.domain.entities.semanticscholar import SemanticScholarPublicationEntity
from bioetl.domain.normalization import normalize_pmc_id, parse_page_range
from bioetl.domain.value_objects import DOI, PubMedId

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.services import IdentityService
    from bioetl.domain.types import BronzeRecord


class SemanticScholarPublicationTransformer(BasePublicationTransformer):
    """Transforms Semantic Scholar papers to Publication entity.

    Mapping:
    - paper_id: paperId (40-char hex S2 ID)
    - doi: externalIds.DOI
    - pmid: externalIds.PubMed
    - arxiv_id: externalIds.ArXiv
    - dblp_id: externalIds.DBLP
    - title: title
    - abstract: abstract
    - tldr: tldr.text (AI-generated summary)
    - authors: authors (extraction + optional PII hashing)
    - journal: journal.name / venue
    - year: year
    - publication_date: publicationDate
    - citation_count: citationCount
    - reference_count: referenceCount
    - influential_citation_count: influentialCitationCount
    - is_oa: isOpenAccess (normalized)
    - oa_status: openAccessPdf.status (normalized to lowercase)
    - open_access_url: openAccessPdf.url
    - fields_of_study: fieldsOfStudy
    - publication_types: publicationTypes

    Handles lookup metadata:
    - _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
    - _original_id: Original identifier used for lookup

    Subclasses BasePublicationTransformer to provide:
    - Unified transformation flow via Template Method
    - Automatic primary ID validation and fallback logging
    - Content hash computation (excluding metadata)
    - Tracing and metrics observability (O1)
    """

    def __init__(
        self,
        provider: str = "semanticscholar",
        entity_type: str = "publication",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ) -> None:
        """Initialize transformer.

        Args:
            provider: Data provider identifier.
            entity_type: Entity type for metrics.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names.
            data_normalizer: Optional data normalization service for DOI normalization.

        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
        )

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract and normalize fields from Semantic Scholar record.

        Args:
            record: Raw Bronze record from Semantic Scholar API.

        Returns:
            Dictionary of extracted and normalized fields.

        """
        rec = cast("dict[str, Any]", record)

        # Primary key - S2 Paper ID
        paper_id = rec.get("paperId")

        # External identifiers
        external_ids = extract_external_ids(rec.get("externalIds"))

        # Validate DOI using Value Object (returns None for invalid/empty)
        raw_doi = external_ids.get("doi")
        doi_vo = DOI.from_raw(raw_doi)
        doi = str(doi_vo) if doi_vo else None

        # Validate PMID using Value Object (returns None for invalid/empty)
        raw_pmid = external_ids.get("pmid")
        pmid_vo = PubMedId.from_raw(raw_pmid)
        pmid = str(pmid_vo) if pmid_vo else None

        # Authors with optional PII hashing
        raw_authors = extract_authors(rec.get("authors"))
        hashed_authors = self.hash_pii_list(raw_authors) or []

        # Journal/venue info
        journal_info = extract_journal_info(
            rec.get("journal"),
            rec.get("venue"),
        )

        # Parse pages into unified first_page/last_page
        pages = journal_info.get("pages")
        first_page, last_page = parse_page_range(pages)

        # Open access info
        oa_info = extract_open_access_info(
            rec.get("isOpenAccess"),
            rec.get("openAccessPdf"),
        )

        # TLDR summary
        tldr = extract_tldr(rec.get("tldr"))

        # Fields of study
        fields_of_study = extract_fields_of_study(rec.get("fieldsOfStudy"))

        # Validate year
        year = validate_year(rec.get("year"))

        # Lookup metadata (from adapter)
        lookup_method = rec.get("_lookup_method", "unknown")
        original_id = rec.get("_original_id")

        return {
            "paper_id": paper_id,
            "doi": doi,
            "pmid": pmid,  # Use validated PMID from PubMedId Value Object
            "pmc_id": normalize_pmc_id(
                external_ids.get("pmcid")
            ),  # API uses "pmcid", we use "pmc_id"
            "arxiv_id": external_ids.get("arxiv"),
            "dblp_id": external_ids.get("dblp"),
            "corpus_id": external_ids.get("corpus_id"),
            "title": rec.get("title"),
            "abstract": self._data_normalizer.strip_html_tags(rec.get("abstract")),
            "tldr": tldr,
            "authors": self.serialize_json_list(hashed_authors),
            "journal": journal_info.get("journal_name"),
            "volume": journal_info.get("volume"),
            "pages": pages,  # Legacy field
            "first_page": first_page,  # Unified field
            "last_page": last_page,  # Unified field
            "venue": rec.get("venue"),
            "year": year,
            "publication_date": self._normalize_partial_date(
                rec.get("publicationDate")
            ),
            "citation_count": rec.get("citationCount"),
            "reference_count": rec.get("referenceCount"),
            "influential_citation_count": rec.get("influentialCitationCount"),
            "is_oa": oa_info.get("is_oa"),
            "open_access_url": oa_info.get("url"),
            "oa_status": oa_info.get("oa_status"),
            "fields_of_study": self.serialize_json(fields_of_study),
            "publication_types": self.serialize_json(rec.get("publicationTypes")),
            "source": "semanticscholar",
            # Lookup metadata
            "_lookup_method": lookup_method,
            "_original_id": original_id,
            # DQ flags (default: no warnings or errors)
            "_dq_warn": False,
            "_dq_error": False,
        }

    def _get_primary_id_field(self) -> str:
        """Return the primary ID field name for Semantic Scholar publications.

        Returns:
            'paper_id' - the Semantic Scholar-specific identifier field.

        """
        return "paper_id"

    def _get_entity_class(self) -> type[SemanticScholarPublicationEntity]:
        """Return the domain entity class for Semantic Scholar publications.

        Returns:
            SemanticScholarPublicationEntity class.

        """
        return SemanticScholarPublicationEntity

    def _normalize_partial_date(self, date_str: str | None) -> str | None:
        """Normalize partial date to YYYY-MM-DD format.

        Semantic Scholar API may return partial dates (YYYY or YYYY-MM).
        This method normalizes them to full ISO dates using end-of-period:
        - YYYY -> YYYY-12-31 (end of year)
        - YYYY-MM -> YYYY-MM-30 (end of month, simplified)
        - YYYY-MM-DD -> unchanged

        Args:
            date_str: Raw date string from API.

        Returns:
            Normalized YYYY-MM-DD date string or None if invalid/empty.

        """
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # Full ISO date (YYYY-MM-DD)
        if len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
            return date_str

        # Year-month only (YYYY-MM) -> use day 30 as end-of-month
        if len(date_str) == 7 and date_str[4] == "-":
            return f"{date_str}-30"

        # Year only (YYYY) -> use December 31 as end-of-year
        if len(date_str) == 4 and date_str.isdigit():
            return f"{date_str}-12-31"

        # Invalid format - return None
        return None

================================================================================
File: __init__.py
Path: pipelines\uniprot\__init__.py
================================================================================
"""UniProt pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the UniProt database.

Main Components:
- UniProtProteinPipeline: Pipeline for protein data
- UniProtProteinTransformer: Transformer for protein data
- IDMappingTransformer: Transformer for ChEMBL → UniProt ID mapping
"""

from __future__ import annotations

from bioetl.application.pipelines.uniprot.idmapping_transformer import (
    IDMappingTransformer,
)
from bioetl.application.pipelines.uniprot.protein import UniProtProteinPipeline
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer

__all__ = [
    "IDMappingTransformer",
    "UniProtProteinPipeline",
    "UniProtProteinTransformer",
]

================================================================================
File: __init__.py
Path: pipelines\uniprot\extractors\__init__.py
================================================================================
"""UniProt data extractors package.

Provides specialized extractors for different aspects of UniProt data.
"""

from bioetl.application.pipelines.uniprot.extractors.comments import CommentExtractor
from bioetl.application.pipelines.uniprot.extractors.crossrefs import CrossRefExtractor
from bioetl.application.pipelines.uniprot.extractors.features import FeatureExtractor
from bioetl.application.pipelines.uniprot.extractors.genes import GeneExtractor
from bioetl.application.pipelines.uniprot.extractors.utils import ExtractorUtils

__all__ = [
    "CommentExtractor",
    "CrossRefExtractor",
    "ExtractorUtils",
    "FeatureExtractor",
    "GeneExtractor",
]

================================================================================
File: comments.py
Path: pipelines\uniprot\extractors\comments.py
================================================================================
"""Comment data extraction for UniProt records."""

from __future__ import annotations

from typing import Any

from bioetl.domain.serialization import serialize_to_json


def _is_comment_of_type(comment: Any, comment_type: str) -> bool:
    """Check if comment matches the specified type.

    Args:
        comment: Comment object to check.
        comment_type: Expected comment type.

    Returns:
        True if comment is a dict with matching commentType.
    """
    return isinstance(comment, dict) and comment.get("commentType") == comment_type


def _extract_reaction_data(reaction: dict[str, Any]) -> dict[str, Any]:
    """Extract reaction data from catalytic activity.

    Args:
        reaction: Reaction dict from comment.

    Returns:
        Activity dict with reaction and ec_number fields.
    """
    activity: dict[str, Any] = {}
    if reaction.get("name"):
        activity["reaction"] = reaction.get("name")
    if reaction.get("ecNumber"):
        activity["ec_number"] = reaction.get("ecNumber")
    return activity


def _extract_location_value(loc: dict[str, Any]) -> str | None:
    """Extract location value from subcellular location entry.

    Args:
        loc: Location entry dict.

    Returns:
        Location value string or None.
    """
    location = loc.get("location", {})
    if isinstance(location, dict):
        value = location.get("value")
        if value:
            return str(value)
    return None


def _build_isoform_data(iso: dict[str, Any]) -> dict[str, Any]:
    """Build isoform data from isoform entry.

    Args:
        iso: Isoform entry dict.

    Returns:
        Isoform data dict with ids and name.
    """
    isoform_data: dict[str, Any] = {}
    isoform_ids = iso.get("isoformIds", [])
    if isoform_ids:
        isoform_data["ids"] = isoform_ids
    name = iso.get("name", {})
    if isinstance(name, dict) and name.get("value"):
        isoform_data["name"] = name.get("value")
    return isoform_data


class CommentExtractor:
    """Extracts comment-related data from UniProt records.

    UniProt comments contain functional annotations like FUNCTION,
    SUBUNIT, CATALYTIC ACTIVITY, SUBCELLULAR LOCATION, etc.
    """

    @staticmethod
    def extract_text_values(comments: list[Any], comment_type: str) -> list[str]:
        """Extract text values from comments of specific type.

        Args:
            comments: List of comment objects.
            comment_type: Comment type to filter by.

        Returns:
            List of extracted text values.
        """
        extracted: list[str] = []
        for comment in comments:
            if not _is_comment_of_type(comment, comment_type):
                continue

            texts = comment.get("texts", [])
            if isinstance(texts, list):
                for text in texts:
                    if isinstance(text, dict):
                        value = text.get("value")
                        if value:
                            extracted.append(str(value))
        return extracted

    @classmethod
    def extract_by_type(cls, comments: Any, comment_type: str) -> str | None:
        """Extract comments of specific type as JSON string.

        Args:
            comments: List of comment objects.
            comment_type: Comment type (FUNCTION, SUBUNIT, etc.)

        Returns:
            JSON string of comment values or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted = cls.extract_text_values(comments, comment_type)
        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @staticmethod
    def extract_catalytic_activity(comments: Any) -> str | None:
        """Extract catalytic activity information.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of catalytic activities or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[dict[str, Any]] = []
        for comment in comments:
            if not _is_comment_of_type(comment, "CATALYTIC ACTIVITY"):
                continue

            reaction = comment.get("reaction", {})
            if isinstance(reaction, dict):
                activity = _extract_reaction_data(reaction)
                if activity:
                    extracted.append(activity)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @staticmethod
    def extract_subcellular_locations(comments: Any) -> str | None:
        """Extract subcellular location information.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of subcellular locations or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[str] = []
        for comment in comments:
            if not _is_comment_of_type(comment, "SUBCELLULAR LOCATION"):
                continue

            locations = comment.get("subcellularLocations", [])
            if isinstance(locations, list):
                for loc in locations:
                    if isinstance(loc, dict):
                        value = _extract_location_value(loc)
                        if value:
                            extracted.append(value)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @staticmethod
    def extract_alternative_products(comments: Any) -> str | None:
        """Extract alternative products (isoforms) information.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of isoform information or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[dict[str, Any]] = []
        for comment in comments:
            if not _is_comment_of_type(comment, "ALTERNATIVE PRODUCTS"):
                continue

            isoforms = comment.get("isoforms", [])
            if isinstance(isoforms, list):
                for iso in isoforms:
                    if isinstance(iso, dict):
                        isoform_data = _build_isoform_data(iso)
                        if isoform_data:
                            extracted.append(isoform_data)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @staticmethod
    def count_isoforms(comments: Any) -> int | None:
        """Count the number of isoforms.

        Args:
            comments: List of comment objects.

        Returns:
            Number of isoforms or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        count = 0
        for comment in comments:
            if not _is_comment_of_type(comment, "ALTERNATIVE PRODUCTS"):
                continue

            isoforms = comment.get("isoforms", [])
            if isinstance(isoforms, list):
                count += len(isoforms)

        return count if count > 0 else None

================================================================================
File: crossrefs.py
Path: pipelines\uniprot\extractors\crossrefs.py
================================================================================
"""Cross-reference data extraction for UniProt records."""

from __future__ import annotations

from typing import Any

from bioetl.domain.serialization import serialize_to_json


class CrossRefExtractor:
    """Extracts cross-reference data from UniProt records.

    Handles GO terms, DrugBank, ChEMBL, and other database references.
    """

    # Valid GO term aspects
    GO_ASPECTS = frozenset(("F", "P", "C"))

    @classmethod
    def extract_go_terms(cls, xrefs: Any) -> str | None:
        """Extract GO terms with structured data.

        Args:
            xrefs: List of cross-reference objects.

        Returns:
            JSON array of GO terms.
        """
        if not xrefs or not isinstance(xrefs, list):
            return None

        go_terms: list[dict[str, Any]] = []
        for xref in xrefs:
            if not isinstance(xref, dict):
                continue
            if xref.get("database") != "GO":
                continue

            go_id = xref.get("id")
            if not go_id:
                continue

            props = cls._parse_properties(xref.get("properties", []))
            aspect, term = cls._parse_go_term_value(props.get("GoTerm", ""))

            go_terms.append(
                {
                    "id": go_id,
                    "term": term,
                    "aspect": aspect,
                    "evidence": props.get("GoEvidenceType"),
                }
            )

        return serialize_to_json(go_terms, ensure_ascii=False) if go_terms else None

    @staticmethod
    def _parse_properties(properties: list[Any]) -> dict[str, str]:
        """Parse cross-reference properties into key-value dict.

        Args:
            properties: List of property objects.

        Returns:
            Dict mapping property keys to values.
        """
        props: dict[str, str] = {}
        if not isinstance(properties, list):
            return props
        for prop in properties:
            if isinstance(prop, dict):
                key = prop.get("key")
                value = prop.get("value")
                if key and value:
                    props[key] = value
        return props

    @classmethod
    def _parse_go_term_value(cls, go_term_value: str) -> tuple[str | None, str | None]:
        """Parse GO term value "F:ATP binding" into aspect and term.

        Args:
            go_term_value: Raw GO term string like "F:ATP binding".

        Returns:
            Tuple of (aspect, term) where aspect is F/P/C or None.
        """
        if not go_term_value or ":" not in go_term_value:
            return None, None

        parts = go_term_value.split(":", 1)
        if len(parts) != 2:
            return None, None

        aspect_candidate = parts[0].strip()
        aspect = aspect_candidate if aspect_candidate in cls.GO_ASPECTS else None
        term = parts[1].strip() if parts[1].strip() else None
        return aspect, term

    @staticmethod
    def extract_xref_ids(xrefs: Any, database: str) -> str | None:
        """Extract cross-reference IDs for specific database.

        Args:
            xrefs: List of cross-reference objects.
            database: Database name (DrugBank, ChEMBL, GuidetoPHARMACOLOGY).

        Returns:
            JSON array of IDs or None.
        """
        if not xrefs or not isinstance(xrefs, list):
            return None

        ids: list[str] = []
        for xref in xrefs:
            if not isinstance(xref, dict):
                continue
            if xref.get("database") != database:
                continue

            xref_id = xref.get("id")
            if xref_id:
                ids.append(str(xref_id))

        return serialize_to_json(ids, ensure_ascii=False) if ids else None

================================================================================
File: features.py
Path: pipelines\uniprot\extractors\features.py
================================================================================
"""Feature and keyword extraction for UniProt records."""

from __future__ import annotations

from typing import Any

from bioetl.domain.serialization import serialize_to_json


def _extract_feature_location(
    location: dict[str, Any], feature_data: dict[str, Any]
) -> None:
    """Extract start/end positions from feature location.

    Args:
        location: Location dict from feature.
        feature_data: Feature dict to add positions to.
    """
    start = location.get("start", {})
    end = location.get("end", {})
    if isinstance(start, dict) and start.get("value"):
        feature_data["start"] = start.get("value")
    if isinstance(end, dict) and end.get("value"):
        feature_data["end"] = end.get("value")


def _build_feature_dict(feature: dict[str, Any]) -> dict[str, Any]:
    """Build a feature data dictionary.

    Args:
        feature: Raw feature dict from API.

    Returns:
        Extracted feature data dict.
    """
    feature_data: dict[str, Any] = {}
    if feature.get("type"):
        feature_data["type"] = feature.get("type")
    if feature.get("description"):
        feature_data["description"] = feature.get("description")
    if feature.get("featureId"):
        feature_data["feature_id"] = feature.get("featureId")

    location = feature.get("location", {})
    if isinstance(location, dict):
        _extract_feature_location(location, feature_data)

    return feature_data


def _build_keyword_dict(kw: dict[str, Any]) -> dict[str, Any]:
    """Build a keyword data dictionary.

    Args:
        kw: Raw keyword dict from API.

    Returns:
        Extracted keyword data dict.
    """
    kw_data: dict[str, Any] = {}
    if kw.get("id"):
        kw_data["id"] = kw.get("id")
    if kw.get("name"):
        kw_data["name"] = kw.get("name")
    if kw.get("category"):
        kw_data["category"] = kw.get("category")
    return kw_data


class FeatureExtractor:
    """Extracts sequence features and keywords from UniProt records."""

    @staticmethod
    def extract_features(features: Any) -> str | None:
        """Extract sequence features.

        Args:
            features: List of feature objects.

        Returns:
            JSON array of features or None.
        """
        if not features or not isinstance(features, list):
            return None

        extracted: list[dict[str, Any]] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            feature_data = _build_feature_dict(feature)
            if feature_data:
                extracted.append(feature_data)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @staticmethod
    def extract_keywords(keywords: Any) -> str | None:
        """Extract UniProt keywords.

        Args:
            keywords: List of keyword objects.

        Returns:
            JSON array of keywords.
        """
        if not keywords or not isinstance(keywords, list):
            return None

        extracted: list[dict[str, Any]] = []
        for kw in keywords:
            if not isinstance(kw, dict):
                continue
            kw_data = _build_keyword_dict(kw)
            if kw_data:
                extracted.append(kw_data)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

================================================================================
File: genes.py
Path: pipelines\uniprot\extractors\genes.py
================================================================================
"""Gene data extraction for UniProt records."""

from __future__ import annotations

from typing import Any

from bioetl.domain.serialization import serialize_to_json


class GeneExtractor:
    """Extracts gene-related data from UniProt records."""

    @staticmethod
    def extract_gene_names(genes: Any) -> list[str]:
        """Extract gene names from genes list.

        Args:
            genes: List of gene objects.

        Returns:
            List of gene name strings.
        """
        if not genes or not isinstance(genes, list):
            return []

        names: list[str] = []
        for gene in genes:
            if not isinstance(gene, dict):
                continue
            gene_name = gene.get("geneName", {})
            if isinstance(gene_name, dict):
                name = gene_name.get("value")
                if name:
                    names.append(str(name))
        return names

    @staticmethod
    def extract_primary_gene(genes: Any) -> str | None:
        """Extract primary gene name.

        Args:
            genes: List of gene objects.

        Returns:
            Primary gene name or None.
        """
        if not genes or not isinstance(genes, list):
            return None

        for gene in genes:
            if isinstance(gene, dict):
                gene_name = gene.get("geneName", {})
                if isinstance(gene_name, dict):
                    value = gene_name.get("value")
                    if value:
                        return str(value)
        return None

    @staticmethod
    def extract_gene_synonyms(genes: Any) -> str | None:
        """Extract gene synonyms.

        Args:
            genes: List of gene objects.

        Returns:
            JSON array of gene synonyms or None.
        """
        if not genes or not isinstance(genes, list):
            return None

        all_synonyms: list[str] = []
        for gene in genes:
            if not isinstance(gene, dict):
                continue
            synonyms = gene.get("synonyms", [])
            if isinstance(synonyms, list):
                for syn in synonyms:
                    if isinstance(syn, dict):
                        value = syn.get("value")
                        if value:
                            all_synonyms.append(str(value))
        return (
            serialize_to_json(all_synonyms, ensure_ascii=False)
            if all_synonyms
            else None
        )

    @staticmethod
    def extract_gene_orf_names(genes: Any) -> str | None:
        """Extract ORF names from genes.

        Args:
            genes: List of gene objects.

        Returns:
            JSON array of ORF names or None.
        """
        if not genes or not isinstance(genes, list):
            return None

        all_orf: list[str] = []
        for gene in genes:
            if not isinstance(gene, dict):
                continue
            orf_names = gene.get("orfNames", [])
            if isinstance(orf_names, list):
                for orf in orf_names:
                    if isinstance(orf, dict):
                        value = orf.get("value")
                        if value:
                            all_orf.append(str(value))
        return serialize_to_json(all_orf, ensure_ascii=False) if all_orf else None

================================================================================
File: utils.py
Path: pipelines\uniprot\extractors\utils.py
================================================================================
"""Utility functions for UniProt data extraction."""

from __future__ import annotations

from typing import Any, ClassVar

import orjson


class ExtractorUtils:
    """Common utility methods for UniProt data extraction."""

    # Mapping of UniProt protein existence values
    EXISTENCE_MAP: ClassVar[dict[str, str]] = {
        "1: Evidence at protein level": "Evidence at protein level",
        "2: Evidence at transcript level": "Evidence at transcript level",
        "3: Inferred from homology": "Inferred from homology",
        "4: Predicted": "Predicted",
        "5: Uncertain": "Uncertain",
    }

    @staticmethod
    def serialize_list(value: Any) -> str | None:
        """Serialize a list to JSON string.

        Args:
            value: List to serialize, or None/non-list.

        Returns:
            JSON string or None if empty/None/not a list.
        """
        if not value or not isinstance(value, list):
            return None
        return orjson.dumps(value).decode("utf-8")

    @staticmethod
    def count_list(value: Any) -> int | None:
        """Count items in a list.

        Args:
            value: List to count, or None/non-list.

        Returns:
            Count or None if not a list.
        """
        if value is None:
            return None
        if isinstance(value, list):
            return len(value)
        return None

    @staticmethod
    def is_reviewed(entry_type: Any) -> bool:
        """Check if entry is Swiss-Prot (reviewed).

        Args:
            entry_type: Entry type string from record.

        Returns:
            True if reviewed (Swiss-Prot), False otherwise.
        """
        return "Swiss-Prot" in str(entry_type or "")

    @classmethod
    def extract_protein_existence(cls, existence: Any) -> str | None:
        """Extract and normalize protein existence level.

        Args:
            existence: Raw protein existence value from API.

        Returns:
            Normalized protein existence level or None.
        """
        if not existence:
            return None
        existence_str = str(existence)
        return cls.EXISTENCE_MAP.get(existence_str, existence_str)

    @staticmethod
    def _extract_values_from_list(
        data: list[dict[str, Any]], key: str = "value"
    ) -> list[str]:
        """Extract values from a list of dictionaries.

        Args:
            data: List of dictionaries.
            key: Key to extract from each dictionary.

        Returns:
            List of extracted values.
        """
        values = [item.get(key) for item in data if isinstance(item, dict)]
        return [v for v in values if v]

    @staticmethod
    def extract_short_names(recommended_name: dict[str, Any] | None) -> str | None:
        """Extract short names from recommended name.

        Args:
            recommended_name: proteinDescription.recommendedName dict.

        Returns:
            JSON array of short names or None.
        """
        if not recommended_name:
            return None
        short_names = recommended_name.get("shortNames")
        if not isinstance(short_names, list):
            return None
        values = ExtractorUtils._extract_values_from_list(short_names)
        return orjson.dumps(values).decode("utf-8") if values else None

    @staticmethod
    def extract_alternative_names(protein_desc: Any) -> str | None:
        """Extract alternative protein names.

        Args:
            protein_desc: proteinDescription dict.

        Returns:
            JSON array of alternative names or None.
        """
        if not protein_desc or not isinstance(protein_desc, dict):
            return None
        alt_names = protein_desc.get("alternativeNames")
        if not isinstance(alt_names, list):
            return None

        values = []
        for alt in alt_names:
            if not isinstance(alt, dict):
                continue
            full_name = alt.get("fullName")
            if isinstance(full_name, dict):
                name = full_name.get("value")
                if name:
                    values.append(name)
        return orjson.dumps(values).decode("utf-8") if values else None

    @staticmethod
    def extract_ec_numbers(recommended_name: dict[str, Any] | None) -> str | None:
        """Extract EC numbers from recommended name.

        Args:
            recommended_name: proteinDescription.recommendedName dict.

        Returns:
            JSON array of EC numbers or None.
        """
        if not recommended_name:
            return None
        ec_numbers = recommended_name.get("ecNumbers")
        if not isinstance(ec_numbers, list):
            return None
        values = ExtractorUtils._extract_values_from_list(ec_numbers)
        return orjson.dumps(values).decode("utf-8") if values else None

================================================================================
File: idmapping_transformer.py
Path: pipelines\uniprot\idmapping_transformer.py
================================================================================
"""UniProt ID Mapping Transformer.

Transforms ID Mapping results into Silver-layer format using
the IDMappingResult domain entity for validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities.uniprot import IDMappingResult
from bioetl.domain.services import IdentityService

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord, SilverRecord


class IDMappingTransformer(BaseTransformer):
    """Transformer for UniProt ID Mapping results.

    Transforms ChEMBL → UniProt mapping results to Silver records.
    Records without a successful mapping have:
    - uniprot_accession: None
    - mapping_status: 'not_found'
    - _dq_warn: True

    Input (Bronze-like): {"target_chembl_id": "CHEMBL204", "uniprot_accession": "P00742"}
    Output (Silver): Full entity with lineage metadata and DQ flags.
    """

    def __init__(
        self,
        provider: str = "uniprot",
        entity_type: str = "idmapping",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ):
        """Initialize ID Mapping transformer.

        Args:
            provider: Data provider identifier (default: 'uniprot').
            entity_type: Entity type for metrics labels (default: 'idmapping').
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing sensitive data.
            data_normalizer: Data normalization service for text normalization.
        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform ID Mapping result to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Bronze-like record with target_chembl_id and uniprot_accession.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            TransformationError: If required fields are missing.
            ValueError: If IDMappingResult entity validation fails.
        """
        # Step 1: Extract required field
        target_chembl_id = self._get_required_field(record, "target_chembl_id")
        uniprot_accession = record.get("uniprot_accession")  # Can be None

        # Step 2: Determine mapping status
        mapping_status = "found" if uniprot_accession else "not_found"

        # Step 3: Build business data dictionary for content hash
        business_data: dict[str, Any] = {
            "target_chembl_id": target_chembl_id,
            "uniprot_accession": uniprot_accession,
            "mapping_status": mapping_status,
        }

        # Step 4: Generate entity_id using IdentityService (RULES.md §2.8)
        entity_id = self.compute_entity_id(
            source_id=target_chembl_id,
            record={"target_chembl_id": target_chembl_id},
        )

        # Step 5: Compute content_hash (RULES.md §2.8.1)
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Step 6: Create domain entity with lineage metadata
        entity = self._create_entity(
            IDMappingResult,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # Step 7: Convert to SilverRecord with lineage field renaming
        silver_record = self.entity_to_silver_record(entity)

        # Step 8: Set DQ warning flag for not_found mappings
        silver_record["_dq_warn"] = mapping_status != "found"

        return cast("SilverRecord", silver_record)

================================================================================
File: protein.py
Path: pipelines\uniprot\protein.py
================================================================================
"""UniProt Protein Pipeline Implementation.

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class UniProtProteinPipeline(BasePipeline):
    """Pipeline for processing UniProt proteins.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline

================================================================================
File: transformer.py
Path: pipelines\uniprot\transformer.py
================================================================================
"""UniProt Target Transformer.

Transforms raw UniProt protein records into Silver-layer format using
the UniprotTarget domain entity for validation and invariant checking.

Delegates data extraction to specialized extractors for maintainability.

.. versionchanged:: 2.0.0
    Uses UniprotTarget (canonical) instead of Protein (deprecated).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    TransformationError,
)
from bioetl.application.pipelines.uniprot.extractors import (
    CommentExtractor,
    CrossRefExtractor,
    ExtractorUtils,
    FeatureExtractor,
    GeneExtractor,
)
from bioetl.domain.entities import UniprotTarget
from bioetl.domain.services import IdentityService

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord, SilverRecord


class UniProtProteinTransformer(BaseTransformer):
    """Transformer for UniProt protein records.

    Uses UniprotTarget domain entity (canonical name) for validation
    and lineage tracking. Records without required fields (accession,
    entry_name) are skipped. protein_name is optional and may be None.

    Delegates extraction logic to specialized extractors:
    - CommentExtractor: functional annotations
    - CrossRefExtractor: GO terms, database references
    - FeatureExtractor: sequence features and keywords
    - GeneExtractor: gene names and synonyms
    - ExtractorUtils: protein names and utilities
    """

    # Pre-defined paths for optimized extraction
    _PROTEIN_DESC_FLAG_PATH = ("proteinDescription", "flag")
    _ORGANISM_SCIENTIFIC_PATH = ("organism", "scientificName")
    _ORGANISM_COMMON_PATH = ("organism", "commonName")
    _ORGANISM_TAXON_ID_PATH = ("organism", "taxonId")
    _ORGANISM_LINEAGE_PATH = ("organism", "lineage")
    _SEQUENCE_VALUE_PATH = ("sequence", "value")
    _SEQUENCE_LENGTH_PATH = ("sequence", "length")
    _SEQUENCE_MOL_WEIGHT_PATH = ("sequence", "molWeight")
    _SEQUENCE_CRC64_PATH = ("sequence", "crc64")
    _PROTEIN_NAME_PATH = (
        "proteinDescription",
        "recommendedName",
        "fullName",
        "value",
    )

    def __init__(
        self,
        provider: str = "uniprot",
        entity_type: str = "protein",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ):
        """Initialize UniProt protein transformer.

        Args:
            provider: Data provider identifier.
            entity_type: Entity type for metrics labels. Defaults to 'protein'.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names and other PII.
            data_normalizer: Data normalization service for text normalization.
        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform raw UniProt record to Silver format."""
        accession = self._get_required_field(record, "primaryAccession")
        entry_name = self._get_entry_name(record)

        business_data = self._build_business_data(record, accession, entry_name)

        entity_id = self.compute_entity_id(
            source_id=accession,
            record={"accession": accession},
        )
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        entity = self._create_entity(
            UniprotTarget,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        return cast("SilverRecord", self.entity_to_silver_record(entity))

    def _get_entry_name(self, record: BronzeRecord) -> str:
        """Extract entry name (uniProtkbId) as required field."""
        entry_name = record.get("uniProtkbId")
        if not entry_name:
            raise TransformationError(
                "Missing required field: uniProtkbId", field="uniProtkbId"
            )
        return str(entry_name)

    def _build_business_data(
        self, record: BronzeRecord, accession: str, entry_name: str
    ) -> dict[str, Any]:
        """Build the business data dictionary from record."""
        data: dict[str, Any] = {"accession": accession, "entry_name": entry_name}

        self._add_core_identifiers(record, data)
        self._add_protein_names(record, data)
        self._add_gene_data(record, data)
        self._add_organism_data(record, data)
        self._add_evidence_data(record, data)
        self._add_sequence_data(record, data)
        self._add_functional_annotations(record, data)
        self._add_cross_references(record, data)
        self._add_features_and_keywords(record, data)
        self._add_counts(record, data)

        # Legacy compatibility
        data["organism_id"] = data.get("taxonomy_id")

        return data

    def _add_core_identifiers(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add core identifier fields."""
        data["entry_type"] = record.get("entryType")
        data["secondary_accessions"] = ExtractorUtils.serialize_list(
            record.get("secondaryAccessions")
        )

    def _add_protein_names(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add protein name fields."""
        protein_desc = record.get("proteinDescription", {})
        recommended_name = (
            protein_desc.get("recommendedName")
            if isinstance(protein_desc, dict)
            else None
        )

        data["protein_name"] = self._extract_protein_name(record)
        data["protein_short_names"] = ExtractorUtils.extract_short_names(
            recommended_name
        )
        data["protein_alternative_names"] = ExtractorUtils.extract_alternative_names(
            protein_desc
        )
        data["protein_ec_numbers"] = ExtractorUtils.extract_ec_numbers(recommended_name)
        data["flag"] = self._extract_by_path(record, self._PROTEIN_DESC_FLAG_PATH)

    def _add_gene_data(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add gene-related fields."""
        genes = record.get("genes")
        data["gene_names"] = GeneExtractor.extract_gene_names(genes)
        data["gene_primary"] = GeneExtractor.extract_primary_gene(genes)
        data["gene_synonyms"] = GeneExtractor.extract_gene_synonyms(genes)
        data["gene_orf_names"] = GeneExtractor.extract_gene_orf_names(genes)

    def _add_organism_data(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add organism and taxonomy fields."""
        data["organism_scientific"] = self._extract_by_path(
            record, self._ORGANISM_SCIENTIFIC_PATH
        )
        data["organism_common"] = self._extract_by_path(
            record, self._ORGANISM_COMMON_PATH
        )
        data["taxonomy_id"] = self._extract_by_path(
            record, self._ORGANISM_TAXON_ID_PATH
        )
        data["lineage"] = ExtractorUtils.serialize_list(
            self._extract_by_path(record, self._ORGANISM_LINEAGE_PATH)
        )

    def _add_evidence_data(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add evidence and quality fields."""
        data["protein_existence"] = ExtractorUtils.extract_protein_existence(
            record.get("proteinExistence")
        )
        data["annotation_score"] = record.get("annotationScore")
        data["reviewed"] = ExtractorUtils.is_reviewed(record.get("entryType"))

    def _add_sequence_data(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add sequence fields."""
        data["sequence"] = self._extract_by_path(record, self._SEQUENCE_VALUE_PATH)
        data["sequence_length"] = self._extract_by_path(
            record, self._SEQUENCE_LENGTH_PATH
        )
        data["sequence_mass"] = self._extract_by_path(
            record, self._SEQUENCE_MOL_WEIGHT_PATH
        )
        data["sequence_checksum"] = self._extract_by_path(
            record, self._SEQUENCE_CRC64_PATH
        )

    def _add_functional_annotations(
        self, record: BronzeRecord, data: dict[str, Any]
    ) -> None:
        """Add functional annotation fields."""
        comments = record.get("comments")
        data["function_comment"] = CommentExtractor.extract_by_type(
            comments, "FUNCTION"
        )
        data["catalytic_activity"] = CommentExtractor.extract_catalytic_activity(
            comments
        )
        data["activity_regulation"] = CommentExtractor.extract_by_type(
            comments, "ACTIVITY REGULATION"
        )
        data["subunit"] = CommentExtractor.extract_by_type(comments, "SUBUNIT")
        data["pathway"] = CommentExtractor.extract_by_type(comments, "PATHWAY")
        data["subcellular_location"] = CommentExtractor.extract_subcellular_locations(
            comments
        )
        data["tissue_specificity"] = CommentExtractor.extract_by_type(
            comments, "TISSUE SPECIFICITY"
        )
        data["alternative_products"] = CommentExtractor.extract_alternative_products(
            comments
        )
        data["disease_involvement"] = CommentExtractor.extract_by_type(
            comments, "DISEASE"
        )
        data["similarity_comment"] = CommentExtractor.extract_by_type(
            comments, "SIMILARITY"
        )
        data["caution"] = CommentExtractor.extract_by_type(comments, "CAUTION")

    def _add_cross_references(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add cross-reference fields."""
        xrefs = record.get("uniProtKBCrossReferences")
        data["go_terms"] = CrossRefExtractor.extract_go_terms(xrefs)
        data["drugbank_ids"] = CrossRefExtractor.extract_xref_ids(xrefs, "DrugBank")
        data["chembl_ids"] = CrossRefExtractor.extract_xref_ids(xrefs, "ChEMBL")
        data["guidetopharmacology_ids"] = CrossRefExtractor.extract_xref_ids(
            xrefs, "GuidetoPHARMACOLOGY"
        )

    def _add_features_and_keywords(
        self, record: BronzeRecord, data: dict[str, Any]
    ) -> None:
        """Add feature and keyword fields."""
        data["features"] = FeatureExtractor.extract_features(record.get("features"))
        data["keywords"] = FeatureExtractor.extract_keywords(record.get("keywords"))

    def _add_counts(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add count fields."""
        xrefs = record.get("uniProtKBCrossReferences")
        comments = record.get("comments")
        data["cross_reference_count"] = ExtractorUtils.count_list(xrefs)
        data["feature_count"] = ExtractorUtils.count_list(record.get("features"))
        data["keyword_count"] = ExtractorUtils.count_list(record.get("keywords"))
        data["isoform_count"] = CommentExtractor.count_isoforms(comments)

    def _extract_protein_name(self, record: BronzeRecord) -> str | None:
        """Extract protein name (optional field)."""
        protein_name = self._extract_by_path(
            record,
            self._PROTEIN_NAME_PATH,
        )
        return str(protein_name) if protein_name else None

================================================================================
File: __init__.py
Path: services\__init__.py
================================================================================
"""Application services for cross-cutting concerns.

Implements RULES.md §4 - Application Layer services.
These services coordinate business logic and are injected into runners.

Administrative services for CLI operations:
- CheckpointService: Checkpoint listing, deletion, inspection
- QuarantineService: Quarantine inspection, replay, purge
- LockService: Lock management
- BronzeCleanupService: Bronze retention cleanup
- PipelineRunnerService: Universal pipeline execution
- ConfigService: Configuration access and validation
- HealthService: Provider health checking
"""

from __future__ import annotations

from bioetl.application.services.bronze_cleanup_service import (
    BronzeCleanupService,
    CleanupResult,
)
from bioetl.application.services.checkpoint_service import (
    CheckpointInfo,
    CheckpointService,
)
from bioetl.application.services.config_service import (
    ConfigService,
    PipelineInfo,
    SettingsInfo,
)
from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.dq_report_service import (
    DQReportContext,
    DQReportResult,
    DQReportService,
)
from bioetl.application.services.export_service import (
    ColumnInfo,
    ExportOptions,
    ExportResult,
    ExportService,
    TableInfo,
    TablePreview,
)
from bioetl.application.services.health_service import (
    HealthCheckSummary,
    HealthResult,
    HealthService,
)
from bioetl.application.services.lock_service import (
    LockInfo,
    LockService,
)
from bioetl.application.services.medallion_lifecycle import (
    ClearResult,
    MedallionLifecycleService,
)
from bioetl.application.services.metrics_service import (
    MetricsServerError,
    MetricsServerPort,
    MetricsServerStatus,
    MetricsService,
    StartResult,
)
from bioetl.application.services.pipeline_runner_service import (
    PipelineNotFoundError,
    PipelineRunnerService,
    RunOptions,
    RunResult,
    RunStatus,
)
from bioetl.application.services.quarantine_service import (
    QuarantineRecord,
    QuarantineService,
)
from bioetl.application.services.shutdown_service import (
    PipelineShutdownError,
    ShutdownReason,
    ShutdownService,
)
from bioetl.application.services.vacuum_service import (
    TableCollectorPort,
    TableVacuumResult,
    VacuumAllResult,
    VacuumService,
)

# Re-export from domain for backward compatibility
from bioetl.domain.services.dq_metrics_calculator import (
    DQMetricsCalculator,
    DQMetricsInput,
)

__all__ = [
    "BronzeCleanupService",
    "CheckpointInfo",
    "CheckpointService",
    "CleanupResult",
    "ClearResult",
    "ColumnInfo",
    "ConfigService",
    "DQMetricsCalculator",
    "DQMetricsInput",
    "DQReportContext",
    "DQReportResult",
    "DQReportService",
    "DataQualityService",
    "ExportOptions",
    "ExportResult",
    "ExportService",
    "HealthCheckSummary",
    "HealthResult",
    "HealthService",
    "LockInfo",
    "LockService",
    "MedallionLifecycleService",
    "MetricsServerError",
    "MetricsServerPort",
    "MetricsServerStatus",
    "MetricsService",
    "PipelineInfo",
    "PipelineNotFoundError",
    "PipelineRunnerService",
    "PipelineShutdownError",
    "QuarantineRecord",
    "QuarantineService",
    "RunOptions",
    "RunResult",
    "RunStatus",
    "SettingsInfo",
    "ShutdownReason",
    "ShutdownService",
    "StartResult",
    "TableCollectorPort",
    "TableInfo",
    "TablePreview",
    "TableVacuumResult",
    "VacuumAllResult",
    "VacuumService",
]

================================================================================
File: bronze_cleanup_service.py
Path: services\bronze_cleanup_service.py
================================================================================
"""Bronze cleanup service for retention operations (Application layer).

Provides high-level Bronze layer cleanup for CLI and other interfaces.
Uses StoragePort for actual cleanup operations.

Implements RULES.md §2.1 - Bronze layer 90-day retention policy.
Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, StoragePort


@dataclass(frozen=True, slots=True)
class CleanupResult:
    """Result of Bronze cleanup operation.

    Attributes:
        files_removed: Number of files removed.
        bytes_freed: Total bytes freed.
        directories_removed: Number of empty directories removed.
        dry_run: Whether this was a dry run.
        cutoff_date: Cutoff date used for cleanup.
    """

    files_removed: int
    bytes_freed: int
    directories_removed: int
    dry_run: bool
    cutoff_date: datetime


@dataclass
class BronzeCleanupService:
    """Service for Bronze layer cleanup operations.

    Provides high-level operations for Bronze cleanup
    used by CLI and other interfaces. Wraps StoragePort
    for Application-layer abstraction.

    Implements RULES.md §2.1 Bronze layer retention:
    - Default retention: 90 days
    - Files older than retention period are removed
    - Empty directories are cleaned up

    Attributes:
        storage: StoragePort for storage operations.
        logger: Structured logger for observability.

    Example:
        >>> service = BronzeCleanupService(storage=storage, logger=logger)
        >>> result = await service.cleanup(retention_days=90)
        >>> logger.info("cleanup_complete", files_removed=result.files_removed)
    """

    storage: StoragePort
    logger: LoggerPort

    async def cleanup(
        self,
        retention_days: int = 90,
        dry_run: bool = False,
    ) -> CleanupResult:
        """Clean up old Bronze files based on retention policy.

        Removes files older than the specified retention period.
        Per RULES.md §2.1, default retention is 90 days.

        Args:
            retention_days: Files older than this will be removed (default: 90).
            dry_run: If True, only show what would be removed.

        Returns:
            CleanupResult with cleanup statistics.
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

        self.logger.info(
            "Starting Bronze cleanup",
            retention_days=retention_days,
            cutoff_date=cutoff_date.isoformat(),
            dry_run=dry_run,
        )

        result = await self.storage.cleanup_bronze(
            cutoff_date=cutoff_date,
            dry_run=dry_run,
        )

        cleanup_result = CleanupResult(
            files_removed=result["files_removed"],
            bytes_freed=result["bytes_freed"],
            directories_removed=result["directories_removed"],
            dry_run=dry_run,
            cutoff_date=cutoff_date,
        )

        self._log_result(cleanup_result)

        return cleanup_result

    def _log_result(self, result: CleanupResult) -> None:
        """Log cleanup result.

        Args:
            result: The cleanup result to log.
        """
        self.logger.info(
            "bronze_cleanup_completed",
            files_removed=result.files_removed,
            bytes_freed=result.bytes_freed,
            directories_removed=result.directories_removed,
            cutoff_date=result.cutoff_date.isoformat(),
            dry_run=result.dry_run,
        )

    @staticmethod
    def format_bytes(b: int) -> str:
        """Format bytes as human-readable string.

        Args:
            b: Number of bytes.

        Returns:
            Human-readable string (e.g., "1.5 GB").
        """
        for unit, div in [("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)]:
            if b >= div:
                return f"{b / div:.2f} {unit}"
        return f"{b} bytes"

    async def aclose(self) -> None:
        """Close the service and release resources."""
        await self.storage.aclose()

================================================================================
File: checkpoint_service.py
Path: services\checkpoint_service.py
================================================================================
"""Checkpoint service for administrative operations (Application layer).

Provides high-level checkpoint management for CLI and other interfaces.
Uses CheckpointPort for actual persistence operations.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.ports import CheckpointPort, LoggerPort


@dataclass(frozen=True, slots=True)
class CheckpointInfo:
    """Information about a checkpoint.

    Attributes:
        pipeline_name: Name of the pipeline.
        run_id: Run ID that created this checkpoint.
        metadata: Checkpoint metadata (records_processed, etc.).
    """

    pipeline_name: str
    run_id: str | None
    metadata: dict[str, Any]


@dataclass
class CheckpointService:
    """Service for administrative checkpoint operations.

    Provides high-level operations for checkpoint management
    used by CLI and other interfaces. Wraps CheckpointPort
    for Application-layer abstraction.

    Attributes:
        checkpoint_port: Port for checkpoint persistence.
        logger: Structured logger for observability.

    Example:
        >>> service = CheckpointService(checkpoint_port=port, logger=logger)
        >>> checkpoints = await service.list_checkpoints()
        >>> for cp in checkpoints:
        ...     logger.info("checkpoint", pipeline=cp.pipeline_name, metadata=cp.metadata)
    """

    checkpoint_port: CheckpointPort
    logger: LoggerPort

    async def list_checkpoints(self) -> list[CheckpointInfo]:
        """List all checkpoints across all pipelines.

        Returns:
            List of CheckpointInfo with pipeline names and metadata.
        """
        self.logger.debug("Listing all checkpoints")

        pipeline_names = await self.checkpoint_port.list_all()
        checkpoints: list[CheckpointInfo] = []

        for pipeline_name in pipeline_names:
            checkpoint_data = await self.checkpoint_port.load(pipeline_name)
            if checkpoint_data:
                run_id, metadata = checkpoint_data
                checkpoints.append(
                    CheckpointInfo(
                        pipeline_name=pipeline_name,
                        run_id=str(run_id),
                        metadata=metadata,
                    )
                )
            else:
                # Checkpoint exists but couldn't be loaded
                checkpoints.append(
                    CheckpointInfo(
                        pipeline_name=pipeline_name,
                        run_id=None,
                        metadata={},
                    )
                )

        self.logger.info(
            "Listed checkpoints",
            checkpoint_count=len(checkpoints),
        )

        return checkpoints

    async def get_checkpoint(self, pipeline_name: str) -> CheckpointInfo | None:
        """Get checkpoint for a specific pipeline.

        Args:
            pipeline_name: Name of the pipeline.

        Returns:
            CheckpointInfo if checkpoint exists, None otherwise.
        """
        self.logger.debug("Getting checkpoint", pipeline=pipeline_name)

        checkpoint_data = await self.checkpoint_port.load(pipeline_name)
        if checkpoint_data is None:
            self.logger.debug("Checkpoint not found", pipeline=pipeline_name)
            return None

        run_id, metadata = checkpoint_data
        self.logger.info(
            "Got checkpoint",
            pipeline=pipeline_name,
            run_id=str(run_id),
        )

        return CheckpointInfo(
            pipeline_name=pipeline_name,
            run_id=str(run_id),
            metadata=metadata,
        )

    async def delete_checkpoint(self, pipeline_name: str) -> bool:
        """Delete checkpoint for a specific pipeline.

        Args:
            pipeline_name: Name of the pipeline.

        Returns:
            True if checkpoint was deleted, False if it didn't exist.
        """
        self.logger.debug("Deleting checkpoint", pipeline=pipeline_name)

        # Check if checkpoint exists first
        existing = await self.checkpoint_port.load(pipeline_name)
        if existing is None:
            self.logger.debug(
                "Checkpoint not found for deletion", pipeline=pipeline_name
            )
            return False

        await self.checkpoint_port.delete(pipeline_name)
        self.logger.info("Deleted checkpoint", pipeline=pipeline_name)

        return True

    async def aclose(self) -> None:
        """Close the service and release resources."""
        await self.checkpoint_port.aclose()

================================================================================
File: config_service.py
Path: services\config_service.py
================================================================================
"""Configuration service for administrative operations (Application layer).

Provides high-level configuration access for CLI and other interfaces.
Abstracts infrastructure configuration loading behind application service.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bioetl.domain.config import PipelineConfig

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class PipelineInfo:
    """Summary information about a registered pipeline.

    Attributes:
        name: Name of the pipeline (e.g., 'chembl_activity').
        provider: Data provider (e.g., 'chembl').
        entity_type: Entity type being processed (e.g., 'activity').
        silver_table: Name of the Silver table.
        gold_table: Name of the Gold table (if configured).
    """

    name: str
    provider: str
    entity_type: str
    silver_table: str
    gold_table: str | None


@dataclass(frozen=True, slots=True)
class SettingsInfo:
    """Application settings information.

    Attributes:
        env: Current environment (dev, staging, prod).
        data_dir: Base directory for all data storage.
        bronze_path: Path for Bronze layer storage.
        silver_path: Path for Silver layer storage.
        gold_path: Path for Gold layer storage.
        checkpoint_path: Path for checkpoint storage.
        quarantine_path: Path for quarantine storage.
        debug: Debug mode enabled.
        test_mode: Test mode enabled.
        metrics_enabled: Metrics collection enabled.
        metrics_port: Port for Prometheus metrics HTTP server.
        batch_size: Default batch size for pipeline execution.
        additional: Additional settings as dictionary.
    """

    env: str
    data_dir: str
    bronze_path: str
    silver_path: str
    gold_path: str
    checkpoint_path: str
    quarantine_path: str
    debug: bool
    test_mode: bool
    metrics_enabled: bool
    metrics_port: int
    batch_size: int
    additional: dict[str, Any]


@dataclass
class ConfigService:
    """Service for configuration access operations.

    Provides high-level operations for accessing application configuration
    used by CLI and other interfaces. Abstracts infrastructure details
    for Application-layer access.

    Attributes:
        logger: Structured logger for observability.
        _settings_loader: Callable to load Settings from infrastructure.
        _pipeline_config_loader: Callable to load pipeline YAML config.
        _domain_config_mapper: Callable to convert YAML config to domain config.
        _registry_accessor: Callable to access pipeline registry.

    Example:
        >>> service = ConfigService(logger=logger, ...)
        >>> settings = service.get_settings()
        >>> logger.info("environment", env=settings.env)
    """

    logger: LoggerPort
    _settings_loader: Any  # Callable[[], Settings]
    _pipeline_config_loader: Any  # Callable[[str], PipelineYamlConfig]
    _domain_config_mapper: Any  # Callable[[PipelineYamlConfig], PipelineConfig]
    _registry_accessor: Any  # Callable[[], PipelineRegistry]

    def get_settings(self) -> SettingsInfo:
        """Get application settings.

        Returns:
            SettingsInfo with current application configuration.
        """
        self.logger.debug("Getting application settings")

        settings = self._settings_loader()

        # Extract additional settings for extensibility
        settings_dict = settings.model_dump()
        additional = {
            k: v
            for k, v in settings_dict.items()
            if k
            not in {
                "env",
                "data_dir",
                "debug",
                "test_mode",
                "metrics_enabled",
                "metrics_port",
                "pipeline",
            }
        }

        info = SettingsInfo(
            env=settings.env,
            data_dir=str(settings.data_dir),
            bronze_path=str(settings.bronze_path),
            silver_path=str(settings.silver_path),
            gold_path=str(settings.gold_path),
            checkpoint_path=str(settings.checkpoint_path),
            quarantine_path=str(settings.quarantine_path),
            debug=settings.debug,
            test_mode=settings.test_mode,
            metrics_enabled=settings.metrics_enabled,
            metrics_port=settings.metrics_port,
            batch_size=settings.pipeline.batch_size,
            additional=additional,
        )

        self.logger.info("Got application settings", env=info.env)
        return info

    def load_pipeline_config(self, pipeline_name: str) -> PipelineConfig:
        """Load and validate pipeline configuration.

        Args:
            pipeline_name: Name of the pipeline (e.g., 'chembl_activity').

        Returns:
            PipelineConfig domain object for the pipeline.

        Raises:
            ValueError: If pipeline configuration not found.
            FileNotFoundError: If pipeline config file is missing.
        """
        self.logger.debug("Loading pipeline config", pipeline=pipeline_name)

        yaml_config = self._pipeline_config_loader(pipeline_name)
        domain_config: PipelineConfig = self._domain_config_mapper(yaml_config)

        self.logger.info(
            "Loaded pipeline config",
            pipeline=pipeline_name,
            provider=domain_config.provider,
            entity_type=domain_config.entity_type,
        )

        return domain_config

    def get_pipeline_yaml_config(self, pipeline_name: str) -> dict[str, Any]:
        """Get raw pipeline YAML configuration as dictionary.

        Useful for CLI display commands that show full configuration.

        Args:
            pipeline_name: Name of the pipeline (e.g., 'chembl_activity').

        Returns:
            Dictionary representation of the YAML configuration.

        Raises:
            ValueError: If pipeline configuration not found.
            FileNotFoundError: If pipeline config file is missing.
        """
        self.logger.debug("Getting pipeline YAML config", pipeline=pipeline_name)

        yaml_config = self._pipeline_config_loader(pipeline_name)

        # Convert Pydantic model to dict
        if hasattr(yaml_config, "model_dump"):
            config_dict: dict[str, Any] = yaml_config.model_dump()
        else:
            config_dict = dict(yaml_config)

        self.logger.info("Got pipeline YAML config", pipeline=pipeline_name)
        return config_dict

    def validate_pipeline_config(self, pipeline_name: str) -> PipelineInfo:
        """Validate pipeline configuration and return summary info.

        Args:
            pipeline_name: Name of the pipeline (e.g., 'chembl_activity').

        Returns:
            PipelineInfo with summary of validated configuration.

        Raises:
            ValueError: If pipeline configuration is invalid.
            FileNotFoundError: If pipeline config file is missing.
        """
        self.logger.debug("Validating pipeline config", pipeline=pipeline_name)

        yaml_config = self._pipeline_config_loader(pipeline_name)

        info = PipelineInfo(
            name=pipeline_name,
            provider=yaml_config.provider,
            entity_type=yaml_config.entity_type,
            silver_table=yaml_config.silver_table,
            gold_table=yaml_config.gold_table,
        )

        self.logger.info(
            "Validated pipeline config",
            pipeline=pipeline_name,
            provider=info.provider,
        )

        return info

    def list_pipelines(self) -> list[str]:
        """List all registered pipelines.

        Returns:
            List of pipeline names.
        """
        self.logger.debug("Listing registered pipelines")

        registry = self._registry_accessor()
        pipelines: list[str] = registry.list_pipelines()

        self.logger.info("Listed pipelines", count=len(pipelines))
        return pipelines

================================================================================
File: data_quality_service.py
Path: services\data_quality_service.py
================================================================================
"""Data Quality Service for centralized DQ evaluation.

Application Service that handles all data quality checks and anomaly detection.
Extracted from PostrunService to follow Single Responsibility Principle.

Responsibilities:
- Threshold checks (soft/hard fail)
- Anomaly detection via DQMonitorPort
- DQ metrics emission
- Baseline updates

Does NOT handle:
- VACUUM operations (MedallionLifecycleService)
- Tracer cleanup (PostrunService)
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from bioetl.domain.exceptions.data_quality import DataQualityThresholdError
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

if TYPE_CHECKING:
    from bioetl.domain.config import DQConfig
    from bioetl.domain.ports import DQMonitorPort, LoggerPort, MetricsPort


class DataQualityService:
    """Centralized service for data quality evaluation.

    Performs threshold checks, anomaly detection, and metrics emission.
    Designed to be injected into PostrunService or used standalone.

    Attributes:
        _dq_monitor: Optional DQ monitor for anomaly detection.
        _config: DQ configuration with thresholds.
        _logger: Structured logger for DQ events.
        _metrics: Optional metrics port for observability.
        _pipeline_name: Pipeline name for metric labels.
    """

    def __init__(
        self,
        dq_monitor: DQMonitorPort | None,
        config: DQConfig,
        logger: LoggerPort,
        metrics: MetricsPort | None,
        pipeline_name: str,
    ) -> None:
        """Initialize DataQualityService.

        Args:
            dq_monitor: Optional DQ monitor for anomaly detection.
            config: DQ configuration with soft/hard thresholds.
            logger: Structured logger for DQ events.
            metrics: Optional metrics port for observability.
            pipeline_name: Pipeline name for metric labels.
        """
        self._dq_monitor = dq_monitor
        self._config = config
        self._logger = logger
        self._metrics = metrics
        self._pipeline_name = pipeline_name

    async def evaluate(
        self,
        metrics: dict[str, float],
    ) -> DQResult:
        """Evaluate data quality based on metrics.

        Performs threshold checks before anomaly detection:
        1. If error_rate >= hard_fail_threshold: raises DataQualityThresholdError
        2. If error_rate >= soft_fail_threshold: logs warning + emits metric
        3. Then runs anomaly detection if dq_monitor is available

        Args:
            metrics: Dictionary of metric names to values.
                     Must contain 'error_rate' key.

        Returns:
            DQResult with evaluation outcome.

        Raises:
            DataQualityThresholdError: If error rate exceeds hard threshold.
        """
        error_rate = metrics.get("error_rate", 0.0)

        # Check hard threshold first - raises if exceeded
        self._check_hard_threshold(error_rate)

        # Determine status based on soft threshold
        status = self._determine_status(error_rate)

        # Log warning and emit metric if soft threshold exceeded
        if status == DQEvaluationStatus.WARNING:
            self._emit_soft_threshold_warning(error_rate)

        # Run anomaly detection if monitor available
        if self._dq_monitor is None:
            return DQResult(
                error_rate=error_rate,
                status=status,
                anomalies=(),
                has_critical=False,
                check_duration_ms=0.0,
            )

        return self._run_anomaly_detection(metrics, error_rate, status)

    def _check_hard_threshold(self, error_rate: float) -> None:
        """Check if error rate exceeds hard threshold.

        Args:
            error_rate: Current error rate.

        Raises:
            DataQualityThresholdError: If threshold exceeded.
        """
        if error_rate >= self._config.hard_fail_threshold:
            self._logger.error(
                "DQ hard threshold exceeded",
                error_rate=error_rate,
                threshold=self._config.hard_fail_threshold,
                pipeline=self._pipeline_name,
            )
            raise DataQualityThresholdError(
                error_rate=error_rate,
                threshold=self._config.hard_fail_threshold,
            )

    def _determine_status(self, error_rate: float) -> DQEvaluationStatus:
        """Determine DQ status based on error rate.

        Args:
            error_rate: Current error rate.

        Returns:
            DQEvaluationStatus based on threshold comparison.
        """
        if error_rate >= self._config.soft_fail_threshold:
            return DQEvaluationStatus.WARNING
        return DQEvaluationStatus.PASSED

    def _emit_soft_threshold_warning(self, error_rate: float) -> None:
        """Log warning and emit metric for soft threshold breach.

        Args:
            error_rate: Current error rate.
        """
        self._logger.warning(
            "DQ soft threshold exceeded",
            error_rate=error_rate,
            threshold=self._config.soft_fail_threshold,
            pipeline=self._pipeline_name,
        )
        if self._metrics:
            self._metrics.increment_counter(
                "dq_soft_threshold_exceeded",
                1,
                {"pipeline": self._pipeline_name},
            )

    def _run_anomaly_detection(
        self,
        metrics: dict[str, float],
        error_rate: float,
        status: DQEvaluationStatus,
    ) -> DQResult:
        """Run anomaly detection and process results.

        Args:
            metrics: Metrics to check for anomalies.
            error_rate: Calculated error rate.
            status: Determined DQ status.

        Returns:
            DQResult with anomaly detection results.

        Note:
            Caller must ensure dq_monitor is not None before calling.
        """
        assert self._dq_monitor is not None

        start_time = time.monotonic()
        anomalies = self._dq_monitor.check_quality(metrics)
        check_duration_ms = (time.monotonic() - start_time) * 1000

        self._record_check_duration(check_duration_ms)

        has_critical = self._process_anomalies(anomalies)

        # Update baseline only if no critical anomalies
        self._dq_monitor.update_baseline_from_metrics(metrics)
        self._update_baseline_metrics(metrics, has_critical)

        return DQResult(
            error_rate=error_rate,
            status=status,
            anomalies=tuple(anomalies),
            has_critical=has_critical,
            check_duration_ms=check_duration_ms,
        )

    def _record_check_duration(self, duration_ms: float) -> None:
        """Record DQ check duration metric.

        Args:
            duration_ms: Duration in milliseconds.
        """
        if self._metrics:
            self._metrics.observe_histogram(
                "dq_check_duration_ms",
                duration_ms,
                {"pipeline": self._pipeline_name},
            )

    def _process_anomalies(self, anomalies: list[Any]) -> bool:
        """Process detected anomalies and check for critical ones.

        Args:
            anomalies: List of detected anomalies.

        Returns:
            True if any critical anomalies found.
        """
        has_critical = False
        for anomaly in anomalies:
            self._process_single_anomaly(anomaly)
            if anomaly.severity.value == "critical":
                has_critical = True
        return has_critical

    def _process_single_anomaly(self, anomaly: Any) -> None:
        """Log and track a single anomaly.

        Args:
            anomaly: Detected anomaly to process.
        """
        self._logger.warning(
            "dq_anomaly_detected",
            anomaly_type=anomaly.anomaly_type.value,
            severity=anomaly.severity.value,
            metric=anomaly.metric_name,
            current_value=anomaly.current_value,
            baseline_mean=anomaly.baseline_mean,
            baseline_stddev=anomaly.baseline_stddev,
            z_score=anomaly.z_score,
            message=anomaly.message,
        )

        if self._metrics:
            self._metrics.increment_counter(
                "dq_anomaly_detected",
                1,
                {
                    "pipeline": self._pipeline_name,
                    "metric": anomaly.metric_name,
                    "severity": anomaly.severity.value,
                    "anomaly_type": anomaly.anomaly_type.value,
                },
            )

        if anomaly.severity.value == "critical":
            self._logger.error(
                "critical_dq_anomaly",
                metric=anomaly.metric_name,
                message=anomaly.message,
            )

    def _update_baseline_metrics(
        self, metrics: dict[str, float], has_critical: bool
    ) -> None:
        """Update baseline metrics counters.

        Args:
            metrics: Metrics used for baseline.
            has_critical: Whether critical anomalies were found.
        """
        if not self._metrics or has_critical:
            return

        for metric_name in metrics:
            self._metrics.increment_counter(
                "dq_baseline_updated",
                1,
                {"pipeline": self._pipeline_name, "metric": metric_name},
            )


__all__ = ["DataQualityService"]

================================================================================
File: __init__.py
Path: services\dq\__init__.py
================================================================================
"""DQ (Data Quality) analysis services.

Provides application services for analyzing data quality across
Medallion Architecture layers (Bronze, Silver, Gold).

Components:
- BronzeDQAnalyzer: Minimal validation for raw data
- SilverDQAnalyzer: Data quality monitoring for normalized data
- GoldDQAnalyzer: Strict validation for data marts
- DQReportSerializer: Report serialization to JSON/YAML/HTML
"""

from bioetl.application.services.dq.bronze_analyzer import BronzeDQAnalyzer
from bioetl.application.services.dq.gold_analyzer import GoldDQAnalyzer
from bioetl.application.services.dq.silver_analyzer import SilverDQAnalyzer
from bioetl.domain.services.dq_serializer import DQReportSerializer

__all__ = [
    "BronzeDQAnalyzer",
    "DQReportSerializer",
    "GoldDQAnalyzer",
    "SilverDQAnalyzer",
]

================================================================================
File: bronze_analyzer.py
Path: services\dq\bronze_analyzer.py
================================================================================
"""Bronze layer DQ analyzer.

Implements minimal validation for raw Bronze data:
- Record count
- File integrity (checksum, size)
- Schema snapshot (field detection)
- Field presence rates
- Encoding validation

Follows RULES.md §3.1 DQ strategy for Bronze layer.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import orjson

from bioetl.domain.ports import BronzeDQConfigPort
from bioetl.domain.value_objects.dq_report import (
    BronzeDQCheckType,
    BronzeDQReport,
    DQCheckStatus,
    DQReportStatus,
    DQReportSummary,
    EncodingValidationResult,
    FileIntegrityResult,
    MedallionLayer,
    RecordCountResult,
    SchemaSnapshotResult,
)


class BronzeDQAnalyzer:
    """Analyzer for Bronze layer DQ checks.

    Performs minimal validation on raw data to capture lineage
    without blocking ingestion. Implements BronzeDQAnalyzerPort.
    """

    def analyze(
        self,
        records: Iterator[bytes],
        *,
        run_id: str,
        pipeline: str,
        batch_id: str,
        source_file: str,
        config: BronzeDQConfigPort,
        timestamp: datetime,
    ) -> BronzeDQReport:
        """Analyze Bronze data and generate DQ report.

        Args:
            records: Iterator of raw JSON bytes records.
            run_id: Pipeline run identifier.
            pipeline: Pipeline name.
            batch_id: Batch identifier.
            source_file: Path to the Bronze file.
            config: DQ report configuration.
            timestamp: Report generation timestamp (UTC).

        Returns:
            BronzeDQReport: Complete DQ report for Bronze layer.
        """
        # Materialize records for analysis (Bronze batches are typically small)
        record_list = list(records)
        enabled_checks = set(config.get_checks_enums())

        checks: dict[str, Any] = {}
        passed = 0
        failed = 0
        warnings = 0

        # Record count check
        if BronzeDQCheckType.RECORD_COUNT in enabled_checks:
            record_count_result = self._check_record_count(record_list)
            checks["record_count"] = self._result_to_dict(record_count_result)
            passed, failed, warnings = self._update_counts(
                record_count_result.status, passed, failed, warnings
            )

        # File integrity check
        if BronzeDQCheckType.FILE_INTEGRITY in enabled_checks:
            file_integrity_result = self._check_file_integrity(record_list)
            checks["file_integrity"] = self._result_to_dict(file_integrity_result)
            passed, failed, warnings = self._update_counts(
                file_integrity_result.status, passed, failed, warnings
            )

        # Schema snapshot
        if BronzeDQCheckType.SCHEMA_SNAPSHOT in enabled_checks:
            schema_snapshot_result = self._check_schema_snapshot(record_list)
            checks["schema_snapshot"] = self._result_to_dict(schema_snapshot_result)
            passed, failed, warnings = self._update_counts(
                schema_snapshot_result.status, passed, failed, warnings
            )

        # Raw field presence
        if BronzeDQCheckType.RAW_FIELD_PRESENCE in enabled_checks:
            field_presence_result = self._check_field_presence(record_list)
            checks["raw_field_presence"] = field_presence_result  # Already a dict
            # Count as pass (info only)
            passed += 1

        # Encoding validation
        if BronzeDQCheckType.ENCODING_VALIDATION in enabled_checks:
            encoding_result = self._check_encoding(record_list)
            checks["encoding_validation"] = self._result_to_dict(encoding_result)
            passed, failed, warnings = self._update_counts(
                encoding_result.status, passed, failed, warnings
            )

        total_checks = passed + failed + warnings

        # Determine overall status
        if failed > 0:
            overall_status = DQReportStatus.FAIL
        elif warnings > 0:
            overall_status = DQReportStatus.WARNING
        else:
            overall_status = DQReportStatus.PASS

        summary = DQReportSummary(
            total_checks=total_checks,
            passed=passed,
            failed=failed,
            warnings=warnings,
            overall_status=overall_status,
        )

        return BronzeDQReport(
            layer=MedallionLayer.BRONZE,
            timestamp=timestamp,
            run_id=run_id,
            pipeline=pipeline,
            batch_id=batch_id,
            source_file=source_file,
            checks=checks,
            summary=summary,
        )

    def _check_record_count(self, records: list[bytes]) -> RecordCountResult:
        """Check record count."""
        count = len(records)
        return RecordCountResult(
            value=count,
            status=DQCheckStatus.PASS if count > 0 else DQCheckStatus.WARN,
        )

    def _check_file_integrity(self, records: list[bytes]) -> FileIntegrityResult:
        """Check file integrity via BLAKE2 checksum."""
        # Calculate combined checksum of all records
        hasher = hashlib.blake2b()
        total_size = 0

        for record in records:
            hasher.update(record)
            total_size += len(record)

        checksum = hasher.hexdigest()

        return FileIntegrityResult(
            checksum_blake2=checksum,
            size_bytes=total_size,
            compression_ratio=None,  # Will be calculated after compression
            status=DQCheckStatus.PASS,
        )

    def _check_schema_snapshot(self, records: list[bytes]) -> SchemaSnapshotResult:
        """Detect schema from records."""
        field_types: dict[str, set[str]] = {}

        for record in records:
            try:
                data = orjson.loads(record)
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key not in field_types:
                            field_types[key] = set()
                        field_types[key].add(self._infer_type(value))
            except orjson.JSONDecodeError:
                continue

        # Convert sets to string representation
        schema = {}
        for field, types in field_types.items():
            if len(types) == 1:
                schema[field] = next(iter(types))
            else:
                schema[field] = "|".join(sorted(types))

        return SchemaSnapshotResult(
            fields_detected=len(schema),
            schema=schema,
            new_fields_since_last_run=(),  # Would need previous schema
            missing_fields_since_last_run=(),
            status=DQCheckStatus.PASS,
        )

    def _check_field_presence(self, records: list[bytes]) -> dict[str, float]:
        """Calculate field presence rates."""
        field_counts: Counter[str] = Counter()
        total_records = len(records)

        if total_records == 0:
            return {}

        for record in records:
            try:
                data = orjson.loads(record)
                if isinstance(data, dict):
                    for key in data:
                        field_counts[key] += 1
            except orjson.JSONDecodeError:
                continue

        return {
            field: round(count / total_records, 4)
            for field, count in field_counts.items()
        }

    def _check_encoding(self, records: list[bytes]) -> EncodingValidationResult:
        """Validate UTF-8 encoding."""
        encoding_errors = 0
        invalid_records: list[int] = []

        for idx, record in enumerate(records):
            try:
                record.decode("utf-8")
            except UnicodeDecodeError:
                encoding_errors += 1
                invalid_records.append(idx)

        status = DQCheckStatus.PASS if encoding_errors == 0 else DQCheckStatus.FAIL

        return EncodingValidationResult(
            encoding_errors=encoding_errors,
            invalid_utf8_records=tuple(invalid_records),
            status=status,
        )

    def _infer_type(self, value: Any) -> str:
        """Infer JSON type from Python value."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "unknown"

    def _result_to_dict(self, result: Any) -> dict[str, Any]:
        """Convert dataclass result to dict for serialization."""
        if hasattr(result, "__dataclass_fields__"):
            return {
                field: getattr(result, field)
                for field in result.__dataclass_fields__
                if not field.startswith("_")
            }
        return {"value": result}

    def _update_counts(
        self,
        status: DQCheckStatus,
        passed: int,
        failed: int,
        warnings: int,
    ) -> tuple[int, int, int]:
        """Update check counts based on status."""
        if status == DQCheckStatus.PASS:
            return passed + 1, failed, warnings
        elif status == DQCheckStatus.FAIL:
            return passed, failed + 1, warnings
        else:  # WARN
            return passed, failed, warnings + 1


__all__ = ["BronzeDQAnalyzer"]

================================================================================
File: gold_analyzer.py
Path: services\dq\gold_analyzer.py
================================================================================
"""Gold layer DQ analyzer.

Implements strict validation for Gold data marts:
- Record count with baseline comparison
- Completeness checks for required fields
- Business rules validation
- Referential integrity checks
- Statistical profiling with MA30 baseline
- Anomaly detection
- SCD (Slowly Changing Dimension) integrity

Follows RULES.md §3.1 DQ strategy for Gold layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import polars as pl
import pyarrow as pa

from bioetl.domain.ports import GoldDQConfigPort
from bioetl.domain.value_objects.dq_report import (
    AnomalyDetectionResult,
    AnomalyMetric,
    BusinessRuleResult,
    BusinessRulesResult,
    CompletenessResult,
    DataFreshnessResult,
    DQCheckStatus,
    DQReportStatus,
    DQReportSummary,
    ForeignKeyResult,
    GoldDQCheckType,
    GoldDQReport,
    MedallionLayer,
    RecordCountResult,
    ReferentialIntegrityResult,
    SCDIntegrityResult,
    StatisticalMetric,
    StatisticalProfileResult,
)


def _convert_value(value: Any) -> Any:
    """Convert a value to serializable format."""
    if hasattr(value, "value"):  # Enum
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return _result_to_dict(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_convert_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _convert_value(v) for k, v in value.items()}
    return value


def _result_to_dict(result: Any) -> dict[str, Any]:
    """Convert dataclass result to dict for serialization."""
    if hasattr(result, "__dataclass_fields__"):
        return {
            field: _convert_value(getattr(result, field))
            for field in result.__dataclass_fields__
            if not field.startswith("_")
        }
    return {"value": result}


def _update_counts(
    status: DQCheckStatus, passed: int, failed: int, warnings: int
) -> tuple[int, int, int]:
    """Update check counts based on status."""
    if status == DQCheckStatus.PASS:
        return passed + 1, failed, warnings
    if status == DQCheckStatus.FAIL:
        return passed, failed + 1, warnings
    return passed, failed, warnings + 1


class GoldDQAnalyzer:
    """Analyzer for Gold layer DQ checks.

    Performs strict validation on data marts for business-critical metrics.
    Implements GoldDQAnalyzerPort.
    """

    # Anomaly detection thresholds from RULES.md §3.4.1
    NULL_RATE_WARNING_MULTIPLIER = 2.0
    NULL_RATE_CRITICAL_MULTIPLIER = 5.0
    RECORD_COUNT_WARNING_THRESHOLD = 0.70
    RECORD_COUNT_CRITICAL_THRESHOLD = 0.50
    FRESHNESS_WARNING_HOURS = 24
    FRESHNESS_CRITICAL_HOURS = 72

    def _execute_checks(
        self,
        df: pl.DataFrame,
        enabled_checks: set[GoldDQCheckType],
        required_fields: list[str],
        completeness_threshold: float,
        business_rules: list[dict[str, Any]],
        reference_tables: dict[str, pl.DataFrame | pa.Table],
        baseline_stats: dict[str, Any] | None,
        scd_config: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], int, int, int]:
        """Execute all enabled DQ checks and collect results.

        Args:
            df: Polars DataFrame with Gold data.
            enabled_checks: Set of enabled check types.
            required_fields: List of required fields for completeness.
            completeness_threshold: Minimum completeness score threshold.
            business_rules: List of business rule definitions.
            reference_tables: Tables for referential integrity checks.
            baseline_stats: Historical baseline for anomaly detection.
            scd_config: SCD configuration if applicable.

        Returns:
            Tuple of (checks dict, passed count, failed count, warnings count).
        """
        checks: dict[str, Any] = {}
        passed, failed, warnings = 0, 0, 0

        if GoldDQCheckType.RECORD_COUNT in enabled_checks:
            record_count_result = self._check_record_count(df, baseline_stats)
            checks["record_count"] = _result_to_dict(record_count_result)
            passed, failed, warnings = _update_counts(
                record_count_result.status, passed, failed, warnings
            )

        if GoldDQCheckType.COMPLETENESS in enabled_checks:
            completeness_result = self._check_completeness(
                df, required_fields, completeness_threshold
            )
            checks["completeness"] = _result_to_dict(completeness_result)
            passed, failed, warnings = _update_counts(
                completeness_result.status, passed, failed, warnings
            )

        if GoldDQCheckType.BUSINESS_RULES in enabled_checks:
            business_rules_result = self._check_business_rules(df, business_rules)
            checks["business_rules"] = _result_to_dict(business_rules_result)
            passed, failed, warnings = _update_counts(
                business_rules_result.status, passed, failed, warnings
            )

        if GoldDQCheckType.REFERENTIAL_INTEGRITY in enabled_checks:
            ref_integrity_result = self._check_referential_integrity(
                df, reference_tables
            )
            checks["referential_integrity"] = _result_to_dict(ref_integrity_result)
            passed, failed, warnings = _update_counts(
                ref_integrity_result.status, passed, failed, warnings
            )

        if GoldDQCheckType.STATISTICAL_PROFILE in enabled_checks:
            stat_profile_result = self._check_statistical_profile(df, baseline_stats)
            checks["statistical_profile"] = _result_to_dict(stat_profile_result)
            passed, failed, warnings = _update_counts(
                stat_profile_result.status, passed, failed, warnings
            )

        if GoldDQCheckType.ANOMALY_DETECTION in enabled_checks:
            anomaly_result = self._check_anomaly_detection(df, baseline_stats)
            checks["anomaly_detection"] = _result_to_dict(anomaly_result)
            passed, failed, warnings = _update_counts(
                anomaly_result.status, passed, failed, warnings
            )

        if GoldDQCheckType.SCD_INTEGRITY in enabled_checks:
            scd_result = self._check_scd_integrity(df, scd_config)
            checks["scd_integrity"] = _result_to_dict(scd_result)
            passed, failed, warnings = _update_counts(
                scd_result.status, passed, failed, warnings
            )

        return checks, passed, failed, warnings

    def _build_summary(
        self,
        passed: int,
        failed: int,
        warnings: int,
    ) -> DQReportSummary:
        """Build DQ report summary with overall status.

        Args:
            passed: Number of passed checks.
            failed: Number of failed checks.
            warnings: Number of warning checks.

        Returns:
            DQReportSummary with overall status.
        """
        if failed > 0:
            overall_status = DQReportStatus.FAIL
        elif warnings > 0:
            overall_status = DQReportStatus.WARNING
        else:
            overall_status = DQReportStatus.PASS

        return DQReportSummary(
            total_checks=passed + failed + warnings,
            passed=passed,
            failed=failed,
            warnings=warnings,
            overall_status=overall_status,
        )

    def analyze(
        self,
        data: pl.DataFrame | pa.Table,
        *,
        run_id: str,
        pipeline: str,
        target_table: str,
        config: GoldDQConfigPort,
        timestamp: datetime,
        required_fields: list[str] | None = None,
        completeness_threshold: float = 0.90,
        business_rules: list[dict[str, Any]] | None = None,
        reference_tables: dict[str, pl.DataFrame | pa.Table] | None = None,
        baseline_stats: dict[str, Any] | None = None,
        scd_config: dict[str, Any] | None = None,
    ) -> GoldDQReport:
        """Analyze Gold data and generate DQ report.

        Args:
            data: Polars DataFrame or PyArrow Table with Gold data.
            run_id: Pipeline run identifier.
            pipeline: Pipeline name.
            target_table: Gold table path.
            config: DQ report configuration.
            timestamp: Report generation timestamp (UTC).
            required_fields: List of required fields for completeness.
            completeness_threshold: Minimum completeness score threshold.
            business_rules: List of business rule definitions.
            reference_tables: Tables for referential integrity checks.
            baseline_stats: Historical baseline for anomaly detection.
            scd_config: SCD configuration if applicable.

        Returns:
            GoldDQReport: Complete DQ report for Gold layer.
        """
        # Convert PyArrow to Polars for consistent processing
        if isinstance(data, pa.Table):
            df: pl.DataFrame = pl.from_arrow(data)  # type: ignore[assignment]
        else:
            df = data

        enabled_checks = set(config.get_checks_enums())

        # Execute all enabled checks
        checks, passed, failed, warnings = self._execute_checks(
            df=df,
            enabled_checks=enabled_checks,
            required_fields=required_fields or [],
            completeness_threshold=completeness_threshold,
            business_rules=business_rules or [],
            reference_tables=reference_tables or {},
            baseline_stats=baseline_stats,
            scd_config=scd_config,
        )

        # Data freshness check
        data_freshness = self._check_data_freshness(df, timestamp)

        # Build summary
        summary = self._build_summary(passed, failed, warnings)

        return GoldDQReport(
            layer=MedallionLayer.GOLD,
            timestamp=timestamp,
            run_id=run_id,
            pipeline=pipeline,
            target_table=target_table,
            checks=checks,
            data_freshness=data_freshness,
            summary=summary,
        )

    def _check_record_count(
        self, df: pl.DataFrame, baseline_stats: dict[str, Any] | None
    ) -> RecordCountResult:
        """Check record count against baseline."""
        current = len(df)
        baseline = (
            baseline_stats.get("record_count_ma30", current)
            if baseline_stats
            else current
        )
        delta = (current - baseline) / baseline if baseline > 0 else 0.0

        # Check for significant drop
        status = DQCheckStatus.PASS
        if delta < -0.5:  # >50% drop
            status = DQCheckStatus.FAIL
        elif delta < -0.3:  # >30% drop
            status = DQCheckStatus.WARN

        return RecordCountResult(
            value=current,
            status=status,
            delta_from_last_run=int(current - baseline) if baseline else None,
        )

    def _check_completeness(
        self,
        df: pl.DataFrame,
        required_fields: list[str],
        threshold: float,
    ) -> CompletenessResult:
        """Check completeness of required fields."""
        if not required_fields:
            return CompletenessResult(
                required_fields={},
                overall_completeness_score=1.0,
                minimum_threshold=threshold,
                status=DQCheckStatus.PASS,
            )

        field_rates = {}
        total_rate = 0.0
        count = 0

        for field in required_fields:
            if field in df.columns:
                null_count = df[field].null_count()
                rate = 1.0 - (null_count / len(df)) if len(df) > 0 else 0.0
                field_rates[field] = round(rate, 4)
                total_rate += rate
                count += 1
            else:
                field_rates[field] = 0.0

        overall_score = total_rate / count if count > 0 else 0.0

        status = (
            DQCheckStatus.PASS if overall_score >= threshold else DQCheckStatus.FAIL
        )

        return CompletenessResult(
            required_fields=field_rates,
            overall_completeness_score=round(overall_score, 4),
            minimum_threshold=threshold,
            status=status,
        )

    def _check_not_null_rule(
        self, df: pl.DataFrame, column: str
    ) -> tuple[bool, int | None]:
        """Check not_null rule for a column."""
        violations = df[column].null_count()
        return violations == 0, violations

    def _check_range_rule(
        self,
        df: pl.DataFrame,
        column: str,
        min_val: Any | None,
        max_val: Any | None,
    ) -> tuple[bool, int]:
        """Check range rule for a column."""
        violations = 0
        col_data = df[column].drop_nulls()
        if min_val is not None:
            violations += (col_data < min_val).sum()
        if max_val is not None:
            violations += (col_data > max_val).sum()
        return violations == 0, violations

    def _check_in_list_rule(
        self, df: pl.DataFrame, column: str, allowed: list[Any]
    ) -> tuple[bool, int | None]:
        """Check in_list rule for a column."""
        if not allowed:
            return True, 0
        violations = int((~df[column].is_in(allowed)).sum())
        return violations == 0, violations

    def _check_regex_rule(
        self, df: pl.DataFrame, column: str, pattern: str
    ) -> tuple[bool, int | None]:
        """Check regex rule for a column."""
        if not pattern:
            return True, 0
        violations = int((~df[column].str.contains(pattern, literal=False)).sum())
        return violations == 0, violations

    def _evaluate_single_rule(
        self, df: pl.DataFrame, rule: dict[str, Any]
    ) -> tuple[bool, int | None]:
        """Evaluate a single business rule."""
        column = rule.get("column")
        condition = rule.get("condition")

        if not column or column not in df.columns:
            return True, 0

        if condition == "not_null":
            return self._check_not_null_rule(df, column)
        if condition == "range":
            return self._check_range_rule(df, column, rule.get("min"), rule.get("max"))
        if condition == "in_list":
            return self._check_in_list_rule(df, column, rule.get("values", []))
        if condition == "regex":
            return self._check_regex_rule(df, column, rule.get("pattern", ""))
        return True, 0

    def _check_business_rules(
        self, df: pl.DataFrame, rules: list[dict[str, Any]]
    ) -> BusinessRulesResult:
        """Validate business rules."""
        if not rules:
            return BusinessRulesResult(
                rules_evaluated=0,
                rules_passed=0,
                rules_failed=0,
                rules=(),
                status=DQCheckStatus.PASS,
            )

        results = []
        rules_passed = 0
        rules_failed = 0

        for rule in rules:
            try:
                passed, violations = self._evaluate_single_rule(df, rule)
            except Exception:
                passed, violations = False, None

            if passed:
                rules_passed += 1
            else:
                rules_failed += 1

            results.append(
                BusinessRuleResult(
                    rule_id=rule.get("rule_id", ""),
                    name=rule.get("name", ""),
                    description=rule.get("description", ""),
                    passed=passed,
                    violations=violations,
                )
            )

        status = DQCheckStatus.PASS if rules_failed == 0 else DQCheckStatus.FAIL

        return BusinessRulesResult(
            rules_evaluated=len(rules),
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            rules=tuple(results),
            status=status,
        )

    def _check_referential_integrity(
        self, df: pl.DataFrame, reference_tables: dict[str, pl.DataFrame | pa.Table]
    ) -> ReferentialIntegrityResult:
        """Check foreign key references."""
        if not reference_tables:
            return ReferentialIntegrityResult(
                foreign_keys={},
                status=DQCheckStatus.PASS,
            )

        fk_results: dict[str, ForeignKeyResult] = {}
        has_failures = False
        has_warnings = False

        for ref_key, ref_table in reference_tables.items():
            # Parse reference: "local_col -> ref_table.ref_col"
            parts = ref_key.split("->")
            if len(parts) != 2:
                continue

            local_col = parts[0].strip()
            ref_parts = parts[1].strip().split(".")
            if len(ref_parts) != 2:
                continue

            ref_col = ref_parts[1]

            if local_col not in df.columns:
                continue

            # Convert reference table to Polars if needed
            if isinstance(ref_table, pa.Table):
                ref_df: pl.DataFrame = pl.from_arrow(ref_table)  # type: ignore[assignment]
            else:
                ref_df = ref_table

            if ref_col not in ref_df.columns:
                continue

            # Count references
            local_values = df[local_col].drop_nulls()
            ref_values = ref_df[ref_col].unique()

            total_refs = len(local_values)
            valid_refs = int(local_values.is_in(ref_values).sum())
            orphans = total_refs - valid_refs

            if orphans > 0:
                if orphans / total_refs > 0.01:  # >1% orphans
                    status = DQCheckStatus.FAIL
                    has_failures = True
                else:
                    status = DQCheckStatus.WARN
                    has_warnings = True
            else:
                status = DQCheckStatus.PASS

            fk_results[ref_key] = ForeignKeyResult(
                reference=ref_key,
                total_references=total_refs,
                valid_references=valid_refs,
                orphan_records=orphans,
                status=status,
            )

        overall_status = DQCheckStatus.PASS
        if has_failures:
            overall_status = DQCheckStatus.FAIL
        elif has_warnings:
            overall_status = DQCheckStatus.WARN

        return ReferentialIntegrityResult(
            foreign_keys=fk_results,
            status=overall_status,
        )

    def _check_statistical_profile(
        self, df: pl.DataFrame, baseline_stats: dict[str, Any] | None
    ) -> StatisticalProfileResult:
        """Compare statistics against baseline (MA30)."""
        if not baseline_stats:
            return StatisticalProfileResult(
                baseline_period_days=30,
                metrics={},
                status=DQCheckStatus.PASS,
            )

        metrics: dict[str, StatisticalMetric] = {}

        # Check null rate
        if "null_rate_ma30" in baseline_stats:
            total_nulls = sum(df[col].null_count() for col in df.columns)
            total_cells = len(df) * len(df.columns)
            current_null_rate = total_nulls / total_cells if total_cells > 0 else 0.0
            baseline_null_rate = baseline_stats["null_rate_ma30"]

            ratio = (
                current_null_rate / baseline_null_rate
                if baseline_null_rate > 0
                else 1.0
            )

            if ratio > self.NULL_RATE_CRITICAL_MULTIPLIER:
                status = DQCheckStatus.FAIL
            elif ratio > self.NULL_RATE_WARNING_MULTIPLIER:
                status = DQCheckStatus.WARN
            else:
                status = DQCheckStatus.PASS

            metrics["null_rate_avg"] = StatisticalMetric(
                current=round(current_null_rate, 4),
                baseline=round(baseline_null_rate, 4),
                ratio=round(ratio, 4),
                threshold_warning=self.NULL_RATE_WARNING_MULTIPLIER,
                threshold_critical=self.NULL_RATE_CRITICAL_MULTIPLIER,
                status=status,
            )

        # Check record count
        if "record_count_ma30" in baseline_stats:
            current_count = len(df)
            baseline_count = baseline_stats["record_count_ma30"]

            ratio = current_count / baseline_count if baseline_count > 0 else 1.0

            if ratio < self.RECORD_COUNT_CRITICAL_THRESHOLD:
                status = DQCheckStatus.FAIL
            elif ratio < self.RECORD_COUNT_WARNING_THRESHOLD:
                status = DQCheckStatus.WARN
            else:
                status = DQCheckStatus.PASS

            metrics["record_count_daily"] = StatisticalMetric(
                current=float(current_count),
                baseline=float(baseline_count),
                ratio=round(ratio, 4),
                threshold_warning=self.RECORD_COUNT_WARNING_THRESHOLD,
                threshold_critical=self.RECORD_COUNT_CRITICAL_THRESHOLD,
                status=status,
            )

        overall_status = DQCheckStatus.PASS
        for metric in metrics.values():
            if metric.status == DQCheckStatus.FAIL:
                overall_status = DQCheckStatus.FAIL
                break
            elif metric.status == DQCheckStatus.WARN:
                overall_status = DQCheckStatus.WARN

        return StatisticalProfileResult(
            baseline_period_days=30,
            metrics=metrics,
            status=overall_status,
        )

    def _check_anomaly_detection(
        self, df: pl.DataFrame, baseline_stats: dict[str, Any] | None
    ) -> AnomalyDetectionResult:
        """Detect anomalies using baseline comparison."""
        cold_start_days = 30
        current_day = baseline_stats.get("days_since_start", 0) if baseline_stats else 0
        cold_start_mode = current_day < cold_start_days

        if cold_start_mode or not baseline_stats:
            return AnomalyDetectionResult(
                cold_start_days=cold_start_days,
                current_day=current_day,
                cold_start_mode=True,
                anomalies_detected=(),
                metrics_monitored=(),
                status=DQCheckStatus.PASS,
            )

        anomalies = []
        metrics_monitored = []

        # Check null rate anomaly
        total_nulls = sum(df[col].null_count() for col in df.columns)
        total_cells = len(df) * len(df.columns)
        current_null_rate = total_nulls / total_cells if total_cells > 0 else 0.0
        baseline_null_rate = baseline_stats.get("null_rate_ma30", current_null_rate)

        null_zscore = (
            (current_null_rate - baseline_null_rate) / baseline_null_rate
            if baseline_null_rate > 0
            else 0.0
        )

        if abs(null_zscore) > 3:
            anomalies.append("null_rate")
            null_status = "anomaly"
        else:
            null_status = "normal"

        metrics_monitored.append(
            AnomalyMetric(
                metric="null_rate",
                current_value=round(current_null_rate, 4),
                baseline_value=round(baseline_null_rate, 4),
                zscore=round(null_zscore, 2),
                status=null_status,
            )
        )

        # Check record count anomaly
        current_count = float(len(df))
        baseline_count = baseline_stats.get("record_count_ma30", current_count)
        count_zscore = (
            (current_count - baseline_count) / baseline_count
            if baseline_count > 0
            else 0.0
        )

        if abs(count_zscore) > 3:
            anomalies.append("record_count")
            count_status = "anomaly"
        else:
            count_status = "normal"

        metrics_monitored.append(
            AnomalyMetric(
                metric="record_count",
                current_value=current_count,
                baseline_value=baseline_count,
                zscore=round(count_zscore, 2),
                status=count_status,
            )
        )

        status = DQCheckStatus.WARN if anomalies else DQCheckStatus.PASS

        return AnomalyDetectionResult(
            cold_start_days=cold_start_days,
            current_day=current_day,
            cold_start_mode=False,
            anomalies_detected=tuple(anomalies),
            metrics_monitored=tuple(metrics_monitored),
            status=status,
        )

    def _check_scd_integrity(
        self, df: pl.DataFrame, scd_config: dict[str, Any] | None
    ) -> SCDIntegrityResult:
        """Check SCD (Slowly Changing Dimension) integrity."""
        if not scd_config:
            return SCDIntegrityResult(
                scd_type=2,
                total_entities=len(df),
                entities_with_history=0,
                avg_versions_per_entity=1.0,
                version_gaps=0,
                temporal_conflicts=0,
                overlapping_validity_periods=0,
                status=DQCheckStatus.PASS,
            )

        scd_type = scd_config.get("type", 2)
        entity_key = scd_config.get("entity_key")
        valid_from = scd_config.get("valid_from_col", "_valid_from")
        valid_to = scd_config.get("valid_to_col", "_valid_to")

        if not entity_key or entity_key not in df.columns:
            return SCDIntegrityResult(
                scd_type=scd_type,
                total_entities=len(df),
                entities_with_history=0,
                avg_versions_per_entity=1.0,
                version_gaps=0,
                temporal_conflicts=0,
                overlapping_validity_periods=0,
                status=DQCheckStatus.PASS,
            )

        # Count unique entities
        unique_entities = df[entity_key].n_unique()
        total_records = len(df)

        # Entities with multiple versions
        version_counts = df.group_by(entity_key).agg(pl.count().alias("versions"))
        entities_with_history = int((version_counts["versions"] > 1).sum())
        avg_versions = total_records / unique_entities if unique_entities > 0 else 1.0

        # Check temporal integrity if columns exist
        version_gaps = 0
        temporal_conflicts = 0
        overlapping = 0

        if valid_from in df.columns and valid_to in df.columns:
            # Check for overlapping validity periods
            # This is a simplified check
            try:
                for entity in df[entity_key].unique().to_list()[:100]:  # Sample
                    entity_records = df.filter(pl.col(entity_key) == entity).sort(
                        valid_from
                    )
                    if len(entity_records) > 1:
                        # Check for overlaps
                        for i in range(len(entity_records) - 1):
                            current_to = entity_records[valid_to][i]
                            next_from = entity_records[valid_from][i + 1]
                            if (
                                current_to is not None
                                and next_from is not None
                                and current_to > next_from
                            ):
                                overlapping += 1
            except Exception:
                pass

        status = DQCheckStatus.PASS if overlapping == 0 else DQCheckStatus.WARN

        return SCDIntegrityResult(
            scd_type=scd_type,
            total_entities=unique_entities,
            entities_with_history=entities_with_history,
            avg_versions_per_entity=round(avg_versions, 2),
            version_gaps=version_gaps,
            temporal_conflicts=temporal_conflicts,
            overlapping_validity_periods=overlapping,
            status=status,
        )

    def _check_data_freshness(
        self, df: pl.DataFrame, current_time: datetime
    ) -> DataFreshnessResult:
        """Check data freshness based on timestamp columns."""
        # Try to find timestamp column
        timestamp_cols = ["_updated_at", "updated_at", "_ingestion_ts", "created_at"]
        max_ts = None

        for col in timestamp_cols:
            if col in df.columns:
                try:
                    col_max = df[col].max()
                    if col_max is not None:
                        if isinstance(col_max, datetime):
                            max_ts = col_max
                        break
                except Exception:
                    pass

        if max_ts is None:
            return DataFreshnessResult(
                max_updated_at=None,
                freshness_lag_seconds=0.0,
                freshness_lag_hours=0.0,
                status=DQCheckStatus.PASS,
            )

        # Calculate lag
        lag_seconds = (current_time - max_ts).total_seconds()
        lag_hours = lag_seconds / 3600

        if lag_hours > self.FRESHNESS_CRITICAL_HOURS:
            status = DQCheckStatus.FAIL
        elif lag_hours > self.FRESHNESS_WARNING_HOURS:
            status = DQCheckStatus.WARN
        else:
            status = DQCheckStatus.PASS

        return DataFreshnessResult(
            max_updated_at=max_ts,
            freshness_lag_seconds=round(lag_seconds, 2),
            freshness_lag_hours=round(lag_hours, 2),
            status=status,
        )


__all__ = ["GoldDQAnalyzer"]

================================================================================
File: silver_analyzer.py
Path: services\dq\silver_analyzer.py
================================================================================
"""Silver layer DQ analyzer.

Implements data quality monitoring for normalized Silver data:
- Record count with input/output comparison
- Null rate analysis per column
- Uniqueness and cardinality checks
- Type conformance validation
- Value distribution statistics
- Schema drift detection
- Deduplication statistics
- Content hash integrity

Follows RULES.md §3.1 DQ strategy for Silver layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import polars as pl
import pyarrow as pa

from bioetl.domain.ports import SilverDQConfigPort
from bioetl.domain.value_objects.dq_report import (
    CategoricalDistribution,
    ContentHashIntegrityResult,
    DeduplicationStatsResult,
    DQCheckStatus,
    DQReportStatus,
    DQReportSummary,
    DQThresholds,
    DriftLevel,
    MedallionLayer,
    NullRateResult,
    NumericDistribution,
    RecordCountResult,
    SchemaDriftResult,
    SilverDQCheckType,
    SilverDQReport,
    TypeConformanceResult,
    UniquenessResult,
    ValueDistributionResult,
)


class SilverDQAnalyzer:
    """Analyzer for Silver layer DQ checks.

    Performs comprehensive data quality monitoring on normalized data.
    Implements SilverDQAnalyzerPort.
    """

    def _execute_checks(
        self,
        df: pl.DataFrame,
        enabled_checks: set[SilverDQCheckType],
        primary_keys: list[str],
        input_record_count: int | None,
        quarantined_count: int,
        previous_schema: dict[str, str] | None,
    ) -> tuple[dict[str, Any], int, int, int]:
        """Execute all enabled DQ checks and collect results.

        Args:
            df: Polars DataFrame with Silver data.
            enabled_checks: Set of enabled check types.
            primary_keys: List of primary key columns.
            input_record_count: Original record count before transforms.
            quarantined_count: Number of quarantined records.
            previous_schema: Previous schema for drift detection.

        Returns:
            Tuple of (checks dict, passed count, failed count, warnings count).
        """
        checks: dict[str, Any] = {}
        passed, failed, warnings = 0, 0, 0

        if SilverDQCheckType.RECORD_COUNT in enabled_checks:
            record_count_result = self._check_record_count(
                df, input_record_count, quarantined_count
            )
            checks["record_count"] = self._result_to_dict(record_count_result)
            passed, failed, warnings = self._update_counts(
                record_count_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.NULL_RATE in enabled_checks:
            null_results, overall_rate = self._check_null_rates(df)
            checks["null_rate"] = {
                "columns": {
                    r.column_name: self._result_to_dict(r) for r in null_results
                },
                "overall_null_rate": overall_rate,
                "status": DQCheckStatus.PASS.value,
            }
            passed += 1

        if SilverDQCheckType.UNIQUENESS in enabled_checks:
            uniqueness_result = self._check_uniqueness(df, primary_keys)
            checks["uniqueness"] = self._result_to_dict(uniqueness_result)
            passed, failed, warnings = self._update_counts(
                uniqueness_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.TYPE_CONFORMANCE in enabled_checks:
            conformance_result = self._check_type_conformance(df)
            checks["type_conformance"] = self._result_to_dict(conformance_result)
            passed, failed, warnings = self._update_counts(
                conformance_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.VALUE_DISTRIBUTION in enabled_checks:
            distribution_result = self._check_value_distribution(df)
            checks["value_distribution"] = self._distribution_to_dict(
                distribution_result
            )
            passed += 1

        if SilverDQCheckType.SCHEMA_DRIFT in enabled_checks:
            drift_result = self._check_schema_drift(df, previous_schema)
            checks["schema_drift"] = self._result_to_dict(drift_result)
            passed, failed, warnings = self._update_counts(
                drift_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.DEDUPLICATION_STATS in enabled_checks:
            dedup_result = self._check_deduplication(
                df, primary_keys, input_record_count or len(df)
            )
            checks["deduplication_stats"] = self._result_to_dict(dedup_result)
            passed, failed, warnings = self._update_counts(
                dedup_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.CONTENT_HASH_INTEGRITY in enabled_checks:
            hash_result = self._check_content_hash_integrity(df)
            checks["content_hash_integrity"] = self._result_to_dict(hash_result)
            passed, failed, warnings = self._update_counts(
                hash_result.status, passed, failed, warnings
            )

        return checks, passed, failed, warnings

    def _calculate_thresholds(
        self,
        df_len: int,
        input_record_count: int | None,
        quarantined_count: int,
        soft_fail_threshold: float,
        hard_fail_threshold: float,
    ) -> DQThresholds:
        """Calculate DQ thresholds and error rate status.

        Args:
            df_len: Length of the DataFrame.
            input_record_count: Original record count before transforms.
            quarantined_count: Number of quarantined records.
            soft_fail_threshold: Warning threshold for error rate.
            hard_fail_threshold: Failure threshold for error rate.

        Returns:
            DQThresholds with calculated error rate and status.
        """
        total_input = input_record_count or df_len + quarantined_count
        error_rate = quarantined_count / total_input if total_input > 0 else 0.0

        if error_rate >= hard_fail_threshold:
            threshold_status = DQCheckStatus.FAIL
        elif error_rate >= soft_fail_threshold:
            threshold_status = DQCheckStatus.WARN
        else:
            threshold_status = DQCheckStatus.PASS

        return DQThresholds(
            soft_fail_threshold=soft_fail_threshold,
            hard_fail_threshold=hard_fail_threshold,
            current_error_rate=round(error_rate, 4),
            threshold_status=threshold_status,
        )

    def _build_summary(
        self,
        passed: int,
        failed: int,
        warnings: int,
        threshold_status: DQCheckStatus,
    ) -> DQReportSummary:
        """Build DQ report summary with overall status.

        Args:
            passed: Number of passed checks.
            failed: Number of failed checks.
            warnings: Number of warning checks.
            threshold_status: Status from threshold calculation.

        Returns:
            DQReportSummary with overall status.
        """
        if failed > 0 or threshold_status == DQCheckStatus.FAIL:
            overall_status = DQReportStatus.FAIL
        elif warnings > 0 or threshold_status == DQCheckStatus.WARN:
            overall_status = DQReportStatus.WARNING
        else:
            overall_status = DQReportStatus.PASS

        return DQReportSummary(
            total_checks=passed + failed + warnings,
            passed=passed,
            failed=failed,
            warnings=warnings,
            overall_status=overall_status,
        )

    def analyze(
        self,
        data: pl.DataFrame | pa.Table,
        *,
        run_id: str,
        pipeline: str,
        target_table: str,
        source_batch_ids: list[str],
        config: SilverDQConfigPort,
        timestamp: datetime,
        primary_keys: list[str],
        soft_fail_threshold: float = 0.05,
        hard_fail_threshold: float = 0.20,
        input_record_count: int | None = None,
        quarantined_count: int = 0,
        previous_schema: dict[str, str] | None = None,
    ) -> SilverDQReport:
        """Analyze Silver data and generate DQ report.

        Args:
            data: Polars DataFrame or PyArrow Table with Silver data.
            run_id: Pipeline run identifier.
            pipeline: Pipeline name.
            target_table: Silver table path.
            source_batch_ids: List of Bronze batch IDs processed.
            config: DQ report configuration.
            timestamp: Report generation timestamp (UTC).
            primary_keys: List of primary key columns.
            soft_fail_threshold: Warning threshold for error rate.
            hard_fail_threshold: Failure threshold for error rate.
            input_record_count: Original record count before transforms.
            quarantined_count: Number of quarantined records.
            previous_schema: Previous schema for drift detection.

        Returns:
            SilverDQReport: Complete DQ report for Silver layer.
        """
        # Convert PyArrow to Polars for consistent processing
        if isinstance(data, pa.Table):
            df: pl.DataFrame = pl.from_arrow(data)  # type: ignore[assignment]
        else:
            df = data

        enabled_checks = set(config.get_checks_enums())

        # Execute all enabled checks
        checks, passed, failed, warnings = self._execute_checks(
            df=df,
            enabled_checks=enabled_checks,
            primary_keys=primary_keys,
            input_record_count=input_record_count,
            quarantined_count=quarantined_count,
            previous_schema=previous_schema,
        )

        # Calculate thresholds
        thresholds = self._calculate_thresholds(
            df_len=len(df),
            input_record_count=input_record_count,
            quarantined_count=quarantined_count,
            soft_fail_threshold=soft_fail_threshold,
            hard_fail_threshold=hard_fail_threshold,
        )

        # Build summary
        summary = self._build_summary(
            passed=passed,
            failed=failed,
            warnings=warnings,
            threshold_status=thresholds.threshold_status,
        )

        return SilverDQReport(
            layer=MedallionLayer.SILVER,
            timestamp=timestamp,
            run_id=run_id,
            pipeline=pipeline,
            source_batch_ids=tuple(source_batch_ids),
            target_table=target_table,
            checks=checks,
            thresholds=thresholds,
            summary=summary,
        )

    def _check_record_count(
        self,
        df: pl.DataFrame,
        input_count: int | None,
        quarantined_count: int,
    ) -> RecordCountResult:
        """Check record count statistics."""
        output_count = len(df)
        input_records = input_count or (output_count + quarantined_count)
        quarantine_rate = (
            quarantined_count / input_records if input_records > 0 else 0.0
        )

        # Warn if significant data loss
        status = DQCheckStatus.PASS
        if quarantine_rate > 0.1:  # >10% quarantined
            status = DQCheckStatus.WARN

        return RecordCountResult(
            value=output_count,
            status=status,
            input_records=input_records,
            output_records=output_count,
            quarantined_records=quarantined_count,
            quarantine_rate=round(quarantine_rate, 4),
        )

    def _check_null_rates(self, df: pl.DataFrame) -> tuple[list[NullRateResult], float]:
        """Calculate null rates per column."""
        results = []
        total_nulls = 0
        total_cells = 0

        for col in df.columns:
            null_count = df[col].null_count()
            total = len(df)
            null_rate = null_count / total if total > 0 else 0.0

            total_nulls += null_count
            total_cells += total

            # Status based on null rate
            status = DQCheckStatus.WARN if null_rate > 0.5 else DQCheckStatus.PASS

            results.append(
                NullRateResult(
                    column_name=col,
                    null_rate=round(null_rate, 4),
                    status=status,
                )
            )

        overall_null_rate = total_nulls / total_cells if total_cells > 0 else 0.0
        return results, round(overall_null_rate, 4)

    def _check_uniqueness(
        self, df: pl.DataFrame, primary_keys: list[str]
    ) -> UniquenessResult:
        """Check uniqueness of primary keys."""
        if not primary_keys:
            return UniquenessResult(
                primary_key="",
                unique_count=len(df),
                total_count=len(df),
                duplicate_rate=0.0,
                status=DQCheckStatus.PASS,
            )

        # Check which primary keys exist in dataframe
        existing_keys = [k for k in primary_keys if k in df.columns]
        if not existing_keys:
            return UniquenessResult(
                primary_key=",".join(primary_keys),
                unique_count=len(df),
                total_count=len(df),
                duplicate_rate=0.0,
                status=DQCheckStatus.WARN,
                column_stats={"_note": {"message": "Primary key columns not found"}},
            )

        pk_name = ",".join(existing_keys)
        unique_count = df.select(existing_keys).unique().height
        total_count = len(df)
        duplicate_count = total_count - unique_count
        duplicate_rate = duplicate_count / total_count if total_count > 0 else 0.0

        # Calculate column cardinality
        column_stats = {}
        for col in df.columns[:10]:  # Limit to first 10 columns
            try:
                cardinality = df[col].n_unique()
                column_stats[col] = {
                    "cardinality": cardinality,
                    "uniqueness_ratio": round(cardinality / len(df), 4)
                    if len(df) > 0
                    else 0.0,
                }
            except Exception:
                pass

        status = DQCheckStatus.PASS if duplicate_rate == 0 else DQCheckStatus.WARN

        return UniquenessResult(
            primary_key=pk_name,
            unique_count=unique_count,
            total_count=total_count,
            duplicate_rate=round(duplicate_rate, 4),
            column_stats=column_stats,
            status=status,
        )

    def _check_type_conformance(self, df: pl.DataFrame) -> TypeConformanceResult:
        """Check type conformance against expected schema."""
        # For now, just validate that columns have consistent types
        errors = []
        type_coercions: dict[str, dict[str, Any]] = {}

        for col in df.columns:
            dtype = df[col].dtype
            # Check for object/mixed types that indicate inconsistency
            if dtype == pl.Object:
                errors.append(f"Column {col} has mixed types (Object)")

        status = DQCheckStatus.PASS if not errors else DQCheckStatus.WARN

        return TypeConformanceResult(
            schema_version=None,
            pandera_passed=len(errors) == 0,
            errors=tuple(errors),
            type_coercions=type_coercions,
            status=status,
        )

    def _check_value_distribution(self, df: pl.DataFrame) -> ValueDistributionResult:
        """Calculate value distributions for columns."""
        numeric_cols: dict[str, NumericDistribution] = {}
        categorical_cols: dict[str, CategoricalDistribution] = {}

        for col in df.columns[:20]:  # Limit to first 20 columns
            dtype = df[col].dtype

            if dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.Int16, pl.Int8):
                try:
                    stats = df[col].drop_nulls()
                    if len(stats) > 0:
                        min_val = stats.min()
                        max_val = stats.max()
                        mean_val = stats.mean()
                        std_val = stats.std()
                        median_val = stats.median()
                        # Type narrowing: values are numeric due to dtype check above
                        numeric_cols[col] = NumericDistribution(
                            min=float(min_val) if min_val is not None else None,  # type: ignore[arg-type]
                            max=float(max_val) if max_val is not None else None,  # type: ignore[arg-type]
                            mean=float(mean_val) if mean_val is not None else None,  # type: ignore[arg-type]
                            std=float(std_val) if std_val is not None else None,  # type: ignore[arg-type]
                            median=float(median_val)  # type: ignore[arg-type]
                            if median_val is not None
                            else None,
                        )
                except Exception:
                    pass

            elif dtype in (pl.Utf8, pl.Categorical):
                try:
                    value_counts = df[col].value_counts().head(5)
                    cardinality = df[col].n_unique()
                    top_values = []
                    for row in value_counts.iter_rows(named=True):
                        val = row.get(col) or row.get("value")
                        count = row.get("count") or row.get("counts", 0)
                        top_values.append(
                            {
                                "value": str(val) if val is not None else None,
                                "count": count,
                                "pct": round(count / len(df), 4) if len(df) > 0 else 0,
                            }
                        )
                    categorical_cols[col] = CategoricalDistribution(
                        top_values=tuple(top_values),
                        cardinality=cardinality,
                    )
                except Exception:
                    pass

        return ValueDistributionResult(
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            status=DQCheckStatus.PASS,
        )

    def _check_schema_drift(
        self, df: pl.DataFrame, previous_schema: dict[str, str] | None
    ) -> SchemaDriftResult:
        """Detect schema drift from previous run."""
        current_schema = {col: str(df[col].dtype) for col in df.columns}

        if previous_schema is None:
            return SchemaDriftResult(
                drift_level=DriftLevel.INFO,
                status=DQCheckStatus.PASS,
            )

        new_fields = [f for f in current_schema if f not in previous_schema]
        missing_fields = [f for f in previous_schema if f not in current_schema]
        type_changes = []

        for field in current_schema:
            if (
                field in previous_schema
                and current_schema[field] != previous_schema[field]
            ):
                type_changes.append(
                    {
                        "field": field,
                        "from": previous_schema[field],
                        "to": current_schema[field],
                    }
                )

        # Determine drift level
        if missing_fields or type_changes:
            drift_level = DriftLevel.CRITICAL
            status = DQCheckStatus.WARN
        elif new_fields:
            drift_level = DriftLevel.INFO
            status = DQCheckStatus.PASS
        else:
            drift_level = DriftLevel.INFO
            status = DQCheckStatus.PASS

        return SchemaDriftResult(
            drift_level=drift_level,
            new_fields=tuple(new_fields),
            missing_fields=tuple(missing_fields),
            type_changes=tuple(type_changes),
            status=status,
        )

    def _check_deduplication(
        self,
        df: pl.DataFrame,
        primary_keys: list[str],
        input_count: int,
    ) -> DeduplicationStatsResult:
        """Calculate deduplication statistics."""
        output_count = len(df)
        dedupe_count = input_count - output_count

        # Check content hash duplicates if column exists
        content_hash_dupes = 0
        if "_content_hash" in df.columns:
            unique_hashes = df["_content_hash"].n_unique()
            content_hash_dupes = output_count - unique_hashes

        return DeduplicationStatsResult(
            input_before_dedupe=input_count,
            duplicates_by_content_hash=content_hash_dupes,
            duplicates_by_business_key=dedupe_count - content_hash_dupes,
            output_after_dedupe=output_count,
            status=DQCheckStatus.PASS,
        )

    def _check_content_hash_integrity(
        self, df: pl.DataFrame
    ) -> ContentHashIntegrityResult:
        """Check content hash integrity."""
        if "_content_hash" not in df.columns:
            return ContentHashIntegrityResult(
                records_checked=0,
                hash_collisions=0,
                rehash_mismatches=0,
                status=DQCheckStatus.PASS,
            )

        records_checked = len(df)

        # Check for hash collisions (same hash, different content)
        hash_counts = df["_content_hash"].value_counts()
        duplicates = hash_counts.filter(pl.col("count") > 1)
        hash_collisions = len(duplicates)

        status = DQCheckStatus.PASS if hash_collisions == 0 else DQCheckStatus.WARN

        return ContentHashIntegrityResult(
            records_checked=records_checked,
            hash_collisions=hash_collisions,
            rehash_mismatches=0,  # Would need to recalculate hashes to check
            status=status,
        )

    def _result_to_dict(self, result: Any) -> dict[str, Any]:
        """Convert dataclass result to dict for serialization."""
        if hasattr(result, "__dataclass_fields__"):
            output = {}
            for field in result.__dataclass_fields__:
                if field.startswith("_"):
                    continue
                value = getattr(result, field)
                if hasattr(value, "value"):  # Enum
                    output[field] = value.value
                elif hasattr(value, "__dataclass_fields__"):
                    output[field] = self._result_to_dict(value)
                else:
                    output[field] = value
            return output
        return {"value": result}

    def _distribution_to_dict(self, result: ValueDistributionResult) -> dict[str, Any]:
        """Convert distribution result to dict."""
        output: dict[str, Any] = {
            "numeric_columns": {},
            "categorical_columns": {},
            "status": result.status.value,
        }

        for col, numeric_dist in result.numeric_columns.items():
            output["numeric_columns"][col] = self._result_to_dict(numeric_dist)

        for col, categorical_dist in result.categorical_columns.items():
            output["categorical_columns"][col] = {
                "top_values": list(categorical_dist.top_values),
                "cardinality": categorical_dist.cardinality,
            }

        return output

    def _update_counts(
        self,
        status: DQCheckStatus,
        passed: int,
        failed: int,
        warnings: int,
    ) -> tuple[int, int, int]:
        """Update check counts based on status."""
        if status == DQCheckStatus.PASS:
            return passed + 1, failed, warnings
        elif status == DQCheckStatus.FAIL:
            return passed, failed + 1, warnings
        else:  # WARN
            return passed, failed, warnings + 1


__all__ = ["SilverDQAnalyzer"]

================================================================================
File: dq_metrics_calculator.py
Path: services\dq_metrics_calculator.py
================================================================================
"""Re-export DQMetricsCalculator from domain layer.

This module re-exports DQMetricsCalculator and DQMetricsInput from the domain
layer for backward compatibility. The actual implementation has been moved to
bioetl.domain.services.dq_metrics_calculator to fix architecture violations
(infrastructure layer cannot import from application layer).

New code should import directly from bioetl.domain.services.
"""

from bioetl.domain.services.dq_metrics_calculator import (
    DQMetricsCalculator,
    DQMetricsInput,
)

__all__ = ["DQMetricsCalculator", "DQMetricsInput"]

================================================================================
File: dq_report_service.py
Path: services\dq_report_service.py
================================================================================
"""DQ Report Service for orchestrating DQ report generation.

Application Service that handles DQ report generation across all Medallion layers.
Generates Bronze, Silver, and Gold DQ reports when enabled in configuration.

This service is called during the post-run phase and generates detailed
DQ analysis reports separate from the threshold-based DQ checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        BronzeDQAnalyzerPort,
        BronzeDQConfigPort,
        DQReportWriterPort,
        GoldDQAnalyzerPort,
        GoldDQConfigPort,
        LoggerPort,
        SilverDQAnalyzerPort,
        SilverDQConfigPort,
    )


@dataclass(frozen=True, slots=True)
class DQReportResult:
    """Result of DQ report generation for all layers.

    Attributes:
        bronze_report_path: Path to Bronze DQ report (if generated).
        silver_report_path: Path to Silver DQ report (if generated).
        gold_report_path: Path to Gold DQ report (if generated).
        bronze_enabled: Whether Bronze DQ report was enabled.
        silver_enabled: Whether Silver DQ report was enabled.
        gold_enabled: Whether Gold DQ report was enabled.
    """

    bronze_report_path: Path | None = None
    silver_report_path: Path | None = None
    gold_report_path: Path | None = None
    bronze_enabled: bool = False
    silver_enabled: bool = False
    gold_enabled: bool = False

    @property
    def any_generated(self) -> bool:
        """Check if any report was generated."""
        return any(
            [
                self.bronze_report_path is not None,
                self.silver_report_path is not None,
                self.gold_report_path is not None,
            ]
        )

    @property
    def reports_count(self) -> int:
        """Count of generated reports."""
        return sum(
            [
                self.bronze_report_path is not None,
                self.silver_report_path is not None,
                self.gold_report_path is not None,
            ]
        )


@dataclass(frozen=True, slots=True)
class DQReportContext:
    """Context for DQ report generation.

    Contains all metadata and data needed for generating DQ reports.

    Attributes:
        run_id: Pipeline run identifier.
        pipeline_name: Name of the pipeline.
        timestamp: Report generation timestamp (UTC).
        provider: Data provider name (e.g., 'chembl').
        entity: Entity type name (e.g., 'activity').
        bronze_source_file: Path to Bronze source file (for Bronze report).
        bronze_batch_id: Bronze batch identifier.
        bronze_records: Raw Bronze records (bytes iterator, consumed only once).
        bronze_output_path: Base path for Bronze DQ reports (optional).
        silver_data: Silver layer DataFrame (Polars).
        silver_target_table: Silver target table path.
        silver_source_batch_ids: List of Bronze batch IDs processed.
        silver_primary_keys: Primary key columns.
        silver_input_count: Total records before transformation.
        silver_quarantined_count: Quarantined records count.
        silver_output_path: Base path for Silver DQ reports (optional).
        gold_data: Gold layer DataFrame (Polars).
        gold_target_table: Gold target table path.
        gold_required_fields: Required fields for completeness check.
        gold_business_rules: Business rules for Gold validation.
        gold_baseline_stats: Baseline statistics for drift detection.
        gold_output_path: Base path for Gold DQ reports (optional).
        dq_soft_threshold: Soft fail threshold for DQ checks.
        dq_hard_threshold: Hard fail threshold for DQ checks.
        flat_structure: Whether to use flat file structure for DQ reports.
    """

    run_id: str
    pipeline_name: str
    timestamp: datetime

    # Provider and entity for filename generation
    provider: str | None = None
    entity: str | None = None

    # Bronze context
    bronze_source_file: str | None = None
    bronze_batch_id: str | None = None
    bronze_records: list[bytes] | None = None
    bronze_output_path: str | None = None
    bronze_date_str: str | None = None  # Date string (YYYY-MM-DD) for filename

    # Silver context
    silver_data: Any | None = None  # pl.DataFrame
    silver_target_table: str | None = None
    silver_source_batch_ids: list[str] | None = None
    silver_primary_keys: list[str] | None = None
    silver_input_count: int | None = None
    silver_quarantined_count: int = 0
    silver_previous_schema: dict[str, str] | None = None
    silver_output_path: str | None = None

    # Gold context
    gold_data: Any | None = None  # pl.DataFrame
    gold_target_table: str | None = None
    gold_required_fields: list[str] | None = None
    gold_business_rules: list[dict[str, Any]] | None = None
    gold_baseline_stats: dict[str, Any] | None = None
    gold_output_path: str | None = None

    # DQ thresholds
    dq_soft_threshold: float = 0.05
    dq_hard_threshold: float = 0.20

    # Flat structure flag for DQ reports
    flat_structure: bool = False


class DQReportService:
    """Service for orchestrating DQ report generation.

    Generates detailed DQ analysis reports for Bronze, Silver, and Gold layers
    when enabled in the pipeline configuration.

    Attributes:
        _bronze_analyzer: Bronze layer DQ analyzer (optional).
        _silver_analyzer: Silver layer DQ analyzer (optional).
        _gold_analyzer: Gold layer DQ analyzer (optional).
        _report_writer: DQ report writer (optional).
        _logger: Structured logger for observability.
    """

    def __init__(
        self,
        logger: LoggerPort,
        bronze_analyzer: BronzeDQAnalyzerPort | None = None,
        silver_analyzer: SilverDQAnalyzerPort | None = None,
        gold_analyzer: GoldDQAnalyzerPort | None = None,
        report_writer: DQReportWriterPort | None = None,
    ) -> None:
        """Initialize DQ report service.

        Args:
            logger: Structured logger for observability.
            bronze_analyzer: Optional Bronze layer DQ analyzer.
            silver_analyzer: Optional Silver layer DQ analyzer.
            gold_analyzer: Optional Gold layer DQ analyzer.
            report_writer: Optional DQ report writer.
        """
        self._logger = logger
        self._bronze_analyzer = bronze_analyzer
        self._silver_analyzer = silver_analyzer
        self._gold_analyzer = gold_analyzer
        self._report_writer = report_writer

    async def generate_reports(
        self,
        context: DQReportContext,
        bronze_config: BronzeDQConfigPort | None = None,
        silver_config: SilverDQConfigPort | None = None,
        gold_config: GoldDQConfigPort | None = None,
    ) -> DQReportResult:
        """Generate DQ reports for all enabled layers.

        Args:
            context: DQ report context with data and metadata.
            bronze_config: Bronze DQ report configuration (optional).
            silver_config: Silver DQ report configuration (optional).
            gold_config: Gold DQ report configuration (optional).

        Returns:
            DQReportResult with paths to generated reports.
        """
        bronze_enabled = self._is_config_enabled(bronze_config)
        silver_enabled = self._is_config_enabled(silver_config)
        gold_enabled = self._is_config_enabled(gold_config)

        self._log_generation_start(
            context.run_id, bronze_enabled, silver_enabled, gold_enabled
        )

        bronze_path = await self._try_generate_bronze(
            context, bronze_config, bronze_enabled
        )
        silver_path = await self._try_generate_silver(
            context, silver_config, silver_enabled
        )
        gold_path = await self._try_generate_gold(context, gold_config, gold_enabled)

        result = DQReportResult(
            bronze_report_path=bronze_path,
            silver_report_path=silver_path,
            gold_report_path=gold_path,
            bronze_enabled=bronze_enabled,
            silver_enabled=silver_enabled,
            gold_enabled=gold_enabled,
        )

        self._log_generation_result(context.run_id, result)
        return result

    @staticmethod
    def _is_config_enabled(config: Any) -> bool:
        """Check if a config is present and enabled."""
        return config is not None and config.enabled

    def _log_generation_start(
        self,
        run_id: str,
        bronze_enabled: bool,
        silver_enabled: bool,
        gold_enabled: bool,
    ) -> None:
        """Log the start of DQ report generation."""
        self._logger.debug(
            "dq_report_generation_started",
            run_id=run_id,
            bronze_enabled=bronze_enabled,
            silver_enabled=silver_enabled,
            gold_enabled=gold_enabled,
        )

    def _log_generation_result(self, run_id: str, result: DQReportResult) -> None:
        """Log the result of DQ report generation if any were generated."""
        if not result.any_generated:
            return
        self._logger.info(
            "dq_reports_generated",
            run_id=run_id,
            reports_count=result.reports_count,
            bronze_path=self._path_to_str(result.bronze_report_path),
            silver_path=self._path_to_str(result.silver_report_path),
            gold_path=self._path_to_str(result.gold_report_path),
        )

    @staticmethod
    def _path_to_str(path: Path | None) -> str | None:
        """Convert path to string or None."""
        return str(path) if path else None

    async def _try_generate_bronze(
        self,
        context: DQReportContext,
        config: BronzeDQConfigPort | None,
        enabled: bool,
    ) -> Path | None:
        """Try to generate Bronze report if enabled."""
        if enabled and config:
            return await self._generate_bronze_report(context, config)
        return None

    async def _try_generate_silver(
        self,
        context: DQReportContext,
        config: SilverDQConfigPort | None,
        enabled: bool,
    ) -> Path | None:
        """Try to generate Silver report if enabled."""
        if enabled and config:
            return await self._generate_silver_report(context, config)
        return None

    async def _try_generate_gold(
        self,
        context: DQReportContext,
        config: GoldDQConfigPort | None,
        enabled: bool,
    ) -> Path | None:
        """Try to generate Gold report if enabled."""
        if enabled and config:
            return await self._generate_gold_report(context, config)
        return None

    async def _generate_bronze_report(
        self,
        context: DQReportContext,
        config: BronzeDQConfigPort,
    ) -> Path | None:
        """Generate Bronze DQ report.

        Args:
            context: DQ report context.
            config: Bronze DQ report configuration.

        Returns:
            Path to the generated report, or None if generation failed.
        """
        if not self._bronze_analyzer or not self._report_writer:
            self._logger.warning(
                "bronze_dq_report_skipped",
                reason="analyzer or writer not available",
                run_id=context.run_id,
            )
            return None

        if context.bronze_records is None or context.bronze_batch_id is None:
            self._logger.warning(
                "bronze_dq_report_skipped",
                reason="no bronze data available",
                run_id=context.run_id,
            )
            return None

        try:
            # Analyze Bronze data
            report = self._bronze_analyzer.analyze(
                records=iter(context.bronze_records),
                run_id=context.run_id,
                pipeline=context.pipeline_name,
                batch_id=context.bronze_batch_id,
                source_file=context.bronze_source_file or "",
                config=config,
                timestamp=context.timestamp,
            )

            # Write report - use context output_path if provided, else config
            output_path: Path | None = None
            if context.bronze_output_path:
                output_path = Path(context.bronze_output_path)
            elif config.output_path:
                output_path = Path(config.output_path)

            path = await self._report_writer.write_bronze_report(
                report=report,
                output_path=output_path,
                format=config.get_format_enum(),
                provider=context.provider,
                entity=context.entity,
                date_str=context.bronze_date_str,
            )

            self._logger.debug(
                "bronze_dq_report_generated",
                run_id=context.run_id,
                path=str(path),
                status=report.summary.overall_status.value,
            )

            return path

        except Exception as e:
            self._logger.error(
                "bronze_dq_report_failed",
                run_id=context.run_id,
                error=str(e),
            )
            return None

    async def _generate_silver_report(
        self,
        context: DQReportContext,
        config: SilverDQConfigPort,
    ) -> Path | None:
        """Generate Silver DQ report.

        Args:
            context: DQ report context.
            config: Silver DQ report configuration.

        Returns:
            Path to the generated report, or None if generation failed.
        """
        if not self._silver_analyzer or not self._report_writer:
            self._logger.warning(
                "silver_dq_report_skipped",
                reason="analyzer or writer not available",
                run_id=context.run_id,
            )
            return None

        if context.silver_data is None or context.silver_target_table is None:
            self._logger.warning(
                "silver_dq_report_skipped",
                reason="no silver data available",
                run_id=context.run_id,
            )
            return None

        try:
            # Analyze Silver data
            report = self._silver_analyzer.analyze(
                data=context.silver_data,
                run_id=context.run_id,
                pipeline=context.pipeline_name,
                target_table=context.silver_target_table,
                source_batch_ids=context.silver_source_batch_ids or [],
                config=config,
                timestamp=context.timestamp,
                primary_keys=context.silver_primary_keys or [],
                soft_fail_threshold=context.dq_soft_threshold,
                hard_fail_threshold=context.dq_hard_threshold,
                input_record_count=context.silver_input_count,
                quarantined_count=context.silver_quarantined_count,
                previous_schema=context.silver_previous_schema,
            )

            # Write report - use context output_path if provided, else config
            output_path: Path | None = None
            if context.silver_output_path:
                output_path = Path(context.silver_output_path)
            elif config.output_path:
                output_path = Path(config.output_path)

            path = await self._report_writer.write_silver_report(
                report=report,
                output_path=output_path,
                format=config.get_format_enum(),
                provider=context.provider,
                entity=context.entity,
            )

            self._logger.debug(
                "silver_dq_report_generated",
                run_id=context.run_id,
                path=str(path),
                status=report.summary.overall_status.value,
            )

            return path

        except Exception as e:
            self._logger.error(
                "silver_dq_report_failed",
                run_id=context.run_id,
                error=str(e),
            )
            return None

    async def _generate_gold_report(
        self,
        context: DQReportContext,
        config: GoldDQConfigPort,
    ) -> Path | None:
        """Generate Gold DQ report.

        Args:
            context: DQ report context.
            config: Gold DQ report configuration.

        Returns:
            Path to the generated report, or None if generation failed.
        """
        if not self._gold_analyzer or not self._report_writer:
            self._logger.warning(
                "gold_dq_report_skipped",
                reason="analyzer or writer not available",
                run_id=context.run_id,
            )
            return None

        if context.gold_data is None or context.gold_target_table is None:
            self._logger.warning(
                "gold_dq_report_skipped",
                reason="no gold data available",
                run_id=context.run_id,
            )
            return None

        try:
            # Analyze Gold data
            report = self._gold_analyzer.analyze(
                data=context.gold_data,
                run_id=context.run_id,
                pipeline=context.pipeline_name,
                target_table=context.gold_target_table,
                config=config,
                timestamp=context.timestamp,
                required_fields=context.gold_required_fields,
                business_rules=context.gold_business_rules,
                baseline_stats=context.gold_baseline_stats,
            )

            # Write report - use context output_path if provided, else config
            output_path: Path | None = None
            if context.gold_output_path:
                output_path = Path(context.gold_output_path)
            elif config.output_path:
                output_path = Path(config.output_path)

            path = await self._report_writer.write_gold_report(
                report=report,
                output_path=output_path,
                format=config.get_format_enum(),
                provider=context.provider,
                entity=context.entity,
            )

            self._logger.debug(
                "gold_dq_report_generated",
                run_id=context.run_id,
                path=str(path),
                status=report.summary.overall_status.value,
            )

            return path

        except Exception as e:
            self._logger.error(
                "gold_dq_report_failed",
                run_id=context.run_id,
                error=str(e),
            )
            return None

    def is_any_report_enabled(
        self,
        bronze_config: BronzeDQConfigPort | None = None,
        silver_config: SilverDQConfigPort | None = None,
        gold_config: GoldDQConfigPort | None = None,
    ) -> bool:
        """Check if any DQ report generation is enabled.

        Args:
            bronze_config: Bronze DQ report configuration.
            silver_config: Silver DQ report configuration.
            gold_config: Gold DQ report configuration.

        Returns:
            True if any layer has DQ report enabled.
        """
        return (
            (bronze_config is not None and bronze_config.enabled)
            or (silver_config is not None and silver_config.enabled)
            or (gold_config is not None and gold_config.enabled)
        )


__all__ = [
    "DQReportContext",
    "DQReportResult",
    "DQReportService",
]

================================================================================
File: export_service.py
Path: services\export_service.py
================================================================================
"""Export service for Delta Lake tables.

Provides high-level export operations for Silver/Gold Delta tables
to CSV, XLSX, and TSV formats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.domain.ports import DeltaReaderPort, LoggerPort


ExportFormat = Literal["csv", "xlsx", "tsv"]


@dataclass(frozen=True, slots=True)
class ColumnInfo:
    """Information about a table column.

    Attributes:
        name: Column name.
        type: Column data type as string.
        nullable: Whether the column allows nulls.
    """

    name: str
    type: str
    nullable: bool


@dataclass(frozen=True, slots=True)
class TablePreview:
    """Preview of a Delta table for display.

    Attributes:
        table_name: Full table name (e.g., chembl.activity).
        layer: Medallion layer (silver/gold).
        row_count: Total number of rows.
        columns: List of column information.
        sample_rows: First few rows as dictionaries.
    """

    table_name: str
    layer: str
    row_count: int
    columns: tuple[ColumnInfo, ...]
    sample_rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class TableInfo:
    """Information about a discovered table.

    Attributes:
        name: Table name in format "provider.entity".
        layer: Medallion layer (silver/gold).
        path: Full path to the table directory.
    """

    name: str
    layer: str
    path: Path


@dataclass(frozen=True, slots=True)
class ExportOptions:
    """Options for export operation.

    Attributes:
        format: Output format (csv, xlsx, tsv).
        output_path: Directory to write output file.
        limit: Maximum rows to export (None for all).
        columns: Columns to include (None for all).
    """

    format: ExportFormat = "csv"
    output_path: Path | None = None
    limit: int | None = None
    columns: list[str] | None = None


@dataclass(frozen=True, slots=True)
class ExportResult:
    """Result of an export operation.

    Attributes:
        table_name: Name of exported table.
        layer: Medallion layer.
        format: Output format used.
        output_path: Path to the exported file.
        row_count: Number of rows exported.
        error: Error message if export failed.
    """

    table_name: str
    layer: str
    format: ExportFormat
    output_path: Path | None
    row_count: int
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if export succeeded."""
        return self.error is None


def _scan_layer_for_tables(base_path: Path, layer_name: str) -> list[TableInfo]:
    """Scan a layer directory for Delta tables.

    Args:
        base_path: Root path of the layer.
        layer_name: Name of the layer (silver/gold).

    Returns:
        List of TableInfo for discovered tables.
    """
    tables: list[TableInfo] = []
    if not base_path.exists():
        return tables

    for provider_dir in base_path.iterdir():
        if not provider_dir.is_dir():
            continue
        tables.extend(_scan_provider_for_tables(provider_dir, layer_name))

    return tables


def _scan_provider_for_tables(provider_dir: Path, layer_name: str) -> list[TableInfo]:
    """Scan a provider directory for Delta tables.

    Args:
        provider_dir: Provider directory path.
        layer_name: Name of the layer.

    Returns:
        List of TableInfo for discovered tables.
    """
    tables: list[TableInfo] = []
    for entity_dir in provider_dir.iterdir():
        if not entity_dir.is_dir():
            continue
        for table_dir in entity_dir.iterdir():
            if table_dir.is_dir() and (table_dir / "_delta_log").exists():
                tables.append(
                    TableInfo(name=table_dir.name, layer=layer_name, path=table_dir)
                )
    return tables


def _write_delimited_file(
    table: pa.Table, output_path: Path, delimiter: str = ","
) -> Path:
    """Write Arrow table to delimited file (CSV or TSV).

    Args:
        table: PyArrow table to write.
        output_path: Path to output file.
        delimiter: Field delimiter character.

    Returns:
        Path to written file.
    """
    import pyarrow.csv as pv

    from bioetl.domain.serialization import flatten_arrow_table_for_export

    flattened = flatten_arrow_table_for_export(table)
    write_options = pv.WriteOptions(delimiter=delimiter)
    pv.write_csv(flattened, output_path, write_options=write_options)
    return output_path


def _write_xlsx_file(table: pa.Table, output_path: Path) -> Path:
    """Write Arrow table to XLSX file.

    Args:
        table: PyArrow table to write.
        output_path: Path to output file.

    Returns:
        Path to written file.

    Raises:
        ImportError: If openpyxl is not installed.
    """
    from bioetl.domain.serialization import flatten_arrow_table_for_export

    flattened = flatten_arrow_table_for_export(table)
    df = flattened.to_pandas()

    try:
        df.to_excel(output_path, index=False, engine="openpyxl")
    except ImportError as e:
        raise ImportError(
            "openpyxl is required for XLSX export. Install with: pip install openpyxl"
        ) from e

    return output_path


@dataclass
class ExportService:
    """Service for exporting Delta Lake tables to various formats.

    Responsibilities:
    - Discover tables in Silver/Gold layers
    - Preview table schema and sample data
    - Export tables to CSV, XLSX, TSV formats

    Attributes:
        reader: Delta reader for accessing tables.
        logger: Structured logger for observability.
        silver_path: Base path for Silver layer.
        gold_path: Base path for Gold layer.
        export_path: Default export output directory.
    """

    reader: DeltaReaderPort
    logger: LoggerPort
    silver_path: Path
    gold_path: Path
    export_path: Path = field(default_factory=lambda: Path("data/exports"))

    def list_tables(self, layer: str = "all") -> list[TableInfo]:
        """Discover available Delta tables.

        Args:
            layer: Which layer to scan - "all", "silver", or "gold".

        Returns:
            List of discovered tables, sorted alphabetically.
        """
        tables: list[TableInfo] = []
        if layer in ("all", "silver"):
            tables.extend(_scan_layer_for_tables(self.silver_path, "silver"))
        if layer in ("all", "gold"):
            tables.extend(_scan_layer_for_tables(self.gold_path, "gold"))
        return sorted(tables, key=lambda t: (t.layer, t.name))

    async def preview(
        self,
        table_name: str,
        layer: str = "silver",
        sample_rows: int = 5,
    ) -> TablePreview:
        """Get preview of a table's schema and sample data.

        Args:
            table_name: Table name in format "provider.entity".
            layer: Medallion layer to read from.
            sample_rows: Number of sample rows to include.

        Returns:
            TablePreview with schema and sample data.

        Raises:
            FileNotFoundError: If table does not exist.
        """
        table_path = self._get_table_path(table_name, layer)

        schema = await self.reader.get_schema(str(table_path))
        columns = tuple(
            ColumnInfo(name=f.name, type=str(f.type), nullable=f.nullable)
            for f in schema
        )

        row_count = await self.reader.get_row_count(str(table_path))
        sample_table = await self.reader.read_table(str(table_path), limit=sample_rows)
        samples = tuple(sample_table.to_pylist())

        return TablePreview(
            table_name=table_name,
            layer=layer,
            row_count=row_count,
            columns=columns,
            sample_rows=samples,
        )

    async def export(
        self,
        table_name: str,
        layer: str = "silver",
        options: ExportOptions | None = None,
    ) -> ExportResult:
        """Export a Delta table to the specified format.

        Args:
            table_name: Table name in format "provider.entity".
            layer: Medallion layer to read from.
            options: Export options (format, output path, etc.).

        Returns:
            ExportResult with export outcome.
        """
        options = options or ExportOptions()
        table_path = self._get_table_path(table_name, layer)

        try:
            if not await self.reader.table_exists(str(table_path)):
                return ExportResult(
                    table_name=table_name,
                    layer=layer,
                    format=options.format,
                    output_path=None,
                    row_count=0,
                    error=f"Table not found: {table_path}",
                )

            self.logger.info(
                "Reading table for export",
                table=table_name,
                layer=layer,
                format=options.format,
                limit=options.limit,
            )

            table = await self.reader.read_table(
                str(table_path), columns=options.columns, limit=options.limit
            )
            row_count = table.num_rows

            output_dir = options.output_path or self.export_path
            output_dir.mkdir(parents=True, exist_ok=True)

            output_path = self._write_export(
                table, table_name, layer, options.format, output_dir
            )

            self.logger.info(
                "Export completed",
                table=table_name,
                rows=row_count,
                output=str(output_path),
            )

            return ExportResult(
                table_name=table_name,
                layer=layer,
                format=options.format,
                output_path=output_path,
                row_count=row_count,
            )

        except Exception as e:
            self.logger.error(
                "Export failed", table=table_name, layer=layer, error=str(e)
            )
            return ExportResult(
                table_name=table_name,
                layer=layer,
                format=options.format,
                output_path=None,
                row_count=0,
                error=str(e),
            )

    def _write_export(
        self,
        table: pa.Table,
        table_name: str,
        layer: str,
        fmt: ExportFormat,
        output_dir: Path,
    ) -> Path:
        """Write table to export file using appropriate format."""
        safe_name = f"{layer}_{table_name.replace('.', '_')}"

        if fmt == "csv":
            return _write_delimited_file(table, output_dir / f"{safe_name}.csv", ",")
        elif fmt == "tsv":
            return _write_delimited_file(table, output_dir / f"{safe_name}.tsv", "\t")
        elif fmt == "xlsx":
            return _write_xlsx_file(table, output_dir / f"{safe_name}.xlsx")
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def _get_table_path(self, table_name: str, layer: str) -> Path:
        """Get the filesystem path for a table."""
        if layer == "silver":
            base_path = self.silver_path
        elif layer == "gold":
            base_path = self.gold_path
        else:
            raise ValueError(f"Invalid layer: {layer}")

        if not base_path.exists():
            raise FileNotFoundError(f"Layer path not found: {base_path}")

        for provider_dir in base_path.iterdir():
            if not provider_dir.is_dir():
                continue
            for entity_dir in provider_dir.iterdir():
                if not entity_dir.is_dir():
                    continue
                table_dir = entity_dir / table_name
                if table_dir.exists() and (table_dir / "_delta_log").exists():
                    return table_dir.resolve()

        raise FileNotFoundError(
            f"Table '{table_name}' not found in {layer} layer at {base_path}"
        )

================================================================================
File: health_service.py
Path: services\health_service.py
================================================================================
"""Health check service for administrative operations (Application layer).

Provides high-level health check operations for CLI and other interfaces.
Abstracts provider health checking behind application service.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from bioetl.domain.ports import HealthCheckPort, HealthCheckResult

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@runtime_checkable
class DataSourceFactoryPort(Protocol):
    """Protocol for data source factory operations.

    Abstracts data source creation for health checking.
    """

    @staticmethod
    def list_providers() -> list[str]:
        """List available provider names."""
        ...

    @staticmethod
    def create(provider_name: str) -> Any:
        """Create a data source adapter for the given provider."""
        ...


@dataclass(frozen=True, slots=True)
class HealthResult:
    """Result of a health check for a single provider.

    Attributes:
        provider: Name of the provider.
        status: Health status (healthy, degraded, unhealthy, unknown).
        latency_ms: Latency of the health check in milliseconds.
        endpoint: The endpoint used for health check.
        error: Error message if health check failed.
        checked_at: Timestamp when the health check was performed.
    """

    provider: str
    status: str
    latency_ms: float | None = None
    endpoint: str | None = None
    error: str | None = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @property
    def is_healthy(self) -> bool:
        """Return True if status is healthy."""
        return self.status == "healthy"

    @property
    def is_degraded(self) -> bool:
        """Return True if status is degraded."""
        return self.status == "degraded"

    @property
    def is_unhealthy(self) -> bool:
        """Return True if status is unhealthy or unknown."""
        return self.status in ("unhealthy", "unknown")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "status": self.status,
        }
        if self.latency_ms is not None:
            result["latency_ms"] = f"{self.latency_ms:.2f}"
        if self.endpoint:
            result["endpoint"] = self.endpoint
        if self.error:
            result["error"] = self.error
        return result


@dataclass(frozen=True, slots=True)
class HealthCheckSummary:
    """Summary of health check results across all providers.

    Attributes:
        results: Dictionary mapping provider names to health results.
        all_healthy: True if all providers are healthy.
        checked_at: Timestamp when the health checks were performed.
    """

    results: dict[str, HealthResult]
    all_healthy: bool
    checked_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @property
    def healthy_count(self) -> int:
        """Number of healthy providers."""
        return sum(1 for r in self.results.values() if r.is_healthy)

    @property
    def unhealthy_count(self) -> int:
        """Number of unhealthy providers."""
        return sum(1 for r in self.results.values() if r.is_unhealthy)

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Convert to dictionary for serialization."""
        return {name: result.to_dict() for name, result in self.results.items()}


@dataclass
class HealthService:
    """Service for provider health check operations.

    Provides high-level operations for checking provider health
    used by CLI and other interfaces. Abstracts data source factory
    for Application-layer abstraction.

    Attributes:
        logger: Structured logger for observability.
        _factory: Data source factory for creating adapters.

    Example:
        >>> service = HealthService(logger=logger, _factory=DataSourceFactory)
        >>> summary = await service.check_providers()
        >>> if summary.all_healthy:
        ...     logger.info("All providers healthy")
    """

    logger: LoggerPort
    _factory: Any  # DataSourceFactoryPort

    async def check_providers(
        self,
        providers: list[str] | None = None,
    ) -> HealthCheckSummary:
        """Check health of data providers.

        Args:
            providers: Specific providers to check. If None, checks all available.

        Returns:
            HealthCheckSummary with results for all checked providers.
        """
        self.logger.debug("Starting health checks", providers=providers)

        # Get providers to check
        available_providers = self._factory.list_providers()
        providers_to_check = list(providers) if providers else available_providers

        results: dict[str, HealthResult] = {}

        for provider in providers_to_check:
            result = await self._check_single_provider(provider)
            results[provider] = result

        all_healthy = all(r.is_healthy for r in results.values())

        summary = HealthCheckSummary(
            results=results,
            all_healthy=all_healthy,
        )

        self.logger.info(
            "Health checks completed",
            providers_checked=len(results),
            all_healthy=all_healthy,
            healthy_count=summary.healthy_count,
            unhealthy_count=summary.unhealthy_count,
        )

        return summary

    async def _check_single_provider(self, provider: str) -> HealthResult:
        """Check health of a single provider.

        Args:
            provider: Name of the provider to check.

        Returns:
            HealthResult for the provider.
        """
        self.logger.debug("Checking provider health", provider=provider)

        try:
            adapter = self._factory.create(provider)

            # Use runtime checkable protocol to verify adapter implements HealthCheckPort
            if isinstance(adapter, HealthCheckPort):
                result: HealthCheckResult = await adapter.check_health()
                return HealthResult(
                    provider=provider,
                    status=result.status.value.lower(),
                    latency_ms=result.latency_ms,
                    endpoint=result.endpoint,
                    error=result.last_error,
                    checked_at=result.checked_at,
                )

            # Adapter doesn't implement HealthCheckPort
            self.logger.warning(
                "Adapter does not implement HealthCheckPort",
                provider=provider,
            )
            return HealthResult(
                provider=provider,
                status="unknown",
                error="Adapter does not implement HealthCheckPort",
            )

        except Exception as e:
            self.logger.error(
                "Health check failed",
                provider=provider,
                error=str(e),
            )
            return HealthResult(
                provider=provider,
                status="unhealthy",
                error=str(e),
            )

    def list_available_providers(self) -> list[str]:
        """List all available providers that can be health checked.

        Returns:
            List of provider names.
        """
        providers: list[str] = self._factory.list_providers()
        self.logger.debug("Listed available providers", count=len(providers))
        return providers

================================================================================
File: lock_service.py
Path: services\lock_service.py
================================================================================
"""Lock service for administrative operations (Application layer).

Provides high-level lock management for CLI and other interfaces.
Uses LockPort for actual lock operations.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LockPort, LoggerPort
    from bioetl.domain.types import RunID


@dataclass(frozen=True, slots=True)
class LockInfo:
    """Information about a held lock.

    Attributes:
        key: Lock key (typically pipeline name).
        owner_id: Run ID that holds the lock.
        exclusive: Whether this is an exclusive lock.
    """

    key: str
    owner_id: str
    exclusive: bool


@dataclass
class LockService:
    """Service for administrative lock operations.

    Provides high-level operations for lock management
    used by CLI and other interfaces. Wraps LockPort
    for Application-layer abstraction.

    Note: The current LockPort interface doesn't support
    listing all locks. This service provides what's possible
    with the current port interface.

    Attributes:
        lock_port: Port for lock operations.
        logger: Structured logger for observability.

    Example:
        >>> service = LockService(lock_port=port, logger=logger)
        >>> released = await service.release_lock("chembl_activity", run_id)
        >>> logger.info("lock_released", pipeline="chembl_activity", released=released)
    """

    lock_port: LockPort
    logger: LoggerPort

    async def check_lock(
        self,
        pipeline_id: str,
        owner_id: RunID,
    ) -> bool:
        """Check if a specific lock is held by the given owner.

        Args:
            pipeline_id: Pipeline identifier (lock key).
            owner_id: Run ID to check.

        Returns:
            True if the lock is held by this owner, False otherwise.
        """
        self.logger.debug(
            "Checking lock",
            pipeline=pipeline_id,
            owner_id=str(owner_id),
        )

        # Use validate_owner to check if lock is held
        is_held = await self.lock_port.validate_owner(
            key=pipeline_id,
            owner_id=owner_id,
        )

        self.logger.info(
            "Lock check complete",
            pipeline=pipeline_id,
            is_held=is_held,
        )

        return is_held

    async def release_lock(
        self,
        pipeline_id: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """Release a lock for a specific pipeline.

        Args:
            pipeline_id: Pipeline identifier (lock key).
            owner_id: Run ID that holds the lock.
            exclusive: Whether this is an exclusive lock.

        Returns:
            True if lock was released, False if it wasn't held.
        """
        self.logger.info(
            "Releasing lock",
            pipeline=pipeline_id,
            owner_id=str(owner_id),
            exclusive=exclusive,
        )

        released = await self.lock_port.release(
            key=pipeline_id,
            owner_id=owner_id,
            exclusive=exclusive,
        )

        if released:
            self.logger.info(
                "Lock released",
                pipeline=pipeline_id,
            )
        else:
            self.logger.warning(
                "Lock not released (not held or already released)",
                pipeline=pipeline_id,
            )

        return released

    async def force_release_all(
        self,
        owner_id: RunID,
        pipeline_ids: list[str],
    ) -> list[str]:
        """Attempt to release locks for multiple pipelines.

        This is useful for cleanup after a crashed process.
        Only releases locks that are actually held by the given owner.

        Args:
            owner_id: Run ID that should hold the locks.
            pipeline_ids: List of pipeline identifiers to try releasing.

        Returns:
            List of pipeline IDs where locks were successfully released.
        """
        self.logger.info(
            "Force releasing locks",
            owner_id=str(owner_id),
            pipeline_count=len(pipeline_ids),
        )

        released: list[str] = []

        for pipeline_id in pipeline_ids:
            # Try both regular and exclusive locks
            if await self.release_lock(pipeline_id, owner_id, exclusive=False):
                released.append(pipeline_id)
            elif await self.release_lock(pipeline_id, owner_id, exclusive=True):
                released.append(f"{pipeline_id}:exclusive")

        self.logger.info(
            "Force release complete",
            released_count=len(released),
            released=released,
        )

        return released

    async def list_locks(self) -> list[LockInfo]:
        """List all currently held locks.

        Note: The current LockPort interface doesn't support
        listing all locks. This method returns an empty list
        and logs a warning. Future implementations may extend
        the LockPort to support this operation.

        Returns:
            List of LockInfo for all held locks (currently empty).
        """
        self.logger.warning(
            "list_locks not supported by current LockPort implementation",
            note="Returning empty list - port extension required",
        )

        # LockPort doesn't support listing locks
        # Would need to extend the port interface for this functionality
        return []

    async def aclose(self) -> None:
        """Close the service and release resources."""
        await self.lock_port.aclose()

================================================================================
File: medallion_lifecycle.py
Path: services\medallion_lifecycle.py
================================================================================
"""Medallion lifecycle service (Application layer - orchestration).

Implements RULES.md §2.1-2.3 medallion architecture lifecycle operations.
This service manages clearing, vacuum, and future archive operations.

All medallion layer operations are consolidated here:
- prepare_for_run(): Pre-run clearing based on run type policy
- finalize_run(): Post-run vacuum operations
- clear(): Direct clearing based on policy
- vacuum(): Single table vacuum operation
- archive(): Cold storage archival
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.medallion_types import (
    ClearResult,
    PrepareResult,
    VacuumResult,
)

if TYPE_CHECKING:
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.medallion import MedallionPolicy
    from bioetl.domain.ports import LoggerPort, MetricsPort, StoragePort


@dataclass
class MedallionLifecycleService:
    """Unified service for managing medallion layer lifecycle operations.

    Consolidates all medallion lifecycle operations under one interface:
    - Pre-run: prepare_for_run() clears layers based on run type policy
    - Post-run: finalize_run() vacuums tables to reclaim storage
    - Direct: clear(), vacuum(), archive() for fine-grained control

    This service replaces the separate LifecycleOrchestrator and vacuum
    logic previously scattered across PostrunService.

    Attributes:
        storage: StoragePort for data layer operations.
        logger: Structured logger for observability.

    Example:
        >>> # Unified lifecycle for pipeline runs
        >>> service = MedallionLifecycleService(storage=storage, logger=logger)
        >>> # Pre-run: clear based on run type
        >>> prepare_result = await service.prepare_for_run(config, runtime)
        >>> # Post-run: vacuum if enabled
        >>> vacuum_result = await service.finalize_run(config, runtime)
    """

    storage: StoragePort
    logger: LoggerPort

    async def clear(
        self,
        policy: MedallionPolicy,
        silver_table: str,
        gold_table: str,
        dry_run: bool = False,
    ) -> ClearResult:
        """Clear medallion layers according to policy.

        Enforces medallion architecture invariants:
        - Only clears based on policy (not run type directly)
        - Logs all operations for observability

        Args:
            policy: Medallion policy determining what to clear.
            silver_table: Silver table name.
            gold_table: Gold table name.
            dry_run: If True, only count without deleting.

        Returns:
            ClearResult with counts of cleared records.
        """
        silver_cleared = 0
        gold_cleared = 0

        if policy.should_clear_silver:
            silver_cleared = await self.storage.clear_silver(
                silver_table, dry_run=dry_run
            )

        if policy.should_clear_gold:
            gold_cleared = await self.storage.clear_gold(gold_table, dry_run=dry_run)

        result = ClearResult(
            silver_cleared=silver_cleared,
            gold_cleared=gold_cleared,
            dry_run=dry_run,
        )

        self._log_result(policy, silver_table, gold_table, result)

        return result

    def _log_result(
        self,
        policy: MedallionPolicy,
        silver_table: str,
        gold_table: str,
        result: ClearResult,
    ) -> None:
        """Log clear operation result.

        Args:
            policy: The medallion policy used.
            silver_table: Silver table name.
            gold_table: Gold table name.
            result: The clear operation result.
        """
        if result.dry_run:
            self.logger.info(
                "DRY RUN: Would clear storage",
                extra={
                    "policy": policy.clear_policy.value,
                    "silver_table": silver_table,
                    "gold_table": gold_table,
                    "silver_would_clear": result.silver_cleared,
                    "gold_would_clear": result.gold_cleared,
                },
            )
        elif result.total_cleared > 0:
            self.logger.info(
                "Cleared storage",
                extra={
                    "policy": policy.clear_policy.value,
                    "silver_cleared": result.silver_cleared,
                    "gold_cleared": result.gold_cleared,
                },
            )

    async def vacuum(
        self,
        table: str,
        retention_days: int = 7,
        dry_run: bool = False,
    ) -> int:
        """Vacuum Delta table to reclaim storage space.

        Removes files older than retention period that are no longer
        referenced by the Delta log. Safe to run concurrently with reads.

        Args:
            table: Table name in format "provider.entity"
            retention_days: Minimum age of files to remove (default 7)
            dry_run: If True, only report what would be removed

        Returns:
            Number of files removed

        Raises:
            StorageError: If vacuum fails
        """
        retention_hours = retention_days * 24

        self.logger.info(
            "Starting vacuum operation",
            table=table,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        try:
            files_removed = await self.storage.vacuum(
                table_name=table,
                retention_hours=retention_hours,
                dry_run=dry_run,
            )

            self.logger.info(
                "Vacuum completed",
                table=table,
                files_removed=files_removed,
                dry_run=dry_run,
            )

            return files_removed

        except Exception as e:
            self.logger.error(
                "Vacuum failed",
                table=table,
                error=str(e),
            )
            raise

    async def archive(
        self,
        table: str,
        target_path: str,
        remove_source: bool = False,
    ) -> int:
        """Archive Delta table to cold storage.

        Copies table data to archive location. Optionally removes source
        after successful copy.

        Args:
            table: Table name to archive
            target_path: Destination path for archive
            remove_source: If True, remove source after successful copy

        Returns:
            Number of files archived

        Raises:
            StorageError: If archive fails
        """
        self.logger.info(
            "Starting archive operation",
            table=table,
            target_path=target_path,
            remove_source=remove_source,
        )

        try:
            files_archived = await self.storage.archive(
                table_name=table,
                target_path=target_path,
                remove_source=remove_source,
            )

            self.logger.info(
                "Archive completed",
                table=table,
                files_archived=files_archived,
            )

            return files_archived

        except Exception as e:
            self.logger.error(
                "Archive failed",
                table=table,
                error=str(e),
            )
            raise

    # =========================================================================
    # High-level pipeline lifecycle operations
    # =========================================================================

    async def prepare_for_run(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
    ) -> PrepareResult:
        """Prepare medallion layers for pipeline run.

        Clears Silver/Gold tables based on run type policy:
        - REBUILD/BACKFILL: Clear both Silver and Gold
        - INCREMENTAL: Never clear (merge/upsert behavior)

        This method consolidates logic previously in LifecycleOrchestrator.

        Args:
            config: Pipeline configuration with table names.
            runtime: Runtime configuration with run type and dry_run flag.

        Returns:
            PrepareResult with clear result and policy used.
        """
        from bioetl.domain.medallion import MedallionPolicy

        policy = MedallionPolicy.for_run_type(runtime.run_type)

        gold_table = config.gold_table or f"{config.provider}.{config.entity_type}"

        result = await self.clear(
            policy=policy,
            silver_table=config.silver_table,
            gold_table=gold_table,
            dry_run=runtime.dry_run,
        )

        self.logger.debug(
            "Medallion prepare completed",
            extra={
                "run_type": runtime.run_type.value,
                "clear_policy": policy.clear_policy.value,
                "silver_cleared": result.silver_cleared,
                "gold_cleared": result.gold_cleared,
            },
        )

        return PrepareResult(clear_result=result, policy=policy)

    async def finalize_run(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        metrics: MetricsPort | None = None,
    ) -> VacuumResult:
        """Finalize medallion layers after pipeline run.

        Optimizes storage (Vacuum/Cleanup) if enabled:
        - Skipped if neither optimize_storage nor vacuum_after_run is True
        - Uses StoragePort.optimize() for unified maintenance

        Args:
            config: Pipeline configuration with table names.
            runtime: Runtime configuration with vacuum settings.
            metrics: Optional metrics port for observability.

        Returns:
            VacuumResult (counts are 0 as implementation details are hidden).
        """
        # Support both new flag and legacy flag
        enabled = runtime.optimize_storage or runtime.vacuum_after_run

        if not enabled:
            return VacuumResult(
                silver_files_removed=0, gold_files_removed=0, skipped=True
            )

        self.logger.info(
            "Starting storage optimization",
            extra={
                "stage": "optimize",
                "retention_days": runtime.vacuum_retention_days,
                "dry_run": runtime.dry_run,
                "target": config.silver_table,
            },
        )

        try:
            # StoragePort.optimize unifies vacuum and file cleanup
            # We call it for both Silver and Gold tables to ensure all layers are covered
            # even if table names differ (custom Gold table).

            # Optimize based on Silver table name (covers Silver layer + Bronze)
            await self.storage.optimize(
                table_name=config.silver_table,
                retention_hours=runtime.vacuum_retention_days * 24,
                dry_run=runtime.dry_run,
            )

            gold_table = config.gold_table or f"{config.provider}.{config.entity_type}"

            # Optimize based on Gold table name if different (covers Gold layer)
            if gold_table != config.silver_table:
                await self.storage.optimize(
                    table_name=gold_table,
                    retention_hours=runtime.vacuum_retention_days * 24,
                    dry_run=runtime.dry_run,
                )

            # Metrics for success
            if metrics:
                metrics.increment_counter(
                    "storage_optimization_total",
                    1,
                    {"pipeline": config.pipeline_name, "status": "success"},
                )

            # Implementation details are hidden, so we return 0 counts
            # This is acceptable as the unification hides explicit layer operations
            return VacuumResult(
                silver_files_removed=0,
                gold_files_removed=0,
                skipped=False,
            )

        except Exception as e:
            self.logger.error(
                "storage_optimization_failed",
                pipeline=config.pipeline_name,
                error=str(e),
            )
            if metrics:
                metrics.increment_counter(
                    "storage_optimization_total",
                    1,
                    {"pipeline": config.pipeline_name, "status": "failed"},
                )
            # Don't fail the pipeline for maintenance tasks
            return VacuumResult(
                silver_files_removed=0,
                gold_files_removed=0,
                skipped=False,
            )


__all__ = [
    "ClearResult",
    "MedallionLifecycleService",
    "PrepareResult",
    "VacuumResult",
]

================================================================================
File: medallion_types.py
Path: services\medallion_types.py
================================================================================
"""Value objects for Medallion lifecycle operations.

Extracted from medallion_lifecycle.py to reduce file size and coupling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.medallion import MedallionPolicy


@dataclass(frozen=True, slots=True)
class ClearResult:
    """Result of clear operation.

    Attributes:
        silver_cleared: Number of Silver records cleared.
        gold_cleared: Number of Gold records cleared.
        dry_run: Whether this was a dry run (no actual deletion).
    """

    silver_cleared: int
    gold_cleared: int
    dry_run: bool

    @property
    def total_cleared(self) -> int:
        """Get total records cleared.

        Returns:
            Sum of silver and gold cleared records.
        """
        return self.silver_cleared + self.gold_cleared


@dataclass(frozen=True, slots=True)
class VacuumResult:
    """Result of VACUUM operation.

    Attributes:
        silver_files_removed: Number of files removed from Silver table.
        gold_files_removed: Number of files removed from Gold table.
        skipped: Whether VACUUM was skipped.
    """

    silver_files_removed: int
    gold_files_removed: int
    skipped: bool


@dataclass(frozen=True, slots=True)
class PrepareResult:
    """Result of prepare_for_run operation.

    Combines clear result with policy used for transparency.

    Attributes:
        clear_result: Result of clear operation.
        policy: MedallionPolicy used for the operation.
    """

    clear_result: ClearResult
    policy: MedallionPolicy

================================================================================
File: metrics_service.py
Path: services\metrics_service.py
================================================================================
"""Metrics service for application-layer metrics server management.

Provides high-level operations for managing the Prometheus metrics server.
Abstracts infrastructure concerns from CLI and other interfaces.

Implements RULES.md §1.1 - Application layer depends only on Domain.

Note:
    MetricsServerError is defined in domain.exceptions.critical
    and re-exported here for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.domain.exceptions import MetricsServerError

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

# Re-export for backward compatibility
__all__ = [
    "MetricsServerError",
    "MetricsServerPort",
    "MetricsServerStatus",
    "MetricsService",
    "StartResult",
]


@runtime_checkable
class MetricsServerPort(Protocol):
    """Protocol for metrics server operations.

    Abstracts the metrics server infrastructure for application layer.
    """

    def start(
        self,
        port: int,
        *,
        fail_fast: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> bool:
        """Start the metrics server.

        Args:
            port: Port to bind the HTTP server.
            fail_fast: If True, raise on failure.
            retry_count: Number of retries for transient errors.
            retry_delay: Delay between retries in seconds.

        Returns:
            True if server started successfully, False otherwise.
        """
        ...

    def is_running(self) -> bool:
        """Check if the server is currently running."""
        ...

    def reset(self) -> None:
        """Reset server state (for testing purposes)."""
        ...


@dataclass(frozen=True, slots=True)
class MetricsServerStatus:
    """Status of the metrics server.

    Attributes:
        running: Whether the server is running.
        port: Port the server is bound to (if running).
        started_at: When the server was started.
        error: Error message if server failed to start.
    """

    running: bool
    port: int | None = None
    started_at: datetime | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class StartResult:
    """Result of starting the metrics server.

    Attributes:
        success: Whether the server started successfully.
        port: Port the server is bound to.
        already_running: True if server was already running.
        error: Error message if failed.
    """

    success: bool
    port: int
    already_running: bool = False
    error: str | None = None


@dataclass
class MetricsService:
    """Service for metrics server operations.

    Provides high-level operations for managing the Prometheus metrics
    server used by CLI and other interfaces. Abstracts infrastructure
    details for Application-layer abstraction.

    Attributes:
        logger: Structured logger for observability.
        _server: Metrics server port implementation.
        _port: Current configured port.
        _started_at: Timestamp when server was started.

    Example:
        >>> service = MetricsService(logger=logger, _server=server_adapter)
        >>> result = service.start(port=8000)
        >>> if result.success:
        ...     logger.info("Metrics server started", port=result.port)
    """

    logger: LoggerPort
    _server: MetricsServerPort
    _port: int | None = field(default=None, repr=False)
    _started_at: datetime | None = field(default=None, repr=False)

    def _handle_start_error(
        self, port: int, e: Exception, fail_fast: bool
    ) -> StartResult:
        """Handle error during server start."""
        error_msg = str(e)
        self.logger.error(
            "Metrics server error",
            port=port,
            error=error_msg,
            error_type=type(e).__name__,
        )
        if fail_fast:
            raise MetricsServerError(
                port=port, reason=error_msg, original_error=e
            ) from e
        return StartResult(success=False, port=port, error=error_msg)

    def start(
        self,
        port: int = 8000,
        *,
        fail_fast: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> StartResult:
        """Start the Prometheus metrics server.

        Idempotent operation - safe to call multiple times.

        Args:
            port: Port to bind the HTTP server (default: 8000).
            fail_fast: If True, raise MetricsServerError on failure.
            retry_count: Number of retries for transient errors (default: 3).
            retry_delay: Delay between retries in seconds (default: 1.0).

        Returns:
            StartResult with operation status.

        Raises:
            MetricsServerError: If fail_fast=True and server cannot start.
        """
        self.logger.debug("Starting metrics server", port=port, fail_fast=fail_fast)

        if self._server.is_running():
            self.logger.debug("Metrics server already running")
            return StartResult(
                success=True, port=self._port or port, already_running=True
            )

        try:
            success = self._server.start(
                port=port,
                fail_fast=fail_fast,
                retry_count=retry_count,
                retry_delay=retry_delay,
            )
            if success:
                object.__setattr__(self, "_port", port)
                object.__setattr__(self, "_started_at", datetime.now(tz=UTC))
                self.logger.info("Metrics server started", port=port)
                return StartResult(success=True, port=port)

            self.logger.warning("Metrics server failed to start", port=port)
            return StartResult(success=False, port=port, error="Failed to bind port")
        except Exception as e:
            return self._handle_start_error(port, e, fail_fast)

    def get_status(self) -> MetricsServerStatus:
        """Get the current status of the metrics server.

        Returns:
            MetricsServerStatus with current state.

        Example:
            >>> status = service.get_status()
            >>> if status.running:
            ...     logger.info("Server running", port=status.port)
        """
        running = self._server.is_running()
        return MetricsServerStatus(
            running=running,
            port=self._port if running else None,
            started_at=self._started_at if running else None,
        )

    def is_running(self) -> bool:
        """Check if the metrics server is currently running.

        Returns:
            True if server is running, False otherwise.
        """
        return self._server.is_running()

================================================================================
File: pipeline_runner_service.py
Path: services\pipeline_runner_service.py
================================================================================
"""Pipeline runner service for universal pipeline execution.

Provides a high-level, interface-agnostic API for running pipelines.
Can be used from CLI, REST API, Airflow operators, or any other orchestrator.

Implements RULES.md §1.1 - Application Layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from bioetl.domain.context import (
    InputFilterContext,
    PipelineRunContext,
    VacuumConfig,
)
from bioetl.domain.types import RunID, RunType

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        LoggerPort,
        MetricsExtractorPort,
        RunnablePort,
        RunnerFactoryPort,
    )


class RunStatus(str, Enum):
    """Pipeline run completion status.

    Attributes:
        SUCCESS: Pipeline completed successfully.
        SHUTDOWN: Pipeline was gracefully shut down (SIGTERM/SIGINT).
        FAILED: Pipeline failed with an error.
        DRY_RUN: Dry-run mode, no actual execution performed.
    """

    SUCCESS = "success"
    SHUTDOWN = "shutdown"
    FAILED = "failed"
    DRY_RUN = "dry_run"


@dataclass(frozen=True)
class RunResult:
    """Result of pipeline execution.

    Provides execution metrics and status for orchestration layers.
    This is the unified return type for PipelineRunnerService.run()
    and enables programmatic access to execution results.

    Attributes:
        status: Completion status (success, shutdown, failed, dry_run).
        pipeline_name: Name of the executed pipeline.
        run_id: Unique identifier for this run.
        run_type: Type of run (incremental, backfill, rebuild).
        records_fetched: Total records retrieved from source.
        records_bronze: Records written to Bronze layer.
        records_silver: Records written to Silver layer.
        records_gold: Records written to Gold layer.
        records_quarantined: Records sent to quarantine.
        started_at: Timestamp when execution started.
        completed_at: Timestamp when execution completed.
        error_message: Error message if status is FAILED.
        error_type: Exception class name if status is FAILED.

    Example:
        >>> result = await service.run("chembl_activity")
        >>> if result.status == RunStatus.SUCCESS:
        ...     logger.info("pipeline_success", records_silver=result.records_silver)
        >>> elif result.status == RunStatus.FAILED:
        ...     logger.error("pipeline_failed", error_message=result.error_message)
    """

    status: RunStatus
    pipeline_name: str
    run_id: str
    run_type: str
    records_fetched: int = 0
    records_bronze: int = 0
    records_silver: int = 0
    records_gold: int = 0
    records_quarantined: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    completed_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    error_message: str | None = None
    error_type: str | None = None

    @property
    def duration_seconds(self) -> float:
        """Calculate execution duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def success_rate(self) -> float:
        """Calculate success rate (non-quarantined / fetched)."""
        if self.records_fetched == 0:
            return 1.0
        return (self.records_fetched - self.records_quarantined) / self.records_fetched

    @property
    def is_success(self) -> bool:
        """Check if run was successful (or dry_run)."""
        return self.status in (RunStatus.SUCCESS, RunStatus.DRY_RUN)


@dataclass(frozen=True)
class RunOptions:
    """Options for running a pipeline.

    These are the user-facing options that can be set via CLI, REST API,
    or any other orchestration interface.

    Attributes:
        run_type: Type of run (incremental, backfill, rebuild). Default: incremental.
        resume: Whether to resume from the last checkpoint.
        limit: Maximum number of records to process.
        dry_run: Preview mode without execution.
        input_csv: Path to CSV file with filter IDs.
        filter_column: Column name in CSV containing filter IDs.
        filter_field: API field name to filter by.
        filter_ids: Direct filter IDs (e.g., DOIs) without CSV file.
        vacuum_after_run: Enable automatic VACUUM after successful run.
        vacuum_retention_days: Minimum age of files to remove during VACUUM.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO.
        ignore_yaml_filter: Ignore input_filter from YAML config (for composite mode).
    """

    run_type: str = "incremental"
    resume: bool = False
    limit: int | None = None
    dry_run: bool = False
    input_csv: str | None = None
    filter_column: str | None = None
    filter_field: str | None = None
    filter_ids: tuple[str, ...] | None = None  # Direct filter IDs (no CSV)
    vacuum_after_run: bool | None = None
    vacuum_retention_days: int | None = None
    log_level: str = "INFO"
    ignore_yaml_filter: bool = False


class PipelineNotFoundError(ValueError):
    """Raised when a pipeline is not found in the registry."""

    def __init__(self, pipeline_name: str, available: list[str]) -> None:
        self.pipeline_name = pipeline_name
        self.available = available
        super().__init__(f"Unknown pipeline: {pipeline_name}. Available: {available}")


@dataclass
class PipelineRunnerService:
    """Application service for running pipelines.

    Provides a universal, interface-agnostic API for pipeline execution.
    Stateless and thread-safe - creates runners per call via injected factory.

    This service can be used from:
    - CLI (Click commands)
    - REST API (FastAPI/Flask endpoints)
    - Schedulers (Airflow operators, Prefect flows)
    - Python scripts (direct programmatic access)

    Attributes:
        runner_factory: Factory for creating pipeline runners (injected).
        metrics_extractor: Extractor for runner execution metrics (injected).
        logger: Structured logger for observability (injected).

    Example:
        >>> service = get_pipeline_runner_service()
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> result = await service.run("chembl_activity", options=options)
        >>> logger.info("pipeline_complete", records_silver=result.records_silver, duration_s=result.duration_seconds)
    """

    runner_factory: RunnerFactoryPort
    metrics_extractor: MetricsExtractorPort
    logger: LoggerPort

    async def run(
        self,
        pipeline_name: str,
        dry_run: bool = False,
        run_id: UUID | None = None,
        options: RunOptions | None = None,
    ) -> RunResult:
        """Run a pipeline with the given configuration.

        This is the main entry point for pipeline execution. It handles:
        - Pipeline validation and resolution
        - Configuration loading and merging
        - Run ID creation
        - Dry-run preview mode
        - Exception classification and result building

        Args:
            pipeline_name: Name of the pipeline to run (e.g., 'chembl_activity').
            dry_run: If True, only preview what would be done.
            run_id: Optional run ID. If None, a new UUID is generated.
            options: Optional RunOptions for detailed configuration.
                     If provided, takes precedence over individual parameters.

        Returns:
            RunResult with execution metrics and status.

        Raises:
            PipelineNotFoundError: If pipeline_name is not registered.

        Example:
            >>> result = await service.run("chembl_activity", dry_run=True)
            >>> if result.status == RunStatus.DRY_RUN:
            ...     logger.info("dry_run_complete", pipeline="chembl_activity")
        """
        started_at = datetime.now(tz=UTC)

        # Merge options with individual parameters
        effective_options = self._merge_options(options, dry_run)

        # Validate pipeline exists
        if not self.runner_factory.contains(pipeline_name):
            available = self.runner_factory.list_pipelines()
            raise PipelineNotFoundError(pipeline_name, available)

        # Generate run_id if not provided
        effective_run_id: RunID = cast(RunID, run_id or uuid4())

        self.logger.info(
            "Starting pipeline run",
            pipeline=pipeline_name,
            run_id=str(effective_run_id),
            run_type=effective_options.run_type,
            dry_run=effective_options.dry_run,
            limit=effective_options.limit,
        )

        # Handle dry-run mode
        if effective_options.dry_run:
            self.logger.info(
                "Dry-run mode: no execution performed",
                pipeline=pipeline_name,
                run_id=str(effective_run_id),
            )
            return RunResult(
                status=RunStatus.DRY_RUN,
                pipeline_name=pipeline_name,
                run_id=str(effective_run_id),
                run_type=effective_options.run_type,
                started_at=started_at,
                completed_at=datetime.now(tz=UTC),
            )

        # Build context and create runner
        context = self._build_context(
            pipeline_name, effective_run_id, effective_options
        )
        runner = self.runner_factory.create(context)

        # Execute pipeline
        return await self._execute_pipeline(
            runner=runner,
            pipeline_name=pipeline_name,
            run_id=effective_run_id,
            run_type=effective_options.run_type,
            started_at=started_at,
        )

    def list_pipelines(self) -> list[str]:
        """List all available pipeline names.

        Returns:
            Sorted list of registered pipeline names.
        """
        return self.runner_factory.list_pipelines()

    def validate_pipeline(self, pipeline_name: str) -> bool:
        """Check if a pipeline is registered.

        Args:
            pipeline_name: Name of the pipeline to check.

        Returns:
            True if pipeline exists, False otherwise.
        """
        return self.runner_factory.contains(pipeline_name)

    def _merge_options(
        self,
        options: RunOptions | None,
        dry_run: bool,
    ) -> RunOptions:
        """Merge individual parameters with RunOptions.

        Args:
            options: Optional RunOptions object.
            dry_run: Dry-run flag (fallback if options not provided).

        Returns:
            RunOptions with merged values.
        """
        if options is not None:
            return options

        return RunOptions(dry_run=dry_run)

    def _build_context(
        self,
        pipeline_name: str,
        run_id: RunID,
        options: RunOptions,
    ) -> PipelineRunContext:
        """Build PipelineRunContext from options.

        Args:
            pipeline_name: Name of the pipeline.
            run_id: Unique run identifier.
            options: Run options.

        Returns:
            PipelineRunContext ready for runner creation.
        """
        # Build InputFilterContext
        if options.input_csv:
            input_filter = InputFilterContext(
                enabled=True,
                source_path=options.input_csv,
                column_name=options.filter_column or "",
                filter_field=options.filter_field or "",
            )
        else:
            input_filter = InputFilterContext.disabled()

        # Build VacuumConfig
        vacuum = VacuumConfig(
            enabled=options.vacuum_after_run,
            retention_days=options.vacuum_retention_days or 7,
        )

        return PipelineRunContext(
            pipeline_name=pipeline_name,
            run_id=run_id,
            run_type=RunType(options.run_type),
            resume=options.resume,
            limit=options.limit,
            dry_run=options.dry_run,
            input_filter=input_filter,
            vacuum=vacuum,
            log_level=options.log_level,
        )

    async def _execute_pipeline(
        self,
        runner: RunnablePort,
        pipeline_name: str,
        run_id: RunID,
        run_type: str,
        started_at: datetime,
    ) -> RunResult:
        """Execute pipeline and build result.

        Args:
            runner: Pipeline runner to execute.
            pipeline_name: Name of the pipeline.
            run_id: Run identifier.
            run_type: Type of run.
            started_at: Execution start time.

        Returns:
            RunResult with execution outcome.
        """
        # Import inside method to avoid circular import:
        # application/services/__init__.py -> pipeline_runner_service.py
        # -> application/core/shutdown.py -> application/services/shutdown_service.py
        from bioetl.application.core.shutdown import PipelineShutdownError

        status = RunStatus.SUCCESS
        error_message: str | None = None
        error_type: str | None = None

        try:
            await runner.run()
            self.logger.info(
                "Pipeline completed successfully",
                pipeline=pipeline_name,
                run_id=str(run_id),
            )
        except PipelineShutdownError:
            status = RunStatus.SHUTDOWN
            self.logger.warning(
                "Pipeline was gracefully shut down",
                pipeline=pipeline_name,
                run_id=str(run_id),
            )
        except Exception as e:
            status = RunStatus.FAILED
            error_message = str(e)
            error_type = type(e).__name__
            self.logger.exception(
                "Pipeline failed with exception",
                pipeline=pipeline_name,
                run_id=str(run_id),
                error_type=error_type,
            )

        completed_at = datetime.now(tz=UTC)

        # Extract metrics from runner
        metrics = self.metrics_extractor.extract_metrics(runner)

        return RunResult(
            status=status,
            pipeline_name=pipeline_name,
            run_id=str(run_id),
            run_type=run_type,
            records_fetched=metrics.get("records_fetched", 0),
            records_bronze=metrics.get("records_bronze", 0),
            records_silver=metrics.get("records_silver", 0),
            records_gold=metrics.get("records_gold", 0),
            records_quarantined=metrics.get("records_quarantined", 0),
            started_at=started_at,
            completed_at=completed_at,
            error_message=error_message,
            error_type=error_type,
        )

================================================================================
File: quarantine_service.py
Path: services\quarantine_service.py
================================================================================
"""Quarantine service for administrative operations (Application layer).

Provides high-level quarantine management for CLI and other interfaces.
Uses QuarantinePort for actual persistence operations.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from bioetl.domain.types import QuarantineRecordStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, QuarantinePort


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    """Representation of a quarantined record.

    Attributes:
        error_code: Error code that caused quarantine, or None if unknown.
        payload: Original record data.
        batch_id: Bronze batch ID.
        pipeline: Pipeline name.
        ingestion_ts: When record was quarantined.
        metadata: Additional metadata.
    """

    error_code: str | None
    payload: dict[str, Any]
    batch_id: str | None
    pipeline: str
    ingestion_ts: datetime | None
    metadata: dict[str, Any]


@dataclass
class QuarantineService:
    """Service for administrative quarantine operations.

    Provides high-level operations for quarantine management
    used by CLI and other interfaces. Wraps QuarantinePort
    for Application-layer abstraction.

    Attributes:
        quarantine_port: Port for quarantine persistence.
        logger: Structured logger for observability.

    Example:
        >>> service = QuarantineService(quarantine_port=port, logger=logger)
        >>> records = await service.inspect("chembl_activity", limit=10)
        >>> for rec in records:
        ...     logger.info("quarantine_record", error_code=rec.error_code, payload=rec.payload)
    """

    quarantine_port: QuarantinePort
    logger: LoggerPort

    async def inspect(
        self,
        pipeline: str,
        limit: int = 100,
        error_code: str | None = None,
    ) -> list[QuarantineRecord]:
        """Inspect quarantined records for a pipeline.

        Args:
            pipeline: Pipeline name to inspect.
            limit: Maximum number of records to return.
            error_code: Optional filter by error code.

        Returns:
            List of QuarantineRecord objects.
        """
        self.logger.debug(
            "Inspecting quarantine",
            pipeline=pipeline,
            limit=limit,
            error_code=error_code,
        )

        raw_records = await self.quarantine_port.inspect(
            pipeline=pipeline,
            limit=limit,
            error_code=error_code,
        )

        records = [
            QuarantineRecord(
                error_code=rec.get("error_code"),
                payload=rec.get("payload", {}),
                batch_id=rec.get("bronze_batch_id"),
                pipeline=pipeline,
                ingestion_ts=rec.get("ingestion_ts"),
                metadata=rec.get("metadata", {}),
            )
            for rec in raw_records
        ]

        self.logger.info(
            "Inspected quarantine",
            pipeline=pipeline,
            record_count=len(records),
        )

        return records

    async def get_stats(self, pipeline: str) -> dict[str, Any]:
        """Get statistics about quarantined records.

        Args:
            pipeline: Pipeline name.

        Returns:
            Dictionary with quarantine statistics by error code.
        """
        self.logger.debug("Getting quarantine stats", pipeline=pipeline)

        stats = await self.quarantine_port.get_stats(pipeline)

        self.logger.info(
            "Got quarantine stats",
            pipeline=pipeline,
            stats=stats,
        )

        return stats

    def replay(
        self,
        pipeline: str,
        error_code: str | None = None,
        max_age_days: int = 7,
    ) -> list[dict[str, Any]]:
        """Replay quarantine records for reprocessing.

        Retrieves quarantined records that match the filter criteria
        for reprocessing by the pipeline.

        Args:
            pipeline: Pipeline name to filter by.
            error_code: Optional error code to filter by.
            max_age_days: Maximum age of records to replay (default 7).

        Returns:
            List of quarantine records suitable for replay.
        """
        now = datetime.now(tz=UTC)
        self.logger.info(
            "Replaying quarantine records",
            pipeline=pipeline,
            error_code=error_code,
            max_age_days=max_age_days,
        )

        records = list(
            self.quarantine_port.replay(
                pipeline=pipeline,
                error_code=error_code,
                max_age_days=max_age_days,
                now=now,
            )
        )

        self.logger.info(
            "Replay records retrieved",
            pipeline=pipeline,
            record_count=len(records),
        )

        return records

    def mark_as_reprocessed(
        self,
        records: list[dict[str, Any]],
    ) -> int:
        """Mark replay records as reprocessed.

        Updates the status of records to REPROCESSED after successful replay.

        Args:
            records: List of records from replay() to mark as reprocessed.

        Returns:
            Number of records successfully marked.
        """
        count = 0
        for rec in records:
            payload_hash = rec.get("payload_hash")
            if payload_hash and self.quarantine_port.update_status(
                payload_hash, QuarantineRecordStatus.REPROCESSED
            ):
                count += 1

        self.logger.info(
            "Marked records as reprocessed",
            record_count=count,
        )
        return count

    def purge(
        self,
        pipeline: str,
        older_than_days: int = 30,
    ) -> int:
        """Purge old quarantine records.

        Removes quarantine records older than the specified age.
        Implements RULES.md §2.6 - 30-day retention policy.

        Args:
            pipeline: Pipeline name.
            older_than_days: Records older than this will be purged (default 30).

        Returns:
            Number of records deleted.
        """
        now = datetime.now(tz=UTC)
        self.logger.info(
            "Purging old quarantine records",
            pipeline=pipeline,
            older_than_days=older_than_days,
        )

        count = self.quarantine_port.purge(
            pipeline=pipeline,
            older_than_days=older_than_days,
            now=now,
        )

        self.logger.info(
            "Purged quarantine records",
            pipeline=pipeline,
            records_purged=count,
        )

        return count

    def update_status(
        self,
        payload_hash: str,
        new_status: QuarantineRecordStatus,
    ) -> bool:
        """Update DQ status for a quarantined record.

        Used to mark records as IGNORED, REVIEWED, or REPROCESSED
        after manual inspection.

        Args:
            payload_hash: Hash of the payload to identify the record.
            new_status: New status to set.

        Returns:
            True if record was found and updated, False otherwise.
        """
        self.logger.debug(
            "Updating quarantine status",
            payload_hash=payload_hash,
            new_status=new_status.value,
        )

        success = self.quarantine_port.update_status(payload_hash, new_status)

        if success:
            self.logger.info(
                "Updated quarantine status",
                payload_hash=payload_hash,
                new_status=new_status.value,
            )
        else:
            self.logger.warning(
                "Failed to update quarantine status - record not found",
                payload_hash=payload_hash,
            )

        return success

    async def aclose(self) -> None:
        """Close the service and release resources."""
        await self.quarantine_port.aclose()

================================================================================
File: shutdown_service.py
Path: services\shutdown_service.py
================================================================================
"""Shutdown Service for graceful pipeline termination.

This service consolidates all shutdown-related logic in one place,
implementing ADR-008 graceful shutdown strategy:
1. Stop fetching new records
2. Wait for current batch to complete
3. Save checkpoint
4. Release lock
5. Emit shutdown metrics

Follows RULES.md §5.3: At-Least-Once + deduplication guarantee.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort


class ShutdownReason(Enum):
    """Enumeration of shutdown reasons for metrics and logging."""

    SIGNAL_SIGTERM = "SIGTERM"
    SIGNAL_SIGINT = "SIGINT"
    LOCK_LOST = "lock_lost"
    DQ_THRESHOLD_EXCEEDED = "dq_threshold"
    TIMEOUT = "timeout"
    USER_REQUESTED = "user_requested"
    UNKNOWN = "unknown"


@dataclass
class ShutdownService:
    """Unified service for coordinating graceful shutdown.

    This service implements ShutdownPort and provides centralized
    shutdown coordination for all pipeline components.

    Responsibilities:
    - Maintain shutdown state (requested flag, asyncio.Event)
    - Provide async waiting for shutdown completion
    - Track shutdown reason and timing for observability
    - Emit metrics on shutdown initiation and completion

    The service does NOT directly manage resources (locks, checkpoints).
    Resource cleanup is delegated to their respective managers via
    context managers and the shutdown flag.

    Example:
        shutdown_service = ShutdownService(logger=logger, metrics=metrics)

        # In signal handler
        await shutdown_service.initiate_shutdown("SIGTERM received")

        # In executor loop
        if shutdown_service.is_shutting_down():
            await checkpoint_manager.save()
            break

        # Wait for graceful completion
        completed = await shutdown_service.wait_for_completion(timeout=30.0)

    """

    logger: LoggerPort
    metrics: MetricsPort | None = None

    # Internal state (not exposed via __init__)
    _requested: bool = field(default=False, init=False)
    _event: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    _completion_event: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    _reason: ShutdownReason = field(default=ShutdownReason.UNKNOWN, init=False)
    _reason_detail: str = field(default="", init=False)

    def is_shutting_down(self) -> bool:
        """Check if shutdown has been requested.

        Returns:
            True if shutdown was initiated, False otherwise.

        Note:
            Thread-safe via asyncio.Event internal locking.
        """
        return self._requested

    @property
    def reason(self) -> ShutdownReason:
        """Get the reason for shutdown.

        Returns:
            ShutdownReason enum value, or UNKNOWN if not yet initiated.
        """
        return self._reason

    async def initiate_shutdown(self, reason: str) -> None:
        """Initiate graceful shutdown with a reason.

        This method:
        1. Sets the shutdown flag (idempotent)
        2. Parses reason to ShutdownReason enum
        3. Notifies waiting components via asyncio.Event
        4. Logs the shutdown initiation
        5. Emits shutdown_initiated metric

        Args:
            reason: Human-readable reason for shutdown (e.g., "signal 15",
                "Lock lost", "DQ threshold exceeded").

        Note:
            Idempotent - multiple calls have no additional effect.
            First call sets the reason, subsequent calls are ignored.
        """
        if self._requested:
            return  # Already shutting down, ignore

        self._requested = True
        self._reason = self._parse_reason(reason)
        self._reason_detail = reason
        self._event.set()

        self.logger.warning(
            "Shutdown initiated",
            reason=reason,
            reason_type=self._reason.value,
        )

        if self.metrics is not None:
            self.metrics.increment_counter(
                "shutdown_initiated",
                value=1,
                labels={"reason": self._reason.value},
            )

    def request(self) -> None:
        """Synchronous shutdown request (backward compatibility).

        Use initiate_shutdown() for async contexts with reason tracking.
        This method exists for compatibility with existing ShutdownSignal
        usage patterns.

        Note:
            Does not emit metrics or log detailed reason.
        """
        if not self._requested:
            self._requested = True
            self._reason = ShutdownReason.UNKNOWN
            self._event.set()

    async def wait(self) -> None:
        """Wait until shutdown is requested.

        Blocks until initiate_shutdown() or request() is called.
        Use with asyncio.wait_for() for timeout-based waiting.

        This is backward-compatible with ShutdownSignal.wait().
        """
        await self._event.wait()

    async def wait_for_completion(self, timeout: float) -> bool:
        """Wait for shutdown completion with timeout.

        Blocks until mark_completed() is called or timeout expires.

        Args:
            timeout: Maximum seconds to wait for completion.

        Returns:
            True if shutdown completed within timeout, False if timeout expired.
        """
        try:
            await asyncio.wait_for(self._completion_event.wait(), timeout=timeout)
            return True
        except TimeoutError:
            self.logger.warning(
                "Shutdown completion timeout",
                timeout_seconds=timeout,
            )
            return False

    def mark_completed(self) -> None:
        """Mark shutdown as completed.

        Called by the runner after all cleanup is done.
        Signals wait_for_completion() to return.
        """
        self._completion_event.set()

        if self.metrics is not None:
            self.metrics.increment_counter(
                "shutdown_completed",
                value=1,
                labels={"reason": self._reason.value},
            )

    def reset(self) -> None:
        """Reset service for reuse (e.g., in tests).

        Warning: Only use in tests or when you're certain no components
        are currently checking the shutdown state.
        """
        self._requested = False
        self._event.clear()
        self._completion_event.clear()
        self._reason = ShutdownReason.UNKNOWN
        self._reason_detail = ""

    @staticmethod
    def _parse_reason(reason: str) -> ShutdownReason:
        """Parse reason string to ShutdownReason enum.

        Args:
            reason: Human-readable shutdown reason.

        Returns:
            Matching ShutdownReason, or UNKNOWN if not recognized.
        """
        reason_lower = reason.lower()

        # Pattern matching table: (keywords, result)
        patterns: list[tuple[tuple[str, ...], ShutdownReason]] = [
            (("sigterm", "signal 15"), ShutdownReason.SIGNAL_SIGTERM),
            (("sigint", "signal 2"), ShutdownReason.SIGNAL_SIGINT),
            (("timeout",), ShutdownReason.TIMEOUT),
            (("user",), ShutdownReason.USER_REQUESTED),
        ]

        for keywords, result in patterns:
            if any(kw in reason_lower for kw in keywords):
                return result

        # Special case: requires both "lock" and "lost"
        if "lock" in reason_lower and "lost" in reason_lower:
            return ShutdownReason.LOCK_LOST

        # DQ threshold check
        if "dq" in reason_lower or "threshold" in reason_lower:
            return ShutdownReason.DQ_THRESHOLD_EXCEEDED

        return ShutdownReason.UNKNOWN


class PipelineShutdownError(Exception):
    """Raised when pipeline receives shutdown signal.

    This exception signals that the pipeline should gracefully terminate,
    saving any pending checkpoints before exit.

    Attributes:
        reason: The reason for shutdown.
        shutdown_service: Optional reference to the ShutdownService.
    """

    def __init__(
        self,
        message: str = "Pipeline shutdown requested",
        *,
        reason: ShutdownReason | None = None,
    ) -> None:
        """Initialize PipelineShutdownError.

        Args:
            message: Error message describing the shutdown cause.
            reason: Optional ShutdownReason enum value.
        """
        super().__init__(message)
        self.reason = reason or ShutdownReason.UNKNOWN


__all__ = [
    "PipelineShutdownError",
    "ShutdownReason",
    "ShutdownService",
]

================================================================================
File: vacuum_service.py
Path: services\vacuum_service.py
================================================================================
"""Vacuum service for batch Delta table maintenance.

Provides high-level vacuum operations across multiple tables.
This service belongs to Application layer and orchestrates vacuum
operations without CLI-specific formatting concerns.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.ports import LoggerPort


#: Type alias for table collector callable.
#: This defines the interface for collecting tables from the pipeline registry.
#: The implementation lives in the composition layer to maintain proper
#: dependency direction (application -> domain <- composition).
TableCollectorPort = Callable[[str], list[tuple[str, str]]]
"""Protocol for collecting tables for vacuum operations.

A callable that takes a layer name ("all", "silver", or "gold") and
returns a list of (table_name, layer) tuples.
"""


@dataclass(frozen=True, slots=True)
class TableVacuumResult:
    """Result of vacuum operation on a single table.

    Attributes:
        table_name: Name of the vacuumed table.
        layer: Medallion layer (silver/gold).
        files_removed: Number of files removed.
        error: Error message if vacuum failed, None otherwise.
    """

    table_name: str
    layer: str
    files_removed: int
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if vacuum succeeded."""
        return self.error is None


@dataclass(frozen=True, slots=True)
class VacuumAllResult:
    """Result of vacuum-all operation across multiple tables.

    Attributes:
        results: List of per-table results.
        total_files_removed: Sum of files removed across all tables.
        failed_tables: List of table names that failed.
        dry_run: Whether this was a dry run.
    """

    results: tuple[TableVacuumResult, ...]
    dry_run: bool

    @property
    def total_files_removed(self) -> int:
        """Get total files removed across all tables."""
        return sum(r.files_removed for r in self.results)

    @property
    def failed_tables(self) -> list[str]:
        """Get list of failed table identifiers."""
        return [f"{r.layer}/{r.table_name}" for r in self.results if r.error]

    @property
    def success_count(self) -> int:
        """Count of successfully vacuumed tables."""
        return sum(1 for r in self.results if r.success)


@dataclass
class VacuumService:
    """Service for batch vacuum operations on Delta tables.

    Responsibilities:
    - Collect tables from pipeline registry for vacuum-all (via injected collector)
    - Orchestrate vacuum operations across multiple tables
    - Track and report results

    This service encapsulates business logic that was previously
    in CLI (_collect_vacuum_tables, _vacuum_table).

    Attributes:
        lifecycle: MedallionLifecycleService for individual vacuum ops.
        logger: Structured logger for observability.
        table_collector: Injected function for collecting tables from registry.

    Example:
        >>> def collect_tables(layer: str) -> list[tuple[str, str]]:
        ...     # Implementation in composition layer
        ...     return [("chembl_activity", "silver"), ("chembl_activity", "gold")]
        >>> service = VacuumService(
        ...     lifecycle=lifecycle,
        ...     logger=logger,
        ...     table_collector=collect_tables,
        ... )
        >>> tables = service.collect_tables(layer="all")
        >>> result = await service.vacuum_all(tables, retention_days=7)
        >>> logger.info("vacuum_complete", files_removed=result.total_files_removed)
    """

    lifecycle: MedallionLifecycleService
    logger: LoggerPort
    table_collector: TableCollectorPort = field(repr=False)

    def collect_tables(self, layer: str = "all") -> list[tuple[str, str]]:
        """Collect tables from all registered pipelines.

        Delegates to the injected table_collector function which queries
        the pipeline registry in the composition layer.

        Args:
            layer: Which layer to collect - "all", "silver", or "gold".

        Returns:
            List of (table_name, layer) tuples sorted alphabetically.
        """
        return self.table_collector(layer)

    async def vacuum_table(
        self,
        table_name: str,
        layer: str,
        retention_days: int,
        dry_run: bool,
    ) -> TableVacuumResult:
        """Vacuum a single table and return structured result.

        Args:
            table_name: Name of the table to vacuum.
            layer: Medallion layer (silver/gold).
            retention_days: Minimum age of files to remove.
            dry_run: If True, only report what would be removed.

        Returns:
            TableVacuumResult with operation outcome.
        """
        try:
            files_removed = await self.lifecycle.vacuum(
                table=table_name,
                retention_days=retention_days,
                dry_run=dry_run,
            )
            return TableVacuumResult(
                table_name=table_name,
                layer=layer,
                files_removed=files_removed,
                error=None,
            )
        except Exception as e:
            self.logger.error(
                "Vacuum failed for table",
                table_name=table_name,
                layer=layer,
                error=str(e),
            )
            return TableVacuumResult(
                table_name=table_name,
                layer=layer,
                files_removed=0,
                error=str(e),
            )

    async def vacuum_all(
        self,
        tables: list[tuple[str, str]],
        retention_days: int,
        dry_run: bool,
    ) -> VacuumAllResult:
        """Vacuum multiple tables and aggregate results.

        Args:
            tables: List of (table_name, layer) tuples to vacuum.
            retention_days: Minimum age of files to remove.
            dry_run: If True, only report what would be removed.

        Returns:
            VacuumAllResult with aggregated statistics.
        """
        self.logger.info(
            "Starting vacuum-all operation",
            table_count=len(tables),
            retention_days=retention_days,
            dry_run=dry_run,
        )

        results: list[TableVacuumResult] = []
        for table_name, layer in tables:
            result = await self.vacuum_table(
                table_name=table_name,
                layer=layer,
                retention_days=retention_days,
                dry_run=dry_run,
            )
            results.append(result)

        vacuum_result = VacuumAllResult(
            results=tuple(results),
            dry_run=dry_run,
        )

        self.logger.info(
            "Vacuum-all completed",
            total_files_removed=vacuum_result.total_files_removed,
            success_count=vacuum_result.success_count,
            failed_count=len(vacuum_result.failed_tables),
            dry_run=dry_run,
        )

        return vacuum_result

