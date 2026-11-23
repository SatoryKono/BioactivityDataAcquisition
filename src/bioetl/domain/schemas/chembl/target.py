"""Pandera schema for ChEMBL Target entity.

Aligned with RULES.md v5.24 and ChEMBL 34 schema.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.normalization.target_classification_values import (
    detail_is_canonical,
)
from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import (
    CHEMBL_ID_PATTERN,
    TARGET_ORGANISM_CLASSES,
    TARGET_TYPES,
)

__all__ = [
    "TargetSchema",
    "TargetSchemaV31",
    "TargetSchemaV32",
    "build_target_classification_detail_model",
    "register_canonical_classification_detail",
]


class TargetSchema(ETLRecordSchema):
    """Target validation schema for Silver layer."""

    # === Primary Key ===
    # tid: Series[int] = pa.Field(
    #     nullable=False, description="Primary key."
    # )
    # Removed tid as it is not in Silver schema. target_id is the PK.

    # === Identifiers ===
    target_id: Series[str] = pa.Field(
        nullable=False,
        unique=True,
        str_matches=CHEMBL_ID_PATTERN,
        description="ChEMBL ID.",
    )

    # === Classification ===
    target_type: Series[str] = pa.Field(
        nullable=False,
        isin=list(TARGET_TYPES),
        description="Target type.",
    )
    # target_parent_type: Optional[Series[str]] = pa.Field(
    #     nullable=True,
    #     isin=["MOLECULAR", "NON-MOLECULAR", "PROTEIN", "UNDEFINED"],
    #     description="Target parent type.",
    # )

    # === Metadata ===
    pref_name: Series[str] = pa.Field(nullable=False, description="Preferred name.")
    taxonomy_id: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="NCBI Taxonomy ID."
    )
    organism: Series[str] = pa.Field(nullable=False, description="Organism.")
    organism_class: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(TARGET_ORGANISM_CLASSES),
        description="Organism cellularity classification.",
    )
    species_group_flag: Series[bool] = pa.Field(
        nullable=False,
        coerce=False,
        description="Species group flag.",
    )
    target_description: Series[str] | None = pa.Field(
        nullable=True, description="Target description."
    )

    target_protein_synonyms: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited UNIPROT-derived target synonyms or unknown.",
    )
    target_gene_synonyms: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited gene-symbol-derived target synonyms or unknown.",
    )
    target_ec_numbers: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited EC-number-derived target synonyms or unknown.",
    )
    target_xref_pdb_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited PDB/PDBe xref IDs or unknown.",
    )
    target_xref_go_component: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited GO cellular component xref names or unknown.",
    )
    target_xref_go_function: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited GO molecular function xref names or unknown.",
    )
    target_xref_go_process: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited GO biological process xref names or unknown.",
    )
    target_xref_hgnc_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited HGNC xref IDs or unknown.",
    )
    target_xref_reactome_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited Reactome xref IDs or unknown.",
    )
    target_xref_uniprot_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited UniProt xref IDs or unknown.",
    )

    # === Flattened Component Fields (JSON Arrays) ===
    primary_component_id: Series[float] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Primary component ID (first from list).",
    )
    protein_classifications: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON string of aggregated component protein classifications.",
    )
    target_protein_class_id_L1: Series[str] | None = pa.Field(
        nullable=True, description="L1 target protein class ID."
    )
    target_protein_class_name_L1: Series[str] | None = pa.Field(
        nullable=True, description="L1 target protein class name."
    )
    target_protein_class_desc_L1: Series[str] | None = pa.Field(
        nullable=True, description="L1 target protein class description."
    )
    target_protein_class_id_L2: Series[str] | None = pa.Field(
        nullable=True, description="L2 target protein class ID."
    )
    target_protein_class_name_L2: Series[str] | None = pa.Field(
        nullable=True, description="L2 target protein class name."
    )
    target_protein_class_desc_L2: Series[str] | None = pa.Field(
        nullable=True, description="L2 target protein class description."
    )
    target_protein_class_id_L3: Series[str] | None = pa.Field(
        nullable=True, description="L3 target protein class ID."
    )
    target_protein_class_name_L3: Series[str] | None = pa.Field(
        nullable=True, description="L3 target protein class name."
    )
    target_protein_class_desc_L3: Series[str] | None = pa.Field(
        nullable=True, description="L3 target protein class description."
    )
    target_protein_class_id_L4: Series[str] | None = pa.Field(
        nullable=True, description="L4 target protein class ID."
    )
    target_protein_class_name_L4: Series[str] | None = pa.Field(
        nullable=True, description="L4 target protein class name."
    )
    target_protein_class_desc_L4: Series[str] | None = pa.Field(
        nullable=True, description="L4 target protein class description."
    )
    target_protein_class_id_L5: Series[str] | None = pa.Field(
        nullable=True, description="L5 target protein class ID."
    )
    target_protein_class_name_L5: Series[str] | None = pa.Field(
        nullable=True, description="L5 target protein class name."
    )
    target_protein_class_desc_L5: Series[str] | None = pa.Field(
        nullable=True, description="L5 target protein class description."
    )
    component_accessions: Series[str] | None = pa.Field(
        nullable=True, description="Canonical JSON array of component accessions."
    )
    component_descriptions: Series[str] | None = pa.Field(
        nullable=True, description="Canonical JSON array of component descriptions."
    )
    component_ids: Series[str] | None = pa.Field(
        nullable=True, description="Canonical JSON array of component IDs."
    )
    component_types: Series[str] | None = pa.Field(
        nullable=True, description="Canonical JSON array of component types."
    )
    component_relationships: Series[str] | None = pa.Field(
        nullable=True, description="Canonical JSON array of component relationships."
    )

    # === Complex Fields (JSON Strings) ===
    target_components: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of target components."
    )
    cross_references: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of cross references."
    )
    target_component_synonyms: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of aggregated component synonyms."
    )

    class Config:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = False


class TargetSchemaV31(TargetSchema):
    """Add the complete nullable IUPHAR projection only for enrich runs."""

    iuphar_target_id: Series[str] = pa.Field(nullable=True)
    iuphar_class: Series[str] = pa.Field(nullable=True)
    iuphar_match_status: Series[str] = pa.Field(nullable=True)
    iuphar_annotation_status: Series[str] = pa.Field(nullable=True)
    local_class: Series[str] = pa.Field(nullable=True)
    effective_class: Series[str] = pa.Field(nullable=True)
    effective_source: Series[str] = pa.Field(nullable=True)
    decision_status: Series[str] = pa.Field(nullable=True)
    target_class_profile_sha256: Series[str] = pa.Field(
        nullable=True, str_matches=r"^[0-9a-f]{64}$"
    )


def register_canonical_classification_detail() -> None:
    """Register the 3.2.0 column check on the schema boundary, once."""
    if hasattr(pa.Check, "canonical_classification_detail"):
        return

    register = cast(
        Callable[[Callable[..., bool]], Callable[..., bool]],
        pa.extensions.register_check_method(
            statistics=["field_name"], check_type="element_wise"
        ),
    )

    @register
    def canonical_classification_detail(value: object, *, field_name: str) -> bool:
        return detail_is_canonical(field_name, value)


register_canonical_classification_detail()


def _detail_field(name: str, description: str) -> object:
    return pa.Field(
        nullable=True,
        description=description,
        canonical_classification_detail=name,
    )


_DETAIL_FIELD_SPECS: tuple[tuple[str, str], ...] = (
    ("iuphar_type_raw", "Raw IUPHAR source type. Null means not computed."),
    (
        "iuphar_source_completeness",
        "typed, family_only, source_unavailable or unannotated.",
    ),
    ("iuphar_family_ids", "Canonical JSON set of IUPHAR family ids."),
    ("iuphar_subclasses", "Canonical JSON set of IUPHAR subclasses."),
    ("iuphar_family_paths", "Canonical JSON set of {family_id, root_to_leaf}."),
    ("local_status", "Local-rule status. Null means not computed."),
    ("local_subclasses", "Canonical JSON set of local subclasses."),
    ("local_rule_ids", "Canonical JSON set of local rule ids."),
    ("effective_subclasses", "Canonical JSON set of effective subclasses."),
    ("conflict_codes", "Canonical JSON set of conflict codes."),
    ("classification_evidence_refs", "Canonical JSON struct of evidence id sets."),
)


def build_target_classification_detail_model(
    base: type[pa.DataFrameModel],
    name: str,
    doc: str,
    module: str,
) -> type[pa.DataFrameModel]:
    """Add the shared detail columns after the columns of ``base``."""
    annotations: dict[str, object] = {}
    namespace: dict[str, object] = {
        "__annotations__": annotations,
        "__module__": module,
        "__doc__": doc,
    }
    for field_name, description in _DETAIL_FIELD_SPECS:
        annotations[field_name] = Series[str]
        namespace[field_name] = _detail_field(field_name, description)
    model = type(name, (base,), namespace)
    if not issubclass(model, pa.DataFrameModel):
        raise TypeError("detail schema must be a Pandera model")
    return model


TargetSchemaV32 = build_target_classification_detail_model(
    TargetSchemaV31,
    "TargetSchemaV32",
    "Persist IUPHAR detail as canonical JSON strings. Null means not computed.",
    __name__,
)
