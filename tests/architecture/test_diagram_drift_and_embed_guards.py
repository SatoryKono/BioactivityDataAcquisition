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
from __future__ import annotations

import importlib.util
import os
import re
import stat
import sys
from pathlib import Path
from types import ModuleType

import pytest

from tests.architecture._platform_skip_support import mounted_worktree_skip_reason

pytestmark = pytest.mark.architecture

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
DIAGRAM_ROOT = REPO_ROOT / "docs" / "02-architecture" / "diagrams"
VIEW_COLLECTION = DIAGRAM_ROOT / "views"
MMD_COLLECTIONS: dict[str, Path] = {
    "architecture": DIAGRAM_ROOT / "architecture",
    "class-diagrams": DIAGRAM_ROOT / "class-diagrams",
    "foundation": DIAGRAM_ROOT / "foundation",
}

_DECL_LINE_RE = re.compile(
    r"^(flowchart|graph|stateDiagram|classDiagram|sequenceDiagram|erDiagram|"
    r"mindmap|gantt|pie|xychart|C4Context|C4Container|C4Component|C4Dynamic)\b",
    flags=re.IGNORECASE,
)
_PARENT_SOURCE_RE = re.compile(r"^%%\s*Parent source:\s*(.+?)\s*$")
# Match documentation_sync active-doc exclusions, plus diagram companion dumps
# that F014 does not author. Scanning those trees on Windows cloud checkouts
# can block in read_text() until pytest-timeout (90s) fires.
_SKIPPED_DIR_NAMES = frozenset(
    {"99-archive", "archive", "reports", "site", "exports", "generated"}
)
_DIAGRAM_COMPANION_DIR_NAMES = frozenset({"descriptions", "bundles"})
_MERMAID_FENCE_MARKERS = (b"```mermaid", b"``` mermaid")
# Authored docs in this tree stay well under 400 KiB; refuse multi-MB slurps.
_MAX_ACTIVE_DOC_BYTES = 1_048_576
# Windows cloud placeholders (OneDrive/Google Drive). Reading them hydrates
# remotely and can hang the 90s architecture-fast budget.
_FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
_FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000
_CLOUD_PLACEHOLDER_ATTRIBUTES = (
    _FILE_ATTRIBUTE_RECALL_ON_OPEN | _FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
)


def _load_apply_elk_layout() -> ModuleType:
    module_path = REPO_ROOT / "scripts" / "diagrams" / "fix" / "apply_elk_layout.py"
    spec = importlib.util.spec_from_file_location(
        "apply_elk_layout_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _active_source_stems(directory: Path, suffix: str) -> set[str]:
    if not directory.exists():
        return set()
    return {
        p.stem
        for p in sorted(directory.glob(f"*{suffix}"))
        if p.is_file() and not p.name.startswith("_")
    }


def _rendered_stems(source_dir: Path, rendered_dir_name: str, suffix: str) -> set[str]:
    rendered_dir = source_dir / rendered_dir_name
    if not rendered_dir.exists():
        return set()
    return {p.stem for p in rendered_dir.glob(f"*{suffix}") if p.is_file()}


def _prune_walk_dirnames(root: Path, dirpath: str, dirnames: list[str]) -> None:
    """Drop archive/generated/companion trees before os.walk descends."""
    base = Path(dirpath)
    try:
        rel_parts = base.relative_to(root).parts
    except ValueError:
        dirnames[:] = []
        return
    skip = set(_SKIPPED_DIR_NAMES)
    if rel_parts[:2] == ("02-architecture", "diagrams"):
        skip |= _DIAGRAM_COMPANION_DIR_NAMES
    dirnames[:] = [item for item in dirnames if item not in skip]


def _is_cloud_placeholder(st: os.stat_result) -> bool:
    attrs = int(getattr(st, "st_file_attributes", 0) or 0)
    return bool(attrs & _CLOUD_PLACEHOLDER_ATTRIBUTES)


def _read_active_markdown_lines(path: Path) -> list[str] | None:
    """Return lines only for regular local files that contain a mermaid fence."""
    try:
        st = path.stat()
    except OSError:
        return None
    if not stat.S_ISREG(st.st_mode) or _is_cloud_placeholder(st):
        return None
    if st.st_size > _MAX_ACTIVE_DOC_BYTES:
        raise AssertionError(
            f"{path} is {st.st_size} bytes; F014 refuses to slurp files larger "
            f"than {_MAX_ACTIVE_DOC_BYTES} bytes"
        )
    if st.st_size == 0:
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if not any(marker in raw for marker in _MERMAID_FENCE_MARKERS):
        return None
    return raw.decode("utf-8").splitlines()


def _active_markdown_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        _prune_walk_dirnames(root, dirpath, dirnames)
        base = Path(dirpath)
        for filename in filenames:
            if not filename.endswith(".md"):
                continue
            path = base / filename
            try:
                if path.is_file():
                    paths.append(path)
            except OSError:
                continue
    return sorted(paths)


def test_architecture_svg_coverage_for_all_mmd() -> None:
    """F001: architecture .mmd MUST have sibling rendered SVG artifacts."""
    source_dir = MMD_COLLECTIONS["architecture"]
    source_stems = _active_source_stems(source_dir, ".mmd")
    rendered_stems = _rendered_stems(source_dir, "svg", ".svg")
    missing_svg = sorted(source_stems - rendered_stems)
    assert not missing_svg, f"architecture missing rendered SVG: {missing_svg}"


def test_full_mermaid_matches_foundation_mmd() -> None:
    """F006: views/*-full.mermaid body MUST match declared parent source."""

    def extract_body(path: Path) -> str:
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, ln in enumerate(lines):
            s = ln.strip()
            if not s or s.startswith("%%"):
                continue
            if _DECL_LINE_RE.match(s):
                # Ignore metadata + ELK init blocks; compare only the diagram body.
                body_lines = [x.strip() for x in lines[i:]]
                while body_lines and body_lines[-1] == "":
                    body_lines.pop()
                return "\n".join(body_lines)
        raise AssertionError(f"Diagram declaration not found: {path}")

    def extract_parent_source(path: Path) -> Path:
        lines = path.read_text(encoding="utf-8").splitlines()
        for ln in lines:
            match = _PARENT_SOURCE_RE.match(ln.strip())
            if match:
                return REPO_ROOT / match.group(1)
        raise AssertionError(f"Full view missing Parent source metadata: {path}")

    source_dirs = frozenset(MMD_COLLECTIONS.values())
    for view_path in sorted(VIEW_COLLECTION.glob("*-full.mermaid")):
        if not view_path.is_file() or view_path.name.startswith("_"):
            continue
        mmd_path = extract_parent_source(view_path)
        assert mmd_path.parent in source_dirs, (
            f"Full view parent must be a canonical source: {view_path} -> {mmd_path}"
        )
        assert mmd_path.exists(), f"Missing parent source for full view: {view_path}"
        mmd_body = extract_body(mmd_path)
        view_body = extract_body(view_path)
        assert mmd_body == view_body, (
            f"Drift in diagram body for {mmd_path.relative_to(DIAGRAM_ROOT)} â†” {view_path}"
        )


def test_no_orphan_svg_without_source() -> None:
    """F012: canonical rendered SVG artifacts MUST NOT be orphans."""
    for collection, source_dir in (
        ("architecture", MMD_COLLECTIONS["architecture"]),
        ("class-diagrams", MMD_COLLECTIONS["class-diagrams"]),
        ("foundation", MMD_COLLECTIONS["foundation"]),
        ("views", VIEW_COLLECTION),
    ):
        suffix = ".mmd" if collection != "views" else ".mermaid"
        source_stems = _active_source_stems(source_dir, suffix)
        rendered_stems = _rendered_stems(source_dir, "svg", ".svg")
        orphan_svg = sorted(rendered_stems - source_stems)
        assert not orphan_svg, (
            f"{collection} has orphan SVG artifacts without source: {orphan_svg}"
        )


def test_apply_elk_default_dir_is_canonical() -> None:
    """F004: apply_elk_layout.py default dir MUST be canonical architecture tree."""
    module = _load_apply_elk_layout()
    assert module.ARCH_DIR == DIAGRAM_ROOT / "architecture", (
        f"ARCH_DIR mismatch: {module.ARCH_DIR}"
    )


def test_active_markdown_paths_skip_generated_companion_trees() -> None:
    """F014 walks authored docs, not generated diagram dumps or export trees."""
    relative = [
        path.relative_to(DOCS_ROOT).as_posix()
        for path in _active_markdown_paths(DOCS_ROOT)
    ]
    assert relative
    assert all(not item.startswith("99-archive/") for item in relative)
    assert all(not item.startswith("exports/") for item in relative)
    assert all("/generated/" not in f"/{item}/" for item in relative)
    assert all(
        not item.startswith("02-architecture/diagrams/descriptions/")
        for item in relative
    )
    assert all(
        not item.startswith("02-architecture/diagrams/bundles/") for item in relative
    )
    assert "02-architecture/system-context.md" in relative


@pytest.mark.timeout(180)
def test_embedded_mermaid_in_active_docs_valid() -> None:
    """F014: fenced ```mermaid blocks in active docs must look like real Mermaid."""
    skip_reason = mounted_worktree_skip_reason()
    if skip_reason is not None:
        pytest.skip(skip_reason)

    placeholder_re = re.compile(r"\b(placeholder|TODO|FIXME|stub)\b", re.IGNORECASE)
    init_re = re.compile(r"%%\s*\{\s*init\s*:", re.IGNORECASE)
    metadata_directive_re = re.compile(r"^%%\s*@", re.IGNORECASE)

    def iter_fenced_mermaid_blocks(md_lines: list[str]) -> list[tuple[list[str], int]]:
        blocks: list[tuple[list[str], int]] = []
        in_block = False
        current: list[str] = []
        block_start_line = 0

        for idx, raw in enumerate(md_lines, start=1):
            line = raw.rstrip("\n")
            if not in_block:
                if re.match(r"^```\s*mermaid\s*$", line.strip()):
                    in_block = True
                    current = []
                    block_start_line = idx
                continue

            # closing fence
            if line.strip().startswith("```"):
                blocks.append((current, block_start_line))
                in_block = False
                current = []
                continue

            current.append(line)

        if in_block:
            raise AssertionError("Unclosed ```mermaid fenced block in Markdown file.")

        return blocks

    md_paths = _active_markdown_paths(DOCS_ROOT)

    issues: list[str] = []
    for md_path in md_paths:
        lines = _read_active_markdown_lines(md_path)
        if lines is None:
            continue
        blocks = iter_fenced_mermaid_blocks(lines)
        for block_lines, start_ln in blocks:
            block_text = "\n".join(block_lines).strip()
            if not block_text:
                issues.append(f"{md_path} at L{start_ln}: empty ```mermaid block")
                continue
            if placeholder_re.search(block_text):
                issues.append(
                    f"{md_path} at L{start_ln}: placeholder markers in ```mermaid block"
                )
                continue

            has_decl = any(_DECL_LINE_RE.match(ln.strip()) for ln in block_lines)
            has_init = any(init_re.search(ln) for ln in block_lines)
            has_metadata_directive = any(
                metadata_directive_re.match(ln.strip()) for ln in block_lines
            )
            if not has_decl and not has_init and not has_metadata_directive:
                issues.append(
                    f"{md_path} at L{start_ln}: ```mermaid block lacks diagram "
                    "declaration, init directive, or metadata directive"
                )

    assert not issues, "Invalid/unsupported embedded mermaid blocks:\n" + "\n".join(
        issues
    )
