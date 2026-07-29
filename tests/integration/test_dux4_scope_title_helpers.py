# pyright: reportArgumentType=false
"""DUX4-01 scope title helper contracts."""

from __future__ import annotations

from tests.integration._grafana_test_support import (
    SCOPE_TITLE_PREFIX_RE,
    index_panels_by_base_title,
    panel_base_title,
    strip_scope_title_prefix,
)


def test_strip_scope_title_prefix_removes_ascii_markers() -> None:
    assert (
        strip_scope_title_prefix("[NOW/HEALTH] Status") == "Status"
    )
    assert (
        strip_scope_title_prefix("[RANGE/EVIDENCE] Monitor Foo") == "Monitor Foo"
    )
    assert strip_scope_title_prefix("Status") == "Status"


def test_scope_title_prefix_regex_matches_families() -> None:
    assert SCOPE_TITLE_PREFIX_RE.match("[WORKFLOW/IMPACT] Ranked Active Suspects")
    assert not SCOPE_TITLE_PREFIX_RE.match("[INVALID/HEALTH] X")


def test_index_panels_by_base_title_tolerates_optional_prefix() -> None:
    panels = [
        {"title": "[NOW/HEALTH] Status", "id": 1},
        {"title": "First Action", "id": 2},
    ]
    indexed = index_panels_by_base_title(panels)
    assert indexed["Status"]["id"] == 1
    assert indexed["First Action"]["id"] == 2
    assert panel_base_title(panels[0]) == "Status"
