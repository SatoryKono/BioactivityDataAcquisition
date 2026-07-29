"""Sync BioETL Cursor rules into Windsurf/Cascade workspace surfaces.

Canonical rule content: ``docs/00-project/ai/rules/cursor/*.mdc``
Tracked Windsurf mirror: ``docs/00-project/ai/rules/windsurf/rules/*.md``
Local deploy target: ``.windsurf/rules/*.md`` (gitignored)
Workflows source: ``docs/00-project/ai/rules/windsurf/workflows/*.md``
Workflows deploy: ``.windsurf/workflows/*.md``
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

WINDSURF_MAX_RULE_CHARS = 12_000

GOVERNANCE_TOKENS = (
    "AGENTS.md",
    "docs/00-project/RULES.md",
    "docs/01-requirements/REQUIREMENTS.md",
    "docs/02-architecture/decisions/",
)

# Per-file trigger overrides (Windsurf Wave 8 format).
TRIGGER_OVERRIDES: dict[str, str] = {
    "00-bioetl-core-governance.mdc": "always_on",
    "05-agent-workflow.mdc": "always_on",
    "04-patterns.mdc": "model_decision",
    "07-qodo-enforcement.mdc": "model_decision",
}


@dataclass(frozen=True)
class CursorRule:
    path: Path
    description: str
    globs: tuple[str, ...]
    always_apply: bool
    body: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}, text
    raw = match.group(1)
    body = text[match.end() :]
    meta: dict[str, object] = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key == "globs":
            items = re.findall(r'"([^"]+)"', value)
            meta[key] = items
        elif key == "alwaysApply":
            meta[key] = value.lower() == "true"
        else:
            meta[key] = value.strip('"')
    return meta, body


def _parse_globs(meta: dict[str, object]) -> tuple[str, ...]:
    raw = meta.get("globs")
    if isinstance(raw, list):
        return tuple(str(item) for item in raw)
    return ()


def _infer_trigger(meta: dict[str, object], filename: str) -> str:
    if filename in TRIGGER_OVERRIDES:
        return TRIGGER_OVERRIDES[filename]
    if meta.get("alwaysApply") is True:
        return "always_on"
    globs = _parse_globs(meta)
    if globs:
        return "glob"
    return "model_decision"


def _load_cursor_rule(path: Path) -> CursorRule:
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    description = str(meta.get("description", path.stem))
    return CursorRule(
        path=path,
        description=description,
        globs=_parse_globs(meta),
        always_apply=bool(meta.get("alwaysApply")),
        body=body.lstrip("\n"),
    )


def _render_windsurf_rule(rule: CursorRule) -> str:
    trigger = _infer_trigger(
        {
            "alwaysApply": rule.always_apply,
            "globs": list(rule.globs),
        },
        rule.path.name,
    )
    lines = [
        "---",
        f"trigger: {trigger}",
        f'description: "{rule.description}"',
    ]
    if trigger == "glob" and rule.globs:
        lines.append("globs:")
        lines.extend(f'  - "{glob_pattern}"' for glob_pattern in rule.globs)
    lines.extend(["---", "", rule.body.rstrip(), ""])
    return "\n".join(lines)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _validate_rule(path: Path, content: str) -> list[str]:
    issues: list[str] = []
    if len(content) > WINDSURF_MAX_RULE_CHARS:
        issues.append(
            f"{path.name}: {len(content)} chars exceeds Windsurf limit "
            f"{WINDSURF_MAX_RULE_CHARS}"
        )
    for token in GOVERNANCE_TOKENS:
        if token not in content:
            issues.append(f"{path.name}: missing governance token {token!r}")
    return issues


def _render_cursor_rules(
    cursor_files: list[Path], *, windsurf_rules_dir: Path
) -> tuple[dict[Path, str], list[str]]:
    rendered: dict[Path, str] = {}
    issues: list[str] = []
    for cursor_path in cursor_files:
        if cursor_path.name == "sonarqube_mcp_instructions.mdc":
            continue
        rule = _load_cursor_rule(cursor_path)
        content = _render_windsurf_rule(rule)
        target = windsurf_rules_dir / f"{cursor_path.stem}.md"
        rendered[target] = content
        issues.extend(_validate_rule(target, content))
    return rendered, issues


def _check_rendered_targets(
    rendered: dict[Path, str], *, root: Path
) -> list[str]:
    issues: list[str] = []
    for target, content in rendered.items():
        if not target.exists():
            issues.append(f"{target.relative_to(root)}: missing")
        elif target.read_text(encoding="utf-8") != content:
            issues.append(f"{target.relative_to(root)}: out of sync")
    return issues


def sync_rules(
    *,
    root: Path,
    deploy_local: bool,
    check_only: bool,
) -> list[str]:
    cursor_dir = root / "docs/00-project/ai/rules/cursor"
    windsurf_rules_dir = root / "docs/00-project/ai/rules/windsurf/rules"
    local_rules_dir = root / ".windsurf/rules"

    cursor_files = sorted(cursor_dir.glob("*.mdc"))
    if not cursor_files:
        return [f"No cursor rules found in {cursor_dir}"]

    rendered, issues = _render_cursor_rules(
        cursor_files, windsurf_rules_dir=windsurf_rules_dir
    )
    if check_only:
        issues.extend(_check_rendered_targets(rendered, root=root))
        return issues

    for target, content in rendered.items():
        _atomic_write(target, content)
        if deploy_local:
            _atomic_write(local_rules_dir / target.name, content)
    return issues


def _workflow_governance_issues(source: Path, content: str) -> list[str]:
    return [
        f"{source.name}: missing governance token {token!r}"
        for token in GOVERNANCE_TOKENS
        if token not in content
    ]


def _check_or_deploy_workflow(
    *,
    source: Path,
    content: str,
    target: Path,
    root: Path,
    deploy_local: bool,
    check_only: bool,
) -> list[str]:
    if check_only:
        if not target.exists():
            return [f"{target.relative_to(root)}: missing"]
        if target.read_text(encoding="utf-8") != content:
            return [f"{target.relative_to(root)}: out of sync"]
        return []
    if deploy_local:
        _atomic_write(target, content)
    return []


def sync_workflows(
    *,
    root: Path,
    deploy_local: bool,
    check_only: bool,
) -> list[str]:
    source_dir = root / "docs/00-project/ai/rules/windsurf/workflows"
    local_dir = root / ".windsurf/workflows"
    if not source_dir.exists():
        return [f"Missing workflows source: {source_dir}"]

    issues: list[str] = []
    for source in sorted(source_dir.glob("*.md")):
        content = source.read_text(encoding="utf-8")
        issues.extend(_workflow_governance_issues(source, content))
        issues.extend(
            _check_or_deploy_workflow(
                source=source,
                content=content,
                target=local_dir / source.name,
                root=root,
                deploy_local=deploy_local,
                check_only=check_only,
            )
        )
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=_repo_root(),
        help="Repository root (default: auto-detected)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify tracked mirror and local deploy are in sync",
    )
    parser.add_argument(
        "--no-deploy",
        action="store_true",
        help="Update tracked mirror only; skip .windsurf/ deploy",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable summary",
    )
    args = parser.parse_args(argv)

    deploy_local = not args.no_deploy and not args.check
    rule_issues = sync_rules(
        root=args.root,
        deploy_local=deploy_local,
        check_only=args.check,
    )
    workflow_issues = sync_workflows(
        root=args.root,
        deploy_local=deploy_local,
        check_only=args.check,
    )
    issues = rule_issues + workflow_issues

    if args.json:
        print(
            json.dumps(
                {
                    "ok": not issues,
                    "issues": issues,
                    "deploy_local": deploy_local,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    elif issues:
        for issue in issues:
            print(issue, file=sys.stderr)
    else:
        action = "checked" if args.check else "synced"
        print(f"Windsurf rules {action} successfully.")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
