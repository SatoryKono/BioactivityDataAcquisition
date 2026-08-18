"""Trace identifier helpers for observability workflow dossiers."""

from __future__ import annotations


def trace_identifiers_available(tracer: object | None) -> bool:
    """Проверить доступность trace identifiers без UI handoff."""
    if tracer is None:
        return False
    return getattr(tracer, "is_noop", False) is not True


def build_trace_ids(
    *,
    run_id: str,
    diagnostics: dict[str, object],
    trace_identifiers_available: bool,
) -> list[str]:
    """Собрать trace/correlation identifiers без привязки к UI adapter."""
    composite_run_id = resolve_primary_composite_run_id(diagnostics)
    explicit_trace_ids = _explicit_trace_ids(
        diagnostics=diagnostics,
        composite_run_id=composite_run_id,
    )
    if explicit_trace_ids:
        return explicit_trace_ids
    return _generated_trace_ids(
        run_id=run_id,
        composite_run_id=composite_run_id,
        trace_identifiers_available=trace_identifiers_available,
    )


def _explicit_trace_ids(
    *,
    diagnostics: dict[str, object],
    composite_run_id: str | None,
) -> list[str]:
    explicit_trace_ids = diagnostics.get("trace_ids")
    if not isinstance(explicit_trace_ids, list):
        return []
    normalized = [
        value.strip()
        for value in explicit_trace_ids
        if isinstance(value, str) and value.strip()
    ]
    if composite_run_id is not None:
        normalized.append(composite_run_id)
    return list(dict.fromkeys(normalized))


def _generated_trace_ids(
    *,
    run_id: str,
    composite_run_id: str | None,
    trace_identifiers_available: bool,
) -> list[str]:
    generated: list[str] = []
    if trace_identifiers_available and run_id:
        generated.append(run_id)
    if composite_run_id is not None:
        generated.append(composite_run_id)
    return list(dict.fromkeys(generated))


def resolve_primary_composite_run_id(diagnostics: dict[str, object]) -> str | None:
    """Вернуть один канонический composite correlation anchor из dossier projection."""
    projection = diagnostics.get("composite_dossier_projection")
    if not isinstance(projection, dict):
        return None
    candidate = projection.get("primary_composite_run_id")
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    composite_run_ids = projection.get("composite_run_ids")
    if (
        isinstance(composite_run_ids, list)
        and len(composite_run_ids) == 1
        and isinstance(composite_run_ids[0], str)
        and composite_run_ids[0].strip()
    ):
        return composite_run_ids[0].strip()
    return None
