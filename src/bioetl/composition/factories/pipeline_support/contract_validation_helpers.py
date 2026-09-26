"""Contract preflight helpers extracted from pipeline.contract_validator."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)
from bioetl.infrastructure.config.contract_policy_validation import (
    resolve_silver_columns as _resolve_silver_columns_impl,
)
from bioetl.infrastructure.config.contract_policy_validation import (
    schema_columns as _schema_columns_impl,
)
from bioetl.infrastructure.config.contract_policy_validation import (
    validate_pipeline_contract_policy as _validate_pipeline_contract_policy_impl,
)

from bioetl.application.core.base_transformer import BaseTransformer

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.composition.factories.pipeline.config_types import (
        PipelineFactoryConfig,
        TransformerClassRef,
    )


def _schema_columns(
    schema_class: object,
) -> set[str]:
    """Compatibility wrapper over canonical schema-column extraction helper."""
    return _schema_columns_impl(schema_class)


def _resolve_silver_columns(config: PipelineFactoryConfig) -> set[str]:
    """Compatibility wrapper over canonical Silver schema resolution helper."""
    return _resolve_silver_columns_impl(
        provider=config.provider,
        entity_type=config.entity_type,
        pandera_silver_schema=config.pandera_silver_schema,
        silver_schema=config.silver_schema,
    )


def _validate_contract_policy(config: PipelineFactoryConfig) -> None:
    """Assembly-scoped wrapper over canonical contract-policy validation."""
    _validate_pipeline_contract_policy_impl(
        provider=config.provider,
        entity_type=config.entity_type,
        pandera_silver_schema=config.pandera_silver_schema,
        silver_schema=config.silver_schema,
        gold_schema=config.gold_schema,
        load_policy=load_pipeline_contract_policy,
    )


def _resolve_transformer_class_ref(
    transformer_class: TransformerClassRef | None,
) -> type[BaseTransformer] | None:
    """Resolve a manifest transformer reference into the actual class."""
    if transformer_class is None or not isinstance(transformer_class, str):
        return transformer_class
    module_name, _, attr_name = transformer_class.rpartition(".")
    if not module_name or not attr_name:
        raise ValueError(f"Invalid transformer class reference: {transformer_class!r}")
    resolved = getattr(import_module(module_name), attr_name)

    if not isinstance(resolved, type) or not issubclass(resolved, BaseTransformer):
        raise TypeError(
            f"Transformer reference must resolve to BaseTransformer: {transformer_class}"
        )
    return resolved


__all__ = [
    "_resolve_silver_columns",
    "_resolve_transformer_class_ref",
    "_schema_columns",
    "_validate_contract_policy",
]
