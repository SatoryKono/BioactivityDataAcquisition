"""Bronze cleanup metrics emission and shared group journal types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

from bioetl.domain.ports import MetricsPort

from .cleanup_core import valid_bronze_scope_name
from .cleanup_support import date_dir_name_is_older, is_owned_artifact
from .validation_mixin import BronzeWriterValidationMixin


def emit_cleanup_outcome_metrics(metrics: MetricsPort, result: dict[str, int]) -> None:
    """Emit retained artifact counts via registered metric families."""
    labels = {"operation": "cleanup"}
    if result["files_skipped"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_files_skipped_total",
            result["files_skipped"],
            labels,
        )
    if result["bytes_skipped"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_bytes_skipped_total",
            result["bytes_skipped"],
            labels,
        )
    if result["files_conflicted"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_files_conflicted_total",
            result["files_conflicted"],
            labels,
        )
    if result["bytes_conflicted"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_bytes_conflicted_total",
            result["bytes_conflicted"],
            labels,
        )
    if result["files_failed"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_files_failed_total",
            result["files_failed"],
            labels,
        )
    if result["bytes_failed"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_bytes_failed_total",
            result["bytes_failed"],
            labels,
        )
    if result["directories_skipped"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_directories_skipped_total",
            result["directories_skipped"],
            labels,
        )
    if result["directories_conflicted"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_directories_conflicted_total",
            result["directories_conflicted"],
            labels,
        )
    if result["directories_failed"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_directories_failed_total",
            result["directories_failed"],
            labels,
        )


class GroupJournalConflict(OSError):
    """The journal or a group member cannot be proven to be the original."""

    operation_id: str | None = None
    removed: int = 0
    possibly_unlinked: int = 0
    removed_bytes: int = 0
    possibly_unlinked_bytes: int = 0
    phase: str = "read"


class GroupJournalFailure(OSError):
    """An I/O barrier failed after a known number of successful unlinks."""

    def __init__(
        self,
        operation_id: str,
        removed: int,
        phase: str,
        possibly_unlinked: int,
        removed_bytes: int = 0,
        possibly_unlinked_bytes: int = 0,
    ):
        super().__init__(
            f"group {operation_id} failed at {phase}; durably_removed={removed}; "
            f"possibly_unlinked={possibly_unlinked}"
        )
        self.operation_id = operation_id
        self.removed = removed
        self.phase = phase
        self.possibly_unlinked = possibly_unlinked
        self.removed_bytes = removed_bytes
        self.possibly_unlinked_bytes = possibly_unlinked_bytes


@dataclass(slots=True)
class GroupRecoveryResult:
    """Per-call durable removals and unconfirmed unlinks; never cumulative."""

    removed: int = 0
    possibly_unlinked: int = 0
    removed_bytes: int = 0
    possibly_unlinked_bytes: int = 0
    phase: str = "read"


@dataclass(frozen=True, slots=True)
class GroupSpec:
    """Exact writer scope and calendar eligibility for one complete group."""

    provider: str
    entity: str
    date: str
    batch_id: str
    cutoff: str
    flat_structure: bool = False

    def names(self) -> dict[str, str]:
        """Return owned artifact names; raise ValueError for invalid group scope."""
        if not all(valid_bronze_scope_name(x) for x in (self.provider, self.entity)):
            raise ValueError("invalid Bronze provider/entity")
        for value in (self.date, self.cutoff):
            try:
                if datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") != value:
                    raise ValueError("non-canonical date")
            except ValueError as exc:
                raise ValueError("invalid Bronze date/cutoff") from exc
        if not date_dir_name_is_older(self.date, self.cutoff):
            raise ValueError("group is not older than cutoff")
        try:
            if str(UUID(self.batch_id)) != self.batch_id:
                raise ValueError("non-canonical batch ID")
        except ValueError as exc:
            raise ValueError("invalid batch ID") from exc
        payload = f"batch_{self.date}_{self.batch_id}.jsonl.zst"
        if not is_owned_artifact(payload, date_name=self.date):
            raise ValueError("group does not match writer naming")
        return {
            "copy": payload.removesuffix(".zst"),
            "payload": payload,
            "sidecar": f"{payload}.meta.json",
        }

    def relative_date(self) -> Path:
        """Return the relative date directory; reject invalid layout or scope."""
        if type(self.flat_structure) is not bool:
            raise ValueError("invalid Bronze layout flag")
        payload = self.names()["payload"]
        resolver = BronzeWriterValidationMixin()
        resolver._flat_structure = self.flat_structure
        return Path(
            resolver._resolve_bronze_path(
                self.provider, self.entity, self.date, payload
            )
        ).parent
