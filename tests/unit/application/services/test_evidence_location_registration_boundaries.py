"""Registration diagnostics fail closed without inventing a ready locator."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

from bioetl.application.services.evidence_location import registration as subject
from bioetl.domain.control_plane.run_evidence_location import (
    EvidenceLocationLookupResult,
    EvidenceLocationRegisterResult,
)

pytestmark = pytest.mark.unit


def _request():
    return subject.EvidenceLocationRegisterRequest(
        kind=subject.EvidenceLocationKind.PIPELINE,
        owner="chembl_assay",
        run_id="fixture-run",
        runtime_source_id="a" * 64,
        relative_data_root=".",
    )


def test_invalid_request_never_reaches_registration_or_lookup():
    store = Mock()
    service = subject.EvidenceLocationRegistrationService(store)
    request = replace(_request(), relative_data_root="../escape")
    assert service.register(request).code == "invalid"
    verified = service.verify(request)
    assert (verified.code, verified.verdict) == ("invalid", "INCOMPLETE")
    store.register.assert_not_called()
    store.lookup.assert_not_called()


@pytest.mark.parametrize(
    "error,code",
    [
        (subject.EvidenceLocationConflictError("occupied"), "conflict"),
        (OSError("offline"), "error"),
        (ValueError("bad binding"), "error"),
    ],
)
def test_store_failure_is_a_diagnostic_without_published_revision(error, code):
    store = Mock()
    store.register.side_effect = error
    result = subject.EvidenceLocationRegistrationService(store).register(_request())
    assert result.code == code
    assert result.revision is None
    assert result.detail


def test_conflicting_result_retains_revision_and_default_conflict_reason():
    store = Mock()
    store.register.return_value = EvidenceLocationRegisterResult(
        outcome=subject.EvidenceLocationRegisterOutcome.CONFLICT,
        location=subject._location_from_request(_request()),
    )
    result = subject.EvidenceLocationRegistrationService(store).register(_request())
    assert result.code == "conflict" and result.detail == "binding_conflict"
    assert result.revision == subject._location_from_request(_request()).revision


@pytest.mark.parametrize(
    "code",
    [
        subject.EvidenceLocationLookupCode.LOCATION_INVALID,
        subject.EvidenceLocationLookupCode.IDENTITY_CONFLICT,
    ],
)
def test_invalid_or_foreign_lookup_never_becomes_ok(code):
    store = Mock()
    store.lookup.return_value = EvidenceLocationLookupResult(
        code=code, detail="untrusted"
    )
    result = subject.EvidenceLocationRegistrationService(store).verify(_request())
    assert result.code == code.value
    assert result.verdict == "ERROR" and result.detail == "untrusted"


def test_found_without_payload_is_incomplete_and_observed_as_such(monkeypatch):
    store = Mock()
    store.lookup.return_value = EvidenceLocationLookupResult(
        code=subject.EvidenceLocationLookupCode.FOUND
    )
    observe = Mock()
    monkeypatch.setattr(subject, "record_run_observation", observe)
    result = subject.EvidenceLocationRegistrationService(
        store
    ).record_verify_observation(_request())
    assert (result.code, result.verdict) == ("location_missing", "INCOMPLETE")
    assert observe.call_args.kwargs["verdict"] == "INCOMPLETE"
    assert observe.call_args.kwargs["facts"]["owner"] == "chembl_assay"
