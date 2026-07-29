"""Content-addressed backup and verified recovery for memory directories."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memory.storage import atomic_write_json

MANIFEST_NAME = "manifest.json"
PAYLOAD_DIR = "payload"


class BackupVerificationError(RuntimeError):
    """Raised when a backup cannot be trusted for recovery."""


@dataclass(frozen=True, slots=True)
class BackupResult:
    """Description of an idempotent content-addressed backup."""

    bundle_path: Path
    root_digest: str
    file_count: int
    created: bool


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_files(source: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(
            (
                path
                for path in source.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and not path.name.endswith((".pyc", ".pyo"))
            ),
            key=lambda path: path.relative_to(source).as_posix(),
        )
    )


def _manifest(source: Path) -> dict[str, Any]:
    files = [
        {
            "path": path.relative_to(source).as_posix(),
            "sha256": _file_digest(path),
            "size": path.stat().st_size,
        }
        for path in _source_files(source)
    ]
    identity = json.dumps(files, separators=(",", ":"), sort_keys=True).encode()
    return {
        "schema_version": 1,
        "algorithm": "sha256",
        "root_digest": hashlib.sha256(identity).hexdigest(),
        "files": files,
    }


def verify_backup(bundle_path: Path) -> dict[str, Any]:
    """Verify manifest identity and every payload file."""
    manifest_path = bundle_path / MANIFEST_NAME
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupVerificationError("backup manifest is unreadable") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise BackupVerificationError("unsupported backup manifest")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise BackupVerificationError("backup manifest files must be a list")
    normalized_files: list[dict[str, Any]] = []
    for entry in files:
        if not isinstance(entry, dict):
            raise BackupVerificationError("invalid backup file entry")
        relative = Path(str(entry.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            raise BackupVerificationError("unsafe backup path")
        payload_path = bundle_path / PAYLOAD_DIR / relative
        if not payload_path.is_file():
            raise BackupVerificationError(f"missing backup payload: {relative}")
        actual_digest = _file_digest(payload_path)
        if actual_digest != entry.get("sha256"):
            raise BackupVerificationError(f"backup digest mismatch: {relative}")
        if payload_path.stat().st_size != entry.get("size"):
            raise BackupVerificationError(f"backup size mismatch: {relative}")
        normalized_files.append(
            {
                "path": relative.as_posix(),
                "sha256": actual_digest,
                "size": payload_path.stat().st_size,
            }
        )
    identity = json.dumps(
        normalized_files,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    root_digest = hashlib.sha256(identity).hexdigest()
    if root_digest != manifest.get("root_digest"):
        raise BackupVerificationError("backup root digest mismatch")
    return manifest


def create_backup(source: Path, backup_root: Path) -> BackupResult:
    """Create or reuse a deterministic content-addressed directory backup."""
    source = source.resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"memory source directory not found: {source}")
    manifest = _manifest(source)
    root_digest = str(manifest["root_digest"])
    bundle_path = backup_root / f"memory-backup-{root_digest}"
    if bundle_path.exists():
        verify_backup(bundle_path)
        return BackupResult(bundle_path, root_digest, len(manifest["files"]), False)

    backup_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".memory-backup-", dir=backup_root))
    try:
        payload_root = staging / PAYLOAD_DIR
        for entry in manifest["files"]:
            relative = Path(entry["path"])
            destination = payload_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, destination)
        atomic_write_json(staging / MANIFEST_NAME, manifest)
        verify_backup(staging)
        try:
            os.replace(staging, bundle_path)  # noqa: PTH105 - atomic publish
        except FileExistsError:
            verify_backup(bundle_path)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return BackupResult(bundle_path, root_digest, len(manifest["files"]), True)


def recover_backup(
    bundle_path: Path,
    target: Path,
    *,
    apply: bool = False,
) -> tuple[Path, ...]:
    """Verify and optionally recover a backup via rollback-safe directory swap."""
    manifest = verify_backup(bundle_path)
    recovered = tuple(Path(entry["path"]) for entry in manifest["files"])
    if not apply:
        return recovered
    target_parent = target.parent
    target_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.recovery-", dir=target_parent)
    )
    rollback = target_parent / f".{target.name}.rollback"
    if rollback.exists():
        raise BackupVerificationError(f"recovery rollback path exists: {rollback}")
    try:
        for relative in recovered:
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(bundle_path / PAYLOAD_DIR / relative, destination)
        if target.exists():
            os.replace(target, rollback)  # noqa: PTH105 - rollback-safe swap
        try:
            os.replace(staging, target)  # noqa: PTH105 - rollback-safe swap
        except Exception:
            if rollback.exists():
                os.replace(rollback, target)  # noqa: PTH105 - rollback restore
            raise
        if rollback.exists():
            shutil.rmtree(rollback)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return recovered
