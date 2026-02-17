"""Verify that committed Gold JSON contracts match generated schema output."""

from __future__ import annotations

import difflib
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any

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
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubChemCompoundGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)
from bioetl.domain.contracts.gold.composite import CompositePublicationGoldSchema

logger = logging.getLogger(__name__)

SCHEMA_FILE_MAP: dict[str, tuple[type[Any], str]] = {
    "chembl_activity_v1.0.json": (
        ChEMBLActivityGoldSchema,
        "ChEMBL Activity Gold Contract",
    ),
    "chembl_assay_v1.0.json": (ChEMBLAssayGoldSchema, "ChEMBL Assay Gold Contract"),
    "chembl_assay_parameters_v1.0.json": (
        ChEMBLAssayParametersGoldSchema,
        "ChEMBL Assay Parameters Gold Contract",
    ),
    "chembl_cell_line_v1.0.json": (
        ChEMBLCellLineGoldSchema,
        "ChEMBL Cell Line Gold Contract",
    ),
    "chembl_compound_record_v1.0.json": (
        ChEMBLCompoundRecordGoldSchema,
        "ChEMBL Compound Record Gold Contract",
    ),
    "chembl_document_v1.0.json": (
        ChEMBLDocumentGoldSchema,
        "ChEMBL Document Gold Contract",
    ),
    "chembl_document_similarity_v1.0.json": (
        ChEMBLDocumentSimilarityGoldSchema,
        "ChEMBL Document Similarity Gold Contract",
    ),
    "chembl_document_term_v1.0.json": (
        ChEMBLDocumentTermGoldSchema,
        "ChEMBL Document Term Gold Contract",
    ),
    "chembl_molecule_v1.0.json": (
        ChEMBLMoleculeGoldSchema,
        "ChEMBL Molecule Gold Contract",
    ),
    "chembl_protein_class_v1.0.json": (
        ChEMBLProteinClassGoldSchema,
        "ChEMBL Protein Class Gold Contract",
    ),
    "chembl_target_component_v1.0.json": (
        ChEMBLTargetComponentGoldSchema,
        "ChEMBL Target Component Gold Contract",
    ),
    "chembl_target_v1.0.json": (ChEMBLTargetGoldSchema, "ChEMBL Target Gold Contract"),
    "composite_publication_v1.0.json": (
        CompositePublicationGoldSchema,
        "Composite Publication Gold Contract",
    ),
    "crossref_publication_v1.0.json": (
        CrossRefPublicationGoldSchema,
        "CrossRef Publication Gold Contract",
    ),
    "openalex_publication_v1.0.json": (
        OpenAlexPublicationGoldSchema,
        "OpenAlex Publication Gold Contract",
    ),
    "pubchem_compound_v1.0.json": (
        PubChemCompoundGoldSchema,
        "PubChem Compound Gold Contract",
    ),
    "pubmed_publication_v1.0.json": (
        PubMedPublicationGoldSchema,
        "PubMed Publication Gold Contract",
    ),
    "semanticscholar_publication_v1.0.json": (
        SemanticScholarPublicationGoldSchema,
        "Semantic Scholar Publication Gold Contract",
    ),
    "uniprot_idmapping_v1.0.json": (
        UniProtIDMappingGoldSchema,
        "UniProt ID Mapping Gold Contract",
    ),
    "uniprot_protein_v1.0.json": (
        UniProtProteinGoldSchema,
        "UniProt Protein Gold Contract",
    ),
}


def _canonical_dump(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _to_json_type(dtype: Any, nullable: bool) -> str | list[str]:
    dtype_name = str(dtype).lower()
    if "int" in dtype_name:
        base_type = "integer"
    elif "float" in dtype_name or "double" in dtype_name or "decimal" in dtype_name:
        base_type = "number"
    elif "bool" in dtype_name:
        base_type = "boolean"
    else:
        base_type = "string"
    return [base_type, "null"] if nullable else base_type


def _build_contract(schema_cls: type[Any], title: str) -> dict[str, Any]:
    schema = schema_cls.to_schema()
    properties: dict[str, dict[str, str | list[str]]] = {}
    required: list[str] = []

    for field_name, column in schema.columns.items():
        properties[field_name] = {"type": _to_json_type(column.dtype, column.nullable)}
        if not column.nullable:
            required.append(field_name)

    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$version": "1.0.0",
        "title": title,
        "description": (
            f"Gold layer data contract for {title}. "
            f"Auto-generated from Pandera schema {schema_cls.__name__}."
        ),
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _generate_expected_contracts(output_dir: Path) -> None:
    for file_name, (schema_cls, title) in SCHEMA_FILE_MAP.items():
        output_file = output_dir / file_name
        output_file.write_text(
            _canonical_dump(_build_contract(schema_cls, title)), encoding="utf-8"
        )


def _json_files(path: Path) -> set[str]:
    return {file.name for file in path.glob("*.json") if file.is_file()}


def _read_normalized_json(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _canonical_dump(payload)


def verify_schema_parity() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    committed_dir = repo_root / "docs/04-reference/contracts/gold"

    if not committed_dir.exists():
        logger.error("Committed contracts directory not found: %s", committed_dir)
        return 1

    with tempfile.TemporaryDirectory(prefix="gold-contracts-") as tmp_dir_str:
        generated_dir = Path(tmp_dir_str)
        _generate_expected_contracts(generated_dir)

        committed_files = _json_files(committed_dir)
        generated_files = _json_files(generated_dir)

        missing_in_committed = sorted(generated_files - committed_files)
        unexpected_in_committed = sorted(committed_files - generated_files)

        has_diff = False

        if missing_in_committed:
            has_diff = True
            logger.error(
                "Missing committed contracts: %s", ", ".join(missing_in_committed)
            )

        if unexpected_in_committed:
            has_diff = True
            logger.error(
                "Unexpected committed contracts (not generated): %s",
                ", ".join(unexpected_in_committed),
            )

        for file_name in sorted(generated_files & committed_files):
            generated_text = _read_normalized_json(generated_dir / file_name)
            committed_text = _read_normalized_json(committed_dir / file_name)

            if generated_text == committed_text:
                continue

            has_diff = True
            logger.error("Contract drift detected: %s", file_name)
            diff_lines = difflib.unified_diff(
                committed_text.splitlines(),
                generated_text.splitlines(),
                fromfile=f"committed/{file_name}",
                tofile=f"generated/{file_name}",
                lineterm="",
            )
            for line in diff_lines:
                logger.error(line)

        if has_diff:
            logger.error("Schema parity verification failed.")
            return 1

        logger.info("Schema parity verification passed.")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(verify_schema_parity())
