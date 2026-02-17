#!/usr/bin/env python3
"""Generate versioned JSON Schema contracts from Gold Pandera models."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.domain.contracts.gold import (
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
    CompositePublicationGoldSchema,
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubChemCompoundGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "04-reference" / "contracts" / "gold"

ENTITY_SCHEMA_MAP = {
    "chembl_activity_v1.0": ChEMBLActivityGoldSchema,
    "chembl_assay_v1.0": ChEMBLAssayGoldSchema,
    "chembl_assay_parameters_v1.0": ChEMBLAssayParametersGoldSchema,
    "chembl_cell_line_v1.0": ChEMBLCellLineGoldSchema,
    "chembl_compound_record_v1.0": ChEMBLCompoundRecordGoldSchema,
    "chembl_document_v1.0": ChEMBLDocumentGoldSchema,
    "chembl_document_similarity_v1.0": ChEMBLDocumentSimilarityGoldSchema,
    "chembl_document_term_v1.0": ChEMBLDocumentTermGoldSchema,
    "chembl_molecule_v1.0": ChEMBLMoleculeGoldSchema,
    "chembl_protein_class_v1.0": ChEMBLProteinClassGoldSchema,
    "chembl_target_v1.0": ChEMBLTargetGoldSchema,
    "chembl_target_component_v1.0": ChEMBLTargetComponentGoldSchema,
    "chembl_tissue_v1.0": ChEMBLTissueGoldSchema,
    "chembl_subcellular_fraction_v1.0": ChEMBLSubcellularFractionGoldSchema,
    "pubchem_compound_v1.0": PubChemCompoundGoldSchema,
    "pubmed_publication_v1.0": PubMedPublicationGoldSchema,
    "crossref_publication_v1.0": CrossRefPublicationGoldSchema,
    "openalex_publication_v1.0": OpenAlexPublicationGoldSchema,
    "semanticscholar_publication_v1.0": SemanticScholarPublicationGoldSchema,
    "uniprot_protein_v1.0": UniProtProteinGoldSchema,
    "uniprot_idmapping_v1.0": UniProtIDMappingGoldSchema,
    "composite_publication_v1.0": CompositePublicationGoldSchema,
}


def generate_contracts() -> None:
    """Render all Gold contracts as JSON Schema files in docs."""
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

    for entity, schema_cls in sorted(ENTITY_SCHEMA_MAP.items()):
        output_file = CONTRACTS_DIR / f"{entity}.json"
        json_schema = schema_cls.to_json_schema()
        with output_file.open("w", encoding="utf-8") as file_obj:
            json.dump(json_schema, file_obj, indent=2, ensure_ascii=False)
            file_obj.write("\n")
        print(f"Generated: {output_file.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    generate_contracts()
