"""File-backed lifecycle planner for control-plane artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleApplyResult,
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactLifecyclePolicy,
    ControlPlaneArtifactRef,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_planning import (
    _iter_artifact_refs,
    _resolve_protected_refs,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort

__all__ = ["FileControlPlaneArtifactLifecycleStore"]


@dataclass(slots=True)
class FileControlPlaneArtifactLifecycleStore:
    """Plan and apply lifecycle decisions for file-backed control-plane artifacts."""

    base_path: Path
    logger: LoggerPort | None = None
    metrics: MetricsPort | None = None

    def plan(
        self,
        policy: ControlPlaneArtifactLifecyclePolicy,
        *,
        dry_run: bool = True,
    ) -> ControlPlaneArtifactLifecyclePlan:
        """Build a deterministic retention plan without mutating files."""
        cutoff = policy.now - timedelta(days=policy.retention_days)
        protected_refs = _resolve_protected_refs(
            base_path=self.base_path,
            policy=policy,
            cutoff=cutoff,
        )
        artifacts = tuple(
            sorted(
                _iter_artifact_refs(
                    base_path=self.base_path,
                    cutoff=cutoff,
                    protected_refs=protected_refs,
                ),
                key=lambda ref: (ref.surface.value, ref.path),
            )
        )
        return ControlPlaneArtifactLifecyclePlan(
            generated_at=policy.now,
            cutoff=cutoff,
            dry_run=dry_run,
            artifacts=artifacts,
        )

    def apply(
        self,
        plan: ControlPlaneArtifactLifecyclePlan,
    ) -> ControlPlaneArtifactLifecycleApplyResult:
        """Delete files selected by a previously generated lifecycle plan."""
        deleted_paths: list[str] = []
        missing_paths: list[str] = []
        if plan.dry_run:
            self._emit_apply_summary(
                plan=plan,
                deleted_paths=(),
                missing_paths=(),
            )
            return ControlPlaneArtifactLifecycleApplyResult(
                plan=plan,
                deleted_paths=(),
                missing_paths=(),
            )
        for artifact in plan.artifacts:
            if not artifact.delete_selected:
                continue
            path = Path(artifact.path)
            if not path.exists():
                missing_paths.append(artifact.path)
                continue
            path.unlink()
            deleted_paths.append(artifact.path)
            self._emit_deleted_artifact(artifact)
        self._emit_apply_summary(
            plan=plan,
            deleted_paths=tuple(deleted_paths),
            missing_paths=tuple(missing_paths),
        )
        return ControlPlaneArtifactLifecycleApplyResult(
            plan=plan,
            deleted_paths=tuple(deleted_paths),
            missing_paths=tuple(missing_paths),
        )

    def _emit_deleted_artifact(self, artifact: ControlPlaneArtifactRef) -> None:
        if self.logger is not None:
            self.logger.info(
                "control_plane_lifecycle_artifact_deleted",
                surface=artifact.surface.value,
                artifact_id=artifact.artifact_id,
                path=artifact.path,
                reason=artifact.reason,
            )
        if self.metrics is not None:
            self.metrics.increment_counter(
                "bioetl_control_plane_lifecycle_deleted_total",
                1,
                labels={"surface": artifact.surface.value},
            )

    def _emit_apply_summary(
        self,
        *,
        plan: ControlPlaneArtifactLifecyclePlan,
        deleted_paths: tuple[str, ...],
        missing_paths: tuple[str, ...],
    ) -> None:
        if self.logger is not None:
            self.logger.info(
                "control_plane_lifecycle_apply_summary",
                dry_run=plan.dry_run,
                cutoff=plan.cutoff.isoformat(),
                delete_count=plan.delete_count,
                retain_count=plan.retain_count,
                deleted_count=len(deleted_paths),
                missing_count=len(missing_paths),
            )
        if self.metrics is not None:
            self.metrics.set_gauge(
                "bioetl_control_plane_lifecycle_delete_candidates",
                float(plan.delete_count),
            )
            self.metrics.increment_counter(
                "bioetl_control_plane_lifecycle_apply_total",
                1,
                labels={"dry_run": str(plan.dry_run).lower()},
            )
