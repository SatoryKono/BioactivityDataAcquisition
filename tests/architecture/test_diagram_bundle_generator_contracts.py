"""Architecture checks for canonical diagram bundle generator and wrappers."""

from __future__ import annotations

import pytest

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


pytestmark = pytest.mark.architecture

def _load_generate_all_bundles() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "diagrams" / "generate_all_bundles.py"
    script_dir = str(module_path.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "diagram_bundle_generator_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_generate_all_bundles_supports_collection_selection() -> None:
    module = _load_generate_all_bundles()

    args = module.parse_args(["--collection", "views", "--collection", "architecture"])

    assert args.collection == ["views", "architecture"]


def test_views_toc_is_grouped_by_parent_family() -> None:
    module = _load_generate_all_bundles()
    parsed = [
        (
            Path("views/01-full-system-component-dataflow.mermaid"),
            {
                "stem": "01-full-system-component-dataflow",
                "title": "01 Full System Component",
                "view_type": "Data-Flow",
            },
        ),
        (
            Path("views/01-full-system-component-full.mermaid"),
            {
                "stem": "01-full-system-component-full",
                "title": "Full System Component Diagram",
                "view_type": "Full",
            },
        ),
        (
            Path("views/01-full-system-component-overview.mermaid"),
            {
                "stem": "01-full-system-component-overview",
                "title": "01 Full System Component",
                "view_type": "Overview",
            },
        ),
    ]

    lines = module.build_toc_lines(parsed, "views")

    assert any("01-full-system-component" in line for line in lines)
    assert any("3 views: data-flow, full, overview" in line for line in lines)
    assert not any(
        line.startswith("- [01-full-system-component-dataflow") for line in lines
    )


def test_diagrams_router_exposes_collection_specific_bundle_commands() -> None:
    content = Path("scripts/diagrams/__main__.py").read_text(encoding="utf-8")

    assert '"render-pdf"' in content
    assert '"generate_all_bundles.py", "--collection", "architecture"' in content
    assert '"render-views"' in content
    assert '"generate_all_bundles.py", "--collection", "views"' in content
    assert not Path("scripts/diagrams/generate_architecture_bundle.py").exists()
    assert not Path("scripts/diagrams/generate_views_bundle.py").exists()


def test_bundle_generator_prefers_svg_embed_over_png(tmp_path: Path) -> None:
    module = _load_generate_all_bundles()
    collection_dir = tmp_path / "architecture"
    output_md = tmp_path / "bundles" / "architecture.bundle.md"
    (collection_dir / "svg").mkdir(parents=True)
    (collection_dir / "png").mkdir(parents=True)
    output_md.parent.mkdir(parents=True)
    (collection_dir / "svg" / "01-sample.svg").write_text("<svg/>", encoding="utf-8")
    (collection_dir / "png" / "01-sample.png").write_bytes(b"png")

    markdown = module.resolve_bundle_image_markdown(
        collection_dir, "01-sample", output_md
    )

    assert "svg/01-sample.svg" in markdown
    assert "png/01-sample.png" not in markdown


def test_bundle_generator_falls_back_to_png_when_svg_missing(tmp_path: Path) -> None:
    module = _load_generate_all_bundles()
    collection_dir = tmp_path / "architecture"
    output_md = tmp_path / "bundles" / "architecture.bundle.md"
    (collection_dir / "png").mkdir(parents=True)
    output_md.parent.mkdir(parents=True)
    (collection_dir / "png" / "01-sample.png").write_bytes(b"png")

    markdown = module.resolve_bundle_image_markdown(
        collection_dir, "01-sample", output_md
    )

    assert "png/01-sample.png" in markdown
