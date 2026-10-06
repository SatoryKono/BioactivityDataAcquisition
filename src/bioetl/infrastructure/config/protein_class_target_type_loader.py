"""Loader for ChEMBL protein-class L1 target-type JSON asset."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path

from bioetl.domain.mapping.protein_class_target_type import (
    ProteinClassTargetTypeMappingData,
    ProteinClassTopLevelMappingEntry,
    current_protein_class_target_type_mapping,
)
from bioetl.domain.types import JsonDict

__all__ = [
    "ProteinClassTargetTypeMappingLoader",
    "freeze_target_mapping",
    "restore_target_mapping",
]


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


def _required_text(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"protein class mapping asset missing {key}")
    return value.strip()


def freeze_target_mapping() -> JsonDict:
    """Capture the exact initialized mapping consumed by target dependency joins."""
    mapping = current_protein_class_target_type_mapping()
    return {
        "mapping_version": mapping.mapping_version,
        "entries": [asdict(entry) for entry in mapping.entries],
        "non_counting_classes": sorted(mapping.non_counting_classes),
    }


def restore_target_mapping(payload: JsonDict) -> ProteinClassTargetTypeMappingData:
    """Reject sealed mapping data that cannot restore the target collaborator."""
    version = payload.get("mapping_version")
    entries = payload.get("entries")
    ignored = payload.get("non_counting_classes")
    if not isinstance(version, str) or not isinstance(entries, list):
        raise ValueError("composite_replay_target_mapping_invalid")
    if not isinstance(ignored, list) or not all(isinstance(x, str) for x in ignored):
        raise ValueError("composite_replay_target_mapping_invalid")
    restored = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "raw_label",
            "canonical_l1",
            "counts_for_target_type",
        }:
            raise ValueError("composite_replay_target_mapping_invalid")
        raw, canonical, counting = (
            entry["raw_label"],
            entry["canonical_l1"],
            entry["counts_for_target_type"],
        )
        if (
            not isinstance(raw, str)
            or not isinstance(canonical, str)
            or not isinstance(counting, bool)
        ):
            raise ValueError("composite_replay_target_mapping_invalid")
        restored.append(ProteinClassTopLevelMappingEntry(raw, canonical, counting))
    return ProteinClassTargetTypeMappingData(
        version, tuple(restored), frozenset(ignored)
    )
