"""ChEMBL target protein-classification relation transformer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import TargetProteinClassification
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, PrimaryId, SilverRecord

_CLASSIFICATION_STATUS_VALUES = {
    "missing_classification",
    "quarantined",
    "resolved",
}


class TargetProteinClassificationTransformer(BaseChemblTransformer):
    """Transforms shaped target classification rows to Silver records."""

    entity_class = TargetProteinClassification
    primary_id_field = "target_id"
    default_entity_type = "target_protein_classification"

    async def transform_pre_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> PreSilverRecord | None:
        """Build an intermediate target-classification relation payload."""
        del context, index
        business_data = self._extract_business_data(
            record,
            self._resolve_primary_id(record),
        )
        return self._stage_optional_normalized_business_data(
            business_data=business_data,
            resolve_entity_id=_target_classification_entity_id,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Build a stable Silver row keyed by target_id + hierarchy_index."""
        business_data = self._extract_business_data(
            record,
            self._resolve_primary_id(record),
        )
        return self._transform_optional_normalized_business_data(
            context=context,
            index=index,
            business_data=business_data,
            resolve_entity_id=_target_classification_entity_id,
        )

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> JsonDict:
        """Extract shaped target protein-classification relation fields."""
        hierarchy_index = _required_non_negative_int(
            record.get("hierarchy_index"),
            field_name="hierarchy_index",
        )
        return {
            "target_id": str(primary_id),
            "component_id": _optional_int(record.get("component_id")),
            "hierarchy_index": hierarchy_index,
            "leaf_id": _optional_int(record.get("leaf_id")),
            "l1_id": _optional_int(record.get("l1_id")),
            "l1_name": _optional_text(record.get("l1_name")),
            "l1_desc": _optional_text(record.get("l1_desc")),
            "l2_id": _optional_int(record.get("l2_id")),
            "l2_name": _optional_text(record.get("l2_name")),
            "l2_desc": _optional_text(record.get("l2_desc")),
            "l3_id": _optional_int(record.get("l3_id")),
            "l3_name": _optional_text(record.get("l3_name")),
            "l3_desc": _optional_text(record.get("l3_desc")),
            "l4_id": _optional_int(record.get("l4_id")),
            "l4_name": _optional_text(record.get("l4_name")),
            "l4_desc": _optional_text(record.get("l4_desc")),
            "l5_id": _optional_int(record.get("l5_id")),
            "l5_name": _optional_text(record.get("l5_name")),
            "l5_desc": _optional_text(record.get("l5_desc")),
            "classification_status": _classification_status(
                record.get("classification_status")
            ),
        }


def _target_classification_entity_id(record: JsonDict) -> str:
    return f"{record['target_id']}:{record['hierarchy_index']}"


def _classification_status(value: object) -> str:
    if value is None:
        return "missing_classification"
    normalized = str(value).strip()
    if normalized not in _CLASSIFICATION_STATUS_VALUES:
        raise ValueError(f"Invalid classification_status: {normalized}")
    return normalized


def _required_non_negative_int(value: object, *, field_name: str) -> int:
    coerced = _optional_int(value)
    if coerced is None or coerced < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return coerced


def _optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None
