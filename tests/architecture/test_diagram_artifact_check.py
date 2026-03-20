"""Architecture tests for diagram artifact validation checks."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "diagrams" / "check_diagram_artifacts.py"
    spec = importlib.util.spec_from_file_location(
        "diagram_artifacts_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_to_png_path_converts_svg_segment() -> None:
    module = _load_module()
    svg = Path("docs/02-architecture/diagrams/foundation/svg/01-sample.svg")

    png = module.to_png_path(svg)

    assert png.parts[-3:] == ("foundation", "png", "01-sample.png")


def test_validate_artifacts_skips_missing_png_by_default(tmp_path: Path) -> None:
    module = _load_module()
    repo = tmp_path
    svg_rel = Path("docs/a/svg/sample.svg")
    svg_abs = repo / svg_rel
    svg_abs.parent.mkdir(parents=True, exist_ok=True)
    svg_abs.write_text("<svg></svg>", encoding="utf-8")

    issues = module.validate_artifacts(repo, [svg_rel])

    assert not any(issue.kind == "DIAG-T011" for issue in issues)


def test_validate_artifacts_reports_missing_png_when_required(tmp_path: Path) -> None:
    module = _load_module()
    repo = tmp_path
    svg_rel = Path("docs/a/svg/sample.svg")
    svg_abs = repo / svg_rel
    svg_abs.parent.mkdir(parents=True, exist_ok=True)
    svg_abs.write_text("<svg></svg>", encoding="utf-8")

    issues = module.validate_artifacts(repo, [svg_rel], require_png=True)

    assert any(issue.kind == "DIAG-T011" for issue in issues)


def test_validate_artifacts_reports_empty_svg_and_png(tmp_path: Path) -> None:
    module = _load_module()
    repo = tmp_path
    svg_rel = Path("docs/a/svg/sample.svg")
    png_rel = Path("docs/a/png/sample.png")

    svg_abs = repo / svg_rel
    png_abs = repo / png_rel
    svg_abs.parent.mkdir(parents=True, exist_ok=True)
    png_abs.parent.mkdir(parents=True, exist_ok=True)
    svg_abs.write_text("", encoding="utf-8")
    png_abs.write_bytes(b"")

    issues = module.validate_artifacts(repo, [svg_rel], require_png=True)

    assert any(
        issue.kind == "DIAG-T012" and issue.file.endswith("sample.svg")
        for issue in issues
    )
    assert any(
        issue.kind == "DIAG-T012" and issue.file.endswith("sample.png")
        for issue in issues
    )


def test_parse_args_supports_optional_png_requirement() -> None:
    module = _load_module()

    args = module.parse_args([])

    assert args.require_png is False
