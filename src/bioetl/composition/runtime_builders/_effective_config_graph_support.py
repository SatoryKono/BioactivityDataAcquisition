"""Config-graph discovery helpers for effective-config artifact source refs."""

from __future__ import annotations

import posixpath
from pathlib import Path

import yaml

from bioetl.infrastructure.config.contract_registry_loader import (
    DEFAULT_CONTRACT_REGISTRY_PATH,
)

_CONFIG_GRAPH_FILE_SUFFIXES = (".yaml", ".yml", ".toml", ".lock")
_DEPENDENCY_PROVENANCE_FILES = ("pyproject.toml", "uv.lock", "poetry.lock")

def _normalize_relative_posix_path(value: str) -> str:
    return posixpath.normpath(value.replace("\\", "/"))

def _core_config_graph_paths(*, provider: str, entity: str) -> list[str]:
    core_paths = ["configs/base/pipeline.yaml", "configs/base/quality.yaml"]
    if provider == "composite":
        core_paths.extend(
            [
                f"configs/composites/{entity}.yaml",
                f"configs/quality/entities/composite/{entity}.yaml",
            ]
        )
    else:
        core_paths.extend(
            [
                f"configs/providers/{provider}.yaml",
                f"configs/entities/{provider}/{entity}.yaml",
                f"configs/quality/entities/{provider}/{entity}.yaml",
            ]
        )
    core_paths.append(DEFAULT_CONTRACT_REGISTRY_PATH.as_posix())
    return core_paths

def _candidate_seed_paths(*, provider: str, entity: str) -> tuple[str, ...]:
    if provider == "composite":
        return (
            f"configs/composites/{entity}.yaml",
            f"configs/quality/entities/composite/{entity}.yaml",
        )
    return (
        f"configs/providers/{provider}.yaml",
        f"configs/entities/{provider}/{entity}.yaml",
        f"configs/quality/entities/{provider}/{entity}.yaml",
    )

def _extract_config_reference_strings(payload: object) -> list[str]:
    references: list[str] = []
    if isinstance(payload, str):
        references.append(payload)
    elif isinstance(payload, dict):
        for value in payload.values():
            references.extend(_extract_config_reference_strings(value))
    elif isinstance(payload, (list, tuple)):
        for value in payload:
            references.extend(_extract_config_reference_strings(value))
    return references

def _resolve_config_graph_reference(*, raw_value: str, base_dir: str) -> str | None:
    candidate = raw_value.strip()
    if not candidate or "://" in candidate:
        return None
    if not candidate.endswith(_CONFIG_GRAPH_FILE_SUFFIXES):
        return None
    normalized_candidate = _normalize_relative_posix_path(candidate)
    if normalized_candidate in _DEPENDENCY_PROVENANCE_FILES:
        return normalized_candidate
    if normalized_candidate.startswith("/"):
        return None
    if normalized_candidate.startswith("configs/"):
        return normalized_candidate
    resolved = _normalize_relative_posix_path(
        posixpath.join(base_dir, normalized_candidate)
    )
    if resolved.startswith("../") or resolved == "..":
        return None
    if resolved.startswith("configs/"):
        return resolved
    return None

def _load_config_graph_references(*, relative_path: str, repo_root: Path) -> list[str]:
    source_path = repo_root / relative_path
    if source_path.suffix not in {".yaml", ".yml"} or not source_path.exists():
        return []
    payload = yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}
    base_dir = posixpath.dirname(relative_path)
    discovered: list[str] = []
    for raw_value in _extract_config_reference_strings(payload):
        resolved = _resolve_config_graph_reference(
            raw_value=raw_value,
            base_dir=base_dir,
        )
        if resolved is not None:
            discovered.append(resolved)
    return discovered

def _discover_effective_config_graph_paths(
    *,
    provider: str,
    entity: str,
    repo_root: Path,
) -> list[str]:
    discovered: list[str] = []
    pending = list(_candidate_seed_paths(provider=provider, entity=entity))
    seen: set[str] = set()
    while pending:
        relative_path = pending.pop(0)
        normalized = _normalize_relative_posix_path(relative_path)
        if normalized in seen:
            continue
        seen.add(normalized)
        if not (repo_root / normalized).exists():
            continue
        discovered.append(normalized)
        for reference in _load_config_graph_references(
            relative_path=normalized,
            repo_root=repo_root,
        ):
            if reference not in seen:
                pending.append(reference)
    return discovered

def build_effective_config_candidate_paths(
    *,
    provider: str,
    entity: str,
    repo_root: Path,
) -> list[str]:
    """Return ordered config/dependency inputs for effective-config hashing."""
    candidate_paths: list[str] = []
    for relative_path in _core_config_graph_paths(provider=provider, entity=entity):
        if relative_path not in candidate_paths:
            candidate_paths.append(relative_path)
    for relative_path in _discover_effective_config_graph_paths(
        provider=provider,
        entity=entity,
        repo_root=repo_root,
    ):
        if relative_path not in candidate_paths:
            candidate_paths.append(relative_path)
    for relative_path in _DEPENDENCY_PROVENANCE_FILES:
        if relative_path not in candidate_paths:
            candidate_paths.append(relative_path)
    return candidate_paths

__all__ = [
    "_DEPENDENCY_PROVENANCE_FILES",
    "build_effective_config_candidate_paths",
]
