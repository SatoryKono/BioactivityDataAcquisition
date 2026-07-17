"""Protocol definitions for CompositeConfig serialization."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy


class _SeedConfigProtocol(Protocol):
    @property
    def pipeline(self) -> str: ...

    @property
    def output_keys(self) -> tuple[str, ...]: ...

    @property
    def silver_table(self) -> str: ...


class _DependencyConfigProtocol(Protocol):
    @property
    def pipeline(self) -> str: ...

    @property
    def join_keys(self) -> tuple[str, ...]: ...

    @property
    def required(self) -> bool: ...

    @property
    def timeout_seconds(self) -> int: ...

    @property
    def silver_table(self) -> str | None: ...

    @property
    def filter_fields(self) -> tuple[str, ...] | None: ...


class _EnricherConfigProtocol(Protocol):
    @property
    def pipeline(self) -> str: ...

    @property
    def join_keys(self) -> tuple[str, ...]: ...

    @property
    def required(self) -> bool: ...

    @property
    def timeout_seconds(self) -> int: ...


class _MergeConfigProtocol(Protocol):
    @property
    def strategy(self) -> MergeStrategy: ...

    @property
    def conflict_resolution(self) -> ConflictResolution: ...

    @property
    def output_silver_path(self) -> str: ...

    @property
    def output_gold_path(self) -> str: ...

    @property
    def sort_by_silver(self) -> tuple[str, ...]: ...

    @property
    def sort_by_gold(self) -> tuple[str, ...]: ...


class CompositeConfigProtocol(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def seed(self) -> _SeedConfigProtocol: ...

    @property
    def dependencies(self) -> Sequence[_DependencyConfigProtocol]: ...

    @property
    def enrichers(self) -> Sequence[_EnricherConfigProtocol]: ...

    @property
    def merge(self) -> _MergeConfigProtocol: ...
