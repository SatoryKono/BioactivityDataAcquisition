"""Operator-facing labels for pipeline run report Grafana tables."""

from __future__ import annotations

_REASON_OPERATOR_LABELS: dict[str, str] = {
    "gold_contract_schema_failure": "Excluded by Gold schema contract",
    "gold_contract_required_failure": "Excluded by Gold required-field contract",
    "gold_contract_reference_failure": "Excluded by Gold reference contract",
    "gold_semantic_business_exclusion": "Excluded by Gold business rule",
    "gold_semantic_profile_exclusion": "Excluded by Gold profile rule",
    "SCHEMA_VALIDATION_FAILURE": "Silver schema validation failed",
    "DQ_THRESHOLD_VIOLATION": "DQ threshold exceeded",
    "structural_policy_required_missing": "Required Silver field missing",
    "structural_policy_null_optional_forbidden": "Forbidden null in optional Silver field",
    "structural_policy_type_mismatch": "Silver type mismatch",
    "FILTERED_OUT_SILVER": "Filtered out in Silver",
    "DEDUP_KEY_COLLISION": "Deduplicated on business key",
}

_ARTIFACT_TITLES: dict[str, str] = {
    "pipeline_run_report_json": "Report JSON",
    "pipeline_run_report_md": "Readable Markdown report",
}

_ARTIFACT_ACTIONS: dict[str, str] = {
    "pipeline_run_report_json": "Download",
    "pipeline_run_report_md": "Open",
}


def _reason_operator_label(code: str) -> str:
    """Keep the machine code and add a short operator translation."""
    label = _REASON_OPERATOR_LABELS.get(code)
    if label is None:
        return code
    return f"{label} ({code})"


def _removal_code(item: dict[str, object]) -> str:
    return str(item.get("reason_code") or item.get("outcome") or "").strip()


def _prefixed_count(label: str, count: object) -> str:
    if count in (None, ""):
        return label
    return f"{count} {label}"


def _removal_label(item: object) -> str:
    if not isinstance(item, dict):
        return ""
    code = _removal_code(item)
    if not code:
        return ""
    return _prefixed_count(_reason_operator_label(code), item.get("count"))


def _join_labels(parts: list[str]) -> str:
    labeled = [part for part in parts if part]
    if not labeled:
        return "—"
    return ", ".join(labeled)


def _removals_summary(removals: object) -> str:
    """Compact funnel removals for Grafana (not raw JSON arrays)."""
    if not isinstance(removals, list):
        return "—"
    return _join_labels([_removal_label(item) for item in removals])


def _funnel_stage_row(stage: object) -> object:
    if not isinstance(stage, dict):
        return stage
    row = dict(stage)
    row["removals_summary"] = _removals_summary(stage.get("removals"))
    return row


def _shape_funnel_rows(payload: dict[str, object]) -> object:
    """Copy funnel stages and add removals_summary for table display."""
    funnel = payload.get("funnel")
    if not isinstance(funnel, list):
        return []
    return [_funnel_stage_row(stage) for stage in funnel]


def _display_fallback(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    fallback = payload.get(key)
    if isinstance(fallback, list):
        return list(fallback)
    return []


def _reason_row(item: dict[str, object]) -> dict[str, object]:
    code = str(item.get("reason_code") or "").strip()
    row = dict(item)
    row["reason_label"] = _reason_operator_label(code) if code else ""
    row["explain"] = "Open Data Quality"
    return row


def _shape_reasons_display(payload: dict[str, object]) -> list[dict[str, object]]:
    reasons = payload.get("reasons_top_n")
    if not isinstance(reasons, list) or not reasons:
        return _display_fallback(payload, "reasons_top_n_display")
    return [_reason_row(item) for item in reasons if isinstance(item, dict)]


def _artifact_kind(item: dict[str, object]) -> str:
    return str(item.get("kind") or item.get("name") or "").strip()


def _artifact_row(item: dict[str, object]) -> dict[str, object]:
    kind = _artifact_kind(item)
    row = dict(item)
    row["title"] = _ARTIFACT_TITLES.get(kind, kind or "Artifact")
    row["action"] = _ARTIFACT_ACTIONS.get(kind, "Open")
    row["format"] = kind
    return row


def _shape_artifacts_display(payload: dict[str, object]) -> list[dict[str, object]]:
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return _display_fallback(payload, "artifacts_display")
    return [_artifact_row(item) for item in artifacts if isinstance(item, dict)]
