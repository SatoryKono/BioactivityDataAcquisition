"""Species-variant projection of one official GtoPdb target group."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from iuphar_target_class.iuphar_mapping import approved_class_mappings
from iuphar_target_class.stage0.io import canonical_json_bytes

from ._manifest import sha256
from ._official_targets_csv import (
    _FAMILY_ID,
    _FAMILY_NAME,
    _TARGET_ID,
    _TARGET_NAME,
    SOURCE_FORMAT,
    SPECIES_COLUMNS,
    OfficialProjection,
    _consistent,
    _groups,
    _one,
    _read_export,
    _selection,
    _StringList,
    _tokens,
)
from ._snapshot_payloads import identifier
from .snapshot_evidence import SourceEvidence


def _variant(row: Mapping[str, str], taxon: str) -> dict[str, object] | None:
    prefix, symbol = SPECIES_COLUMNS[taxon]
    accessions = _tokens(row[prefix + " SwissProt"])
    gene_id, gene_symbol = _one(row[prefix + " Entrez Gene"]), _one(row[symbol])
    if not accessions and gene_id is None and gene_symbol is None:
        return None
    return {
        "targetId": identifier(row[_TARGET_ID]),
        "taxonId": taxon,
        "uniprotIds": accessions,
        "geneId": gene_id,
        "geneSymbol": gene_symbol,
        "name": row[_TARGET_NAME] or None,
        "names": [
            row[key]
            for key in (
                _TARGET_NAME,
                "Target systematic name",
                "Target abbreviated name",
            )
            if row[key]
        ],
        "synonyms": _tokens(row["synonyms"]),
    }


def _family_rows(
    group: list[tuple[int, dict[str, str]]], release: str
) -> list[dict[str, object]]:
    types, _ = approved_class_mappings(release)
    result: list[dict[str, object]] = []
    for record, row in group:
        if row["Type"] not in types:
            raise ValueError("unsupported official family type")
        result.append(
            {
                "familyId": identifier(row[_FAMILY_ID]),
                "familyName": row[_FAMILY_NAME],
                "familyType": row["Type"],
                "sourceRecord": record,
            }
        )
    return result


def _project_group(
    group: list[tuple[int, dict[str, str]]],
    species: list[str],
    release: str,
    raw_hash: str,
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    row = _consistent(group)
    families = _family_rows(group, release)
    outputs: list[dict[str, object]] = []
    gaps: list[dict[str, str]] = []
    for taxon in species:
        variant = _variant(row, taxon)
        if variant is None:
            gaps.append({"target_id": row[_TARGET_ID], "taxon_id": taxon})
            continue
        outputs.append(
            {
                **variant,
                "familyIds": sorted({str(item["familyId"]) for item in families}),
                "familyRows": families,
                "source_sha256": raw_hash,
                "annotationCapability": "family_only",
            }
        )
    if not outputs:
        raise ValueError(
            "target without supported species identity needs explicit exclusion"
        )
    return outputs, gaps


def _raw_scope(
    evidence: SourceEvidence,
) -> tuple[
    bytes,
    list[dict[str, str]],
    dict[str, list[tuple[int, dict[str, str]]]],
    set[str],
    list[str],
]:
    if evidence.source_format != SOURCE_FORMAT or set(evidence.raw_artifacts) != {
        "targets_csv"
    }:
        raise ValueError("unsupported official export source format")
    raw = evidence.raw_artifacts["targets_csv"]
    rows = _read_export(raw, evidence.provider_release)
    groups = _groups(rows)
    scope = evidence.scope
    if (
        len(rows) != scope["expected_raw_row_count"]
        or len(groups) != scope["expected_provider_target_count"]
    ):
        raise ValueError("official raw denominator differs from reviewed scope")
    selected = _selection(groups, scope)
    species = cast(_StringList, scope["species_taxon_ids"])
    if not set(species).issubset(SPECIES_COLUMNS):
        raise ValueError(
            "official wide export supports only its explicit species columns"
        )
    return raw, rows, groups, selected, species


def project_official_export(evidence: SourceEvidence) -> OfficialProjection:
    """Preserve all raw rows; CSV Type is family evidence, never target type."""
    raw, rows, groups, selected, species = _raw_scope(evidence)
    scope = evidence.scope
    projected: list[dict[str, object]] = []
    uncovered: list[dict[str, str]] = []
    for target in sorted(selected, key=int):
        outputs, gaps = _project_group(
            groups[target], species, evidence.provider_release, sha256(raw)
        )
        projected.extend(outputs)
        uncovered.extend(gaps)
    if len(projected) != scope["expected_variant_count"]:
        raise ValueError("species variant count differs from reviewed scope")
    loaded_types = {row["Type"] for target in selected for _, row in groups[target]}
    if not set(cast(_StringList, scope["required_family_types"])).issubset(
        loaded_types
    ):
        raise ValueError("required reviewed family types are missing")
    audit = {
        "artifact": "bioetl_iuphar_projection_audit",
        "schema_version": 2,
        "annotation_capability": "family_only",
        "raw_row_count": len(rows),
        "raw_provider_target_count": len(groups),
        "included_provider_target_count": len(selected),
        "species_variant_count": len(projected),
        "uncovered_species": uncovered,
        "included_source_records": {
            target: [record for record, _ in groups[target]]
            for target in sorted(selected, key=int)
        },
        "excluded_targets": scope["excluded_targets"],
    }
    return OfficialProjection(
        canonical_json_bytes(projected),
        canonical_json_bytes(audit),
        not uncovered and not scope["excluded_targets"],
    )
