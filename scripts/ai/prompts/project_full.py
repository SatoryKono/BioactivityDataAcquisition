"""Keep relative links valid in generated project/full prompt pastes."""

from __future__ import annotations

import os
import re
from pathlib import Path

from scripts.ai.prompts.registry import (
    PROMPTS_ROOT,
    REPO_ROOT,
    find_entry,
    load_registry,
)

PROJECT_FULL_ROOT = PROMPTS_ROOT / "library" / "audit" / "project" / "full"

_SOURCE_ID_RE = re.compile(
    r"\A<!-- GENERATED full paste\. Source id: (?P<id>prompt\.[a-z0-9.-]+)\."
)
_MARKDOWN_LINK_RE = re.compile(
    r"(?P<prefix>\[[^\]\n]*\]\()"
    r"(?P<target><[^>\n]+>|[^)\s]+)"
    r"(?P<suffix>[^)\n]*\))"
)


def _split_target(raw_target: str) -> tuple[str, str, bool]:
    """Return filesystem path, query/fragment suffix, and angle-bracket form."""
    angle_brackets = raw_target.startswith("<") and raw_target.endswith(">")
    target = raw_target[1:-1] if angle_brackets else raw_target
    suffix_at = len(target)
    for delimiter in ("#", "?"):
        index = target.find(delimiter)
        if index >= 0:
            suffix_at = min(suffix_at, index)
    return target[:suffix_at], target[suffix_at:], angle_brackets


def _is_local_relative(path_text: str) -> bool:
    if not path_text or path_text.startswith(("#", "/", "\\")):
        return False
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", path_text):
        return False
    return not Path(path_text).is_absolute()


def rebase_project_full_links(output_path: Path, text: str) -> str:
    """Rebase source-card-relative links for one generated full paste.

    Links already valid beside the generated output are left unchanged. A
    broken output-relative link is rebased only when it resolves beside the
    source card named in the generated-file header.
    """
    source_match = _SOURCE_ID_RE.match(text)
    if source_match is None:
        return text

    try:
        source = find_entry(load_registry(), source_match.group("id")).absolute_path
    except (FileNotFoundError, KeyError, TypeError, ValueError):
        return text

    def replace(match: re.Match[str]) -> str:
        raw_target = match.group("target")
        path_text, suffix, angle_brackets = _split_target(raw_target)
        if not _is_local_relative(path_text):
            return match.group(0)

        output_target = (output_path.parent / path_text).resolve()
        if output_target.exists():
            return match.group(0)

        source_target = (source.parent / path_text).resolve()
        try:
            source_target.relative_to(REPO_ROOT)
        except ValueError:
            return match.group(0)
        if not source_target.exists():
            return match.group(0)

        rebased = Path(os.path.relpath(source_target, output_path.parent)).as_posix()
        rendered_target = f"{rebased}{suffix}"
        if angle_brackets:
            rendered_target = f"<{rendered_target}>"
        return f"{match.group('prefix')}{rendered_target}{match.group('suffix')}"

    return _MARKDOWN_LINK_RE.sub(replace, text)


def find_project_full_link_drift() -> list[Path]:
    """Return generated prompt files whose relative links need rebasing."""
    drift: list[Path] = []
    for path in sorted(PROJECT_FULL_ROOT.glob("*.md")):
        current = path.read_text(encoding="utf-8")
        if rebase_project_full_links(path, current) != current:
            drift.append(path)
    return drift


def sync_project_full_links() -> list[Path]:
    """Rebase drifted project/full links and return changed paths."""
    changed: list[Path] = []
    for path in sorted(PROJECT_FULL_ROOT.glob("*.md")):
        current = path.read_text(encoding="utf-8")
        expected = rebase_project_full_links(path, current)
        if expected == current:
            continue
        path.write_text(expected, encoding="utf-8")
        changed.append(path)
    return changed
