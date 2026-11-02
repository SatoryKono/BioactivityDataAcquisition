"""Atomic file adapter for run evidence location locators (RF-003).

Bounded lookup uses the exact catalog path from domain path segments —
never ``rglob`` across data roots. Register is create-if-absent /
idempotent-identical; conflicts refuse overwrite.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import override

from bioetl.domain.control_plane.run_evidence_location import (
    EVIDENCE_LOCATIONS_DIRNAME,
    EvidenceLocationConflictError,
    EvidenceLocationInvalidError,
    EvidenceLocationKind,
    EvidenceLocationLookupCode,
    EvidenceLocationLookupResult,
    EvidenceLocationRegisterOutcome,
    EvidenceLocationRegisterResult,
    RunEvidenceLocation,
    decide_register_outcome,
    evidence_location_record_segments,
    ownership_key,
    parse_run_evidence_location,
)
from bioetl.domain.ports.control_plane.run_evidence_location import (
    RunEvidenceLocationReadPort,
    RunEvidenceLocationRegisterPort,
)
from bioetl.infrastructure.control_plane._evidence_location_publish import (
    publish_bytes_if_absent,
    read_existing_bytes,
)

__all__ = ["FileEvidenceLocationStore"]


def _serialize_location(location: RunEvidenceLocation) -> bytes:
    payload = location.to_dict()
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return (text + "\n").encode("utf-8")


def _parse_location_bytes(raw: bytes) -> RunEvidenceLocation:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceLocationInvalidError(
            "evidence location bytes are not valid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise EvidenceLocationInvalidError(
            "evidence location payload must be a JSON object"
        )
    return parse_run_evidence_location(payload)


@dataclass(slots=True)
class FileEvidenceLocationStore(
    RunEvidenceLocationReadPort,
    RunEvidenceLocationRegisterPort,
):
    """File-backed evidence-location catalog under the report root."""

    report_root: Path

    def _locations_root(self) -> Path:
        return Path(self.report_root) / EVIDENCE_LOCATIONS_DIRNAME

    def _record_path(
        self,
        *,
        kind: EvidenceLocationKind | str,
        owner: str,
        run_id: str,
    ) -> Path:
        kind_seg, owner_seg, filename = evidence_location_record_segments(
            kind=kind,
            owner=owner,
            run_id=run_id,
        )
        return self._locations_root() / kind_seg / owner_seg / filename

    def _load_at(
        self,
        path: Path,
        *,
        kind: EvidenceLocationKind | str,
        owner: str,
        run_id: str,
    ) -> RunEvidenceLocation | None:
        raw = read_existing_bytes(path)
        if raw is None:
            return None
        location = _parse_location_bytes(raw)
        expected = ownership_key(kind=kind, owner=owner, run_id=run_id)
        actual = ownership_key(
            kind=location.kind, owner=location.owner, run_id=location.run_id
        )
        if expected != actual:
            raise EvidenceLocationInvalidError(
                "evidence location ownership does not match catalog path"
            )
        return location

    @override
    def get(
        self,
        *,
        kind: EvidenceLocationKind | str,
        owner: str,
        run_id: str,
    ) -> RunEvidenceLocation | None:
        """Return the locator for one ownership key, or ``None`` when missing."""
        path = self._record_path(kind=kind, owner=owner, run_id=run_id)
        return self._load_at(path, kind=kind, owner=owner, run_id=run_id)

    @override
    def lookup(
        self,
        *,
        kind: EvidenceLocationKind | str,
        owner: str,
        run_id: str,
        expected_runtime_source_id: str | None = None,
    ) -> EvidenceLocationLookupResult:
        """Classify found / missing / invalid / identity conflict without a verdict."""
        try:
            path = self._record_path(kind=kind, owner=owner, run_id=run_id)
        except EvidenceLocationInvalidError as exc:
            return EvidenceLocationLookupResult(
                code=EvidenceLocationLookupCode.LOCATION_INVALID,
                detail=str(exc),
            )
        try:
            location = self._load_at(path, kind=kind, owner=owner, run_id=run_id)
        except EvidenceLocationInvalidError as exc:
            return EvidenceLocationLookupResult(
                code=EvidenceLocationLookupCode.LOCATION_INVALID,
                detail=str(exc),
            )
        except (OSError, ValueError) as exc:
            return EvidenceLocationLookupResult(
                code=EvidenceLocationLookupCode.LOCATION_INVALID,
                detail=str(exc),
            )
        if location is None:
            return EvidenceLocationLookupResult(
                code=EvidenceLocationLookupCode.LOCATION_MISSING
            )
        if expected_runtime_source_id is not None:
            expected = str(expected_runtime_source_id).strip().lower()
            if expected != location.runtime_source_id:
                return EvidenceLocationLookupResult(
                    code=EvidenceLocationLookupCode.IDENTITY_CONFLICT,
                    location=location,
                    detail="runtime_source_mismatch",
                )
        return EvidenceLocationLookupResult(
            code=EvidenceLocationLookupCode.FOUND,
            location=location,
        )

    def _decision_for_existing(
        self,
        *,
        candidate: RunEvidenceLocation,
        path: Path,
    ) -> EvidenceLocationRegisterResult:
        raw = read_existing_bytes(path)
        if raw is None:
            return EvidenceLocationRegisterResult(
                outcome=EvidenceLocationRegisterOutcome.CONFLICT,
                location=candidate,
                detail="existing_vanished_during_register",
            )
        try:
            existing = _parse_location_bytes(raw)
        except EvidenceLocationInvalidError as exc:
            raise EvidenceLocationConflictError(
                "refusing to overwrite invalid location bytes"
            ) from exc
        decision = decide_register_outcome(candidate=candidate, existing=existing)
        if decision.outcome is EvidenceLocationRegisterOutcome.CONFLICT:
            raise EvidenceLocationConflictError(decision.detail or "binding_conflict")
        return decision

    @override
    def register(self, location: RunEvidenceLocation) -> EvidenceLocationRegisterResult:
        """Persist ``location`` when absent; no-op when identical; conflict otherwise."""
        path = self._record_path(
            kind=location.kind, owner=location.owner, run_id=location.run_id
        )
        payload = _serialize_location(location)
        created = publish_bytes_if_absent(path, payload)
        if created:
            return EvidenceLocationRegisterResult(
                outcome=EvidenceLocationRegisterOutcome.REGISTERED,
                location=location,
            )
        return self._decision_for_existing(candidate=location, path=path)
