"""Record conversion and extraction helpers for BaseTransformer."""

from __future__ import annotations

__all__ = ["ScalarValue", "T", "TEntity_co"]

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.application.core.base_transformer_runtime import (
    ScalarValue,
    T,
    TEntity_co,
    create_entity,
    extract_by_path,
    extract_nested,
    get_required_field,
    normalize_lineage_value,
    serialize_dict,
    serialize_json,
    serialize_json_fields,
    serialize_json_list,
    serialize_list,
)
from bioetl.domain.types import GoldRecord

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord


class _BaseTransformerRecordHelpersMixin:
    """Serialization and record helper methods shared by transformers."""

    @staticmethod
    def serialize_json(value: object) -> ScalarValue:
        """Serialize dict/list to JSON string or native type for Silver layer.

        Args:
            value: Value to serialize. Dicts and lists are converted to JSON strings;
                scalars and None are returned as-is.

        Returns:
            JSON string for composite types, the original scalar for primitives,
            or None when the value is None or an empty composite.
        """
        return serialize_json(value)

    @staticmethod
    def _serialize_dict(d: dict[str, object]) -> str | None:
        return serialize_dict(d)

    @staticmethod
    def _serialize_list(lst: list[object]) -> ScalarValue:
        return serialize_list(lst)

    @staticmethod
    def serialize_json_list(value: Sequence[object] | None) -> str | None:
        """Serialize list to JSON string without unwrapping single elements.

        Args:
            value: Sequence to serialize. Single-element sequences are kept as arrays,
                unlike ``serialize_json`` which unwraps them.

        Returns:
            JSON array string, or None when the sequence is None or empty.
        """
        return serialize_json_list(value)

    @classmethod
    def serialize_json_fields(
        cls,
        record: GoldRecord,
        field_names: Sequence[str],
    ) -> dict[str, str | int | float | bool | None]:
        """Serialize multiple JSON fields at once.

        Args:
            record: Source record from which field values are extracted.
            field_names: Names of fields to serialize via ``serialize_json``.

        Returns:
            Dictionary mapping each field name to its serialized scalar value.
        """
        return serialize_json_fields(record=record, field_names=field_names)

    @staticmethod
    def _normalize_lineage_value(
        field_name: str,
        value: object,
    ) -> object:
        """Normalize lineage/meta field values after rename."""
        return normalize_lineage_value(field_name=field_name, value=value)

    @staticmethod
    def _get_required_field(
        record: BronzeRecord,
        field: str,
        *,
        allow_empty: bool = False,
    ) -> object:
        """Extract and validate a required field from the record.

        Args:
            record: Bronze record to extract the field from.
            field: Name of the required field.
            allow_empty: When False (default), empty strings and empty
                collections also raise TransformationError.

        Returns:
            The field value if present and non-empty (per ``allow_empty`` rules).
        """
        return get_required_field(record=record, field=field, allow_empty=allow_empty)

    @staticmethod
    def _extract_by_path(
        record: BronzeRecord,
        keys: Sequence[str],
        default: object | None = None,
    ) -> object | None:
        """Safely extract a value from nested dictionaries by key sequence.

        Args:
            record: Bronze record serving as the root of the traversal.
            keys: Ordered sequence of keys representing the path to the target value.
            default: Value to return when any key is missing or an intermediate
                value is not a dict. Defaults to None.

        Returns:
            The extracted value at the end of the key path, or ``default`` if not found.
        """
        return extract_by_path(record=record, keys=keys, default=default)

    @staticmethod
    def _extract_nested(
        record: BronzeRecord,
        path: str,
        default: object | None = None,
    ) -> object | None:
        """Safely extract a value from nested dictionaries using dot path.

        Args:
            record: Bronze record serving as the root of the traversal.
            path: Dot-separated key path (e.g., ``'journal.issue.volume'``).
            default: Value returned when the path cannot be fully resolved. Defaults to None.

        Returns:
            The value at the end of the dot path, or ``default`` if not found.
        """
        return extract_nested(record=record, path=path, default=default)

    def _create_entity(
        self,
        entity_class: type[T],
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        **business_data: object,
    ) -> T:
        """Create a domain entity with lineage metadata.

        Args:
            entity_class: Concrete entity dataclass to instantiate.
            context: Pipeline execution context providing run ID, run type, and ingestion timestamp.
            entity_id: Stable identifier for the entity, wrapped as ``EntityID``.
            content_hash: SHA-based hash of entity content for deduplication, wrapped as ``ContentHash``.
            index: Zero-based position of the record within the current batch.
            **business_data: Provider-specific field values passed as keyword arguments to the entity.

        Returns:
            Instantiated entity of type ``T`` with lineage fields populated.
        """
        return create_entity(
            entity_class=entity_class,
            context=context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            business_data=business_data,
        )
