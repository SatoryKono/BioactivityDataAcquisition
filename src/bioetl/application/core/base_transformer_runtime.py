# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Pure helper functions for BaseTransformer record handling."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, TypeVar, cast

import orjson

from bioetl.domain.types import ContentHash, EntityID, GoldRecord

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.types import BronzeRecord

T = TypeVar("T", bound="BaseEntity")
TEntity_co = TypeVar("TEntity_co", bound="BaseEntity", covariant=True)
ScalarValue = str | int | float | bool | None
type _DICT_STR_OBJECT = dict[str, object]


class _EntityConstructor(Protocol[TEntity_co]):
    """Constructor protocol for entity dataclasses with lineage kwargs."""

    def __call__(
        self,
        *,
        entity_id: EntityID,
        content_hash: ContentHash,
        run_id: object,
        run_type: object,
        source_batch_id: object | None,
        ingestion_ts: datetime.datetime,
        _index: int,
        **business_data: object,
    ) -> TEntity_co:
        """Create and return an entity instance."""
        ...


def serialize_dict(data: dict[str, object]) -> str | None:
    """Serialize a dictionary deterministically or return None when empty."""
    if not data:
        return None
    return orjson.dumps(data, option=orjson.OPT_SORT_KEYS).decode("utf-8")


def serialize_list(values: list[object]) -> ScalarValue:
    """Serialize list payloads using BaseTransformer single-item semantics."""
    if not values:
        return None
    if len(values) == 1:
        item = values[0]
        if isinstance(item, dict):
            return serialize_dict(cast(_DICT_STR_OBJECT, item))
        if isinstance(item, list):
            return (
                None
                if not item
                else orjson.dumps(item, option=orjson.OPT_SORT_KEYS).decode("utf-8")
            )
        return cast("ScalarValue", item)
    return orjson.dumps(values, option=orjson.OPT_SORT_KEYS).decode("utf-8")


def serialize_json(value: object) -> ScalarValue:
    """Serialize dict/list to JSON string or native type for Silver layer."""
    if value is None:
        return None
    if isinstance(value, dict):
        return serialize_dict(cast(_DICT_STR_OBJECT, value))
    if isinstance(value, list):
        return serialize_list(cast("list[object]", value))
    return cast("ScalarValue", value)


def serialize_json_list(value: Sequence[object] | None) -> str | None:
    """Serialize list to JSON string without unwrapping single elements."""
    if value is None or len(value) == 0:
        return None
    json_bytes: bytes = orjson.dumps(list(value), option=orjson.OPT_SORT_KEYS)
    return json_bytes.decode("utf-8")


def serialize_json_fields(
    *,
    record: GoldRecord,
    field_names: Sequence[str],
) -> dict[str, str | int | float | bool | None]:
    """Serialize multiple JSON fields at once."""
    return {name: serialize_json(record.get(name)) for name in field_names}


def normalize_lineage_value(
    *,
    field_name: str,
    value: object,
) -> object:
    """Normalize lineage/meta field values after rename."""
    if field_name == "run_id" and value is not None:
        return str(value)
    if field_name == "run_type" and value is not None:
        return str(getattr(value, "value", value))
    if field_name == "source_batch_id":
        return str(value) if value else None
    if field_name == "ingestion_ts" and isinstance(value, datetime.datetime):
        return value.isoformat()
    return value


def get_required_field(
    *,
    record: BronzeRecord,
    field: str,
    allow_empty: bool = False,
) -> object:
    """Extract and validate a required field from the record."""
    from bioetl.application.core.base_transformer.errors import TransformationError

    value = record.get(field)
    if value is None:
        raise TransformationError(f"Missing required field: {field}", field=field)
    if not allow_empty:
        if isinstance(value, str) and not value.strip():
            raise TransformationError(f"Required field is empty: {field}", field=field)
        if isinstance(value, (list, dict)) and len(value) == 0:
            raise TransformationError(f"Required field is empty: {field}", field=field)
    return value


def extract_by_path(
    *,
    record: BronzeRecord,
    keys: Sequence[str],
    default: object | None = None,
) -> object | None:
    """Safely extract a value from nested dictionaries by key sequence."""
    current: object = record
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = cast(_DICT_STR_OBJECT, current).get(key)
        if current is None:
            return default
    return current


def extract_nested(
    *,
    record: BronzeRecord,
    path: str,
    default: object | None = None,
) -> object | None:
    """Safely extract a value from nested dictionaries using dot path."""
    return extract_by_path(record=record, keys=path.split("."), default=default)


def create_entity[T: "BaseEntity"](
    *,
    entity_class: type[T],
    context: PipelineContext,
    entity_id: str,
    content_hash: str,
    index: int,
    business_data: dict[str, object],
) -> T:
    """Create a domain entity with lineage metadata."""
    entity_factory = cast("EntityConstructor[T]", entity_class)  # pyright: ignore[reportInvalidCast]
    return entity_factory(
        entity_id=EntityID(entity_id),
        content_hash=ContentHash(content_hash),
        run_id=context.run_id,
        run_type=context.run_type,
        source_batch_id=context.source_batch_id,
        ingestion_ts=context.started_at,
        _index=index,
        **business_data,
    )


EntityConstructor = _EntityConstructor

__all__ = [
    "EntityConstructor",
    "ScalarValue",
    "T",
    "TEntity_co",
    "create_entity",
    "extract_by_path",
    "extract_nested",
    "get_required_field",
    "normalize_lineage_value",
    "serialize_dict",
    "serialize_json",
    "serialize_json_fields",
    "serialize_json_list",
    "serialize_list",
]
