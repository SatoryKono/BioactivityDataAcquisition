"""Classification and FK-closure checks for target migration candidates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
)
from bioetl.infrastructure.adapters.iuphar.adapter import (
    IupharTargetClassificationAdapter,
)
from bioetl.infrastructure.adapters.iuphar.snapshot_models import LoadedIupharProfile
from bioetl.infrastructure.storage.target_migration_row_ops import (
    by_id,
    hash_input,
    read_delta,
    scoped_target_hash,
)


def verify_candidate_hashes(
    rows: Sequence[Mapping[str, object]], include_fields: tuple[str, ...]
) -> None:
    """Reject arbitrary or stale candidate hashes, including classification drift."""
    profile = target_v31_normalization_profile()
    for row in rows:
        if row.get("content_hash") != scoped_target_hash(row, include_fields, profile):
            raise ValueError("candidate V31 content hash verification failed")


def verify_source_classifications(
    layers: Mapping[str, list[dict[str, object]]], profile: LoadedIupharProfile
) -> None:
    """Reclassify original Silver inputs, then bind both candidate projections."""
    adapter = IupharTargetClassificationAdapter(profile)
    silver_ids = {key[0] for key in by_id(layers["silver"])}
    for layer, rows in layers.items():
        for (target_id, version), row in by_id(rows).items():
            if layer == "gold" and target_id not in silver_ids:
                raise ValueError(
                    "candidate Gold target has no classified Silver source"
                )
            business = {
                key: value
                for key, value in hash_input(row).items()
                if key not in TARGET_CLASSIFICATION_FIELDS
            }
            result = adapter.classify_record(
                business,
                input_row_id=f"migration:{layer}:{target_id}:{version}",
                run_id="migration-validation",
                run_started_at="1970-01-01T00:00:00+00:00",
            )
            assert_classification_projection(row, result.projection)


def assert_classification_projection(
    row: Mapping[str, object], expected: Mapping[str, str | None]
) -> None:
    """Keep direct, local and effective fields equal to the admitted classifier."""
    for field in TARGET_CLASSIFICATION_FIELDS:
        if row.get(field) != expected[field]:
            raise ValueError(
                f"candidate classification differs from admitted source: {field}"
            )


def assert_candidate_cohort_closure(
    paths: dict[str, Path], gold_rows: Sequence[Mapping[str, object]]
) -> None:
    """Require every final assay FK, preserving additional Gold targets."""
    assay_targets = {
        row["target_id"]
        for row in read_delta(paths["assay"])
        if row.get("target_id") is not None and row.get("_is_current", True)
    }
    current_target_ids = {
        key[0] for key, row in by_id(gold_rows).items() if row.get("_is_current", True)
    }
    if not assay_targets.issubset(current_target_ids):
        raise ValueError("baseline assay/target foreign-key closure failed")


__all__ = [
    "assert_candidate_cohort_closure",
    "assert_classification_projection",
    "verify_candidate_hashes",
    "verify_source_classifications",
]
