"""Control-plane identity table payload helpers for the HTTP health server."""

from __future__ import annotations


def build_control_plane_identity_payload(
    *,
    requested_pipeline: str,
    resolved_manifest: object | None,
    selected_pipelines: tuple[str, ...],
    selected_run_id: str | None,
    selected_run_types: tuple[str, ...],
    resolved_via: str,
) -> dict[str, object]:
    """Build the Grafana identity-table payload for one control-plane scope."""
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
        ),
    }


def _build_identity_rows(
    *,
    requested_pipeline: str,
    resolved_manifest: object | None,
    selected_pipelines: tuple[str, ...],
    selected_run_id: str | None,
) -> list[dict[str, str]]:
    manifest_unavailable = (
        "select one concrete pipeline or exact run_id"
        if len(selected_pipelines) != 1 and resolved_manifest is None
        else "not available for current scope"
    )
    provenance_unavailable = "not available in selected manifest"
    code_provenance = (
        getattr(resolved_manifest, "code_provenance", None)
        if resolved_manifest is not None
        else None
    )
    return [
        _identity_row(
            "manifest_id",
            getattr(resolved_manifest, "manifest_id", None),
            unavailable=manifest_unavailable,
        ),
        _identity_row(
            "run_id",
            getattr(resolved_manifest, "run_id", None) or selected_run_id,
            unavailable=manifest_unavailable,
        ),
        _identity_row(
            "pipeline name",
            getattr(resolved_manifest, "pipeline_name", None) or requested_pipeline,
            unavailable="not available for current scope",
        ),
        _identity_row(
            "pipelineversion",
            getattr(code_provenance, "pipeline_version", None),
            unavailable=provenance_unavailable,
        ),
        _identity_row(
            "git commit hash",
            getattr(code_provenance, "git_commit", None),
            unavailable=provenance_unavailable,
        ),
        _identity_row(
            "config hash",
            getattr(code_provenance, "config_hash", None),
            unavailable=provenance_unavailable,
        ),
        _identity_row(
            "execution fingerprint",
            getattr(resolved_manifest, "execution_fingerprint", None),
            unavailable=manifest_unavailable,
        ),
        _identity_row(
            "schema contract",
            getattr(code_provenance, "contract_ref", None),
            unavailable=provenance_unavailable,
        ),
        _identity_row(
            "version",
            getattr(code_provenance, "contract_version", None),
            unavailable=provenance_unavailable,
        ),
    ]


def _identity_row(
    parameter: str,
    value: object | None,
    *,
    unavailable: str,
) -> dict[str, str]:
    return {"parameter": parameter, "value": _display(value, unavailable=unavailable)}


def _display(value: object | None, *, unavailable: str) -> str:
    if value is None:
        return unavailable
    text = str(value).strip()
    return text or unavailable
