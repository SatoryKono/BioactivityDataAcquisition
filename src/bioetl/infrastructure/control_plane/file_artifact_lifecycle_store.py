"""File-backed lifecycle planner for control-plane artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleApplyResult,
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactLifecyclePolicy,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactSurface,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort

__all__ = ["FileControlPlaneArtifactLifecycleStore"]

_INDEX_DIR_NAMES = {
    "_by_fragment_id",
    "_by_manifest_id",
    "_by_node_id",
    "_by_run_id",
    "_occurrences",
}


@dataclass(frozen=True, slots=True)
class _ProtectedRefs:
    """Resolved reference sets that block lifecycle deletion."""

    manifest_ids: frozenset[str]
    run_ids: frozenset[str]
    input_snapshot_ids: frozenset[str]
    effective_config_artifact_ids: frozenset[str]
    lineage_fragment_ids: frozenset[str]


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
        protected_refs = self._resolve_protected_refs(policy=policy, cutoff=cutoff)
        artifacts = tuple(
            sorted(
                self._iter_artifact_refs(cutoff=cutoff, protected_refs=protected_refs),
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

    def _extract_manifest_refs(
        self, cutoff: datetime, state: dict[str, set[str]]
    ) -> None:
        """Extract live references from recent manifest artifacts."""
        for manifest_path in self._iter_surface_files(
            ControlPlaneArtifactSurface.RUN_MANIFEST
        ):
            if manifest_path.parent.name in _INDEX_DIR_NAMES:
                continue
            payload = _read_json_object_or_empty(manifest_path)
            if not payload:
                continue
            created_at = _resolve_payload_or_file_time(manifest_path, payload)
            if created_at is not None and created_at < cutoff:
                continue
            state["manifest_ids"].add(
                str(payload.get("manifest_id") or manifest_path.stem)
            )
            if (run_id := _optional_text(payload.get("run_id"))) is not None:
                state["run_ids"].add(run_id)
            if (
                replay_id := _optional_text(payload.get("replay_of_manifest_id"))
            ) is not None:
                state["manifest_ids"].add(replay_id)
            if (artifact_id := _effective_config_artifact_id(payload)) is not None:
                state["effective_config_artifact_ids"].add(artifact_id)
            state["input_snapshot_ids"].update(_input_snapshot_ids(payload))

    def _extract_checkpoint_refs(
        self, cutoff: datetime, state: dict[str, set[str]]
    ) -> None:
        """Extract live references from recent checkpoint artifacts."""
        for checkpoint_path in self._iter_surface_files(
            ControlPlaneArtifactSurface.CHECKPOINT
        ):
            payload = _read_json_object_or_empty(checkpoint_path)
            if not payload:
                continue
            created_at = _resolve_payload_or_file_time(checkpoint_path, payload)
            if created_at is not None and created_at < cutoff:
                continue
            if (run_id := _payload_text(payload, "run_id")) is not None:
                state["run_ids"].add(run_id)
            if (manifest_id := _payload_text(payload, "manifest_id")) is not None:
                state["manifest_ids"].add(manifest_id)
            if (
                artifact_id := _payload_text(payload, "effective_config_artifact_id")
            ) is not None:
                state["effective_config_artifact_ids"].add(artifact_id)

    def _extract_lineage_refs(self, state: dict[str, set[str]]) -> None:
        """Extract live references from active lineage fragments."""
        frozen_manifests = frozenset(state["manifest_ids"])
        frozen_runs = frozenset(state["run_ids"])
        for fragment_path in self._lineage_fragment_files():
            payload = _read_json_object_or_empty(fragment_path)
            if not payload:
                continue
            if _manifest_or_run_is_protected(
                payload, manifest_ids=frozen_manifests, run_ids=frozen_runs
            ):
                state["lineage_fragment_ids"].update(
                    _lineage_fragment_id_candidates(payload)
                )

    def _resolve_protected_refs(
        self,
        *,
        policy: ControlPlaneArtifactLifecyclePolicy,
        cutoff: datetime,
    ) -> _ProtectedRefs:
        """Resolve explicit and live-reference protections before planning."""
        state = {
            "manifest_ids": set(policy.protected_manifest_ids),
            "run_ids": set(policy.protected_run_ids),
            "input_snapshot_ids": set(policy.protected_input_snapshot_ids),
            "effective_config_artifact_ids": set(
                policy.protected_effective_config_artifact_ids
            ),
            "lineage_fragment_ids": set(policy.protected_lineage_fragment_ids),
        }
        self._extract_manifest_refs(cutoff, state)
        self._extract_checkpoint_refs(cutoff, state)
        self._extract_lineage_refs(state)

        return _ProtectedRefs(
            manifest_ids=frozenset(state["manifest_ids"]),
            run_ids=frozenset(state["run_ids"]),
            input_snapshot_ids=frozenset(state["input_snapshot_ids"]),
            effective_config_artifact_ids=frozenset(
                state["effective_config_artifact_ids"]
            ),
            lineage_fragment_ids=frozenset(state["lineage_fragment_ids"]),
        )

    def _iter_artifact_refs(
        self,
        *,
        cutoff: datetime,
        protected_refs: _ProtectedRefs,
    ) -> tuple[ControlPlaneArtifactRef, ...]:
        refs: list[ControlPlaneArtifactRef] = []
        for surface in ControlPlaneArtifactSurface:
            for path in self._iter_surface_files(surface):
                refs.append(
                    self._build_artifact_ref(
                        surface=surface,
                        path=path,
                        cutoff=cutoff,
                        protected_refs=protected_refs,
                    )
                )
        return tuple(refs)

    def _build_artifact_ref(
        self,
        *,
        surface: ControlPlaneArtifactSurface,
        path: Path,
        cutoff: datetime,
        protected_refs: _ProtectedRefs,
    ) -> ControlPlaneArtifactRef:
        payload = _read_json_object_or_empty(path)
        created_at = _resolve_payload_or_file_time(path, payload)
        protected_by = self._protected_by(
            surface=surface,
            path=path,
            payload=payload,
            protected_refs=protected_refs,
        )
        stale = created_at is not None and created_at < cutoff
        decision = (
            ControlPlaneArtifactLifecycleDecision.DELETE
            if stale and not protected_by
            else ControlPlaneArtifactLifecycleDecision.RETAIN
        )
        reason = _resolve_lifecycle_reason(stale=stale, protected_by=protected_by)
        return ControlPlaneArtifactRef(
            surface=surface,
            path=str(path),
            artifact_id=_artifact_id(surface=surface, path=path, payload=payload),
            decision=decision,
            reason=reason,
            created_at=created_at,
            protected_by=protected_by,
        )

    def _protected_by_run_manifest_or_ledger(
        self,
        path: Path,
        payload: dict[str, object],
        protected_refs: _ProtectedRefs,
        reasons: list[str],
    ) -> None:
        manifest_id = str(payload.get("manifest_id") or path.stem)
        run_id = _optional_text(payload.get("run_id"))
        if manifest_id in protected_refs.manifest_ids:
            reasons.append(f"manifest:{manifest_id}")
        if run_id in protected_refs.run_ids:
            reasons.append(f"run:{run_id}")
        indexed_run_id = _indexed_stem(path)
        if indexed_run_id in protected_refs.run_ids:
            reasons.append(f"run:{indexed_run_id}")

    def _protected_by_effective_config(
        self,
        path: Path,
        payload: dict[str, object],
        protected_refs: _ProtectedRefs,
        reasons: list[str],
    ) -> None:
        artifact_id = str(payload.get("artifact_id") or path.stem)
        run_id = _optional_text(payload.get("run_id")) or _indexed_stem(path)
        if artifact_id in protected_refs.effective_config_artifact_ids:
            reasons.append(f"effective_config:{artifact_id}")
        if run_id in protected_refs.run_ids:
            reasons.append(f"run:{run_id}")

    def _protected_by_lineage(
        self,
        path: Path,
        payload: dict[str, object],
        protected_refs: _ProtectedRefs,
        reasons: list[str],
    ) -> None:
        for fragment_id in _lineage_fragment_id_candidates(payload) or (path.stem,):
            if fragment_id in protected_refs.lineage_fragment_ids:
                reasons.append(f"lineage:{fragment_id}")
        if _manifest_or_run_is_protected(
            payload,
            manifest_ids=protected_refs.manifest_ids,
            run_ids=protected_refs.run_ids,
        ):
            manifest_id = _optional_text(payload.get("manifest_id"))
            run_id = _optional_text(payload.get("run_id"))
            if manifest_id is not None:
                reasons.append(f"manifest:{manifest_id}")
            if run_id is not None:
                reasons.append(f"run:{run_id}")

    def _protected_by_checkpoint(
        self,
        payload: dict[str, object],
        protected_refs: _ProtectedRefs,
        reasons: list[str],
    ) -> None:
        run_id = _payload_text(payload, "run_id")
        manifest_id = _payload_text(payload, "manifest_id")
        artifact_id = _payload_text(payload, "effective_config_artifact_id")
        if run_id in protected_refs.run_ids:
            reasons.append(f"run:{run_id}")
        if manifest_id in protected_refs.manifest_ids:
            reasons.append(f"manifest:{manifest_id}")
        if artifact_id in protected_refs.effective_config_artifact_ids:
            reasons.append(f"effective_config:{artifact_id}")

    def _protected_by(
        self,
        *,
        surface: ControlPlaneArtifactSurface,
        path: Path,
        payload: dict[str, object],
        protected_refs: _ProtectedRefs,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if surface in {
            ControlPlaneArtifactSurface.RUN_MANIFEST,
            ControlPlaneArtifactSurface.RUN_LEDGER,
        }:
            self._protected_by_run_manifest_or_ledger(
                path, payload, protected_refs, reasons
            )
        elif surface is ControlPlaneArtifactSurface.EFFECTIVE_CONFIG:
            self._protected_by_effective_config(path, payload, protected_refs, reasons)
        elif surface is ControlPlaneArtifactSurface.LINEAGE:
            self._protected_by_lineage(path, payload, protected_refs, reasons)
        elif surface is ControlPlaneArtifactSurface.CHECKPOINT:
            self._protected_by_checkpoint(payload, protected_refs, reasons)
        elif surface is ControlPlaneArtifactSurface.CACHED_BRONZE:
            snapshot_id = _content_addressed_file_snapshot_id(path)
            if snapshot_id in protected_refs.input_snapshot_ids:
                reasons.append(f"snapshot:{snapshot_id}")
        return tuple(dict.fromkeys(reasons))

    def _iter_surface_files(
        self,
        surface: ControlPlaneArtifactSurface,
    ) -> tuple[Path, ...]:
        surface_root = self._surface_root(surface)
        if not surface_root.exists():
            return ()
        return tuple(path for path in surface_root.rglob("*") if path.is_file())

    def _surface_root(self, surface: ControlPlaneArtifactSurface) -> Path:
        if surface in {
            ControlPlaneArtifactSurface.CACHED_BRONZE,
            ControlPlaneArtifactSurface.CHECKPOINT,
        }:
            return self.base_path.parent / surface.value
        return self.base_path / surface.value

    def _lineage_fragment_files(self) -> tuple[Path, ...]:
        fragments_root = (
            self.base_path / ControlPlaneArtifactSurface.LINEAGE / "fragments"
        )
        if not fragments_root.exists():
            return ()
        return tuple(path for path in fragments_root.glob("*.json") if path.is_file())


def _read_json_object_or_empty(path: Path) -> dict[str, object]:
    """Best-effort JSON object read for planner metadata."""
    if path.suffix not in {".json", ".jsonl"}:
        return {}
    try:
        if path.suffix == ".jsonl":
            line = next(
                (
                    item
                    for item in path.read_text(encoding="utf-8").splitlines()
                    if item
                ),
                "",
            )
            if not line:
                return {}
            payload = json.loads(line)
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, StopIteration, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items()}


def _resolve_payload_or_file_time(
    path: Path,
    payload: dict[str, object],
) -> datetime | None:
    for key in ("created_at", "updated_at", "occurred_at"):
        timestamp = _parse_datetime(_payload_value(payload, key))
        if timestamp is not None:
            return timestamp
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    except OSError:
        return None


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        timestamp = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def _artifact_id(
    *,
    surface: ControlPlaneArtifactSurface,
    path: Path,
    payload: dict[str, object],
) -> str:
    if surface is ControlPlaneArtifactSurface.RUN_MANIFEST:
        return str(payload.get("manifest_id") or path.stem)
    if surface is ControlPlaneArtifactSurface.RUN_LEDGER:
        return str(payload.get("manifest_id") or path.stem)
    if surface is ControlPlaneArtifactSurface.EFFECTIVE_CONFIG:
        return str(payload.get("artifact_id") or path.stem)
    if surface is ControlPlaneArtifactSurface.LINEAGE:
        return str(
            payload.get("stored_fragment_id") or payload.get("fragment_id") or path.stem
        )
    if surface is ControlPlaneArtifactSurface.CHECKPOINT:
        return (
            _payload_text(payload, "manifest_id")
            or _payload_text(payload, "run_id")
            or path.stem
        )
    if surface is ControlPlaneArtifactSurface.CACHED_BRONZE:
        return _content_addressed_file_snapshot_id(path)
    return path.stem


def _effective_config_artifact_id(payload: dict[str, object]) -> str | None:
    code_provenance = payload.get("code_provenance")
    if not isinstance(code_provenance, dict):
        return None
    return _optional_text(code_provenance.get("effective_config_artifact_id"))


def _input_snapshot_ids(payload: dict[str, object]) -> tuple[str, ...]:
    source_refs = payload.get("source_refs")
    if not isinstance(source_refs, list):
        return ()
    snapshot_ids: list[str] = []
    for source_ref in source_refs:
        if not isinstance(source_ref, dict):
            continue
        input_snapshots = source_ref.get("input_snapshots")
        if not isinstance(input_snapshots, list):
            continue
        for input_snapshot in input_snapshots:
            if not isinstance(input_snapshot, dict):
                continue
            snapshot_id = _optional_text(input_snapshot.get("snapshot_id"))
            if snapshot_id is not None:
                snapshot_ids.append(snapshot_id)
    return tuple(snapshot_ids)


def _payload_text(payload: dict[str, object], key: str) -> str | None:
    return _optional_text(_payload_value(payload, key))


def _payload_value(payload: dict[str, object], key: str) -> object:
    if key in payload:
        return payload.get(key)
    metadata = payload.get("metadata")
    if isinstance(metadata, dict) and key in metadata:
        return metadata.get(key)
    return None


def _content_addressed_file_snapshot_id(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return f"unreadable:{path.stem}"
    return f"sha256:{digest.hexdigest()}"


def _indexed_stem(path: Path) -> str | None:
    if path.parent.name not in _INDEX_DIR_NAMES:
        return None
    return path.stem


def _lineage_fragment_id_candidates(payload: dict[str, object]) -> tuple[str, ...]:
    candidates = (
        _optional_text(payload.get("stored_fragment_id")),
        _optional_text(payload.get("fragment_id")),
    )
    return tuple(candidate for candidate in candidates if candidate)


def _manifest_or_run_is_protected(
    payload: dict[str, object],
    *,
    manifest_ids: frozenset[str],
    run_ids: frozenset[str],
) -> bool:
    manifest_id = _optional_text(payload.get("manifest_id"))
    run_id = _optional_text(payload.get("run_id"))
    return (manifest_id in manifest_ids) or (run_id in run_ids)


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_lifecycle_reason(*, stale: bool, protected_by: tuple[str, ...]) -> str:
    if protected_by:
        return "protected_reference"
    if stale:
        return "retention_expired"
    return "within_retention_window"
