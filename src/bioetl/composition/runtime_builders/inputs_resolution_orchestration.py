"""Orchestration helpers for preparing runtime runner inputs."""

from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders._runner_control_plane_data_root_policy import (
    validate_strict_data_root_policy as _validate_strict_data_root_policy,
)
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    build_runtime_config as _build_runtime_config,
    log_filter_config as _log_filter_config,
    resolve_runtime_projection as _resolve_runtime_projection,
)
from bioetl.domain.config import RuntimeConfig

from bioetl.domain.filtering import InputFilterConfig

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_runtime_models import (
        ResolvedVacuumSettings,
    )
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def validate_runner_data_root_policy(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    required_persistence_profile: str,
) -> None:
    _validate_strict_data_root_policy(
        settings=settings,
        required_profile=required_persistence_profile,
        exact_replay=bool(getattr(ctx, "exact_replay", False)),
    )


def resolve_runner_runtime_config(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    yaml_config: PipelineYamlConfig,
    observability: ObservabilityBundle,
    default_health_check_mode: Literal["strict", "probe"],
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings],
    assemble_runtime_config_fn: Callable[..., RuntimeConfig],
) -> RuntimeConfig:
    vacuum = assemble_vacuum_settings_fn(
        cli_vacuum=ctx.vacuum,
        yaml_maintenance=yaml_config.maintenance,
    )
    runtime_projection = _resolve_runtime_projection(
        ctx=ctx,
        settings=settings,
        yaml_config=yaml_config,
        observability=observability,
        default_health_check_mode=default_health_check_mode,
    )
    return _build_runtime_config(
        assemble_runtime_config_fn=assemble_runtime_config_fn,
        ctx=ctx,
        vacuum=vacuum,
        runtime_projection=runtime_projection,
    )


def resolve_runner_filter_config(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    yaml_config: PipelineYamlConfig,
    observability: ObservabilityBundle,
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None],
    adjust_batch_size_for_filter_fn: Callable[..., None],
    load_source_config_fn: Callable[..., object] | None,
) -> InputFilterConfig | None:
    filter_config = assemble_filter_config_fn(
        yaml_filter=yaml_config.input_filter,
        ctx=ctx,
        test_mode=settings.test_mode,
    )
    _log_filter_config(
        observability=observability,
        filter_config=filter_config,
        from_cli=ctx.input_filter.enabled,
    )
    adjust_batch_size_for_filter_fn(
        yaml_config=yaml_config,
        filter_config=filter_config,
        observability=observability,
        load_source_config_fn=load_source_config_fn,
    )
    return filter_config

_QUERY_OR_FILTER_PIPELINES: frozenset[str] = frozenset(
    {
        "crossref_publication",
        "openalex_publication",
        "pubchem_compound",
    }
)


class ExtractionInputError(ValueError):
    """Resolved extraction input is missing or unusable before extract/API."""


@dataclass(frozen=True, slots=True)
class ExtractionInputProvenance:
    """Non-secret provenance of the accepted extraction input."""

    pipeline_name: str
    provider: str
    input_kind: str
    source_path: str | None
    column_name: str | None
    filter_field: str | None
    id_count: int | None


def validate_resolved_extraction_input(
    *,
    pipeline_name: str,
    provider: str,
    query: str | None,
    filter_config: InputFilterConfig | None,
) -> ExtractionInputProvenance | None:
    """Validate resolved query/filter for pipelines that require an input mode.

    Returns provenance when the pipeline is in the required-input set and the
    input is usable. Returns ``None`` for pipelines that allow open full-scan.
    Raises :class:`ExtractionInputError` with an actionable reason otherwise.
    """
    if pipeline_name not in _QUERY_OR_FILTER_PIPELINES:
        return None

    normalized_query = query.strip() if isinstance(query, str) else ""
    if normalized_query:
        return ExtractionInputProvenance(
            pipeline_name=pipeline_name,
            provider=provider,
            input_kind="query",
            source_path=None,
            column_name=None,
            filter_field=None,
            id_count=None,
        )

    if filter_config is None or not filter_config.enabled:
        raise ExtractionInputError(
            f"{pipeline_name} requires either filter IDs (CSV/`--csv`/"
            f"direct IDs) or a non-empty `--query` before extract; "
            f"resolved input has neither."
        )

    if filter_config.is_direct_multi_filter:
        multi = filter_config.direct_multi_filter_ids or {}
        total = sum(len(ids) for ids in multi.values())
        if total == 0:
            raise ExtractionInputError(
                f"{pipeline_name}: direct_multi_filter_ids resolved empty; "
                f"provide non-empty ID lists or a non-empty `--query`."
            )
        return ExtractionInputProvenance(
            pipeline_name=pipeline_name,
            provider=provider,
            input_kind="direct_multi_filter_ids",
            source_path=None,
            column_name=None,
            filter_field=",".join(sorted(multi)),
            id_count=total,
        )

    if filter_config.is_direct_filter:
        ids = filter_config.direct_filter_ids or ()
        if not ids:
            raise ExtractionInputError(
                f"{pipeline_name}: direct_filter_ids resolved empty; "
                f"provide non-empty IDs or a non-empty `--query`."
            )
        return ExtractionInputProvenance(
            pipeline_name=pipeline_name,
            provider=provider,
            input_kind="direct_filter_ids",
            source_path=None,
            column_name=None,
            filter_field=filter_config.filter_field,
            id_count=len(ids),
        )

    source_path = filter_config.source_path
    if not source_path:
        raise ExtractionInputError(
            f"{pipeline_name}: input filter is enabled but source_path is "
            f"absent; provide `--csv`/`--input`, direct IDs, or `--query`."
        )

    column_name = filter_config.column_name
    if filter_config.columns and not column_name:
        column_name = filter_config.columns[0].column_name
    if not column_name:
        raise ExtractionInputError(
            f"{pipeline_name}: input filter CSV is configured without a "
            f"column_name; set column_name/filter_field or pass CLI overrides."
        )

    id_count = _peek_csv_id_count(source_path=source_path, column_name=column_name)
    return ExtractionInputProvenance(
        pipeline_name=pipeline_name,
        provider=provider,
        input_kind="csv_filter_ids",
        source_path=source_path,
        column_name=column_name,
        filter_field=filter_config.filter_field,
        id_count=id_count,
    )


def _peek_csv_id_count(*, source_path: str, column_name: str) -> int:
    """Synchronously validate CSV presence/column/non-empty IDs without network."""
    path = Path(source_path)
    if not path.is_file():
        raise ExtractionInputError(
            f"Input filter CSV is absent: {source_path}. "
            f"Create the file, pass `--csv`/`--input` to an existing path, "
            f"or provide a non-empty `--query`."
        )

    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ExtractionInputError(
                    f"Input filter CSV is empty (no header): {source_path}."
                )
            if column_name not in reader.fieldnames:
                raise ExtractionInputError(
                    f"Input filter CSV is missing required column "
                    f"{column_name!r}: {source_path}. "
                    f"Available columns: {list(reader.fieldnames)}."
                )
            count = 0
            for row in reader:
                value = (row.get(column_name) or "").strip()
                if value:
                    count += 1
            if count == 0:
                raise ExtractionInputError(
                    f"Input filter CSV column {column_name!r} has no non-empty "
                    f"IDs: {source_path}."
                )
            return count
    except OSError as exc:
        raise ExtractionInputError(
            f"Input filter CSV could not be read: {source_path} ({exc})."
        ) from exc
