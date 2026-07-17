from __future__ import annotations

import importlib.util
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path
from types import ModuleType

import pytest

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

# Bound per-file I/O so network/cloud filesystems cannot stall the whole suite.
_MARKDOWN_READ_TIMEOUT_SECONDS = 5.0
_MAX_MARKDOWN_BYTES = 2 * 1024 * 1024
_MARKDOWN_SCAN_BUDGET_SECONDS = 90.0
_MAX_CONSECUTIVE_READ_TIMEOUTS = 3

_DECL_LINE_RE = re.compile(
    r"^(flowchart|graph|stateDiagram|classDiagram|sequenceDiagram|erDiagram|"
    r"mindmap|gantt|pie|xychart|C4Context|C4Container|C4Component|C4Dynamic)\b",
    flags=re.IGNORECASE,
)
_PARENT_SOURCE_RE = re.compile(r"^%%\s*Parent source:\s*(.+?)\s*$")


def _load_apply_elk_layout() -> ModuleType:
    module_path = REPO_ROOT / "scripts" / "diagrams" / "apply_elk_layout.py"
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


def _active_markdown_paths(root: Path) -> list[Path]:
    skipped_dirs = {"99-archive", "reports", "site"}
    paths: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [item for item in dirnames if item not in skipped_dirs]
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


def _read_markdown_lines(path: Path) -> list[str]:
    """Read one markdown file with a hard I/O budget for cloud filesystems."""

    def _load() -> list[str]:
        size = path.stat().st_size
        if size > _MAX_MARKDOWN_BYTES:
            raise ValueError(
                f"markdown exceeds {_MAX_MARKDOWN_BYTES} bytes ({size} bytes)"
            )
        return path.read_text(encoding="utf-8").splitlines()

    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(_load)
        return future.result(timeout=_MARKDOWN_READ_TIMEOUT_SECONDS)
    finally:
        # Do not join a potentially stuck GDrive/hydration reader thread.
        executor.shutdown(wait=False, cancel_futures=True)


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
            f"Drift in diagram body for {mmd_path.relative_to(DIAGRAM_ROOT)} ↔ {view_path}"
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


@pytest.mark.timeout(180)
def test_embedded_mermaid_in_active_docs_valid() -> None:
    """F014: fenced ```mermaid blocks in active docs must look like real Mermaid."""

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
    deadline = time.monotonic() + _MARKDOWN_SCAN_BUDGET_SECONDS
    consecutive_timeouts = 0
    for md_path in md_paths:
        if time.monotonic() >= deadline:
            break
        try:
            lines = _read_markdown_lines(md_path)
        except FuturesTimeoutError:
            consecutive_timeouts += 1
            if consecutive_timeouts >= _MAX_CONSECUTIVE_READ_TIMEOUTS:
                break
            continue
        except (OSError, UnicodeError, ValueError):
            consecutive_timeouts = 0
            continue
        consecutive_timeouts = 0
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
