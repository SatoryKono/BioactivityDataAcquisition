"""ChEMBL Assay Transformer.

Transforms Bronze records to Silver format (Assay entity inflation).
Uses declarative field_specs DSL for mapping where applicable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.field_specs import (
    FieldGroup,
    FieldSpec,
    int_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.core.transform_utils import flatten_nested_dict
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Assay
from bioetl.domain.transformations import (
    safe_float,
    safe_int,
    safe_str,
)

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# Mapping for variant sequence fields extraction (from ChEMBL nested structure)
_VARIANT_FIELDS: dict[str, Any] = {
    "accession": safe_str,
    "isoform": safe_str,
    "mutation": safe_str,
    "organism": safe_str,
    "sequence": safe_str,
    "tax_id": safe_int,
}


def _extract_variant(data: dict[str, Any] | None) -> dict[str, Any]:
    """Extract variant sequence fields using flatten_nested_dict.

    Args:
        data: Nested variant_sequence dictionary from ChEMBL API.
            Expected structure: {"accession": "P12345", "mutation": "V600E", ...}

    Returns:
        Flattened dictionary with variant_ prefixed keys.

    """
    return flatten_nested_dict(data, "variant_", _VARIANT_FIELDS)


# ============================================================================
# Declarative field groups for Assay entity
# ============================================================================

_IDENTIFIERS = FieldGroup(
    name="identifiers",
    fields=(
        *simple_fields(
            "target_chembl_id",
            "document_chembl_id",
            "cell_chembl_id",
            "tissue_chembl_id",
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
        *int_fields("assay_tax_id"),
    ),
)

_METADATA = FieldGroup(
    name="metadata",
    fields=(
        *simple_fields(
            "description",
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
    primary_id_field = "assay_chembl_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract Assay business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated assay_chembl_id value.

        Returns:
            Dictionary of Assay business fields.

        """
        return {
            # Primary identifier
            "assay_chembl_id": str(primary_id),
            # Declarative field groups
            **map_field_groups(record, _ASSAY_GROUPS),
            # Nested dict extraction (variant)
            **_extract_variant(
                cast("dict[str, Any] | None", record.get("variant_sequence"))
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
