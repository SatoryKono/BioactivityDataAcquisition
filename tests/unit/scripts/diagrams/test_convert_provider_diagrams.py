"""Tests for the governed provider-diagram metadata converter."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.diagrams import __main__ as diagrams_main
from scripts.diagrams.fix import convert_provider_diagrams as converter


pytestmark = pytest.mark.unit

LEGACY_DIAGRAM = """---
title: Example Provider Flow
version: 2.0.0
last_verified: 2026-08-09
adr_references:
  - ADR-010: Local-only deployment
  - ADR-040: Diagram governance
description: |
  Example provider flow with legacy metadata.
---

%% @version 2.0.0
%% @date 2026-08-09
%% @type flowchart
%% @level system
flowchart TD
    Start([Start]) --> Work[Work]
    Work --> End([End])
    style Start fill:#e1f5ff
    style End fill:#e1f5ff
"""


def test_convert_legacy_content_is_deterministic_and_preserves_style_roles() -> None:
    converted = converter.convert_legacy_content(LEGACY_DIAGRAM)

    assert converted is not None
    assert converted.startswith("%% Title: Example Provider Flow\n")
    assert "%% Description: Example provider flow with legacy metadata.\n" in converted
    assert "%% @nodes 3\n" in converted
    assert "%% @adr ADR-010, ADR-040\n" in converted
    assert "style Start" not in converted
    assert "classDef interfaces" in converted
    assert "class Start,End interfaces" in converted
    assert converter.convert_legacy_content(converted) is None


def test_convert_file_check_mode_does_not_modify_input(tmp_path: Path) -> None:
    provider_root = tmp_path / "providers"
    diagram = provider_root / "example" / "flow.mmd"
    diagram.parent.mkdir(parents=True)
    diagram.write_text(LEGACY_DIAGRAM, encoding="utf-8")

    assert converter.convert_file(diagram, provider_root=provider_root, write=False)
    assert diagram.read_text(encoding="utf-8") == LEGACY_DIAGRAM

    assert converter.convert_file(diagram, provider_root=provider_root, write=True)
    assert not converter.convert_file(diagram, provider_root=provider_root, write=False)


def test_converter_rejects_targets_outside_provider_root(tmp_path: Path) -> None:
    provider_root = tmp_path / "providers"
    provider_root.mkdir()
    outside = tmp_path / "outside.mmd"
    outside.write_text(LEGACY_DIAGRAM, encoding="utf-8")

    with pytest.raises(ValueError, match="outside"):
        converter.convert_file(outside, provider_root=provider_root, write=False)


def test_diagram_router_owns_provider_converter_command() -> None:
    spec = diagrams_main.COMMAND_SPECS["convert-provider-diagrams"]

    assert spec.runner == "python"
    assert spec.target == "fix/convert_provider_diagrams.py"
