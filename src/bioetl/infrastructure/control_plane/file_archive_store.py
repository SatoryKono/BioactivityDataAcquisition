"""Local, non-destructive archive copies with manifest-bound restore evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import stat
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactSurface,
    RunManifest,
)
from bioetl.infrastructure.control_plane.archive_run_reports import (
    selected_report_sources,
)

_SCHEMA = "bioetl_local_archive_v1"
_ARCHIVE_READ_WORKERS = 16


def _index_error(payload: object, manifest: RunManifest) -> str | None:
    if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
        return "archive_index_invalid"
    if (
        payload.get("manifest_id") != manifest.manifest_id
        or payload.get("run_id") != str(manifest.run_id)
        or payload.get("manifest_sha256") != _manifest_digest(manifest)
    ):
        return "archive_identity_mismatch"
    return None


def _entry_error(
    entry: object,
    *,
    sources: dict[str, Path],
    seen: set[str],
    pack: Path,
) -> str | None:
    if not isinstance(entry, dict):
        return "archive_index_invalid"
    relative, digest = entry.get("path"), entry.get("sha256")
    if not isinstance(relative, str) or relative not in sources or relative in seen:
        return "archive_inventory_mismatch"
    seen.add(relative)
    for area in ("files", "restored"):
        if _digest(_contained_file(pack / area, relative)) != digest:
            return "archive_checksum_mismatch"
    if _digest(sources[relative]) != digest:
        return "archive_source_mismatch"
    return None


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _manifest_digest(manifest: RunManifest) -> str:
    serialized = json.dumps(manifest.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def _contained_file(base: Path, relative: str) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("archive_path_outside_root")
    candidate = base.absolute() / relative_path
    # Inspect every component without following links. Reusing this lstat result
    # avoids resolving the same path and then stat-ing every component again.
    # No metadata survives this call, so later requests recheck all components.
    for part in (*reversed(candidate.parents), candidate):
        metadata = part.lstat()
        if stat.S_ISLNK(metadata.st_mode) or part.is_junction():
            raise ValueError("archive_symlink_rejected")
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("archive_path_outside_root")
    return candidate


def _validate_manifest_source(path: Path, manifest: RunManifest) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if path.name.endswith(".contract-evidence.json"):
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != "contract_evidence_v1"
            or payload.get("manifest_id") != manifest.manifest_id
        ):
            raise ValueError("archive_contract_evidence_mismatch")
        return False  # A copied sidecar cannot replace the full manifest.
    try:
        persisted = RunManifest.from_dict(payload)
    except (KeyError, TypeError) as exc:
        raise ValueError("archive_manifest_invalid") from exc
    if _manifest_digest(persisted) != _manifest_digest(manifest):
        raise ValueError("archive_manifest_mismatch")
    return True


def _source_entry(
    artifact: ControlPlaneArtifactRef, *, root: Path, manifest: RunManifest
) -> tuple[str, Path, bool]:
    path = Path(artifact.path)
    relative = path.absolute().relative_to(root).as_posix()
    resolved = _contained_file(root, relative)
    is_manifest = (
        _validate_manifest_source(path, manifest)
        if artifact.surface is ControlPlaneArtifactSurface.RUN_MANIFEST
        else False
    )
    return relative, resolved, is_manifest


@dataclass(frozen=True, slots=True)
class FileArchiveStore:
    """Verify local archive and restored copies without trusting a stored OK flag."""

    data_root: Path
    archive_root: Path
    report_root: Path | None = None

    def _pack(self, manifest: RunManifest) -> Path:
        key = hashlib.sha256(manifest.manifest_id.encode()).hexdigest()
        return self.archive_root.resolve() / key

    def _sources(
        self, plan: ControlPlaneArtifactLifecyclePlan, manifest: RunManifest
    ) -> dict[str, Path]:
        if plan.resolution_issues or not plan.artifacts:
            raise ValueError("archive_source_evidence_incomplete")
        read_source = partial(
            _source_entry, root=self.data_root.resolve(), manifest=manifest
        )
        with ThreadPoolExecutor(max_workers=_ARCHIVE_READ_WORKERS) as executor:
            entries = list(executor.map(read_source, plan.artifacts))
        if not any(found for _, _, found in entries):
            raise ValueError("archive_manifest_missing")
        return {
            **{relative: path for relative, path, _ in entries},
            **selected_report_sources(self.report_root, manifest),
        }

    def create(
        self, *, manifest: RunManifest, plan: ControlPlaneArtifactLifecyclePlan
    ) -> Path:
        """Copy and restore selected evidence once; never overwrite or remove sources.

        An interrupted copy has no index and cannot pass verification. Existing
        packs are deliberately preserved for inspection instead of being replaced.
        """
        root = self.data_root.resolve()
        archive_root = self.archive_root.resolve()
        if archive_root.is_relative_to(root) or root.is_relative_to(archive_root):
            raise ValueError("archive_root_must_be_separate")
        sources = self._sources(plan, manifest)
        pack = self._pack(manifest)
        pack.mkdir(parents=True, exist_ok=False)
        entries: list[dict[str, object]] = []
        for relative, source in sorted(sources.items()):
            digest = _digest(source)
            for area in ("files", "restored"):
                destination = pack / area / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                previous = source if area == "files" else pack / "files" / relative
                shutil.copyfile(previous, destination)
                if _digest(destination) != digest:
                    raise ValueError("archive_copy_checksum_mismatch")
            if _digest(source) != digest:
                raise ValueError("archive_source_changed")
            entries.append({"path": relative, "sha256": digest})
        payload = {
            "schema": _SCHEMA,
            "manifest_id": manifest.manifest_id,
            "run_id": str(manifest.run_id),
            "manifest_sha256": _manifest_digest(manifest),
            "files": entries,
        }
        # Exclusive publication is last, after both copy and restore verification.
        with (pack / "index.json").open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
        verified, reason = self.verify(manifest=manifest, plan=plan)
        if verified is not True:
            raise ValueError(reason)
        return pack

    def verify(
        self, *, manifest: RunManifest, plan: ControlPlaneArtifactLifecyclePlan
    ) -> tuple[bool | None, str]:
        """Return true/false/unknown and a bounded reason; re-read every file."""
        pack = self._pack(manifest)
        if not (pack / "index.json").exists():
            return None, "archive_evidence_not_recorded"
        try:
            index_path = _contained_file(
                self.archive_root.resolve(), f"{pack.name}/index.json"
            )
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            identity_error = _index_error(payload, manifest)
            if identity_error is not None:
                return False, identity_error
            entries = payload.get("files") if isinstance(payload, dict) else None
            if not isinstance(entries, list) or not entries:
                return False, "archive_index_invalid"
            sources = self._sources(plan, manifest)
            seen: set[str] = set()
            for entry in entries:
                if not isinstance(entry, dict):
                    return False, "archive_index_invalid"
                relative = entry.get("path")
                if (
                    not isinstance(relative, str)
                    or relative not in sources
                    or relative in seen
                ):
                    return False, "archive_inventory_mismatch"
                seen.add(relative)
            if seen != set(sources):
                return False, "archive_inventory_mismatch"

            def verify_entry(entry: object) -> str | None:
                return _entry_error(entry, sources=sources, seen=set(), pack=pack)

            # Keep all source/path/checksum checks, without cross-request cache.
            # Validate inventory serially before independent filesystem reads.
            with ThreadPoolExecutor(max_workers=_ARCHIVE_READ_WORKERS) as executor:
                errors = list(executor.map(verify_entry, entries))
            for error in errors:
                if error is not None:
                    return False, error
        except (OSError, ValueError, TypeError, KeyError):
            return False, "archive_evidence_invalid"
        return True, "archive_restore_verified"
