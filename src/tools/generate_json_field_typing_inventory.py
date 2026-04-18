"""Generate JSON field typing inventory (Bronze -> Silver -> Gold)."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bioetl.domain.contracts import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLAssayParametersGoldSchema,
    ChEMBLCellLineGoldSchema,
    ChEMBLCompoundRecordGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLProteinClassGoldSchema,
    ChEMBLPublicationGoldSchema,
    ChEMBLPublicationSimilarityGoldSchema,
    ChEMBLPublicationTermGoldSchema,
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
from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.assay_parameters import AssayParametersSchema
from bioetl.domain.schemas.chembl.cell_line import CellLineSchema
from bioetl.domain.schemas.chembl.compound_record import CompoundRecordSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema
from bioetl.domain.schemas.chembl.protein_classification import (
    ProteinClassificationSchema,
)
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema
from bioetl.domain.schemas.chembl.publication_similarity import (
    PublicationSimilaritySchema,
)
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.target_component import TargetComponentSchema
from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema
from bioetl.domain.schemas.pubchem.compound import PubchemMoleculeSchema
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema
from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
)
from bioetl.domain.schemas.uniprot.idmapping import IDMappingSchema
from bioetl.domain.schemas.uniprot.protein import UniprotTargetSchema
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
    CHEMBL_TARGET_COMPONENT_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
    CROSSREF_PUBLICATION_SCHEMA,
    OPENALEX_PUBLICATION_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
    UNIPROT_ID_MAPPING_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "docs/03-data-model/json-field-typing-inventory.md"
_PUBLICATION_INPUT_CSV = "data/input/publication.csv"


@dataclass(frozen=True)
class SchemaBundle:
    """Bundle all layers for a pipeline schema."""

    name: str
    pandera_silver: type
    pyarrow_silver: Any
    gold_contract: type
    bronze_csv: str | None


SCHEMA_BUNDLES: tuple[SchemaBundle, ...] = (
    SchemaBundle(
        "chembl_activity",
        ActivitySchema,
        CHEMBL_ACTIVITY_SCHEMA,
        ChEMBLActivityGoldSchema,
        "data/input/activity.csv",
    ),
    SchemaBundle(
        "chembl_assay",
        AssaySchema,
        CHEMBL_ASSAY_SCHEMA,
        ChEMBLAssayGoldSchema,
        "data/input/assay.csv",
    ),
    SchemaBundle(
        "chembl_assay_parameters",
        AssayParametersSchema,
        CHEMBL_ASSAY_PARAMETERS_SCHEMA,
        ChEMBLAssayParametersGoldSchema,
        None,
    ),
    SchemaBundle(
        "chembl_cell_line",
        CellLineSchema,
        CHEMBL_CELL_LINE_SCHEMA,
        ChEMBLCellLineGoldSchema,
        "data/input/cell.csv",
    ),
    SchemaBundle(
        "chembl_compound_record",
        CompoundRecordSchema,
        CHEMBL_COMPOUND_RECORD_SCHEMA,
        ChEMBLCompoundRecordGoldSchema,
        "data/input/compound_record.csv",
    ),
    SchemaBundle(
        "chembl_document",
        ChemblPublicationSchema,
        CHEMBL_PUBLICATION_SCHEMA,
        ChEMBLPublicationGoldSchema,
        _PUBLICATION_INPUT_CSV,
    ),
    SchemaBundle(
        "chembl_document_similarity",
        PublicationSimilaritySchema,
        CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
        ChEMBLPublicationSimilarityGoldSchema,
        None,
    ),
    SchemaBundle(
        "chembl_document_term",
        PublicationTermSchema,
        CHEMBL_DOCUMENT_TERM_SCHEMA,
        ChEMBLPublicationTermGoldSchema,
        None,
    ),
    SchemaBundle(
        "chembl_molecule",
        MoleculeSchema,
        CHEMBL_MOLECULE_SCHEMA,
        ChEMBLMoleculeGoldSchema,
        "data/input/molecule.csv",
    ),
    SchemaBundle(
        "chembl_protein_class",
        ProteinClassificationSchema,
        CHEMBL_PROTEIN_CLASS_SCHEMA,
        ChEMBLProteinClassGoldSchema,
        "data/input/protein_classification.csv",
    ),
    SchemaBundle(
        "chembl_target",
        TargetSchema,
        CHEMBL_TARGET_SCHEMA,
        ChEMBLTargetGoldSchema,
        "data/input/target.csv",
    ),
    SchemaBundle(
        "chembl_target_component",
        TargetComponentSchema,
        CHEMBL_TARGET_COMPONENT_SCHEMA,
        ChEMBLTargetComponentGoldSchema,
        "data/input/target_component.csv",
    ),
    SchemaBundle(
        "pubchem_compound",
        PubchemMoleculeSchema,
        PUBCHEM_COMPOUND_SCHEMA,
        PubChemCompoundGoldSchema,
        None,
    ),
    SchemaBundle(
        "pubmed_publication",
        PubMedPublicationSchema,
        PUBMED_PUBLICATION_SCHEMA,
        PubMedPublicationGoldSchema,
        "data/input/pubmed.csv",
    ),
    SchemaBundle(
        "crossref_publication",
        PublicationEnrichedSchema,
        CROSSREF_PUBLICATION_SCHEMA,
        CrossRefPublicationGoldSchema,
        "data/input/dois.csv",
    ),
    SchemaBundle(
        "openalex_publication",
        OpenAlexPublicationSchema,
        OPENALEX_PUBLICATION_SCHEMA,
        OpenAlexPublicationGoldSchema,
        _PUBLICATION_INPUT_CSV,
    ),
    SchemaBundle(
        "semanticscholar_publication",
        SemanticScholarPublicationSchema,
        SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
        SemanticScholarPublicationGoldSchema,
        _PUBLICATION_INPUT_CSV,
    ),
    SchemaBundle(
        "uniprot_protein",
        UniprotTargetSchema,
        UNIPROT_PROTEIN_SCHEMA,
        UniProtProteinGoldSchema,
        "data/input/protein.csv",
    ),
    SchemaBundle(
        "uniprot_idmapping",
        IDMappingSchema,
        UNIPROT_ID_MAPPING_SCHEMA,
        UniProtIDMappingGoldSchema,
        None,
    ),
)


def _infer_scalar_type(raw: str) -> str:
    text = raw.strip()
    if not text:
        return "null"
    if text.lower() in {"true", "false"}:
        return "boolean"
    if text.startswith("["):
        return "array"
    if text.startswith("{"):
        return "object"
    try:
        int(text)
        return "integer"
    except ValueError:
        pass
    try:
        float(text)
        return "float"
    except ValueError:
        return "string"


def _kind(dtype: str) -> str:
    value = dtype.lower()
    if "list" in value or "array" in value:
        return "native_list"
    if "object" in value or "dict" in value:
        return "native_object"
    if "str" in value or "string" in value:
        return "canonical_string"
    return "scalar"


def _fmt(dtype: str, nullable: bool | None) -> str:
    if not dtype:
        return "—"
    if nullable is None:
        return f"`{dtype}`"
    nullable_text = "nullable" if nullable else "not-null"
    return f"`{dtype}` ({nullable_text})"


def _collect_bronze_type_hints() -> tuple[dict[str, set[str]], dict[str, bool]]:
    """Infer Bronze CSV scalar types across all available sample files."""
    bronze_types: dict[str, set[str]] = defaultdict(set)
    bronze_nullable: dict[str, bool] = defaultdict(bool)

    for bundle in SCHEMA_BUNDLES:
        if bundle.bronze_csv is None:
            continue
        csv_path = PROJECT_ROOT / bundle.bronze_csv
        if not csv_path.exists():
            continue
        with csv_path.open(encoding="utf-8", newline="") as file_obj:
            reader = csv.DictReader(file_obj)
            for row in reader:
                for field, value in row.items():
                    inferred = _infer_scalar_type(value or "")
                    bronze_types[field].add(inferred)
                    if inferred == "null":
                        bronze_nullable[field] = True
    return bronze_types, bronze_nullable


def _build_inventory_row(
    *,
    field_name: str,
    pandera_columns: dict[str, Any],
    pyarrow_fields: dict[str, Any],
    gold_columns: dict[str, Any],
    bronze_types: dict[str, set[str]],
    bronze_nullable: dict[str, bool],
) -> tuple[str, str, str, str] | None:
    """Build one formatted markdown row for JSON-like fields."""
    pandera_dtype = (
        str(pandera_columns[field_name].dtype) if field_name in pandera_columns else ""
    )
    pyarrow_dtype = (
        str(pyarrow_fields[field_name].type) if field_name in pyarrow_fields else ""
    )
    gold_dtype = (
        str(gold_columns[field_name].dtype) if field_name in gold_columns else ""
    )

    kinds = {_kind(pandera_dtype), _kind(pyarrow_dtype), _kind(gold_dtype)}
    if not kinds.intersection({"canonical_string", "native_list", "native_object"}):
        return None

    bronze_type = "|".join(sorted(bronze_types.get(field_name, {"unknown"})))
    return (
        _fmt(bronze_type, bronze_nullable.get(field_name, True)),
        _fmt(
            pandera_dtype,
            pandera_columns[field_name].nullable
            if field_name in pandera_columns
            else None,
        ),
        _fmt(
            pyarrow_dtype,
            pyarrow_fields[field_name].nullable
            if field_name in pyarrow_fields
            else None,
        ),
        _fmt(
            gold_dtype,
            gold_columns[field_name].nullable if field_name in gold_columns else None,
        ),
    )


def build_inventory() -> str:
    bronze_types, bronze_nullable = _collect_bronze_type_hints()

    rows: dict[str, tuple[str, str, str, str]] = {}
    for bundle in SCHEMA_BUNDLES:
        pandera_columns = bundle.pandera_silver.to_schema().columns
        pyarrow_fields = {field.name: field for field in bundle.pyarrow_silver}
        gold_columns = bundle.gold_contract.to_schema().columns

        field_names = set(pandera_columns) | set(pyarrow_fields) | set(gold_columns)
        for field_name in sorted(field_names):
            row = _build_inventory_row(
                field_name=field_name,
                pandera_columns=pandera_columns,
                pyarrow_fields=pyarrow_fields,
                gold_columns=gold_columns,
                bronze_types=bronze_types,
                bronze_nullable=bronze_nullable,
            )
            if row is None:
                continue
            rows[field_name] = row

    lines = [
        "# JSON Field Typing Inventory (Bronze -> Silver -> Gold)",
        "",
        "Scope: inferred Bronze CSV samples + Silver Pandera + Silver PyArrow + Gold contracts.",
        "",
        "| Field | Bronze inferred | Silver Pandera | Silver PyArrow | Gold contract |",
        "| --- | --- | --- | --- | --- |",
    ]

    for field_name in sorted(rows):
        bronze, pandera, pyarrow, gold = rows[field_name]
        lines.append(f"| `{field_name}` | {bronze} | {pandera} | {pyarrow} | {gold} |")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    content = build_inventory()
    args.output.write_text(content, encoding="utf-8")
    print(f"Updated {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
