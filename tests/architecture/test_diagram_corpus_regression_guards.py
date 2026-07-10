"""Regression guards for the active diagram corpus and governance baseline."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest


pytestmark = pytest.mark.architecture

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGRAM_ROOT = REPO_ROOT / "docs" / "02-architecture" / "diagrams"
DESCRIPTION_ROOT = DIAGRAM_ROOT / "descriptions"

MMD_COLLECTIONS = {
    "architecture": DIAGRAM_ROOT / "architecture",
    "class-diagrams": DIAGRAM_ROOT / "class-diagrams",
    "foundation": DIAGRAM_ROOT / "foundation",
}
VIEW_COLLECTION = DIAGRAM_ROOT / "views"


def _load_apply_elk_layout() -> ModuleType:
    module_path = REPO_ROOT / "src" / "tools" / "apply_elk_layout.py"
    spec = importlib.util.spec_from_file_location(
        "apply_elk_layout_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _source_files(directory: Path, suffix: str) -> list[Path]:
    return sorted(
        path
        for path in directory.glob(f"*{suffix}")
        if path.is_file() and not path.name.startswith("_")
    )


def _rendered_stems(directory: Path, rendered_dir: str, suffix: str) -> set[str]:
    path = directory / rendered_dir
    if not path.exists():
        return set()
    return {artifact.stem for artifact in path.glob(f"*{suffix}") if artifact.is_file()}


def _active_source_stems(directory: Path, suffix: str) -> set[str]:
    return {path.stem for path in _source_files(directory, suffix)}


def test_precommit_diagram_paths_cover_canonical_tree() -> None:
    content = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert (
        "docs/02-architecture/diagrams/(architecture|foundation|class-diagrams)"
        in content
    )
    assert "docs/02-architecture/diagrams/views" in content
    assert "lint-diagrams-views" in content
    assert "prune-orphan-diagram-view-nodes" in content
    assert "mmd-diagrams" not in content
    assert "diagrams/mermaid" not in content


def test_mmdc_docker_fallback_is_version_pinned() -> None:
    wrapper = (REPO_ROOT / "scripts" / "diagrams" / "mmdc_wrapper.sh").read_text(
        encoding="utf-8"
    )

    assert "minlag/mermaid-cli:10.6.1" in wrapper
    assert 'MMDC_REQUIRED_VERSION="${MMDC_REQUIRED_VERSION:-10.6.1}"' in wrapper
    assert "MMDC_ALLOW_VERSION_DRIFT" in wrapper
    assert "MMDC_DOCKER_IMAGE:-minlag/mermaid-cli}" not in wrapper


def test_diagram_renderer_uses_atomic_svg_and_png_writes() -> None:
    renderer = (
        REPO_ROOT / "docs" / "02-architecture" / "diagrams" / "tooling" / "render.sh"
    ).read_text(encoding="utf-8")

    assert "replace_atomically" in renderer
    assert ".${base}.svg.tmp.XXXXXX" in renderer
    assert ".${base}.png.tmp.XXXXXX" in renderer
    assert 'replace_atomically "$svg_tmp" "$svg_out"' in renderer
    assert 'replace_atomically "$png_tmp" "$png_out"' in renderer


def test_apply_elk_default_dir_is_canonical_architecture_tree() -> None:
    module = _load_apply_elk_layout()

    assert module.ARCH_DIR == DIAGRAM_ROOT / "architecture"


def test_governance_docs_match_active_diagram_counts() -> None:
    architecture_count = len(_source_files(MMD_COLLECTIONS["architecture"], ".mmd"))
    class_count = len(_source_files(MMD_COLLECTIONS["class-diagrams"], ".mmd"))
    foundation_count = len(_source_files(MMD_COLLECTIONS["foundation"], ".mmd"))
    template_count = int((DIAGRAM_ROOT / "_template.mmd").exists())
    mmd_total = architecture_count + class_count + foundation_count + template_count
    view_count = len(_source_files(VIEW_COLLECTION, ".mermaid"))

    assert (
        architecture_count,
        class_count,
        foundation_count,
        mmd_total,
        view_count,
    ) == (
        83,
        94,
        55,
        233,
        165,
    )

    docs_to_check = {
        REPO_ROOT
        / "docs"
        / "02-architecture"
        / "decisions"
        / "ADR-040-diagram-governance.md": [
            f"`architecture/` — {architecture_count}",
            f"`class-diagrams/` — {class_count}",
            f"`foundation/` — {foundation_count}",
            f"{mmd_total} `.mmd`",
            f"{view_count} `.mermaid`",
        ],
        DIAGRAM_ROOT / "governance" / "diagrams-index.md": [
            f"`architecture/` — {architecture_count}",
            f"`class-diagrams/` — {class_count}",
            f"`foundation/` — {foundation_count}",
            f"`views/` — {view_count}",
        ],
        DIAGRAM_ROOT / "governance" / "DIAGRAM-WORKFLOW-GUIDE.md": [
            f"**{mmd_total}** `.mmd`",
            f"**{view_count}** `.mermaid`",
            f"| `architecture/`   | {architecture_count}",
            f"| `class-diagrams/` | {class_count}",
            f"| `foundation/`     | {foundation_count}",
        ],
    }

    for doc, expected_fragments in docs_to_check.items():
        content = doc.read_text(encoding="utf-8")
        missing = [
            fragment for fragment in expected_fragments if fragment not in content
        ]
        assert not missing, f"{doc} is missing current baseline fragments: {missing}"


@pytest.mark.parametrize(
    ("collection", "suffix"),
    [
        ("architecture", ".mmd"),
        ("class-diagrams", ".mmd"),
        ("foundation", ".mmd"),
        ("views", ".mermaid"),
    ],
)
def test_source_diagrams_have_sibling_svg_artifacts(
    collection: str, suffix: str
) -> None:
    source_dir = (
        VIEW_COLLECTION if collection == "views" else MMD_COLLECTIONS[collection]
    )
    source_stems = _active_source_stems(source_dir, suffix)

    missing_svg = sorted(source_stems - _rendered_stems(source_dir, "svg", ".svg"))

    assert not missing_svg, (
        f"{collection} is missing rendered SVG artifacts: {missing_svg}"
    )


def test_legacy_mmd_diagrams_tree_has_no_canonical_sources() -> None:
    legacy_root = REPO_ROOT / "docs" / "02-architecture" / "mmd-diagrams"
    if not legacy_root.exists():
        return

    legacy_sources = sorted(
        path
        for path in legacy_root.rglob("*")
        if path.is_file() and path.suffix in {".mmd", ".mermaid"}
    )
    assert not legacy_sources, (
        "Legacy mmd-diagrams/ must not contain canonical diagram sources: "
        f"{[str(path.relative_to(REPO_ROOT)) for path in legacy_sources]}"
    )


@pytest.mark.parametrize(
    ("collection", "suffix"),
    [
        ("architecture", ".mmd"),
        ("class-diagrams", ".mmd"),
        ("foundation", ".mmd"),
        ("views", ".mermaid"),
    ],
)
def test_no_orphan_sibling_rendered_diagram_artifacts(
    collection: str, suffix: str
) -> None:
    source_dir = (
        VIEW_COLLECTION if collection == "views" else MMD_COLLECTIONS[collection]
    )
    source_stems = _active_source_stems(source_dir, suffix)

    orphan_svg = sorted(_rendered_stems(source_dir, "svg", ".svg") - source_stems)
    orphan_png = sorted(_rendered_stems(source_dir, "png", ".png") - source_stems)

    assert not orphan_svg, f"{collection} has orphan SVG artifacts: {orphan_svg}"
    assert not orphan_png, f"{collection} has orphan PNG artifacts: {orphan_png}"


def test_no_top_level_rendered_png_artifacts_for_canonical_sources() -> None:
    top_level_png = sorted((DIAGRAM_ROOT / "png").glob("*.png"))

    assert not top_level_png, (
        "Rendered PNG artifacts must live in the source collection sibling png/ tree: "
        f"{[path.name for path in top_level_png]}"
    )


def test_required_description_cards_cover_policy_backed_sources() -> None:
    architecture_missing = _missing_description_cards("architecture", ".mmd")
    foundation_missing = _missing_description_cards("foundation", ".mmd")
    views_missing = _missing_description_cards("views", ".mermaid")
    class_missing = _missing_primary_class_description_cards()

    assert not architecture_missing, (
        f"architecture descriptions missing: {architecture_missing}"
    )
    assert not foundation_missing, (
        f"foundation descriptions missing: {foundation_missing}"
    )
    assert not views_missing, f"views descriptions missing: {views_missing}"
    assert not class_missing, f"class primary descriptions missing: {class_missing}"


def _missing_description_cards(collection: str, suffix: str) -> list[str]:
    source_dir = (
        VIEW_COLLECTION if collection == "views" else MMD_COLLECTIONS[collection]
    )
    desc_dir = DESCRIPTION_ROOT / ("views" if collection == "views" else collection)
    source_stems = _active_source_stems(source_dir, suffix)
    description_stems = {
        path.stem for path in desc_dir.glob("*.md") if path.name != "INDEX.md"
    }
    return sorted(source_stems - description_stems)


def _missing_primary_class_description_cards() -> list[str]:
    source_stems = _active_source_stems(MMD_COLLECTIONS["class-diagrams"], ".mmd")
    required_stems = {
        stem for stem in source_stems if _is_primary_class_description_stem(stem)
    }
    description_stems = {
        path.stem
        for path in (DESCRIPTION_ROOT / "class").glob("*.md")
        if path.name != "INDEX.md"
    }
    return sorted(required_stems - description_stems)


def _is_primary_class_description_stem(stem: str) -> bool:
    """Return whether a class diagram requires an individual narrative card."""
    if stem == "07-application-core-services-frontmatter-sandbox":
        return False
    if stem.startswith("90-pkg-"):
        return False
    return re.match(r"^(0[1-9]|1[0-6])-", stem) is not None
