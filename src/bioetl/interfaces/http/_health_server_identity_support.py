"""Control-plane identity table payload helpers for the HTTP health server."""

from __future__ import annotations

from typing import cast

from bioetl.domain.control_plane import RunManifest
from bioetl.interfaces.http.control_plane_identity.checkpoint import (
    build_checkpoint_compare,
)
from bioetl.interfaces.http.control_plane_identity.extractors import (
    build_anchor_values,
    is_composite,
)

# Shared operator-facing unavailability markers for identity table rows.
IDENTITY_UNAVAILABLE_CURRENT_SCOPE = "not available for current scope"
IDENTITY_UNAVAILABLE_SELECTED_MANIFEST = "not available in selected manifest"
IDENTITY_UNAVAILABLE_SELECT_CONCRETE = "select one concrete pipeline or exact run_id"
IDENTITY_UNAVAILABLE_VALUES = frozenset(
    {
        IDENTITY_UNAVAILABLE_CURRENT_SCOPE,
        IDENTITY_UNAVAILABLE_SELECTED_MANIFEST,
        IDENTITY_UNAVAILABLE_SELECT_CONCRETE,
    }
)


def build_control_plane_identity_payload(
    *,
    requested_pipeline: str,
    resolved_manifest: object | None,
    selected_pipelines: tuple[str, ...],
    selected_run_id: str | None,
    selected_run_types: tuple[str, ...],
    resolved_via: str,
    checkpoint_metadata: dict[str, object] | None = None,
    identity_evidence_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the Grafana identity-table payload for one control-plane scope."""
    if resolved_via == "selection_required":
        return {
            "pipeline": requested_pipeline,
            "run_type": list(selected_run_types),
            "selected_run_id": selected_run_id,
            "resolved_via": resolved_via,
            "rows": [],
        }
    return {
        "pipeline": requested_pipeline,
        "run_type": list(selected_run_types),
        "selected_run_id": selected_run_id,
        "resolved_via": resolved_via,
        "rows": _build_identity_rows(
            requested_pipeline=requested_pipeline,
            resolved_manifest=resolved_manifest,
            selected_pipelines=selected_pipelines,
            selected_run_id=selected_run_id,
            checkpoint_metadata=checkpoint_metadata,
            identity_evidence_summary=identity_evidence_summary,
        ),
    }


def _build_identity_rows(
    *,
    requested_pipeline: str,
    resolved_manifest: object | None,
    selected_pipelines: tuple[str, ...],
    selected_run_id: str | None,
    checkpoint_metadata: dict[str, object] | None,
    identity_evidence_summary: dict[str, object] | None,
) -> list[dict[str, str]]:
    manifest_unavailable = (
        IDENTITY_UNAVAILABLE_SELECT_CONCRETE
        if len(selected_pipelines) != 1 and resolved_manifest is None
        else IDENTITY_UNAVAILABLE_CURRENT_SCOPE
    )
    manifest = (
        cast(RunManifest, resolved_manifest) if resolved_manifest is not None else None
    )
    values = _anchor_values(manifest, checkpoint_metadata=checkpoint_metadata)
    rows = [
        _identity_row(
            "Run ID [Pipeline]",
            values.get("run_id") or selected_run_id,
            unavailable=manifest_unavailable,
        ),
        _identity_row(
            "Manifest ID [Control Plane]",
            values.get("manifest_id"),
            unavailable=manifest_unavailable,
        ),
        _identity_row(
            "Provider.Entity [Version]",
            _provider_entity_version(
                requested_pipeline=requested_pipeline,
                values=values,
            ),
            unavailable=IDENTITY_UNAVAILABLE_CURRENT_SCOPE,
        ),
        _identity_row(
            "Contract [Schema]",
            _contract_schema(values),
            unavailable=IDENTITY_UNAVAILABLE_SELECTED_MANIFEST,
        ),
        _identity_row(
            "Execution [Type|Context|Git]",
            _execution_summary(manifest, values),
            unavailable=manifest_unavailable,
        ),
        _identity_row(
            "Resume|Dry run|Cached Bronze",
            _execution_flags(manifest),
            unavailable=manifest_unavailable,
        ),
        _identity_row(
            "Replay [Capability.Mode]",
            _replay_summary(values),
            unavailable=manifest_unavailable,
        ),
        _identity_row(
            "Checkpoint [Anchors]",
            _checkpoint_anchor_status(values, identity_evidence_summary),
            unavailable=manifest_unavailable,
        ),
    ]
    if manifest is not None and is_composite(manifest):
        rows.append(
            _identity_row(
                "Composite Run",
                values.get("composite_run_identity"),
                unavailable=IDENTITY_UNAVAILABLE_SELECTED_MANIFEST,
            )
        )
    rows.append(
        _identity_row(
            "Identity Health [Gaps]",
            _identity_health(values, identity_evidence_summary)
            if manifest is not None
            else None,
            unavailable=manifest_unavailable,
        )
    )
    rows.extend(
        _report_identity_rows(
            manifest=manifest,
            identity_evidence_summary=identity_evidence_summary,
            unavailable=manifest_unavailable,
        )
    )
    return rows


def _anchor_values(
    manifest: RunManifest | None,
    *,
    checkpoint_metadata: dict[str, object] | None = None,
) -> dict[str, object | None]:
    if manifest is None:
        return {}
    checkpoint_status = str(
        build_checkpoint_compare(
            manifest,
            checkpoint_metadata=checkpoint_metadata,
        ).get("status")
        or ""
    )
    return build_anchor_values(
        manifest,
        ledger_entries=(),
        checkpoint_status=checkpoint_status,
    )


def _provider_entity_version(
    *,
    requested_pipeline: str,
    values: dict[str, object | None],
) -> str | None:
    """Return provider.entity [version] when known; never use the pipeline selector."""
    _ = requested_pipeline
    scope = _text(values.get("provider_entity"))
    if not scope:
        return None
    version = _text(values.get("pipeline_version"))
    return f"{scope} [{version}]" if version else scope


def _contract_schema(values: dict[str, object | None]) -> str | None:
    contract_ref = _text(values.get("contract_ref"))
    contract_version = _text(values.get("contract_version"))
    schema_hash = _text(values.get("contract_schema_hash"))
    if contract_ref and contract_version:
        contract = f"{contract_ref}.{contract_version}"
    elif contract_ref:
        contract = contract_ref
    elif contract_version:
        contract = f"version={contract_version}"
    else:
        contract = ""
    if contract and schema_hash:
        return f"{contract} [{schema_hash}]"
    if contract:
        return contract
    if schema_hash:
        return f"schema={schema_hash}"
    return None


def _execution_summary(
    manifest: RunManifest | None,
    values: dict[str, object | None],
) -> str | None:
    if manifest is None:
        return None
    run_type = _text(getattr(manifest.run_type, "value", manifest.run_type))
    context = _payload_value(manifest, "execution_context")
    if not context:
        context = "composite" if is_composite(manifest) else "isolated"
    git_commit = _text(values.get("git_commit"))
    parts = [item for item in (run_type, context) if item]
    if git_commit:
        parts.append(f"git={git_commit}")
    return " | ".join(parts)


def _execution_flags(manifest: RunManifest | None) -> str | None:
    if manifest is None:
        return None
    return " | ".join(
        (
            _yes_no(_payload_value(manifest, "resume")),
            _yes_no(_payload_value(manifest, "dry_run")),
            _yes_no(_payload_value(manifest, "use_cached_bronze")),
        )
    )


def _replay_summary(values: dict[str, object | None]) -> str | None:
    if not values:
        return None
    eligible = _display_eligible(values.get("exact_replay_eligible"))
    capability = _display_capability(values.get("replay_capability"))
    mode = _display_replay_mode(values.get("replay_mode"))
    return f"{eligible} [{capability}.{mode}]"


def _checkpoint_anchor_status(
    values: dict[str, object | None],
    identity_evidence_summary: dict[str, object] | None,
) -> object | None:
    if identity_evidence_summary is not None:
        summary_status = identity_evidence_summary.get("checkpoint_anchor_status")
        if summary_status not in (None, ""):
            return summary_status
    return values.get("checkpoint_anchor_status")


def _report_identity_rows(
    *,
    manifest: RunManifest | None,
    identity_evidence_summary: dict[str, object] | None,
    unavailable: str,
) -> list[dict[str, str]]:
    """Append report/ledger identity fields (D6-IA-09) onto the compact ID table."""
    summary = identity_evidence_summary or {}
    status = _text(summary.get("run_status")) or _text(summary.get("status"))
    started_at = _text(summary.get("started_at"))
    completed_at = _text(summary.get("completed_at"))
    duration = summary.get("duration_seconds")
    coverage = _text(summary.get("tracking_coverage"))
    if duration in (None, ""):
        duration = _payload_value(manifest, "duration_seconds") if manifest else None
    return [
        _identity_row("Status", status, unavailable=unavailable),
        _identity_row("Started at", started_at, unavailable=unavailable),
        _identity_row("Completed at", completed_at, unavailable=unavailable),
        _identity_row("Duration seconds", duration, unavailable=unavailable),
        _identity_row("Tracking coverage", coverage, unavailable=unavailable),
    ]


def _identity_health(
    values: dict[str, object | None],
    identity_evidence_summary: dict[str, object] | None,
) -> str:
    if identity_evidence_summary is not None:
        gap_count = _int_or_zero(identity_evidence_summary.get("identity_gap_count"))
        complete = identity_evidence_summary.get("identity_graph_complete")
        if complete is True:
            status = "Complete"
        elif complete is False:
            status = "Incomplete"
        else:
            status = "Incomplete" if gap_count else "Unknown"
        summary = [status, f"[{gap_count} gaps]"]
        return " ".join(summary)
    gaps = values.get("correlation_anchor_gaps")
    gap_count = _gap_count(gaps)
    complete = values.get("identity_graph_complete")
    if complete is True or str(complete).strip().lower() == "complete":
        status = "Complete"
    elif complete is False or gap_count:
        status = "Incomplete"
    else:
        status = "Unknown"
    return f"{status} [{gap_count} gaps]"


def _int_or_zero(value: object | None) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, float):
        return max(int(value), 0)
    if isinstance(value, str):
        try:
            return max(int(value), 0)
        except ValueError:
            return 0
    return 0


def _payload_value(manifest: RunManifest, *keys: str) -> str | None:
    for payload in (
        manifest.runtime_config,
        manifest.launch_context,
        manifest.resolved_config,
    ):
        for key in keys:
            value = payload.get(key)
            if value not in (None, False, "", [], {}):
                return str(value)
    return None


def _yes_no(value: object | None) -> str:
    if value is True:
        return "Yes"
    if isinstance(value, str) and value.strip().lower() in {"true", "yes", "1"}:
        return "Yes"
    return "No"


def _display_eligible(value: object | None) -> str:
    if value is True:
        return "Yes"
    if isinstance(value, str) and value.strip().lower() in {"true", "yes", "1"}:
        return "Yes"
    if value is False or value is not None:
        return "No"
    return "Unknown"


def _display_capability(value: object | None) -> str:
    normalized = _normalized_token(value)
    return {
        "exact_replay_supported": "Supported",
        "resume_only": "Resume only",
        "rebuild_only": "Rebuild only",
    }.get(normalized, _title_token(normalized))


def _display_replay_mode(value: object | None) -> str:
    normalized = _normalized_token(value)
    return {
        "exact_replay": "Exact Replay",
        "replay": "Replay",
        "backfill": "Backfill",
        "rebuild": "Rebuild",
        "incremental": "Incremental",
    }.get(normalized, _title_token(normalized))


def _normalized_token(value: object | None) -> str:
    raw_value = getattr(value, "value", value)
    return str(raw_value or "unknown").strip().lower().replace("-", "_")


def _title_token(value: str) -> str:
    return value.replace("_", " ").title() if value else "Unknown"


def _gap_count(value: object | None) -> int:
    if isinstance(value, dict):
        total = 0
        for item in value.values():
            if isinstance(item, (int, float, bool)):
                total += int(item)
            elif isinstance(item, list | tuple | set | dict):
                total += len(item)
            elif item:
                total += 1
        return total
    if isinstance(value, list | tuple | set):
        return len(value)
    return 0


def _identity_row(
    parameter: str, value: object | None, *, unavailable: str
) -> dict[str, str]:
    return {"parameter": parameter, "value": _display(value, unavailable=unavailable)}


def _display(value: object | None, *, unavailable: str) -> str:
    text = _text(value)
    return unavailable if text is None else text


def _text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
