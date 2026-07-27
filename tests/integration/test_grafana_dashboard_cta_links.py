"""Grafana dashboard CTA, runbook, and fallback link contracts."""

import json
from pathlib import Path

import pytest
from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    get_dashboard_files,
    get_dashboard_navigation_links,
    get_dashboard_panels,
    load_dashboard,
)


def _require_dashboard(name: str) -> Path:
    path = Path("grafana/dashboards") / name
    if not path.exists():
        pytest.skip(f"{name} retired in grafana simplification epic #6570/#6576")
    return path


from tests.integration._grafana_dashboard_links_support import (
    _CANONICAL_GITHUB_BLOB_PREFIX,
    _DASHBOARD_TIME_HANDOFF_TOKENS,
    _REQUIRED_LINK_VARS_BY_TARGET_UID,
    _assert_required_time_tokens,
    _extract_dashboard_uid,
    _extract_link_vars,
    _find_panel_by_id,
    _iter_panel_data_links,
    _load_dashboards_by_uid,
    _local_repo_path_from_canonical_github_blob_url,
)

pytestmark = pytest.mark.integration


def test_runtime_incident_panels_do_not_duplicate_control_plane_dashboard_link() -> (
    None
):
    """Runtime incident panels must not duplicate the top-level Control Plane link."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel_titles = {
        "Inspect Control-plane Alert Conditions",
        "Monitor No-Records Runs",
    }

    for panel_title in panel_titles:
        panel = next(
            (
                item
                for item in get_dashboard_panels(dashboard)
                if item.get("title") == panel_title
            ),
            None,
        )
        assert panel is not None, (
            f"Panel '{panel_title}' not found in bioetl-runtime.json"
        )
        data_links = panel.get("options", {}).get("dataLinks", [])
        dashboard_links = [
            link
            for link in data_links
            if _extract_dashboard_uid(str(link.get("url", "")))
            == "bioetl-control-plane-v1"
        ]
        assert not dashboard_links, (
            f"Panel '{panel_title}' must not duplicate dashboard handoff links"
        )


def test_runtime_first_screen_status_panels_expose_actionable_drilldowns() -> None:
    """Runtime current-status panels should link directly to blocker drilldowns."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panels_by_id = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("id") is not None
    }

    current_status_links = _iter_panel_data_links(panels_by_id[9100])
    current_status_urls = {
        str(link.get("title")): str(link.get("url")) for link in current_status_links
    }
    assert "viewPanel=9101" in current_status_urls["Open Runtime Blockers"]
    assert (
        "viewPanel=242" in current_status_urls["Inspect Active Runtime Blocker Detail"]
    )
    assert (
        "docs/05-operations/runbooks/observability-checklist.md"
        in current_status_urls["Open Runtime Troubleshooting Runbook"]
    )

    top_blocker_links = _iter_panel_data_links(panels_by_id[9101])
    top_blocker_urls = {
        str(link.get("title")): str(link.get("url")) for link in top_blocker_links
    }
    assert "viewPanel=242" in top_blocker_urls["Inspect Active Runtime Blocker Detail"]
    assert (
        "docs/05-operations/runbooks/observability-checklist.md"
        in top_blocker_urls["Open Runtime Troubleshooting Runbook"]
    )

    telemetry_links = _iter_panel_data_links(panels_by_id[9102])
    telemetry_urls = {
        str(link.get("title")): str(link.get("url")) for link in telemetry_links
    }
    assert telemetry_urls["Open Prometheus Targets"] == "http://localhost:9090/targets"
    prometheus_targets_link = next(
        link
        for link in telemetry_links
        if link.get("title") == "Open Prometheus Targets"
    )
    assert prometheus_targets_link.get("targetBlank") is True

    detail_links = _iter_panel_data_links(panels_by_id[242])
    detail_urls = {
        str(link.get("title")): str(link.get("url")) for link in detail_links
    }
    for link_title, expected_suffix in {
        "Open Runtime Troubleshooting Runbook": "docs/05-operations/runbooks/observability-checklist.md",
        "Open Pipeline Failure Runbook": "docs/05-operations/runbooks/pipeline-failure-critical.md",
        "Open Checkpoint Debugging Runbook": "docs/05-operations/runbooks/checkpoint-debugging.md",
        "Open Run Manifest Runbook": "docs/05-operations/runbooks/run-manifest-inspection.md",
    }.items():
        assert detail_urls[link_title].endswith(expected_suffix)


def test_runtime_alert_condition_panels_expose_direct_runbook_links() -> None:
    """Runtime condition-summary panels should route operators directly to runbooks."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expectations = {
        "Monitor Pipeline Alert Conditions": (
            "Open Pipeline Failure Runbook",
            "docs/05-operations/runbooks/pipeline-failure-critical.md",
        ),
        "Inspect DQ Alert Conditions": (
            "Open DQ Failure Runbook",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "Inspect Control-plane Alert Conditions": (
            "Open Run Manifest Runbook",
            "docs/05-operations/runbooks/run-manifest-inspection.md",
        ),
        "Inspect Provider Alert Conditions": (
            "Open Provider Incident Runbook",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "Inspect GLOBAL Provider Alert Conditions": (
            "Open Provider Incident Runbook",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "Inspect Freshness Lagged Entities >24h": (
            "Open DQ Freshness Runbook",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "Monitor No-Records Runs": (
            "Open Checkpoint Debugging Runbook",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
    }

    for panel_title, (link_title, expected_suffix) in expectations.items():
        panel = next(
            (
                item
                for item in get_dashboard_panels(dashboard)
                if item.get("title") == panel_title
            ),
            None,
        )
        assert panel is not None, (
            f"Panel '{panel_title}' not found in bioetl-runtime.json"
        )
        data_links = panel.get("options", {}).get("dataLinks", [])
        link = next(
            (item for item in data_links if item.get("title") == link_title), None
        )
        assert link is not None, (
            f"Panel '{panel_title}' must expose direct runbook handoff"
        )
        url = link.get("url", "")
        assert url.startswith(
            "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/"
        ), f"Panel '{panel_title}' runbook link must target canonical GitHub docs"
        assert url.endswith(expected_suffix), (
            f"Panel '{panel_title}' runbook link must target {expected_suffix}"
        )


def test_runtime_alert_condition_panels_expose_dashboard_handoffs() -> None:
    """Runtime condition-summary panels should route operators directly to target dashboards."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expectations = {
        "Monitor Pipeline Alert Conditions": (
            "Inspect active runtime blocker",
            "bioetl-runtime",
        ),
        "Inspect DQ Alert Conditions": (
            "Open 4. Data Quality",
            "bioetl-dq-v2",
        ),
        "Inspect Provider Alert Conditions": (
            "Open 3. Provider Health",
            "bioetl-provider-health-v2",
        ),
        "Inspect GLOBAL Provider Alert Conditions": (
            "Open 3. Provider Health",
            "bioetl-provider-health-v2",
        ),
        "Inspect Freshness Lagged Entities >24h": (
            "Open 4. Data Quality",
            "bioetl-dq-v2",
        ),
        "Monitor No-Records Runs": (
            "Inspect stage expectedness",
            "bioetl-runtime",
        ),
    }

    for panel_title, (link_title, target_uid) in expectations.items():
        panel = next(
            (
                item
                for item in get_dashboard_panels(dashboard)
                if item.get("title") == panel_title
            ),
            None,
        )
        assert panel is not None, (
            f"Panel '{panel_title}' not found in bioetl-runtime.json"
        )

        data_links = panel.get("options", {}).get("dataLinks", [])
        link = next(
            (item for item in data_links if item.get("title") == link_title), None
        )
        assert link is not None, (
            f"Panel '{panel_title}' must expose dashboard handoff '{link_title}'"
        )

        url = str(link.get("url", ""))
        assert target_uid in url, (
            f"Panel '{panel_title}' handoff must target {target_uid}"
        )
        assert "${__url_time_range}" in url, (
            f"Panel '{panel_title}' handoff must preserve time range"
        )

        required_vars = _REQUIRED_LINK_VARS_BY_TARGET_UID.get(target_uid)
        if required_vars:
            passed_vars = _extract_link_vars(url)
            missing = required_vars - passed_vars
            assert not missing, f"Missing required vars {missing} in URL {url}"


def test_provider_health_critical_panels_expose_incident_runbook_links() -> None:
    """Provider Health condition panels should point directly to incident-response runbook."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    targets = {
        9102: "Open Provider Incident Runbook",
        9103: "Open Provider Incident Runbook",
        104: "Open Provider Incident Runbook",
        106: "Open Provider Incident Runbook",
        114: "Open Provider Incident Runbook",
    }

    panels_by_id = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }
    for panel_id, expected_title in targets.items():
        panel = panels_by_id.get(panel_id)
        assert isinstance(panel, dict), f"Provider Health missing panel id={panel_id}"
        data_links = panel.get("options", {}).get("dataLinks", [])
        assert isinstance(data_links, list) and data_links, (
            f"Provider Health panel id={panel_id} must define dataLinks"
        )
        link = next(
            (item for item in data_links if item.get("title") == expected_title),
            None,
        )
        assert link is not None, (
            f"Provider Health panel id={panel_id} must expose '{expected_title}'"
        )
        url = str(link.get("url", ""))
        assert url == (
            _CANONICAL_GITHUB_BLOB_PREFIX
            + "docs/05-operations/runbooks/incident-response.md"
        ), f"Provider Health panel id={panel_id} runbook URL must be canonical"


def test_control_plane_runbook_links_target_existing_local_runbooks() -> None:
    """Control Plane runbook links must target maintained local runbooks."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    legacy_targets: list[str] = []
    missing_targets: list[str] = []
    noncanonical_targets: list[str] = []

    for panel in get_dashboard_panels(dashboard):
        panel_ref = f"id={panel.get('id')} title={panel.get('title')!r}"
        for link in _iter_panel_data_links(panel):
            url = str(link.get("url", ""))
            if "docs/05-operations/runbooks/" not in url:
                continue
            if "replay-resume.md" in url or "replay-debugging.md" in url:
                legacy_targets.append(f"{panel_ref} -> {url}")
            local_path = _local_repo_path_from_canonical_github_blob_url(url)
            if local_path is None:
                noncanonical_targets.append(f"{panel_ref} -> {url}")
                continue
            if not local_path.is_file():
                missing_targets.append(f"{panel_ref} -> {local_path}")

    assert not legacy_targets, (
        "Control Plane must retire legacy replay runbook targets:\n"
        + "\n".join(legacy_targets)
    )
    assert not noncanonical_targets, (
        "Control Plane runbook links must target canonical GitHub docs URLs:\n"
        + "\n".join(noncanonical_targets)
    )
    assert not missing_targets, (
        "Control Plane runbook links must resolve to existing local runbooks:\n"
        + "\n".join(missing_targets)
    )


def test_control_plane_replay_and_manifest_panels_route_to_expected_runbooks() -> None:
    """Control Plane replay-family and manifest-family panels must use stable runbook routing."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    expectations = {
        "Monitor: Replay Safety State": (
            "Open Checkpoint Debugging Runbook",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "Monitor: Manifest / Ledger Integrity": (
            "Open Run Manifest Inspection",
            "docs/05-operations/runbooks/run-manifest-inspection.md",
        ),
        "Track: Replay / Resume Blockers in Range": (
            "Open Checkpoint Debugging Runbook",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "Monitor: Replay Not Reconstructable": (
            "Open Checkpoint Debugging",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "Monitor: Replay Drift": (
            "Open Checkpoint Debugging",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "Track: Replay Lag Seconds": (
            "Open Checkpoint Debugging",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "Track: Replay Drift by Type": (
            "Checkpoint Debugging",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "Track: Replay Lag Trend": (
            "Checkpoint Debugging",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
    }

    for panel_title, (expected_title, expected_suffix) in expectations.items():
        panel = next(
            (
                item
                for item in get_dashboard_panels(dashboard)
                if item.get("title") == panel_title
            ),
            None,
        )
        assert panel is not None, f"Control Plane missing panel {panel_title!r}"
        links = _iter_panel_data_links(panel)
        assert links, f"Control Plane panel {panel_title!r} must expose a runbook CTA"
        titles = {str(link.get("title", "")) for link in links}
        assert expected_title in titles, (
            f"Control Plane panel {panel_title!r} must expose {expected_title!r}. "
            f"Actual titles: {sorted(titles)}"
        )
        urls = {str(link.get("url", "")) for link in links}
        assert all(url.startswith(_CANONICAL_GITHUB_BLOB_PREFIX) for url in urls), (
            f"Control Plane panel {panel_title!r} must target canonical GitHub docs"
        )
        assert any(expected_suffix in url for url in urls), (
            f"Control Plane panel {panel_title!r} must target {expected_suffix}"
        )


def test_control_plane_panels_do_not_mix_runbook_families_within_one_panel() -> None:
    """A single Control Plane panel must not expose conflicting runbook families across link surfaces."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    allowed_suffixes = (
        "docs/05-operations/runbooks/checkpoint-debugging.md",
        "docs/05-operations/runbooks/run-manifest-inspection.md",
        "docs/05-operations/runbooks/observability-checklist.md",
        "docs/05-operations/runbooks/traceability-signal-ownership.md",
    )

    for panel in get_dashboard_panels(dashboard):
        panel_ref = f"id={panel.get('id')} title={panel.get('title')!r}"
        suffixes = set()
        for link in _iter_panel_data_links(panel):
            url = str(link.get("url", ""))
            for suffix in allowed_suffixes:
                if suffix in url:
                    suffixes.add(suffix)
        assert len(suffixes) <= 1, (
            f"Control Plane panel {panel_ref} mixes multiple runbook families: "
            f"{sorted(suffixes)}"
        )


def test_control_plane_provider_health_handoff_omits_adapter_fallback() -> None:
    """Control Plane -> Provider Health handoff must let target dashboard use its own adapter fallback."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    link = next(
        (
            item
            for item in get_dashboard_navigation_links(dashboard)
            if item.get("title") == "3. Provider Health"
        ),
        None,
    )
    assert link is not None, "Control Plane must expose top-level Provider Health link"
    url = str(link.get("url", ""))
    assert "var-provider=unknown" in url
    assert "var-pipeline_context=$pipeline" in url
    assert "var-adapter=" not in url, (
        "Control Plane -> Provider Health handoff must omit adapter when source has no adapter context"
    )


def test_control_plane_first_screen_stat_panels_do_not_duplicate_runbook_ctas() -> None:
    """First-screen trust KPI panels should expose one clear runbook CTA each."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    expected_titles = {
        "Monitor: Replay Safety State",
        "Monitor: Manifest / Ledger Integrity",
    }

    for panel_title in expected_titles:
        panel = next(
            (
                item
                for item in get_dashboard_panels(dashboard)
                if item.get("title") == panel_title
            ),
            None,
        )
        assert panel is not None, f"Control Plane missing panel {panel_title!r}"
        links = _iter_panel_data_links(panel)
        assert len(links) == 1, (
            f"Control Plane first-screen panel {panel_title!r} must expose exactly one runbook CTA"
        )


def test_runtime_first_action_cta_links_preserve_scoped_vars_and_time() -> None:
    """Runtime First Action row must use explicit allowlisted vars and preserve time."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expected = {
        "Review current status": (
            "var-workflow=$workflow",
            "var-pipeline=$pipeline",
            "var-run_type=$run_type",
            "var-stage=$stage",
        ),
        "Review range evidence": (
            "var-workflow=$workflow",
            "var-pipeline=$pipeline",
            "var-run_type=$run_type",
            "var-stage=$stage",
        ),
        "Inspect top blockers": (
            "var-workflow=$workflow",
            "var-pipeline=$pipeline",
            "var-run_type=$run_type",
            "var-stage=$stage",
        ),
        "Inspect active blocker": (
            "var-workflow=$workflow",
            "var-pipeline=$pipeline",
            "var-run_type=$run_type",
            "var-stage=$stage",
        ),
    }
    forbidden = (
        "var-status=",
        "var-run_id=",
        "var-quarantine_run_id=",
        "var-payload_hash=",
    )

    panel = _find_panel_by_id(dashboard, 9991)
    assert panel is not None, "Runtime First Action panel id=9991 must exist"
    assert panel.get("title") == "First Action"
    links = panel.get("links", [])
    assert isinstance(links, list) and links, (
        "Runtime First Action panel must expose CTA links"
    )
    links_by_title = {str(link.get("title")): link for link in links}

    for title, required_tokens in expected.items():
        link = links_by_title.get(title)
        assert link is not None, f"Runtime First Action must expose CTA '{title}'"
        assert link.get("includeVars") is False, (
            f"Runtime First Action CTA '{title}' must keep includeVars=false"
        )
        url = str(link.get("url", ""))
        _assert_required_time_tokens(
            url,
            tokens=_DASHBOARD_TIME_HANDOFF_TOKENS,
            context=f"Runtime First Action CTA '{title}'",
        )
        for token in required_tokens:
            assert token in url, (
                f"Runtime First Action CTA '{title}' must include {token}"
            )
        for token in forbidden:
            assert token not in url, (
                f"Runtime First Action CTA '{title}' must not leak {token}"
            )


def test_runtime_contextual_handoffs_do_not_duplicate_top_level_dq_provider_links() -> (
    None
):
    """Runtime panel CTAs to DQ/Provider must be contextual, not duplicate nav labels."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    forbidden_panel_titles_by_target = {
        "bioetl-dq-v2": {"4. Data Quality", "Open Data Quality", "Open DQ"},
        "bioetl-provider-health-v2": {
            "3. Provider Health",
            "Open Provider Health",
            "Check Provider Health",
        },
    }

    offenders = []
    for panel in get_dashboard_panels(dashboard):
        if panel.get("id") == 1000:
            continue
        for link in _iter_panel_data_links(panel) + list(panel.get("links") or []):
            url = str(link.get("url", ""))
            target_uid = _extract_dashboard_uid(url)
            if target_uid not in forbidden_panel_titles_by_target:
                continue
            title = str(link.get("title", ""))
            if title in forbidden_panel_titles_by_target[target_uid]:
                offenders.append(f"{panel.get('id')}:{panel.get('title')}->{title}")

    assert not offenders, (
        "Runtime panel-level DQ/Provider links must encode contextual intent:\n"
        + "\n".join(offenders)
    )


def test_data_quality_lineage_handoff_panel_points_to_canonical_control_plane_row() -> (
    None
):
    """DQ lineage ownership must hand off to the canonical Control Plane row."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Review: Lineage Handoff to Control Plane"
        ),
        None,
    )
    assert panel is not None, (
        "Panel 'Review: Lineage Handoff to Control Plane' not found in bioetl-dq-v2.json"
    )
    links = list(panel.get("links") or [])
    matching_links = [
        link
        for link in links
        if _extract_dashboard_uid(str(link.get("url", ""))) == "bioetl-control-plane-v1"
    ]
    assert matching_links, "DQ lineage handoff panel must link to Control Plane"
    assert any("viewPanel=904" in str(link.get("url", "")) for link in matching_links)


def test_silver_reject_explorer_record_level_panels_do_not_use_prometheus() -> None:
    """Record-level explorer panels must use the BioETL Ops HTTP datasource."""
    dashboard = load_dashboard(pytest.skip("Silver Reject Explorer removed 2026-07-23"))
    expected_titles = {
        "Inspect Filtered Records Table",
        "Inspect Selected Record Details",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_titles
    }
    assert panels.keys() == expected_titles, (
        "Silver Reject Explorer must define both table and detail panels"
    )
    for title, panel in panels.items():
        datasource = panel.get("datasource")
        assert datasource == "BioETL Ops HTTP", (
            f"Panel {title!r} must use BioETL Ops HTTP datasource"
        )


def test_silver_reject_explorer_summary_panels_use_distinct_projections() -> None:
    """Summary trio should expose total, reject-rate view, and full scope summary separately."""
    dashboard = load_dashboard(pytest.skip("Silver Reject Explorer removed 2026-07-23"))
    panel_map = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
        in {
            "Monitor Filtered Records Total",
            "Track Reject Rate vs Bronze",
            "Inspect Run Scope Summary",
        }
    }
    assert panel_map.keys() == {
        "Monitor Filtered Records Total",
        "Track Reject Rate vs Bronze",
        "Inspect Run Scope Summary",
    }, "Silver Reject Explorer must define all three scoped summary panels"

    total_panel = panel_map["Monitor Filtered Records Total"]
    total_transformations = total_panel.get("transformations", [])
    assert total_transformations, (
        "Filtered Records Total must project only total field, not full raw payload"
    )
    total_organize = next(
        (
            transformation
            for transformation in total_transformations
            if transformation.get("id") == "organize"
        ),
        None,
    )
    assert total_organize is not None, (
        "Filtered Records Total must use organize transform to isolate total"
    )
    total_options = total_organize.get("options", {})
    assert (
        total_options.get("renameByName", {}).get("total") == "filtered_records_total"
    )
    assert total_options.get("excludeByName", {}).get("reject_ratio") is True

    ratio_panel = panel_map["Track Reject Rate vs Bronze"]
    ratio_transformations = ratio_panel.get("transformations", [])
    ratio_organize = next(
        (
            transformation
            for transformation in ratio_transformations
            if transformation.get("id") == "organize"
        ),
        None,
    )
    assert ratio_organize is not None, (
        "Reject Rate vs Bronze must use organize transform for ratio/bronze/total view"
    )
    ratio_options = ratio_organize.get("options", {})
    assert ratio_options.get("renameByName", {}).get("reject_ratio") == (
        "reject_rate_vs_bronze"
    )
    assert ratio_options.get("excludeByName", {}).get("by_reason_code") is True

    ratio_overrides = ratio_panel.get("fieldConfig", {}).get("overrides", [])
    assert any(
        override.get("matcher", {}).get("options") == "reject_ratio"
        and any(prop.get("id") == "unit" for prop in override.get("properties", []))
        for override in ratio_overrides
        if isinstance(override, dict)
    ), "Reject Rate vs Bronze must format reject_ratio as percentage"

    summary_panel = panel_map["Inspect Run Scope Summary"]
    assert not summary_panel.get("transformations"), (
        "Run Scope Summary must remain full payload panel for forensic context"
    )


def test_silver_reject_explorer_selected_record_details_uses_safe_payload_filter() -> (
    None
):
    """Selected Record Details should not depend on path-bound payload hash."""
    dashboard = load_dashboard(pytest.skip("Silver Reject Explorer removed 2026-07-23"))
    panel = next(
        (
            candidate
            for candidate in get_dashboard_panels(dashboard)
            if candidate.get("title") == "Inspect Selected Record Details"
        ),
        None,
    )
    assert panel is not None, (
        "Silver Reject Explorer must include Selected Record Details"
    )

    targets = panel.get("targets", [])
    assert targets, "Selected Record Details must define at least one query target"
    target = targets[0]
    url = target.get("url", "")
    assert isinstance(url, str), "Selected Record Details query URL must be a string"
    assert "/ops/quarantine/filtered-records" in url, (
        "Selected Record Details must query list endpoint to avoid hard failure "
        "when payload_hash is blank"
    )
    assert "/ops/quarantine/filtered-record/${payload_hash}" not in url, (
        "Selected Record Details must not use strict path payload hash endpoint"
    )
    assert "payload_hash=${payload_hash}" in url, (
        "Selected Record Details must filter by payload_hash via query parameter"
    )
    assert target.get("root_selector") == "items", (
        "Selected Record Details must parse list payload via items root selector"
    )


def test_control_plane_dashboard_does_not_expose_top_level_runbook_link() -> None:
    """Top navigation may expose only dashboard bus and canonical Explore links."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    allowed_prefixes = (
        "/d/",
        "/a/grafana-lokiexplore-app/",
        "/a/grafana-exploretraces-app/",
    )
    navigation_urls = [
        str(link.get("url", "")) for link in get_dashboard_navigation_links(dashboard)
    ]
    unexpected_urls = [
        url for url in navigation_urls if not url.startswith(allowed_prefixes)
    ]
    assert not unexpected_urls, (
        "Control-plane top navigation must not mix dashboard bus/Explore adjuncts "
        f"with runbooks or docs: {unexpected_urls}"
    )


def test_all_runbook_links_use_canonical_github_urls_and_resolve_locally() -> None:
    """Shipped runbook CTAs must use canonical GitHub blob URLs to existing docs."""
    missing_targets: list[str] = []
    noncanonical_targets: list[str] = []
    observed = 0

    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for link in _collect_dashboard_links(dashboard):
            if not isinstance(link, dict):
                continue
            url = str(link.get("url", ""))
            if "docs/05-operations/runbooks/" not in url:
                continue
            observed += 1
            local_path = _local_repo_path_from_canonical_github_blob_url(url)
            if local_path is None:
                noncanonical_targets.append(f"{dashboard_path.name} -> {url}")
                continue
            if not local_path.is_file():
                missing_targets.append(f"{dashboard_path.name} -> {local_path}")

    assert observed > 0, "Shipped dashboards must expose at least one runbook CTA"
    assert not noncanonical_targets, (
        "Runbook CTAs must target canonical GitHub blob URLs:\n"
        + "\n".join(noncanonical_targets)
    )
    assert not missing_targets, (
        "Runbook CTAs must resolve to existing local docs:\n"
        + "\n".join(missing_targets)
    )


def test_overview_panels_use_dashboard_handoffs_not_runbook_ctas() -> None:
    """Overview remains dashboard-routing-first rather than runbook-first."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    offenders: list[str] = []

    for panel in get_dashboard_panels(dashboard):
        for link in _iter_panel_data_links(panel):
            url = str(link.get("url", ""))
            if "docs/05-operations/runbooks/" in url:
                offenders.append(
                    f"id={panel.get('id')} title={panel.get('title')!r} -> {url}"
                )

    assert not offenders, (
        "Overview panel-level CTAs must stay dashboard-routing-first:\n"
        + "\n".join(offenders)
    )


def test_workflow_range_cards_do_not_ship_panel_level_runbook_links() -> None:
    """Workflow selected-range cards should hand off via First Action instead."""
    dashboard = load_dashboard(_require_dashboard("bioetl-workflow-overview.json"))
    expected_titles = {
        "Failed Workflow Runs / Range",
        "Failed Pipeline Steps / Range",
        "Failed Transform Steps / Range",
        "Skipped Step Events / Range",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_titles
    }
    assert set(panels) == expected_titles

    offenders: list[str] = []
    for title, panel in panels.items():
        for link in _iter_panel_data_links(panel):
            offenders.append(f"{title} -> {link.get('title')} -> {link.get('url')}")

    assert not offenders, (
        "Workflow selected-range summary cards must stay free of panel-level CTAs; "
        "handoff belongs to First Action:\n" + "\n".join(offenders)
    )

    next_panel = next(
        (
            panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title") == "First Action"
        ),
        None,
    )
    assert next_panel is not None
    next_links = _iter_panel_data_links(next_panel)
    assert next_links, "Workflow First Action must keep dashboard handoffs"
    assert all(str(link.get("url", "")).startswith("/d/") for link in next_links), (
        "Workflow First Action must stay dashboard-handoff-only"
    )


def test_design_system_documents_role_based_runbook_cta_policy() -> None:
    """Design-system must describe runbook CTA coverage as role-based policy."""
    text = Path("docs/03-guides/dashboards/design-system.md").read_text(
        encoding="utf-8"
    )
    required_tokens = {
        "Role-based runbook CTA policy",
        "`bioetl-overview-v2` является dashboard-routing-first surface",
        "`bioetl-workflow-overview` является selected-range evidence surface",
        "runbook CTA управляется ролью dashboard-а",
        "canonical GitHub blob pattern",
    }
    missing = sorted(token for token in required_tokens if token not in text)
    assert not missing, (
        f"design-system must document role-based runbook CTA policy; missing={missing}"
    )


def test_cross_dashboard_links_enforce_required_handoff_or_explicit_fallback() -> None:
    """Top-level links must pass required target vars or rely on explicit fallback."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)

        for link in get_dashboard_navigation_links(dashboard):
            url = link.get("url", "")
            if not isinstance(url, str) or not url.startswith("/d/"):
                continue

            target_uid = _extract_dashboard_uid(url)
            assert target_uid is not None, f"Could not parse dashboard UID from {url}"

            required_vars = _REQUIRED_LINK_VARS_BY_TARGET_UID.get(target_uid)
            assert required_vars is not None, (
                f"Link target {target_uid} must be declared in required vars map"
            )
            passed_vars = _extract_link_vars(url)

            source_vars = {
                var.get("name")
                for var in dashboard.get("templating", {}).get("list", [])
                if var.get("name")
            }
            required_from_source = {var for var in required_vars if var in source_vars}
            missing = required_from_source - passed_vars
            assert not missing, (
                f"{dashboard_path.name} top-level link to {target_uid} must pass available "
                f"required vars {sorted(missing)}. URL: {url}"
            )


def test_provider_dashboard_exposes_single_runtime_link() -> None:
    """Provider Health must not duplicate Runtime handoffs."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    links = get_dashboard_navigation_links(dashboard)

    runtime_links = [
        link
        for link in links
        if _extract_dashboard_uid(str(link.get("url", ""))) == "bioetl-runtime"
    ]
    assert len(runtime_links) == 1


def test_workflow_overview_first_action_cta_contract() -> None:
    """Workflow First Action panel must have exactly 5 dashboard handoffs."""
    dashboard = load_dashboard(_require_dashboard("bioetl-workflow-overview.json"))
    next_diagnostic_panel = next(
        (
            p
            for p in get_dashboard_panels(dashboard)
            if p.get("title") == "First Action"
        ),
        None,
    )
    assert next_diagnostic_panel is not None, (
        "Workflow Overview missing First Action panel"
    )
    options = next_diagnostic_panel.get("options", {})
    links = options.get("dataLinks", [])
    assert isinstance(links, list), "First Action panel must have dataLinks list"
    assert len(links) == 5, (
        f"First Action panel must have exactly 5 CTAs, got {len(links)}"
    )
    expected_targets = [
        "bioetl-runtime",
        "bioetl-dq-v2",
        "bioetl-provider-health-v2",
        "bioetl-control-plane-v1",
        "bioetl-overview-v2",
    ]
    for link in links:
        url = link.get("url", "")
        assert isinstance(url, str), "Link URL must be a string"
        assert any(target in url for target in expected_targets), (
            f"Link must target one of {expected_targets}, got {url}"
        )


def test_dashboard_links_do_not_default_run_type_to_unknown() -> None:
    """Missing run-type context must use Run Type=All, never unknown."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        links_json = json.dumps(get_dashboard_navigation_links(dashboard))
        assert "var-run_type=unknown" not in links_json, (
            f"{dashboard_path.name} must not link with Run Type=unknown"
        )


def test_run_type_variables_default_to_all_not_unknown() -> None:
    """Run Type dashboard variables must default to All."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        variables = dashboard.get("templating", {}).get("list", [])
        assert isinstance(variables, list)

        for variable in variables:
            if not isinstance(variable, dict) or variable.get("name") != "run_type":
                continue
            current = variable.get("current", {})
            assert current.get("text") == "All", (
                f"{dashboard_path.name} run_type current text must be All"
            )
            assert current.get("value") == "$__all", (
                f"{dashboard_path.name} run_type current value must be $__all"
            )


def test_pipeline_and_provider_variables_are_single_select_unknown_default() -> None:
    """Pipeline and Provider selectors must be single-value fail-closed scopes."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        variables = {
            var.get("name"): var
            for var in dashboard.get("templating", {}).get("list", [])
            if isinstance(var, dict) and var.get("name")
        }
        for variable_name in ("pipeline", "provider"):
            variable = variables.get(variable_name)
            if variable is None:
                continue
            assert variable.get("multi") is False, (
                f"{dashboard_path.name} '{variable_name}' must be single-select"
            )
            current = variable.get("current", {})
            assert isinstance(current, dict)
            if (
                dashboard_path.name == "bioetl-overview-v2.json"
                and variable_name == "pipeline"
            ):
                assert variable.get("includeAll") is True, (
                    f"{dashboard_path.name} 'pipeline' must default to All so "
                    "the overview landing page renders a meaningful scope"
                )
                assert current.get("value") == "$__all", (
                    f"{dashboard_path.name} 'pipeline' must default to All"
                )
                continue
            assert variable.get("includeAll") is False, (
                f"{dashboard_path.name} '{variable_name}' must disable All"
            )
            assert current.get("value") == "unknown", (
                f"{dashboard_path.name} '{variable_name}' must default to unknown"
            )


def test_provider_health_handoff_fail_closes_and_remembers_return_context() -> None:
    """Pipeline-scoped dashboards preserve pipeline_context and fail-close provider scope."""
    pipeline_sources = {
        "bioetl-control-plane-v1",
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-dq-v2",
    }
    dashboards = _load_dashboards_by_uid()

    for source_uid in pipeline_sources:
        dashboard = dashboards[source_uid]
        link = next(
            item
            for item in get_dashboard_navigation_links(dashboard)
            if _extract_dashboard_uid(str(item.get("url", "")))
            == "bioetl-provider-health-v2"
        )
        url = str(link.get("url", ""))
        tooltip = str(link.get("tooltip", ""))
        assert "var-provider=unknown" in url
        assert "var-pipeline_context=$pipeline" in url
        assert "var-provider=All" not in url
        assert "Context mapping" in tooltip
        assert "provider=unknown" in tooltip

    provider_dashboard = dashboards["bioetl-provider-health-v2"]
    provider_vars = {
        var.get("name"): var
        for var in provider_dashboard.get("templating", {}).get("list", [])
        if isinstance(var, dict)
    }
    pipeline_context = provider_vars.get("pipeline_context")
    assert pipeline_context is not None
    assert pipeline_context.get("hide") == 2
    assert pipeline_context.get("current", {}).get("value") == "unknown"

    for target_uid in {
        "bioetl-control-plane-v1",
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-dq-v2",
    }:
        link = next(
            item
            for item in get_dashboard_navigation_links(provider_dashboard)
            if _extract_dashboard_uid(str(item.get("url", ""))) == target_uid
        )
        url = str(link.get("url", ""))
        assert "var-pipeline=$pipeline_context" in url
        assert "var-pipeline=All" not in url


def test_dashboard_links_do_not_use_all_for_pipeline_or_provider() -> None:
    """Unknown is the only explicit fallback for Pipeline/Provider handoff values."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for link in _collect_dashboard_links(dashboard):
            url = str(link.get("url", ""))
            assert "var-pipeline=All" not in url
            assert "var-provider=All" not in url


def test_provider_health_first_action_cta_contract() -> None:
    """bioetl-provider-health-v2 First Action panel (9002) must have exactly 3 CTAs."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panels_by_id = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("id") is not None
    }

    first_action_panel = panels_by_id[9002]
    links = first_action_panel.get("links", [])

    assert len(links) == 3, (
        f"Provider Health First Action panel must have exactly 3 CTAs, got {len(links)}"
    )

    link_titles = {link.get("title") for link in links}
    required_titles = {
        "Review severity matrix",
        "Inspect critical providers",
        "Inspect provider top causes",
    }
    assert required_titles.issubset(link_titles), (
        f"Provider Health First Action panel missing required CTAs. "
        f"Required: {required_titles}, Got: {link_titles}"
    )


def test_dq_first_action_cta_contract() -> None:
    """bioetl-dq-v2 First Action panel (9103) after Silver Reject Explorer removal."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panels_by_id = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("id") is not None
    }

    first_action_panel = panels_by_id[9103]
    links = first_action_panel.get("links", [])

    assert len(links) == 2, (
        f"DQ First Action panel must have exactly 2 CTAs, got {len(links)}"
    )

    link_titles = {link.get("title") for link in links}
    required_titles = {
        "Review current status",
        "Inspect current reasons",
    }
    assert required_titles.issubset(link_titles), (
        f"DQ First Action panel missing required CTAs. "
        f"Required: {required_titles}, Got: {link_titles}"
    )


def test_silver_reject_explorer_first_action_cta_contract() -> None:
    dashboard = load_dashboard(pytest.skip("Silver Reject Explorer removed 2026-07-23"))
    panels_by_id = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("id") is not None
    }

    first_action_panel = panels_by_id[10]
    links = first_action_panel.get("links", [])

    assert len(links) == 2, (
        f"Silver Reject Explorer First Action panel must have exactly 2 CTAs, got {len(links)}"
    )

    link_titles = {link.get("title") for link in links}
    required_titles = {
        "Review total rejects",
        "Review scoped summary",
    }
    assert required_titles.issubset(link_titles), (
        f"Silver Reject Explorer First Action panel missing required CTAs. "
        f"Required: {required_titles}, Got: {link_titles}"
    )
