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


def _atomic_copy(source: Path, target: Path, *, allowed_root: Path) -> None:
    from scripts.engineering.common.repo_paths import ensure_path_within_root

    safe_root = allowed_root.expanduser().resolve(strict=False)
    confined_source = ensure_path_within_root(source, safe_root)
    confined_target = ensure_path_within_root(target, safe_root)
    relative_source = confined_source.relative_to(safe_root)
    relative_target = confined_target.relative_to(safe_root)
    safe_source = ensure_path_within_root(
        safe_root.joinpath(*relative_source.parts), safe_root
    )
    safe_target = ensure_path_within_root(
        safe_root.joinpath(*relative_target.parts), safe_root
    )
    safe_target.parent.mkdir(parents=True, exist_ok=True)
    content = safe_source.read_text(  # NOSONAR - confined by ensure_path_within_root
        encoding="utf-8"
    )
    tmp = ensure_path_within_root(
        safe_target.parent / f"{safe_target.name}.tmp", safe_root
    )
    with tmp.open(  # NOSONAR - tmp confined by ensure_path_within_root
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write(content)
    os.replace(
        tmp, safe_target
    )  # NOSONAR - tmp/safe_target confined by ensure_path_within_root


def _list_mdc_files(directory: Path) -> list[Path]:
    """Return sorted non-excluded ``*.mdc`` files under directory."""
    return sorted(
        path for path in directory.glob("*.mdc") if path.name not in EXCLUDED_FILENAMES
    )


def _check_one_rule(
    *,
    safe_source: Path,
    target: Path,
    safe_root: Path,
) -> list[str]:
    """Compare one canonical rule against its deploy target (check mode)."""
    if not target.exists():
        return [f"{target.relative_to(safe_root)}: missing"]
    if (
        safe_source.read_bytes()  # NOSONAR - confined by ensure_path_within_root
        != target.read_bytes()  # NOSONAR - confined by ensure_path_within_root
    ):
        return [f"{target.relative_to(safe_root)}: out of sync with canonical"]
    return []


def _orphan_deploy_issues(
    *,
    deploy_dir: Path,
    canonical_files: list[Path],
    safe_root: Path,
) -> list[str]:
    """Report deploy-surface files not present in the canonical set."""
    from scripts.engineering.common.repo_paths import ensure_path_within_root

    issues: list[str] = []
    extra_deploy_files = _list_mdc_files(deploy_dir)
    canonical_names = {path.name for path in canonical_files}
    for target in extra_deploy_files:
        safe_target = ensure_path_within_root(target, safe_root)
        if safe_target.name not in canonical_names:
            issues.append(
                f"{safe_target.relative_to(safe_root)}: orphan deploy file "
                "(not in canonical cursor rules)"
            )
    return issues


def sync_cursor_rules(
    *,
    root: Path,
    deploy: bool,
    check_only: bool,
) -> list[str]:
    from scripts.engineering.common.repo_paths import ensure_path_within_root

    safe_root = root.expanduser().resolve(strict=False)
    canonical_dir = ensure_path_within_root(safe_root / CURSOR_RULE_DOCS_DIR, safe_root)
    deploy_dir = ensure_path_within_root(safe_root / CURSOR_RULES_DIR, safe_root)
    issues: list[str] = []

    if not canonical_dir.is_dir():
        issues.append(f"Missing canonical cursor rules dir: {canonical_dir}")
        return issues

    canonical_files = _list_mdc_files(canonical_dir)
    if not canonical_files:
        issues.append(f"No cursor rules found in {canonical_dir}")
        return issues

    verify_mode = check_only or not deploy
    for source in canonical_files:
        safe_source = ensure_path_within_root(source, safe_root)
        target = ensure_path_within_root(deploy_dir / safe_source.name, safe_root)
        if verify_mode:
            issues.extend(
                _check_one_rule(
                    safe_source=safe_source,
                    target=target,
                    safe_root=safe_root,
                )
            )
            continue
        _atomic_copy(safe_source, target, allowed_root=safe_root)

    if verify_mode:
        issues.extend(
            _orphan_deploy_issues(
                deploy_dir=deploy_dir,
                canonical_files=canonical_files,
                safe_root=safe_root,
            )
        )

    return issues


def _resolve_cli_root(raw_root: Path) -> Path:
    """Resolve CLI --root (relative confined under repo; absolute accepted)."""
    from scripts.engineering.common.repo_paths import resolve_cli_path

    root = Path(raw_root).expanduser()
    if not root.is_absolute():
        return resolve_cli_path(root, root=_repo_root())
    return root.resolve(strict=False)


def _emit_sync_result(
    *,
    issues: list[str],
    as_json: bool,
    check_mode: bool,
) -> None:
    """Print JSON or human-readable sync outcome."""
    if as_json:
        print(
            json.dumps(
                {
                    "ok": not issues,
                    "issues": issues,
                    "mode": "check" if check_mode else "deploy",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return
    action = "checked" if check_mode else "deployed"
    print(f"Cursor rules {action} successfully.")


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
        root=_resolve_cli_root(args.root),
        deploy=args.deploy,
        check_only=args.check,
    )
    _emit_sync_result(issues=issues, as_json=args.json, check_mode=args.check)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
