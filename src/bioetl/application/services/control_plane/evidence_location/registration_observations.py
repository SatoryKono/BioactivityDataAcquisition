"""Soft diagnostic observations for Evidence Location registration."""

from __future__ import annotations

from bioetl.application.services.run_reports.observations import record_run_observation

__all__ = [
    "EVIDENCE_LOCATION_OBSERVATION_DOMAIN",
    "record_location_verify_observation",
    "record_registration_exception_observation",
    "record_registration_outcome_observation",
    "record_registration_soft_failure_observation",
    "record_verify_exception_observation",
    "soft_failure_exception_detail",
]

EVIDENCE_LOCATION_OBSERVATION_DOMAIN = "Evidence Location"
_REGISTRATION_SUCCESS_CODES = frozenset({"registered", "already_identical"})


def soft_failure_exception_detail(exc: BaseException) -> str:
    """Stable ``Type: message`` detail for soft-failure observations."""
    return f"{type(exc).__name__}: {exc}"


def record_registration_soft_failure_observation(
    *,
    code: str,
    detail: str | None = None,
    facts: dict[str, object] | None = None,
) -> None:
    """Publish conflict/error/exception diagnostics without mutating status."""
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


def record_location_verify_observation(
    *,
    verdict: str,
    code: str,
    kind: str,
    owner: str,
    run_id: str,
    workflow_run_id: str | None,
    root_alias: str,
    relative_data_root: str,
    detail: str | None,
) -> None:
    """Publish verification outcome facts without changing run status."""
    record_run_observation(
        EVIDENCE_LOCATION_OBSERVATION_DOMAIN,
        verdict=verdict,
        reason=code,
        facts={
            "kind": kind,
            "owner": owner,
            "run_id": run_id,
            "workflow_run_id": workflow_run_id,
            "root_alias": root_alias,
            "relative_data_root": relative_data_root,
            "detail": detail,
        },
    )
