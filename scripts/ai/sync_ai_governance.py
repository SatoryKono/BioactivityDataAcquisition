"""Normalize and sync BioETL AI governance surfaces.

Operations:
- normalize tracked Codex agent runtime files (``.codex/agents/*.md``)
- inject canonical-source blocks into docs agent mirrors
- add normative index links to Codex/docs skill mirrors
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

CANONICAL_SOURCES_BLOCK = """## Canonical Sources

Read before planning or editing:

- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `AGENTS.md`
"""

NORMATIVE_SKILL_LINE_CODEX = (
    "- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`\n"
)
NORMATIVE_SKILL_LINE_DOCS = "- Normative index: `../../../../NORMATIVE_SOURCES.md`\n"

MIRROR_HEADER_PATTERN = re.compile(
    r"^> Mirror status:.*?^_{10,}\s*\n",
    re.MULTILINE | re.DOTALL,
)
CANONICAL_SOURCES_PATTERN = re.compile(
    r"^## Canonical Sources\s*\n(?:.*?\n)*?(?=^(?:## |name:|# |\Z))",
    re.MULTILINE,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _strip_mirror_header(text: str) -> str:
    return MIRROR_HEADER_PATTERN.sub("", text, count=1)


def _ensure_canonical_sources(text: str) -> str:
    cleaned = _strip_mirror_header(text)
    if CANONICAL_SOURCES_PATTERN.search(cleaned):
        return CANONICAL_SOURCES_PATTERN.sub(
            CANONICAL_SOURCES_BLOCK.rstrip() + "\n\n",
            cleaned,
            count=1,
        )
    return CANONICAL_SOURCES_BLOCK + "\n" + cleaned.lstrip("\n")


def _insert_after_source_header(body: str, line: str) -> str:
    marker = "## Source Of Truth\n"
    if "NORMATIVE_SOURCES" in body:
        return body
    idx = body.find(marker)
    if idx == -1:
        return body
    insert_at = idx + len(marker)
    if insert_at < len(body) and body[insert_at] == "\n":
        insert_at += 1
    return body[:insert_at] + line + body[insert_at:]


def normalize_codex_agents(root: Path, *, check_only: bool) -> list[str]:
    agents_dir = root / ".codex" / "agents"
    issues: list[str] = []
    if not agents_dir.is_dir():
        issues.append(f"Missing {agents_dir}")
        return issues

    for path in sorted(agents_dir.glob("*.md")):
        original = path.read_text(encoding="utf-8")
        updated = _ensure_canonical_sources(original)
        if updated != original:
            rel = path.relative_to(root)
            if check_only:
                issues.append(f"{rel}: would normalize canonical sources")
            else:
                _atomic_write(path, updated)
    return issues


def inject_docs_agent_sources(root: Path, *, check_only: bool) -> list[str]:
    agents_dir = root / "docs/00-project/ai/agents/agents"
    issues: list[str] = []
    for path in sorted(agents_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        original = path.read_text(encoding="utf-8")
        if CANONICAL_SOURCES_PATTERN.search(original):
            continue
        match = re.search(r"^_{10,}\s*$", original, re.MULTILINE)
        if not match:
            issues.append(f"{path.relative_to(root)}: missing mirror separator")
            continue
        insert_at = match.end()
        while insert_at < len(original) and original[insert_at] in "\r\n":
            insert_at += 1
        updated = (
            original[:insert_at]
            + "\n"
            + CANONICAL_SOURCES_BLOCK
            + "\n"
            + original[insert_at:].lstrip("\n")
        )
        if check_only:
            issues.append(f"{path.relative_to(root)}: would inject canonical sources")
        else:
            _atomic_write(path, updated)
    return issues


def normalize_codex_skills(root: Path, *, check_only: bool) -> list[str]:
    skills_root = root / ".codex" / "skills"
    issues: list[str] = []
    for path in sorted(skills_root.glob("*/SKILL.md")):
        original = path.read_text(encoding="utf-8")
        updated = _insert_after_source_header(original, NORMATIVE_SKILL_LINE_CODEX)
        if updated != original:
            rel = path.relative_to(root)
            if check_only:
                issues.append(f"{rel}: would add normative index link")
            else:
                _atomic_write(path, updated)
    return issues


GOVERNANCE_SKILL_LINES_DOCS = (
    "- Normative index: `../../../../NORMATIVE_SOURCES.md`",
    "- Root runtime contract: `../../../../../AGENTS.md`",
    "- Project rules: `../../../../RULES.md`",
    "- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`",
    "- Accepted ADRs in `../../../../../02-architecture/decisions/`",
    "- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`",
    "- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`",
)


def _ensure_docs_skill_governance(body: str) -> str:
    if "## Source Of Truth" not in body:
        workflow_idx = body.find("## Workflow")
        block = "## Source Of Truth\n\n" + "\n".join(GOVERNANCE_SKILL_LINES_DOCS) + "\n\n"
        if workflow_idx != -1:
            return body[:workflow_idx] + block + body[workflow_idx:]
        return body.rstrip() + "\n\n" + block

    updated = body
    marker = "## Source Of Truth\n"
    insert_at = updated.find(marker) + len(marker)
    if insert_at < len(updated) and updated[insert_at] == "\n":
        insert_at += 1
    for line in GOVERNANCE_SKILL_LINES_DOCS:
        token = line.split("`", 2)[1]
        if token not in updated:
            updated = updated[:insert_at] + line + "\n" + updated[insert_at:]
            insert_at += len(line) + 1
    return updated


def sync_docs_skill_mirrors(root: Path, *, check_only: bool) -> list[str]:
    docs_root = root / "docs/00-project/ai/skills/local"
    issues: list[str] = []
    for path in sorted(docs_root.glob("*/SKILL.md")):
        original = path.read_text(encoding="utf-8")
        updated = _ensure_docs_skill_governance(original)
        if updated != original:
            rel = path.relative_to(root)
            if check_only:
                issues.append(f"{rel}: would sync governance source-of-truth links")
            else:
                _atomic_write(path, updated)
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_repo_root())
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--only",
        choices=("codex-agents", "docs-agents", "codex-skills", "docs-skills", "all"),
        default="all",
    )
    args = parser.parse_args(argv)

    runners = {
        "codex-agents": normalize_codex_agents,
        "docs-agents": inject_docs_agent_sources,
        "codex-skills": normalize_codex_skills,
        "docs-skills": sync_docs_skill_mirrors,
    }
    selected = list(runners) if args.only == "all" else [args.only]

    issues: list[str] = []
    for key in selected:
        issues.extend(runners[key](args.root, check_only=args.check))

    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1

    action = "checked" if args.check else "synced"
    print(f"AI governance surfaces {action} successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
