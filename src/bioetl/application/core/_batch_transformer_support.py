"""Private helpers for BatchTransformer construction paths."""

from __future__ import annotations

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.core.record_processor_config import RecordProcessorConfig


def build_default_normalization_processor(
    config: RecordProcessorConfig,
) -> RecordNormalizationProcessor | None:
    """Build the default normalization stage from record-processor config."""
    if not config.normalization_enabled:
        return None
    return RecordNormalizationProcessor(
        provider=config.provider,
        entity_type=config.entity_type,
        rule_set=config.normalization_rule_set,
        allow_compatibility_fallback=config.allow_compatibility_fallback,
        content_hash_policy_authoritative=config.content_hash_policy_authoritative,
        content_hash_include_fields=config.content_hash_include_fields,
        content_hash_exclude_fields=config.content_hash_exclude_fields,
        content_hash_policy_by_version=config.content_hash_policy_by_version,
    )
