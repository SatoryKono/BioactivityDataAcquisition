"""Soft RF-004/RF-003 evidence-location observation helpers."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.application.services.run_reports.observations import record_run_observation
from bioetl.domain.control_plane.run_evidence_location import (
    EvidenceLocationConflictError,
    EvidenceLocationInvalidError,
)

__all__ = [
    "EVIDENCE_LOCATION_OBSERVATION_DOMAIN",
    "EVIDENCE_LOCATION_SOFT_FAILURE_EXCEPTIONS",
    "record_registration_exception_observation",
    "record_registration_outcome_observation",
    "record_registration_soft_failure_observation",
    "record_verify_exception_observation",
    "soft_failure_exception_detail",
    "soft_invoke_evidence_location_register",
    "soft_invoke_evidence_location_verify",
]

EVIDENCE_LOCATION_OBSERVATION_DOMAIN = "Evidence Location"

_REGISTRATION_SUCCESS_CODES = frozenset({"registered", "already_identical"})

# Soft RF-004/RF-003 callbacks must not mask processing success.
EVIDENCE_LOCATION_SOFT_FAILURE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    EvidenceLocationConflictError,
    EvidenceLocationInvalidError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


def soft_failure_exception_detail(exc: BaseException) -> str:
    """Stable ``Type: message`` detail for soft-failure observations."""
    return f"{type(exc).__name__}: {exc}"


def record_registration_soft_failure_observation(
    *,
    code: str,
    detail: str | None = None,
    facts: dict[str, object] | None = None,
) -> None:
    """Publish conflict/error/exception diagnostics without mutating status.

    Success and explicit skip codes stay silent. Soft-register callers use this
    so RF-004 failures remain visible on the Evidence Location observation
    channel while processing_status stays untouched.
    """
    if code in _REGISTRATION_SUCCESS_CODES or code.startswith("skipped_"):
        return
    payload = dict(facts or {})
    if detail is not None:
        payload.setdefault("detail", detail)
    record_run_observation(
        EVIDENCE_LOCATION_OBSERVATION_DOMAIN,
        verdict="ERROR",
        reason=code,
        facts=payload,
    )


def record_verify_exception_observation(
    *,
    kind: str,
    owner: str,
    run_id: str,
    exc: BaseException,
) -> None:
    """Record finalize-time verify exceptions without mutating processing status."""
    record_registration_soft_failure_observation(
        code="verify_exception",
        detail=soft_failure_exception_detail(exc),
        facts={"kind": kind, "owner": owner, "run_id": run_id},
    )


def soft_invoke_evidence_location_verify(
    callback: Callable[[], object] | None,
    *,
    kind: str,
    owner: str,
    run_id: str,
) -> None:
    """Run finalize verify; soft-fail so processing success stays intact."""
    if callback is None:
        return
    try:
        callback()
    except EVIDENCE_LOCATION_SOFT_FAILURE_EXCEPTIONS as exc:
        record_verify_exception_observation(
            kind=kind, owner=owner, run_id=run_id, exc=exc
        )


def soft_invoke_evidence_location_register(
    callback: Callable[[], object] | None,
    *,
    kind: str,
    owner: str,
    run_id: str,
) -> None:
    """Run post-save register; soft-fail so processing success stays intact."""
    if callback is None:
        return
    try:
        outcome = callback()
    except EVIDENCE_LOCATION_SOFT_FAILURE_EXCEPTIONS as exc:
        record_registration_exception_observation(
            kind=kind, owner=owner, run_id=run_id, exc=exc
        )
        return
    if outcome is not None:
        record_registration_outcome_observation(
            outcome, kind=kind, owner=owner, run_id=run_id
        )


def record_registration_exception_observation(
    *,
    kind: str,
    exc: BaseException,
    owner: str | None = None,
    run_id: str | None = None,
) -> None:
    """Record soft-register exceptions without mutating processing status."""
    facts: dict[str, object] = {"kind": kind}
    if owner is not None:
        facts["owner"] = owner
    if run_id is not None:
        facts["run_id"] = run_id
    record_registration_soft_failure_observation(
        code="registration_exception",
        detail=soft_failure_exception_detail(exc),
        facts=facts,
    )


def record_registration_outcome_observation(
    outcome: object,
    *,
    kind: str,
    owner: str,
    run_id: str,
) -> None:
    """Surface a soft-register outcome code when the callback returns one."""
    code = getattr(outcome, "code", None)
    if not isinstance(code, str):
        return
    record_registration_soft_failure_observation(
        code=code,
        detail=getattr(outcome, "detail", None),
        facts={
            "kind": kind,
            "owner": owner,
            "run_id": run_id,
            "revision": getattr(outcome, "revision", None),
        },
    )
