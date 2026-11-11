"""Expose selection provenance separately from immutable saved-run verdicts."""

from __future__ import annotations

from datetime import UTC, datetime

from bioetl.interfaces.http._selected_run_a2_resolve import is_unresolved_run_id


def with_selection_context(
    payload: dict[str, object], requested_run_id: str
) -> dict[str, object]:
    """Stamp the physical resolution once, before caching its result.

    This clock is server context resolution, not run start or browser click time.
    Cache hits retain it; changing an explicit Run ID uses a different cache key.
    """
    run_id = str(payload.get("run_id") or "-")
    automatic = is_unresolved_run_id(requested_run_id)
    mode = "AUTO · latest run in scope" if automatic else "EXPLICIT · requested Run ID"
    if automatic and is_unresolved_run_id(run_id):
        mode = (
            "NO RUN · empty scope"
            if payload.get("reason") == "no_runs_in_scope"
            else "Context unavailable"
        )
    context = {
        "context": mode,
        "run_id": run_id,
        "execution_state": payload.get("execution_state") or "UNKNOWN",
        "verdict": payload.get("verdict") or "UNKNOWN",
        "resolved_at": datetime.now(UTC).isoformat(),
    }
    return {**payload, "selection_context": [context]}
