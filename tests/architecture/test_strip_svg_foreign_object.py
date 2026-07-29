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
"""Tests for scripts/diagrams/strip_svg_foreign_object.py."""

from __future__ import annotations

import pytest

import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType


pytestmark = pytest.mark.architecture


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "diagrams" / "strip_svg_foreign_object.py"
    spec = importlib.util.spec_from_file_location(
        "strip_svg_foreign_object_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_strip_foreign_objects_removes_html_labels_and_keeps_fallback_text(
    tmp_path: Path,
) -> None:
    module = _load_module()
    svg_path = tmp_path / "sample.svg"
    svg_path.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg" xmlns:html="http://www.w3.org/1999/xhtml">
          <g class="edgeLabel">
            <text class="fo-fallback">reads from</text>
            <foreignObject x="0" y="0" width="100" height="20">
              <html:div>reads from</html:div>
            </foreignObject>
          </g>
        </svg>
        """.strip(),
        encoding="utf-8",
    )

    removed = module.strip_foreign_objects(svg_path)
    assert removed == 1

    root = ET.parse(svg_path).getroot()
    foreign_objects = [
        elem for elem in root.iter() if elem.tag.endswith("foreignObject")
    ]
    assert foreign_objects == []

    fallback_nodes = [
        elem
        for elem in root.iter()
        if elem.tag.endswith("text") and "fo-fallback" in elem.attrib.get("class", "")
    ]
    assert len(fallback_nodes) == 1
    assert fallback_nodes[0].text == "reads from"


def test_strip_foreign_objects_is_idempotent(tmp_path: Path) -> None:
    module = _load_module()
    svg_path = tmp_path / "sample.svg"
    svg_path.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg" xmlns:html="http://www.w3.org/1999/xhtml">
          <g class="label">
            <foreignObject x="0" y="0" width="120" height="30">
              <html:div>node</html:div>
            </foreignObject>
          </g>
        </svg>
        """.strip(),
        encoding="utf-8",
    )

    first_removed = module.strip_foreign_objects(svg_path)
    second_removed = module.strip_foreign_objects(svg_path)

    assert first_removed == 1
    assert second_removed == 0
