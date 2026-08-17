"""Domain types for debug export audit packs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.immutability import deep_freeze_json

__all__ = ["DebugExportPack", "DebugExportResult"]


@dataclass(frozen=True, slots=True)
class DebugExportPack:
    """Deterministic in-memory representation of one debug export run pack."""

    run_id: str
    pipeline_id: str
    provider_id: str
    workflow_id: str
    manifest_id: str | None
    status: str
    output_root: str
    formats: tuple[str, ...]
    include_bom: bool
    max_rows_per_sheet: int
    created_at: datetime
    tables: Mapping[str, tuple[Mapping[str, object], ...]]
    reason_dictionary: tuple[Mapping[str, str], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "tables", deep_freeze_json(dict(self.tables)))
        object.__setattr__(
            self,
            "reason_dictionary",
            deep_freeze_json(list(self.reason_dictionary)),
        )


@dataclass(frozen=True, slots=True)
class DebugExportResult:
    """Persisted debug export artifact metadata."""

    root_path: str
    manifest_path: str
    debug_export_hash: str
    file_paths: tuple[str, ...] = ()
