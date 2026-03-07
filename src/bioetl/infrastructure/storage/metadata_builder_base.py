"""Shared base helpers for metadata builders."""

from __future__ import annotations

from datetime import datetime
from platform import node as hostname
from platform import python_version
from typing import TYPE_CHECKING

from bioetl.domain.types import JsonDict
from bioetl.domain.version import get_version as _get_bioetl_version

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import (
        DQSummary,
        EnvironmentMetadata,
        LineageMetadata,
        PipelineMetadata,
        RuntimeMetadata,
    )


def _get_git_commit_cached() -> str | None:
    """Get git commit hash directly via subprocess."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def _parse_table_name(table_name: str) -> tuple[str, str]:
    """Parse table name into provider and entity components."""
    if "." in table_name:
        parts = table_name.split(".")
        return parts[0], parts[1] if len(parts) > 1 else parts[0]
    if "/" in table_name:
        parts = table_name.split("/")
        return (parts[0] if len(parts) > 1 else "composite"), parts[-1]
    if "_" in table_name:
        parts = table_name.split("_", 1)
        return parts[0], parts[1] if len(parts) > 1 else parts[0]
    return "unknown", table_name if table_name else "unknown"


class _MetadataBuilderBase:
    """Shared initialization for Silver/Gold metadata builders."""

    def __init__(
        self,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
    ) -> None:
        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()

    def _build_composite_runtime_pipeline_lineage(
        self,
        *,
        table_name: str,
        now: datetime,
        run_id: str | None,
        sources_used: list[str] | None,
    ) -> tuple[RuntimeMetadata, PipelineMetadata, LineageMetadata]:
        """Build runtime/pipeline/lineage metadata for composite merged outputs."""
        from bioetl.domain.models.metadata import (
            LineageMetadata,
            PipelineMetadata,
            RuntimeMetadata,
            RunTypeEnum,
        )

        provider_name, entity_name = _parse_table_name(table_name)
        runtime = RuntimeMetadata(
            run_id=run_id or "",
            run_type=RunTypeEnum.INCREMENTAL,
            started_at_utc=now,
            completed_at_utc=now,
        )
        pipeline = PipelineMetadata(
            name=f"composite_{entity_name}",
            provider=provider_name,
            entity=entity_name,
            version=_get_bioetl_version(),
            git_commit=_get_git_commit_cached(),
        )
        lineage = LineageMetadata(
            bronze_paths=[],
            transform_version=self._transform_version or "1.0.0",
            transform_steps=(
                list(self._transform_steps) if self._transform_steps else ["merge"]
            ),
            source_tables=dict.fromkeys(sources_used or [], 0),
        )
        return runtime, pipeline, lineage

    @staticmethod
    def _build_merged_dq_summary(
        records: list[JsonDict],  # Any: heterogeneous metadata values
    ) -> DQSummary:
        """Build DQ summary for merged records."""
        from bioetl.domain.models.metadata import DQSummary

        return DQSummary(
            total_records=len(records),
            valid_records=len(records),
            error_records=0,
            error_rate=0.0,
        )

    @staticmethod
    def _build_environment_metadata() -> EnvironmentMetadata:
        """Build environment metadata for current process."""
        from bioetl.domain.models.metadata import EnvironmentMetadata

        return EnvironmentMetadata(
            hostname=hostname(),
            python_version=python_version(),
            bioetl_version=_get_bioetl_version(),
        )


__all__ = ["_MetadataBuilderBase", "_parse_table_name"]
