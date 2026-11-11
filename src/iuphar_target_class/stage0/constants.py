"""Closed stage-0 vocabularies taken from issue #13008 and plan v1 r8 §7."""

from __future__ import annotations

PROVENANCE_ESTABLISHED = "установлено"
PROVENANCE_UNESTABLISHED = "не установлено"

USAGE_LEGACY = "legacy"
USAGE_CANDIDATE_ONLY = "candidate_only"

# Restrictions apply only while provenance is unestablished (plan §7 stage 0).
USAGE_LIMIT_WHEN_UNESTABLISHED: dict[str, str] = {
    "L1": USAGE_CANDIDATE_ONLY,
    "L2": USAGE_CANDIDATE_ONLY,
    "target_all": USAGE_LEGACY,
}

REQUIRED_FIELD_IDS: tuple[str, ...] = (
    "L1",
    "L2",
    "g2p_availability",
    "target_all",
)

ROLE_STATUS_ASSIGNED = "назначен"
ROLE_STATUS_UNESTABLISHED = "не установлено"

MISSING_ROLE_PARAMETERS: tuple[str, ...] = (
    "исполнитель модуля",
    "проверяющий эталонов",
)

CONTENT_ABSENT = "absent"
CONTENT_INSPECTED_NOT_SELECTED = "inspected_not_selected"
CONTENT_SELECTED = "selected_copy"

WATCHED_COLUMNS: tuple[str, ...] = (
    "G2P",
    "GtoPdb",
    "L1",
    "L2",
    "g2p",
    "gtopdb",
    "target_all",
)

RECORDED_AT_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
SHA256_PATTERN = r"^[a-f0-9]{64}$"

PROVENANCE_COLUMNS: tuple[str, ...] = (
    "field_id",
    "provenance_status",
    "source_ref",
    "source_sha256",
    "rule_or_process",
    "confirmation_owner",
    "usage_limit",
    "accepted_as_ground_truth",
)

M_CODE_COLUMNS: tuple[str, ...] = (
    "version_id",
    "source_ref",
    "source_sha256",
)

CONTENT_CHECK_COLUMNS: tuple[str, ...] = (
    "check_id",
    "subject",
    "status",
    "row_count",
    "byte_count",
    "sha256",
    "column_count",
    "watched_fields",
    "selected_as_stage0_source",
    "note",
)

ARTIFACT_NAMES: tuple[str, ...] = (
    "content_checks.csv",
    "m_code_versions.csv",
    "manifest.json",
    "provenance_map.csv",
    "stage_report.json",
)
