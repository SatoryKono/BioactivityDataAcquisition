"""Classification and FK-closure checks for target migration candidates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from bioetl.domain.config.target_classification import (
    TARGET_CLASSIFICATION_DETAIL_FIELDS,
    TARGET_CLASSIFICATION_FIELDS,
)
from bioetl.domain.normalization.profiles.base import NormalizationProfile
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
)
from bioetl.infrastructure.adapters.iuphar.adapter import (
    IupharTargetClassificationAdapter,
)
from bioetl.infrastructure.adapters.iuphar.snapshot_models import LoadedIupharProfile
from bioetl.infrastructure.storage.target_fk_restoration_plan import (
    ADMISSIBLE_ABSENCE_REASONS,
    ASSAY_TARGET_CLOSURE_ERROR,
    BLOCKING_ABSENCE_REASONS,
    TargetAbsenceFinding,
    TargetFKRestorationPlan,
    TargetRecoveryInput,
    canonical_row_sha256,
    classify_target_absence,
    current_assay_target_ids,
    current_target_ids,
    plan_target_fk_restoration,
)
from bioetl.infrastructure.storage.target_migration_row_ops import (
    by_id,
    hash_input,
    read_delta,
    scoped_target_hash,
)


def verify_candidate_hashes(
    rows: Sequence[Mapping[str, object]],
    include_fields: tuple[str, ...],
    profile: NormalizationProfile | None = None,
) -> None:
    """Reject arbitrary or stale candidate hashes, including classification drift."""
    selected = profile or target_v31_normalization_profile()
    for row in rows:
        if row.get("content_hash") != scoped_target_hash(row, include_fields, selected):
            raise ValueError("candidate V31 content hash verification failed")


def _business_without_classification(
    row: Mapping[str, object],
) -> dict[str, object]:
    return {
        key: value
        for key, value in hash_input(row).items()
        if key not in TARGET_CLASSIFICATION_FIELDS
    }


def candidate_input_row_id(target_id: str) -> str:
    """Use the same row identity the candidate builder stored."""
    return "candidate:" + target_id


def verify_source_classifications(
    layers: Mapping[str, list[dict[str, object]]], profile: LoadedIupharProfile
) -> None:
    """Reclassify Silver, then require every Gold version to carry that projection.

    Historical Gold business fields are not classified again. The documented
    migration copies the current Silver projection onto each Gold version.
    """
    adapter = IupharTargetClassificationAdapter(profile)
    projections: dict[str, Mapping[str, str | None]] = {}
    for (target_id, _version), row in by_id(layers["silver"]).items():
        result = adapter.classify_record(
            _business_without_classification(row),
            input_row_id=candidate_input_row_id(target_id),
            run_id="migration-validation",
            run_started_at="1970-01-01T00:00:00+00:00",
        )
        assert_classification_projection(row, result.projection)
        previous = projections.get(target_id)
        if previous is not None and dict(previous) != dict(result.projection):
            raise ValueError(
                "candidate Silver versions disagree on admitted classification"
            )
        projections[target_id] = result.projection
    for (target_id, _version), row in by_id(layers["gold"]).items():
        expected = projections.get(target_id)
        if expected is None:
            raise ValueError("candidate Gold target has no classified Silver source")
        assert_classification_projection(row, expected)


def assert_classification_projection(
    row: Mapping[str, object], expected: Mapping[str, str | None]
) -> None:
    """Keep direct, local and effective fields equal to the admitted classifier."""
    fields = TARGET_CLASSIFICATION_FIELDS
    if any(name in expected for name in TARGET_CLASSIFICATION_DETAIL_FIELDS):
        fields = (
            *fields,
            *(name for name in TARGET_CLASSIFICATION_DETAIL_FIELDS if name in expected),
        )
    for field in fields:
        if row.get(field) != expected[field]:
            raise ValueError(
                f"candidate classification differs from admitted source: {field}"
            )


def assert_candidate_cohort_closure(
    paths: dict[str, Path], gold_rows: Sequence[Mapping[str, object]]
) -> None:
    """Require every final assay FK, preserving additional Gold targets."""
    assay_targets = current_assay_target_ids(read_delta(paths["assay"]))
    if not assay_targets.issubset(current_target_ids(gold_rows)):
        raise ValueError(ASSAY_TARGET_CLOSURE_ERROR)


_ABSENCE_REASONS = frozenset(
    {"limited_sample", "incomplete_load", "selection_filter", "contract_mismatch"}
)


def reject_unverified_fk_addition(record: Mapping[str, object]) -> None:
    """Refuse a placeholder or an unresolved contract row. Nothing is written."""
    if record.get("placeholder") or not record.get("source_sha256"):
        raise ValueError("unverified target addition")
    reason = record.get("absence_reason")
    if reason not in _ABSENCE_REASONS:
        raise ValueError("target absence reason is not recorded")
    if reason == "contract_mismatch" and record.get("contract_decision") != "resolved":
        raise ValueError("unresolved target contract mismatch")


__all__ = [
    "ADMISSIBLE_ABSENCE_REASONS",
    "ASSAY_TARGET_CLOSURE_ERROR",
    "BLOCKING_ABSENCE_REASONS",
    "TargetAbsenceFinding",
    "TargetFKRestorationPlan",
    "TargetRecoveryInput",
    "assert_candidate_cohort_closure",
    "assert_classification_projection",
    "candidate_input_row_id",
    "canonical_row_sha256",
    "classify_target_absence",
    "current_assay_target_ids",
    "current_target_ids",
    "plan_target_fk_restoration",
    "reject_unverified_fk_addition",
    "verify_candidate_hashes",
    "verify_source_classifications",
]
