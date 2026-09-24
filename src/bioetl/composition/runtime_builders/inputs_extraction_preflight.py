"""Preflight validation for runner extraction query/filter inputs (#10578)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.filtering import InputFilterConfig

__all__ = [
    "ExtractionInputError",
    "ExtractionInputProvenance",
    "validate_resolved_extraction_input",
]

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


def _query_provenance(
    *, pipeline_name: str, provider: str
) -> ExtractionInputProvenance:
    return ExtractionInputProvenance(
        pipeline_name=pipeline_name,
        provider=provider,
        input_kind="query",
        source_path=None,
        column_name=None,
        filter_field=None,
        id_count=None,
    )


def _filter_provenance(
    *,
    pipeline_name: str,
    provider: str,
    filter_config: InputFilterConfig,
) -> ExtractionInputProvenance:
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
        return _query_provenance(pipeline_name=pipeline_name, provider=provider)

    if filter_config is None or not filter_config.enabled:
        raise ExtractionInputError(
            f"{pipeline_name} requires either filter IDs (CSV/`--csv`/"
            f"direct IDs) or a non-empty `--query` before extract; "
            f"resolved input has neither."
        )

    return _filter_provenance(
        pipeline_name=pipeline_name,
        provider=provider,
        filter_config=filter_config,
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
