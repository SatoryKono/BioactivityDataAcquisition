"""Loader for publication type classification JSON asset."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.domain.mapping.classification_data import ClassificationData

_DASH = "\u2014"  # em-dash sentinel for "no mapping"


def _build_row_index(rows: list[list[str]], *, col: int) -> dict[str, int]:
    """Build provider lookup key → 1-based row index from JSON rows.

    Replicates the codegen script logic: skip dash sentinels,
    strip trailing ``*``, lowercase keys, first-occurrence wins.

    Returns:
        Dictionary mapping normalized provider key strings to 1-based row indices.
    """
    mapping: dict[str, int] = {}
    for row_idx, row in enumerate(rows, start=1):
        raw_key = row[col]
        if raw_key == _DASH:
            continue
        key = raw_key.rstrip("*").lower()
        if key not in mapping:
            mapping[key] = row_idx
    return mapping


class PublicationTypeClassificationLoader:
    """Load ``ClassificationData`` from the versioned JSON asset."""

    def __init__(self, configs_root: Path) -> None:
        self._asset_path = (
            configs_root / "enums" / "publication_type_classification.asset.v1.json"
        )

    def load(self) -> ClassificationData:
        """Read and parse the JSON asset into a domain value object.

        Returns:
            ClassificationData instance with all provider row indices populated.
        """
        raw = json.loads(self._asset_path.read_text("utf-8"))
        rows: list[list[str]] = raw["rows"]

        entry_cores = tuple((r[0], r[1], r[2]) for r in rows)
        openalex_idx = _build_row_index(rows, col=3)
        crossref_idx = _build_row_index(rows, col=4)
        pubmed_idx = _build_row_index(rows, col=5)
        s2_idx = _build_row_index(rows, col=6)

        return ClassificationData(
            entry_cores=entry_cores,
            openalex_row_index=openalex_idx,
            crossref_row_index=crossref_idx,
            pubmed_row_index=pubmed_idx,
            s2_row_index=s2_idx,
        )
