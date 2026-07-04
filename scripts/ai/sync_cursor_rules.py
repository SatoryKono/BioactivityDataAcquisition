"""Sync canonical Cursor rules into the IDE deploy surface.

Canonical rule content: ``docs/00-project/ai/rules/cursor/*.mdc``
Deploy target: ``.cursor/rules/*.mdc`` (machine-local deploy; sonarqube excluded)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

CURSOR_RULE_DOCS_DIR = Path("docs/00-project/ai/rules/cursor")
CURSOR_RULES_DIR = Path(".cursor/rules")
EXCLUDED_FILENAMES = frozenset({"sonarqube_mcp_instructions.mdc"})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    content = source.read_text(encoding="utf-8")
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, target)


def sync_cursor_rules(
    *,
    root: Path,
    deploy: bool,
    check_only: bool,
) -> list[str]:
    canonical_dir = root / CURSOR_RULE_DOCS_DIR
    deploy_dir = root / CURSOR_RULES_DIR
    issues: list[str] = []

    if not canonical_dir.is_dir():
        issues.append(f"Missing canonical cursor rules dir: {canonical_dir}")
        return issues

    canonical_files = sorted(
        path
        for path in canonical_dir.glob("*.mdc")
        if path.name not in EXCLUDED_FILENAMES
    )
    if not canonical_files:
        issues.append(f"No cursor rules found in {canonical_dir}")
        return issues

    for source in canonical_files:
        target = deploy_dir / source.name
        if check_only or not deploy:
            if not target.exists():
                issues.append(f"{target.relative_to(root)}: missing")
                continue
            if source.read_bytes() != target.read_bytes():
                issues.append(f"{target.relative_to(root)}: out of sync with canonical")
            continue
        _atomic_copy(source, target)

    if check_only or not deploy:
        extra_deploy_files = sorted(
            path
            for path in deploy_dir.glob("*.mdc")
            if path.name not in EXCLUDED_FILENAMES
        )
        canonical_names = {path.name for path in canonical_files}
        for target in extra_deploy_files:
            if target.name not in canonical_names:
                issues.append(
                    f"{target.relative_to(root)}: orphan deploy file "
                    "(not in canonical cursor rules)"
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
        help="Verify deploy surface matches canonical rules",
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Copy canonical rules into .cursor/rules/",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable summary",
    )
    args = parser.parse_args(argv)

    if args.check and args.deploy:
        print("Use either --check or --deploy, not both.", file=sys.stderr)
        return 2

    if not args.check and not args.deploy:
        args.deploy = True

    issues = sync_cursor_rules(
        root=args.root,
        deploy=args.deploy,
        check_only=args.check,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "ok": not issues,
                    "issues": issues,
                    "mode": "check" if args.check else "deploy",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    elif issues:
        for issue in issues:
            print(issue, file=sys.stderr)
    else:
        action = "checked" if args.check else "deployed"
        print(f"Cursor rules {action} successfully.")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
