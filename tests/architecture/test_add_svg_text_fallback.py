"""Tests for scripts/diagrams/add_svg_text_fallback.py fallback label generation."""

from __future__ import annotations

import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType


def _load_fallback_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "diagrams" / "add_svg_text_fallback.py"
    spec = importlib.util.spec_from_file_location(
        "add_svg_text_fallback_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_fallback_text_emits_multiline_tspans() -> None:
    module = _load_fallback_module()
    fo = ET.fromstring(
        """
        <foreignObject xmlns="http://www.w3.org/2000/svg"
                       xmlns:html="http://www.w3.org/1999/xhtml"
                       x="10" y="20" width="220" height="120">
          <html:div>
            <html:span>
              <html:p>Header<html:br/>Line 1<html:br/>Line 2</html:p>
            </html:span>
          </html:div>
        </foreignObject>
        """
    )

    fallback = module._build_fallback_text(fo)
    assert fallback is not None

    tspans = [child for child in fallback if child.tag.endswith("tspan")]
    assert len(tspans) >= 3
    assert tspans[0].text == "Header"
    assert tspans[1].text == "Line 1"
    assert tspans[2].text == "Line 2"


def test_add_fallbacks_replaces_old_single_line_text(tmp_path: Path) -> None:
    module = _load_fallback_module()
    svg_path = tmp_path / "sample.svg"
    svg_path.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg" xmlns:html="http://www.w3.org/1999/xhtml">
          <g class="label">
            <text class="fo-fallback">Old single line</text>
            <foreignObject x="0" y="0" width="200" height="100">
              <html:div>
                <html:span>
                  <html:p>Title<html:br/>Value 1<html:br/>Value 2</html:p>
                </html:span>
              </html:div>
            </foreignObject>
          </g>
        </svg>
        """.strip(),
        encoding="utf-8",
    )

    changed = module.add_fallbacks(svg_path, require_repo=False)
    assert changed >= 1

    root = ET.parse(svg_path).getroot()
    fallback_nodes = [
        elem
        for elem in root.iter()
        if elem.tag.endswith("text") and "fo-fallback" in elem.attrib.get("class", "")
    ]
    assert len(fallback_nodes) == 1
    assert fallback_nodes[0].text in (None, "")

    tspans = [child for child in fallback_nodes[0] if child.tag.endswith("tspan")]
    assert len(tspans) >= 3
    assert [t.text for t in tspans[:3]] == ["Title", "Value 1", "Value 2"]


def test_sanitize_preserves_method_signature_parentheses() -> None:
    module = _load_fallback_module()

    assert (
        module._sanitize_label_line("+fetch(entity_type, limit)", label_kind="methods")
        == "+fetch(entity_type, limit)"
    )
    assert (
        module._sanitize_label_line("DataSourcePort(fetch)", label_kind="generic")
        == "DataSourcePort (fetch)"
    )


def test_suffix_spacing_skips_methods_and_applies_for_titles() -> None:
    module = _load_fallback_module()

    assert (
        module._add_suffix_spacing_for_long_object_name(
            "VeryLongComponentAdapter",
            max_chars=8,
            label_kind="methods",
        )
        == "VeryLongComponentAdapter"
    )
    assert (
        module._add_suffix_spacing_for_long_object_name(
            "VeryLongComponentAdapter",
            max_chars=8,
            label_kind="title",
        )
        == "VeryLongComponent Adapter"
    )


def test_add_fallbacks_methods_group_keeps_method_format_and_supports_escaped_newline(
    tmp_path: Path,
) -> None:
    module = _load_fallback_module()
    svg_path = tmp_path / "methods.svg"
    svg_path.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg" xmlns:html="http://www.w3.org/1999/xhtml">
          <g class="node default">
            <g class="methods-group text">
              <g class="label">
                <foreignObject x="0" y="0" width="460" height="90">
                  <html:div>
                    <html:span>
                      <html:p>+fetch(entity_type, limit)\\n+aclose()</html:p>
                    </html:span>
                  </html:div>
                </foreignObject>
              </g>
            </g>
          </g>
        </svg>
        """.strip(),
        encoding="utf-8",
    )

    changed = module.add_fallbacks(svg_path, require_repo=False)
    assert changed >= 1

    root = ET.parse(svg_path).getroot()
    fallback_nodes = [
        elem
        for elem in root.iter()
        if elem.tag.endswith("text") and "fo-fallback" in elem.attrib.get("class", "")
    ]
    assert len(fallback_nodes) == 1

    tspans = [child for child in list(fallback_nodes[0]) if child.tag.endswith("tspan")]
    assert [t.text for t in tspans[:2]] == ["+fetch(entity_type, limit)", "+aclose()"]
