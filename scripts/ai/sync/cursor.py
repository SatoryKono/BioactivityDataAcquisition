"""Sync canonical Cursor rules and project commands into the IDE deploy surface.

Canonical rule content: ``docs/00-project/ai/rules/cursor/*.mdc``
Deploy target: ``.cursor/rules/*.mdc`` (machine-local deploy; sonarqube excluded)

Canonical commands: ``docs/00-project/ai/rules/cursor/commands/*.md``
Deploy target: ``.cursor/commands/*.md`` (machine-local; gitignored)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

CURSOR_RULE_DOCS_DIR = Path("docs/00-project/ai/rules/cursor")
CURSOR_RULES_DIR = Path(".cursor/rules")
CURSOR_COMMAND_DOCS_DIR = Path("docs/00-project/ai/rules/cursor/commands")
CURSOR_COMMANDS_DIR = Path(".cursor/commands")
EXCLUDED_FILENAMES = frozenset({"sonarqube_mcp_instructions.mdc"})
MANAGED_COMMAND_MARKER = "<!-- bioetl:managed-cursor-command -->"
COMMAND_GOVERNANCE_TOKENS = (
    "AGENTS.md",
    "docs/00-project/RULES.md",
    "docs/01-requirements/REQUIREMENTS.md",
    "docs/02-architecture/decisions/",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


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


def _list_md_files(directory: Path) -> list[Path]:
    """Return sorted ``*.md`` files directly under directory."""
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.glob("*.md") if path.is_file())


def _is_managed_command(content: str) -> bool:
    return MANAGED_COMMAND_MARKER in content.splitlines()


def _prune_managed_commands(deploy_dir: Path, keep: set[str]) -> list[str]:
    """Remove marked copies whose canonical command is gone or invalid."""
    from scripts.engineering.common.repo_paths import ensure_path_within_root

    issues = []
    for target in _list_md_files(deploy_dir):
        try:
            if target.name in keep or target.is_symlink():
                continue
            safe_target = ensure_path_within_root(target, deploy_dir)
            content = safe_target.read_text(encoding="utf-8", errors="replace")
            if _is_managed_command(content):
                safe_target.unlink(missing_ok=True)
        except (OSError, ValueError) as exc:
            issues.append(f"{target.name}: unable to prune command: {exc}")
    return issues


def _deploy_one_command(
    source: Path, target: Path, *, deploy_dir: Path, safe_root: Path
) -> list[str]:
    """Keep unmarked local commands and links out of managed writes."""
    from scripts.engineering.common.repo_paths import ensure_path_within_root

    if target.is_symlink():
        return [f"{target.relative_to(safe_root)}: local command is a symlink"]
    target = ensure_path_within_root(target, deploy_dir)
    if target.exists() and not _is_managed_command(
        target.read_text(encoding="utf-8", errors="replace")
    ):
        return [f"{target.relative_to(safe_root)}: unmarked local command preserved"]
    _atomic_copy(source, target, allowed_root=safe_root)
    return []


def _command_governance_issues(source: Path, content: str) -> list[str]:
    """Report Cascade governance tokens missing from a command prompt."""
    return [
        f"{source.name}: missing governance token {token!r}"
        for token in COMMAND_GOVERNANCE_TOKENS
        if token not in content
    ]


def _orphan_command_issues(
    *,
    deploy_dir: Path,
    canonical_files: list[Path],
    safe_root: Path,
) -> list[str]:
    """Report deploy-surface command files absent from the canonical set."""
    from scripts.engineering.common.repo_paths import ensure_path_within_root

    issues: list[str] = []
    canonical_names = {path.name for path in canonical_files}
    for target in _list_md_files(deploy_dir):
        if target.name in canonical_names or target.is_symlink():
            continue
        safe_target = ensure_path_within_root(target, deploy_dir)
        if _is_managed_command(
            safe_target.read_text(encoding="utf-8", errors="replace")
        ):
            issues.append(
                f"{safe_target.relative_to(safe_root)}: orphan deploy file "
                "(not in canonical cursor commands)"
            )
    return issues


def sync_cursor_commands(
    *,
    root: Path,
    deploy: bool,
    check_only: bool,
) -> list[str]:
    """Copy or verify project slash commands.

    Files that omit governance tokens are not deployed.
    """
    from scripts.engineering.common.repo_paths import ensure_path_within_root

    safe_root = root.expanduser().resolve(strict=False)
    canonical_dir = ensure_path_within_root(
        safe_root / CURSOR_COMMAND_DOCS_DIR, safe_root
    )
    command_path = safe_root / CURSOR_COMMANDS_DIR
    deploy_dir = ensure_path_within_root(command_path, safe_root)
    if deploy_dir != command_path:
        return [f"Linked cursor commands directory is not supported: {command_path}"]
    if not canonical_dir.is_dir():
        return [f"Missing canonical cursor commands dir: {canonical_dir}"]

    canonical_files = _list_md_files(canonical_dir)
    verify_mode = check_only or not deploy
    if not canonical_files:
        issues = [f"No cursor commands found in {canonical_dir}"]
        if not verify_mode:
            issues.extend(_prune_managed_commands(deploy_dir, set()))
        return issues

    issues: list[str] = []
    valid_names: set[str] = set()
    for source in canonical_files:
        safe_source = ensure_path_within_root(source, safe_root)
        content = (
            safe_source.read_text(  # NOSONAR - confined by ensure_path_within_root
                encoding="utf-8"
            )
        )
        token_issues = _command_governance_issues(safe_source, content)
        if not _is_managed_command(content):
            token_issues.append(f"{safe_source.name}: missing managed command marker")
        issues.extend(token_issues)
        if token_issues:
            continue
        valid_names.add(safe_source.name)
        target = deploy_dir / safe_source.name
        if verify_mode:
            target = ensure_path_within_root(target, deploy_dir)
            issues.extend(
                _check_one_rule(
                    safe_source=safe_source,
                    target=target,
                    safe_root=safe_root,
                )
            )
            continue
        issues.extend(
            _deploy_one_command(
                safe_source, target, deploy_dir=deploy_dir, safe_root=safe_root
            )
        )

    if verify_mode:
        issues.extend(
            _orphan_command_issues(
                deploy_dir=deploy_dir,
                canonical_files=canonical_files,
                safe_root=safe_root,
            )
        )
    else:
        issues.extend(_prune_managed_commands(deploy_dir, valid_names))
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
    print(f"Cursor rules and commands {action} successfully.")


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
        help="Verify deploy surface matches canonical rules and commands",
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Copy canonical rules into .cursor/rules/ and commands into .cursor/commands/",
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
        args.check = True

    root = _resolve_cli_root(args.root)
    issues = sync_cursor_rules(
        root=root,
        deploy=args.deploy,
        check_only=args.check,
    )
    issues.extend(
        sync_cursor_commands(
            root=root,
            deploy=args.deploy,
            check_only=args.check,
        )
    )
    _emit_sync_result(issues=issues, as_json=args.json, check_mode=args.check)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
