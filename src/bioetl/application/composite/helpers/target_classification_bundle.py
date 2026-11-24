"""Build the whitelisted business payload for one joined target row."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from bioetl.application.composite.helpers.target_classification_values import (
    controlled_keyword_ids,
    first_ec,
    first_present,
    first_text,
    hierarchy_levels,
    keyword_status,
    put_value,
    sha256_text,
)
from bioetl.application.composite.target_protein_classification_summary import (
    agreed_chembl_release,
)
from bioetl.domain.composite.enriched_target_features import (
    OPTIONAL_ENRICHED_FEATURES,
    hierarchy_mapping_records,
)
from bioetl.domain.types import JsonDict

_RELEASE_COLUMNS: Final = (
    "chembl.target_protein_classification.chembl_release",
    "chembl_release",
)
_EC_COLUMNS: Final = (
    "uniprot.protein.protein_ec_numbers",
    "protein_ec_numbers",
)
_CHEMBL_EC_COLUMNS: Final = ("chembl.target.target_ec_numbers", "target_ec_numbers")
_KEYWORD_COLUMNS: Final = ("uniprot.protein.keywords", "keywords")
_ACCESSION_COLUMNS: Final = (
    "uniprot.idmapping.uniprot_accession",
    "uniprot.protein.accession",
    "uniprot_accession",
)
TARGET_ID_COLUMNS: Final = ("target_id", "chembl.target.target_id")
_TARGET_TYPE_COLUMNS: Final = ("chembl.target.target_type", "target_type")
_PREF_NAME_COLUMNS: Final = ("chembl.target.pref_name", "pref_name")
_TAXON_COLUMNS: Final = ("chembl.target.taxonomy_id", "taxonomy_id")
_ORGANISM_COLUMNS: Final = ("chembl.target.organism", "organism")
_ACCESSION_LIST_COLUMNS: Final = (
    "chembl.target.component_accessions",
    "component_accessions",
)
_GENE_COLUMNS: Final = ("chembl.target.gene_symbol", "gene_symbol")


def feature_bundle(
    row: Mapping[str, object],
    hashes: Mapping[tuple[str, str], str],
) -> dict[str, object]:
    """Build the whitelist, its origins, and the completeness flag."""
    _target_column, target_id = first_text(row, TARGET_ID_COLUMNS)
    accession_column, accession = first_text(row, _ACCESSION_COLUMNS)
    ec_column, ec_value = first_ec(row, (*_EC_COLUMNS, *_CHEMBL_EC_COLUMNS))
    keyword_column, keyword_value = first_present(row, _KEYWORD_COLUMNS)
    keyword_ids = controlled_keyword_ids(keyword_value)
    hierarchy, hierarchy_columns = hierarchy_levels(row)
    release, release_status = agreed_chembl_release(
        row.get(column) for column in _RELEASE_COLUMNS if column in row
    )
    origins = _origins(
        row,
        hashes,
        target_id=target_id,
        accession=accession,
        accession_column=accession_column,
        ec_column=ec_column,
        keyword_column=keyword_column,
        keyword_value=keyword_value,
        keyword_ids=keyword_ids,
        hierarchy_columns=hierarchy_columns,
    )
    absent = _absent(origins)
    business = _business(
        row,
        target_id=target_id,
        accession=accession,
        ec_value=ec_value,
        keyword_ids=keyword_ids,
        hierarchy=hierarchy,
        release=release,
        release_status=release_status,
        origins=origins,
    )
    completeness = "limited" if absent else "full"
    return {"business": business, "completeness": completeness, "absent": absent}


def _absent(origins: tuple[dict[str, object], ...]) -> tuple[str, ...]:
    return tuple(
        feature_id
        for feature_id in OPTIONAL_ENRICHED_FEATURES
        if not any(
            item["feature_id"] == feature_id and item["present"] for item in origins
        )
    )


def _origins(
    row: Mapping[str, object],
    hashes: Mapping[tuple[str, str], str],
    *,
    target_id: str | None,
    accession: str | None,
    accession_column: str | None,
    ec_column: str | None,
    keyword_column: str | None,
    keyword_value: object,
    keyword_ids: tuple[str, ...],
    hierarchy_columns: tuple[str, ...],
) -> tuple[dict[str, object], ...]:
    taxon_column, taxon_value = first_present(row, _TAXON_COLUMNS)
    seed_hash = hashes.get(("chembl_target", target_id or "")) or sha256_text(
        row.get("chembl.target.content_hash")
    )
    protein_hash = hashes.get(("uniprot_protein", accession or ""))
    chembl_ec = ec_column in _CHEMBL_EC_COLUMNS
    return (
        _origin(
            "ec",
            present=ec_column is not None,
            column=ec_column,
            pipeline="chembl_target" if chembl_ec else "uniprot_protein",
            source_hash=seed_hash if chembl_ec else protein_hash,
        ),
        *(
            _origin(
                "protein_hierarchy",
                present=column is not None,
                column=column,
                pipeline="chembl_target_protein_classification",
                source_hash=hashes.get(
                    ("chembl_target_protein_classification", target_id or "")
                ),
            )
            for column in hierarchy_columns or (None,)
        ),
        _origin(
            "keywords",
            present=bool(keyword_ids),
            column=keyword_column,
            pipeline="uniprot_protein",
            source_hash=protein_hash,
            status=keyword_status(keyword_value, keyword_ids),
        ),
        _origin(
            "uniprot_accession",
            present=accession is not None,
            column=accession_column,
            pipeline="uniprot_idmapping",
            source_hash=hashes.get(("uniprot_idmapping", target_id or "")),
        ),
        _origin(
            "taxon",
            present=taxon_value is not None,
            column=taxon_column,
            pipeline="chembl_target",
            source_hash=seed_hash,
        ),
    )


def _business(
    row: Mapping[str, object],
    *,
    target_id: str | None,
    accession: str | None,
    ec_value: object,
    keyword_ids: tuple[str, ...],
    hierarchy: list[dict[str, object]],
    release: str | None,
    release_status: str,
    origins: tuple[dict[str, object], ...],
) -> JsonDict:
    business: JsonDict = {}
    put_value(business, "target_id", target_id)
    put_value(business, "target_type", first_text(row, _TARGET_TYPE_COLUMNS)[1])
    put_value(business, "pref_name", first_text(row, _PREF_NAME_COLUMNS)[1])
    put_value(business, "taxonomy_id", first_present(row, _TAXON_COLUMNS)[1])
    put_value(business, "organism", first_text(row, _ORGANISM_COLUMNS)[1])
    put_value(
        business,
        "component_accessions",
        first_present(row, _ACCESSION_LIST_COLUMNS)[1],
    )
    put_value(business, "uniprot_accession", accession)
    put_value(business, "gene_symbol", first_text(row, _GENE_COLUMNS)[1])
    for name in (
        "target_protein_synonyms",
        "target_gene_synonyms",
        "target_xref_uniprot_ids",
    ):
        put_value(
            business, name, first_present(row, (f"chembl.target.{name}", name))[1]
        )
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
    return business


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
    if present and source_hash is not None:
        origin["source_content_hash"] = source_hash
    return origin
