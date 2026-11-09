"""Verify the Control Plane frame contracts used by the live audit."""

from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject


def test_replay_status_panels_resolve_donor_and_explain_empty_values() -> None:
    specs = {
        spec.panel_id: spec
        for spec in audit_subject.effective_panel_specs()
        if spec.dashboard_uid == "bioetl-control-plane-v1"
    }
    for panel_id in (9422, 9423):
        spec = specs[panel_id]
        panel = audit_subject._find_panel(spec)
        target = audit_subject._select_target(panel, spec, field="url")
        assert target is not None
        assert target["url"].startswith("/ops/observability/selected-run-status?")
        assert panel["fieldConfig"]["defaults"]["noValue"] == (
            "SELECT RUN if no Run ID is selected. QUERY ERROR if the request failed."
        )


def test_control_plane_table_contracts_are_not_processed_records() -> None:
    for panel_id, contract in (
        (9408, "control_plane_identity_evidence_v1"),
        (9406, "control_plane_identity_evidence_v1"),
        (9414, "control_plane_validation_evidence_v1"),
    ):
        spec = next(
            spec
            for spec in audit_subject.REVIEWED_PANEL_SPECS
            if spec.dashboard_uid == "bioetl-control-plane-v1"
            and spec.panel_id == panel_id
        )
        assert audit_subject._classify_http_panel_payload(
            spec,
            {
                "contract": contract,
                "resolved_via": "run_id",
                "rows": [{"status": "ok"}],
            },
        )[:2] == ("ok", "nonempty_table")


def test_replay_audit_uses_projected_frames_instead_of_donor_rows() -> None:
    from bioetl.interfaces.http._selected_run_unavailable import unavailable_status

    specs = {
        spec.panel_id: spec
        for spec in audit_subject.REVIEWED_PANEL_SPECS
        if spec.dashboard_uid == "bioetl-control-plane-v1"
        and spec.panel_id in (9422, 9423)
    }
    for spec in specs.values():
        missing = unavailable_status("chembl_activity", "-", "НЕТ ЗАПУСКОВ", "empty")
        assert missing["rows"]
        assert audit_subject._classify_http_panel_payload(spec, missing)[:2] == (
            "error",
            "no_data",
        )
        failed = unavailable_status(
            "chembl_activity", "-", "QUERY ERROR", "backend error"
        )
        assert audit_subject._classify_http_panel_payload(spec, failed)[:2] == (
            "error",
            "endpoint_execution_error",
        )

    available = {"replay_readiness": [{"verdict": "READY"}], "rows": [{"domain": "dq"}]}
    assert audit_subject._classify_http_panel_payload(specs[9422], available)[:2] == (
        "ok",
        "nonempty_table",
    )
    assert audit_subject._classify_http_panel_payload(specs[9423], available)[:2] == (
        "error",
        "no_data",
    )
    available["replay_checks"] = [{"code": "identity", "result": "unknown"}]
    assert audit_subject._classify_http_panel_payload(specs[9423], available)[:2] == (
        "error",
        "no_data",
    )
    incomplete = {
        **available,
        "replay_readiness": [{"verdict": "INSUFFICIENT"}],
    }
    for spec in specs.values():
        assert audit_subject._classify_http_panel_payload(spec, incomplete)[:2] == (
            "error",
            "no_data",
        )
    available["replay_checks"] = [{"code": "identity", "result": "pass"}]
    assert audit_subject._classify_http_panel_payload(specs[9423], available)[:2] == (
        "ok",
        "nonempty_table",
    )
