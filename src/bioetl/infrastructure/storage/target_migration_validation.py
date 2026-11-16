"""Full-cohort checks and managed-writer quiescence for target promotion."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, cast

import psutil
import yaml

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.domain.normalization.profiles.chembl_target import CHEMBL_TARGET_PROFILE
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
)
from bioetl.domain.transformations import generate_content_hash
from bioetl.infrastructure.adapters.iuphar.adapter import (
    IupharTargetClassificationAdapter,
)
from bioetl.infrastructure.adapters.iuphar.snapshot_loader import load_profile

if TYPE_CHECKING:
    from pandera.pandas import DataFrameModel

    from bioetl.domain.normalization.profiles.base import NormalizationProfile
    from bioetl.infrastructure.adapters.iuphar.snapshot_loader import (
        LoadedIupharProfile,
    )

_META = frozenset({"entity_id", "content_hash"})


def assert_no_managed_writers() -> None:
    """Refuse promotion while known pipeline/workflow/campaign writers live."""
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        if process.info["pid"] == os.getpid():
            continue
        command = " ".join(process.info.get("cmdline") or ())
        if any(
            marker in command
            for marker in (
                "bioetl workflow run",
                "bioetl run chembl_target",
                "workflow-campaigns" + os.sep,
                "workflow-campaigns/",
                "workflow-campaigns\\",
            )
        ):
            raise RuntimeError(
                f"managed writer is still active: PID {process.info['pid']}"
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
    """Preserve the original entity identity and every old business value."""
    if previous.get("entity_id") != current.get("entity_id"):
        raise ValueError(f"candidate changed legacy entity_id: {key}")
    for field, value in _business(previous).items():
        if field not in current or current[field] != value:
            raise ValueError(f"candidate changed legacy business field: {key}/{field}")


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
) -> tuple[dict[str, int], list[dict[str, object]]]:
    """Validate one full layer and its unchanged legacy/hash projection."""
    old = _read_delta(paths[name])
    new = _read_delta(paths["candidate_" + name])
    import pandas as pd

    schema.validate(pd.DataFrame(new), lazy=True)
    if any(row.get("target_class_profile_sha256") != profile_sha256 for row in new):
        raise ValueError("candidate rows belong to another IUPHAR profile")
    result = compare_target_rows(old, new, legacy_include_fields)
    _verify_candidate_hashes(new, v31_include_fields)
    return result, new


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
