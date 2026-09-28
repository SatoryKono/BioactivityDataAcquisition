#!/usr/bin/env python3
"""Canonical untrusted-input header check/generator for OpenCode agents (#11693).

OpenCode consumes `.opencode/agent/*.md` as-is: markdown includes are NOT
resolved, so a shared `_shared/*.md` file can never reach the agent unless
its text is embedded verbatim. The canonical core lives in
`.opencode/agent/_shared/untrusted-header.md`; every agent file must contain
it byte-for-byte, with per-agent tails (e.g. `agent-fix` notes in
`triage.md`/`bugfix.md`) kept AFTER the core.

Usage:
  python -m scripts.ai.opencode.check_agent_headers --check
  python -m scripts.ai.opencode.check_agent_headers --update
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT_DIR = REPO_ROOT / ".opencode" / "agent"
CANON_PATH = AGENT_DIR / "_shared" / "untrusted-header.md"
CANON_REL = CANON_PATH.relative_to(REPO_ROOT).as_posix()
_HEADING = "## Language and untrusted input"
_AGENT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.md$")


@dataclass(slots=True)
class HeaderIssue:
    level: str  # "error" | "warning"
    code: str
    message: str
    path: str = ""


@dataclass(slots=True)
class HeaderReport:
    errors: list[HeaderIssue] = field(default_factory=list)
    warnings: list[HeaderIssue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, code: str, message: str, path: str = "") -> None:
        self.errors.append(HeaderIssue("error", code, message, path))


def _confine_under(root: Path, candidate: Path) -> Path:
    """Resolve *candidate* and require it to stay under *root*."""
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"path escapes agent directory: {candidate}")
    return resolved


def load_core(canon_path: Path = CANON_PATH) -> str:
    """Read the canonical core block (exactly as embedded in agents)."""
    if canon_path == CANON_PATH:
        path = CANON_PATH.resolve()
    else:
        parent = canon_path.parent.resolve()
        path = _confine_under(parent, canon_path)
        _confine_under(parent.parent, path)
    return path.read_text(encoding="utf-8")


def agent_files(agent_dir: Path = AGENT_DIR) -> list[Path]:
    """Agent prompt files, excluding the `_shared/` canon directory."""
    root = agent_dir.resolve()
    if not root.is_dir():
        return []
    confined: list[Path] = []
    for path in root.glob("*.md"):
        if not path.is_file() or path.name == "README.md":
            continue
        if not _AGENT_NAME_RE.fullmatch(path.name):
            continue
        try:
            resolved = _confine_under(root, path)
        except ValueError:
            continue
        if resolved.parent != root:
            continue
        confined.append(resolved)
    return sorted(confined)


def check_text(agent_name: str, text: str, core: str) -> str | None:
    """Return an error message when the verbatim core is missing, else None."""
    if core not in text:
        return (
            f"{agent_name}: missing verbatim core from {CANON_REL} — run with --update"
        )
    return None


def _split_frontmatter(lines: list[str]) -> int:
    """Index of the first body line (after the closing `---`), or 0."""
    dashes = [i for i, line in enumerate(lines) if line.strip() == "---"]
    if len(dashes) >= 2:
        return dashes[1] + 1
    return 0


def normalize_text(text: str, core: str) -> str | None:
    """Return text with the verbatim core spliced in, or None if no safe fix.

    Rules: verbatim core already present -> unchanged; drifted block between
    the `## Language and untrusted input` heading and the core's last line ->
    replaced; heading missing entirely -> core inserted after frontmatter.
    """
    if core in text:
        return text
    core_lines = core.splitlines(keepends=True)
    lines = text.splitlines(keepends=True)
    heading = next(
        (i for i, line in enumerate(lines) if line.rstrip() == _HEADING),
        None,
    )
    if heading is None:
        body_at = _split_frontmatter(lines)
        rest = lines[body_at:]
        while rest and rest[0].strip() == "":
            rest = rest[1:]
        return "".join(lines[:body_at] + ["\n"] + core_lines + ["\n"] + rest)
    last_line = core_lines[-1].strip()
    end = next(
        (i for i in range(heading, len(lines)) if lines[i].strip() == last_line),
        None,
    )
    if end is None:
        return None
    return "".join(lines[:heading] + core_lines + lines[end + 1 :])


def check_headers(
    agent_dir: Path = AGENT_DIR,
    canon_path: Path = CANON_PATH,
) -> HeaderReport:
    """Fail when any agent file lacks the verbatim canonical core."""
    report = HeaderReport()
    try:
        core = load_core(canon_path)
    except (OSError, ValueError) as exc:
        report.add_error("canon_missing", str(exc), canon_path.as_posix())
        return report
    files = agent_files(agent_dir)
    if not files:
        report.add_error(
            "agents_missing", f"no agent files under {agent_dir.as_posix()}"
        )
        return report
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            report.add_error("agent_unreadable", str(exc), path.as_posix())
            continue
        message = check_text(path.name, text, core)
        if message is not None:
            try:
                rel = path.relative_to(REPO_ROOT).as_posix()
            except ValueError:
                rel = path.as_posix()
            report.add_error("header_core_missing", message, rel)
    report.stats = {
        "agents": len(files),
        "errors": len(report.errors),
        "warnings": len(report.warnings),
    }
    return report


def update_headers(
    agent_dir: Path = AGENT_DIR,
    canon_path: Path = CANON_PATH,
) -> tuple[HeaderReport, list[str]]:
    """Splice the verbatim core into drifted agents; return (report, updated)."""
    report = HeaderReport()
    try:
        core = load_core(canon_path)
    except (OSError, ValueError) as exc:
        report.add_error("canon_missing", str(exc), canon_path.as_posix())
        return report, []
    updated: list[str] = []
    files = agent_files(agent_dir)
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            report.add_error("agent_unreadable", str(exc), path.as_posix())
            continue
        fixed = normalize_text(text, core)
        if fixed is None:
            try:
                rel = path.relative_to(REPO_ROOT).as_posix()
            except ValueError:
                rel = path.as_posix()
            report.add_error(
                "header_unfixable",
                f"{path.name}: core block not found automatically — fix by hand",
                rel,
            )
            continue
        if fixed != text:
            try:
                target = _confine_under(agent_dir, path)
            except ValueError as exc:
                report.add_error("agent_path_escape", str(exc), path.as_posix())
                continue
            if not _AGENT_NAME_RE.fullmatch(target.name):
                report.add_error(
                    "agent_name_invalid",
                    f"refusing to write {target.name!r}",
                    target.as_posix(),
                )
                continue
            target.write_text(fixed, encoding="utf-8")
            updated.append(target.name)
    report.stats = {
        "agents": len(files),
        "updated": len(updated),
        "errors": len(report.errors),
        "warnings": len(report.warnings),
    }
    return report, updated


def format_report(report: HeaderReport, *, title: str) -> str:
    lines = [title, ""]
    if report.stats:
        lines.append(f"stats: {report.stats}")
        lines.append("")
    if not report.errors and not report.warnings:
        lines.append("OK — no issues")
        return "\n".join(lines) + "\n"
    for issue in report.errors:
        loc = f" [{issue.path}]" if issue.path else ""
        lines.append(f"ERROR {issue.code}{loc}: {issue.message}")
    for issue in report.warnings:
        loc = f" [{issue.path}]" if issue.path else ""
        lines.append(f"WARN  {issue.code}{loc}: {issue.message}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.ai.opencode.check_agent_headers",
        description="Check or sync the canonical OpenCode agent header (#11693).",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="Fail when any agent lacks the verbatim core",
    )
    mode.add_argument(
        "--update",
        action="store_true",
        help="Splice the verbatim core into drifted agents",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.update:
        report, updated = update_headers()
        for name in updated:
            print(f"updated {name}")
        sys.stdout.write(format_report(report, title="OpenCode agent headers"))
        return 0 if report.ok else 1
    report = check_headers()
    sys.stdout.write(format_report(report, title="OpenCode agent headers"))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
