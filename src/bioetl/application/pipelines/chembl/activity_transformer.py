"""ChEMBL Activity Transformer.

Transforms Bronze records to Silver format (Activity entity inflation).
Uses declarative field_specs DSL for mapping where applicable.
"""

from __future__ import annotations

__all__ = ["ActivityTransformer"]


from collections.abc import Mapping
from typing import TYPE_CHECKING, ClassVar, cast, override

from bioetl.application.core.base_transformer import TransformationError
from bioetl.application.core.dict_transformers import flatten_nested_dict
from bioetl.application.core.field_specs import map_field_groups
from bioetl.application.pipelines.chembl._activity_transformer_maps import (
    _ACTION_TYPE_FIELDS,
    _ACTIVITY_GROUPS,
    _LIGAND_EFFICIENCY_FIELDS,
    _ONTOLOGY_COMPANION_DEFAULTS,
)
from bioetl.application.pipelines.chembl.alias_policy import (
    CHEMBL_GOLD_PUBLICATION_IDENTIFIER_PROJECTIONS,
    get_bronze_provider_aliases,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.application.pipelines.chembl.provider_aliases import (
    normalize_provider_aliases,
)
from bioetl.domain.entities import Bioactivity
from bioetl.domain.types import GoldRecord, JsonDict

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, PrimaryId


class ActivityTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze records to silver.

    Uses the unified Bioactivity entity for domain representation.
    """

    entity_class = Bioactivity
    primary_id_field = "activity_id"
    default_entity_type = "activity"
    _PROVIDER_ALIASES: ClassVar[Mapping[str, str]] = get_bronze_provider_aliases(
        "activity"
    )

    @override
    def _prepare_record(
        self,
        record: BronzeRecord,
    ) -> BronzeRecord:
        """Normalize provider-native activity identifiers at the ingestion boundary."""
        return normalize_provider_aliases(record, self._PROVIDER_ALIASES)

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
            for target_field, aliases in (
                CHEMBL_GOLD_PUBLICATION_IDENTIFIER_PROJECTIONS.items()
            )
        }

    @staticmethod
    def _coalesce_activity_relation(
        business_data: Mapping[str, object],
    ) -> object | None:
        """Prefer the raw relation operator, but fall back to standard_relation.

        Recent ChEMBL activity payloads may omit ``relation`` while still
        populating ``standard_relation``. The Silver contract requires the
        canonical ``activity_relation`` field, so preserve replayable coverage
        by reusing the standardized operator when the raw operator is absent.
        """
        relation = business_data.get("relation")
        if isinstance(relation, str):
            if relation.strip():
                return relation
        elif relation is not None:
            return relation
        return business_data.get("standard_relation")

    @override
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
        molecule_id = record.get("molecule_id")
        if not molecule_id:
            raise TransformationError(
                "Missing required field: molecule_id",
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
        business_data["activity_relation"] = self._coalesce_activity_relation(
            business_data
        )

        # Accept canonical FK fields when tests or staged fixtures already normalized them.
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

    @override
    def _postprocess_pre_silver_record(
        self,
        silver_record: GoldRecord,
        *,
        business_data: JsonDict,
    ) -> GoldRecord:
        """Project canonical original activity fields before structural policy checks."""
        relation = silver_record.get("activity_relation")
        if isinstance(relation, str) and not relation.strip():
            relation = None
        silver_record["activity_type"] = (
            silver_record.get("activity_type")
            if silver_record.get("activity_type") is not None
            else business_data.get("standard_type")
        )
        silver_record["activity_relation"] = (
            relation if relation is not None else business_data.get("standard_relation")
        )
        silver_record["activity_value"] = (
            silver_record.get("activity_value")
            if silver_record.get("activity_value") is not None
            else business_data.get("standard_value")
        )
        silver_record.pop("type", None)
        silver_record.pop("relation", None)
        silver_record.pop("value", None)
        return silver_record

    @override
    def transform_for_gold(
        self,
        context: PipelineContext,
        silver_record: GoldRecord,
    ) -> GoldRecord:
        """Project canonical Silver aliases back to the published Gold contract."""
        gold_record = super().transform_for_gold(context, silver_record)
        gold_record["type"] = gold_record.pop("activity_type", None)
        gold_record["relation"] = gold_record.pop("activity_relation", None)
        gold_record["value"] = gold_record.pop("activity_value", None)
        return gold_record
