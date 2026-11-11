"""Typed stage-0 survey and inspection records."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CandidateFile:
    """A repository file inspected as a possible stage-0 source."""

    relative_path: str
    select_as_source: bool


@dataclass(frozen=True, slots=True)
class ExpectedMaterial:
    """A material the stage must account for, present or absent."""

    material_id: str
    relative_path: str | None
    note: str


@dataclass(frozen=True, slots=True)
class ProvenanceClaim:
    """Three provenance elements. Any gap keeps the field unestablished."""

    field_id: str
    source_ref: str | None
    source_sha256: str | None
    rule_or_process: str | None
    confirmation_owner: str | None


@dataclass(frozen=True, slots=True)
class MCodeVersion:
    """One M-processing version pinned for stage 5."""

    version_id: str
    source_ref: str
    source_sha256: str


@dataclass(frozen=True, slots=True)
class LocalObservation:
    """A search fact that CI does not re-execute."""

    location: str
    method: str
    result: str
    ci_recheck: bool


@dataclass(frozen=True, slots=True)
class Stage0Survey:
    """Input contract for the stage-0 publisher."""

    recorded_at_utc: str
    plan_version: str
    plan_revision: str
    plan_issued_on: str
    result_owner_name: str
    result_owner_source: str
    module_executor: str | None
    gold_standard_reviewer: str | None
    candidate_files: tuple[CandidateFile, ...]
    expected_materials: tuple[ExpectedMaterial, ...]
    provenance_claims: tuple[ProvenanceClaim, ...]
    m_code_versions: tuple[MCodeVersion, ...]
    local_observations: tuple[LocalObservation, ...]


@dataclass(frozen=True, slots=True)
class FileInspection:
    """Content facts read from one path. Absence is a fact, not a PASS."""

    check_id: str
    subject: str
    exists: bool
    is_dir: bool
    is_csv: bool
    row_count: int | None
    byte_count: int | None
    sha256: str | None
    columns: tuple[str, ...]
    watched_fields: tuple[str, ...]
    selected_as_stage0_source: bool
    note: str


@dataclass(frozen=True, slots=True)
class CopiedSource:
    """Immutable stage copy of a selected original."""

    source_path: str
    copy_path: str
    sha256: str
    byte_count: int
