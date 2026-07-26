"""Support helpers for effective-config source reference assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from bioetl.domain.control_plane.config_source_hashing import (
    ConfigSourceHashStrategy,
    compute_config_source_hashes,
)
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef


class _CandidatePathsFactory(Protocol):
    def __call__(
        self,
        *,
        provider: str,
        entity: str,
        repo_root: Path,
    ) -> list[str]: ...


def _compute_file_hashes(
    *,
    relative_path: str,
    path: Path,
) -> tuple[str | None, str | None, ConfigSourceHashStrategy | None]:
    """Return semantic and raw hashes for one config source file when available."""
    if not path.exists() or not path.is_file():
        return None, None, None
    hashes = compute_config_source_hashes(
        source_path=relative_path,
        raw_bytes=path.read_bytes(),
    )
    return hashes.semantic_hash, hashes.raw_hash, hashes.hash_strategy


def _build_config_source_ref(
    *,
    relative_path: str,
    priority: int,
    repo_root: Path,
) -> ConfigSourceRef:
    """Build one canonical file-backed source ref with provenance hash."""
    source_path = repo_root / relative_path
    source_hash, raw_source_hash, source_hash_strategy = _compute_file_hashes(
        relative_path=relative_path,
        path=source_path,
    )
    return ConfigSourceRef(
        source_type="file",
        source_path=relative_path,
        source_hash=source_hash,
        raw_source_hash=raw_source_hash,
        source_hash_strategy=source_hash_strategy,
        priority=priority,
    )


def build_effective_config_source_refs(
    *,
    provider: str,
    entity: str,
    candidate_paths_factory: _CandidatePathsFactory,
    repo_root: Path,
) -> list[ConfigSourceRef]:
    """Build source references used to materialize effective-config artifacts."""
    candidate_paths = candidate_paths_factory(
        provider=provider,
        entity=entity,
        repo_root=repo_root,
    )
    refs: list[ConfigSourceRef] = []
    priority = 1
    for relative_path in candidate_paths:
        if not (repo_root / relative_path).exists():
            continue
        refs.append(
            _build_config_source_ref(
                relative_path=relative_path,
                priority=priority,
                repo_root=repo_root,
            )
        )
        priority += 1
    return refs


def resolve_effective_config_entity(provider: str, entity: str) -> str:
    """Map runtime entity labels to canonical effective-config source paths."""
    if provider == "composite" and entity.startswith("composite_"):
        return entity.removeprefix("composite_")
    return entity
