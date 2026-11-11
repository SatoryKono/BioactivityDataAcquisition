"""Build the stage-0 manifest, provenance map, and content checks."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from .constants import (
    ARTIFACT_NAMES,
    CONTENT_ABSENT,
    CONTENT_CHECK_COLUMNS,
    CONTENT_CHECKS_CSV,
    CONTENT_INSPECTED_NOT_SELECTED,
    CONTENT_SELECTED,
    CRITERION_SATISFIED,
    M_CODE_COLUMNS,
    M_CODE_VERSIONS_CSV,
    MANIFEST_JSON,
    MISSING_ROLE_PARAMETERS,
    PROVENANCE_COLUMNS,
    PROVENANCE_ESTABLISHED,
    PROVENANCE_MAP_CSV,
    PROVENANCE_UNESTABLISHED,
    ROLE_STATUS_ASSIGNED,
    ROLE_STATUS_UNESTABLISHED,
    STAGE_REPORT_JSON,
    USAGE_LIMIT_WHEN_UNESTABLISHED,
    WATCHED_COLUMNS,
)
from .io import (
    atomic_write_bytes,
    blank,
    blank_int,
    canonical_csv_bytes,
    canonical_json_bytes,
    csv_bool,
    sha256_bytes,
    sha256_file,
)
from .models import (
    CopiedSource,
    FileInspection,
    ProvenanceClaim,
    Stage0Survey,
)
from .schema import ContentCheckSchema, MCodeVersionSchema, ProvenanceMapSchema
from .survey import load_survey

_BIOLOGICAL_STATEMENT = (
    "Без проверенных данных разработка на синтетических fixtures допустима, "
    "биологическая точность не принимается."
)


def publish_stage0(repo_root: Path, survey_path: Path, output_dir: Path) -> None:
    """Inspect the survey, write stage-0 artifacts, and leave originals unchanged."""
    root = repo_root.resolve()
    survey_file = survey_path.resolve()
    output = output_dir.resolve()
    if not survey_file.is_relative_to(root):
        message = "survey path escapes repo"
        raise ValueError(message)
    if not output.is_relative_to(root):
        message = "output path escapes repo"
        raise ValueError(message)
    survey_bytes = survey_file.read_bytes()
    survey = load_survey(survey_file, root=root)
    _reject_output_overlap(root, survey_file, output, survey)
    artifacts = build_artifacts(
        repo_root=root,
        survey=survey,
        survey_sha256=sha256_bytes(survey_bytes),
        output_dir=output,
    )
    output.mkdir(parents=True, exist_ok=True)
    for name in ARTIFACT_NAMES:
        atomic_write_bytes(output / name, artifacts[name], root=output)


def _reject_output_overlap(
    root: Path,
    survey_file: Path,
    output: Path,
    survey: Stage0Survey,
) -> None:
    """Refuse to publish when an artifact path is a source or the survey."""
    protected = {survey_file}
    protected.update(
        (root / item.source_ref).resolve() for item in survey.m_code_versions
    )
    for candidate in survey.candidate_files:
        protected.add((root / candidate.relative_path).resolve())
    for material in survey.expected_materials:
        if material.relative_path is not None:
            protected.add((root / material.relative_path).resolve())
    planned = {(output / name).resolve() for name in ARTIFACT_NAMES}
    for candidate in survey.candidate_files:
        source = (root / candidate.relative_path).resolve()
        if candidate.select_as_source and source.is_file():
            digest = sha256_file(source)
            planned.add((output / "copies" / f"{digest}.bin").resolve())
    overlap = sorted(path.as_posix() for path in planned & protected)
    if overlap:
        message = "output path replaces source material: " + ", ".join(overlap)
        raise ValueError(message)


def build_artifacts(
    *,
    repo_root: Path,
    survey: Stage0Survey,
    survey_sha256: str,
    output_dir: Path,
) -> dict[str, bytes]:
    """Return canonical artifact bytes without writing them."""
    _verify_m_code_sources(repo_root, survey)
    inspections = inspect_survey(repo_root, survey)
    copies = copy_selected_sources(
        repo_root=repo_root,
        survey=survey,
        inspections=inspections,
        output_dir=output_dir,
    )
    provenance_csv = _provenance_csv(survey, copies)
    m_code_csv = _m_code_csv(survey)
    content_csv = _content_csv(inspections)
    report = _stage_report(
        survey=survey,
        survey_sha256=survey_sha256,
        copies=copies,
        provenance_sha256=sha256_bytes(provenance_csv),
        m_code_sha256=sha256_bytes(m_code_csv),
        content_sha256=sha256_bytes(content_csv),
    )
    report_bytes = canonical_json_bytes(report)
    manifest = _manifest(
        survey=survey,
        survey_sha256=survey_sha256,
        copies=copies,
        provenance_sha256=sha256_bytes(provenance_csv),
        m_code_sha256=sha256_bytes(m_code_csv),
        content_sha256=sha256_bytes(content_csv),
        report_sha256=sha256_bytes(report_bytes),
    )
    return {
        CONTENT_CHECKS_CSV: content_csv,
        M_CODE_VERSIONS_CSV: m_code_csv,
        MANIFEST_JSON: canonical_json_bytes(manifest),
        PROVENANCE_MAP_CSV: provenance_csv,
        STAGE_REPORT_JSON: report_bytes,
    }


def inspect_survey(repo_root: Path, survey: Stage0Survey) -> tuple[FileInspection, ...]:
    """Read candidate files and expected materials. Missing paths stay absent."""
    seen: set[str] = set()
    inspections: list[FileInspection] = []
    for candidate in survey.candidate_files:
        if candidate.relative_path in seen:
            message = f"duplicate candidate path: {candidate.relative_path}"
            raise ValueError(message)
        seen.add(candidate.relative_path)
        inspections.append(
            _inspect_path(
                repo_root=repo_root,
                check_id=f"candidate:{candidate.relative_path}",
                subject=candidate.relative_path,
                relative_path=candidate.relative_path,
                select_as_source=candidate.select_as_source,
                note="",
            ),
        )
    for material in survey.expected_materials:
        inspections.append(
            _inspect_path(
                repo_root=repo_root,
                check_id=f"material:{material.material_id}",
                subject=material.material_id,
                relative_path=material.relative_path,
                select_as_source=False,
                note=material.note,
            ),
        )
    return tuple(sorted(inspections, key=lambda item: item.check_id))


def copy_selected_sources(
    *,
    repo_root: Path,
    survey: Stage0Survey,
    inspections: tuple[FileInspection, ...],
    output_dir: Path,
) -> tuple[CopiedSource, ...]:
    """Copy selected originals by hash. Unselected and absent files are skipped."""
    selected = {
        item.subject: item
        for item in inspections
        if item.check_id.startswith("candidate:") and item.selected_as_stage0_source
    }
    copies: list[CopiedSource] = []
    for candidate in sorted(
        survey.candidate_files, key=lambda item: item.relative_path
    ):
        inspection = selected.get(candidate.relative_path)
        if inspection is None or inspection.sha256 is None:
            continue
        source = _within_repo(repo_root, candidate.relative_path)
        before = source.read_bytes()
        copy_path = output_dir / "copies" / f"{inspection.sha256}.bin"
        atomic_write_bytes(copy_path, before, root=output_dir)
        after = source.read_bytes()
        if after != before or sha256_file(copy_path) != inspection.sha256:
            message = f"copy diverged from original: {candidate.relative_path}"
            raise RuntimeError(message)
        copies.append(
            CopiedSource(
                source_path=candidate.relative_path,
                copy_path=f"copies/{inspection.sha256}.bin",
                sha256=inspection.sha256,
                byte_count=len(before),
            ),
        )
    return tuple(copies)


def _inspect_path(
    *,
    repo_root: Path,
    check_id: str,
    subject: str,
    relative_path: str | None,
    select_as_source: bool,
    note: str,
) -> FileInspection:
    if relative_path is None:
        return _absent(check_id, subject, note)
    path = _within_repo(repo_root, relative_path)
    if not path.exists():
        extra = (
            "survey requested selection but the path is absent"
            if select_as_source
            else ""
        )
        return _absent(check_id, subject, _join_notes(note, extra))
    if path.is_dir():
        if select_as_source:
            message = f"directory cannot be a stage-0 source copy: {relative_path}"
            raise ValueError(message)
        return FileInspection(
            check_id=check_id,
            subject=subject,
            exists=True,
            is_dir=True,
            is_csv=False,
            row_count=None,
            byte_count=None,
            sha256=None,
            columns=(),
            watched_fields=(),
            selected_as_stage0_source=False,
            note=_join_notes(note, "directory; not a table"),
        )
    payload_sha = sha256_file(path)
    byte_count = path.stat().st_size
    columns: tuple[str, ...] = ()
    row_count: int | None = None
    kind_note = "not a csv table"
    is_csv = path.suffix.lower() == ".csv"
    if is_csv:
        row_count, columns = _read_csv_table(path)
        kind_note = ""
    watched = tuple(column for column in WATCHED_COLUMNS if column in columns)
    selected = bool(select_as_source and is_csv)
    status_note = "watched=" + (",".join(watched) if watched else "none")
    if select_as_source and not is_csv:
        status_note = _join_notes(status_note, "selection ignored for a non-csv file")
        selected = False
    return FileInspection(
        check_id=check_id,
        subject=subject,
        exists=True,
        is_dir=False,
        is_csv=is_csv,
        row_count=row_count,
        byte_count=byte_count,
        sha256=payload_sha,
        columns=columns,
        watched_fields=watched,
        selected_as_stage0_source=selected,
        note=_join_notes(note, kind_note, status_note),
    )


def _absent(check_id: str, subject: str, note: str) -> FileInspection:
    return FileInspection(
        check_id=check_id,
        subject=subject,
        exists=False,
        is_dir=False,
        is_csv=False,
        row_count=None,
        byte_count=None,
        sha256=None,
        columns=(),
        watched_fields=(),
        selected_as_stage0_source=False,
        note=note,
    )


def _read_csv_table(path: Path) -> tuple[int, tuple[str, ...]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header_row = next(reader, None)
        if header_row is None:
            return 0, ()
        row_count = sum(1 for _ in reader)
    return row_count, tuple(header_row)


def _provenance_csv(survey: Stage0Survey, copies: tuple[CopiedSource, ...]) -> bytes:
    copies_by_source = {item.source_path: item for item in copies}
    rows: list[dict[str, object]] = []
    for claim in sorted(survey.provenance_claims, key=lambda item: item.field_id):
        established = _claim_established(claim, copies_by_source)
        rows.append(
            {
                "field_id": claim.field_id,
                "provenance_status": (
                    PROVENANCE_ESTABLISHED if established else PROVENANCE_UNESTABLISHED
                ),
                "source_ref": claim.source_ref,
                "source_sha256": claim.source_sha256,
                "rule_or_process": claim.rule_or_process,
                "confirmation_owner": claim.confirmation_owner,
                "usage_limit": (
                    ""
                    if established
                    else USAGE_LIMIT_WHEN_UNESTABLISHED.get(claim.field_id, "")
                ),
                "accepted_as_ground_truth": established,
            },
        )
    frame = _typed_frame(rows, PROVENANCE_COLUMNS, integer_columns=())
    ProvenanceMapSchema.validate(frame)
    return canonical_csv_bytes(PROVENANCE_COLUMNS, [_csv_record(row) for row in rows])


def _claim_established(
    claim: ProvenanceClaim,
    copies_by_source: dict[str, CopiedSource],
) -> bool:
    if not (
        claim.source_ref
        and claim.source_sha256
        and claim.rule_or_process
        and claim.confirmation_owner
    ):
        return False
    copied = copies_by_source.get(claim.source_ref)
    return copied is not None and copied.sha256 == claim.source_sha256


def _verify_m_code_sources(repo_root: Path, survey: Stage0Survey) -> None:
    root = repo_root.resolve()
    for item in survey.m_code_versions:
        source = (root / item.source_ref).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            message = f"M-code source is unavailable inside root: {item.source_ref}"
            raise ValueError(message)
        if sha256_file(source) != item.source_sha256:
            message = f"M-code source SHA-256 mismatch: {item.source_ref}"
            raise ValueError(message)


def _m_code_csv(survey: Stage0Survey) -> bytes:
    rows: list[dict[str, object]] = [
        {
            "version_id": item.version_id,
            "source_ref": item.source_ref,
            "source_sha256": item.source_sha256,
        }
        for item in sorted(
            survey.m_code_versions,
            key=lambda item: (item.version_id, item.source_ref, item.source_sha256),
        )
    ]
    frame = _typed_frame(rows, M_CODE_COLUMNS, integer_columns=())
    MCodeVersionSchema.validate(frame)
    return canonical_csv_bytes(M_CODE_COLUMNS, [_csv_record(row) for row in rows])


def _content_csv(inspections: tuple[FileInspection, ...]) -> bytes:
    rows: list[dict[str, object]] = []
    for item in inspections:
        if not item.exists:
            status = CONTENT_ABSENT
        elif item.selected_as_stage0_source:
            status = CONTENT_SELECTED
        else:
            status = CONTENT_INSPECTED_NOT_SELECTED
        rows.append(
            {
                "check_id": item.check_id,
                "subject": item.subject,
                "status": status,
                "row_count": item.row_count,
                "byte_count": item.byte_count,
                "sha256": item.sha256,
                "column_count": len(item.columns) if item.is_csv else None,
                "watched_fields": ",".join(item.watched_fields)
                if item.watched_fields
                else "none",
                "selected_as_stage0_source": item.selected_as_stage0_source,
                "note": item.note,
            },
        )
    frame = _typed_frame(
        rows,
        CONTENT_CHECK_COLUMNS,
        integer_columns=("row_count", "byte_count", "column_count"),
    )
    ContentCheckSchema.validate(frame)
    return canonical_csv_bytes(
        CONTENT_CHECK_COLUMNS, [_csv_record(row) for row in rows]
    )


def _stage_report(
    *,
    survey: Stage0Survey,
    survey_sha256: str,
    copies: tuple[CopiedSource, ...],
    provenance_sha256: str,
    m_code_sha256: str,
    content_sha256: str,
) -> dict[str, object]:
    missing = _missing_role_parameters(survey)
    m_code_status = (
        PROVENANCE_ESTABLISHED if survey.m_code_versions else PROVENANCE_UNESTABLISHED
    )
    return {
        "artifact": "stage_report",
        "biological_accuracy_accepted": False,
        "criteria": [
            {
                "id": "manifest_and_provenance_published",
                "status": CRITERION_SATISFIED,
            },
            {
                "id": "unestablished_fields_restricted",
                "status": CRITERION_SATISFIED,
            },
            {
                "id": "roles_assigned_by_result_owner",
                "missing_parameters": list(missing),
                "status": "не выполнено" if missing else CRITERION_SATISFIED,
            },
            {
                "id": "biological_accuracy",
                "status": "не принимается",
            },
        ],
        "development_mode": "synthetic_fixtures_only",
        "issue": "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13008",
        "local_observations": [
            {
                "ci_recheck": item.ci_recheck,
                "location": item.location,
                "method": item.method,
                "result": item.result,
            }
            for item in sorted(
                survey.local_observations, key=lambda item: (item.location, item.method)
            )
        ],
        "m_code_version_status": m_code_status,
        "recorded_at_utc": survey.recorded_at_utc,
        "selected_source_count": len(copies),
        "stage": "0",
        "stage_status": (
            "incomplete_missing_parameters"
            if missing
            else "recorded_without_biological_acceptance"
        ),
        "statement": _BIOLOGICAL_STATEMENT,
        "survey_sha256": survey_sha256,
        "table_sha256": {
            CONTENT_CHECKS_CSV: content_sha256,
            M_CODE_VERSIONS_CSV: m_code_sha256,
            PROVENANCE_MAP_CSV: provenance_sha256,
        },
    }


def _manifest(
    *,
    survey: Stage0Survey,
    survey_sha256: str,
    copies: tuple[CopiedSource, ...],
    provenance_sha256: str,
    m_code_sha256: str,
    content_sha256: str,
    report_sha256: str,
) -> dict[str, object]:
    missing = _missing_role_parameters(survey)
    return {
        "artifact": "stage0_manifest",
        "artifact_sha256": {
            CONTENT_CHECKS_CSV: content_sha256,
            M_CODE_VERSIONS_CSV: m_code_sha256,
            PROVENANCE_MAP_CSV: provenance_sha256,
            STAGE_REPORT_JSON: report_sha256,
        },
        "biological_accuracy_accepted": False,
        "copies": [
            {
                "byte_count": item.byte_count,
                "copy_path": item.copy_path,
                "sha256": item.sha256,
                "source_path": item.source_path,
            }
            for item in copies
        ],
        "development_mode": "synthetic_fixtures_only",
        "issue": "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13008",
        "m_code_version_status": (
            PROVENANCE_ESTABLISHED
            if survey.m_code_versions
            else PROVENANCE_UNESTABLISHED
        ),
        "missing_parameters": list(missing),
        "plan": {
            "issued_on": survey.plan_issued_on,
            "revision": survey.plan_revision,
            "version": survey.plan_version,
        },
        "recorded_at_utc": survey.recorded_at_utc,
        "roles": {
            "gold_standard_reviewer": _role(
                "проверяющий эталонов",
                survey.gold_standard_reviewer,
                survey.gold_standard_reviewer_source,
            ),
            "module_executor": _role(
                "исполнитель модуля",
                survey.module_executor,
                survey.module_executor_source,
            ),
            "result_owner": _role(
                "владелец результата",
                survey.result_owner_name,
                survey.result_owner_source,
            ),
        },
        "stage": "0",
        "survey_sha256": survey_sha256,
    }


def _missing_role_parameters(survey: Stage0Survey) -> tuple[str, ...]:
    present = {
        "исполнитель модуля": survey.module_executor,
        "проверяющий эталонов": survey.gold_standard_reviewer,
    }
    return tuple(
        parameter for parameter in MISSING_ROLE_PARAMETERS if not present[parameter]
    )


def _role(parameter: str, name: str | None, source: str | None) -> dict[str, object]:
    if name:
        return {
            "name": name,
            "parameter": parameter,
            "source": source,
            "status": ROLE_STATUS_ASSIGNED,
        }
    return {
        "name": None,
        "parameter": parameter,
        "source": None,
        "status": ROLE_STATUS_UNESTABLISHED,
    }


def _typed_frame(
    rows: list[dict[str, object]],
    columns: tuple[str, ...],
    *,
    integer_columns: tuple[str, ...],
) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=list(columns))
    for column in integer_columns:
        frame[column] = pd.Series([row[column] for row in rows], dtype="Int64")
    return frame.loc[:, list(columns)]


def _csv_record(row: dict[str, object]) -> dict[str, str]:
    encoded: dict[str, str] = {}
    for key, value in row.items():
        if isinstance(value, bool):
            encoded[key] = csv_bool(value)
        elif isinstance(value, int):
            encoded[key] = blank_int(value)
        elif value is None:
            encoded[key] = ""
        else:
            encoded[key] = blank(str(value))
    return encoded


def _join_notes(*parts: str) -> str:
    return "; ".join(part for part in parts if part)


def _within_repo(repo_root: Path, relative_path: str) -> Path:
    path = (repo_root / relative_path).resolve()
    root = repo_root.resolve()
    if path != root and root not in path.parents:
        message = f"path escapes repo: {relative_path}"
        raise ValueError(message)
    return path
