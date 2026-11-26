"""Classification and FK-closure checks for target migration candidates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from bioetl.domain.config.target_classification import (
    TARGET_CLASSIFICATION_DETAIL_FIELDS,
    TARGET_CLASSIFICATION_FIELDS,
)
from bioetl.domain.normalization.profiles.base import NormalizationProfile
from bioetl.domain.normalization.profiles.chembl_target import CHEMBL_TARGET_PROFILE
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
)
from bioetl.infrastructure.adapters.iuphar.adapter import (
    IupharTargetClassificationAdapter,
)
from bioetl.infrastructure.adapters.iuphar.evidence_store import (
    LocalTargetClassificationEvidenceStore,
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


def classification_fields(contract: str) -> tuple[str, ...]:
    """Return the additive columns owned by the selected physical contract."""
    if contract == "3.2.0":
        return (*TARGET_CLASSIFICATION_FIELDS, *TARGET_CLASSIFICATION_DETAIL_FIELDS)
    return TARGET_CLASSIFICATION_FIELDS


def classification_input(
    row: Mapping[str, object], fields: tuple[str, ...]
) -> dict[str, object]:
    """Exclude derived classification fields from the inputs to a fresh classification."""
    return {key: value for key, value in hash_input(row).items() if key not in fields}


def candidate_input_row_id(target_id: str) -> str:
    """Use the same row identity the candidate builder stored."""
    return "candidate:" + target_id


def _classify_candidate_rows(
    adapter: IupharTargetClassificationAdapter,
    store: LocalTargetClassificationEvidenceStore,
    old_silver: Sequence[dict[str, object]],
    old_gold: Sequence[dict[str, object]],
    columns: tuple[str, ...],
    fields: tuple[str, ...],
    normalization: NormalizationProfile,
    *,
    run_id: str,
    run_started_at: str,
    refresh_v31: bool,
) -> tuple[
    dict[str, dict[str, str | None]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[str],
]:
    """Classify frozen Silver rows and project them onto Gold rows."""
    projections: dict[str, dict[str, str | None]] = {}
    new_silver: list[dict[str, object]] = []
    row_ids: list[str] = []
    for row in old_silver:
        identity = str(row["target_id"])
        result = adapter.classify_record(
            classification_input(row, columns),
            input_row_id=candidate_input_row_id(identity),
            run_id=run_id,
            run_started_at=run_started_at,
        )
        projected = {name: result.projection[name] for name in columns}
        projections[identity] = projected
        updated = {**row, **projected}
        updated["content_hash"] = scoped_target_hash(updated, fields, normalization)
        new_silver.append(updated)
        store.publish_result(result, run_id=run_id, batch_id="frozen-silver")
        row_ids.append(result.input_row_id)
    new_gold: list[dict[str, object]] = []
    for row in old_gold:
        if refresh_v31 and row.get("_is_current") is False:
            new_gold.append(row)
            continue
        updated = {**row, **projections[str(row["target_id"])]}
        updated["content_hash"] = scoped_target_hash(updated, fields, normalization)
        new_gold.append(updated)
    return projections, new_silver, new_gold, row_ids


def _refresh_mutable_fields(
    previous: Mapping[str, object],
    classification: frozenset[str],
) -> frozenset[str]:
    """Closed Gold rows stay byte-identical; current rows reclassify."""
    if previous.get("_is_current") is False:
        return frozenset()
    return frozenset({"content_hash"}) | classification


def _compare_single_row(
    key: tuple[str, int | None],
    previous: Mapping[str, object],
    current: Mapping[str, object],
    *,
    legacy_include_fields: tuple[str, ...],
    source_fields: tuple[str, ...],
    source_profile: NormalizationProfile,
    classification: frozenset[str],
    refresh_v31: bool,
) -> None:
    """Check one frozen row against its candidate, including V31 hashes."""
    mutable = frozenset({"content_hash"})
    if refresh_v31:
        mutable = _refresh_mutable_fields(previous, classification)
    _assert_legacy_values(str(key), previous, current, mutable_fields=mutable)
    old_hash = scoped_target_hash(previous, source_fields, source_profile)
    if refresh_v31:
        old_legacy_hash = scoped_target_hash(
            previous, legacy_include_fields, CHEMBL_TARGET_PROFILE
        )
    else:
        old_legacy_hash = old_hash
    new_legacy_hash = scoped_target_hash(
        current, legacy_include_fields, CHEMBL_TARGET_PROFILE
    )
    if old_hash != previous.get("content_hash") or old_legacy_hash != new_legacy_hash:
        raise ValueError(
            "source V31 hash equivalence failed"
            if refresh_v31
            else "legacy 3.0 hash equivalence failed"
        )


def _assert_restored_values(
    key: str,
    published: Mapping[str, object],
    current: Mapping[str, object],
    *,
    contract: str,
) -> None:
    """Keep a published restoration intact apart from its candidate hash and classification."""
    for field, value in published.items():
        if field == "content_hash":
            continue
        if (
            field not in current
            or type(current[field]) is not type(value)
            or current[field] != value
        ):
            raise ValueError(f"restored target changed: {key}/{field}")
    unexpected = set(current) - set(published) - set(classification_fields(contract))
    if unexpected:
        raise ValueError(f"restored target gained unexpected fields: {key}")


def _assert_legacy_values(
    key: str,
    previous: Mapping[str, object],
    current: Mapping[str, object],
    *,
    mutable_fields: frozenset[str] = frozenset({"content_hash"}),
) -> None:
    """Preserve every old physical value, including storage/runtime metadata."""
    if previous.get("entity_id") != current.get("entity_id"):
        raise ValueError(f"candidate changed legacy entity_id: {key}")
    for field, value in previous.items():
        if field in mutable_fields:
            continue
        if (
            field not in current
            or type(current[field]) is not type(value)
            or current[field] != value
        ):
            kind = "technical" if field.startswith("_") else "business"
            raise ValueError(f"candidate changed legacy {kind} field: {key}/{field}")


def verify_source_classifications(
    layers: Mapping[str, list[dict[str, object]]],
    profile: LoadedIupharProfile,
    contract: str = "3.1.0",
    *,
    preserve_closed_gold: bool = False,
) -> None:
    """Reclassify Silver and verify the corresponding Gold projection.

    An initial migration projects Silver's classification onto every Gold version.
    A V31 refresh verifies the projection for current Gold versions.
    """
    adapter = IupharTargetClassificationAdapter(profile, table_contract=contract)
    fields = classification_fields(contract)
    projections: dict[str, Mapping[str, str | None]] = {}
    for (target_id, _version), row in by_id(layers["silver"]).items():
        result = adapter.classify_record(
            classification_input(row, fields),
            input_row_id=candidate_input_row_id(target_id),
            run_id="migration-validation",
            run_started_at="1970-01-01T00:00:00+00:00",
        )
        assert_classification_projection(row, result.projection, fields=fields)
        previous = projections.get(target_id)
        if previous is not None and dict(previous) != dict(result.projection):
            raise ValueError(
                "candidate Silver versions disagree on admitted classification"
            )
        projections[target_id] = result.projection
    for (target_id, _version), row in by_id(layers["gold"]).items():
        if preserve_closed_gold and row.get("_is_current") is False:
            continue
        expected = projections.get(target_id)
        if expected is None:
            raise ValueError("candidate Gold target has no classified Silver source")
        assert_classification_projection(row, expected, fields=fields)


def assert_classification_projection(
    row: Mapping[str, object],
    expected: Mapping[str, str | None],
    *,
    fields: tuple[str, ...] | None = None,
) -> None:
    """Keep direct, local and effective fields equal to the admitted classifier."""
    for field in fields or classification_fields(
        "3.2.0"
        if any(name in expected for name in TARGET_CLASSIFICATION_DETAIL_FIELDS)
        else "3.1.0"
    ):
        if field not in expected or field not in row or row[field] != expected[field]:
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
    "classification_fields",
    "classification_input",
    "classify_target_absence",
    "current_assay_target_ids",
    "current_target_ids",
    "plan_target_fk_restoration",
    "reject_unverified_fk_addition",
    "verify_candidate_hashes",
    "verify_source_classifications",
]
