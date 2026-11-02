# pyright: reportArgumentType=false
"""Contract tests for run evidence location value objects (RF-002 / #12680)."""

from __future__ import annotations

import pytest

from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationConflictError,
    EvidenceLocationIdentityConflictError,
    EvidenceLocationInvalidError,
    EvidenceLocationKind,
    EvidenceLocationLookupCode,
    EvidenceLocationLookupResult,
    EvidenceLocationRegisterOutcome,
    RunEvidenceLocation,
    build_run_evidence_location,
    canonicalize_relative_data_root,
    decide_register_outcome,
    ownership_key,
    parse_run_evidence_location,
)
from bioetl.domain.ports.control_plane.run_evidence_location import (
    RunEvidenceLocationReadPort,
    RunEvidenceLocationRegisterPort,
)

pytestmark = pytest.mark.unit

_SOURCE_A = "a" * 64
_SOURCE_B = "b" * 64


def _location(**overrides: object) -> RunEvidenceLocation:
    payload = {
        "kind": EvidenceLocationKind.PIPELINE,
        "owner": "chembl_assay",
        "run_id": "ac0b4e22-6a6e-5b7e-818e-106aeaf41390",
        "workflow_run_id": "3dc8ffe4-305b-5d4b-a945-fe8e78f03828",
        "runtime_source_id": _SOURCE_A,
        "root_alias": DEFAULT_EVIDENCE_ROOT_ALIAS,
        "relative_data_root": "workflow-limit100-20261102T144403Z/chembl_assay",
    }
    payload.update(overrides)
    return build_run_evidence_location(**payload)  # type: ignore[arg-type]


class _InMemoryEvidenceLocationStore:
    """Reference adapter exercising read/register port semantics in-process."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], RunEvidenceLocation] = {}
        self._invalid: set[tuple[str, str, str]] = set()

    def get(
        self,
        *,
        kind: EvidenceLocationKind | str,
        owner: str,
        run_id: str,
    ) -> RunEvidenceLocation | None:
        key = ownership_key(kind=kind, owner=owner, run_id=run_id)
        if key in self._invalid:
            raise EvidenceLocationInvalidError("corrupt location bytes")
        return self._records.get(key)

    def lookup(
        self,
        *,
        kind: EvidenceLocationKind | str,
        owner: str,
        run_id: str,
        expected_runtime_source_id: str | None = None,
    ) -> EvidenceLocationLookupResult:
        key = ownership_key(kind=kind, owner=owner, run_id=run_id)
        if key in self._invalid:
            return EvidenceLocationLookupResult(
                code=EvidenceLocationLookupCode.LOCATION_INVALID,
                detail="corrupt",
            )
        existing = self._records.get(key)
        if existing is None:
            return EvidenceLocationLookupResult(
                code=EvidenceLocationLookupCode.LOCATION_MISSING
            )
        if expected_runtime_source_id is not None:
            expected = str(expected_runtime_source_id).strip().lower()
            if expected != existing.runtime_source_id:
                return EvidenceLocationLookupResult(
                    code=EvidenceLocationLookupCode.IDENTITY_CONFLICT,
                    location=existing,
                    detail="runtime_source_mismatch",
                )
        return EvidenceLocationLookupResult(
            code=EvidenceLocationLookupCode.FOUND,
            location=existing,
        )

    def register(self, location: RunEvidenceLocation):
        key = ownership_key(
            kind=location.kind, owner=location.owner, run_id=location.run_id
        )
        if key in self._invalid:
            raise EvidenceLocationConflictError(
                "refusing to overwrite invalid location bytes"
            )
        decision = decide_register_outcome(
            candidate=location,
            existing=self._records.get(key),
        )
        if decision.outcome is EvidenceLocationRegisterOutcome.CONFLICT:
            raise EvidenceLocationConflictError(decision.detail or "binding_conflict")
        if decision.outcome is EvidenceLocationRegisterOutcome.REGISTERED:
            self._records[key] = location
        return decision

    def mark_invalid(self, location: RunEvidenceLocation) -> None:
        key = ownership_key(
            kind=location.kind, owner=location.owner, run_id=location.run_id
        )
        self._invalid.add(key)
        self._records.pop(key, None)


def test_standard_root_alias_uses_dot_relative() -> None:
    location = _location(relative_data_root="")
    assert location.relative_data_root == "."
    assert location.root_alias == DEFAULT_EVIDENCE_ROOT_ALIAS
    assert canonicalize_relative_data_root("./") == "."


@pytest.mark.parametrize(
    ("field", "value"),
    [("owner", ".."), ("owner", "."), ("run_id", ".."), ("root_alias", ".")],
)
def test_path_identity_segments_reject_dot_segments(field: str, value: str) -> None:
    with pytest.raises(EvidenceLocationInvalidError, match="safe path segment"):
        _location(**{field: value})


def test_relative_data_root_rejects_values_longer_than_schema_limit() -> None:
    with pytest.raises(EvidenceLocationInvalidError, match="512"):
        _location(relative_data_root="a" * 513)


def test_parse_roundtrip_preserves_domain_revision() -> None:
    payload = _location().to_dict()
    assert parse_run_evidence_location(payload).to_dict() == payload


@pytest.mark.parametrize("kind", ["", "unknown"])
def test_unknown_kind_uses_domain_invalid_error(kind: str) -> None:
    with pytest.raises(EvidenceLocationInvalidError, match="unsupported.*kind"):
        _location(kind=kind)


def test_parse_rejects_missing_required_relative_root() -> None:
    payload = _location().to_dict()
    del payload["relative_data_root"]
    with pytest.raises(EvidenceLocationInvalidError, match="missing required fields"):
        parse_run_evidence_location(payload)


@pytest.mark.parametrize(
    "bad",
    [
        "../escape",
        "/absolute",
        "C:/windows",
        "a/../b",
        "has space",
    ],
)
def test_relative_data_root_rejects_unsafe_paths(bad: str) -> None:
    with pytest.raises(EvidenceLocationInvalidError):
        canonicalize_relative_data_root(bad)


def test_revision_is_binding_digest_not_git_commit() -> None:
    location = _location()
    assert len(location.revision) == 64
    assert location.runtime_source_id == _SOURCE_A
    # runtime_source_id is bind identity; changing only path changes revision.
    other = _location(relative_data_root=".")
    assert other.revision != location.revision
    assert "manifest" not in location.to_dict()
    assert "verdict" not in location.to_dict()
    assert "objects" not in location.to_dict()


def test_parse_rejects_tampered_revision() -> None:
    payload = _location().to_dict()
    payload["revision"] = "0" * 64
    with pytest.raises(EvidenceLocationInvalidError, match="revision"):
        parse_run_evidence_location(payload)


def test_workflow_kind_forbids_workflow_run_id() -> None:
    with pytest.raises(EvidenceLocationInvalidError):
        _location(kind=EvidenceLocationKind.WORKFLOW, workflow_run_id="wf-1")


def test_register_idempotent_identical_and_conflict() -> None:
    store: RunEvidenceLocationRegisterPort = _InMemoryEvidenceLocationStore()
    first = _location()
    decision = store.register(first)
    assert decision.outcome is EvidenceLocationRegisterOutcome.REGISTERED
    again = store.register(_location())
    assert again.outcome is EvidenceLocationRegisterOutcome.ALREADY_IDENTICAL
    with pytest.raises(EvidenceLocationConflictError):
        store.register(_location(relative_data_root="other-root/chembl_assay"))


def test_invalid_existing_does_not_fallback_to_other_run() -> None:
    store = _InMemoryEvidenceLocationStore()
    target = _location()
    foreign = _location(run_id="ffffffff-ffff-ffff-ffff-ffffffffffff")
    store.register(foreign)
    store.mark_invalid(target)
    with pytest.raises(EvidenceLocationConflictError):
        store.register(target)
    # Foreign run remains untouched; no silent redirect.
    assert (
        store.get(kind=foreign.kind, owner=foreign.owner, run_id=foreign.run_id)
        == foreign
    )
    lookup = store.lookup(kind=target.kind, owner=target.owner, run_id=target.run_id)
    assert lookup.code is EvidenceLocationLookupCode.LOCATION_INVALID
    assert lookup.location is None


def test_lookup_codes_stay_distinct_from_replay_verdict() -> None:
    store: RunEvidenceLocationReadPort = _InMemoryEvidenceLocationStore()
    missing = store.lookup(kind="pipeline", owner="chembl_assay", run_id="missing-run")
    assert missing.code is EvidenceLocationLookupCode.LOCATION_MISSING
    assert missing.location is None
    # Manifest gap is a separate post-resolve code; never auto-substituted here.
    assert EvidenceLocationLookupCode.MANIFEST_MISSING.value == "manifest_missing"
    assert "READY" not in {code.value for code in EvidenceLocationLookupCode}
    assert "INCOMPLETE" not in {code.value for code in EvidenceLocationLookupCode}

    location = _location()
    store.register(location)  # type: ignore[attr-defined]
    conflict = store.lookup(
        kind=location.kind,
        owner=location.owner,
        run_id=location.run_id,
        expected_runtime_source_id=_SOURCE_B,
    )
    assert conflict.code is EvidenceLocationLookupCode.IDENTITY_CONFLICT
    found = store.lookup(
        kind=location.kind,
        owner=location.owner,
        run_id=location.run_id,
        expected_runtime_source_id=_SOURCE_A,
    )
    assert found.is_found
    assert found.code is EvidenceLocationLookupCode.FOUND


def test_identity_conflict_error_type_is_available_for_adapters() -> None:
    assert issubclass(EvidenceLocationIdentityConflictError, ValueError)
