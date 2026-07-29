# mypy: disable-error-code="arg-type,attr-defined,unused-ignore"
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Private hook and helper methods for BasePublicationTransformer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from bioetl.application.pipelines.common.publication_transformer_records import (
    classification_payload,
)
from bioetl.application.pipelines.common.publication_vocab_observability import (
    emit_unknown_publication_vocab_metrics,
)
from bioetl.domain.value_objects import PublicationYear
from bioetl.domain.mixin_host import as_mixin_host

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities.base import BaseEntity
    from bioetl.domain.types import BronzeRecord, JsonDict, PrimaryId, SilverRecord


class PublicationTransformerHooksMixin:
    """Cohesive private hooks shared by publication transformers."""

    _CONTENT_FIELDS: tuple[str, ...] = ("abstract",)
    """Fields to normalize via ``strip_html_tags`` after extraction."""

    def _pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None:
        """Optional pre-extraction validation hook."""
        pass

    def _extract_business_data(self, record: BronzeRecord) -> JsonDict:
        """Extract and normalize fields from bronze record."""
        blocks = getattr(self, "extraction_blocks", [])
        if blocks:
            result: JsonDict = {}
            for block in blocks:
                result.update(block.extract(record))
            return result

        raise NotImplementedError(
            f"{as_mixin_host(self).__class__.__name__} must implement extraction_blocks property "  # Any: mixin host surface (self attrs/methods)
            "or override _extract_business_data() method."
        )

    def _get_primary_id_field(self) -> str:
        """Return the name of the primary identifier field."""
        raise NotImplementedError()

    def _get_entity_class(self) -> type[BaseEntity]:
        """Return the domain entity class for this publication type."""
        raise NotImplementedError()

    def _should_log_fallback_lookup(self) -> bool:
        """Return True if fallback lookup logging is enabled."""
        return True

    def _post_process_silver_record(self, silver_record: SilverRecord) -> SilverRecord:
        """Finalize a Silver record after entity inflation.

        Subclasses can override this hook for compatibility-sensitive cleanup,
        but the common publication path should preserve the record unchanged.
        """
        return silver_record

    def _validate_primary_id(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        index: int,
    ) -> tuple[str, PrimaryId] | None:
        """Validate primary ID presence."""
        primary_id_field = as_mixin_host(self)._get_primary_id_field()  # Any: mixin host surface (self attrs/methods)
        primary_id = business_data.get(primary_id_field)
        if not primary_id:
            context.logger.warning(
                "record_skipped_no_id",
                index=index,
                lookup_method=business_data.get("_lookup_method"),
            )
            return None
        return primary_id_field, primary_id

    def _validate_publication_year_value(self, raw: object) -> int | None:
        """Validate publication year and return the canonical integer value."""
        value = as_mixin_host(self).validate_value_object(  # Any: mixin host surface (self attrs/methods)
            PublicationYear,
            raw,
            as_string=False,
        )
        return value if isinstance(value, int) else None

    def _normalize_content_fields(
        self,
        business_data: dict[
            str, Any  # Any: transformer record has heterogeneous values
        ],  # Any: transformer record has heterogeneous values
    ) -> JsonDict:  # Any: transformer record has heterogeneous values
        """Apply uniform text cleanup to configured content fields."""
        for field in as_mixin_host(self)._CONTENT_FIELDS:  # Any: mixin host surface (self attrs/methods)
            raw = business_data.get(field)
            if raw is not None:
                business_data[field] = as_mixin_host(self)._data_normalizer.strip_html_tags(raw)  # Any: mixin host surface (self attrs/methods)
        return business_data

    def _log_fallback_if_needed(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        primary_id_field: str,
        primary_id: PrimaryId,
    ) -> None:
        """Log fallback lookup usage when applicable."""
        if as_mixin_host(self)._metadata_strategy.should_log_fallback_lookup():  # Any: mixin host surface (self attrs/methods)
            lookup_method = business_data.get("_lookup_method", "unknown")
            if lookup_method in ("title_fallback", "title_only"):
                context.logger.info(
                    "fallback_lookup_used",
                    **{primary_id_field: primary_id},
                    lookup_method=lookup_method,
                    original_id=business_data.get("_original_id"),
                )

    def _emit_unknown_publication_vocab_metrics(
        self,
        context: PipelineContext,
        normalized_business_data: JsonDict,
    ) -> None:
        """Publish bounded counters for unknown raw publication vocabulary drift."""
        pipeline_name = context.pipeline_name or f"{as_mixin_host(self).provider}_{as_mixin_host(self).entity_type}"  # Any: mixin host surface (self attrs/methods)
        emit_unknown_publication_vocab_metrics(
            metrics=as_mixin_host(self)._metrics,  # Any: mixin host surface (self attrs/methods)
            pipeline_name=pipeline_name,
            provider=as_mixin_host(self).provider,  # Any: mixin host surface (self attrs/methods)
            normalized_business_data=normalized_business_data,
        )

    def _classify_publication_type(
        self,
        provider: str,
        raw_type: str | None = None,
        raw_types_list: list[str] | None = None,
    ) -> dict[str, str | None]:
        """Classify publication type using the unified 3-level hierarchy."""
        return classification_payload(provider, raw_type, raw_types_list)


__all__ = ["PublicationTransformerHooksMixin"]
