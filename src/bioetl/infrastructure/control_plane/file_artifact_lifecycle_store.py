"""File-backed lifecycle planner for control-plane artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleApplyResult,
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactLifecyclePolicy,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactSurface,
)

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
    effective_config_artifact_ids: frozenset[str]
    lineage_fragment_ids: frozenset[str]


@dataclass(slots=True)
class FileControlPlaneArtifactLifecycleStore:
    """Plan and apply lifecycle decisions for file-backed control-plane artifacts."""

    base_path: Path

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
        return ControlPlaneArtifactLifecycleApplyResult(
            plan=plan,
            deleted_paths=tuple(deleted_paths),
            missing_paths=tuple(missing_paths),
        )

    def _resolve_protected_refs(
        self,
        *,
        policy: ControlPlaneArtifactLifecyclePolicy,
        cutoff: datetime,
    ) -> _ProtectedRefs:
        """Resolve explicit and live-reference protections before planning."""
        manifest_ids = set(policy.protected_manifest_ids)
        run_ids = set(policy.protected_run_ids)
        effective_config_artifact_ids = set(
            policy.protected_effective_config_artifact_ids
        )
        lineage_fragment_ids = set(policy.protected_lineage_fragment_ids)

        for manifest_path in self._iter_surface_files(
            ControlPlaneArtifactSurface.RUN_MANIFEST
        ):
            if manifest_path.parent.name in _INDEX_DIR_NAMES:
                continue
            payload = _read_json_object_or_empty(manifest_path)
            if not payload:
                continue
            created_at = _resolve_payload_or_file_time(manifest_path, payload)
            manifest_id = str(payload.get("manifest_id") or manifest_path.stem)
            run_id = _optional_text(payload.get("run_id"))
            if created_at is not None and created_at < cutoff:
                continue
            manifest_ids.add(manifest_id)
            if run_id is not None:
                run_ids.add(run_id)
            replay_of_manifest_id = _optional_text(payload.get("replay_of_manifest_id"))
            if replay_of_manifest_id is not None:
                manifest_ids.add(replay_of_manifest_id)
            artifact_id = _effective_config_artifact_id(payload)
            if artifact_id is not None:
                effective_config_artifact_ids.add(artifact_id)

        for fragment_path in self._lineage_fragment_files():
            payload = _read_json_object_or_empty(fragment_path)
            if not payload:
                continue
            if _manifest_or_run_is_protected(
                payload,
                manifest_ids=frozenset(manifest_ids),
                run_ids=frozenset(run_ids),
            ):
                lineage_fragment_ids.update(_lineage_fragment_id_candidates(payload))

        return _ProtectedRefs(
            manifest_ids=frozenset(manifest_ids),
            run_ids=frozenset(run_ids),
            effective_config_artifact_ids=frozenset(effective_config_artifact_ids),
            lineage_fragment_ids=frozenset(lineage_fragment_ids),
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
            manifest_id = str(payload.get("manifest_id") or path.stem)
            run_id = _optional_text(payload.get("run_id"))
            if manifest_id in protected_refs.manifest_ids:
                reasons.append(f"manifest:{manifest_id}")
            if run_id in protected_refs.run_ids:
                reasons.append(f"run:{run_id}")
            indexed_run_id = _indexed_stem(path)
            if indexed_run_id in protected_refs.run_ids:
                reasons.append(f"run:{indexed_run_id}")
        elif surface is ControlPlaneArtifactSurface.EFFECTIVE_CONFIG:
            artifact_id = str(payload.get("artifact_id") or path.stem)
            run_id = _optional_text(payload.get("run_id")) or _indexed_stem(path)
            if artifact_id in protected_refs.effective_config_artifact_ids:
                reasons.append(f"effective_config:{artifact_id}")
            if run_id in protected_refs.run_ids:
                reasons.append(f"run:{run_id}")
        elif surface is ControlPlaneArtifactSurface.LINEAGE:
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
        return tuple(dict.fromkeys(reasons))

    def _iter_surface_files(
        self,
        surface: ControlPlaneArtifactSurface,
    ) -> tuple[Path, ...]:
        surface_root = self.base_path / surface.value
        if not surface_root.exists():
            return ()
        return tuple(path for path in surface_root.rglob("*") if path.is_file())

    def _lineage_fragment_files(self) -> tuple[Path, ...]:
        fragments_root = self.base_path / ControlPlaneArtifactSurface.LINEAGE / "fragments"
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
                (item for item in path.read_text(encoding="utf-8").splitlines() if item),
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
    for key in ("created_at", "occurred_at"):
        timestamp = _parse_datetime(payload.get(key))
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
            payload.get("stored_fragment_id")
            or payload.get("fragment_id")
            or path.stem
        )
    return path.stem


def _effective_config_artifact_id(payload: dict[str, object]) -> str | None:
    code_provenance = payload.get("code_provenance")
    if not isinstance(code_provenance, dict):
        return None
    return _optional_text(code_provenance.get("effective_config_artifact_id"))


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
