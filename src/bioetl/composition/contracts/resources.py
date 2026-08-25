"""Resource-management contracts for interface callers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from bioetl.composition.contracts.services import JsonDict


class QuarantineRuntimeServiceProtocol(Protocol):
    """Minimal quarantine runtime-service contract exposed by resource APIs."""

    def inspect(
        self,
        limit: int = 100,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> Awaitable[list[JsonDict]]:
        """Inspect quarantined records."""
        ...

    def get_stats(
        self,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> Awaitable[JsonDict]:
        """Return aggregate quarantine statistics."""
        ...


class CheckpointRuntimeServiceProtocol(Protocol):
    """Minimal checkpoint runtime-service contract exposed by resource APIs."""

    def list_all(self) -> Awaitable[list[object]]:
        """List available checkpoints."""
        ...


class MedallionLifecycleServiceProtocol(Protocol):
    """Minimal lifecycle service contract used by maintenance entrypoints."""

    def vacuum(
        self,
        *,
        table: str,
        retention_days: int,
        dry_run: bool,
    ) -> Awaitable[int]:
        """Vacuum one table."""
        ...

    def archive(
        self,
        *,
        table: str,
        target_path: str,
        remove_source: bool,
    ) -> Awaitable[int]:
        """Archive one table."""
        ...


class CleanupPreviewProtocol(Protocol):
    """Minimal preview payload contract for cleanup dry-run operations."""

    @property
    def total_files(self) -> int:
        """Return the number of files affected by the cleanup."""
        ...


class CleanupServiceProtocol(Protocol):
    """Minimal cleanup service contract used by preview entrypoints."""

    def preview(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> Awaitable[CleanupPreviewProtocol]:
        """Preview cleanup impact for the requested tables."""
        ...
