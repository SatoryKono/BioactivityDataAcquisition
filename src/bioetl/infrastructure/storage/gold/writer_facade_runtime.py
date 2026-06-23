"""Facade-level runtime helpers for :mod:`bioetl.infrastructure.storage.gold_writer`."""

from __future__ import annotations


def normalize_scd_config(
    scd_config: object,
    primary_keys: list[str] | None,
) -> object:
    """Compatibility wrapper preserving canonical monkeypatch/import path."""
    from bioetl.infrastructure.storage.gold.pipeline_helpers import (
        normalize_scd_config as _normalize_scd_config,
    )

    return _normalize_scd_config(scd_config, primary_keys)


async def write_single_target(
    writer: object,
    *,
    request: object,
) -> None:
    """Execute one physical Gold write target through the standard pipeline."""
    from bioetl.infrastructure.storage.gold.writer_support import (
        _write_single_target_impl,
    )

    await _write_single_target_impl(writer, request=request)


async def write_dual_targets(
    writer: object,
    *,
    request: object,
    schema_policy: object,
) -> None:
    """Write all versioned Gold targets and fail on the first error."""
    from bioetl.infrastructure.storage.gold.writer_support import (
        _write_dual_targets_impl,
    )

    await _write_dual_targets_impl(
        writer,
        request=request,
        schema_policy=schema_policy,
    )


__all__ = ["normalize_scd_config", "write_dual_targets", "write_single_target"]
