"""Full-cohort checks and managed-writer quiescence for target promotion."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

import psutil
import yaml

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.domain.normalization.profiles.chembl_target import CHEMBL_TARGET_PROFILE
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
)
from bioetl.domain.schemas.base import ISO8601_TIMESTAMP_REGEX
from bioetl.domain.transformations import generate_content_hash
from bioetl.infrastructure.adapters.iuphar.adapter import (
    IupharTargetClassificationAdapter,
)
from bioetl.infrastructure.adapters.iuphar.snapshot_loader import load_profile

if TYPE_CHECKING:
    from pandas import DataFrame
    from pandera.pandas import DataFrameModel, DataFrameSchema

    from bioetl.domain.normalization.profiles.base import NormalizationProfile
    from bioetl.infrastructure.adapters.iuphar.snapshot_loader import (
        LoadedIupharProfile,
    )

_META = frozenset({"entity_id", "content_hash"})
_LEGACY_PHYSICAL_POLICY = "legacy_physical_target_v30_to_v31_v1"
_OMITTABLE_RUNTIME_COLUMNS = {
    "silver": frozenset({"_run_id", "_run_type", "_ingestion_ts"}),
    "gold": frozenset({"_index", "_dq_error", "_dq_warn"}),
}
_GOLD_SCD_COLUMNS = frozenset({"_valid_from", "_valid_to", "_is_current", "_version"})


def assert_no_managed_writers() -> None:
    """Refuse promotion while known pipeline/workflow/campaign writers live."""
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        if process.info["pid"] == os.getpid():
            continue
        if _managed_writer_command(process.info.get("cmdline") or ()):
            raise RuntimeError(
                f"managed writer is still active: PID {process.info['pid']}"
            )


def _bioetl_arguments(argv: Sequence[str]) -> list[str]:
    for index, arg in enumerate(argv):
        if Path(arg).name.lower() in {"bioetl", "bioetl.exe", "bioetl-script.py"}:
            return list(argv[index + 1 :])
    return []


def _managed_writer_command(argv: Sequence[str]) -> bool:
    """Recognize executable and python-module calls by argument boundary."""
    if any("workflow-campaigns" in arg.replace("\\", "/").split("/") for arg in argv):
        return True
    args = _bioetl_arguments(argv)
    if any(flag in args for flag in ("--dry-run", "--help", "-h")):
        return False
    if any(
        args[index : index + 2] == ["workflow", "run"] for index in range(len(args) - 1)
    ):
        return True
    return "run" in args and (
        "chembl_target" in args or "--pipeline=chembl_target" in args
    )


def _business(row: Mapping[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in row.items()
        if not key.startswith("_") and key not in _META
    }


def _hash_input(row: Mapping[str, object]) -> dict[str, object]:
    record = _business(row)
    if "description" in record and "target_description" not in record:
        record["target_description"] = record["description"]
    return record


def _by_id(rows: Sequence[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    indexed: dict[str, Mapping[str, object]] = {}
    for row in rows:
        identity = row.get("target_id")
        if not isinstance(identity, str) or not identity or identity in indexed:
            raise ValueError("target migration needs unique, nonempty target IDs")
        indexed[identity] = row
    if not indexed:
        raise ValueError("empty target cohort cannot replace a canonical table")
    return indexed


def compare_target_rows(
    original: Sequence[Mapping[str, object]],
    candidate: Sequence[Mapping[str, object]],
    legacy_include_fields: tuple[str, ...],
) -> dict[str, int]:
    """Reject subsets, changed old fields, duplicates or legacy-hash drift."""
    if not legacy_include_fields:
        raise ValueError("explicit frozen legacy hash include-policy required")
    old, new = _by_id(original), _by_id(candidate)
    if old.keys() != new.keys():
        raise ValueError("candidate target IDs differ from the full canonical cohort")
    for key, previous in old.items():
        current = new[key]
        _assert_legacy_values(key, previous, current)
        old_hash = _scoped_target_hash(
            previous, legacy_include_fields, CHEMBL_TARGET_PROFILE
        )
        new_legacy_hash = _scoped_target_hash(
            current, legacy_include_fields, CHEMBL_TARGET_PROFILE
        )
        if old_hash != previous.get("content_hash") or old_hash != new_legacy_hash:
            raise ValueError("legacy 3.0 hash equivalence failed")
    return {"rows": len(old), "legacy_hashes_verified": len(old)}


def _assert_legacy_values(
    key: str, previous: Mapping[str, object], current: Mapping[str, object]
) -> None:
    """Preserve every old physical value, including storage/runtime metadata."""
    if previous.get("entity_id") != current.get("entity_id"):
        raise ValueError(f"candidate changed legacy entity_id: {key}")
    for field, value in previous.items():
        if field == "content_hash":
            continue
        if (
            field not in current
            or type(current[field]) is not type(value)
            or current[field] != value
        ):
            kind = "technical" if field.startswith("_") else "business"
            raise ValueError(f"candidate changed legacy {kind} field: {key}/{field}")


def _scoped_target_hash(
    row: Mapping[str, object],
    include_fields: tuple[str, ...],
    profile: NormalizationProfile,
) -> str:
    """Recompute the runtime hash of an already normalized persisted row.

    Use the same null and set-like policies as RecordNormalizationProcessor.
    Gold's description alias is projected back to the canonical Silver field.
    """
    record = _hash_input(row)
    # Persisted values have already crossed the normalization boundary. Applying
    # display-name or JSON rules again can be lossy (for example virus strains).
    # Only restore the reviewed Gold storage coercion of the integer TaxID.
    taxonomy_id = record.get("taxonomy_id")
    if isinstance(taxonomy_id, float) and taxonomy_id.is_integer():
        record["taxonomy_id"] = int(taxonomy_id)
    return str(
        generate_content_hash(
            record,
            "chembl",
            exclude_none=True,
            include_fields=set(include_fields),
            set_like_fields=set(profile.set_like_fields),
            datetime_policy="v2_datetime_utc",
        )
    )


def _frozen_v31_hash_fields(
    paths: dict[str, Path], legacy_include_fields: tuple[str, ...]
) -> tuple[str, ...]:
    """Extend the exact canonical V30 scope; candidate YAML cannot weaken it."""
    config = yaml.safe_load(paths["config"].read_text(encoding="utf-8"))
    configured = tuple(config["hash_policy"]["hash_policy"]["include_fields"])
    if not configured or configured != legacy_include_fields:
        raise ValueError(
            "migration hash scope differs from the frozen canonical V30 policy"
        )
    return tuple(dict.fromkeys((*legacy_include_fields, *TARGET_CLASSIFICATION_FIELDS)))


def _read_delta(path: Path) -> list[dict[str, object]]:
    from deltalake import DeltaTable

    from bioetl.infrastructure.storage.delta.table_ops import read_delta_records

    # Arrow's JSON-compatible row boundary is untyped in the installed stubs.
    return cast(
        "list[dict[str, object]]",
        read_delta_records(DeltaTable(str(path))),
    )


def validate_target_candidate(
    paths: dict[str, Path],
    legacy_include_fields: tuple[str, ...],
) -> dict[str, object]:
    """Validate admission, strict candidate schemas and both entire cohorts."""
    from bioetl.domain.contracts.gold.chembl_target_classification import (
        ChEMBLTargetGoldSchemaV31,
    )
    from bioetl.domain.schemas.chembl.target import TargetSchemaV31

    profile = _load_candidate_profile(paths)
    v31_include_fields = _frozen_v31_hash_fields(paths, legacy_include_fields)
    result: dict[str, object] = {}
    layers = {}
    for name, schema in (
        ("silver", TargetSchemaV31),
        ("gold", ChEMBLTargetGoldSchemaV31),
    ):
        result[name], layers[name] = _validate_candidate_layer(
            name,
            schema,
            paths,
            profile.profile_sha256,
            legacy_include_fields,
            v31_include_fields,
        )
    _verify_source_classifications(layers, profile)
    _assert_candidate_cohort_closure(paths, layers["gold"])
    result["fk_closure"] = "PASS"
    result["profile_sha256"] = profile.profile_sha256
    return result


def _load_candidate_profile(paths: dict[str, Path]) -> LoadedIupharProfile:
    """Require the exact admitted enrich profile selected by candidate YAML."""
    config = yaml.safe_load(paths["candidate_config"].read_text(encoding="utf-8"))
    classification = config["pipeline"]["target_classification"]
    if classification["mode"] != "enrich":
        raise ValueError("candidate configuration must select admitted enrich")
    profile_path = Path(classification["snapshot_manifest"])
    if not profile_path.is_absolute():
        # Entity configuration lives at configs/entities/chembl/target.yaml.
        root = paths["config"].resolve().parents[3]
        profile_path = root / profile_path
    return load_profile(
        profile_path,
        classification["snapshot_manifest_sha256"],
        require_acceptance=True,
    )


def _validate_candidate_layer(
    name: str,
    schema: type[DataFrameModel],
    paths: dict[str, Path],
    profile_sha256: str,
    legacy_include_fields: tuple[str, ...],
    v31_include_fields: tuple[str, ...],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Validate one full layer and its unchanged legacy/hash projection."""
    old = _read_delta(paths[name])
    new = _read_delta(paths["candidate_" + name])
    result: dict[str, object] = dict(
        compare_target_rows(old, new, legacy_include_fields)
    )
    result["physical_projection"] = _validate_physical_projection(
        name, schema, old, new
    )
    if any(row.get("target_class_profile_sha256") != profile_sha256 for row in new):
        raise ValueError("candidate rows belong to another IUPHAR profile")
    _verify_candidate_hashes(new, v31_include_fields)
    return result, new


def _physical_columns(rows: Sequence[Mapping[str, object]]) -> set[str]:
    if not rows:
        raise ValueError("empty physical target cohort")
    columns = set(rows[0])
    if any(set(row) != columns for row in rows):
        raise ValueError("target physical cohort has inconsistent columns")
    return columns


def _validate_physical_projection(
    layer: str,
    model: type[DataFrameModel],
    old: Sequence[Mapping[str, object]],
    new: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Validate a frozen physical projection without changing runtime schemas.

    Only declared historical technical omissions are permitted. Gold's absent
    nullable description is represented as unknown in the validation view,
    never materialized into the preserved rows or used as invented provenance.
    """
    import pandas as pd

    previous, current = _physical_columns(old), _physical_columns(new)
    if previous.intersection(TARGET_CLASSIFICATION_FIELDS):
        raise ValueError("physical target migration requires a legacy V30 cohort")
    if current != previous.union(TARGET_CLASSIFICATION_FIELDS):
        raise ValueError(
            "candidate physical columns must equal old columns plus nine classification fields"
        )
    schema = model.to_schema()
    omissions = sorted(
        _OMITTABLE_RUNTIME_COLUMNS[layer].intersection(schema.columns) - previous
    )
    if omissions:
        schema = schema.remove_columns(omissions)
    frame = pd.DataFrame(new)
    storage = _validate_storage_envelope(layer, previous, old)
    if storage:
        frame = frame.drop(columns=storage)
    nullable_absences = _logical_nullable_absences(layer, previous, schema, frame)
    schema.validate(frame, lazy=True)
    return {
        "policy_id": _LEGACY_PHYSICAL_POLICY
        if any((omissions, storage, nullable_absences))
        else "target_v31_runtime_shape",
        "omitted_runtime_columns": omissions,
        "logical_nullable_absences": nullable_absences,
        "storage_envelope_columns": storage,
        "physical_columns_preserved": True,
    }


def _logical_nullable_absences(
    layer: str, previous: set[str], schema: DataFrameSchema, frame: DataFrame
) -> list[str]:
    if layer != "gold" or "description" in previous:
        return []
    if not schema.columns["description"].nullable:
        raise ValueError("Gold description is no longer a nullable logical field")
    frame["description"] = None
    return ["description"]


def _validate_storage_envelope(
    layer: str, columns: set[str], rows: Sequence[Mapping[str, object]]
) -> list[str]:
    storage = columns.intersection(_GOLD_SCD_COLUMNS)
    if not storage:
        return []
    if layer != "gold" or storage != _GOLD_SCD_COLUMNS:
        raise ValueError("unsupported or incomplete target storage envelope")
    for row in rows:
        _validate_scd_types(row)
    return sorted(storage)


def _validate_scd_types(row: Mapping[str, object]) -> None:
    if not _scd_timestamp(row["_valid_from"]):
        raise ValueError("Gold SCD _valid_from requires datetime or valid ISO8601 text")
    valid_to = row["_valid_to"]
    if valid_to is not None and not _scd_timestamp(valid_to):
        raise ValueError(
            "Gold SCD _valid_to requires nullable datetime or valid ISO8601 text"
        )
    if type(row["_is_current"]) is not bool:
        raise ValueError("Gold SCD _is_current must retain its boolean type")
    version = row["_version"]
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("Gold SCD _version must retain its positive integer type")


def _scd_timestamp(value: object) -> bool:
    if isinstance(value, datetime):
        return True
    if (
        not isinstance(value, str)
        or re.fullmatch(ISO8601_TIMESTAMP_REGEX, value) is None
    ):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _verify_candidate_hashes(
    rows: Sequence[Mapping[str, object]], include_fields: tuple[str, ...]
) -> None:
    """Reject arbitrary or stale candidate hashes, including classification drift."""
    profile = target_v31_normalization_profile()
    for row in rows:
        if row.get("content_hash") != _scoped_target_hash(row, include_fields, profile):
            raise ValueError("candidate V31 content hash verification failed")


def _verify_source_classifications(
    layers: Mapping[str, list[dict[str, object]]], profile: LoadedIupharProfile
) -> None:
    """Reclassify original Silver inputs, then bind both candidate projections."""
    adapter = IupharTargetClassificationAdapter(profile)
    expected: dict[str, Mapping[str, str | None]] = {}
    for target_id, row in _by_id(layers["silver"]).items():
        business = {
            key: value
            for key, value in _business(row).items()
            if key not in TARGET_CLASSIFICATION_FIELDS
        }
        result = adapter.classify_record(
            business,
            input_row_id="migration:" + target_id,
            run_id="migration-validation",
            run_started_at="1970-01-01T00:00:00+00:00",
        )
        _assert_classification_projection(row, result.projection)
        expected[target_id] = result.projection
    for target_id, row in _by_id(layers["gold"]).items():
        if target_id not in expected:
            raise ValueError("candidate Gold target has no classified Silver source")
        _assert_classification_projection(row, expected[target_id])


def _assert_classification_projection(
    row: Mapping[str, object], expected: Mapping[str, str | None]
) -> None:
    """Keep direct, local and effective fields equal to the admitted classifier."""
    for field in TARGET_CLASSIFICATION_FIELDS:
        if row.get(field) != expected[field]:
            raise ValueError(
                f"candidate classification differs from admitted source: {field}"
            )


def _assert_candidate_cohort_closure(
    paths: dict[str, Path], gold_rows: Sequence[Mapping[str, object]]
) -> None:
    """Require every final assay FK, preserving additional Gold targets.

    Baseline reconciliation mutates Gold only; Silver can retain a superset.
    Each old/new layer's full identity set is checked independently above.
    """
    assay_targets = {
        row["target_id"]
        for row in _read_delta(paths["assay"])
        if row.get("target_id") is not None
    }
    if not assay_targets.issubset(_by_id(gold_rows)):
        raise ValueError("baseline assay/target foreign-key closure failed")
