"""A current-source projection must not impersonate or overwrite a capture."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from defusedxml.common import EntitiesForbidden

from scripts.engineering.qa.report_topology_source_binding import (
    END,
    START,
    BOOTSTRAP_PROFILE,
    bind_bootstrap_profile,
    render_binding,
)

pytestmark = pytest.mark.unit


def test_source_binding_preserves_history_and_is_idempotent():
    historical = "Historical capture: 2026-01-01, coverage 90%, commit original\n"
    result = render_binding(historical, "a" * 64, 3)
    assert result.startswith(historical)
    assert "not a\nnew coverage measurement" in result
    assert render_binding(result, "a" * 64, 3) == result
    revised = render_binding(result, "b" * 64, 4)
    assert revised.startswith(historical)
    assert revised.count(START) == revised.count(END) == 1
    assert "a" * 64 not in revised


def test_source_binding_does_not_relabel_distinct_historical_hashes():
    historical = (
        "Refresh note (2026-10-08): previous accepted capture.\n"
        "`source_tree_sha256=02358f050d0c78c5b18a3c0fb59f7a55f0cda7a80591fb7db505405466c11625`\n"
        "\n"
        "Refresh note (2026-10-07): earlier raw capture.\n"
        "`source_tree_sha256=54049305075ccc3e44a24c65a2c6250e5f1265ad4af28065fe3a86bcc63e1029`\n"
    )
    existing = historical + START + "\nold current binding\n" + END + "\n"

    updated = render_binding(existing, "a" * 64, 3)

    assert updated.split(START, maxsplit=1)[0] == historical
    assert (
        "`source_tree_sha256=02358f050d0c78c5b18a3c0fb59f7a55f0cda7a80591fb7db505405466c11625`"
        in updated
    )
    assert (
        "`source_tree_sha256=54049305075ccc3e44a24c65a2c6250e5f1265ad4af28065fe3a86bcc63e1029`"
        in updated
    )


def test_source_binding_rejects_ambiguous_history():
    with pytest.raises(ValueError, match="delimiters"):
        render_binding(START, "a" * 64, 3)


def test_source_binding_rejects_invalid_inventory():
    with pytest.raises(ValueError, match="identity"):
        render_binding("historical", "unknown", 3)


def _bootstrap_profile(root: Path) -> dict[str, object]:
    profile = {
        "result": {"test_file_count": 1, "test_count": 2, "duration_seconds": 1.5},
        "measurement_provenance": {"junit": "capture.xml", "measured_head": "original"},
    }
    path = root / BOOTSTRAP_PROFILE
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(profile), encoding="utf-8")
    (root / "capture.xml").write_text(
        '<testsuite><testcase classname="tests.unit.composition.bootstrap.test_one.Class"/>'
        '<testcase classname="tests.unit.composition.bootstrap.test_one.OtherClass"/></testsuite>',
        encoding="utf-8",
    )
    test = root / "tests/unit/composition/bootstrap/test_one.py"
    test.parent.mkdir(parents=True)
    test.write_text("", encoding="utf-8")
    return profile


def test_new_source_modules_do_not_relabel_accepted_coverage_measurement(
    tmp_path, monkeypatch
):
    from scripts.engineering.qa import report_test_governance_audit as test_gov
    from scripts.engineering.qa import report_topology_source_binding as reporter

    historical_profile = _bootstrap_profile(tmp_path)
    source = tmp_path / "src/bioetl"
    source.mkdir(parents=True)
    (source / "first.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "new.py").write_text("VALUE = 2\n", encoding="utf-8")
    digest = reporter.compute_source_tree_sha256(repo_root=tmp_path)
    inventory = {
        "source_tree_sha256": digest,
        "modules": [{"module": "bioetl.first"}],
        "summary": {
            "source_module_count": 1,
            "status_counts": {"fully_covered": 1, "partially_covered": 0},
        },
    }
    inventory_path = tmp_path / reporter.INVENTORY
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    original_inventory = inventory_path.read_bytes()
    governance = {
        "source_tree_sha256": "b" * 64,
        "report": {"assertless_total_candidates": 0},
    }
    (tmp_path / "reports/quality/test-governance-current.json").write_text(
        json.dumps(governance), encoding="utf-8"
    )
    monkeypatch.setattr(
        test_gov, "_compute_test_governance_source_tree_sha256", lambda root: "b" * 64
    )
    targets = (
        reporter.SUMMARY,
        Path("docs/02-architecture/current-state-inventory.md"),
    )
    for target in targets:
        path = tmp_path / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Historical capture: original\n", encoding="utf-8")

    assert reporter.main(["--root", str(tmp_path), "--update"]) == 0
    assert reporter.main(["--root", str(tmp_path), "--check"]) == 0
    for target in targets:
        text = (tmp_path / target).read_text(encoding="utf-8")
        assert text.startswith("Historical capture: original\n")
        assert "`source_module_count=2`" in text
        assert "`coverage_inventory_module_count=1`" in text
        assert "Accepted inventory: `1` fully covered" in text
    assert inventory_path.read_bytes() == original_inventory
    updated_profile = json.loads(
        (tmp_path / reporter.BOOTSTRAP_PROFILE).read_text(encoding="utf-8")
    )
    updated_profile.pop("current_source_binding")
    assert updated_profile == historical_profile


def test_bootstrap_binding_preserves_measured_profile_and_detects_new_topology(
    tmp_path: Path,
):
    historical = _bootstrap_profile(tmp_path)
    assert not bind_bootstrap_profile(tmp_path, "a" * 64, "b" * 64, update=False)
    assert not bind_bootstrap_profile(tmp_path, "a" * 64, "b" * 64, update=True)
    assert bind_bootstrap_profile(tmp_path, "a" * 64, "b" * 64, update=False)
    (tmp_path / "tests/unit/composition/bootstrap/test_two.py").write_text(
        "", encoding="utf-8"
    )
    assert not bind_bootstrap_profile(tmp_path, "a" * 64, "b" * 64, update=False)
    bind_bootstrap_profile(tmp_path, "a" * 64, "b" * 64, update=True)
    updated = json.loads((tmp_path / BOOTSTRAP_PROFILE).read_text(encoding="utf-8"))
    assert updated.pop("current_source_binding")["test_file_count"] == 2
    assert updated == historical


def test_bootstrap_binding_rejects_junit_without_classname(tmp_path: Path):
    _bootstrap_profile(tmp_path)
    (tmp_path / "capture.xml").write_text(
        "<testsuite><testcase name='x'/></testsuite>",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Foreign test"):
        bind_bootstrap_profile(tmp_path, "a" * 64, "b" * 64, update=True)


def test_bootstrap_binding_rejects_junit_without_test_module(tmp_path: Path):
    _bootstrap_profile(tmp_path)
    (tmp_path / "capture.xml").write_text(
        "<testsuite><testcase "
        'classname="tests.unit.composition.bootstrap.helper.Class"/></testsuite>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="test module"):
        bind_bootstrap_profile(tmp_path, "a" * 64, "b" * 64, update=True)


def test_bootstrap_binding_rejects_mismatched_historical_capture(tmp_path: Path):
    historical = _bootstrap_profile(tmp_path)
    historical["result"]["test_file_count"] = 2
    (tmp_path / BOOTSTRAP_PROFILE).write_text(json.dumps(historical), encoding="utf-8")
    with pytest.raises(ValueError, match="measured JUnit"):
        bind_bootstrap_profile(tmp_path, "a" * 64, "b" * 64, update=True)


@pytest.mark.parametrize(
    "junit_path",
    ["../outside.xml", "/tmp/outside.xml", "", 12],
)
def test_bootstrap_binding_rejects_junit_path_escape(
    tmp_path: Path, junit_path: object
):
    historical = _bootstrap_profile(tmp_path)
    historical["measurement_provenance"]["junit"] = junit_path
    (tmp_path / BOOTSTRAP_PROFILE).write_text(json.dumps(historical), encoding="utf-8")
    outside = tmp_path.parent / "outside.xml"
    outside.write_text("<testsuite/>", encoding="utf-8")
    with pytest.raises(ValueError):
        bind_bootstrap_profile(tmp_path, "a" * 64, "b" * 64, update=True)
    stored = json.loads((tmp_path / BOOTSTRAP_PROFILE).read_text(encoding="utf-8"))
    assert "current_source_binding" not in stored


def test_bootstrap_binding_confines_capture_reference(tmp_path: Path):
    historical = _bootstrap_profile(tmp_path)
    historical["measurement_provenance"]["junit"] = "../outside.xml"
    profile = tmp_path / BOOTSTRAP_PROFILE
    profile.write_text(json.dumps(historical), encoding="utf-8")
    before = profile.read_bytes()
    with pytest.raises(ValueError):
        bind_bootstrap_profile(tmp_path, "a" * 64, "b" * 64, update=True)
    assert profile.read_bytes() == before


def test_bootstrap_binding_rejects_xml_entities(tmp_path: Path):
    _bootstrap_profile(tmp_path)
    (tmp_path / "capture.xml").write_text(
        '<!DOCTYPE testsuite [<!ENTITY hostile "expanded">]><testsuite>&hostile;</testsuite>',
        encoding="utf-8",
    )
    with pytest.raises(EntitiesForbidden):
        bind_bootstrap_profile(tmp_path, "a" * 64, "b" * 64, update=True)
