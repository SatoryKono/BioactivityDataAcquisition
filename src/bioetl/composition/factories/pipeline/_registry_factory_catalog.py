"""Lazy pipeline factory catalog support for the public registry facade."""

from __future__ import annotations

import threading
from collections.abc import Iterator, Mapping

from bioetl.composition.factories.pipeline.contract_validator import create_factory
from bioetl.composition.factories.pipeline.registry_manifest import PIPELINE_CONFIGS

__all__ = ["LazyFactoryCatalog", "list_pipeline_names"]


def _build_configs_by_name() -> dict[str, object]:
    """Index pipeline configs by name; fail closed on duplicate pipeline_name."""
    by_name: dict[str, object] = {}
    for config in PIPELINE_CONFIGS:
        name = config.pipeline_name
        if name in by_name:
            raise RuntimeError(
                f"Duplicate pipeline_name in PIPELINE_CONFIGS: {name!r}"
            )
        by_name[name] = config
    return by_name


_CONFIGS_BY_NAME = _build_configs_by_name()


class LazyFactoryCatalog(Mapping[str, object]):
    """Read-only lazy pipeline factory catalog."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache: dict[str, object] = {}

    def __getitem__(self, pipeline_name: str) -> object:
        if pipeline_name in self._cache:
            return self._cache[pipeline_name]
        with self._lock:
            if pipeline_name in self._cache:
                return self._cache[pipeline_name]
            try:
                config = _CONFIGS_BY_NAME[pipeline_name]
            except KeyError as exc:
                raise KeyError(pipeline_name) from exc
            factory = create_factory(config)
            self._cache[pipeline_name] = factory
            return factory

    def __iter__(self) -> Iterator[str]:
        return iter(_CONFIGS_BY_NAME)

    def __len__(self) -> int:
        return len(_CONFIGS_BY_NAME)


def list_pipeline_names() -> list[str]:
    """Return available pipeline names in canonical sorted order."""
    return sorted(_CONFIGS_BY_NAME)
