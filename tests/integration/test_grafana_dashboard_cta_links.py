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
from pathlib import Path

import pytest
from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    get_dashboard_files,
    get_dashboard_navigation_links,
    get_dashboard_panels,
    load_dashboard,
)

from tests.integration._grafana_dashboard_links_support import (
    _REQUIRED_LINK_VARS_BY_TARGET_UID,
    _extract_dashboard_uid,
    _extract_link_vars,
    _find_panel_by_id,
    _iter_panel_data_links,
    _local_repo_path_from_canonical_github_blob_url,
)

pytestmark = pytest.mark.integration


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
            if "${__data.fields.alert_runbook}" in url:
                source = Path(
                    "scripts/ops/observability/grafana/_incident_explanations.py"
                ).read_text(encoding="utf-8")
                for slug in ("incident-response", "docker-stability"):
                    assert f'"{slug}"' in source
                    assert Path(f"docs/05-operations/runbooks/{slug}.md").is_file()
                continue
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
            if target in {"bioetl-runtime", "bioetl-dq-v2"}:
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


@pytest.mark.parametrize("retired", ["bioetl-runtime", "bioetl-provider-health-v2"])
def test_retired_workspaces_have_no_active_cta_target(retired: str) -> None:
    assert not (Path("grafana/dashboards") / f"{retired}.json").exists()
    for path in get_dashboard_files():
        for link in _collect_dashboard_links(load_dashboard(path)):
            assert _extract_dashboard_uid(str(link.get("url", ""))) != retired


def test_overview_domain_actions_preserve_all_three_operator_questions() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {p["id"]: p for p in get_dashboard_panels(dashboard)}
    actions = {link["title"]: link for link in panels[9002]["links"]}
    assert set(actions) == {
        "Open Control Plane",
        "Open Data Quality",
        "Open Provider Evidence",
    }
    provider = actions["Open Provider Evidence"]
    assert "viewPanel=9480" in provider["url"]
    assert 9480 in panels
    for link in actions.values():
        assert "${run_id:queryparam}" in link["url"]
        assert "${__url_time_range}" in link["url"]
        assert link["includeVars"] is False


def test_replay_verdict_has_a_direct_exact_checks_action() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {p["id"]: p for p in get_dashboard_panels(dashboard)}
    links = panels[9422]["links"]
    assert len(links) == 1
    assert links[0]["title"] == "View replay checks"
    assert "viewPanel=9423" in links[0]["url"]
    assert "${run_id:queryparam}" in links[0]["url"]
    assert links[0]["includeVars"] is False
    assert 9423 in panels


def test_run_explorer_links_distinguish_provider_report_and_replay_evidence() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-run-explorer-v1.json"))
    panel = _find_panel_by_id(dashboard, 3010)
    links = {link["title"]: link["url"] for link in _iter_panel_data_links(panel)}
    assert "/d/bioetl-overview-v2/" in links["Provider Evidence"]
    assert "viewPanel=9480" in links["Provider Evidence"]
    assert "/d/bioetl-control-plane-v1/" in links["Saved Evidence"]
    assert "viewPanel=9408" in links["Saved Evidence"]
    assert (
        len(
            {
                links[k]
                for k in (
                    "Provider Evidence",
                    "Saved Evidence",
                    "Run Overview",
                    "Replay Readiness",
                )
            }
        )
        == 4
    )
    for key in (
        "Provider Evidence",
        "Saved Evidence",
        "Run Overview",
        "Replay Readiness",
    ):
        assert "${__data.fields.run_id:percentencode}" in links[key]
        assert "${__url_time_range}" in links[key]


def test_dq_summary_routes_to_selected_run_evidence() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = _find_panel_by_id(dashboard, 9406)
    links = _iter_panel_data_links(panel)
    assert any(link["title"] == "Open Run Explorer" for link in links)
    assert all(
        "${run_id:queryparam}" in link["url"]
        for link in links
        if link["url"].startswith("/d/")
    )
