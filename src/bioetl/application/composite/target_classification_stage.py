"""Post-join target classification for the composite target merge.

The stage reads a whitelist of qualified columns after dependency joins.
It does not send the merged row to the classifier and it does not publish
evidence. Publication happens only after the merge write succeeds.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Final, cast

import polars as pl

from bioetl.application.composite.target_protein_classification_summary import (
    agreed_chembl_release,
)
from bioetl.application.services.target_runtime.classification import (
    TargetClassificationRunState,
)
from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.domain.entities.enriched_target_features import (
    COMPOSITE_CLASSIFICATION_BATCH_ID,
    COMPOSITE_CLASSIFICATION_OWNER,
    OPTIONAL_ENRICHED_FEATURES,
    composite_classification_row_id,
    composite_classification_run_id,
    hierarchy_mapping_records,
)
from bioetl.domain.transformations.hashing import generate_content_hash
from bioetl.domain.types import JsonDict

_KEYWORD_ID: Final = re.compile(r"^(?:KW-\d+|\d+)$")
_SHA256: Final = re.compile(r"^[0-9a-f]{64}$")
_HASH_ANCHOR: Final = "1970-01-01T00:00:00+00:00"
_METADATA_FIELDS: Final = (
    "target_classification_owner",
    "target_classification_completeness",
    "target_classification_absent_features",
)
_FRAME_FIELDS: Final = (*TARGET_CLASSIFICATION_FIELDS, *_METADATA_FIELDS)
_RELEASE_COLUMNS: Final = (
    "chembl.target_protein_classification.chembl_release",
    "chembl_release",
)
_EC_COLUMNS: Final = (
    "uniprot.protein.protein_ec_numbers",
    "protein_ec_numbers",
    "chembl.target.target_ec_numbers",
    "target_ec_numbers",
)
_KEYWORD_COLUMNS: Final = ("uniprot.protein.keywords", "keywords")
_ACCESSION_COLUMNS: Final = (
    "uniprot.idmapping.uniprot_accession",
    "uniprot.protein.accession",
    "uniprot_accession",
)
_TARGET_ID_COLUMNS: Final = ("target_id", "chembl.target.target_id")
_TARGET_TYPE_COLUMNS: Final = ("chembl.target.target_type", "target_type")
_PREF_NAME_COLUMNS: Final = ("chembl.target.pref_name", "pref_name")
_TAXON_COLUMNS: Final = ("chembl.target.taxonomy_id", "taxonomy_id")
_ORGANISM_COLUMNS: Final = ("chembl.target.organism", "organism")
_ACCESSION_LIST_COLUMNS: Final = (
    "chembl.target.component_accessions",
    "component_accessions",
)
_GENE_COLUMNS: Final = ("chembl.target.gene_symbol", "gene_symbol")
_HIERARCHY_PARTS: Final = ("id", "name", "desc")
_HIERARCHY_LEVELS: Final = (1, 2, 3, 4, 5)
_HASH_FIELDS: Final = ("target_id", *_FRAME_FIELDS)


def schema_column_names(schema: object) -> frozenset[str] | None:
    """Return Pandera column names when the object exposes them."""
    current = schema
    to_schema = getattr(current, "to_schema", None)
    if callable(to_schema):
        current = to_schema()
    columns = getattr(current, "columns", None)
    if isinstance(columns, dict):
        return frozenset(str(name) for name in columns)
    return None


def project_gold_classification_frame(df: pl.DataFrame, schema: object) -> pl.DataFrame:
    """Keep classification columns out of a strict Gold schema that predates them.

    Silver retains the columns. Gold adoption of the same projection belongs
    to the later output contract.
    """
    names = schema_column_names(schema)
    if names is None:
        return df
    hidden = [column for column in _FRAME_FIELDS if column not in names]
    present = [column for column in hidden if column in df.columns]
    if not present:
        return df
    return df.drop(present)


class CompositeTargetClassificationStage:
    """Apply one pure classification pass and retain its evidence until commit."""

    def __init__(self, session: TargetClassificationRunState) -> None:
        self._session = session
        self._decisions: dict[str, dict[str, str | None]] = {}

    def apply(
        self,
        df: pl.DataFrame,
        *,
        run_id: str,
        started_at: datetime | None,
        dependency_frames: Mapping[str, pl.DataFrame] | None = None,
    ) -> pl.DataFrame:
        """Classify joined rows. Evidence stays in memory."""
        self._decisions = {}
        if df.is_empty():
            return df
        if not any(column in df.columns for column in _TARGET_ID_COLUMNS):
            return df
        occurrence = composite_classification_run_id(run_id)
        started = _started_at(started_at)
        hashes = _source_hashes(dependency_frames)
        rows = list(df.iter_rows(named=True))
        seen: set[str] = set()
        write_fields = (
            _FRAME_FIELDS if self._session.mode == "enrich" else _METADATA_FIELDS
        )
        updates: dict[str, list[str | None]] = {name: [] for name in write_fields}
        for row in rows:
            projected = _project_row(
                row,
                source_hashes=hashes,
                session=self._session,
                occurrence=occurrence,
                started_at=started,
                seen=seen,
            )
            target_id = _text(row.get("target_id")) or _text(
                row.get("chembl.target.target_id")
            )
            if target_id is not None:
                self._decisions[target_id] = projected
            for name in write_fields:
                updates[name].append(projected.get(name))
        result = df
        for name, values in updates.items():
            result = result.with_columns(
                pl.Series(name=name, values=values, dtype=pl.Utf8)
            )
        return result

    def seal_decision(self, df: pl.DataFrame) -> pl.DataFrame:
        """Rewrite the classification decision after seed coalesce.

        ``seed_priority`` fills a null composite field from the seed column.
        The published decision owns those nulls, so they are written again
        after conflict resolution.
        """
        if df.is_empty() or not self._decisions or "target_id" not in df.columns:
            return df
        write_fields = (
            _FRAME_FIELDS if self._session.mode == "enrich" else _METADATA_FIELDS
        )
        updates: dict[str, list[str | None]] = {name: [] for name in write_fields}
        for row in df.iter_rows(named=True):
            decision = self._decisions.get(_text(row.get("target_id")) or "")
            for name in write_fields:
                if decision is None:
                    updates[name].append(_text(row.get(name)))
                    continue
                updates[name].append(decision.get(name))
        result = df
        for name, values in updates.items():
            result = result.with_columns(
                pl.Series(name=name, values=values, dtype=pl.Utf8)
            )
        return result

    def refresh_content_hash(self, df: pl.DataFrame) -> pl.DataFrame:
        """Bind the surviving classification fields into ``content_hash``."""
        if df.is_empty() or "target_classification_owner" not in df.columns:
            return df
        hashes: list[str | None] = []
        has_prior = "content_hash" in df.columns
        for row in df.iter_rows(named=True):
            if row.get("target_classification_owner") != COMPOSITE_CLASSIFICATION_OWNER:
                hashes.append(_text(row.get("content_hash")) if has_prior else None)
                continue
            payload: JsonDict = {
                "prior_content_hash": _text(row.get("content_hash"))
                if has_prior
                else None
            }
            for field_name in _HASH_FIELDS:
                if field_name in row:
                    payload[field_name] = row.get(field_name)
            hashes.append(str(generate_content_hash(payload, "composite_target")))
        return df.with_columns(
            pl.Series(name="content_hash", values=hashes, dtype=pl.Utf8)
        )

    def commit(self, run_id: str) -> None:
        """Publish evidence after the merge write has succeeded."""
        self._session.commit_detached(composite_classification_run_id(run_id))

    def abandon(self, run_id: str) -> None:
        """Drop unpublished evidence when persistence fails."""
        self._session.abandon_detached(composite_classification_run_id(run_id))


def _started_at(value: datetime | None) -> str:
    if value is None:
        return _HASH_ANCHOR
    return value.isoformat()


def _project_row(
    row: Mapping[str, object],
    *,
    source_hashes: Mapping[tuple[str, str], str],
    session: TargetClassificationRunState,
    occurrence: str,
    started_at: str,
    seen: set[str],
) -> dict[str, str | None]:
    features = _feature_bundle(row, source_hashes)
    business = cast(JsonDict, features["business"])
    absent = cast(tuple[str, ...], features["absent"])
    target_id = _text(business.get("target_id"))
    output = _empty_output(cast(str, features["completeness"]), absent)
    if target_id is None:
        return output
    row_id = composite_classification_row_id(target_id)
    if row_id in seen:
        raise ValueError("duplicate composite classification target id")
    seen.add(row_id)
    if session.mode != "enrich":
        session.classify_detached(
            run_id=occurrence,
            batch_id=COMPOSITE_CLASSIFICATION_BATCH_ID,
            row_id=row_id,
            business_data=business,
            run_started_at=started_at,
        )
        return output
    result = session.classify_detached(
        run_id=occurrence,
        batch_id=COMPOSITE_CLASSIFICATION_BATCH_ID,
        row_id=row_id,
        business_data=business,
        run_started_at=started_at,
    )
    for field_name in TARGET_CLASSIFICATION_FIELDS:
        output[field_name] = _text(result.projection.get(field_name))
    return output


def _empty_output(completeness: str, absent: tuple[str, ...]) -> dict[str, str | None]:
    output: dict[str, str | None] = dict.fromkeys(_FRAME_FIELDS)
    output["target_classification_owner"] = COMPOSITE_CLASSIFICATION_OWNER
    output["target_classification_completeness"] = completeness
    output["target_classification_absent_features"] = json.dumps(
        list(absent), separators=(",", ":")
    )
    return output


def _feature_bundle(
    row: Mapping[str, object],
    source_hashes: Mapping[tuple[str, str], str],
) -> dict[str, object]:
    _target_column, target_id = _first_text(row, _TARGET_ID_COLUMNS)
    accession_column, accession = _first_text(row, _ACCESSION_COLUMNS)
    ec_column, ec_value = _first_present(row, _EC_COLUMNS)
    keyword_column, keyword_value = _first_present(row, _KEYWORD_COLUMNS)
    keyword_ids = _controlled_keyword_ids(keyword_value)
    hierarchy = _hierarchy(row)
    release, release_status = agreed_chembl_release(
        row.get(column) for column in _RELEASE_COLUMNS if column in row
    )
    origins = (
        _origin(
            "ec",
            present=ec_value is not None,
            column=ec_column,
            pipeline="uniprot_protein",
            source_hash=source_hashes.get(("uniprot_protein", accession or "")),
        ),
        _origin(
            "protein_hierarchy",
            present=bool(hierarchy),
            column=(
                "chembl.target_protein_classification.target_protein_class_name_L1"
                if hierarchy
                else None
            ),
            pipeline="chembl_target_protein_classification",
            source_hash=source_hashes.get(
                ("chembl_target_protein_classification", target_id or "")
            ),
        ),
        _origin(
            "keywords",
            present=bool(keyword_ids),
            column=keyword_column,
            pipeline="uniprot_protein",
            source_hash=source_hashes.get(("uniprot_protein", accession or "")),
            status=_keyword_status(keyword_value, keyword_ids),
        ),
        _origin(
            "uniprot_accession",
            present=accession is not None,
            column=accession_column,
            pipeline="uniprot_idmapping",
            source_hash=source_hashes.get(("uniprot_idmapping", target_id or "")),
        ),
        _origin(
            "taxon",
            present=_first_present(row, _TAXON_COLUMNS)[1] is not None,
            column=_first_present(row, _TAXON_COLUMNS)[0],
            pipeline="chembl_target",
            source_hash=source_hashes.get(("chembl_target", target_id or "")),
        ),
    )
    absent = tuple(
        feature_id
        for feature_id in OPTIONAL_ENRICHED_FEATURES
        if not any(
            item["feature_id"] == feature_id and item["present"] for item in origins
        )
    )
    business: JsonDict = {}
    _put(business, "target_id", target_id)
    _put(business, "target_type", _first_text(row, _TARGET_TYPE_COLUMNS)[1])
    _put(business, "pref_name", _first_text(row, _PREF_NAME_COLUMNS)[1])
    _put(business, "taxonomy_id", _first_present(row, _TAXON_COLUMNS)[1])
    _put(business, "organism", _first_text(row, _ORGANISM_COLUMNS)[1])
    _put(
        business,
        "component_accessions",
        _first_present(row, _ACCESSION_LIST_COLUMNS)[1],
    )
    _put(business, "uniprot_accession", accession)
    _put(business, "gene_symbol", _first_text(row, _GENE_COLUMNS)[1])
    if ec_value is not None:
        business["target_ec_numbers"] = ec_value
    if keyword_ids:
        business["controlled_keyword_ids"] = list(keyword_ids)
    if hierarchy:
        business["protein_hierarchy"] = hierarchy
    business["hierarchy_field_mapping"] = [
        dict(item)
        for item in hierarchy_mapping_records(
            chembl_release=release,
            release_status=release_status,
        )
    ]
    business["feature_origins"] = [dict(item) for item in origins]
    completeness = "limited" if absent else "full"
    return {"business": business, "completeness": completeness, "absent": absent}


def _origin(
    feature_id: str,
    *,
    present: bool,
    column: str | None,
    pipeline: str,
    source_hash: str | None,
    status: str | None = None,
) -> dict[str, object]:
    origin: dict[str, object] = {
        "feature_id": feature_id,
        "present": present,
        "source_pipeline": pipeline,
        "status": status or ("present" if present else "absent"),
    }
    if column is not None and present:
        origin["qualified_column"] = column
    if source_hash is not None:
        origin["source_content_hash"] = source_hash
    return origin


def _keyword_status(value: object, keyword_ids: tuple[str, ...]) -> str:
    if keyword_ids:
        return "present"
    if value is None:
        return "absent"
    return "uncontrolled_ignored"


def _hierarchy(row: Mapping[str, object]) -> list[dict[str, object]]:
    levels: list[dict[str, object]] = []
    for level in _HIERARCHY_LEVELS:
        entry: dict[str, object] = {"level": level}
        found = False
        for part in _HIERARCHY_PARTS:
            qualified = (
                "chembl.target_protein_classification."
                f"target_protein_class_{part}_L{level}"
            )
            column, value = _first_text(
                row, (qualified, f"target_protein_class_{part}_L{level}")
            )
            if value is None:
                continue
            entry[part] = value
            entry["qualified_column"] = column or qualified
            found = True
        if found:
            entry["equivalent_to_historical_m_column"] = False
            levels.append(entry)
    return levels


def _source_hashes(
    frames: Mapping[str, pl.DataFrame] | None,
) -> dict[tuple[str, str], str]:
    if not frames:
        return {}
    index: dict[tuple[str, str], str] = {}
    key_fields = ("target_id", "uniprot_accession", "accession")
    for pipeline in sorted(frames):
        frame = frames[pipeline]
        if "content_hash" not in frame.columns:
            continue
        key_field = next((name for name in key_fields if name in frame.columns), None)
        if key_field is None:
            continue
        for row in frame.iter_rows(named=True):
            key = _text(row.get(key_field))
            digest = _sha256(row.get("content_hash"))
            if key is not None and digest is not None:
                index[(pipeline, key)] = digest
    return index


def _controlled_keyword_ids(value: object) -> tuple[str, ...]:
    found: list[str] = []
    for item in _json_items(value):
        raw = item.get("id") if isinstance(item, dict) else item
        if not isinstance(raw, str):
            continue
        token = raw.strip()
        if _KEYWORD_ID.fullmatch(token) and token not in found:
            found.append(token)
    return tuple(found)


def _json_items(value: object) -> tuple[object, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return ()
        if text.startswith("["):
            try:
                loaded = json.loads(text)
            except json.JSONDecodeError:
                return ()
            if isinstance(loaded, list):
                return tuple(loaded)
            return ()
        return tuple(part.strip() for part in re.split(r"[|;]", text) if part.strip())
    return ()


def _first_present(
    row: Mapping[str, object], columns: Sequence[str]
) -> tuple[str | None, object]:
    for column in columns:
        if column not in row:
            continue
        value = row.get(column)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return column, value
    return None, None


def _first_text(
    row: Mapping[str, object], columns: Sequence[str]
) -> tuple[str | None, str | None]:
    column, value = _first_present(row, columns)
    return column, _text(value)


def _put(business: JsonDict, key: str, value: object) -> None:
    if value is not None:
        business[key] = value


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _sha256(value: object) -> str | None:
    text = _text(value)
    if text is None or _SHA256.fullmatch(text) is None:
        return None
    return text


__all__ = [
    "CompositeTargetClassificationStage",
    "project_gold_classification_frame",
    "schema_column_names",
]
