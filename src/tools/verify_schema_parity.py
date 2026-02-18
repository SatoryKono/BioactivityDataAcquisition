"""Verify Silver↔Gold schema parity and primary key coverage."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import yaml

from bioetl.domain.contracts import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLAssayParametersGoldSchema,
    ChEMBLCellLineGoldSchema,
    ChEMBLCompoundRecordGoldSchema,
    ChEMBLDocumentGoldSchema,
    ChEMBLDocumentSimilarityGoldSchema,
    ChEMBLDocumentTermGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLProteinClassGoldSchema,
    ChEMBLSubcellularFractionGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
    ChEMBLTissueGoldSchema,
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubChemCompoundGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)
from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    CHEMBL_ASSAY_PARAMETERS_SCHEMA,
    CHEMBL_ASSAY_SCHEMA,
    CHEMBL_CELL_LINE_SCHEMA,
    CHEMBL_COMPOUND_RECORD_SCHEMA,
    CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
    CHEMBL_DOCUMENT_TERM_SCHEMA,
    CHEMBL_MOLECULE_SCHEMA,
    CHEMBL_PROTEIN_CLASS_SCHEMA,
    CHEMBL_PUBLICATION_SCHEMA,
    CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
    CHEMBL_TARGET_COMPONENT_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
    CHEMBL_TISSUE_SCHEMA,
    CROSSREF_PUBLICATION_SCHEMA,
    OPENALEX_PUBLICATION_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
    UNIPROT_ID_MAPPING_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SchemaPair:
    """Silver/Gold schema pair with pipeline config for PK loading."""

    name: str
    silver_schema: object
    gold_model: type
    config_path: str


SCHEMA_PAIRS: tuple[SchemaPair, ...] = (
    SchemaPair(
        "chembl_activity",
        CHEMBL_ACTIVITY_SCHEMA,
        ChEMBLActivityGoldSchema,
        "configs/pipelines/chembl/activity.yaml",
    ),
    SchemaPair(
        "chembl_assay",
        CHEMBL_ASSAY_SCHEMA,
        ChEMBLAssayGoldSchema,
        "configs/pipelines/chembl/assay.yaml",
    ),
    SchemaPair(
        "chembl_assay_parameters",
        CHEMBL_ASSAY_PARAMETERS_SCHEMA,
        ChEMBLAssayParametersGoldSchema,
        "configs/pipelines/chembl/assay_parameters.yaml",
    ),
    SchemaPair(
        "chembl_cell_line",
        CHEMBL_CELL_LINE_SCHEMA,
        ChEMBLCellLineGoldSchema,
        "configs/pipelines/chembl/cell_line.yaml",
    ),
    SchemaPair(
        "chembl_compound_record",
        CHEMBL_COMPOUND_RECORD_SCHEMA,
        ChEMBLCompoundRecordGoldSchema,
        "configs/pipelines/chembl/compound_record.yaml",
    ),
    SchemaPair(
        "chembl_document",
        CHEMBL_PUBLICATION_SCHEMA,
        ChEMBLDocumentGoldSchema,
        "configs/pipelines/chembl/publication.yaml",
    ),
    SchemaPair(
        "chembl_document_similarity",
        CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
        ChEMBLDocumentSimilarityGoldSchema,
        "configs/pipelines/chembl/publication_similarity.yaml",
    ),
    SchemaPair(
        "chembl_document_term",
        CHEMBL_DOCUMENT_TERM_SCHEMA,
        ChEMBLDocumentTermGoldSchema,
        "configs/pipelines/chembl/publication_term.yaml",
    ),
    SchemaPair(
        "chembl_molecule",
        CHEMBL_MOLECULE_SCHEMA,
        ChEMBLMoleculeGoldSchema,
        "configs/pipelines/chembl/molecule.yaml",
    ),
    SchemaPair(
        "chembl_protein_class",
        CHEMBL_PROTEIN_CLASS_SCHEMA,
        ChEMBLProteinClassGoldSchema,
        "configs/pipelines/chembl/protein_class.yaml",
    ),
    SchemaPair(
        "chembl_target",
        CHEMBL_TARGET_SCHEMA,
        ChEMBLTargetGoldSchema,
        "configs/pipelines/chembl/target.yaml",
    ),
    SchemaPair(
        "chembl_target_component",
        CHEMBL_TARGET_COMPONENT_SCHEMA,
        ChEMBLTargetComponentGoldSchema,
        "configs/pipelines/chembl/target_component.yaml",
    ),
    SchemaPair(
        "chembl_tissue",
        CHEMBL_TISSUE_SCHEMA,
        ChEMBLTissueGoldSchema,
        "configs/pipelines/chembl/tissue.yaml",
    ),
    SchemaPair(
        "chembl_subcellular_fraction",
        CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
        ChEMBLSubcellularFractionGoldSchema,
        "configs/pipelines/chembl/subcellular_fraction.yaml",
    ),
    SchemaPair(
        "pubchem_compound",
        PUBCHEM_COMPOUND_SCHEMA,
        PubChemCompoundGoldSchema,
        "configs/pipelines/pubchem/compound.yaml",
    ),
    SchemaPair(
        "pubmed_publication",
        PUBMED_PUBLICATION_SCHEMA,
        PubMedPublicationGoldSchema,
        "configs/pipelines/pubmed/publication.yaml",
    ),
    SchemaPair(
        "crossref_publication",
        CROSSREF_PUBLICATION_SCHEMA,
        CrossRefPublicationGoldSchema,
        "configs/pipelines/crossref/publication.yaml",
    ),
    SchemaPair(
        "openalex_publication",
        OPENALEX_PUBLICATION_SCHEMA,
        OpenAlexPublicationGoldSchema,
        "configs/pipelines/openalex/publication.yaml",
    ),
    SchemaPair(
        "semanticscholar_publication",
        SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
        SemanticScholarPublicationGoldSchema,
        "configs/pipelines/semanticscholar/publication.yaml",
    ),
    SchemaPair(
        "uniprot_protein",
        UNIPROT_PROTEIN_SCHEMA,
        UniProtProteinGoldSchema,
        "configs/pipelines/uniprot/protein.yaml",
    ),
    SchemaPair(
        "uniprot_idmapping",
        UNIPROT_ID_MAPPING_SCHEMA,
        UniProtIDMappingGoldSchema,
        "configs/pipelines/uniprot/idmapping.yaml",
    ),
)


def get_primary_keys(config_path: str) -> list[str]:
    """Load primary_keys from pipeline config."""
    absolute_path = PROJECT_ROOT / config_path
    with absolute_path.open(encoding="utf-8") as file_obj:
        config = yaml.safe_load(file_obj) or {}
    primary_keys = config.get("primary_keys", [])
    if not isinstance(primary_keys, list):
        raise TypeError(f"primary_keys must be list in {config_path}")
    return primary_keys


def check_schema_pair(pair: SchemaPair) -> tuple[list[str], list[str]]:
    """Return (blocking_errors, warning_errors) for one schema pair."""
    blocking: list[str] = []
    warnings: list[str] = []

    silver_fields = {field.name: field for field in pair.silver_schema}
    gold_columns = pair.gold_model.to_schema().columns

    missing_in_gold = sorted(set(silver_fields) - set(gold_columns))
    missing_in_silver = sorted(set(gold_columns) - set(silver_fields))

    if missing_in_gold:
        blocking.append(
            f"{pair.name}: fields present in Silver but missing in Gold: {missing_in_gold}"
        )
    if missing_in_silver:
        blocking.append(
            f"{pair.name}: fields present in Gold but missing in Silver: {missing_in_silver}"
        )

    primary_keys = get_primary_keys(pair.config_path)
    if not primary_keys:
        warnings.append(f"{pair.name}: no primary_keys declared in {pair.config_path}")

    for primary_key in primary_keys:
        if primary_key not in silver_fields:
            blocking.append(
                f"{pair.name}: PK '{primary_key}' missing in Silver schema ({pair.config_path})"
            )
            continue

        if primary_key not in gold_columns:
            blocking.append(
                f"{pair.name}: PK '{primary_key}' missing in Gold schema ({pair.config_path})"
            )
            continue

        if silver_fields[primary_key].nullable:
            warnings.append(
                f"{pair.name}: PK '{primary_key}' is nullable in Silver schema"
            )

        if gold_columns[primary_key].nullable:
            warnings.append(
                f"{pair.name}: PK '{primary_key}' is nullable in Gold schema"
            )

        if silver_fields[primary_key].nullable != gold_columns[primary_key].nullable:
            blocking.append(
                f"{pair.name}: PK '{primary_key}' nullable mismatch "
                f"(Silver={silver_fields[primary_key].nullable}, "
                f"Gold={gold_columns[primary_key].nullable})"
            )

    return blocking, warnings


def main() -> int:
    """Run parity checks and return process exit code."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["all", "blocking", "warnings"],
        default="all",
        help="Which checks should affect process exit code.",
    )
    args = parser.parse_args()

    blocking_errors: list[str] = []
    warning_errors: list[str] = []

    for pair in SCHEMA_PAIRS:
        blocking, warnings = check_schema_pair(pair)
        blocking_errors.extend(blocking)
        warning_errors.extend(warnings)

    print("\n=== Blocking checks (Silver↔Gold parity, PK coverage) ===")
    if blocking_errors:
        for error in blocking_errors:
            print(f"[FAIL] {error}")
    else:
        print("[OK] No blocking schema parity issues.")

    print("\n=== Warning checks (non-blocking quality signals) ===")
    if warning_errors:
        for warning in warning_errors:
            print(f"[WARN] {warning}")
    else:
        print("[OK] No schema warnings.")

    if args.mode == "blocking":
        return 1 if blocking_errors else 0
    if args.mode == "warnings":
        return 1 if warning_errors else 0
    return 1 if blocking_errors or warning_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
