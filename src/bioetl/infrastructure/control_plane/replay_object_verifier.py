"""Revalidate saved replay objects without substituting current runtime inputs."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.normalization.json import stable_json_hash
from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
    FileEffectiveConfigArtifactStore,
)
from bioetl.infrastructure.storage.atomic import atomic_write_bytes


def _digest(value: str | None) -> str | None:
    token = (value or "").removeprefix("sha256:")
    return token if re.fullmatch(r"[0-9a-f]{64}", token) else None


def verify_file(path: Path, expected: str | None) -> bool | None:
    """Missing/unreadable objects stay unknown; mismatching bytes fail."""
    digest = _digest(expected)
    if digest is None:
        return None
    try:
        with path.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
    except OSError:
        return None
    return actual == digest


@dataclass(frozen=True)
class ReplayObjectVerifier:
    """Resolve only saved config, archived lock bytes and referenced Bronze files."""

    config_root: Path
    lock_root: Path
    bronze_root: Path
    # Optional evidence-location trust anchor; when set, absolute/file URI
    # snapshot paths must resolve under this base (RF-003/RF-004).
    trusted_base: Path | None = None

    def verify(self, manifest: RunManifest) -> dict[str, bool]:
        """Return current object checks; never trust historical boolean flags."""
        provenance = manifest.code_provenance
        values = {
            "effective_config_hash": self._config(manifest),
            "dependency_lock_hash": self._dependency_lock(
                provenance.dependency_lock_hash
            ),
            "input_snapshot_fingerprint": self._snapshots(manifest),
        }
        return {key: value for key, value in values.items() if value is not None}

    def _dependency_lock(self, expected: str | None) -> bool | None:
        lock_digest = _digest(expected)
        if lock_digest is None:
            return None
        path = self._contained(self.lock_root / lock_digest)
        return verify_file(path, lock_digest) if path is not None else None

    def _contained(self, path: Path) -> Path | None:
        """Return resolved ``path`` when it stays under ``trusted_base`` (if set)."""
        try:
            resolved = path.resolve(strict=False)
        except OSError:
            return None
        if self.trusted_base is None:
            return resolved
        try:
            base = self.trusted_base.resolve(strict=False)
        except OSError:
            return None
        return resolved if resolved.is_relative_to(base) else None

    def _config(self, manifest: RunManifest) -> bool | None:
        expected = _digest(manifest.code_provenance.effective_config_hash)
        if expected is None:
            return None
        try:
            # Contain index + selected JSON before reading so an outward
            # symlink under config_root cannot forge effective_config_hash.
            run_index = self.config_root / "_by_run_id" / f"{manifest.run_id}.txt"
            if self._contained(run_index) is None:
                return None
            if not run_index.exists():
                return None
            artifact_id = run_index.read_text(encoding="utf-8").strip()
            if not artifact_id:
                return None
            artifact_path = self.config_root / f"{artifact_id}.json"
            if self._contained(artifact_path) is None:
                return None
            payload = FileEffectiveConfigArtifactStore(self.config_root).get(
                artifact_id
            )
            if payload is None:
                return None
            if (
                payload.get("artifact_id")
                != manifest.code_provenance.effective_config_artifact_id
            ):
                return False
            semantic = payload.get("semantic_artifact", payload)
            if not isinstance(semantic, dict):
                return None
            section = semantic.get("effective_execution_config")
            if not isinstance(section, dict) or "config_data" not in section:
                return None
            version = section.get("identity_version")
            if version != "effective-config-v1":
                return None
            return (
                stable_json_hash(
                    {
                        "identity_version": version,
                        "config_data": section["config_data"],
                    }
                )
                == expected
            )
        except (OSError, ValueError, TypeError):
            return None

    def _snapshot_path(
        self, uri: str, provider: str = "", entity: str = ""
    ) -> Path | None:
        if uri.startswith("bronze://"):
            bronze_root = self.bronze_root.resolve()
            root = (bronze_root / provider / entity).resolve()
            if not root.is_relative_to(bronze_root):
                return None
            relative = Path(uri.removeprefix("bronze://"))
            prefix = Path(provider) / entity
            anchor = (
                bronze_root
                if prefix.parts and relative.parts[: len(prefix.parts)] == prefix.parts
                else root
            )
            candidate = (anchor / relative).resolve()
            if not candidate.is_relative_to(root):
                return None
            return self._contained(candidate)
        if uri.startswith("file://"):
            return self._contained(Path(uri.removeprefix("file://")))
        if "://" in uri or not uri:
            return None
        return self._contained(Path(uri))

    def _snapshots(self, manifest: RunManifest) -> bool | None:
        results: list[bool | None] = []
        for source in manifest.source_refs:
            for snapshot in source.input_snapshots:
                path = self._snapshot_path(
                    snapshot.immutable_uri or "",
                    getattr(source, "provider", ""),
                    getattr(source, "entity", ""),
                )
                results.append(
                    verify_file(path, snapshot.content_hash) if path else None
                )
        if False in results:
            return False
        return True if results and all(value is True for value in results) else None

    def archive_lock(self, expected: str | None, source: Path) -> None:
        """Archive matching lock bytes during creation, never during reads."""
        digest = _digest(expected)
        if digest is None:
            return
        for directory in (source, *source.parents):
            for name in ("uv.lock", "poetry.lock"):
                candidate = directory / name
                if verify_file(candidate, digest) is not True:
                    continue
                # Preserve exact bytes, including CRLF.
                content = candidate.read_bytes()
                if hashlib.sha256(content).hexdigest() != digest:
                    return
                destination = self.lock_root / digest
                if destination.exists():
                    return
                self.lock_root.mkdir(parents=True, exist_ok=True)
                atomic_write_bytes(destination, content)
                return
