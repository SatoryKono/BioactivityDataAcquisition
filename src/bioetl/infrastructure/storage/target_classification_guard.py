"""Prevent legacy backfill clear from destroying an enriched target table."""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS


def assert_target_table_compatibility(
    *,
    silver_path: Path,
    gold_path: Path,
    mode: str,
) -> None:
    """Check both existing tables before the runner can clear either one.

    Empty candidate destinations are allowed. Enrich against V30 requires the
    explicit paired migration; off/shadow against V31 requires a real rollback.
    """
    from deltalake import DeltaTable

    if mode not in {"off", "shadow", "enrich"}:
        raise ValueError("unknown target classification mode")
    required = set(TARGET_CLASSIFICATION_FIELDS)
    for path in (silver_path, gold_path):
        if not path.exists() or not any(path.iterdir()):
            continue
        if not (path / "_delta_log").is_dir():
            raise ValueError(
                "unrecognised target directory; refusing pre-backfill clear"
            )
        fields = {field.name for field in DeltaTable(str(path)).schema().fields}
        present = required.intersection(fields)
        if present and present != required:
            raise ValueError(
                "incomplete target classification schema; recovery required"
            )
        if mode == "enrich" and not present:
            raise ValueError(
                "V30 target requires complete-cohort migration before enrich"
            )
        if mode in {"off", "shadow"} and present:
            raise ValueError(
                "V31 target requires physical rollback before legacy writes"
            )


__all__ = ["assert_target_table_compatibility"]
