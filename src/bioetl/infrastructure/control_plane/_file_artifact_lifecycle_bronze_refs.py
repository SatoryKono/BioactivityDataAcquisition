"""Bronze artifact candidate collection for lifecycle planning."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PureWindowsPath

from bioetl.domain.control_plane import (
    ControlPlaneArtifactResolutionIssue,
    ControlPlaneArtifactResolutionIssueCode,
    ControlPlaneArtifactSurface,
    RunManifest,
)

_BRONZE_URI_PREFIX = "bronze://"


def _resolution_issue(
    code: ControlPlaneArtifactResolutionIssueCode,
    surface: ControlPlaneArtifactSurface,
    detail: str,
) -> ControlPlaneArtifactResolutionIssue:
    return ControlPlaneArtifactResolutionIssue(
        code=code,
        surface=surface,
        detail=detail,
    )


def _append_cached_bronze_candidates(
    candidates: list[tuple[ControlPlaneArtifactSurface, Path]],
    issues: list[ControlPlaneArtifactResolutionIssue],
    base_path: Path,
    manifest: RunManifest,
) -> None:
    bronze_root = base_path.parent / "bronze"
    seen: set[Path] = set()
    snapshots = [
        (bronze_root / source.provider / source.entity, snapshot)
        for source in manifest.source_refs
        for snapshot in source.input_snapshots
    ]

    def read_snapshot(
        item: tuple[Path, object],
    ) -> tuple[
        list[tuple[ControlPlaneArtifactSurface, Path]],
        list[ControlPlaneArtifactResolutionIssue],
    ]:
        found: list[tuple[ControlPlaneArtifactSurface, Path]] = []
        problems: list[ControlPlaneArtifactResolutionIssue] = []
        _append_snapshot_bronze_candidate(
            found,
            problems,
            bronze_root=bronze_root,
            source_root=item[0],
            snapshot=item[1],
            seen=set(),
        )
        return found, problems

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(read_snapshot, snapshots))
    for found, problems in results:
        issues.extend(problems)
        for surface, path in found:
            if path not in seen:
                seen.add(path)
                candidates.append((surface, path))
    for artifact in manifest.planned_artifacts:
        _append_planned_bronze_candidate(
            candidates,
            base_path=base_path,
            artifact=artifact,
            seen=seen,
        )


def _append_snapshot_bronze_candidate(
    candidates: list[tuple[ControlPlaneArtifactSurface, Path]],
    issues: list[ControlPlaneArtifactResolutionIssue],
    *,
    bronze_root: Path,
    source_root: Path,
    snapshot: object,
    seen: set[Path],
) -> None:
    """Append one immutable snapshot URI or record its bounded issue."""
    uri = getattr(snapshot, "immutable_uri", None)
    snapshot_id = getattr(snapshot, "snapshot_id", "unknown")
    if uri is None or not str(uri).strip():
        issues.append(
            _resolution_issue(
                ControlPlaneArtifactResolutionIssueCode.SNAPSHOT_URI_NOT_RECORDED,
                ControlPlaneArtifactSurface.CACHED_BRONZE,
                f"Input snapshot '{snapshot_id}' has no immutable_uri.",
            )
        )
        return
    path = resolve_bronze_uri(bronze_root, str(uri).strip())
    # Cached-Bronze launch refs are relative to the provider/entity reader root.
    # Retain support for older refs rooted at the shared Bronze directory.
    if path is not None and not path.is_file():
        scoped_path = resolve_bronze_uri(source_root, str(uri).strip())
        if scoped_path is not None and scoped_path.is_relative_to(
            bronze_root.resolve()
        ):
            path = scoped_path
    if path is None:
        issues.append(
            _resolution_issue(
                ControlPlaneArtifactResolutionIssueCode.SNAPSHOT_URI_NOT_RECORDED,
                ControlPlaneArtifactSurface.CACHED_BRONZE,
                f"Input snapshot '{snapshot_id}' immutable_uri is not a usable "
                "bronze:// location.",
            )
        )
        return
    if path not in seen:
        seen.add(path)
        candidates.append((ControlPlaneArtifactSurface.CACHED_BRONZE, path))


def _append_planned_bronze_candidate(
    candidates: list[tuple[ControlPlaneArtifactSurface, Path]],
    *,
    base_path: Path,
    artifact: object,
    seen: set[Path],
) -> None:
    """Append one planned Bronze artifact when it is usable and new."""
    layer = str(getattr(artifact, "layer", "") or "").strip().lower()
    raw_path = str(getattr(artifact, "path", "") or "").strip()
    if layer not in {"bronze", "cached_bronze"} or not raw_path:
        return
    path = Path(raw_path)
    if not path.is_absolute():
        path = (base_path.parent / path).resolve()
    if path not in seen:
        seen.add(path)
        candidates.append((ControlPlaneArtifactSurface.CACHED_BRONZE, path))


def resolve_bronze_uri(bronze_root: Path, immutable_uri: str) -> Path | None:
    """Resolve a `bronze://` URI to a path under the Bronze root."""
    if not immutable_uri.startswith(_BRONZE_URI_PREFIX):
        return None
    relative = immutable_uri[len(_BRONZE_URI_PREFIX) :].strip()
    if not relative or PureWindowsPath(relative).drive or Path(relative).is_absolute():
        return None
    parts = Path(relative.replace("\\", "/")).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return None
    path = bronze_root.joinpath(*parts).resolve()
    return path if path.is_relative_to(bronze_root.resolve()) else None
