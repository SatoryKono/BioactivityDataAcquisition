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

from pathlib import Path
import re

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "configs" / "quality" / "test_skip_inventory.yaml"
SKIP_CALL_RE = re.compile(r"\bpytest\.skip\(")
IMPORTORSKIP_RE = re.compile(r"\b(?:pytest\.)?importorskip\(")
SCAN_ROOTS = (ROOT / "tests" / "contract", ROOT / "tests" / "integration")

pytestmark = pytest.mark.architecture


def _load_inventory() -> dict[str, object]:
    return yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8"))


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        files.extend(root.rglob("*.py"))
    return sorted(files)


def _skip_call_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return len(SKIP_CALL_RE.findall(text)) + len(IMPORTORSKIP_RE.findall(text))


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
        "git_diff_scope_guard",
        "live_endpoint_unavailability",
        "live_network_opt_in_guard",
        "optional_local_fixture_absence",
        "replay_fixture_pointer_guard",
        "snapshot_refresh_write_mode",
    ]


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
