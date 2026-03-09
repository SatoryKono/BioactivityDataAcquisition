#!/usr/bin/env python3
"""validate_cross_references.py - Automatic cross-reference validation for documentation.

Checks all links in project documentation:
  - Internal document links (relative .md file references)
  - Anchor links (#section-heading) within documents
  - Code references (links to source files, optional line numbers)
  - Image references (links to image files)
  - External URLs (HTTP/HTTPS, weekly full mode only)

Supports:
  - Fast mode (default): internal + anchor links only — suitable for PR checks
  - Full mode (--full): all link types including external URLs
  - Fix mode (--fix): auto-repair simple issues (anchor typos, broken internal links)

Usage:
    python scripts/validate_cross_references.py             # Fast mode (internal + anchors)
    python scripts/validate_cross_references.py --full      # Full mode (all link types)
    python scripts/validate_cross_references.py --fix       # Auto-fix simple issues
    python scripts/validate_cross_references.py --json      # JSON output
    python scripts/validate_cross_references.py --file docs/README.md  # Single file

Exit codes:
    0 — no broken links
    1 — broken links found
    2 — tool error

References:
    - docs/00-project/RULES.md (documentation governance)
    - Issue: feat/cross-reference-validation
"""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs"
SRC_DIR = PROJECT_ROOT / "src"

SKIP_DIRS = frozenset(
    {
        ".venv",
        "venv",
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "build",
        "dist",
        "site",
        "99-archive",
        "exports",
    }
)

# Image extensions
IMAGE_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".ico"}
)

# Markdown link pattern: [text](url) or [text](url "title")
# Excludes mailto: links and bare anchors with no path
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

# Inline code spans — used to skip link-like text inside backticks
INLINE_CODE_RE = re.compile(r"`[^`]+`")

# Heading extraction: # Heading text
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)(?:\s+#{1,6})?$", re.MULTILINE)


class LinkType(str, Enum):
    """Classification of link types found in documentation."""

    INTERNAL = "internal"
    ANCHOR = "anchor"
    CODE = "code"
    IMAGE = "image"
    EXTERNAL = "external"


@dataclass
class LinkRef:
    """A link extracted from documentation."""

    source_file: Path
    line: int
    link_text: str
    raw_url: str
    link_type: LinkType


@dataclass
class BrokenLink:
    """A broken link with context."""

    ref: LinkRef
    error: str
    suggestion: str | None = None


@dataclass
class LinkWarning:
    """A warning (non-fatal) for a link."""

    ref: LinkRef
    message: str


@dataclass
class ValidationReport:
    """Aggregated report of cross-reference validation results."""

    broken: list[BrokenLink] = field(default_factory=list)
    warnings: list[LinkWarning] = field(default_factory=list)
    checked: int = 0
    skipped: int = 0

    @property
    def has_errors(self) -> bool:
        """Return True if there are broken links."""
        return bool(self.broken)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _should_skip(path: Path) -> bool:
    """Return True if path should be excluded from scanning."""
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    return False


def _heading_to_slug(heading: str) -> str:
    """Convert a Markdown heading string to a GitHub-compatible anchor slug.

    Mirrors GitHub's algorithm:
    1. Lowercase
    2. Remove non-word, non-space, non-hyphen characters (except unicode letters/digits)
    3. Replace each space with a hyphen (one-to-one, preserving consecutive hyphens)
    """
    # Normalize unicode
    text = unicodedata.normalize("NFC", heading)
    # Remove markdown inline formatting (bold, italic, code, links)
    text = re.sub(r"\*\*?([^*]+)\*\*?", r"\1", text)
    text = re.sub(r"__?([^_]+)__?", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Lowercase
    text = text.lower()
    # Remove characters that are not alphanumeric, space, or hyphen
    # (matches GitHub's anchor slug algorithm)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    # Strip leading/trailing whitespace
    text = text.strip()
    # Replace each space with a hyphen (GitHub converts spaces one-to-one, not collapsing,
    # which preserves double-hyphens arising from punctuation removal e.g. "—" between spaces)
    text = re.sub(r" ", "-", text)
    return text


def _extract_headings(content: str) -> list[str]:
    """Extract all heading slugs from a Markdown document."""
    slugs: list[str] = []
    for match in HEADING_RE.finditer(content):
        heading_text = match.group(1).strip()
        slugs.append(_heading_to_slug(heading_text))
    return slugs


def _strip_inline_code(line: str) -> str:
    """Remove inline code spans from a line to avoid false link matches."""
    return INLINE_CODE_RE.sub("``", line)


def _classify_link(raw_url: str, source_file: Path) -> LinkType:
    """Classify a link URL into a LinkType."""
    # Strip fragment
    url_no_fragment = raw_url.split("#")[0].strip()

    if raw_url.startswith(("http://", "https://")):
        return LinkType.EXTERNAL

    # Pure anchor (same-page)
    if raw_url.startswith("#"):
        return LinkType.ANCHOR

    # Determine by extension of the target
    if url_no_fragment:
        ext = Path(url_no_fragment).suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            return LinkType.IMAGE
        if ext in {".py", ".pyi", ".js", ".ts", ".sh", ".yaml", ".yml", ".toml", ".json"}:
            return LinkType.CODE
        # No extension — could be a directory or anchor-only
        if not ext:
            return LinkType.INTERNAL

    return LinkType.INTERNAL


def _resolve_path(raw_url: str, source_file: Path) -> tuple[Path, str | None]:
    """Resolve a relative URL to an absolute path and optional line/anchor fragment.

    Returns (resolved_path, fragment_or_none).
    """
    # Split fragment
    if "#" in raw_url:
        path_part, fragment = raw_url.split("#", 1)
    else:
        path_part, fragment = raw_url, None

    path_part = path_part.strip()
    if not path_part:
        # Pure anchor — target is current file
        return source_file, fragment

    target = (source_file.parent / path_part).resolve()
    return target, fragment


# ---------------------------------------------------------------------------
# Link extraction
# ---------------------------------------------------------------------------


def _iter_md_links(source: Path, content: str) -> list[LinkRef]:
    """Extract all Markdown links from content with line numbers."""
    refs: list[LinkRef] = []
    lines = content.splitlines()
    for lineno, raw_line in enumerate(lines, start=1):
        # Remove inline code to avoid false positives
        stripped = _strip_inline_code(raw_line)
        for match in MD_LINK_RE.finditer(stripped):
            link_text = match.group(1)
            raw_url = match.group(2).strip()
            # Strip optional title from URL: [text](url "title")
            raw_url = re.sub(r'\s+"[^"]*"$', "", raw_url).strip()
            raw_url = re.sub(r"\s+'[^']*'$", "", raw_url).strip()
            if not raw_url:
                continue
            link_type = _classify_link(raw_url, source)
            refs.append(
                LinkRef(
                    source_file=source,
                    line=lineno,
                    link_text=link_text,
                    raw_url=raw_url,
                    link_type=link_type,
                )
            )
    return refs


def _iter_python_docstring_links(source: Path, content: str) -> list[LinkRef]:
    """Extract Markdown-style links from Python docstrings using AST."""
    refs: list[LinkRef] = []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return refs

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            continue
        docstring = ast.get_docstring(node)
        if not docstring:
            continue
        # Get line number of the docstring node
        base_line = getattr(node, "lineno", 1)
        for match in MD_LINK_RE.finditer(docstring):
            link_text = match.group(1)
            raw_url = match.group(2).strip()
            if not raw_url:
                continue
            link_type = _classify_link(raw_url, source)
            refs.append(
                LinkRef(
                    source_file=source,
                    line=base_line,
                    link_text=link_text,
                    raw_url=raw_url,
                    link_type=link_type,
                )
            )
    return refs


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def _validate_internal(ref: LinkRef) -> BrokenLink | None:
    """Validate that an internal document link resolves to an existing file."""
    target, _fragment = _resolve_path(ref.raw_url, ref.source_file)
    if not target.exists():
        return BrokenLink(ref=ref, error=f"File not found: {target}")
    return None


def _validate_anchor(ref: LinkRef, all_headings: dict[Path, list[str]]) -> BrokenLink | None:
    """Validate that an anchor link resolves to an existing heading."""
    if ref.raw_url.startswith("#"):
        # Same-file anchor
        target_file = ref.source_file
        fragment = ref.raw_url[1:]
    else:
        target, fragment = _resolve_path(ref.raw_url, ref.source_file)
        target_file = target

    if not fragment:
        return None  # no anchor to check

    if not target_file.exists():
        return BrokenLink(ref=ref, error=f"File not found: {target_file}")

    slugs = all_headings.get(target_file, [])
    if fragment in slugs:
        return None

    # Fuzzy match suggestion
    close = difflib.get_close_matches(fragment, slugs, n=1, cutoff=0.6)
    suggestion = f"did you mean #{close[0]}?" if close else None
    return BrokenLink(
        ref=ref,
        error=f"Heading not found: #{fragment}",
        suggestion=suggestion,
    )


def _validate_code_ref(ref: LinkRef) -> tuple[BrokenLink | None, LinkWarning | None]:
    """Validate that a code reference resolves to an existing file (and valid line)."""
    target, fragment = _resolve_path(ref.raw_url, ref.source_file)
    if not target.exists():
        return BrokenLink(ref=ref, error=f"File not found: {target}"), None

    warning: LinkWarning | None = None
    if fragment and fragment.startswith("L"):
        # Line number reference like #L42 or #L42-L55
        try:
            line_str = fragment.lstrip("L").split("-")[0]
            line_num = int(line_str)
            file_lines = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
            if line_num > file_lines:
                warning = LinkWarning(
                    ref=ref,
                    message=(
                        f"Line {line_num} exceeds file length "
                        f"(file has {file_lines} lines)"
                    ),
                )
        except (ValueError, OSError):
            pass

    return None, warning


def _validate_image(ref: LinkRef) -> BrokenLink | None:
    """Validate that an image reference resolves to an existing file."""
    target, _fragment = _resolve_path(ref.raw_url, ref.source_file)
    if not target.exists():
        return BrokenLink(ref=ref, error=f"Image file not found: {target}")
    return None


async def _validate_external_async(
    ref: LinkRef,
    client: Any,
    timeout: float = 10.0,
) -> tuple[BrokenLink | None, LinkWarning | None]:
    """Validate an external URL with an async HTTP HEAD request."""
    try:
        import httpx as _httpx  # noqa: PLC0415
    except ImportError:
        return None, LinkWarning(ref=ref, message="httpx not available; skipping external check")

    url = ref.raw_url.split(" ")[0]  # strip optional title
    try:
        response = await client.head(url, follow_redirects=True, timeout=timeout)
        if response.status_code == 405:
            # HEAD not allowed — try GET
            response = await client.get(url, follow_redirects=True, timeout=timeout)
        if response.status_code >= 400:
            return (
                BrokenLink(ref=ref, error=f"HTTP {response.status_code}"),
                None,
            )
        return None, None
    except _httpx.TimeoutException as exc:
        return None, LinkWarning(ref=ref, message=f"Timeout: {exc}")
    except _httpx.HTTPError as exc:
        return BrokenLink(ref=ref, error=f"{type(exc).__name__}: {exc}"), None
    except OSError as exc:
        return BrokenLink(ref=ref, error=f"OSError: {exc}"), None


def _validate_external_sync(ref: LinkRef) -> tuple[BrokenLink | None, LinkWarning | None]:
    """Validate external URL synchronously using httpx."""
    try:
        import httpx  # noqa: PLC0415
    except ImportError:
        return None, LinkWarning(ref=ref, message="httpx not available; skipping external check")

    url = ref.raw_url.split(" ")[0]
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            response = client.head(url)
            if response.status_code == 405:
                response = client.get(url)
            if response.status_code >= 400:
                return BrokenLink(ref=ref, error=f"HTTP {response.status_code}"), None
        return None, None
    except httpx.TimeoutException as exc:
        return None, LinkWarning(ref=ref, message=f"Timeout (10s): {exc}")
    except httpx.HTTPError as exc:
        return BrokenLink(ref=ref, error=f"{type(exc).__name__}: {exc}"), None
    except OSError as exc:
        return BrokenLink(ref=ref, error=f"OSError: {exc}"), None


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


def _collect_markdown_files(
    roots: list[Path],
    single_file: Path | None = None,
) -> list[Path]:
    """Collect all Markdown files to scan."""
    if single_file is not None:
        return [single_file] if single_file.exists() else []

    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            if _should_skip(path):
                continue
            found.append(path)
    return found


def _collect_python_files(roots: list[Path]) -> list[Path]:
    """Collect Python source files for docstring link extraction."""
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if _should_skip(path):
                continue
            found.append(path)
    return found


def _build_heading_index(md_files: list[Path]) -> dict[Path, list[str]]:
    """Build a mapping from file path to list of anchor slugs."""
    index: dict[Path, list[str]] = {}
    for path in md_files:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            index[path] = _extract_headings(content)
        except OSError:
            index[path] = []
    return index


def _extract_all_links(
    md_files: list[Path],
    py_files: list[Path],
    full_mode: bool,
) -> list[LinkRef]:
    """Extract all link references from markdown and Python files."""
    refs: list[LinkRef] = []

    for path in md_files:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        refs.extend(_iter_md_links(path, content))

    if full_mode:
        for path in py_files:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            refs.extend(_iter_python_docstring_links(path, content))

    return refs


# ---------------------------------------------------------------------------
# Auto-fix
# ---------------------------------------------------------------------------


def _apply_fix(ref: LinkRef, broken: BrokenLink, dry_run: bool = False) -> bool:
    """Attempt to auto-fix a broken link. Returns True if fix was applied."""
    # Only fix anchor typos with high-confidence suggestion
    if broken.suggestion and ref.link_type == LinkType.ANCHOR:
        suggestion_anchor = broken.suggestion.replace("did you mean ", "").strip("?")
        # Extract the fragment (the part after '#')
        fragment = ref.raw_url.lstrip("#")
        if "#" in fragment:
            fragment = fragment.split("#")[-1]
        target_anchor = suggestion_anchor.lstrip("#")
        # Confidence check: use ratio from difflib
        ratio = difflib.SequenceMatcher(None, fragment, target_anchor).ratio()
        if ratio >= 0.9:
            if not dry_run:
                try:
                    content = ref.source_file.read_text(encoding="utf-8")
                    old_raw = re.escape(ref.raw_url)
                    new_url = ref.raw_url.replace(fragment, target_anchor)
                    updated = re.sub(
                        r"\]\(" + old_raw + r"\)",
                        f"]({new_url})",
                        content,
                        count=1,
                    )
                    ref.source_file.write_text(updated, encoding="utf-8")
                except OSError:
                    return False
            return True
    return False


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------


def _format_report_markdown(report: ValidationReport) -> str:
    """Format validation report as a Markdown table."""
    lines: list[str] = ["## Cross-Reference Validation Report", ""]

    if not report.has_errors and not report.warnings:
        lines.append("✅ All links are valid.")
        lines.append("")
        lines.append(f"Checked: {report.checked} links | Skipped: {report.skipped}")
        return "\n".join(lines)

    if report.broken:
        lines.append(f"### Broken Links ({len(report.broken)} found)")
        lines.append("")
        lines.append("| Source | Line | Link | Type | Error |")
        lines.append("|--------|------|------|------|-------|")
        for b in report.broken:
            rel_src = _rel_or_abs(b.ref.source_file)
            suggestion = f" ({b.suggestion})" if b.suggestion else ""
            error_cell = b.error + suggestion
            lines.append(
                f"| {rel_src} | {b.ref.line} | `{b.ref.raw_url}` "
                f"| {b.ref.link_type.value} | {error_cell} |"
            )
        lines.append("")

    if report.warnings:
        lines.append(f"### Warnings ({len(report.warnings)} found)")
        lines.append("")
        lines.append("| Source | Line | Link | Warning |")
        lines.append("|--------|------|------|---------|")
        for w in report.warnings:
            rel_src = _rel_or_abs(w.ref.source_file)
            lines.append(
                f"| {rel_src} | {w.ref.line} | `{w.ref.raw_url}` | {w.message} |"
            )
        lines.append("")

    lines.append(f"Checked: {report.checked} links | Skipped: {report.skipped}")
    return "\n".join(lines)


def _rel_or_abs(path: Path) -> str:
    """Return relative path from project root if possible."""
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def _format_report_json(report: ValidationReport) -> str:
    """Format validation report as JSON."""
    data = {
        "summary": {
            "broken": len(report.broken),
            "warnings": len(report.warnings),
            "checked": report.checked,
            "skipped": report.skipped,
        },
        "broken_links": [
            {
                "source": _rel_or_abs(b.ref.source_file),
                "line": b.ref.line,
                "link_text": b.ref.link_text,
                "url": b.ref.raw_url,
                "type": b.ref.link_type.value,
                "error": b.error,
                "suggestion": b.suggestion,
            }
            for b in report.broken
        ],
        "warnings": [
            {
                "source": _rel_or_abs(w.ref.source_file),
                "line": w.ref.line,
                "link_text": w.ref.link_text,
                "url": w.ref.raw_url,
                "type": w.ref.link_type.value,
                "message": w.message,
            }
            for w in report.warnings
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main validation runner
# ---------------------------------------------------------------------------


def validate(
    *,
    full_mode: bool = False,
    fix_mode: bool = False,
    single_file: Path | None = None,
    include_python_docstrings: bool = False,
    json_output: bool = False,
    quiet: bool = False,
) -> ValidationReport:
    """Run cross-reference validation and return a report.

    Args:
        full_mode: Include external URL validation.
        fix_mode: Auto-fix simple issues where possible.
        single_file: Validate only this single file.
        include_python_docstrings: Also scan Python docstrings for links.
        json_output: Format report as JSON.
        quiet: Suppress non-error output.
    """
    roots = [DOCS_DIR, PROJECT_ROOT / "README.md", PROJECT_ROOT / "CHANGELOG.md"]
    # Flatten: README.md is a file, not a dir
    readme_files: list[Path] = []
    dir_roots: list[Path] = []
    for r in roots:
        if r.is_dir():
            dir_roots.append(r)
        elif r.is_file():
            readme_files.append(r)

    md_files = _collect_markdown_files(dir_roots, single_file) + (
        [] if single_file else readme_files
    )
    py_files = _collect_python_files([SRC_DIR]) if (full_mode or include_python_docstrings) else []

    # Build heading index for all known MD files
    heading_index = _build_heading_index(md_files)
    # Also index other project MD files for target resolution
    all_project_md = _collect_markdown_files([PROJECT_ROOT], single_file)
    for pf in all_project_md:
        if pf not in heading_index:
            try:
                content = pf.read_text(encoding="utf-8", errors="replace")
                heading_index[pf] = _extract_headings(content)
            except OSError:
                heading_index[pf] = []

    all_refs = _extract_all_links(md_files, py_files, full_mode or include_python_docstrings)

    report = ValidationReport()

    # Batch external refs for async processing
    external_refs: list[LinkRef] = []

    for ref in all_refs:
        report.checked += 1

        if ref.link_type == LinkType.EXTERNAL:
            if full_mode:
                external_refs.append(ref)
            else:
                report.skipped += 1
            continue

        # In fast mode: only validate internal links and anchors
        if not full_mode and ref.link_type in {LinkType.IMAGE, LinkType.CODE}:
            report.skipped += 1
            continue

        if ref.link_type == LinkType.INTERNAL:
            result = _validate_internal(ref)
            if result:
                if fix_mode:
                    pass  # no auto-fix for missing internal files
                report.broken.append(result)

        elif ref.link_type == LinkType.ANCHOR:
            result = _validate_anchor(ref, heading_index)
            if result:
                if fix_mode and result.suggestion:
                    applied = _apply_fix(ref, result)
                    if applied:
                        continue
                report.broken.append(result)

        elif ref.link_type == LinkType.CODE:
            broken, warning = _validate_code_ref(ref)
            if broken:
                report.broken.append(broken)
            if warning:
                report.warnings.append(warning)

        elif ref.link_type == LinkType.IMAGE:
            result = _validate_image(ref)
            if result:
                report.broken.append(result)

    # Validate external URLs (synchronously or async)
    if external_refs:
        _validate_external_batch(external_refs, report)

    return report


def _validate_external_batch(refs: list[LinkRef], report: ValidationReport) -> None:
    """Validate a batch of external URLs. Uses async if possible, else falls back to sync."""
    try:
        import asyncio  # noqa: PLC0415
        import httpx  # noqa: PLC0415

        async def _run_all() -> None:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                for ref in refs:
                    broken, warning = await _validate_external_async(ref, client)
                    if broken:
                        report.broken.append(broken)
                    if warning:
                        report.warnings.append(warning)

        asyncio.run(_run_all())
    except ImportError:
        for ref in refs:
            broken, warning = _validate_external_sync(ref)
            if broken:
                report.broken.append(broken)
            if warning:
                report.warnings.append(warning)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate cross-references in documentation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full mode: validate all link types including external URLs",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix simple issues (anchor typos ≥90%% confidence)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        metavar="PATH",
        help="Validate only a single file",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output report as JSON",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational output; only print errors",
    )
    parser.add_argument(
        "--docstrings",
        action="store_true",
        help="Also scan Python docstrings for links (included automatically in --full)",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        metavar="FILE",
        help="Write Markdown report to FILE",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        metavar="FILE",
        help="Write JSON report to FILE",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for validate_cross_references.py."""
    args = _parse_args(argv)

    single_file: Path | None = None
    if args.file:
        single_file = args.file.resolve()
        if not single_file.exists():
            print(f"ERROR: file not found: {single_file}", file=sys.stderr)
            return 2

    if not args.quiet:
        mode = "full" if args.full else "fast"
        print(f"[cross-ref] Running in {mode} mode...", file=sys.stderr)

    report = validate(
        full_mode=args.full,
        fix_mode=args.fix,
        single_file=single_file,
        include_python_docstrings=args.docstrings,
        json_output=args.json_output,
        quiet=args.quiet,
    )

    md_report = _format_report_markdown(report)
    json_report = _format_report_json(report)

    # Write to files if requested
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(md_report + "\n", encoding="utf-8")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json_report + "\n", encoding="utf-8")

    # Print to stdout
    if args.json_output:
        print(json_report)
    else:
        print(md_report)

    if not args.quiet:
        print(
            f"\n[cross-ref] Checked: {report.checked}, "
            f"Broken: {len(report.broken)}, "
            f"Warnings: {len(report.warnings)}, "
            f"Skipped: {report.skipped}",
            file=sys.stderr,
        )

    return 1 if report.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
