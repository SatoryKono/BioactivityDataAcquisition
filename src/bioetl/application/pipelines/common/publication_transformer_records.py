# pyright: reportInvalidCast=false
# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Record assembly helpers for the base publication transformer."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.pipelines.common.publication_assembly import (
    PreparedPublicationOutcome,
    build_publication_silver_record,
)
from bioetl.domain.mapping.publication_type_classification import (
    build_publication_type_classification_payload,
)

if TYPE_CHECKING:
    from bioetl.application.pipelines.common.base_publication_transformer import (
        BasePublicationTransformer,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import JsonDict, PrimaryId, SilverRecord


def classification_payload(
    provider: str,
    raw_type: str | None,
    raw_types_list: list[str] | None,
) -> dict[str, str | None]:
    """Build the normalized publication-type classification payload."""
    return build_publication_type_classification_payload(
        provider,
        raw_type=raw_type,
        raw_types_list=raw_types_list,
        raw_field_name="publication_type",
    )


def resolve_publication_entity_id(
    transformer: BasePublicationTransformer,
    primary_id_field: str,
    primary_id: PrimaryId,
) -> str:
    """Resolve the stable entity identifier from the validated primary ID."""
    return cast(
        str,
        transformer.compute_entity_id(
            source_id=str(primary_id),
            record={primary_id_field: primary_id},
        ),
    )


def prepare_content_hash_payload(business_data: JsonDict) -> JsonDict:
    """Prepare the hash-ready business payload without orchestration metadata."""
    return {
        key: value for key, value in business_data.items() if not key.startswith("_")
    }


def compute_publication_identifiers(
    transformer: BasePublicationTransformer,
    primary_id_field: str,
    primary_id: PrimaryId,
    business_data: JsonDict,
) -> tuple[str, str]:
    """Compute the stable entity id plus content digest."""
    entity_id = resolve_publication_entity_id(
        transformer,
        primary_id_field,
        primary_id,
    )
    content_hash = transformer.compute_content_hash(
        prepare_content_hash_payload(business_data),
        exclude_none=True,
    )
    return entity_id, content_hash


def build_pre_silver_publication_record(
    transformer: BasePublicationTransformer,
    prepared: PreparedPublicationOutcome,
) -> PreSilverRecord:
    """Build the staged pre-silver publication payload for downstream finalization."""
    entity_id = resolve_publication_entity_id(
        transformer,
        prepared.primary_id_field,
        prepared.primary_id,
    )

    def build_silver_record(
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> JsonDict:
        return build_publication_silver_record(
            transformer,
            context,
            entity_id,
            content_hash,
            index,
            business_data,
        )

    def apply_structural_policy(
        context: PipelineContext,
        record: JsonDict,
        index: int,
    ) -> JsonDict | None:
        return cast(
            "JsonDict | None",
            transformer._apply_structural_policy(
                context,
                cast("SilverRecord", record),
                index,
            ),
        )

    def apply_silver_filter(
        context: PipelineContext,
        record: JsonDict,
        index: int,
    ) -> None:
        transformer._apply_silver_filter(
            context,
            cast("SilverRecord", record),
            index,
        )

    return PreSilverRecord(
        entity_id=entity_id,
        business_data=prepared.business_data,
        build_silver_record=build_silver_record,
        apply_structural_policy=apply_structural_policy,
        apply_silver_filter=apply_silver_filter,
    )


def assemble_publication_silver_record(
    transformer: BasePublicationTransformer,
    context: PipelineContext,
    *,
    index: int,
    prepared: PreparedPublicationOutcome,
    normalized_business_data: JsonDict,
) -> SilverRecord:
    """Assemble the final Silver record from normalized publication business data."""
    entity_id, content_hash = compute_publication_identifiers(
        transformer,
        prepared.primary_id_field,
        prepared.primary_id,
        normalized_business_data,
    )
    silver_record = build_publication_silver_record(
        transformer,
        context,
        entity_id,
        content_hash,
        index,
        normalized_business_data,
    )
    return cast(
        "SilverRecord",
        transformer._record_normalizer.project_normalization_findings(
            silver_record,
            context=context,
            index=index,
        ),
    )


__all__ = [
    "assemble_publication_silver_record",
    "build_pre_silver_publication_record",
    "classification_payload",
    "compute_publication_identifiers",
    "prepare_content_hash_payload",
    "resolve_publication_entity_id",
]
