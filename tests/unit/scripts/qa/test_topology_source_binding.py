"""A current-source projection must not impersonate or overwrite a capture."""

import json
from pathlib import Path

import pytest

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


def test_bootstrap_binding_rejects_mismatched_historical_capture(tmp_path: Path):
    historical = _bootstrap_profile(tmp_path)
    historical["result"]["test_file_count"] = 2
    (tmp_path / BOOTSTRAP_PROFILE).write_text(json.dumps(historical), encoding="utf-8")
    with pytest.raises(ValueError, match="measured JUnit"):
        bind_bootstrap_profile(tmp_path, "a" * 64, "b" * 64, update=True)
