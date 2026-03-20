"""Architecture checks for canonical diagram bundle generator and wrappers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


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


def test_architecture_bundle_wrapper_delegates_to_canonical_generator() -> None:
    content = Path("scripts/diagrams/generate_architecture_bundle.py").read_text(
        encoding="utf-8"
    )

    assert "Compatibility wrapper" in content
    assert "generate_all_bundles.py --collection architecture" in content
    assert 'canonical_main(["--collection", "architecture"])' in content


def test_views_bundle_wrapper_delegates_to_canonical_generator() -> None:
    content = Path("scripts/diagrams/generate_views_bundle.py").read_text(
        encoding="utf-8"
    )

    assert "Compatibility wrapper" in content
    assert "generate_all_bundles.py --collection views" in content
    assert 'canonical_main(["--collection", "views"])' in content
