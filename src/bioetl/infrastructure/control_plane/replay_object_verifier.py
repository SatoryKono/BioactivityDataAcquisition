"""Revalidate saved replay objects without substituting current runtime inputs."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

from bioetl.domain.control_plane import RunManifest, RunSourceRef
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

    def verify(self, manifest: RunManifest) -> dict[str, bool]:
        """Return current object checks; never trust historical boolean flags."""
        provenance = manifest.code_provenance
        lock_digest = _digest(provenance.dependency_lock_hash)
        values = {
            "effective_config_hash": self._config(manifest),
            "dependency_lock_hash": (
                verify_file(self.lock_root / lock_digest, lock_digest)
                if lock_digest
                else None
            ),
            "input_snapshot_fingerprint": self._snapshots(manifest),
        }
        if getattr(
            manifest, "provider", None
        ) == "composite" and manifest.launch_context.get("child_replay_manifests"):
            values["input_snapshot_fingerprint"] = self._composite_children(
                manifest, values["input_snapshot_fingerprint"]
            )
        return {key: value for key, value in values.items() if value is not None}

    def _composite_children(
        self, manifest: RunManifest, snapshots: bool | None
    ) -> bool | None:
        from bioetl.domain.control_plane.composite_replay import (
            has_composite_replay_bindings,
        )
        from bioetl.infrastructure.control_plane.file_run_manifest_store import (
            FileRunManifestStore,
        )

        if not has_composite_replay_bindings(manifest):
            return False
        bindings = manifest.launch_context["child_replay_manifests"]
        if not isinstance(bindings, dict):
            return False
        store = FileRunManifestStore(base_path=self.config_root.parent / "run_manifest")
        sources: list[RunSourceRef] = []
        for pipeline, identity in sorted(bindings.items()):
            child = store.get(str(identity))
            if child is None:
                return None
            if (
                child.provider == "composite"
                or child.pipeline_name != pipeline
                or child.code_provenance.git_commit
                != manifest.code_provenance.git_commit
                or child.code_provenance.dependency_lock_hash
                != manifest.code_provenance.dependency_lock_hash
            ):
                return False
            checks = self.verify(child)
            if False in checks.values():
                return False
            if len(checks) != 3:
                return None
            sources.extend(child.source_refs)
        if tuple(sources) != manifest.source_refs:
            return False
        return snapshots

    def _config(self, manifest: RunManifest) -> bool | None:
        expected = _digest(manifest.code_provenance.effective_config_hash)
        if expected is None:
            return None
        try:
            payload = FileEffectiveConfigArtifactStore(self.config_root).get_by_run_id(
                manifest.run_id
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
            candidate = (root / uri.removeprefix("bronze://")).resolve()
            return candidate if candidate.is_relative_to(root) else None
        if uri.startswith("file://"):
            parsed = urlsplit(uri)
            if parsed.netloc not in ("", "localhost"):
                return None
            return Path(url2pathname(parsed.path))
        return None if "://" in uri or not uri else Path(uri)

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
