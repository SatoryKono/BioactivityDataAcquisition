"""Opt-in bootstrap registry cache helpers for expensive repo-backed tests."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_GLOBS = ("**/*.yaml", "**/*.yml")
_BOOTSTRAP_SOURCE_ROOTS = (
    _REPO_ROOT / "src" / "bioetl" / "composition" / "factories" / "pipeline",
    _REPO_ROOT / "src" / "bioetl" / "composition" / "providers",
)


@dataclass(frozen=True)
class BootstrapCacheKey:
    """Content fingerprint for bootstrap inputs that affect test registries."""

    configs_root: str
    digest: str


@dataclass(frozen=True)
class CachedBootstrapRegistries:
    """Cached registry payload and the fingerprint that produced it."""

    cache_key: BootstrapCacheKey
    pipeline_registry: Any
    provider_registry: Any


def _iter_existing_files(
    paths: Iterable[Path],
    *,
    globs: tuple[str, ...],
) -> list[Path]:
    files: list[Path] = []
    for root in paths:
        if root.is_file():
            files.append(root)
            continue
        if not root.exists():
            continue
        for pattern in globs:
            files.extend(path for path in root.glob(pattern) if path.is_file())
    return sorted({path.resolve() for path in files}, key=lambda path: path.as_posix())


def fingerprint_bootstrap_inputs(
    *,
    configs_root: Path,
    source_roots: Iterable[Path] = _BOOTSTRAP_SOURCE_ROOTS,
) -> BootstrapCacheKey:
    """Return a stable content fingerprint for config and bootstrap source inputs."""
    resolved_configs_root = configs_root.resolve()
    files = _iter_existing_files(
        (resolved_configs_root,),
        globs=_CONFIG_GLOBS,
    )
    files.extend(
        _iter_existing_files(
            (Path(root) for root in source_roots),
            globs=("**/*.py",),
        )
    )

    digest = hashlib.sha256()
    digest.update(resolved_configs_root.as_posix().encode("utf-8"))
    for file_path in sorted(files, key=lambda path: path.as_posix()):
        try:
            relative = file_path.relative_to(_REPO_ROOT)
        except ValueError:
            relative = file_path
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_path.read_bytes())
        digest.update(b"\0")
    return BootstrapCacheKey(
        configs_root=resolved_configs_root.as_posix(),
        digest=digest.hexdigest(),
    )


def build_pipeline_registry() -> Any:
    """Build the canonical populated pipeline registry once for cache storage."""
    from bioetl.composition.factories.pipeline.registry import register_all_pipelines
    from bioetl.composition.registry_api import create_registry

    registry = create_registry()
    register_all_pipelines(registry=registry)
    return registry


def build_provider_registry() -> Any:
    """Build the canonical populated provider registry once for cache storage."""
    from bioetl.composition.providers.provider_registry import (
        create_provider_registry,
        ensure_provider_registry_ready,
    )

    registry = create_provider_registry()
    ensure_provider_registry_ready(registry)
    return registry


def clone_pipeline_registry(cached_registry: Any) -> Any:
    """Return an isolated pipeline registry clone backed by cached definitions."""
    from bioetl.composition.registry_api import create_registry

    clone = create_registry()
    # Tests intentionally clone the immutable registry definitions rather than
    # re-importing every factory; the clone owns its registry dictionary.
    clone._registry.update(cached_registry._registry)
    return clone


def clone_provider_registry(cached_registry: Any) -> Any:
    """Return an isolated provider registry clone backed by cached configs."""
    from bioetl.composition.providers.provider_registry import create_provider_registry

    clone = create_provider_registry()
    for provider_name in cached_registry.list_providers():
        clone.register(provider_name, cached_registry.get(provider_name))
    return clone


class BootstrapRegistryCache:
    """Session-scoped cache with explicit fingerprint invalidation."""

    def __init__(
        self,
        *,
        pipeline_registry_builder: Callable[[], Any] = build_pipeline_registry,
        provider_registry_builder: Callable[[], Any] = build_provider_registry,
        fingerprint_builder: Callable[[Path], BootstrapCacheKey] | None = None,
    ) -> None:
        self._pipeline_registry_builder = pipeline_registry_builder
        self._provider_registry_builder = provider_registry_builder
        self._fingerprint_builder = (
            fingerprint_builder
            if fingerprint_builder is not None
            else lambda configs_root: fingerprint_bootstrap_inputs(
                configs_root=configs_root
            )
        )
        self._cached: CachedBootstrapRegistries | None = None
        self.build_count = 0

    def get_or_build(self, *, configs_root: Path) -> CachedBootstrapRegistries:
        """Return cached registries, rebuilding when bootstrap inputs change."""
        cache_key = self._fingerprint_builder(configs_root)
        if self._cached is not None and self._cached.cache_key == cache_key:
            return self._cached

        self._cached = CachedBootstrapRegistries(
            cache_key=cache_key,
            pipeline_registry=self._pipeline_registry_builder(),
            provider_registry=self._provider_registry_builder(),
        )
        self.build_count += 1
        return self._cached
