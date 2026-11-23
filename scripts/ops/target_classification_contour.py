"""Separate shadow, enrich, migration, live, and biological acceptance.

The report reads attested evidence plus files and repository configs. It does
not promote tables, switch ``mode``, or treat a matched count as biological
qualification. ``READY`` means the technical gates passed while the canonical
entity config is still ``off``. ``LIVE_ACCEPTED`` additionally requires a
promoted enrich config and a readback of the next run.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

import yaml

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.infrastructure.storage.atomic import atomic_write_text
from scripts.engineering.common.repo_paths import confined_io_path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_SCHEMA = "bioetl_iuphar_main_contour_evidence_v1"
REPORT_SCHEMA = "bioetl_iuphar_main_contour_report_v1"
PHYSICAL_CONTRACT = "legacy_physical_target_v30_to_v31_v1"
ENRICH_CONTRACT = "3.1.0"
SHADOW_CONTRACT = "3.0.0"
SMOKE_LIMIT = 1000
_SHA256 = 64
_COMMIT_SHA = 40
_TARGET_YAML = "target.yaml"
_IS_CURRENT = "_is_current"
_ENRICH_REPEAT = "isolated_enrich.repeat"
_ENRICH_XLSX = "isolated_enrich.xlsx"
_CSV_CURRENT_TRUE = frozenset({"1", "t", "true", "yes"})
_CSV_CURRENT_FALSE = frozenset({"0", "f", "false", "no"})
_RUN_STATUSES = frozenset({"PASS", "FAIL", "NOT_RUN"})
_SOURCE_COMPLETENESS = frozenset(
    {"admission_complete", "complete", "incomplete", "not_recorded"}
)
_STATUS_FIELDS = (
    "iuphar_match_status",
    "local_class",
    "effective_class",
    "decision_status",
)
_PHASE_NAMES = (
    "shadow",
    "isolated_enrich",
    "composite_enrich",
    "migration",
    "live",
)
_EVIDENCE_KEYS = frozenset(
    {
        "schema_version",
        "shadow",
        "isolated_enrich",
        "composite_enrich",
        "migration",
        "live",
        "biological",
        "local",
        "ci",
    }
)


class ContourEvidenceError(ValueError):
    """Raised when operator evidence does not match the pinned document."""


@dataclass(frozen=True, slots=True)
class ContourMeasurementPaths:
    """Operator files. Isolated smoke paths stay separate from live readback."""

    discrepancy_report: Path | None = None
    expectations: Path | None = None
    shadow_table: Path | None = None
    shadow_classification: Path | None = None
    table: Path | None = None
    repeat_table: Path | None = None
    xlsx: Path | None = None
    isolated_silver: Path | None = None
    isolated_gold: Path | None = None
    silver: Path | None = None
    gold: Path | None = None
    assay: Path | None = None


@dataclass(frozen=True, slots=True)
class ContourObservations:
    """Facts read from configs, contracts, and operator-supplied files."""

    canonical_mode: str
    canonical_config_sha256: str
    composite_classification_fields: tuple[str, ...]
    entity_classification_fields: tuple[str, ...]
    composite_contract_properties: frozenset[str]
    discrepancy_report_sha256: str | None = None
    expectations_sha256: str | None = None
    shadow_rows: tuple[dict[str, object], ...] | None = None
    shadow_classification_rows: tuple[dict[str, object], ...] | None = None
    duplicate_current_target_ids: bool | None = None
    xlsx_status: str = "NOT_RUN"
    xlsx_table_sha256: str | None = None
    xlsx_file_sha256: str | None = None
    historical_preserved: bool | None = None
    repeat_classification_sha256: str | None = None
    repeat_other_sha256: str | None = None
    fk_unresolved: int | None = None
    silver_sha256: str | None = None
    gold_sha256: str | None = None
    live_projection_match: bool | None = None
    table_profile_values: tuple[str | None, ...] | None = None
    silver_profile_values: tuple[str | None, ...] | None = None
    gold_profile_values: tuple[str | None, ...] | None = None
    live_silver_profile_values: tuple[str | None, ...] | None = None
    live_gold_profile_values: tuple[str | None, ...] | None = None


def _confine(path: Path) -> Path:
    """Rebuild a CLI path before any read or write."""
    return confined_io_path(path, allow_external_absolute=True)


def file_sha256(path: Path) -> str:
    """Return the SHA-256 of exact file bytes."""
    safe = _confine(path)
    digest = hashlib.sha256()
    with safe.open("rb") as handle:  # NOSONAR - confined_io_path
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classification_sha256(
    rows: tuple[dict[str, object], ...] | list[dict[str, object]],
) -> str:
    """Hash classification columns in stable target-id order."""
    projected: list[dict[str, object]] = []
    for row in sorted(rows, key=lambda item: str(item.get("target_id") or "")):
        item = {
            field: _norm_cell(row.get(field)) for field in TARGET_CLASSIFICATION_FIELDS
        }
        item["target_id"] = _norm_cell(row.get("target_id"))
        projected.append(item)
    payload = json.dumps(
        projected, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def status_distributions(
    rows: tuple[dict[str, object], ...] | list[dict[str, object]],
) -> dict[str, dict[str, int]]:
    """Count match, local, effective, and decision statuses."""
    distributions: dict[str, dict[str, int]] = {}
    for field in _STATUS_FIELDS:
        tally: dict[str, int] = {}
        for row in rows:
            key = _status_key(row.get(field))
            tally[key] = tally.get(key, 0) + 1
        distributions[field] = dict(sorted(tally.items()))
    return distributions


def _is_current_row(row: dict[str, object]) -> bool:
    """Match migration closure: a missing flag is current, a falsy flag is closed."""
    return bool(row.get(_IS_CURRENT, True))


def _csv_row(row: dict[str, str]) -> dict[str, object]:
    """Decode a CSV SCD flag before the shared current-row checks."""
    normalized: dict[str, object] = dict(row)
    flag = normalized.get(_IS_CURRENT)
    if not isinstance(flag, str):
        return normalized
    token = flag.strip().lower()
    if token in _CSV_CURRENT_TRUE:
        normalized[_IS_CURRENT] = True
    elif token in _CSV_CURRENT_FALSE:
        normalized[_IS_CURRENT] = False
    return normalized


def _current_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row for row in rows if _is_current_row(row)]


def logical_projection_sha256(rows: list[dict[str, object]]) -> str:
    """Hash current business fields, excluding technical ``_`` metadata."""
    projected: list[dict[str, str | None]] = []
    current = _current_rows(rows)
    ordered = sorted(
        current,
        key=lambda item: (
            str(item.get("target_id") or ""),
            str(item.get("_version") or ""),
        ),
    )
    for row in ordered:
        projected.append(
            {
                str(key): _norm_cell(value)
                for key, value in row.items()
                if not str(key).startswith("_")
            }
        )
    payload = json.dumps(
        projected, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def table_identity_sha256(path: Path, rows: list[dict[str, object]]) -> str:
    """Byte-hash a file, or hash the current logical projection of a directory."""
    safe = _confine(path)
    if safe.is_file():  # NOSONAR - confined_io_path
        return file_sha256(safe)
    return logical_projection_sha256(rows)


def _profile_values(rows: list[dict[str, object]]) -> tuple[str | None, ...]:
    """Current ``target_class_profile_sha256`` values, including blanks."""
    return tuple(
        _norm_cell(row.get("target_class_profile_sha256"))
        for row in _current_rows(rows)
    )


def unresolved_assay_targets(
    assay_rows: list[dict[str, object]],
    gold_rows: list[dict[str, object]],
) -> int:
    """Count current assay target ids absent from current Gold rows."""
    gold_ids = {
        normalized
        for row in _current_rows(gold_rows)
        if (normalized := _norm_cell(row.get("target_id"))) is not None
    }
    missing = {
        normalized
        for row in _current_rows(assay_rows)
        if (normalized := _norm_cell(row.get("target_id"))) is not None
        and normalized not in gold_ids
    }
    return len(missing)


def load_table(path: Path) -> list[dict[str, object]]:
    """Load a CSV, JSON row list, or Delta directory."""
    safe = _confine(path)
    suffix = safe.suffix.lower()
    if suffix == ".csv":
        with safe.open(
            encoding="utf-8-sig", newline=""
        ) as handle:  # NOSONAR - confined_io_path
            return [_csv_row(dict(row)) for row in csv.DictReader(handle)]
    if suffix == ".json":
        payload = json.loads(
            safe.read_text(encoding="utf-8")
        )  # NOSONAR - confined_io_path
        if not isinstance(payload, list):
            raise ContourEvidenceError(f"{safe} must contain a JSON list of rows")
        rows: list[dict[str, object]] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ContourEvidenceError(f"{safe} rows must be objects")
            rows.append(cast(dict[str, object], item))
        return rows
    if safe.is_dir():  # NOSONAR - confined_io_path
        from bioetl.infrastructure.storage.target_migration_row_ops import read_delta

        return read_delta(safe)
    raise ContourEvidenceError(f"unsupported table path: {safe}")


def compare_xlsx_round_trip(
    table_rows: list[dict[str, object]],
    xlsx_path: Path,
    historical_columns: tuple[str, ...],
) -> tuple[str, bool]:
    """Return round-trip status and whether historical columns match."""
    xlsx_rows = _read_xlsx_rows(xlsx_path)
    status = (
        "PASS"
        if _rows_match(table_rows, xlsx_rows, TARGET_CLASSIFICATION_FIELDS)
        else "FAIL"
    )
    if not historical_columns:
        return status, False
    preserved = _rows_match(table_rows, xlsx_rows, historical_columns)
    if not preserved:
        status = "FAIL"
    return status, preserved


def inspect_repository(root: Path = REPO_ROOT) -> ContourObservations:
    """Read canonical mode, composite column groups, and the gold contract."""
    config_path = root / "configs" / "entities" / "chembl" / _TARGET_YAML
    composite_path = root / "configs" / "composites" / _TARGET_YAML
    entity_path = root / "configs" / "entities" / "composite" / _TARGET_YAML
    contract_path = (
        root
        / "docs"
        / "04-reference"
        / "contracts"
        / "gold"
        / "composite_target_v1.0.json"
    )
    mode, digest = _canonical_identity(config_path)
    return ContourObservations(
        canonical_mode=mode,
        canonical_config_sha256=digest,
        composite_classification_fields=_classification_fields(composite_path),
        entity_classification_fields=_classification_fields(entity_path),
        composite_contract_properties=_contract_properties(contract_path),
    )


def evaluate_main_contour(
    evidence: object,
    observations: ContourObservations,
) -> dict[str, object]:
    """Build the operator report. Evidence cannot set the promotion decision."""
    document = parse_evidence(evidence)
    phases = {
        "shadow": _evaluate_shadow(document, observations),
        "isolated_enrich": _evaluate_enrich(document, observations),
        "composite_enrich": _evaluate_composite(document, observations),
        "migration": _evaluate_migration(document, observations),
        "live": _evaluate_live(document, observations),
    }
    biological = _evaluate_biological(document)
    local = _evaluate_local(document)
    ci = _evaluate_ci(document)
    decision, reasons, rollback = _decide(
        document, observations, phases, biological, local, ci
    )
    distributions, distribution_source = _distributions(document, observations)
    biological_claim = cast(dict[str, object], document["biological"])
    return {
        "artifact": "bioetl_iuphar_main_contour_report",
        "schema_version": REPORT_SCHEMA,
        "phases": phases,
        "axes": {
            "local": local,
            "ci": ci,
            "migration": phases["migration"],
            "biological": biological,
        },
        "promotion_decision": decision,
        "promotion_reasons": reasons,
        "rollback_required": rollback,
        "canonical": {
            "mode": observations.canonical_mode,
            "config_sha256": observations.canonical_config_sha256,
        },
        "distributions": distributions,
        "distribution_source": distribution_source,
        "source_completeness": cast(dict[str, object], document["shadow"])[
            "source_completeness"
        ],
        "matched_count": biological_claim["matched_count"],
        "matched_count_substitutes_biological_qualification": biological_claim[
            "matched_count_used_as_qualification"
        ],
        "biological_accuracy_accepted": biological_claim[
            "biological_accuracy_accepted"
        ],
        "rf008_admitted": biological["rf008_admitted"],
        "writers_check": "operator_attestation",
        "smoke_limit": SMOKE_LIMIT,
    }


def write_contour_report(report: dict[str, object], output: Path) -> None:
    """Publish a new report atomically. An existing path is left unchanged."""
    safe = _confine(output)
    if safe.exists():  # NOSONAR - confined_io_path
        raise ContourEvidenceError(
            f"refusing to replace existing contour report: {safe}"
        )
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    atomic_write_text(safe, payload)  # NOSONAR - confined_io_path


def _record_hash(updates: dict[str, object], key: str, path: Path | None) -> None:
    if path is not None:
        updates[key] = file_sha256(path)


def _record_shadow(
    updates: dict[str, object],
    path: Path | None,
    classification: Path | None,
) -> None:
    if path is not None:
        updates["shadow_rows"] = tuple(_current_rows(load_table(path)))
    if classification is not None:
        updates["shadow_classification_rows"] = tuple(
            _current_rows(load_table(classification))
        )


def _record_enrich_table(
    updates: dict[str, object],
    table: Path | None,
    repeat_table: Path | None,
) -> list[dict[str, object]] | None:
    table_rows = load_table(table) if table is not None else None
    repeat_rows = load_table(repeat_table) if repeat_table is not None else None
    if table_rows is not None and table is not None:
        updates["table_profile_values"] = _profile_values(table_rows)
        updates["repeat_classification_sha256"] = classification_sha256(
            _current_rows(table_rows)
        )
        updates["xlsx_table_sha256"] = table_identity_sha256(table, table_rows)
    if repeat_rows is not None:
        updates["repeat_other_sha256"] = classification_sha256(
            _current_rows(repeat_rows)
        )
    return table_rows


def _record_xlsx(
    updates: dict[str, object],
    evidence: dict[str, object],
    table_rows: list[dict[str, object]] | None,
    xlsx: Path | None,
) -> None:
    if xlsx is None or table_rows is None:
        return
    enrich = cast(dict[str, object], evidence["isolated_enrich"])
    xlsx_claim = cast(dict[str, object], enrich["xlsx"])
    historical = cast(tuple[str, ...], xlsx_claim["historical_columns"])
    status, preserved = compare_xlsx_round_trip(
        _current_rows(table_rows), xlsx, historical
    )
    updates["xlsx_status"] = status
    updates["historical_preserved"] = preserved
    updates["xlsx_file_sha256"] = file_sha256(xlsx)


def _record_isolated(
    updates: dict[str, object],
    silver: Path | None,
    gold: Path | None,
) -> None:
    """Hash the isolated enrich tables, not the later main-contour readback."""
    if silver is not None:
        rows = load_table(silver)
        updates["silver_sha256"] = table_identity_sha256(silver, rows)
        updates["silver_profile_values"] = _profile_values(rows)
    if gold is not None:
        rows = load_table(gold)
        updates["gold_sha256"] = table_identity_sha256(gold, rows)
        updates["gold_profile_values"] = _profile_values(rows)


def _record_live(
    updates: dict[str, object],
    silver: Path | None,
    gold: Path | None,
) -> list[dict[str, object]] | None:
    """Compare the main-contour readback without replacing isolated hashes."""
    silver_rows = load_table(silver) if silver is not None else None
    gold_rows = load_table(gold) if gold is not None else None
    if silver_rows is not None:
        updates["live_silver_profile_values"] = _profile_values(silver_rows)
    if gold_rows is not None:
        updates["live_gold_profile_values"] = _profile_values(gold_rows)
    if silver_rows is None or gold_rows is None:
        return gold_rows
    duplicate = _has_duplicate_current_ids(silver_rows) or _has_duplicate_current_ids(
        gold_rows
    )
    updates["duplicate_current_target_ids"] = duplicate
    updates["live_projection_match"] = (
        False if duplicate else _current_projections_match(silver_rows, gold_rows)
    )
    return gold_rows


def _record_fk(
    updates: dict[str, object],
    assay: Path | None,
    gold_rows: list[dict[str, object]] | None,
) -> None:
    if assay is not None and gold_rows is not None:
        updates["fk_unresolved"] = unresolved_assay_targets(
            load_table(assay), gold_rows
        )


def apply_measurements(
    observations: ContourObservations,
    evidence: dict[str, object],
    paths: ContourMeasurementPaths | None = None,
) -> ContourObservations:
    """Fill observations from confined files and current Delta rows."""
    selected = paths or ContourMeasurementPaths()
    updates: dict[str, object] = {}
    _record_hash(updates, "discrepancy_report_sha256", selected.discrepancy_report)
    _record_hash(updates, "expectations_sha256", selected.expectations)
    _record_shadow(updates, selected.shadow_table, selected.shadow_classification)
    table_rows = _record_enrich_table(updates, selected.table, selected.repeat_table)
    _record_xlsx(updates, evidence, table_rows, selected.xlsx)
    _record_isolated(updates, selected.isolated_silver, selected.isolated_gold)
    gold_rows = _record_live(updates, selected.silver, selected.gold)
    _record_fk(updates, selected.assay, gold_rows)
    return cast(ContourObservations, replace(observations, **updates))


def parse_evidence(evidence: object) -> dict[str, object]:
    """Validate the operator evidence document."""
    document = _mapping(evidence, "evidence")
    _exact_keys(document, _EVIDENCE_KEYS, "evidence")
    if document["schema_version"] != EVIDENCE_SCHEMA:
        raise ContourEvidenceError("evidence schema_version is not supported")
    document["shadow"] = _parse_shadow(document["shadow"])
    document["isolated_enrich"] = _parse_enrich(document["isolated_enrich"])
    document["composite_enrich"] = _parse_composite(document["composite_enrich"])
    document["migration"] = _parse_migration(document["migration"])
    document["live"] = _parse_live(document["live"])
    document["biological"] = _parse_biological(document["biological"])
    document["local"] = _parse_attestation(document["local"], "local")
    document["ci"] = _parse_ci(document["ci"])
    return document


def _evaluate_shadow(
    document: dict[str, object],
    observations: ContourObservations,
) -> dict[str, object]:
    shadow = cast(dict[str, object], document["shadow"])
    if shadow["executed"] is not True:
        return _phase("NOT_RUN", ["not_executed"])
    reasons: list[str] = []
    if shadow["separate_directory"] is not True:
        reasons.append("directory_not_separate")
    if shadow["contract_version"] != SHADOW_CONTRACT:
        reasons.append("contract_not_v30")
    if shadow["business_rows_unchanged"] is not True:
        reasons.append("business_rows_changed")
    if not _pinned(shadow["profile_sha256"]) or not _pinned(shadow["config_sha256"]):
        reasons.append("profile_or_config_unpinned")
    if not _pinned(shadow["cohort_sha256"]):
        reasons.append("cohort_unpinned")
    if shadow["source_completeness"] not in {"admission_complete", "complete"}:
        reasons.append("source_incomplete")
    reasons.extend(
        _hash_pair(
            observations.discrepancy_report_sha256,
            shadow["discrepancy_report_sha256"],
            "discrepancy_report",
        )
    )
    reasons.extend(
        _hash_pair(
            observations.expectations_sha256,
            shadow["independent_expectations_sha256"],
            "independent_expectations",
        )
    )
    reasons.extend(_distribution_reasons(shadow, observations))
    return _phase("FAIL" if reasons else "PASS", reasons)


def _unpinned_reasons(
    section: dict[str, object], pairs: tuple[tuple[str, str], ...]
) -> list[str]:
    return [code for key, code in pairs if not _pinned(section[key])]


def _enrich_profile_reasons(
    observations: ContourObservations, profile: object
) -> list[str]:
    reasons: list[str] = []
    cohorts = (
        (
            observations.table_profile_values,
            "enrich_profile_rows_not_measured",
            "enrich_profile_row_mismatch",
        ),
        (
            observations.silver_profile_values,
            "silver_profile_rows_not_measured",
            "silver_profile_row_mismatch",
        ),
        (
            observations.gold_profile_values,
            "gold_profile_rows_not_measured",
            "gold_profile_row_mismatch",
        ),
    )
    for observed, missing_code, mismatch_code in cohorts:
        reasons.extend(
            _profile_row_reasons(observed, profile, missing_code, mismatch_code)
        )
    return reasons


def _enrich_repeat_reasons(
    observations: ContourObservations, enrich: dict[str, object]
) -> list[str]:
    reasons: list[str] = []
    repeat = cast(dict[str, object], enrich["repeat"])
    if repeat["same_inputs"] is not True or repeat["same_versions"] is not True:
        reasons.append("repeat_inputs_or_versions_differ")
    reasons.extend(
        _hash_pair(
            observations.repeat_classification_sha256,
            repeat["classification_sha256"],
            "repeat_classification",
        )
    )
    reasons.extend(
        _hash_pair(
            observations.repeat_other_sha256,
            repeat["repeat_classification_sha256"],
            "repeat_other",
        )
    )
    observed = observations.repeat_classification_sha256
    other = observations.repeat_other_sha256
    if observed is not None and other is not None and observed != other:
        reasons.append("repeat_classification_mismatch")
    return reasons


def _enrich_xlsx_reasons(
    observations: ContourObservations, enrich: dict[str, object]
) -> list[str]:
    reasons: list[str] = []
    xlsx = cast(dict[str, object], enrich["xlsx"])
    if observations.xlsx_status == "NOT_RUN":
        reasons.append("xlsx_not_read")
    elif observations.xlsx_status != "PASS":
        reasons.append("xlsx_round_trip_failed")
    if observations.historical_preserved is not True:
        reasons.append("historical_values_not_preserved")
    reasons.extend(
        _hash_pair(observations.xlsx_table_sha256, xlsx["table_sha256"], "xlsx_table")
    )
    reasons.extend(
        _hash_pair(observations.xlsx_file_sha256, xlsx["xlsx_sha256"], "xlsx_file")
    )
    historical = cast(tuple[str, ...], xlsx["historical_columns"])
    if not historical:
        reasons.append("historical_columns_missing")
    return reasons


def _evaluate_enrich(
    document: dict[str, object],
    observations: ContourObservations,
) -> dict[str, object]:
    enrich = cast(dict[str, object], document["isolated_enrich"])
    if enrich["executed"] is not True:
        return _phase("NOT_RUN", ["not_executed"])
    reasons: list[str] = []
    if enrich["separate_directory"] is not True:
        reasons.append("directory_not_separate")
    if enrich["limit"] != SMOKE_LIMIT:
        reasons.append("limit_1000_required")
    if enrich["full_table_proof"] is True:
        reasons.append("smoke_cannot_prove_full_table")
    if (
        enrich["silver_contract"] != ENRICH_CONTRACT
        or enrich["gold_contract"] != ENRICH_CONTRACT
    ):
        reasons.append("contract_version_mismatch")
    reasons.extend(
        _unpinned_reasons(
            enrich,
            (
                ("profile_sha256", "profile_unpinned"),
                ("config_sha256", "config_unpinned"),
                ("evidence_manifest_sha256", "evidence_manifest_unpinned"),
                ("persisted_silver_sha256", "silver_unpinned"),
                ("persisted_gold_sha256", "gold_unpinned"),
            ),
        )
    )
    reasons.extend(_enrich_profile_reasons(observations, enrich["profile_sha256"]))
    reasons.extend(
        _measured_identity(
            observations.silver_sha256,
            enrich["persisted_silver_sha256"],
            "silver_identity_not_measured",
            "silver_hash_conflict",
        )
    )
    reasons.extend(
        _measured_identity(
            observations.gold_sha256,
            enrich["persisted_gold_sha256"],
            "gold_identity_not_measured",
            "gold_hash_conflict",
        )
    )
    reasons.extend(_enrich_repeat_reasons(observations, enrich))
    reasons.extend(_enrich_xlsx_reasons(observations, enrich))
    return _phase("FAIL" if reasons else "PASS", _unique(reasons))


def _absent_fields(present: frozenset[str] | tuple[str, ...]) -> list[str]:
    return [field for field in TARGET_CLASSIFICATION_FIELDS if field not in present]


def _group_gaps(observations: ContourObservations) -> list[str]:
    return [
        field
        for field in TARGET_CLASSIFICATION_FIELDS
        if field not in observations.composite_classification_fields
        or field not in observations.entity_classification_fields
    ]


def _composite_structure(
    observations: ContourObservations,
) -> dict[str, object] | None:
    missing_contract = _absent_fields(observations.composite_contract_properties)
    missing_groups = _group_gaps(observations)
    drifted = (
        observations.composite_classification_fields
        != observations.entity_classification_fields
    )
    if not missing_contract and not missing_groups:
        if drifted:
            return _phase("FAIL", ["column_group_drift"])
        return None
    reasons: list[str] = []
    if missing_contract:
        reasons.append("composite_contract_missing_fields")
    if missing_groups:
        reasons.append("column_group_missing_fields")
    if drifted:
        reasons.append("column_group_drift")
    return _phase("BLOCKED", reasons)


def _composite_run_reasons(
    composite: dict[str, object], shadow: dict[str, object]
) -> list[str]:
    reasons: list[str] = []
    if composite["separate_directory"] is not True:
        reasons.append("directory_not_separate")
    if composite["same_cohort_as_shadow"] is not True:
        reasons.append("cohort_not_agreed")
    if composite["classification_columns_present"] is not True:
        reasons.append("classification_columns_absent")
    if not _pinned(composite["agreed_cohort_sha256"]) or (
        composite["agreed_cohort_sha256"] != shadow["cohort_sha256"]
    ):
        reasons.append("cohort_hash_mismatch")
    return reasons


def _evaluate_composite(
    document: dict[str, object],
    observations: ContourObservations,
) -> dict[str, object]:
    blocked = _composite_structure(observations)
    if blocked is not None:
        return blocked
    composite = cast(dict[str, object], document["composite_enrich"])
    if composite["executed"] is not True:
        return _phase("NOT_RUN", ["not_executed"])
    shadow = cast(dict[str, object], document["shadow"])
    reasons = _composite_run_reasons(composite, shadow)
    return _phase("FAIL" if reasons else "PASS", reasons)


def _migration_closure_reasons(
    migration: dict[str, object], observations: ContourObservations
) -> list[str]:
    reasons: list[str] = []
    if migration["rehearsal_rollback"] != "PASS":
        reasons.append("rehearsal_rollback_not_passed")
    if migration["full_cohort"] is not True:
        reasons.append("full_cohort_not_proven")
    if observations.fk_unresolved is None:
        reasons.append("fk_not_measured")
    elif observations.fk_unresolved != 0:
        reasons.append("assay_fk_unresolved")
    attested_fk = migration["fk_unresolved"]
    if attested_fk is not None and attested_fk != observations.fk_unresolved:
        reasons.append("fk_evidence_conflict")
    if migration["writers_quiesced"] is not True:
        reasons.append("writers_not_quiesced")
    if migration["backup_retained"] is not True:
        reasons.append("backup_not_retained")
    if migration["physical_contract"] != PHYSICAL_CONTRACT:
        reasons.append("physical_contract_mismatch")
    if migration["source_identity_matches"] is not True:
        reasons.append("source_identity_mismatch")
    return reasons


def _migration_identity_reasons(
    migration: dict[str, object],
    enrich: dict[str, object],
    observations: ContourObservations,
) -> list[str]:
    reasons: list[str] = []
    if not _pinned(migration["effective_profile_sha256"]) or (
        migration["effective_profile_sha256"] != enrich["profile_sha256"]
    ):
        reasons.append("profile_hash_mismatch")
    if not _pinned(migration["effective_config_sha256"]):
        reasons.append("effective_config_unpinned")
    reasons.extend(_promotion_config_reasons(migration, observations))
    return reasons


def _promotion_config_reasons(
    migration: dict[str, object], observations: ContourObservations
) -> list[str]:
    reasons: list[str] = []
    if migration["promoted"] is True:
        if observations.canonical_mode != "enrich":
            reasons.append("promoted_config_not_enrich")
        if migration["effective_config_sha256"] != observations.canonical_config_sha256:
            reasons.append("promoted_config_hash_mismatch")
        return reasons
    if observations.canonical_mode != "off":
        reasons.append("premature_canonical_activation")
    if migration["effective_config_sha256"] == observations.canonical_config_sha256:
        reasons.append("candidate_config_not_separate")
    return reasons


def _evaluate_migration(
    document: dict[str, object],
    observations: ContourObservations,
) -> dict[str, object]:
    migration = cast(dict[str, object], document["migration"])
    enrich = cast(dict[str, object], document["isolated_enrich"])
    if _migration_not_started(migration, observations):
        return _phase("NOT_RUN", ["not_executed"])
    reasons = _migration_closure_reasons(migration, observations)
    reasons.extend(_migration_identity_reasons(migration, enrich, observations))
    return _phase("FAIL" if reasons else "PASS", _unique(reasons))


def _live_profile_reasons(
    observations: ContourObservations, migration: dict[str, object]
) -> list[str]:
    """Current main-contour rows must carry the promoted profile."""
    profile = migration["effective_profile_sha256"]
    reasons: list[str] = []
    reasons.extend(
        _profile_row_reasons(
            observations.live_silver_profile_values,
            profile,
            "live_silver_profile_rows_not_measured",
            "live_silver_profile_row_mismatch",
        )
    )
    reasons.extend(
        _profile_row_reasons(
            observations.live_gold_profile_values,
            profile,
            "live_gold_profile_rows_not_measured",
            "live_gold_profile_row_mismatch",
        )
    )
    return reasons


def _live_projection_reasons(observations: ContourObservations) -> list[str]:
    if observations.duplicate_current_target_ids is True:
        return ["duplicate_current_target_id"]
    if observations.live_projection_match is None:
        return ["classification_readback_missing"]
    if observations.live_projection_match is not True:
        return ["classification_not_reproduced"]
    return []


def _evaluate_live(
    document: dict[str, object],
    observations: ContourObservations,
) -> dict[str, object]:
    live = cast(dict[str, object], document["live"])
    migration = cast(dict[str, object], document["migration"])
    if live["readback"] is not True and live["next_run_executed"] is not True:
        return _phase("NOT_RUN", ["not_executed"])
    reasons: list[str] = []
    if migration["promoted"] is not True:
        reasons.append("live_without_promotion")
    if live["readback"] is not True:
        reasons.append("tables_not_read")
    if live["next_run_executed"] is not True or not _text(live["next_run_id"]):
        reasons.append("next_run_missing")
    if live["tables_match_promoted"] is not True:
        reasons.append("tables_do_not_match_promoted")
    if not _pinned(live["observed_profile_sha256"]) or (
        live["observed_profile_sha256"] != migration["effective_profile_sha256"]
    ):
        reasons.append("live_profile_mismatch")
    if not _pinned(live["observed_config_sha256"]) or (
        live["observed_config_sha256"] != observations.canonical_config_sha256
    ):
        reasons.append("live_config_mismatch")
    reasons.extend(_live_profile_reasons(observations, migration))
    reasons.extend(_live_projection_reasons(observations))
    if live["classification_reproduced"] is not True:
        reasons.append("classification_reproduced_not_attested")
    return _phase("FAIL" if reasons else "PASS", _unique(reasons))


def _accepted_biology(claim: dict[str, object], *, admitted: bool) -> dict[str, object]:
    reasons: list[str] = []
    if claim["scientific_status"] == "bounded_reference_cases_only":
        reasons.append("bounded_reference_is_not_biological_acceptance")
    if not _text(claim["reviewer_reference"]):
        reasons.append("biological_reviewer_missing")
    if not _pinned(claim["independent_reference_sha256"]):
        reasons.append("biological_reference_unpinned")
    if claim["rf008_receipt_status"] != "PASS" or not _pinned(
        claim["rf008_receipt_sha256"]
    ):
        reasons.append("rf008_receipt_missing")
    if reasons:
        return _biological("FAIL", reasons, admitted=False)
    return _biological("PASS", ["independent_biological_review"], admitted=admitted)


def _evaluate_biological(document: dict[str, object]) -> dict[str, object]:
    claim = cast(dict[str, object], document["biological"])
    admitted = _rf008_admitted(claim)
    if claim["matched_count_used_as_qualification"] is True:
        return _biological(
            "FAIL", ["matched_count_used_as_qualification"], admitted=False
        )
    if claim["biological_accuracy_accepted"] is True:
        return _accepted_biology(claim, admitted=admitted)
    if claim["rf008_receipt_status"] == "FAIL":
        return _biological("FAIL", ["rf008_receipt_failed"], admitted=False)
    if admitted:
        return _biological("NOT_ACCEPTED", ["bounded_reference_only"], admitted=True)
    if claim["rf008_receipt_status"] == "PASS":
        return _biological("FAIL", ["rf008_admission_incomplete"], admitted=False)
    return _biological(
        "NOT_ACCEPTED", ["biological_accuracy_not_claimed"], admitted=False
    )


def _evaluate_local(document: dict[str, object]) -> dict[str, object]:
    local = cast(dict[str, object], document["local"])
    status = cast(str, local["status"])
    if status == "NOT_RUN":
        return _phase("NOT_RUN", ["not_executed"])
    if status == "FAIL":
        return _phase("FAIL", ["local_checks_failed"])
    if not _pinned(local["evidence_sha256"]):
        return _phase("FAIL", ["local_evidence_unpinned"])
    return _phase("PASS", [])


def _evaluate_ci(document: dict[str, object]) -> dict[str, object]:
    ci = cast(dict[str, object], document["ci"])
    status = cast(str, ci["status"])
    if status == "NOT_RUN":
        return _phase("NOT_RUN", ["not_executed"])
    if status == "FAIL":
        return _phase("FAIL", ["ci_failed"])
    commit = ci["commit_sha"]
    if (
        not isinstance(commit, str)
        or len(commit) != _COMMIT_SHA
        or any(character not in "0123456789abcdef" for character in commit)
    ):
        return _phase("FAIL", ["ci_commit_unpinned"])
    return _phase("PASS", [])


def _axis_failures(local: dict[str, object], ci: dict[str, object]) -> list[str]:
    return [
        name
        for name, phase in (("local", local), ("ci", ci))
        if phase["status"] == "FAIL"
    ]


def _needs_rollback(
    *,
    promoted: bool,
    failed: list[str],
    live_status: object,
    bio_ok: bool,
    axis_failures: list[str],
) -> bool:
    return promoted and (
        bool(failed) or live_status == "FAIL" or not bio_ok or bool(axis_failures)
    )


def _is_ready(
    *,
    technical: bool,
    bio_ok: bool,
    axes_ok: bool,
    promoted: bool,
    mode: str,
    live_status: object,
) -> bool:
    return (
        technical
        and bio_ok
        and axes_ok
        and not promoted
        and mode == "off"
        and live_status == "NOT_RUN"
    )


def _is_live_accepted(
    *,
    technical: bool,
    bio_ok: bool,
    axes_ok: bool,
    promoted: bool,
    mode: str,
    live_status: object,
) -> bool:
    return (
        technical
        and bio_ok
        and axes_ok
        and promoted
        and mode == "enrich"
        and live_status == "PASS"
    )


def _blocked_reasons(
    *,
    failed: list[str],
    bio_ok: bool,
    local: dict[str, object],
    ci: dict[str, object],
    promoted: bool,
    mode: str,
    live_status: object,
) -> list[str]:
    reasons = [f"{name}_not_passed" for name in failed]
    if not bio_ok:
        reasons.append("biological_gate_not_passed")
    if local["status"] != "PASS":
        reasons.append("local_not_passed")
    if ci["status"] != "PASS":
        reasons.append("ci_not_passed")
    if not promoted and mode != "off":
        reasons.append("premature_canonical_activation")
    if not promoted and live_status != "NOT_RUN":
        reasons.append("live_before_promotion")
    if promoted and live_status != "PASS":
        reasons.append("live_not_passed")
    return reasons or ["promotion_criteria_incomplete"]


def _decide(
    document: dict[str, object],
    observations: ContourObservations,
    phases: dict[str, dict[str, object]],
    biological: dict[str, object],
    local: dict[str, object],
    ci: dict[str, object],
) -> tuple[str, list[str], bool]:
    migration = cast(dict[str, object], document["migration"])
    promoted = migration["promoted"] is True
    technical = all(phases[name]["status"] == "PASS" for name in _PHASE_NAMES[:4])
    bio_ok = biological["status"] == "PASS" or biological["rf008_admitted"] is True
    axes_ok = local["status"] == "PASS" and ci["status"] == "PASS"
    failed = [name for name in _PHASE_NAMES[:4] if phases[name]["status"] != "PASS"]
    axis_failures = _axis_failures(local, ci)
    live_status = phases["live"]["status"]
    if _needs_rollback(
        promoted=promoted,
        failed=failed,
        live_status=live_status,
        bio_ok=bio_ok,
        axis_failures=axis_failures,
    ):
        return (
            "ROLLBACK_REQUIRED",
            ["criteria_violated_after_promotion", *failed, *axis_failures],
            True,
        )
    if _is_ready(
        technical=technical,
        bio_ok=bio_ok,
        axes_ok=axes_ok,
        promoted=promoted,
        mode=observations.canonical_mode,
        live_status=live_status,
    ):
        return "READY", ["technical_gates_passed"], False
    if _is_live_accepted(
        technical=technical,
        bio_ok=bio_ok,
        axes_ok=axes_ok,
        promoted=promoted,
        mode=observations.canonical_mode,
        live_status=live_status,
    ):
        return "LIVE_ACCEPTED", ["live_readback_passed"], False
    return (
        "BLOCKED",
        _blocked_reasons(
            failed=failed,
            bio_ok=bio_ok,
            local=local,
            ci=ci,
            promoted=promoted,
            mode=observations.canonical_mode,
            live_status=live_status,
        ),
        False,
    )


def _distributions(
    document: dict[str, object],
    observations: ContourObservations,
) -> tuple[dict[str, dict[str, int]], str]:
    if observations.shadow_classification_rows is not None:
        return (
            status_distributions(observations.shadow_classification_rows),
            "shadow_classification",
        )
    shadow = cast(dict[str, object], document["shadow"])
    if shadow["executed"] is True:
        return cast(dict[str, dict[str, int]], shadow["status_counts"]), "evidence"
    return {field: {} for field in _STATUS_FIELDS}, "not_recorded"


def _distribution_reasons(
    shadow: dict[str, object],
    observations: ContourObservations,
) -> list[str]:
    counts = cast(dict[str, dict[str, int]], shadow["status_counts"])
    row_count = cast(int, shadow["row_count"])
    reasons: list[str] = []
    for field in _STATUS_FIELDS:
        if sum(counts[field].values()) != row_count:
            reasons.append("status_count_row_mismatch")
            break
    reasons.extend(_shadow_business_reasons(observations, row_count))
    classification = observations.shadow_classification_rows
    if observations.shadow_rows is not None and classification is None:
        reasons.append("shadow_classification_not_read")
        return reasons
    if classification is None:
        return reasons
    if len(classification) != row_count:
        reasons.append("shadow_classification_row_count")
    if status_distributions(classification) != counts:
        reasons.append("status_count_conflict")
    return reasons


def _shadow_business_reasons(
    observations: ContourObservations, row_count: int
) -> list[str]:
    business = observations.shadow_rows
    if business is None:
        return []
    reasons: list[str] = []
    if len(business) != row_count:
        reasons.append("row_count_conflict")
    if not _shadow_business_unchanged(business):
        reasons.append("shadow_business_rows_changed")
    classification = observations.shadow_classification_rows
    if classification is not None and _current_id_set(business) != _current_id_set(
        classification
    ):
        reasons.append("shadow_cohort_mismatch")
    return reasons


def _shadow_business_unchanged(rows: tuple[dict[str, object], ...]) -> bool:
    """A V30 shadow table keeps classification fields out of the business row."""
    forbidden = frozenset(TARGET_CLASSIFICATION_FIELDS)
    return all(forbidden.isdisjoint(row) for row in rows)


def _current_id_set(
    rows: tuple[dict[str, object], ...] | list[dict[str, object]],
) -> set[str]:
    return {
        target_id
        for row in rows
        if (target_id := _norm_cell(row.get("target_id"))) is not None
    }


def _hash_pair(observed: str | None, attested: object, label: str) -> list[str]:
    if not _pinned(observed):
        return [f"{label}_not_read"]
    if attested is not None and attested != observed:
        return [f"{label}_hash_conflict"]
    return []


def _profile_row_reasons(
    observed: tuple[str | None, ...] | None,
    attested: object,
    missing_code: str,
    mismatch_code: str,
) -> list[str]:
    """Every current row must carry the claimed profile digest."""
    if not _pinned(attested):
        return []
    if observed is None:
        return [missing_code]
    if not observed or any(value != attested for value in observed):
        return [mismatch_code]
    return []


def _measured_identity(
    observed: str | None,
    attested: object,
    missing_code: str,
    conflict_code: str,
) -> list[str]:
    if not _pinned(observed):
        return [missing_code]
    if attested is not None and attested != observed:
        return [conflict_code]
    return []


def _index_current_rows(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, object]] | None:
    """Index one current row per target. Duplicate current ids are rejected."""
    indexed: dict[str, dict[str, object]] = {}
    for row in _current_rows(rows):
        target_id = _norm_cell(row.get("target_id"))
        if target_id is None:
            continue
        if target_id in indexed:
            return None
        indexed[target_id] = row
    return indexed


def _has_duplicate_current_ids(rows: list[dict[str, object]]) -> bool:
    return _index_current_rows(rows) is None


def _current_projections_match(
    silver_rows: list[dict[str, object]],
    gold_rows: list[dict[str, object]],
) -> bool:
    """Current Gold classification must match the current Silver row of the same id."""
    silver = _index_current_rows(silver_rows)
    gold = _index_current_rows(gold_rows)
    if silver is None or gold is None or not gold:
        return False
    for target_id, row in gold.items():
        source = silver.get(target_id)
        if source is None or not _same_classification(source, row):
            return False
    return True


def _classification_present(row: dict[str, object]) -> bool:
    return all(field in row for field in TARGET_CLASSIFICATION_FIELDS)


def _same_classification(left: dict[str, object], right: dict[str, object]) -> bool:
    """Missing classification columns are not the same value as null."""
    if not _classification_present(left) or not _classification_present(right):
        return False
    return all(
        _norm_cell(left.get(field)) == _norm_cell(right.get(field))
        for field in TARGET_CLASSIFICATION_FIELDS
    )


def _rf008_admitted(claim: dict[str, object]) -> bool:
    return (
        claim["biological_accuracy_accepted"] is False
        and claim["matched_count_used_as_qualification"] is False
        and claim["rf008_receipt_status"] == "PASS"
        and claim["scientific_status"] == "bounded_reference_cases_only"
        and _pinned(claim["rf008_receipt_sha256"])
        and _pinned(claim["independent_reference_sha256"])
    )


def _migration_not_started(
    migration: dict[str, object],
    observations: ContourObservations,
) -> bool:
    return (
        migration["rehearsal_rollback"] == "NOT_RUN"
        and migration["promoted"] is False
        and migration["full_cohort"] is False
        and migration["physical_contract"] is None
        and migration["fk_unresolved"] is None
        and observations.fk_unresolved is None
    )


def _parse_shadow(value: object) -> dict[str, object]:
    shadow = _section(
        value,
        "shadow",
        {
            "executed",
            "run_id",
            "separate_directory",
            "contract_version",
            "business_rows_unchanged",
            "profile_sha256",
            "config_sha256",
            "cohort_sha256",
            "discrepancy_report_sha256",
            "independent_expectations_sha256",
            "row_count",
            "status_counts",
            "source_completeness",
        },
    )
    _bool_field(shadow, "executed", "shadow")
    _bool_field(shadow, "separate_directory", "shadow")
    _bool_field(shadow, "business_rows_unchanged", "shadow")
    _optional_text(shadow, "run_id", "shadow")
    _optional_text(shadow, "contract_version", "shadow")
    for key in (
        "profile_sha256",
        "config_sha256",
        "cohort_sha256",
        "discrepancy_report_sha256",
        "independent_expectations_sha256",
    ):
        _optional_sha(shadow, key, "shadow")
    if not isinstance(shadow["row_count"], int) or isinstance(
        shadow["row_count"], bool
    ):
        raise ContourEvidenceError("shadow.row_count must be an integer")
    if cast(int, shadow["row_count"]) < 0:
        raise ContourEvidenceError("shadow.row_count must be non-negative")
    completeness = shadow["source_completeness"]
    if completeness not in _SOURCE_COMPLETENESS:
        raise ContourEvidenceError("shadow.source_completeness is not supported")
    shadow["status_counts"] = _parse_counts(shadow["status_counts"])
    return shadow


def _parse_enrich(value: object) -> dict[str, object]:
    enrich = _section(
        value,
        "isolated_enrich",
        {
            "executed",
            "separate_directory",
            "limit",
            "full_table_proof",
            "silver_contract",
            "gold_contract",
            "profile_sha256",
            "config_sha256",
            "evidence_manifest_sha256",
            "persisted_silver_sha256",
            "persisted_gold_sha256",
            "repeat",
            "xlsx",
        },
    )
    _bool_field(enrich, "executed", "isolated_enrich")
    _bool_field(enrich, "separate_directory", "isolated_enrich")
    _bool_field(enrich, "full_table_proof", "isolated_enrich")
    limit = enrich["limit"]
    if limit is not None and (
        not isinstance(limit, int) or isinstance(limit, bool) or limit < 0
    ):
        raise ContourEvidenceError(
            "isolated_enrich.limit must be a non-negative integer or null"
        )
    for key in (
        "silver_contract",
        "gold_contract",
    ):
        _optional_text(enrich, key, "isolated_enrich")
    for key in (
        "profile_sha256",
        "config_sha256",
        "evidence_manifest_sha256",
        "persisted_silver_sha256",
        "persisted_gold_sha256",
    ):
        _optional_sha(enrich, key, "isolated_enrich")
    repeat = _section(
        enrich["repeat"],
        _ENRICH_REPEAT,
        {
            "same_inputs",
            "same_versions",
            "classification_sha256",
            "repeat_classification_sha256",
        },
    )
    _bool_field(repeat, "same_inputs", _ENRICH_REPEAT)
    _bool_field(repeat, "same_versions", _ENRICH_REPEAT)
    _optional_sha(repeat, "classification_sha256", _ENRICH_REPEAT)
    _optional_sha(repeat, "repeat_classification_sha256", _ENRICH_REPEAT)
    xlsx = _section(
        enrich["xlsx"],
        _ENRICH_XLSX,
        {"table_sha256", "xlsx_sha256", "historical_columns"},
    )
    _optional_sha(xlsx, "table_sha256", _ENRICH_XLSX)
    _optional_sha(xlsx, "xlsx_sha256", _ENRICH_XLSX)
    xlsx["historical_columns"] = _string_tuple(
        xlsx["historical_columns"], f"{_ENRICH_XLSX}.historical_columns"
    )
    enrich["repeat"] = repeat
    enrich["xlsx"] = xlsx
    return enrich


def _parse_composite(value: object) -> dict[str, object]:
    composite = _section(
        value,
        "composite_enrich",
        {
            "executed",
            "separate_directory",
            "agreed_cohort_sha256",
            "same_cohort_as_shadow",
            "classification_columns_present",
        },
    )
    _bool_field(composite, "executed", "composite_enrich")
    _bool_field(composite, "separate_directory", "composite_enrich")
    _bool_field(composite, "same_cohort_as_shadow", "composite_enrich")
    _bool_field(composite, "classification_columns_present", "composite_enrich")
    _optional_sha(composite, "agreed_cohort_sha256", "composite_enrich")
    return composite


def _parse_migration(value: object) -> dict[str, object]:
    migration = _section(
        value,
        "migration",
        {
            "rehearsal_rollback",
            "fk_unresolved",
            "writers_quiesced",
            "promoted",
            "source_identity_matches",
            "effective_config_sha256",
            "effective_profile_sha256",
            "physical_contract",
            "backup_retained",
            "full_cohort",
        },
    )
    _run_status(migration, "rehearsal_rollback", "migration")
    fk_unresolved = migration["fk_unresolved"]
    if fk_unresolved is not None and (
        not isinstance(fk_unresolved, int)
        or isinstance(fk_unresolved, bool)
        or fk_unresolved < 0
    ):
        raise ContourEvidenceError(
            "migration.fk_unresolved must be a non-negative integer or null"
        )
    _bool_field(migration, "writers_quiesced", "migration")
    _bool_field(migration, "promoted", "migration")
    _bool_field(migration, "source_identity_matches", "migration")
    _bool_field(migration, "backup_retained", "migration")
    _bool_field(migration, "full_cohort", "migration")
    _optional_sha(migration, "effective_config_sha256", "migration")
    _optional_sha(migration, "effective_profile_sha256", "migration")
    _optional_text(migration, "physical_contract", "migration")
    return migration


def _parse_live(value: object) -> dict[str, object]:
    live = _section(
        value,
        "live",
        {
            "readback",
            "next_run_executed",
            "next_run_id",
            "tables_match_promoted",
            "classification_reproduced",
            "observed_profile_sha256",
            "observed_config_sha256",
        },
    )
    for key in (
        "readback",
        "next_run_executed",
        "tables_match_promoted",
        "classification_reproduced",
    ):
        _bool_field(live, key, "live")
    _optional_text(live, "next_run_id", "live")
    _optional_sha(live, "observed_profile_sha256", "live")
    _optional_sha(live, "observed_config_sha256", "live")
    return live


def _parse_biological(value: object) -> dict[str, object]:
    claim = _section(
        value,
        "biological",
        {
            "biological_accuracy_accepted",
            "matched_count",
            "matched_count_used_as_qualification",
            "scientific_status",
            "rf008_receipt_status",
            "rf008_receipt_sha256",
            "independent_reference_sha256",
            "reviewer_reference",
        },
    )
    _bool_field(claim, "biological_accuracy_accepted", "biological")
    _bool_field(claim, "matched_count_used_as_qualification", "biological")
    matched = claim["matched_count"]
    if matched is not None and (
        not isinstance(matched, int) or isinstance(matched, bool) or matched < 0
    ):
        raise ContourEvidenceError(
            "biological.matched_count must be a non-negative integer or null"
        )
    _optional_text(claim, "scientific_status", "biological")
    _run_status(claim, "rf008_receipt_status", "biological")
    _optional_sha(claim, "rf008_receipt_sha256", "biological")
    _optional_sha(claim, "independent_reference_sha256", "biological")
    _optional_text(claim, "reviewer_reference", "biological")
    return claim


def _parse_attestation(value: object, label: str) -> dict[str, object]:
    attestation = _section(value, label, {"status", "evidence_sha256"})
    _run_status(attestation, "status", label)
    _optional_sha(attestation, "evidence_sha256", label)
    return attestation


def _parse_ci(value: object) -> dict[str, object]:
    ci = _section(value, "ci", {"status", "commit_sha"})
    _run_status(ci, "status", "ci")
    commit = ci["commit_sha"]
    if commit is not None and not isinstance(commit, str):
        raise ContourEvidenceError("ci.commit_sha must be a string or null")
    return ci


def _parse_counts(value: object) -> dict[str, dict[str, int]]:
    counts = _mapping(value, "shadow.status_counts")
    _exact_keys(counts, set(_STATUS_FIELDS), "shadow.status_counts")
    parsed: dict[str, dict[str, int]] = {}
    for field in _STATUS_FIELDS:
        bucket = _mapping(counts[field], f"shadow.status_counts.{field}")
        parsed_bucket: dict[str, int] = {}
        for key in sorted(bucket):
            item = bucket[key]
            if (
                not isinstance(key, str)
                or not isinstance(item, int)
                or isinstance(item, bool)
                or item < 0
            ):
                raise ContourEvidenceError(
                    f"shadow.status_counts.{field} values must be counts"
                )
            parsed_bucket[key] = item
        parsed[field] = parsed_bucket
    return parsed


def _canonical_identity(path: Path) -> tuple[str, str]:
    document = _yaml_mapping(path)
    pipeline = _mapping(document.get("pipeline"), f"{path}:pipeline")
    classification = _mapping(
        pipeline.get("target_classification"),
        f"{path}:pipeline.target_classification",
    )
    mode = classification.get("mode")
    if not isinstance(mode, str):
        raise ContourEvidenceError(
            f"{path} target_classification.mode must be a string"
        )
    return mode, file_sha256(path)


def _classification_fields(path: Path) -> tuple[str, ...]:
    document = _yaml_mapping(path)
    groups = _column_groups(document, path)
    for group in groups:
        mapping = _mapping(group, f"{path}:column_group")
        if mapping.get("name") != "classification":
            continue
        return _string_tuple(mapping.get("fields"), f"{path}:classification.fields")
    raise ContourEvidenceError(f"{path} has no classification column group")


def _column_groups(document: dict[str, object], path: Path) -> list[object]:
    schema = document.get("schema")
    if isinstance(schema, dict):
        groups = cast(dict[str, object], schema).get("column_groups")
        if isinstance(groups, list):
            return groups
    composite = document.get("composite")
    if isinstance(composite, dict):
        merge = cast(dict[str, object], composite).get("merge")
        if isinstance(merge, dict):
            groups = cast(dict[str, object], merge).get("column_groups")
            if isinstance(groups, list):
                return groups
    raise ContourEvidenceError(f"{path} column_groups are missing")


def _contract_properties(path: Path) -> frozenset[str]:
    safe = _confine(path)
    payload = json.loads(safe.read_text(encoding="utf-8"))  # NOSONAR - confined_io_path
    if not isinstance(payload, dict):
        raise ContourEvidenceError(f"{path} must be a JSON object")
    properties = cast(dict[str, object], payload).get("properties")
    if not isinstance(properties, dict):
        raise ContourEvidenceError(f"{path} properties are missing")
    return frozenset(str(key) for key in cast(dict[str, object], properties))


def _yaml_mapping(path: Path) -> dict[str, object]:
    safe = _confine(path)
    loaded = yaml.safe_load(
        safe.read_text(encoding="utf-8")
    )  # NOSONAR - confined_io_path
    return _mapping(loaded, str(safe))


def _xlsx_has_export_manifest(path: Path) -> bool:
    from openpyxl import load_workbook

    from bioetl.infrastructure.export.xlsx_workbook import XLSX_EXPORT_MANIFEST_SHEET

    workbook = load_workbook(
        path, read_only=True, data_only=True
    )  # NOSONAR - confined_io_path
    try:
        return XLSX_EXPORT_MANIFEST_SHEET in workbook.sheetnames
    finally:
        workbook.close()


def _read_xlsx_rows(path: Path) -> list[dict[str, object]]:
    safe = _confine(path)
    if _xlsx_has_export_manifest(safe):
        from bioetl.infrastructure.export.xlsx_workbook import restore_xlsx_table

        restored = restore_xlsx_table(str(safe))  # NOSONAR - confined_io_path
        return [dict(row) for row in restored.to_pylist()]
    return _read_plain_xlsx_rows(safe)


def _read_plain_xlsx_rows(path: Path) -> list[dict[str, object]]:
    from openpyxl import load_workbook

    workbook = load_workbook(
        path, read_only=True, data_only=True
    )  # NOSONAR - confined_io_path
    try:
        worksheet = workbook.worksheets[0]
        iterator = worksheet.iter_rows(values_only=True)
        header_row = next(iterator, None)
        if header_row is None:
            raise ContourEvidenceError(f"{path} has no header row")
        headers = ["" if cell is None else str(cell) for cell in header_row]
        rows: list[dict[str, object]] = []
        for values in iterator:
            if values is None or all(cell is None or cell == "" for cell in values):
                continue
            rows.append(
                {
                    headers[index]: values[index] if index < len(values) else None
                    for index in range(len(headers))
                    if headers[index]
                }
            )
        return rows
    finally:
        workbook.close()


def _rows_match(
    left: list[dict[str, object]],
    right: list[dict[str, object]],
    columns: tuple[str, ...],
) -> bool:
    if len(left) != len(right):
        return False
    left_ids = _ids(left)
    right_ids = _ids(right)
    if left_ids is None or right_ids is None or left_ids != right_ids:
        return False
    left_by_id = {str(row.get("target_id")): row for row in left}
    right_by_id = {str(row.get("target_id")): row for row in right}
    for target_id in left_ids:
        for column in columns:
            if (
                column not in left_by_id[target_id]
                or column not in right_by_id[target_id]
            ):
                return False
            if _norm_cell(left_by_id[target_id].get(column)) != _norm_cell(
                right_by_id[target_id].get(column)
            ):
                return False
    return True


def _ids(rows: list[dict[str, object]]) -> tuple[str, ...] | None:
    values = [_norm_cell(row.get("target_id")) for row in rows]
    if any(value is None for value in values):
        return None
    identifiers = [cast(str, value) for value in values]
    if len(set(identifiers)) != len(identifiers):
        return None
    return tuple(sorted(identifiers))


def _norm_cell(value: object) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _status_key(value: object) -> str:
    normalized = _norm_cell(value)
    return "null" if normalized is None else normalized


def _phase(status: str, reasons: list[str]) -> dict[str, object]:
    return {"status": status, "reasons": sorted(set(reasons))}


def _biological(
    status: str, reasons: list[str], *, admitted: bool
) -> dict[str, object]:
    return {
        "status": status,
        "reasons": sorted(set(reasons)),
        "rf008_admitted": admitted,
    }


def _unique(reasons: list[str]) -> list[str]:
    return sorted(set(reasons))


def _section(value: object, label: str, keys: set[str]) -> dict[str, object]:
    mapping = _mapping(value, label)
    _exact_keys(mapping, keys, label)
    return mapping


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ContourEvidenceError(f"{label} must be an object")
    return cast(dict[str, object], value)


def _exact_keys(
    mapping: dict[str, object], keys: set[str] | frozenset[str], label: str
) -> None:
    actual = set(mapping)
    if actual != set(keys):
        missing = sorted(set(keys) - actual)
        unknown = sorted(actual - set(keys))
        raise ContourEvidenceError(
            f"{label} keys mismatch missing={missing} unknown={unknown}"
        )


def _bool_field(mapping: dict[str, object], key: str, label: str) -> None:
    if not isinstance(mapping[key], bool):
        raise ContourEvidenceError(f"{label}.{key} must be a boolean")


def _optional_text(mapping: dict[str, object], key: str, label: str) -> None:
    value = mapping[key]
    if value is not None and not isinstance(value, str):
        raise ContourEvidenceError(f"{label}.{key} must be a string or null")


def _optional_sha(mapping: dict[str, object], key: str, label: str) -> None:
    value = mapping[key]
    if value is None:
        return
    if not _pinned(value):
        raise ContourEvidenceError(f"{label}.{key} must be a lowercase SHA-256 or null")


def _run_status(mapping: dict[str, object], key: str, label: str) -> None:
    if mapping[key] not in _RUN_STATUSES:
        raise ContourEvidenceError(f"{label}.{key} must be PASS, FAIL, or NOT_RUN")


def _string_tuple(value: object, label: str) -> tuple[str, ...]:
    if isinstance(value, tuple):
        items = list(value)
    elif isinstance(value, list):
        items = value
    else:
        raise ContourEvidenceError(f"{label} must be a list of strings")
    if not all(isinstance(item, str) and item for item in items):
        raise ContourEvidenceError(f"{label} must be a list of strings")
    return tuple(cast(list[str], items))


def _pinned(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _SHA256
        and all(character in "0123456789abcdef" for character in value)
    )


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


__all__ = [
    "EVIDENCE_SCHEMA",
    "PHYSICAL_CONTRACT",
    "REPORT_SCHEMA",
    "ContourEvidenceError",
    "ContourMeasurementPaths",
    "ContourObservations",
    "apply_measurements",
    "classification_sha256",
    "compare_xlsx_round_trip",
    "evaluate_main_contour",
    "file_sha256",
    "inspect_repository",
    "load_table",
    "parse_evidence",
    "status_distributions",
    "unresolved_assay_targets",
    "write_contour_report",
]
