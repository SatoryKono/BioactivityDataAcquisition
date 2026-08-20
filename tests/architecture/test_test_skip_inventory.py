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
"""Architecture checks for the reviewed test skip inventory."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "configs" / "quality" / "test_skip_inventory.yaml"
SCAN_ROOTS = (ROOT / "tests" / "contract", ROOT / "tests" / "integration")
REPLAY_CRITICAL_GATES = (
    ROOT
    / "tests"
    / "integration"
    / "determinism"
    / "test_reproducibility_determinism_gate.py",
    ROOT
    / "tests"
    / "integration"
    / "idempotency"
    / "test_reproducibility_idempotency_gate.py",
)

pytestmark = pytest.mark.architecture


def _load_inventory() -> dict[str, object]:
    return yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8"))


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        files.extend(root.rglob("*.py"))
    return sorted(files)


def _qualified_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _qualified_name(node.value)
        return f"{owner}.{node.attr}" if owner else node.attr
    return None


def _suppression_count_from_source(source: str) -> int:
    count = 0
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = _qualified_name(node.func)
        if name in {"pytest.skip", "pytest.importorskip", "importorskip"}:
            count += 1
        elif name in {
            "pytest.mark.skip",
            "pytest.mark.skipif",
            "pytest.mark.xfail",
        }:
            count += 1
    return count


def _skip_call_count(path: Path) -> int:
    return _suppression_count_from_source(path.read_text(encoding="utf-8"))


def _live_skip_inventory() -> dict[str, int]:
    inventory: dict[str, int] = {}
    for path in _iter_python_files():
        count = _skip_call_count(path)
        if count:
            inventory[path.relative_to(ROOT).as_posix()] = count
    return inventory


def test_test_skip_inventory_schema_is_reviewable() -> None:
    payload = _load_inventory()

    assert payload["policy_scope"] == "test_skip_inventory"
    assert payload["owner"] == "@bioetl-platform"
    assert payload["linked_issue"] == 5007
    assert sorted(payload["allowed_categories"]) == [
        "conditional_environment_guard",
        "git_diff_scope_guard",
        "live_endpoint_unavailability",
        "live_network_opt_in_guard",
        "optional_local_fixture_absence",
        "replay_fixture_pointer_guard",
        "snapshot_refresh_write_mode",
        "temporary_known_failure",
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("@pytest.mark.skip(reason='retired')\ndef test_x(): pass\n", 1),
        ("@pytest.mark.skipif(True, reason='platform')\ndef test_x(): pass\n", 1),
        ("@pytest.mark.xfail(reason='known')\ndef test_x(): pass\n", 1),
        ("pytestmark = pytest.mark.skip(reason='module')\n", 1),
        (
            "pytestmark = [pytest.mark.skipif(True, reason='a'), "
            "pytest.mark.xfail(reason='b')]\n",
            2,
        ),
        ("def test_x():\n    pytest.skip('runtime')\n", 1),
        ("pytest.importorskip('optional')\n", 1),
    ],
)
def test_static_suppression_census_covers_pytest_forms(
    source: str,
    expected: int,
) -> None:
    assert _suppression_count_from_source(source) == expected


def test_test_skip_inventory_tracks_current_live_skip_surfaces() -> None:
    payload = _load_inventory()
    entries = payload["entries"]

    tracked = {entry["path"]: entry for entry in entries}
    live = _live_skip_inventory()

    assert set(tracked) == set(live), (
        "Test skip inventory is stale. Regenerate reviewed rows for:\n"
        + "\n".join(sorted(set(tracked) ^ set(live)))
    )

    allowed_categories = set(payload["allowed_categories"])
    for path, entry in tracked.items():
        assert entry["suite"] in {"contract", "integration"}, path
        assert entry["category"] in allowed_categories, path
        assert str(entry["owner"]).startswith("@bioetl-"), path
        assert str(entry["linked_issue"]).startswith("#"), path
        lifecycle = entry["lifecycle"]
        assert lifecycle in {"permanent_policy", "temporary_debt"}, path
        if lifecycle == "temporary_debt":
            assert str(entry.get("expires_on", "")).strip(), path
        assert isinstance(entry["vcr_related"], bool), path
        assert str(entry["review_date"]).strip(), path
        assert str(entry["rationale"]).strip(), path
        assert entry["reviewed_skip_calls"] == live[path], (
            f"Reviewed skip count drift for {path}: "
            f"expected {live[path]}, got {entry['reviewed_skip_calls']}"
        )


@pytest.mark.parametrize("gate_path", REPLAY_CRITICAL_GATES, ids=lambda path: path.stem)
def test_replay_critical_gates_cannot_be_suppressed(gate_path: Path) -> None:
    """Keep determinism/idempotency merge evidence mandatory on every OS."""
    source = gate_path.read_text(encoding="utf-8")

    assert _suppression_count_from_source(source) == 0, (
        f"{gate_path.relative_to(ROOT)} must run fail-closed on every platform; "
        "isolate its runtime filesystem instead of adding skip/skipif/xfail"
    )
    assert "replay_runtime_root" in source


def _unconditional_skip_marker_paths() -> list[str]:
    """Return unit/architecture files that use bare @pytest.mark.skip(."""
    offenders: list[str] = []
    for root_name in ("unit", "architecture"):
        for path in sorted((ROOT / "tests" / root_name).rglob("*.py")):
            if path.name == "test_test_skip_inventory.py":
                continue
            source = path.read_text(encoding="utf-8")
            if "@pytest.mark.skip(" not in source:
                continue
            # skipif is a different token; strip it before looking for skip(
            if "@pytest.mark.skip(" in source.replace("@pytest.mark.skipif(", ""):
                offenders.append(path.relative_to(ROOT).as_posix())
    return offenders


def test_unit_and_architecture_forbid_unconditional_skip_marker() -> None:
    """Unit/architecture must not hide tests with bare @pytest.mark.skip (#9130)."""
    offenders = _unconditional_skip_marker_paths()
    assert not offenders, (
        "Unconditional @pytest.mark.skip is not inventoried for unit/architecture. "
        "Use skipif with a reason, or move the skip into the reviewed contract/"
        "integration census:\n" + "\n".join(offenders)
    )
