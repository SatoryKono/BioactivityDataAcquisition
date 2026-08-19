"""Fail-closed contracts for #9003 diagram tooling residuals."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def _load(module_name: str, relative: str) -> ModuleType:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_method_decl_re_matches_real_class_diagram_methods() -> None:
    module = _load(
        "check_class_method_render_integrity_9003",
        "scripts/diagrams/check/check_class_method_render_integrity.py",
    )
    pattern = module.METHOD_DECL_RE
    assert pattern.match("+ get_name(") is not None
    assert pattern.match("+ get_id(") is not None
    assert pattern.match("+ foo(") is not None
    assert pattern.match("+ w(") is not None


def test_prune_orphan_nodes_normalizes_sequence_diagram() -> None:
    module = _load(
        "prune_orphan_nodes_9003",
        "scripts/diagrams/fix/prune_orphan_nodes.py",
    )
    assert module.detect_diagram_type(["sequenceDiagram"]) == "sequence"
    assert module.detect_diagram_type(["flowchart TD"]) == "flowchart"
    assert module.detect_diagram_type(["graph LR"]) == "flowchart"


def test_harmonize_link_styles_does_not_treat_er_substring_as_er() -> None:
    import xml.etree.ElementTree as ET

    module = _load(
        "harmonize_link_styles_9003",
        "scripts/diagrams/fix/harmonize_link_styles.py",
    )
    other = ET.fromstring(
        '<svg xmlns="http://www.w3.org/2000/svg"><text>other layer server</text></svg>'
    )
    entity = ET.fromstring(
        '<svg xmlns="http://www.w3.org/2000/svg"><g class="entityBox"/></svg>'
    )
    assert module.detect_diagram_type(other) != "er"
    assert module.detect_diagram_type(entity) == "er"


def test_differentiate_linkstyle_refuses_unparsed_arrow_forms() -> None:
    module = _load(
        "differentiate_linkstyle_9003",
        "scripts/diagrams/fix/differentiate_linkstyle.py",
    )
    lines = [
        "flowchart TD",
        "A --> B",
        "B --- C",
        "C --> D",
        "D --> E",
        "E --> F",
        "F --> G",
    ]
    conns = module.parse_connections(lines)
    assert module.count_mermaid_arrows(lines) != len(conns)


def test_svg2png_has_no_machine_local_puppeteer_path() -> None:
    text = (ROOT / "scripts/diagrams/svg2png.mjs").read_text(encoding="utf-8")
    assert "C:/Users/Fedor" not in text
    assert "PUPPETEER_MODULE_PATH" in text
    assert '"puppeteer"' in text
