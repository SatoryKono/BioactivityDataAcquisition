"""Unavailable / gap payloads for selected-run-status (SELECT RUN, empty catalog)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import cast

from bioetl.application.observability.reason_aliases import display_reason
from bioetl.application.services.control_plane.manifest.diagnostics.selected_run_replay_readiness import (
    INSUFFICIENT,
    empty_replay_readiness,
)
from bioetl.application.services.evidence_location.resolver import (
    EvidenceLocationResolver,
    EvidenceLocationResolveResult,
)
from bioetl.composition.composite_catalog import attach_contract_fields
from bioetl.domain.control_plane.run_evidence_location import EvidenceLocationKind
from bioetl.domain.run_reports.selected_status import DOMAINS, RULES_VERSION
from bioetl.domain.run_reports.stage_diagnostics import project_stage_diagnostics
from bioetl.interfaces.http._reconciliation_display import unavailable_reconciliation
from bioetl.interfaces.http._selected_run_a2_resolve import NO_RUNS_STATUS
from bioetl.interfaces.http._selected_run_presentation import (
    _readiness_fields,
    presentation_rows,
)

_NOT_EVALUATED = "NOT EVALUATED"
_QUERY_ERROR = "QUERY ERROR"
_SELECT_RUN = "SELECT RUN"
_NO_RUNS = NO_RUNS_STATUS
_GAP_STATES = frozenset({_SELECT_RUN, _NO_RUNS})


def readiness_state_for_unavailable(state: str) -> str:
    """Map gap/query states onto replay-readiness vocabulary."""
    if state in _GAP_STATES:
        return state
    if state == _QUERY_ERROR:
        return _QUERY_ERROR
    return INSUFFICIENT


def unavailable_status(
    pipeline: str, run_id: str, state: str, reason: str
) -> dict[str, object]:
    """Emit explicit state rows so unavailable evidence never becomes a green zero."""
    rows: list[dict[str, object]] = [
        {
            "domain": domain,
            "verdict": state,
            "display_verdict": state,
            "reason": reason,
            "reason_display": display_reason(reason),
            "run_id": run_id,
            "pipeline": pipeline,
            "action": (
                "No runs in current scope"
                if state == _NO_RUNS
                else "Select run or inspect evidence"
            ),
        }
        for domain in DOMAINS
    ]
    summary = {
        "pipeline": pipeline,
        "run_id": run_id,
        "verdict": state,
        "reason": reason,
        "evidence_availability": reason,
        "rules_version": RULES_VERSION,
        "execution_state": "UNKNOWN",
        "checks_verdict": "UNKNOWN",
        "evidence_completeness": "INCOMPLETE",
        "replay_readiness_now": readiness_state_for_unavailable(state),
        "heartbeat_now": _NOT_EVALUATED,
    }
    for row in rows:
        row.update({**summary, **row, "run_verdict": state})
    trust = {
        "processing_status": "UNKNOWN",
        "trust_status": state,
        "reasons_text": reason,
        "reasons_display": display_reason(reason),
        "reasons_count": None,
        "trust_reasons_action": "Not assessed",
        "evidence_observed_at": None,
    }
    presentation_summary, presentation_trust = _gap_presentation(
        state, summary, trust, pipeline
    )
    return attach_contract_fields(
        {
            **summary,
            "summary": [summary],
            "presentation_summary": [presentation_summary],
            "presentation_trust": [presentation_trust],
            "domains": rows,
            "reconciliation_display": unavailable_reconciliation(reason),
            "presentation_domains": presentation_rows(
                rows,
                selection=state == _SELECT_RUN,
                empty_catalog=state == _NO_RUNS,
            ),
            "provider_checks": [
                {
                    "provider": "—",
                    "check_result": state,
                    "evidence": reason,
                    "observed_at": None,
                }
            ],
            "provider_options": [],
            "quality_evidence": {"pipeline": pipeline, "funnel": None},
            "rows": rows,
            "trust": [trust],
            **_readiness_fields(
                empty_replay_readiness(
                    pipeline=pipeline,
                    run_id=run_id,
                    verdict=readiness_state_for_unavailable(state),
                    reason=reason,
                )
            ),
            **project_stage_diagnostics(
                None, request_state=state, request_reason=reason
            ),
        }
    )


def _gap_presentation(
    state: str,
    summary: Mapping[str, object],
    trust: Mapping[str, object],
    pipeline: str,
) -> tuple[dict[str, object], dict[str, object]]:
    if state == _SELECT_RUN:
        return (
            {
                **summary,
                "pipeline": "No run selected",
                "run_id": "—",
                "execution_state": _SELECT_RUN,
                "evidence_completeness": _SELECT_RUN,
            },
            {
                **trust,
                "processing_status": _SELECT_RUN,
                "reasons_display": "Choose a run",
            },
        )
    if state == _NO_RUNS:
        return (
            {
                **summary,
                "pipeline": pipeline if pipeline not in {"", ".*"} else "—",
                "run_id": "—",
                "execution_state": _NO_RUNS,
                "evidence_completeness": _NO_RUNS,
                "verdict": _NO_RUNS,
            },
            {
                **trust,
                "processing_status": _NO_RUNS,
                "reasons_display": "Нет запусков в выбранном скоупе",
            },
        )
    return dict(summary), dict(trust)


@dataclass(frozen=True, slots=True)
class RuntimeSourceResolver(EvidenceLocationResolver):
    """Fill in the server source id when a caller does not pass one."""

    bound_runtime_source_id: str | None = None

    def resolve(
        self,
        *,
        kind: EvidenceLocationKind | str,
        owner: str,
        run_id: str,
        expected_runtime_source_id: str | None = None,
    ) -> EvidenceLocationResolveResult:
        # slots=True rebuilds the class; zero-arg super() is a TypeError on 3.12.
        return EvidenceLocationResolver.resolve(
            self,
            kind=kind,
            owner=owner,
            run_id=run_id,
            expected_runtime_source_id=(
                self.bound_runtime_source_id
                if expected_runtime_source_id is None
                else expected_runtime_source_id
            ),
        )


def bind_runtime_source_id(
    resolver: EvidenceLocationResolver | None,
    source_id: str | None,
) -> EvidenceLocationResolver | None:
    """Return a resolver that checks ``source_id`` when the call omits one."""
    if not isinstance(resolver, EvidenceLocationResolver):
        return None
    if not isinstance(source_id, str) or not source_id.strip():
        return resolver
    return RuntimeSourceResolver(
        locations=resolver.locations,
        aliases=resolver.aliases,
        opener=resolver.opener,
        legacy_root_policy=resolver.legacy_root_policy,
        bound_runtime_source_id=source_id,
    )


_ManifestGetter = Callable[[object], object]
_ReplayVerifier = Callable[[object], object]


@dataclass(frozen=True, slots=True)
class _ContextManifestPort:
    """Adapt an open read context to the manifest-port snapshot shape."""

    _get_manifest_by_run_id: _ManifestGetter
    _verify_replay_objects: _ReplayVerifier | None

    def get_by_run_id(self, run_id: object) -> object | None:
        return self._get_manifest_by_run_id(run_id)

    def verify_replay_objects(self, manifest: object) -> object:
        verifier = self._verify_replay_objects
        if verifier is None:
            return None
        return verifier(manifest)


def resolve_selected_run(
    resolver: EvidenceLocationResolver | None,
    *,
    pipeline: str,
    run_id: str,
    expected_runtime_source_id: str | None = None,
) -> tuple[dict[str, object] | None, object | None]:
    """Return a refusal payload, or an open read context.

    ``(None, None)`` means no resolver is configured. A refusal is an error
    payload and must not fall through to the caller's report root. An open
    context is for manifest and replay only; the saved report stays on the
    caller's report root. Allowed legacy fallback already happens inside the
    resolver and arrives here with a context.
    """
    if resolver is None:
        return None, None
    try:
        resolved = resolver.resolve(
            kind="pipeline",
            owner=pipeline,
            run_id=run_id,
            expected_runtime_source_id=expected_runtime_source_id,
        )
    except (OSError, TypeError, ValueError) as exc:
        return unavailable_status(pipeline, run_id, "ERROR", str(exc)), None

    code = resolved.code.value
    context = resolved.context
    if context is None or code in {"identity_conflict", "location_invalid"}:
        return unavailable_status(pipeline, run_id, "ERROR", code), None
    return None, context


def manifest_port_for_context(
    context: object | None,
    fallback: object | None,
) -> object | None:
    """Use the resolved context's manifest when it can load one."""
    if context is None:
        return fallback
    getter = getattr(context, "get_manifest_by_run_id", None)
    if not callable(getter):
        return fallback
    verifier = getattr(context, "verify_replay_objects", None)
    return _ContextManifestPort(
        _get_manifest_by_run_id=cast(_ManifestGetter, getter),
        _verify_replay_objects=(
            cast(_ReplayVerifier, verifier) if callable(verifier) else None
        ),
    )
