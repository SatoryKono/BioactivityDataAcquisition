"""Loader for ChEMBL protein-class L1 target-type JSON asset."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from bioetl.domain.mapping.protein_class_target_type import (
    ProteinClassTargetTypeMappingData,
    ProteinClassTopLevelMappingEntry,
)

__all__ = ["ProteinClassTargetTypeMappingLoader"]


class ProteinClassTargetTypeMappingLoader:
    """Load versioned protein-class target type mapping data from configs."""

    def __init__(self, configs_root: Path) -> None:
        self._asset_path = (
            configs_root / "enums" / "protein_class_l1_target_type.asset.v1.json"
        )

    def load(self) -> ProteinClassTargetTypeMappingData:
        """Read and parse the JSON asset into immutable domain mapping data."""
        raw = json.loads(self._asset_path.read_text("utf-8"))
        if not isinstance(raw, Mapping):
            raise ValueError(f"Invalid protein class mapping asset: {self._asset_path}")
        rows = raw.get("rows")
        if not isinstance(rows, list):
            raise ValueError(f"Invalid protein class mapping asset: {self._asset_path}")
        return ProteinClassTargetTypeMappingData(
            mapping_version=_required_text(raw, "mapping_version"),
            entries=tuple(_entry_from_row(row) for row in rows),
        )


def _entry_from_row(row: object) -> ProteinClassTopLevelMappingEntry:
    if not isinstance(row, list) or len(row) < 3:
        raise ValueError("protein class mapping rows must be arrays with 3+ columns")
    return ProteinClassTopLevelMappingEntry(
        raw_label=str(row[0]),
        canonical_l1=str(row[1]),
        counts_for_target_type=bool(row[2]),
    )


def _required_text(
    raw: Mapping[str, object], key: str
) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"protein class mapping asset missing {key}")
    return value.strip()
