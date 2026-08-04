"""Opt-in bootstrap registry cache helpers for expensive repo-backed tests."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from bioetl.composition.providers._models import (
    AdapterCreatorProtocol,
    DataSourceCreatorProtocol,
)
from bioetl.composition.providers._registry_protocols import ProviderRegistrarProtocol
from bioetl.domain.ports import PipelineFactoryPort


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
class FrozenHttpConfig:
    """Immutable HTTP metadata used to rebuild a provider config."""

    rate: float
    capacity: int
    rate_overrides: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class FrozenProviderDefinition:
    """Immutable provider definition; it contains no registry/container state."""

    name: str
    adapter_class: type[Any]
    http_config: FrozenHttpConfig | None
    requires_http_client: bool
    requires_logger: bool
    default_kwargs: tuple[tuple[str, object], ...]
    adapter_creator: AdapterCreatorProtocol | None
    data_source_creator: DataSourceCreatorProtocol | None


@dataclass(frozen=True)
class CachedBootstrapMetadata:
    """Immutable bootstrap catalog and the fingerprint that produced it."""

    cache_key: BootstrapCacheKey
    pipeline_names: tuple[str, ...]
    provider_definitions: tuple[FrozenProviderDefinition, ...]


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


def build_pipeline_metadata() -> tuple[str, ...]:
    """Build the canonical immutable pipeline-name catalog."""
    from bioetl.composition.factories.pipeline.registry import register_all_pipelines
    from bioetl.composition.registry_api import create_registry

    registry = create_registry()
    register_all_pipelines(registry=registry)
    return tuple(registry.list_pipelines())


def build_provider_metadata() -> tuple[FrozenProviderDefinition, ...]:
    """Build immutable provider definitions without retaining the registry."""
    from bioetl.composition.providers.provider_registry import (
        create_provider_registry,
        ensure_provider_registry_ready,
    )

    registry = create_provider_registry()
    ensure_provider_registry_ready(
        cast(ProviderRegistrarProtocol, cast(object, registry))
    )
    definitions: list[FrozenProviderDefinition] = []
    for name in registry.list_providers():
        config = registry.get(name)
        http_config = config.http_config
        frozen_http = None
        if http_config is not None:
            frozen_http = FrozenHttpConfig(
                rate=http_config.rate,
                capacity=http_config.capacity,
                rate_overrides=tuple(sorted(http_config.rate_overrides.items())),
            )
        definitions.append(
            FrozenProviderDefinition(
                name=name,
                adapter_class=config.adapter_class,
                http_config=frozen_http,
                requires_http_client=config.requires_http_client,
                requires_logger=config.requires_logger,
                default_kwargs=tuple(sorted(config.default_kwargs.items())),
                adapter_creator=config.adapter_creator,
                data_source_creator=config.data_source_creator,
            )
        )
    return tuple(definitions)


def clone_pipeline_registry(metadata: CachedBootstrapMetadata) -> Any:
    """Return a fresh pipeline registry rebuilt from immutable catalog metadata."""
    from bioetl.composition.factories.pipeline.registry import get_factory
    from bioetl.composition.registry_api import create_registry

    clone = create_registry()
    for pipeline_name in metadata.pipeline_names:
        clone.register_factory(cast(PipelineFactoryPort, get_factory(pipeline_name)))
    return clone


def clone_provider_registry(metadata: CachedBootstrapMetadata) -> Any:
    """Return a fresh provider registry rebuilt from immutable metadata."""
    from bioetl.composition.providers.provider_registry import (
        HttpConfig,
        ProviderConfig,
        create_provider_registry,
    )

    clone = create_provider_registry()
    for definition in metadata.provider_definitions:
        http_config = definition.http_config
        clone.register(
            definition.name,
            ProviderConfig(
                adapter_class=definition.adapter_class,
                http_config=(
                    None
                    if http_config is None
                    else HttpConfig(
                        rate=http_config.rate,
                        capacity=http_config.capacity,
                        rate_overrides=dict(http_config.rate_overrides),
                    )
                ),
                requires_http_client=definition.requires_http_client,
                requires_logger=definition.requires_logger,
                default_kwargs=dict(definition.default_kwargs),
                adapter_creator=definition.adapter_creator,
                data_source_creator=definition.data_source_creator,
            ),
        )
    return clone


class BootstrapMetadataCache:
    """Session-scoped immutable metadata cache with fingerprint invalidation."""

    def __init__(
        self,
        *,
        pipeline_metadata_builder: Callable[
            [], tuple[str, ...]
        ] = build_pipeline_metadata,
        provider_metadata_builder: Callable[
            [], tuple[FrozenProviderDefinition, ...]
        ] = build_provider_metadata,
        fingerprint_builder: Callable[[Path], BootstrapCacheKey] | None = None,
    ) -> None:
        self._pipeline_metadata_builder = pipeline_metadata_builder
        self._provider_metadata_builder = provider_metadata_builder
        self._fingerprint_builder = (
            fingerprint_builder
            if fingerprint_builder is not None
            else lambda configs_root: fingerprint_bootstrap_inputs(
                configs_root=configs_root
            )
        )
        self._cached: CachedBootstrapMetadata | None = None
        self.build_count = 0

    def get_or_build(self, *, configs_root: Path) -> CachedBootstrapMetadata:
        """Return immutable metadata, rebuilding when bootstrap inputs change."""
        cache_key = self._fingerprint_builder(configs_root)
        if self._cached is not None and self._cached.cache_key == cache_key:
            return self._cached

        self._cached = CachedBootstrapMetadata(
            cache_key=cache_key,
            pipeline_names=self._pipeline_metadata_builder(),
            provider_definitions=self._provider_metadata_builder(),
        )
        self.build_count += 1
        return self._cached


# Backward-compatible import name; the cached payload is metadata, never a registry.
BootstrapRegistryCache = BootstrapMetadataCache
