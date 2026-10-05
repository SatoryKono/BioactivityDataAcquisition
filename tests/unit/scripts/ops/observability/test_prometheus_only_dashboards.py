"""Fail-closed fallback generation must not copy queries from full dashboards."""

import json

import pytest

from scripts.ops.observability.grafana.generate_prometheus_only_dashboards import (
    build_notice,
    render_notices,
)

pytestmark = pytest.mark.unit


def test_notice_inherits_identity_without_nested_datasources():
    source = {
        "uid": "same-uid",
        "title": "Saved assessment",
        "schemaVersion": 30,
        "panels": [{"targets": [{"datasource": "secret-source"}]}],
        "annotations": {"list": [{"datasource": "prometheus"}]},
        "templating": {"list": [{"query": "a query"}]},
    }
    notice = build_notice(source)
    assert (notice["uid"], notice["title"]) == (source["uid"], source["title"])
    serialized = json.dumps(notice)
    assert '"datasource"' not in serialized
    assert '"targets"' not in serialized
    assert "secret-source" not in serialized
    assert notice["templating"]["list"] == []
    assert notice["annotations"]["list"] == []
    assert "No retention, replay, identity, or run verdict" in serialized


def test_five_notices_are_idempotent_and_check_detects_drift(tmp_path):
    source = tmp_path / "grafana/dashboards"
    source.mkdir(parents=True)
    for number in range(5):
        (source / f"{number}.json").write_text(
            json.dumps({"uid": str(number), "title": str(number), "schemaVersion": 30}),
            encoding="utf-8",
        )
    assert not render_notices(tmp_path, check=True)
    assert render_notices(tmp_path)
    assert render_notices(tmp_path, check=True)
    changed = tmp_path / "grafana/dashboards-prometheus-only/0.json"
    changed.write_text("{}", encoding="utf-8")
    assert not render_notices(tmp_path, check=True)
    assert render_notices(tmp_path)
    assert render_notices(tmp_path, check=True)


def test_incomplete_source_portfolio_fails_before_writing(tmp_path):
    with pytest.raises(ValueError, match="exactly five"):
        render_notices(tmp_path)
    assert not (tmp_path / "grafana/dashboards-prometheus-only").exists()


@pytest.mark.parametrize(
    "relative",
    [
        "outside.json",
        "grafana/dashboards/../outside.json",
        "grafana/dashboards/local.env",
    ],
)
def test_canonical_writer_rejects_foreign_outputs(tmp_path, relative):
    from scripts.ops.observability.grafana.render_nav_bus import write_dashboard_source

    target = tmp_path / relative
    with pytest.raises(ValueError, match="canonical profile"):
        write_dashboard_source(target, "{}", root=tmp_path)
    assert not target.exists()


def test_canonical_writer_rejects_nonobject_json(tmp_path):
    from scripts.ops.observability.grafana.render_nav_bus import write_dashboard_source

    target = tmp_path / "grafana/dashboards/dashboard.json"
    with pytest.raises(ValueError, match="JSON object"):
        write_dashboard_source(target, "[]", root=tmp_path)
    assert not target.exists()
