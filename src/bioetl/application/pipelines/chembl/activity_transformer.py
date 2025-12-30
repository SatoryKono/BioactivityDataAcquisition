"""ChEMBL Activity Transformer.

Transforms Bronze records to Silver format (Activity entity inflation).
Uses declarative field_specs DSL for mapping where applicable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.field_specs import (
    FieldGroup,
    float_fields,
    int_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.core.transform_utils import flatten_nested_dict
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Activity
from bioetl.domain.transformations import safe_float

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# Mapping for ligand efficiency fields extraction (nested dict)
_LIGAND_EFFICIENCY_FIELDS: dict[str, Any] = {
    "bei": safe_float,
    "le": safe_float,
    "lle": safe_float,
    "sei": safe_float,
}

# Mapping for action type fields extraction (nested dict)
_ACTION_TYPE_FIELDS: dict[str, Any] = {
    "action_type": None,
    "description": None,
    "parent_type": None,
}


# ============================================================================
# Declarative field groups for Activity entity
# ============================================================================

_IDENTIFIERS = FieldGroup(
    name="identifiers",
    fields=(
        *simple_fields("target_chembl_id", "assay_chembl_id", "document_chembl_id"),
        *int_fields("record_id", "src_id"),
    ),
)

_MOLECULE_TARGET_ASSAY = FieldGroup(
    name="molecule_target_assay",
    fields=simple_fields(
        "canonical_smiles",
        "molecule_pref_name",
        "parent_molecule_chembl_id",
        "target_pref_name",
        "target_organism",
        "target_tax_id",
        "assay_type",
        "assay_description",
        "assay_variant_accession",
        "assay_variant_mutation",
        "bao_endpoint",
        "bao_format",
        "bao_label",
    ),
)

_RAW_VALUES = FieldGroup(
    name="raw_values",
    fields=(
        *simple_fields("type", "units", "relation", "text_value"),
        *float_fields("value", "upper_value"),
    ),
)

_STANDARD_VALUES = FieldGroup(
    name="standard_values",
    fields=(
        *simple_fields(
            "standard_type",
            "standard_units",
            "standard_relation",
            "standard_text_value",
        ),
        *float_fields("standard_value", "standard_upper_value", "pchembl_value"),
        *int_fields("standard_flag"),
    ),
)

_UNIT_FIELDS = FieldGroup(
    name="units",
    fields=simple_fields("qudt_units", "uo_units"),
)

_QUALITY_ANNOTATIONS = FieldGroup(
    name="quality_annotations",
    fields=(
        *simple_fields(
            "document_journal",
            "activity_comment",
            "data_validity_comment",
            "data_validity_description",
        ),
        *int_fields("document_year", "potential_duplicate", "toid"),
    ),
)

# All declarative field groups
_ACTIVITY_GROUPS: tuple[FieldGroup, ...] = (
    _IDENTIFIERS,
    _MOLECULE_TARGET_ASSAY,
    _RAW_VALUES,
    _STANDARD_VALUES,
    _UNIT_FIELDS,
    _QUALITY_ANNOTATIONS,
)


class ActivityTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze records to silver."""

    entity_class = Activity
    primary_id_field = "activity_id"

    def _extract_ligand_efficiency(
        self, le_data: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Extract ligand efficiency metrics from nested dictionary.

        Args:
            le_data: Nested ligand efficiency dictionary from ChEMBL API.
                     Expected keys: bei, le, lle, sei.

        Returns:
            Flat dictionary with prefixed keys and float-converted values.
        """
        return flatten_nested_dict(
            le_data, "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS
        )

    def _extract_action_type(
        self, action_data: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Extract action type fields from nested dictionary.

        Args:
            action_data: Nested action type dictionary from ChEMBL API.
                         Expected keys: action_type, description, parent_type.

        Returns:
            Flat dictionary with prefixed keys.
        """
        return flatten_nested_dict(action_data, "action_type_", _ACTION_TYPE_FIELDS)

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract Activity business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated activity_id value.

        Returns:
            Dictionary of Activity business fields.

        """
        # Validate secondary required field
        molecule_id = self._get_required_field(record, "molecule_chembl_id")

        return {
            # Primary and secondary identifiers (manual - need special handling)
            "activity_id": str(primary_id),
            "molecule_chembl_id": str(molecule_id),
            # Declarative field groups
            **map_field_groups(record, _ACTIVITY_GROUPS),
            # Nested dict extraction (not declarative)
            **self._extract_ligand_efficiency(
                cast("dict[str, Any] | None", record.get("ligand_efficiency"))
            ),
            **self._extract_action_type(
                cast("dict[str, Any] | None", record.get("action_type"))
            ),
            # JSON serialization
            "activity_properties": self.serialize_json(
                record.get("activity_properties")
            ),
        }
