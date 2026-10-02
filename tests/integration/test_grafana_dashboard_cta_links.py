# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Grafana dashboard CTA, runbook, and fallback link contracts."""

import json
import re
from pathlib import Path

import pytest
from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    get_dashboard_files,
    get_dashboard_navigation_links,
    get_dashboard_panels,
    load_dashboard,
    panel_display_title,
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
    _local_repo_path_from_canonical_github_blob_url,
)

pytestmark = pytest.mark.integration


def test_runtime_incident_panels_do_not_duplicate_control_plane_dashboard_link() -> (
    None
):
    """Runtime incident panels must not duplicate the top-level Control Plane link."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    panel_titles = {
        "Inspect Control Plane Alerts",
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
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    panels_by_id = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("id") is not None
    }

    # Headline Status card owns first-screen drilldowns after Runtime Status → Status.
    current_status_links = _iter_panel_data_links(panels_by_id[18940])
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
    # B3: local Prometheus /targets is not useful outside the host; omit it.
    assert "Open Prometheus Targets" not in telemetry_urls
    assert all("localhost:9090" not in url for url in telemetry_urls.values())

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
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    expectations = {
        "Monitor Pipeline Alerts": (
            "Open Pipeline Failure Runbook",
            "docs/05-operations/runbooks/pipeline-failure-critical.md",
        ),
        "Inspect DQ Alert Conditions": (
            "Open DQ Failure Runbook",
            "docs/05-operations/runbooks/pipeline-failure-dq.md",
        ),
        "Inspect Control Plane Alerts": (
            "Open Run Manifest Runbook",
            "docs/05-operations/runbooks/run-manifest-inspection.md",
        ),
        "Inspect Provider Alerts": (
            "Open Provider Incident Runbook",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "Inspect Global Provider Alert Conditions": (
            "Open Provider Incident Runbook",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "Inspect Entities Stale Over 24h": (
            "Open DQ Freshness Runbook",
            "docs/05-operations/runbooks/pipeline-failure-dq.md",
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
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    expectations = {
        "Monitor Pipeline Alerts": (
            "Inspect active runtime blocker",
            "bioetl-incident-v1",
        ),
        "Inspect DQ Alert Conditions": (
            "Open Data Quality",
            "bioetl-dq-v2",
        ),
        "Inspect Provider Alerts": (
            "Open Provider Evidence",
            "bioetl-overview-v2",
        ),
        "Inspect Global Provider Alert Conditions": (
            "Open Provider Evidence",
            "bioetl-overview-v2",
        ),
        "Inspect Entities Stale Over 24h": (
            "Open Data Quality",
            "bioetl-dq-v2",
        ),
        "Monitor No-Records Runs": (
            "Inspect stage expectedness",
            "bioetl-incident-v1",
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
    """Live provider conditions retain the incident-response runbook on Incident."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    for panel_id in (6, 259):
        panel = _find_panel_by_id(dashboard, panel_id)
        links = _iter_panel_data_links(panel)
        link = next(
            candidate
            for candidate in links
            if candidate["title"] == "Open Provider Incident Runbook"
        )
        assert (
            link["url"]
            == _CANONICAL_GITHUB_BLOB_PREFIX
            + "docs/05-operations/runbooks/incident-response.md"
        )
    saved = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    assert not any(
        "runbooks" in str(candidate.get("url"))
        for pid in (9480, 9481)
        for candidate in _iter_panel_data_links(_find_panel_by_id(saved, pid))
    )


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
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    expectations = {
        "Monitor Replay": (
            "Open Checkpoint Debugging Runbook",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "Monitor Ledger": (
            "Open Run Manifest Inspection",
            "docs/05-operations/runbooks/run-manifest-inspection.md",
        ),
        "Track Replay Blockers": (
            "Open Checkpoint Debugging Runbook",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "Track Unreconstructable": (
            "Open Checkpoint Debugging",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "Track Replay Drift": (
            "Open Checkpoint Debugging",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "Track Peak Replay Lag": (
            "Open Checkpoint Debugging",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "Track Replay Drift by Type": (
            "Checkpoint Debugging",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "Track Replay Lag": (
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
    control = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    assert all(
        "bioetl-provider-health-v2" not in str(candidate)
        for candidate in _collect_dashboard_links(control)
    )
    overview = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    link = next(
        candidate
        for candidate in _find_panel_by_id(overview, 9002)["links"]
        if candidate["title"] == "Open Provider Evidence"
    )
    assert "viewPanel=9480" in link["url"]
    assert _extract_dashboard_uid(link["url"]) == "bioetl-overview-v2"
    assert not {"provider", "adapter", "pipeline_context"} & _extract_link_vars(
        link["url"]
    )
    assert "${run_id:queryparam}" in link["url"]


def test_control_plane_first_screen_stat_panels_do_not_duplicate_runbook_ctas() -> None:
    """First-screen trust KPI panels should expose one clear runbook CTA each."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    expected_titles = {
        "Monitor Replay",
        "Monitor Ledger",
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
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    expected = {
        "Review current status": (
            "${workflow:queryparam}",
            "${pipeline:queryparam}",
            "${run_type:queryparam}",
        ),
        "Review range evidence": (
            "${workflow:queryparam}",
            "${pipeline:queryparam}",
            "${run_type:queryparam}",
        ),
        "Inspect top blockers": (
            "${workflow:queryparam}",
            "${pipeline:queryparam}",
            "${run_type:queryparam}",
        ),
        "Inspect active blocker": (
            "${workflow:queryparam}",
            "${pipeline:queryparam}",
            "${run_type:queryparam}",
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
    assert panel_display_title(panel) == "Start Pipeline Triage"
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
    """DQ and provider evidence are contextual actions, absent from the visible bus."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    nav = get_dashboard_navigation_links(dashboard)
    assert all(
        _extract_dashboard_uid(candidate["url"]) != "bioetl-dq-v2" for candidate in nav
    )
    for pid in (4, 7):
        link = next(
            candidate
            for candidate in _iter_panel_data_links(_find_panel_by_id(dashboard, pid))
            if candidate["title"] == "Open Data Quality"
        )
        assert _extract_dashboard_uid(link["url"]) == "bioetl-dq-v2"
        assert "var-stage=$__all" in link["url"]
        assert "${run_id:queryparam}" in link["url"]
        assert "${__url_time_range}" in link["url"]
    for pid in (6, 259):
        link = next(
            candidate
            for candidate in _iter_panel_data_links(_find_panel_by_id(dashboard, pid))
            if candidate["title"] == "Open Provider Evidence"
        )
        assert "viewPanel=9480" in link["url"]
        assert "do not prove" in link["tooltip"]


def test_data_quality_lineage_handoff_panel_points_to_canonical_control_plane_row() -> (
    None
):
    dq = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    links = get_dashboard_navigation_links(dq)
    link = next(
        candidate
        for candidate in links
        if _extract_dashboard_uid(candidate["url"]) == "bioetl-control-plane-v1"
    )
    assert "${run_id:queryparam}" in link["url"]
    assert "${__url_time_range}" in link["url"]
    control = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    row = _find_panel_by_id(control, 9430)
    assert row["collapsed"] is True
    assert 9415 in {p["id"] for p in row["panels"]}
    lineage = _find_panel_by_id(control, 9415)
    assert "run_id=${run_id}" in lineage["targets"][0]["url"]


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
            if "${__data.fields.alert_runbook}" in url:
                assert (
                    url
                    == _CANONICAL_GITHUB_BLOB_PREFIX
                    + "docs/05-operations/runbooks/${__data.fields.alert_runbook}.md"
                )
                exprs = " ".join(
                    str(t.get("expr", ""))
                    for p in get_dashboard_panels(dashboard)
                    for t in p.get("targets", [])
                )
                stems = re.findall(r'"alert_runbook"\s*,\s*"([a-z][a-z0-9-]*)"', exprs)
                assert stems, "dynamic runbook requires a bounded literal label catalog"
                assert all(
                    Path(f"docs/05-operations/runbooks/{stem}.md").is_file()
                    for stem in stems
                )
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
    dashboard = load_dashboard(_require_dashboard("bioetl-incident-v1.json"))
    expected_titles = {
        "Track Failed Workflow Runs",
        "Track Failed Workflow Steps",
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
        (panel for panel in get_dashboard_panels(dashboard) if panel.get("id") == 9991),
        None,
    )
    assert next_panel is not None
    next_links = next_panel.get("links", [])
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
        "`bioetl-incident-v1` owns selected-range workflow evidence",
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
    assert not Path("grafana/dashboards/bioetl-provider-health-v2.json").exists()
    overview = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    links = get_dashboard_navigation_links(overview)
    incident = [
        candidate
        for candidate in links
        if _extract_dashboard_uid(candidate["url"]) == "bioetl-incident-v1"
    ]
    assert len(incident) == 1
    assert "${pipeline:queryparam}" in incident[0]["url"]
    assert "${__url_time_range}" in incident[0]["url"]


def test_workflow_overview_first_action_cta_contract() -> None:
    """Retained fleet triage exposes four explicit destinations in its owner."""
    dashboard = load_dashboard(_require_dashboard("bioetl-incident-v1.json"))
    panel = next(p for p in get_dashboard_panels(dashboard) if p.get("id") == 9991)
    links = panel["links"]
    assert len(links) == 4
    destinations = {9401, 205, 9101, 242}
    assert {
        int(str(link["url"]).split("viewPanel=")[1].split("&")[0]) for link in links
    } == destinations
    for link in links:
        assert "/d/bioetl-incident-v1/" in link["url"]
        assert "${workflow:queryparam}" in link["url"]
        assert "${pipeline:queryparam}" in link["url"]
        assert "${__url_time_range}" in link["url"]
        assert link["includeVars"] is False


def test_dashboard_links_do_not_default_run_type_to_unknown() -> None:
    """Missing run-type context must use Run Type=All, never unknown."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        links_json = json.dumps(get_dashboard_navigation_links(dashboard))
        assert "var-run_type=unknown" not in links_json, (
            f"{dashboard_path.name} must not link with Run Type=unknown"
        )


def test_run_type_variables_default_to_all_not_unknown() -> None:
    """Run Type defaults: Overview keeps All; other boards default to backfill (SEL-P0).

    Missing context must never use run_type=unknown.
    """
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        variables = dashboard.get("templating", {}).get("list", [])
        assert isinstance(variables, list)

        for variable in variables:
            if not isinstance(variable, dict) or variable.get("name") != "run_type":
                continue
            current = variable.get("current", {})
            text = current.get("text")
            value = current.get("value")
            assert text != "unknown" and value != "unknown", (
                f"{dashboard_path.name} run_type must not default to unknown"
            )
            if dashboard_path.name in {
                "bioetl-overview-v2.json",
                "bioetl-run-explorer-v1.json",
            }:
                assert text == "All", (
                    f"{dashboard_path.name} run_type current text must be All"
                )
                assert value == "$__all", (
                    f"{dashboard_path.name} run_type current value must be $__all"
                )
            else:
                assert text == "backfill", (
                    f"{dashboard_path.name} run_type current text must be backfill"
                )
                assert value == "backfill", (
                    f"{dashboard_path.name} run_type current value must be backfill"
                )


def test_pipeline_and_provider_variables_follow_explicit_scope_defaults() -> None:
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
            if (variable_name == "pipeline") or (
                dashboard_path.name == "bioetl-provider-health-v2.json"
                and variable_name == "provider"
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
    overview = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    link = next(
        candidate
        for candidate in _find_panel_by_id(overview, 9002)["links"]
        if candidate["title"] == "Open Provider Evidence"
    )
    assert link["includeVars"] is False
    for token in (
        "${workflow:queryparam}",
        "${pipeline:queryparam}",
        "${run_type:queryparam}",
        "${run_id:queryparam}",
        "${__url_time_range}",
    ):
        assert token in link["url"]
    assert "viewPanel=9480" in link["url"]
    assert not {"adapter", "provider", "pipeline_context"} & _extract_link_vars(
        link["url"]
    )


def test_dashboard_links_do_not_use_all_for_pipeline_or_provider() -> None:
    """Unknown is the only explicit fallback for Pipeline/Provider handoff values."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for link in _collect_dashboard_links(dashboard):
            url = str(link.get("url", ""))
            assert "var-pipeline=All" not in url
            assert "var-provider=All" not in url


def test_nav_bus_never_uses_literal_stage_unknown() -> None:
    """Portfolio nav bus must not reintroduce stage=unknown after #7721/#7725.

    Stage is multi/includeAll on Runtime and DQ. Literal unknown is not a stage
    label and empties stage-scoped evidence on drill-down.
    """
    operator_uids = {
        "bioetl-control-plane-v1",
        "bioetl-overview-v2",
        "bioetl-dq-v2",
        "bioetl-incident-v1",
        "bioetl-run-explorer-v1",
    }
    for uid in sorted(operator_uids):
        if uid == "bioetl-run-explorer-v1":
            continue
        dashboard = load_dashboard(Path("grafana/dashboards") / f"{uid}.json")
        nav = next(
            (
                panel
                for panel in get_dashboard_panels(dashboard)
                if panel.get("id") == 1000
            ),
            None,
        )
        assert nav is not None, f"{uid} missing navigation panel id=1000"
        content = str((nav.get("options") or {}).get("content") or "")
        assert "var-stage=unknown" not in content, (
            f"{uid} nav HTML must not hardcode var-stage=unknown"
        )
        for link in nav.get("links") or []:
            url = str(link.get("url") or "")
            assert "var-stage=unknown" not in url, (
                f"{uid} nav link {link.get('title')!r} must not use var-stage=unknown"
            )
            target = _extract_dashboard_uid(url)
            if target == "bioetl-dq-v2":
                assert "var-stage=$__all" in url, (
                    f"{uid} → {target} must pass var-stage=$__all"
                )

    from scripts.ops.observability.grafana.render_nav_bus import _url_for

    for target_uid in ("bioetl-dq-v2",):
        url = _url_for(
            {"uid": target_uid, "path": target_uid, "title": "x"},
            source_uid="bioetl-overview-v2",
        )
        assert "var-stage=unknown" not in url
        assert "var-stage=$__all" in url


def test_provider_health_first_action_cta_contract() -> None:
    overview = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    links = _find_panel_by_id(overview, 9002)["links"]
    assert len(links) == 3
    assert {candidate["title"] for candidate in links} == {
        "Open Control Plane",
        "Open Data Quality",
        "Open Provider Evidence",
    }
    assert all(candidate["includeVars"] is False for candidate in links)


def test_dq_first_action_cta_contract() -> None:
    dq = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = _find_panel_by_id(dq, 9406)
    assert "SELECTED RUN" in panel["description"]
    links = panel["links"]
    assert len(links) == 1
    assert _extract_dashboard_uid(links[0]["url"]) == "bioetl-run-explorer-v1"
    assert "${run_id:queryparam}" in links[0]["url"]
    assert "${__url_time_range}" in links[0]["url"]
    assert links[0]["includeVars"] is False
