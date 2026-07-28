"""Idempotency-contract validation helpers for medallion preflight."""

from __future__ import annotations

from bioetl.domain.config.table import APPEND_SAFE_IDEMPOTENCY_CONTRACTS
from bioetl.domain.medallion import Layer
from bioetl.domain.types import ConfigValidationError


def validate_idempotency_contracts(
    *,
    silver_mode: str,
    gold_mode: str,
    silver_contract: str | None,
    gold_contract: str | None,
) -> list[ConfigValidationError]:
    """Validate explicit sink idempotency contracts against write semantics."""
    return [
        *_validate_layer_idempotency_contract(
            layer=Layer.SILVER,
            mode=silver_mode,
            contract=silver_contract,
        ),
        *_validate_layer_idempotency_contract(
            layer=Layer.GOLD,
            mode=gold_mode,
            contract=gold_contract,
        ),
    ]

def _validate_layer_idempotency_contract(
    *,
    layer: Layer,
    mode: str,
    contract: str | None,
) -> list[ConfigValidationError]:
    field = f"sink.{layer.value}.idempotency_contract"
    if contract is None:
        return [
            ConfigValidationError(
                field=field,
                expected=f"explicit idempotency contract for {layer.value} mode '{mode}'",
                actual="missing",
                rule="RULES §2.1: semantic Silver/Gold outputs MUST declare idempotency_contract",
            )
        ]
    if contract == "disallowed":
        return [
            ConfigValidationError(
                field=field,
                expected="contract compatible with configured write mode",
                actual="disallowed",
                rule="RULES §2.1: semantic Silver/Gold outputs must not declare idempotency_contract=disallowed",
            )
        ]
    if mode == "append":
        if contract in APPEND_SAFE_IDEMPOTENCY_CONTRACTS:
            return []
        return [
            ConfigValidationError(
                field=field,
                expected=(
                    "one of: append_log, occurrence_only, "
                    "partition_append_with_stable_partition_key"
                ),
                actual=contract,
                rule="RULES §2.1: append-mode semantic outputs require append-safe idempotency_contract",
            )
        ]
    expected_contract = _expected_contract_for_mode(layer=layer, mode=mode)
    if expected_contract is None or contract == expected_contract:
        return []
    return [
        ConfigValidationError(
            field=field,
            expected=expected_contract,
            actual=contract,
            rule="RULES §2.1: declared idempotency_contract must match configured semantic write mode",
        )
    ]

def _expected_contract_for_mode(*, layer: Layer, mode: str) -> str | None:
    if layer is Layer.SILVER and mode == "merge":
        return "merge_upsert"
    if layer is Layer.GOLD and mode == "scd2":
        return "scd2"
    if layer is Layer.GOLD and mode == "overwrite":
        return "overwrite_rebuild"
    return None

__all__ = [
    "validate_idempotency_contracts",
]
