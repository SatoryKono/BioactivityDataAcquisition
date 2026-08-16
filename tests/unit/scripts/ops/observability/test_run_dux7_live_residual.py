"""Regression tests for fail-closed DUX7 keyboard navigation evidence."""

from __future__ import annotations

from typing import Any

import pytest

from scripts.ops.observability.grafana.run_dux7_live_residual import (
    _focus_style_is_visible,
    _navigation_render_pass,
    keyboard_nav_check,
)


pytestmark = pytest.mark.unit


class _FakePage:
    def __init__(self, *evaluations: dict[str, Any]) -> None:
        self._evaluations = list(evaluations)

    def wait_for_selector(self, _selector: str, *, timeout: int) -> None:
        assert timeout == 15000

    def evaluate(self, _script: str) -> dict[str, Any]:
        return self._evaluations.pop(0)


def _nav_info() -> dict[str, Any]:
    return {
        "found": True,
        "aria_current": True,
        "data_current": True,
        "link_count": 6,
        "current_underline": "underline",
        "current_border": "2px rgb(125, 211, 252)",
    }


def test_focus_style_requires_nonzero_outline_or_shadow() -> None:
    assert not _focus_style_is_visible(
        outline_style="none",
        outline_width="0px",
        box_shadow="none",
    )
    assert _focus_style_is_visible(
        outline_style="auto",
        outline_width="1px",
        box_shadow="none",
    )


def test_navigation_render_contract_fails_closed_on_font_or_clipping() -> None:
    evidence = {
        "found": True,
        "titleText": "Navigate Dashboards",
        "titleFontPx": 19,
        "minimumLinkFontPx": 16,
        "linkCount": 7,
        "contentFitsPanel": True,
        "allLinksFitPanel": True,
    }
    assert _navigation_render_pass(evidence)

    for key, failing_value in (
        ("titleFontPx", 18),
        ("minimumLinkFontPx", 15),
        ("linkCount", 6),
        ("contentFitsPanel", False),
        ("allLinksFitPanel", False),
    ):
        failing = dict(evidence)
        failing[key] = failing_value
        assert not _navigation_render_pass(failing), key
    assert _focus_style_is_visible(
        outline_style="none",
        outline_width="0px",
        box_shadow="rgb(125, 211, 252) 0px 0px 0px 2px",
    )


def test_keyboard_nav_check_fails_without_visible_focus_indicator() -> None:
    page = _FakePage(
        _nav_info(),
        {
            "tag": "A",
            "text": "0. Trust",
            "outlineStyle": "none",
            "outlineWidth": "0px",
            "outlineColor": "rgb(0, 0, 0)",
            "boxShadow": "none",
            "inNav": True,
        },
    )

    result = keyboard_nav_check(page)

    assert result["tab_reached_nav"] is True
    assert result["focus_outline_nonzero"] is False
    assert result["pass"] is False
    assert result["classification"] == "DASHBOARD_DEFECT"


def test_keyboard_nav_check_passes_with_visible_focus_indicator() -> None:
    page = _FakePage(
        _nav_info(),
        {
            "tag": "A",
            "text": "0. Trust",
            "outlineStyle": "auto",
            "outlineWidth": "1px",
            "outlineColor": "rgb(125, 211, 252)",
            "boxShadow": "none",
            "inNav": True,
        },
    )

    result = keyboard_nav_check(page)

    assert result["focus_outline_nonzero"] is True
    assert result["pass"] is True
    assert result["classification"] == "PASS"


def test_keyboard_nav_check_classifies_missing_dom_as_environment_blocker() -> None:
    result = keyboard_nav_check(_FakePage({"found": False}))

    assert result["nav_found"] is False
    assert result["pass"] is False
    assert result["classification"] == "RENDER_ENVIRONMENT_BLOCKED"
