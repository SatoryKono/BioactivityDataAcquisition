"""ChEMBL Assay Transformer.

Transforms Bronze records to Silver format (Assay entity inflation).
Uses declarative field_specs DSL for mapping where applicable.
"""

from __future__ import annotations

from bioetl.domain.types import GoldRecord, JsonDict

__all__ = ["AssayTransformer"]


from typing import TYPE_CHECKING, cast

from bioetl.application.core.dict_transformers import flatten_nested_dict
from bioetl.application.core.field_specs import (
    FieldGroup,
    FieldSpec,
    int_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Assay
from bioetl.domain.transformations import (
    safe_float,
    safe_str,
)
from bioetl.domain.value_objects.taxonomy_id import validate_taxonomy_id

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_context import PipelineContext
    from bioetl.domain.types import BronzeRecord, PrimaryId

# Mapping for variant sequence fields extraction (from ChEMBL nested structure)
# Source field is 'tax_id' from API, will be renamed to 'taxonomy_id' via renames
_VARIANT_FIELDS: JsonDict = {  # Any: transformer record has heterogeneous values
    "accession": safe_str,
    "isoform": safe_str,
    "mutation": safe_str,
    "organism": safe_str,
    "sequence": safe_str,
    "tax_id": validate_taxonomy_id,  # Will be renamed to taxonomy_id
}

# Rename mapping for variant fields (tax_id -> taxonomy_id for NCBI consistency)
_VARIANT_RENAMES: dict[str, str] = {
    "variant_tax_id": "variant_taxonomy_id",
}


def _extract_variant(
    data: JsonDict | None,  # Any: transformer record has heterogeneous values
) -> JsonDict:  # Any: transformer record has heterogeneous values
    """Extract variant sequence fields using flatten_nested_dict.

    Args:
        data: Nested variant_sequence dictionary from ChEMBL API.
            Expected structure: {"accession": "P12345", "mutation": "V600E", ...}

    Returns:
        Flattened dictionary with variant_ prefixed keys.
        tax_id is renamed to taxonomy_id for NCBI consistency.

    """
    return flatten_nested_dict(
        data, "variant_", _VARIANT_FIELDS, renames=_VARIANT_RENAMES
    )


# ============================================================================
# Declarative field groups for Assay entity
# ============================================================================

_IDENTIFIERS = FieldGroup(
    name="identifiers",
    fields=(
        FieldSpec("target_chembl_id", target="target_id"),
        FieldSpec("document_chembl_id", target="publication_id"),
        FieldSpec("cell_chembl_id", target="cell_id"),
        FieldSpec("tissue_chembl_id", target="tissue_id"),
        *simple_fields(
            "src_assay_id",
            "aidx",
        ),
        *int_fields("src_id"),
    ),
)

_CLASSIFICATION = FieldGroup(
    name="classification",
    fields=simple_fields(
        "assay_type",
        "assay_type_description",
        "assay_category",
        "assay_test_type",
        "assay_group",
    ),
)

_BIOLOGICAL_CONTEXT = FieldGroup(
    name="biological_context",
    fields=(
        *simple_fields(
            "assay_organism",
            "assay_cell_type",
            "assay_tissue",
            "assay_strain",
            "assay_subcellular_fraction",
            "bao_format",
            "bao_label",
        ),
        # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
        FieldSpec(
            "assay_tax_id", target="assay_taxonomy_id", converter=validate_taxonomy_id
        ),
    ),
)

_METADATA = FieldGroup(
    name="metadata",
    fields=(
        FieldSpec("description", target="assay_description"),
        *simple_fields(
            "confidence_description",
            "relationship_type",
            "relationship_description",
            "assay_pref_name",
        ),
        *int_fields("confidence_score"),
        FieldSpec("score", converter=safe_float),
    ),
)

# All declarative field groups
_ASSAY_GROUPS: tuple[FieldGroup, ...] = (
    _IDENTIFIERS,
    _CLASSIFICATION,
    _BIOLOGICAL_CONTEXT,
    _METADATA,
)


class AssayTransformer(BaseChemblTransformer):
    """Transforms ChEMBL assay bronze records to silver."""

    entity_class = Assay
    primary_id_field = "assay_id"

    def _prepare_record(
        self,
        record: BronzeRecord,
    ) -> BronzeRecord:
        """Support both unified and legacy assay identifier field names."""
        if "assay_id" not in record and record.get("assay_chembl_id") is not None:
            record = dict(record)
            record["assay_id"] = record.get("assay_chembl_id")
        return record

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> JsonDict:  # Any: transformer record has heterogeneous values
        """Extract Assay business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated assay_id value.

        Returns:
            Dictionary of Assay business fields.

        """
        business_data = {
            # Primary identifier
            "assay_id": str(primary_id),
            # Declarative field groups
            **map_field_groups(record, _ASSAY_GROUPS),
            "assay_subcellular_fraction_raw": record.get("assay_subcellular_fraction"),
            "bao_format_iri": None,
            "bao_format_mapping_status": None,
            "bao_ontology_version": None,
            # Nested dict extraction (variant)
            **_extract_variant(
                cast(
                    "JsonDict | None",  # Any: transformer record has heterogeneous values
                    record.get(
                        "variant_sequence"
                    ),  # Any: transformer record has heterogeneous values
                )  # Any: transformer record has heterogeneous values
            ),
            # JSON serialization
            "variant_sequence_json": self.serialize_json(
                record.get("variant_sequence")
            ),
            "assay_classifications": self.serialize_json(
                record.get("assay_classifications")
            ),
            "assay_parameters": self.serialize_json(record.get("assay_parameters")),
        }
        # Support both unified and legacy FK source fields.
        business_data["target_id"] = business_data.get("target_id") or record.get(
            "target_id"
        )
        business_data["publication_id"] = business_data.get(
            "publication_id"
        ) or record.get("publication_id")
        business_data["cell_id"] = business_data.get("cell_id") or record.get("cell_id")
        business_data["tissue_id"] = business_data.get("tissue_id") or record.get(
            "tissue_id"
        )
        return business_data

    def _postprocess_pre_silver_record(
        self,
        silver_record: JsonDict,
        *,
        business_data: JsonDict,
    ) -> JsonDict:
        """Project legacy ChEMBL input aliases to the canonical Silver assay shape."""
        description = silver_record.get("assay_description")
        if description is None:
            description = silver_record.pop("description", None)
        if description is None:
            description = business_data.get("assay_description")
        if description is None:
            description = business_data.get("description")
        silver_record.pop("description", None)
        silver_record["assay_description"] = description
        return silver_record

    def transform_for_gold(
        self,
        context: PipelineContext,
        silver_record: GoldRecord,
    ) -> GoldRecord:
        """Re-project canonical Silver assay fields to the legacy Gold contract."""
        gold_record = super().transform_for_gold(context, silver_record)
        gold_record["description"] = gold_record.pop("assay_description", None)
        return gold_record
