"""ChEMBL Activity Transformer.

Transforms Bronze records to Silver format (Activity entity inflation).
Uses declarative field_specs DSL for mapping where applicable.
"""

from __future__ import annotations

__all__ = ["ActivityTransformer"]


from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer import TransformationError
from bioetl.application.core.dict_transformers import flatten_nested_dict
from bioetl.application.core.field_specs import (
    FieldGroup,
    FieldSpec,
    float_fields,
    int_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Bioactivity
from bioetl.domain.transformations import safe_float
from bioetl.domain.types import GoldRecord, JsonDict
from bioetl.domain.value_objects.taxonomy_id import validate_taxonomy_id

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord, PrimaryId


# Mapping for ligand efficiency fields extraction (nested dict)
_LIGAND_EFFICIENCY_FIELDS: JsonDict = {  # Any: converter callables or None
    "bei": safe_float,
    "le": safe_float,
    "lle": safe_float,
    "sei": safe_float,
}

# Mapping for action type fields extraction (nested dict)
_ACTION_TYPE_FIELDS: JsonDict = {  # Any: converter callables or None
    "action_type": None,
    "description": None,
    "parent_type": None,
}

_PUBLICATION_IDENTIFIER_ALIASES: dict[str, tuple[str, ...]] = {
    "publication_doi": ("publication_doi", "doi", "document_doi"),
    "publication_pmid": (
        "publication_pmid",
        "pmid",
        "pubmed_id",
        "document_pubmed_id",
    ),
    "publication_pmc_id": ("publication_pmc_id", "pmc_id", "document_pmc_id"),
}

_ONTOLOGY_COMPANION_DEFAULTS: JsonDict = {
    "bao_endpoint_iri": None,
    "bao_endpoint_mapping_status": None,
    "bao_format_iri": None,
    "bao_format_mapping_status": None,
    "bao_ontology_version": None,
    "uo_unit_iri": None,
    "uo_unit_mapping_status": None,
    "uo_ontology_version": None,
    "qudt_unit_iri": None,
    "qudt_unit_mapping_status": None,
    "qudt_ontology_version": None,
}

# ============================================================================
# Declarative field groups for Activity entity
# ============================================================================

_IDENTIFIERS = FieldGroup(
    name="identifiers",
    fields=(
        FieldSpec("target_chembl_id", target="target_id"),
        FieldSpec("assay_chembl_id", target="assay_id"),
        FieldSpec("document_chembl_id", target="publication_id"),
        *int_fields("record_id", "src_id"),
    ),
)

_MOLECULE_TARGET_ASSAY = FieldGroup(
    name="molecule_target_assay",
    fields=(
        *simple_fields(
            "canonical_smiles",
            "molecule_pref_name",
            "target_pref_name",
            "target_organism",
        ),
        FieldSpec("parent_molecule_chembl_id", target="parent_molecule_id"),
        # Standardized to 'target_taxonomy_id' for NCBI consistency (was 'tax_id')
        FieldSpec(
            "target_tax_id",
            target="target_taxonomy_id",
            converter=validate_taxonomy_id,
        ),
        *simple_fields(
            "assay_type",
            "assay_description",
            "assay_variant_accession",
            "assay_variant_mutation",
            "bao_endpoint",
            "bao_format",
            "bao_label",
        ),
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
        FieldSpec("document_journal", target="journal"),
        *simple_fields(
            "activity_comment",
            "data_validity_comment",
            "data_validity_description",
        ),
        FieldSpec("document_year", target="publication_year"),
        *int_fields(
            "potential_duplicate",
            "toid",
            "manual_curation_flag",
            "original_activity_id",
        ),
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
    """Transforms ChEMBL bronze records to silver.

    Uses the unified Bioactivity entity for domain representation.
    """

    entity_class = Bioactivity
    primary_id_field = "activity_id"
    default_entity_type = "activity"

    @staticmethod
    def _extract_ligand_efficiency(
        le_data: JsonDict | None,  # Any: untyped ChEMBL API JSON
    ) -> JsonDict:  # Any: untyped ChEMBL API JSON
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

    @staticmethod
    def _extract_action_type(
        action_data: JsonDict | None,  # Any: untyped ChEMBL API JSON
    ) -> JsonDict:  # Any: untyped ChEMBL API JSON
        """Extract action type fields from nested dictionary.

        Args:
            action_data: Nested action type dictionary from ChEMBL API.
                         Expected keys: action_type, description, parent_type.

        Returns:
            Flat dictionary with prefixed keys.
        """
        return flatten_nested_dict(
            action_data,
            "action_type_",
            _ACTION_TYPE_FIELDS,
            renames={"action_type_action_type": "action_type"},
        )

    @staticmethod
    def _first_truthy_value(
        record: BronzeRecord,
        *field_names: str,
    ) -> object | None:
        """Return the first populated value across source alias fields."""
        for field_name in field_names:
            value = record.get(field_name)
            if value:
                return cast("object", value)
        return None

    @classmethod
    def _extract_publication_identifiers(
        cls,
        record: BronzeRecord,
    ) -> JsonDict:
        """Extract publication identifiers from canonical and provider aliases."""
        return {
            target_field: cls._first_truthy_value(record, *aliases)
            for target_field, aliases in _PUBLICATION_IDENTIFIER_ALIASES.items()
        }

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> GoldRecord:
        """Extract Activity business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated activity_id value.

        Returns:
            Dictionary of Activity business fields.

        """
        # Support both unified and legacy identifier names
        molecule_id = record.get("molecule_chembl_id") or record.get("molecule_id")
        if not molecule_id:
            raise TransformationError(
                "Missing required field: molecule_chembl_id or molecule_id",
                field="molecule_id",
            )

        business_data = {
            # Primary and secondary identifiers (manual - need special handling)
            "activity_id": str(primary_id),
            "molecule_id": str(molecule_id),
            # Declarative field groups
            **map_field_groups(record, _ACTIVITY_GROUPS),
            # Shared domain normalization resolves ontology companion bundles
            # only for fields that are present in the staged payload.
            **_ONTOLOGY_COMPANION_DEFAULTS,
            # Nested dict extraction (not declarative)
            **self._extract_ligand_efficiency(
                cast(
                    "JsonDict | None",  # Any: untyped ChEMBL API JSON
                    record.get("ligand_efficiency"),
                )
            ),
            **self._extract_action_type(
                cast(
                    "JsonDict | None",  # Any: untyped ChEMBL API JSON
                    record.get("action_type"),
                )
            ),
            **self._extract_publication_identifiers(record),
            # JSON serialization
            "activity_properties": self.serialize_json(
                record.get("activity_properties")
            ),
        }

        # Support both unified and legacy FK source fields from input record
        business_data["target_id"] = business_data.get("target_id") or record.get(
            "target_id"
        )
        business_data["assay_id"] = business_data.get("assay_id") or record.get(
            "assay_id"
        )
        business_data["publication_id"] = business_data.get(
            "publication_id"
        ) or record.get("publication_id")
        return business_data
