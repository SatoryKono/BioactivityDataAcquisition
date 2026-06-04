"""Facade-level runtime helpers for :mod:`bioetl.infrastructure.storage.gold_writer`."""

from __future__ import annotations

from bioetl.domain.types import GoldSchemaPolicyByVersion, ScdConfig
from bioetl.infrastructure.storage.gold.pipeline_helpers import GoldWriteRequest
from bioetl.infrastructure.storage.gold.writer_support import (
    _write_dual_targets_impl,
    _write_single_target_impl,
)


def normalize_scd_config(
    scd_config: ScdConfig,
    primary_keys: list[str] | None,
) -> ScdConfig:
    """Compatibility wrapper preserving canonical monkeypatch/import path."""
    from bioetl.infrastructure.storage.gold.pipeline_helpers import (
        normalize_scd_config as _normalize_scd_config,
    )

    return _normalize_scd_config(scd_config, primary_keys)


async def write_single_target(
    writer: object,
    *,
    request: GoldWriteRequest,
) -> None:
    """Execute one physical Gold write target through the standard pipeline."""
    await _write_single_target_impl(writer, request=request)


async def write_dual_targets(
    writer: object,
    *,
    request: GoldWriteRequest,
    schema_policy: GoldSchemaPolicyByVersion,
) -> None:
    """Write all versioned Gold targets and fail on the first error."""
    await _write_dual_targets_impl(
        writer,
        request=request,
        schema_policy=schema_policy,
    )


__all__ = ["normalize_scd_config", "write_dual_targets", "write_single_target"]
