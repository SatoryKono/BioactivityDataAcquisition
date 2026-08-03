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
"""Architecture tests for SVG text visibility smoke check."""

from __future__ import annotations

import pytest

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


pytestmark = pytest.mark.architecture


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "diagrams" / "check_svg_text_visibility.py"
    spec = importlib.util.spec_from_file_location("svg_visibility_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_analyze_svg_ok_with_fallback_and_css(tmp_path: Path) -> None:
    checker = _load_module()
    svg = """<svg xmlns="http://www.w3.org/2000/svg">
<style>
#my-svg .edgeLabel span{color:#111827!important;fill:#111827!important}
#my-svg text.fo-fallback{color:#111827!important;fill:#111827!important}
</style>
<g class="edgeLabel">
  <text class="fo-fallback">reads from</text>
  <foreignObject><div xmlns="http://www.w3.org/1999/xhtml">reads from</div></foreignObject>
</g>
</svg>"""
    path = tmp_path / "ok.svg"
    path.write_text(svg, encoding="utf-8")

    metrics, issues = checker.analyze_svg(path)

    assert metrics.edge_label_groups == 1
    assert metrics.edge_label_groups_with_text == 1
    assert metrics.foreign_objects == 1
    assert metrics.fallback_text_nodes == 1
    assert issues == []


def test_analyze_svg_fails_without_fallback(tmp_path: Path) -> None:
    checker = _load_module()
    svg = """<svg xmlns="http://www.w3.org/2000/svg">
<g class="edgeLabel">
  <foreignObject><div xmlns="http://www.w3.org/1999/xhtml">label</div></foreignObject>
</g>
</svg>"""
    path = tmp_path / "no-fallback.svg"
    path.write_text(svg, encoding="utf-8")

    _, issues = checker.analyze_svg(path)

    assert any("missing edge-label text safeguards" in issue for issue in issues)


def test_analyze_svg_fails_when_edge_label_text_missing(tmp_path: Path) -> None:
    checker = _load_module()
    svg = """<svg xmlns="http://www.w3.org/2000/svg">
<style>
#my-svg .edgeLabel span{color:#111827!important;fill:#111827!important}
#my-svg text.fo-fallback{color:#111827!important;fill:#111827!important}
</style>
<g class="edgeLabel">
  <foreignObject><div xmlns="http://www.w3.org/1999/xhtml"></div></foreignObject>
</g>
</svg>"""
    path = tmp_path / "empty-edge-label.svg"
    path.write_text(svg, encoding="utf-8")

    _, issues = checker.analyze_svg(path)

    assert any("no readable label text" in issue for issue in issues)
