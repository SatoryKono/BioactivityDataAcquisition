"""Policy helpers for local control-plane archive after a successful run."""

from __future__ import annotations

from pathlib import Path

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunOptions,
    RunResult,
)

DEFAULT_CONTROL_PLANE_ARCHIVE_ROOT = Path("reports/local/gf14-archive/verified")


def resolve_control_plane_archive_root(archive_root: Path | None) -> Path:
    """Use an explicit root when set; otherwise the reports-local default."""
    if archive_root is not None:
        return Path(archive_root)
    return DEFAULT_CONTROL_PLANE_ARCHIVE_ROOT


def should_archive_control_plane(result: RunResult, options: RunOptions | None) -> bool:
    """Archive only successful, non-dry-run pipeline completions with a manifest."""
    if options is not None and (options.no_control_plane_archive or options.dry_run):
        return False
    return (
        result.status is PipelineRunResult.SUCCESS
        and bool(result.manifest_id)
        and bool(result.run_id)
    )
