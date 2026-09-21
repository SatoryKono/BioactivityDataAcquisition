# src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py
"""ChEMBL AssayParameters Transformer.

Transforms Bronze records to Silver format (AssayParameters entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.field_specs import (
    FieldGroup,
    float_fields,
    map_field_groups,
    simple_fields,
    standard_value_fields,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities.chembl_assay_parameters import AssayParameters
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, PrimaryId


# ============================================================================
# Declarative field groups for AssayParameters entity
# ============================================================================

_RAW_VALUES = FieldGroup(
    name="raw_values",
    fields=(
        *simple_fields("relation", "units", "text_value", "comments"),
        *float_fields("value"),
    ),
)

_STANDARD_VALUES = FieldGroup(
    name="standard_values",
    fields=standard_value_fields(relation_before_units=True),
)

_ASSAY_PARAMS_GROUPS: tuple[FieldGroup, ...] = (
    _RAW_VALUES,
    _STANDARD_VALUES,
)


class AssayParametersTransformer(BaseChemblTransformer):
    """Transforms ChEMBL assay_parameters bronze records to silver.

    Handles:
        - Numeric value normalization (round to 10 decimals via safe_float)
        - Unit standardization awareness
        - Text value preservation
        - Parameter type normalization
        - Heterogeneous value handling (numeric vs text)

    Entity Class: AssayParameters
    Primary ID Field: assay_param_id
    """

    entity_class = AssayParameters
    primary_id_field = "assay_param_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> JsonDict:  # Any: transformer record has heterogeneous values
        """Extract AssayParameters business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated assay_param_id value.

        Returns:
            Dictionary of AssayParameters business fields.
        """
        # Build business data dictionary
        business_data: JsonDict = {
            # Primary identifier (integer)
            "assay_param_id": int(primary_id),
            # Foreign key
            "assay_id": record.get("assay_id") or record.get("assay_chembl_id"),
            # Profile-owned controlled vocabulary normalization runs centrally.
            "type_raw": record.get("type"),
            "type": record.get("type"),
        }

        # Apply declarative field groups
        business_data.update(map_field_groups(record, _ASSAY_PARAMS_GROUPS))

        for raw_name in ("type", "relation", "value"):
            business_data[f"parameter_{raw_name}"] = business_data.pop(raw_name, None)
        return business_data

    def _build_pre_silver_record(
        self,
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> JsonDict:
        """Bridge canonical hash fields to the legacy entity constructor only."""
        entity_data = dict(business_data)
        for raw_name in ("type", "relation", "value"):
            entity_data[raw_name] = entity_data.pop(f"parameter_{raw_name}", None)
        return super()._build_pre_silver_record(
            context, entity_id, content_hash, index, entity_data
        )

    def _postprocess_pre_silver_record(
        self, silver_record: JsonDict, *, business_data: JsonDict
    ) -> JsonDict:
        """Publish canonical aliases before schema, filter and partition checks."""
        del business_data
        for raw_name in ("type", "relation", "value"):
            silver_record[f"parameter_{raw_name}"] = silver_record.pop(raw_name, None)
        return silver_record

    def _has_any_value(self, record: BronzeRecord) -> bool:
        """Check if record has at least one value field populated.

        Used for DQ validation - parameters without any values
        are flagged but not rejected.

        Args:
            record: Bronze record to check.

        Returns:
            True if at least one value field is present.
        """
        return any(
            [
                record.get("value") is not None,
                record.get("text_value") is not None,
                record.get("standard_value") is not None,
                record.get("standard_text_value") is not None,
            ]
        )


__all__ = ["AssayParametersTransformer"]
