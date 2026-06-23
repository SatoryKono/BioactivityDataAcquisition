"""Architecture checks for canonical diagram description index generation."""

from __future__ import annotations

import pytest

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


pytestmark = pytest.mark.architecture


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "diagrams" / "generate_description_indexes.py"
    script_dir = str(module_path.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "diagram_description_indexes_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_collect_cards_ignores_index_markdown(tmp_path: Path) -> None:
    module = _load_module()
    family_dir = tmp_path / "class"
    family_dir.mkdir(parents=True)
    (family_dir / "01-a.md").write_text("# a\n", encoding="utf-8")
    (family_dir / "INDEX.md").write_text("# index\n", encoding="utf-8")

    original_root = module.DESCRIPTION_ROOT
    module.DESCRIPTION_ROOT = tmp_path
    try:
        cards = module.collect_cards("class")
    finally:
        module.DESCRIPTION_ROOT = original_root

    assert [path.name for path in cards] == ["01-a.md"]


def test_root_index_groups_view_cards_by_parent_family() -> None:
    module = _load_module()
    cards_by_family = {
        "architecture": [
            Path("docs/02-architecture/diagrams/descriptions/architecture/01-a.md")
        ],
        "class": [Path("docs/02-architecture/diagrams/descriptions/class/01-c.md")],
        "foundation": [
            Path("docs/02-architecture/diagrams/descriptions/foundation/01-f.md")
        ],
        "views": [
            Path(
                "docs/02-architecture/diagrams/descriptions/views/01-demo-dataflow.md"
            ),
            Path("docs/02-architecture/diagrams/descriptions/views/01-demo-full.md"),
            Path(
                "docs/02-architecture/diagrams/descriptions/views/01-demo-overview.md"
            ),
        ],
    }

    text = module.build_root_index_markdown(cards_by_family)

    assert "View cards: **3** across **1** parent families" in text
    assert (
        "[01-demo](views/01-demo-full.md) - 3 cards: dataflow, full, overview" in text
    )
    assert "[01-demo-dataflow]" not in text


def test_render_desc_indexes_command_is_registered() -> None:
    content = Path("scripts/diagrams/__main__.py").read_text(encoding="utf-8")

    assert "render-desc-indexes" in content
    assert "generate_description_indexes.py" in content
