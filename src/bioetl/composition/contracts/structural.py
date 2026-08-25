"""Structural typed views used by composition bootstrap/factories."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.ports import AuditPort


class ModelDumpable(Protocol):
    def model_dump(self) -> dict[str, object]: ...


@runtime_checkable
class ModelDumpProvider(Protocol):
    def model_dump(self) -> object:
        """Return a serializable configuration payload."""
        ...


@runtime_checkable
class ModelDumpHost(Protocol):
    def model_dump(
        self,
        *,
        mode: str = "python",
        exclude_none: bool = False,
    ) -> Mapping[str, object]: ...


@runtime_checkable
class DictHost(Protocol):
    def dict(self, *, exclude_none: bool = False) -> Mapping[str, object]: ...


class AuditRequiredFn(Protocol):
    def __call__(self, *, audit: AuditPort | None, audit_required: bool) -> bool: ...


class ControlPlaneSettingsFn(Protocol):
    def __call__(self, *, control_plane: object | None) -> tuple[str, bool, bool]: ...


class CandidatePathsFactory(Protocol):
    def __call__(
        self,
        *,
        provider: str,
        entity: str,
        repo_root: Path,
    ) -> list[str]: ...
