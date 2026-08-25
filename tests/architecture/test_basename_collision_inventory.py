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
"""Basename collision inventory + request_metadata rename guard (TEST-SYS-10 / #7032)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pytest
from tests.architecture.quality_artifacts import quality_artifact_path
from tests.helpers.git_index_scan import git_tracked_files

pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]
_INV = quality_artifact_path("test-basename-collision-inventory.json")


@pytest.mark.architecture
def test_request_metadata_basenames_are_provider_prefixed() -> None:
    adapter_tests = git_tracked_files(
        root=_REPO,
        paths=("tests/unit/infrastructure/adapters",),
        suffixes=(".py",),
    )
    legacy = [path for path in adapter_tests if path.name == "test_request_metadata.py"]
    assert not legacy, (
        "Provider-prefixed names required after TEST-SYS-10: "
        + ", ".join(p.relative_to(_REPO).as_posix() for p in legacy)
    )
    renamed = [
        path
        for path in adapter_tests
        if path.name.startswith("test_") and path.name.endswith("_request_metadata.py")
    ]
    assert len(renamed) >= 7


@pytest.mark.architecture
def test_basename_collision_inventory_exists_and_is_honest() -> None:
    assert _INV.is_file()
    payload = json.loads(_INV.read_text(encoding="utf-8"))
    by_base: dict[str, list[str]] = defaultdict(list)
    for path in git_tracked_files(
        root=_REPO,
        paths=("tests",),
        suffixes=(".py",),
    ):
        if not path.name.startswith("test_"):
            continue
        by_base[path.name].append(path.relative_to(_REPO).as_posix())
    live_dups = {k: v for k, v in by_base.items() if len(v) > 1}
    assert payload["duplicate_basename_count"] == len(live_dups)
    # High-churn family must no longer collide.
    assert "test_request_metadata.py" not in live_dups
