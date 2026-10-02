"""Unit tests for canonical Grafana dashboard context URLs."""

from __future__ import annotations

import pytest

from scripts.ops.observability.grafana.dashboard_context_links import (
    DashboardContext,
    RunIdError,
    build_handoff_url,
    normalize_run_id,
    preserves_time_window,
    rewrite_dashboard_handoff_url,
    urls_for_context,
)

from scripts.ops.observability.grafana.action_target_routes import (
    ACTION_DASHBOARD_UID_BY_TARGET,
    dashboard_uid_for_target,
    row_aware_dashboard_url,
)

pytestmark = pytest.mark.unit


def test_normalize_run_id_trims_and_rejects_internal_space() -> None:
    assert normalize_run_id("  abc-def  ") == "abc-def"
    with pytest.raises(RunIdError):
        normalize_run_id("  ")
    with pytest.raises(RunIdError):
        normalize_run_id("ab cd")


def test_rewrite_fills_missing_run_id_and_time() -> None:
    url = rewrite_dashboard_handoff_url(
        "/d/bioetl-run-explorer-v1/bioetl-run-explorer-v1?var-pipeline=$pipeline"
    )
    assert "var-run_id=$run_id" in url
    assert preserves_time_window(url)
    viewpanel = rewrite_dashboard_handoff_url(
        "/d/bioetl-runtime/bioetl-runtime?viewPanel=9401&var-pipeline=$pipeline"
        "&var-run_type=$run_type&var-stage=$stage&${__url_time_range}"
    )
    assert viewpanel.startswith("/d/bioetl-overview-v2/2-overview?")
    assert "var-run_id=" in viewpanel
    assert "viewPanel=" not in viewpanel
    assert preserves_time_window(viewpanel)


def test_rewrite_trims_concrete_run_id() -> None:
    url = rewrite_dashboard_handoff_url(
        "/d/bioetl-control-plane-v1/bioetl-control-plane-v1"
        "?var-run_id=%20%2068c11d41-1d2f-5dc9-b041-9265bc485046"
    )
    assert "var-run_id=68c11d41-1d2f-5dc9-b041-9265bc485046" in url


def test_template_handoff_preserves_visible_pipeline_from_provider_board() -> None:
    url = build_handoff_url(
        "bioetl-overview-v2",
        source_uid="bioetl-provider-health-v2",
        template=True,
    )
    assert "${pipeline:queryparam}" in url
    assert "pipeline_context" not in url
    assert "${run_id:queryparam}" in url


def test_urls_for_context_do_not_keep_a_foreign_uuid() -> None:
    context = DashboardContext(
        workflow="wf",
        pipeline="chembl_assay",
        run_type="backfill",
        run_id="68c11d41-1d2f-5dc9-b041-9265bc485046",
    )
    urls = urls_for_context(context)
    assert "64927" not in "".join(urls.values())
    assert all(
        "var-run_id=68c11d41-1d2f-5dc9-b041-9265bc485046" in url
        for url in urls.values()
    )


@pytest.mark.parametrize("retired", ["bioetl-runtime", "bioetl-provider-health-v2"])
def test_legacy_handoff_maps_to_live_owner_without_losing_identity_or_time(
    retired: str,
) -> None:
    from urllib.parse import parse_qs, urlsplit

    run_id = "68c11d41-1d2f-5dc9-b041-9265bc485046"
    url = rewrite_dashboard_handoff_url(
        f"/d/{retired}/old-slug?var-workflow=wf&var-pipeline=chembl_assay"
        f"&var-run_type=backfill&var-run_id={run_id}&from=1000&to=2000"
        "&var-provider=chembl&var-pipeline_context=wrong&var-stage=silver&viewPanel=9101"
    )
    parsed = urlsplit(url)
    assert parsed.path == "/d/bioetl-overview-v2/2-overview"
    assert parse_qs(parsed.query) == {
        "var-workflow": ["wf"],
        "var-pipeline": ["chembl_assay"],
        "var-run_type": ["backfill"],
        "var-run_id": [run_id],
        "from": ["1000"],
        "to": ["2000"],
    }
    assert rewrite_dashboard_handoff_url(url) == url


@pytest.mark.parametrize("retired", ["bioetl-runtime", "bioetl-provider-health-v2"])
def test_legacy_template_builder_never_emits_retired_selectors(retired: str) -> None:
    url = build_handoff_url(retired, extras={"provider": "unknown", "stage": "silver"})
    assert url.startswith("/d/bioetl-overview-v2/2-overview?")
    assert "${run_id:queryparam}" in url
    assert preserves_time_window(url)
    assert "provider" not in url and "stage" not in url


def test_context_urls_and_routes_cover_exactly_the_shipped_portfolio() -> None:
    import json
    from pathlib import Path
    from scripts.ops.observability.grafana.dashboard_context_links import (
        ACTIVE_UIDS,
        PATH_BY_UID,
    )

    shipped = {
        json.loads(p.read_text(encoding="utf-8"))["uid"]
        for p in Path("grafana/dashboards").glob("*.json")
    }
    assert set(ACTIVE_UIDS) == set(PATH_BY_UID) == shipped
    with pytest.raises(ValueError, match="unknown dashboard"):
        build_handoff_url("unknown-dashboard")


def test_action_targets_use_allowlisted_dashboard_routes() -> None:
    assert dashboard_uid_for_target("runtime") == "bioetl-overview-v2"
    assert dashboard_uid_for_target("data_quality") == "bioetl-dq-v2"
    assert dashboard_uid_for_target("verify_dq_reason_rules") is None
    assert dashboard_uid_for_target("unknown") is None
    assert ACTION_DASHBOARD_UID_BY_TARGET["provider"] == "bioetl-overview-v2"

    url = row_aware_dashboard_url()
    assert "${__data.fields.action_dashboard_uid}" in url
    assert "var-run_id=${__data.fields.run_id}" in url
    assert "${__url_time_range}" in url


def test_action_normalization_preserves_rank_query_and_visible_column() -> None:
    """A navigation refresh must not erase confidence or hide the Action field."""
    from copy import deepcopy

    from scripts.ops.observability.grafana.dashboard_context_links import (
        normalize_dashboard_actions,
    )

    panel = {
        "id": 2010,
        "targets": [{"expr": "rank_with_confidence"}],
        "transformations": [
            {
                "id": "organize",
                "options": {
                    "renameByName": {"action": "Action"},
                    "indexByName": {"action": 0, "domain": 1},
                },
            }
        ],
        "fieldConfig": {
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "Action"},
                    "properties": [
                        {"id": "custom.width", "value": 105},
                        {"id": "custom.hidden", "value": False},
                    ],
                }
            ],
        },
    }
    dashboard = {"uid": "bioetl-incident-v1", "panels": [panel]}
    normalize_dashboard_actions(dashboard)
    first = deepcopy(dashboard)
    normalize_dashboard_actions(dashboard)
    assert dashboard == first
    assert panel["targets"][0]["expr"] == "rank_with_confidence"
    properties = panel["fieldConfig"]["overrides"][0]["properties"]
    assert {"id": "custom.hidden", "value": False} in properties
    assert {"id": "custom.width", "value": 105} in properties
    link = next(prop["value"][0] for prop in properties if prop["id"] == "links")
    assert "${__data.fields.route_pipeline}" in link["url"]


@pytest.mark.parametrize(
    "uid, slug",
    [
        ("bioetl-run-explorer-v1", "run-explorer"),
        ("bioetl-control-plane-v1", "1-trust"),
        ("bioetl-overview-v2", "2-overview"),
        ("bioetl-dq-v2", "5-data-quality"),
        ("bioetl-incident-v1", "6-incident-workspace"),
    ],
)
def test_handoff_uses_canonical_numbered_slug(uid: str, slug: str) -> None:
    assert build_handoff_url(uid).startswith(f"/d/{uid}/{slug}?")


def test_late_links_are_finalized_without_rewriting_row_context() -> None:
    from copy import deepcopy
    from scripts.ops.observability.grafana.dashboard_context_links import (
        finalize_dashboard_links,
    )

    url = "/d/${__data.fields.action_dashboard_uid}/?var-pipeline=${__data.fields.pipeline:percentencode}"
    link = {"url": url, "includeVars": True}
    payload = {
        "panels": [{"panels": [{"options": {"dataLinks": []}, "links": [link]}]}]
    }
    finalize_dashboard_links(payload)
    assert link == {"url": url, "includeVars": False}
    assert payload["panels"][0]["panels"][0]["options"] == {}
    first = deepcopy(payload)
    finalize_dashboard_links(payload)
    assert payload == first


@pytest.mark.parametrize("color", ["text", "#A3A3A3", "#555555", "gray"])
def test_neutral_status_colors_remain_neutral(color: str) -> None:
    from scripts.engineering.qa.check_dashboard_visual_semantics import (
        _semantic_palette,
    )

    assert _semantic_palette({"text": "UNKNOWN", "color": color}) == {
        "text": "UNKNOWN",
        "color": "gray",
    }


@pytest.mark.parametrize("color", ["green", "red", "orange", "yellow"])
def test_severity_colors_are_never_normalized_to_unknown(color: str) -> None:
    from scripts.engineering.qa.check_dashboard_visual_semantics import (
        _semantic_palette,
    )

    assert _semantic_palette({"text": "UNKNOWN", "color": color})["color"] == color


def test_queryparam_handoffs_remain_stable_across_regeneration() -> None:
    from scripts.ops.observability.grafana.dashboard_context_links import (
        finalize_dashboard_links,
    )

    link = {
        "url": "/d/bioetl-overview-v2/2-overview?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&${__url_time_range}"
    }
    payload = {"links": [link]}
    finalize_dashboard_links(payload)
    first = link["url"]
    for _ in range(3):
        finalize_dashboard_links(payload)
        assert link["url"] == first
    for name in ("workflow", "pipeline", "run_type", "run_id"):
        assert first.count("${" + name + ":queryparam}") == 1
        assert "${" + name + ":queryparam}=" not in first
