"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

__all__ = [
    "_workflow_job_dependency_ids",
]


def _workflow_job_dependency_ids(job_payload: dict[str, object]) -> tuple[str, ...]:
    needs_payload = job_payload.get("needs")
    if isinstance(needs_payload, str):
        return (needs_payload,)
    if isinstance(needs_payload, list):
        return tuple(str(item) for item in needs_payload if isinstance(item, str))
    return ()
