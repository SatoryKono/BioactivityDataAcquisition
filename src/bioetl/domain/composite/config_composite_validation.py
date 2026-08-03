"""Validation helpers for CompositeConfig."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

__all__ = [
    "coerce_composite_collections",
    "validate_composite_config",
]


class _SeedConfigProtocol(Protocol):
    @property
    def output_keys(self) -> tuple[str, ...]: ...


class _DependencyConfigProtocol(Protocol):
    @property
    def pipeline(self) -> str: ...

    @property
    def join_keys(self) -> tuple[str, ...]: ...

    @property
    def uses_seed_keys(self) -> bool: ...


class _EnricherConfigProtocol(Protocol):
    @property
    def pipeline(self) -> str: ...

    @property
    def join_keys(self) -> tuple[str, ...]: ...


class CompositeConfigProtocol(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def seed(self) -> _SeedConfigProtocol: ...

    @property
    def enrichers(self) -> Sequence[_EnricherConfigProtocol]: ...

    @property
    def dependencies(self) -> Sequence[_DependencyConfigProtocol]: ...


def coerce_composite_collections(config: CompositeConfigProtocol) -> None:
    """Coerce mutable list inputs to tuples for immutable dataclass fields.

    Args:
        config: CompositeConfig instance whose list fields will be coerced in-place.
    """
    if isinstance(config.enrichers, list):
        object.__setattr__(config, "enrichers", tuple(config.enrichers))
    if isinstance(config.dependencies, list):
        object.__setattr__(config, "dependencies", tuple(config.dependencies))


def validate_composite_config(config: CompositeConfigProtocol) -> None:
    """Validate all CompositeConfig invariants.

    Args:
        config: CompositeConfig instance to validate.
    """
    if not config.name:
        raise ValueError("composite name cannot be empty")
    if not config.version:
        raise ValueError("composite version cannot be empty")
    if not config.enrichers and not config.dependencies:
        raise ValueError("composite must have at least one enricher or dependency")
    _validate_join_keys(config)
    _validate_dependency_join_keys(config)
    _validate_unique_enrichers(config)
    _validate_unique_dependencies(config)


def _validate_join_keys(config: CompositeConfigProtocol) -> None:
    """Validate that enricher join keys exist in seed output keys."""
    if not config.enrichers:
        return
    seed_keys = set(config.seed.output_keys)
    for enricher in config.enrichers:
        for key in enricher.join_keys:
            if key not in seed_keys:
                raise ValueError(
                    f"Enricher {enricher.pipeline} join_key '{key}' "
                    f"not found in seed output_keys: {config.seed.output_keys}"
                )


def _validate_dependency_join_keys(config: CompositeConfigProtocol) -> None:
    """Validate dependency join keys for seed-key dependencies."""
    seed_keys = set(config.seed.output_keys)
    for dependency in config.dependencies:
        if not dependency.uses_seed_keys:
            continue
        for key in dependency.join_keys:
            if key not in seed_keys:
                raise ValueError(
                    f"Dependency {dependency.pipeline} join_key '{key}' "
                    f"not found in seed output_keys: {config.seed.output_keys}"
                )


def _validate_unique_enrichers(config: CompositeConfigProtocol) -> None:
    """Validate that enricher pipeline names are unique."""
    if not config.enrichers:
        return
    seen: set[str] = set()
    duplicates: set[str] = set()
    for enricher in config.enrichers:
        (duplicates if enricher.pipeline in seen else seen).add(enricher.pipeline)
    if duplicates:
        raise ValueError(f"Duplicate enricher pipelines: {duplicates}")


def _validate_unique_dependencies(config: CompositeConfigProtocol) -> None:
    """Validate that dependency pipeline names are unique."""
    names = [dependency.pipeline for dependency in config.dependencies]
    if len(names) != len(set(names)):
        duplicates = [name for name in names if names.count(name) > 1]
        raise ValueError(f"Duplicate dependency pipelines: {set(duplicates)}")
