"""Explicit local post-change checks, not native lifecycle or CI admission.

Existing pre-commit/pytest/CI owners retain their full validation duties.
Only state-bound, timeless static observations may be reused for 60 seconds.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import partial
import json
import math
import os
from pathlib import Path
import sys
import subprocess
from collections.abc import Callable
import time
import tomllib
from typing import Any

from scripts.engineering.repo import hook_receipts as receipts
from scripts.engineering.repo import hook_runtime
from scripts.engineering.repo.check_no_partial_tree import (
    resolve_revision,
    validate_repo,
)
from scripts.engineering.repo.process_deadline import run_owned


PRE_COMMIT_CONFIG = ".pre-commit-config.yaml"
PYPROJECT = "pyproject.toml"
PYTEST_CONFIG = "pytest.ini"
DEPENDENCY_LOCK = "uv.lock"
WORKFLOW_PREFIX = ".github/"
DASHBOARD_PREFIX = "grafana/"


@dataclass(frozen=True)
class Check:
    id: str
    argv: tuple[str, ...]
    timeout: int = 30
    cacheable: bool = False


def _python(*args: str) -> tuple[str, ...]:
    return (sys.executable, "-B", *args)


def changed_paths(root: Path, base: str) -> list[str]:
    """Union committed, both staged indexes, unstaged and nonignored new paths."""
    from scripts.engineering.repo.check_no_partial_tree import _index_views

    names: set[str] = set()
    for view in _index_views(root):
        for args in [
            (
                "diff",
                base,
                "HEAD",
                "--no-ext-diff",
                "--no-textconv",
                "--no-renames",
                "--name-only",
                "-z",
            ),
            (
                "diff",
                "--cached",
                "HEAD",
                "--no-ext-diff",
                "--no-textconv",
                "--no-renames",
                "--name-only",
                "-z",
            ),
            (
                "diff-files",
                "--no-ext-diff",
                "--no-textconv",
                "--no-renames",
                "--name-only",
                "-z",
            ),
            ("ls-files", "--others", "--exclude-standard", "-z"),
        ]:
            names.update(
                p.decode("utf-8")
                for p in receipts._git(root, *args, index_file=view).split(b"\0")
                if p
            )
    return sorted(names)


def dashboard_input(path: str) -> bool:
    return (
        path.startswith(
            (
                DASHBOARD_PREFIX,
                "docs/03-guides/dashboards/",
                "scripts/ops/observability/grafana/",
                "tests/integration/_dashboard",
                "tests/integration/_grafana_test_support",
                "tests/integration/test_grafana_",
                "tests/unit/scripts/ops/observability/test_grafana_",
                "tests/helpers",
                "tests/integration/test_dashboard",
            )
        )
        or path
        in {
            "docs/01-requirements/DASHBOARD_REQUIREMENTS.md",
            "docker-compose.yml",
            "docker-compose.monitoring.yml",
            PYPROJECT,
            DEPENDENCY_LOCK,
            PYTEST_CONFIG,
        }
        or path.startswith(
            (
                "configs/quality/dashboard",
                "scripts/engineering/qa/report_dashboard",
                "scripts/engineering/qa/check_dashboard",
            )
        )
    )


def _runtime_input(path: str) -> bool:
    return path.startswith(
        (".codex/", ".junie/", ".devin/", "scripts/ai/junie/", "scripts/ai/codex/")
    ) or path in {
        "AGENTS.md",
        "scripts/ai/junie/junie-mirror-contract.json",
    }


def _docs_input(path: str) -> bool:
    return (
        path.endswith(".md")
        or path.startswith("scripts/docs/")
        or path
        in {"mkdocs.yml", "docs/reports/generated/documentation-cleanup-inventory.json"}
    )


def _module_input(path: str) -> bool:
    return (path.startswith("src/bioetl/") and path.endswith(".py")) or path in {
        "reports/quality/module-coverage-inventory.json",
        "scripts/engineering/qa/report_module_coverage_inventory.py",
    }


def _first_window_input(path: str) -> bool:
    # DASH-FIT-004 explicitly owns a global code/docs gate; do not narrow it.
    return path.startswith(
        ("src/", "tests/", "docs/", DASHBOARD_PREFIX, "scripts/", WORKFLOW_PREFIX)
    ) or path in {PRE_COMMIT_CONFIG, PYPROJECT, DEPENDENCY_LOCK, PYTEST_CONFIG}


def _check_rules() -> list[tuple[Callable[[str], bool], Check]]:
    return [
        (
            _runtime_input,
            Check(
                "runtime-parity",
                _python("scripts/ai/junie/check_junie_mirror.py", "--check"),
            ),
        ),
        (
            _runtime_input,
            Check(
                "runtime-source-contract",
                _python("scripts/ai/codex/doctor.py", "static", "--no-write"),
            ),
        ),
        (
            _docs_input,
            Check(
                "docs-cleanup-inventory",
                _python("-m", "scripts.docs", "generate-cleanup-inventory", "--check"),
            ),
        ),
        (
            _module_input,
            Check(
                "module-coverage-source",
                _python(
                    "-m",
                    "scripts.engineering.qa",
                    "report-module-coverage",
                    "--check",
                    "--allow-missing-coverage-xml",
                ),
            ),
        ),
        (
            lambda path: path == PRE_COMMIT_CONFIG,
            Check(
                "precommit-config",
                _python("-m", "pre_commit", "validate-config"),
                cacheable=True,
            ),
        ),
        (
            lambda path: path.startswith(WORKFLOW_PREFIX),
            Check(
                "actions-runtime-policy",
                _python(
                    "-m", "scripts.engineering.repo", "check-actions-runtime-policy"
                ),
            ),
        ),
        (
            _first_window_input,
            Check(
                "dashboard-first-window",
                _python(
                    "-m",
                    "pytest",
                    "tests/integration/test_dashboard_first_window_noscroll.py",
                    "-q",
                    "--no-cov",
                ),
                timeout=90,
            ),
        ),
        (
            dashboard_input,
            Check(
                "dashboard-static-gates",
                _python(
                    "-m",
                    "pytest",
                    "tests/integration/test_dashboard_qa_check_gates.py",
                    "-q",
                    "--no-cov",
                ),
                timeout=90,
            ),
        ),
    ]


def _lint_cacheable(root: Path) -> bool:
    config = root / PYPROJECT
    if not config.is_file():
        return False
    payload = tomllib.loads(config.read_text(encoding="utf-8"))
    tool = payload.get("tool", {})
    ruff = tool.get("ruff", {}) if isinstance(tool, dict) else None
    # External extends need their own input closure; run fresh instead.
    return isinstance(ruff, dict) and "extend" not in ruff


def select_checks(root: Path, paths: list[str]) -> list[Check]:
    """Select additive post-change gates; existing mandatory CI duties remain."""
    result = [
        check for predicate, check in _check_rules() if any(predicate(p) for p in paths)
    ]
    python_files = [
        str(root / p) for p in paths if p.endswith(".py") and (root / p).is_file()
    ]
    if python_files:
        result.append(
            Check(
                "python-lint",
                _python(
                    "-m",
                    "ruff",
                    "check",
                    "--config",
                    str(root / PYPROJECT),
                    "--",
                    *python_files,
                ),
                cacheable=_lint_cacheable(root),
            )
        )
    return result


def build_plan(root: Path, base: str) -> dict[str, Any]:
    base_sha = resolve_revision(root, base)
    paths = changed_paths(root, base_sha)
    for relative in paths:
        if not (root / relative).resolve().is_relative_to(root):
            raise ValueError("changed path escaped repository")
    # Unknown surfaces need an explicit broader owner; no inferred complete PASS.
    known = (
        "docs/",
        "src/",
        "tests/",
        "scripts/",
        "configs/",
        WORKFLOW_PREFIX,
        ".codex/",
        ".junie/",
        ".devin/",
        ".opencode/",
        DASHBOARD_PREFIX,
        "reports/",
        "data/",
    )
    root_files = {
        "README.md",
        "CONTRIBUTING.md",
        "AGENTS.md",
        "mkdocs.yml",
        PYPROJECT,
        DEPENDENCY_LOCK,
        PYTEST_CONFIG,
        "Makefile",
        PRE_COMMIT_CONFIG,
        ".gitignore",
        ".gitattributes",
        "opencode.json",
        "docker-compose.yml",
        "docker-compose.monitoring.yml",
    }
    unknown = [p for p in paths if not p.startswith(known) and p not in root_files]
    return {
        "base_sha": base_sha,
        "paths": paths,
        "checks": select_checks(root, paths),
        "unknown": unknown,
    }


def stable_plan(root: Path, base: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if base != hook_runtime.TRUSTED_BASE:
        raise ValueError("post-change checks require the trusted base")
    before = receipts.snapshot(root, base=base)
    plan = build_plan(root, base)
    after = receipts.snapshot(root, base=base)
    if before != after or plan["base_sha"] != before["base_sha"]:
        raise ValueError("state changed during planning")
    return plan, after


def _core_checks(root: Path, base: str) -> list[Check]:
    core = [
        Check(
            name,
            tuple(base if arg == hook_runtime.TRUSTED_BASE else arg for arg in argv),
        )
        for name, argv in hook_runtime._guard_commands(root, "pre-commit", b"")
    ]
    core.append(
        Check(
            "budgets-worktree",
            _python(
                str(Path(__file__).with_name("budget_guard.py")),
                "--repo-root",
                str(root),
                "--base",
                base,
                "--worktree",
            ),
        )
    )
    return core


def _expected_ids(plan: dict[str, Any]) -> list[str]:
    return [
        "tree",
        "budgets",
        "budgets-worktree",
        *[check.id for check in plan["checks"]],
    ]


def _row(
    check: Check, status: str, code: int | None, duration: int, *, reused: bool = False
) -> dict[str, Any]:
    return {
        "id": check.id,
        "status": status,
        "returncode": code,
        "duration_ms": duration,
        "cacheable": check.cacheable,
        "argv_sha256": receipts.digest(list(check.argv)),
        "reused": reused,
    }


def _execute(
    check: Check, root: Path, directory: Path, remaining: float
) -> dict[str, Any]:
    if remaining <= 0:
        return _row(check, "ERROR", None, 0)
    env = dict(
        os.environ,
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=os.pathsep.join((str(root), str(root / "src"))),
    )
    result = run_owned(
        check.argv,
        cwd=root,
        state_dir=directory,
        timeout=min(check.timeout, remaining),
        env=env,
    )
    return _row(
        check, result.status, result.returncode, int(result.duration_seconds * 1000)
    )


def _execute_plan(
    root: Path,
    directory: Path,
    checks: list[Check],
    can_reuse: Callable[[], bool],
    started: float,
    timeout: float,
) -> list[dict[str, Any]]:
    rows = []
    for check in checks:
        if check.cacheable and can_reuse():
            row = _row(check, "PASS", 0, 0, reused=True)
        else:
            row = _execute(
                check, root, directory, timeout - (time.monotonic() - started)
            )
        rows.append(row)
        if row["status"] != "PASS":
            break
    return rows


def _cache_state(
    root: Path,
    reuse: Path | None,
    state: dict[str, Any],
    static: list[Check],
) -> tuple[bool, bool]:
    if reuse is None:
        return False, False
    verdict = receipts.validate_receipt(
        root,
        reuse,
        state,
        [check.id for check in static],
        for_reuse=True,
    )
    cached = verdict["status"] == "PASS"
    return cached, not cached and verdict.get(
        "reason"
    ) == "receipt_unavailable_or_invalid"


def _can_reuse(
    enabled: bool,
    root: Path,
    reuse: Path | None,
    state: dict[str, Any],
    static: list[Check],
) -> bool:
    if not enabled:
        return False
    cached, invalid = _cache_state(root, reuse, state, static)
    if invalid:
        raise ValueError("cache receipt changed during checks")
    return cached


def validate(
    root: Path,
    *,
    base: str = "origin/main",
    reuse: Path | None = None,
    timeout: float = 120,
) -> dict[str, Any]:
    if (
        isinstance(timeout, bool)
        or not math.isfinite(timeout)
        or not 0 < timeout <= 180
    ):
        raise ValueError("invalid local check deadline")
    started = time.monotonic()
    plan, state = stable_plan(root, base)
    if plan["unknown"]:
        return {
            "status": "ERROR",
            "reason": "unknown_surface_requires_owner",
            "runtime_admission": False,
        }
    checks = plan["checks"]
    static = [c for c in checks if c.cacheable]
    cached, invalid_cache = _cache_state(root, reuse, state, static)
    if invalid_cache:
        return {
            "status": "ERROR",
            "reason": "invalid_cache_receipt",
            "runtime_admission": False,
        }
    directory = receipts.receipt_directory(root)
    directory.mkdir(exist_ok=True)
    core = _core_checks(root, plan["base_sha"])
    can_reuse = partial(_can_reuse, cached, root, reuse, state, static)
    rows = _execute_plan(root, directory, [*core, *checks], can_reuse, started, timeout)
    after = receipts.snapshot(root, base=plan["base_sha"])
    if after != state or resolve_revision(root, base) != plan["base_sha"]:
        return {
            "status": "ERROR",
            "reason": "state_changed_during_checks",
            "runtime_admission": False,
        }
    target = receipts.write_receipt(root, state, rows)
    passed = len(rows) == len(core) + len(checks) and all(
        row["status"] == "PASS" for row in rows
    )
    # A cache hit preserves the original observation time, never a sliding TTL.
    cache_hit = any(row["reused"] for row in rows)
    cache_path = reuse if passed and cache_hit else None
    if passed and static and not cache_hit:
        cache_path = receipts.write_receipt(
            root, state, [row for row in rows if row["cacheable"]]
        )
    return {
        "status": "PASS" if passed else "ERROR",
        "receipt": str(target),
        "cache_receipt": str(cache_path) if cache_path else None,
        "checks": rows,
        "runtime_admission": False,
        "ci_acceptance": False,
        "scope": "local_post_change_only",
        "cache": "HIT" if cache_hit else "MISS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "validate", "receipt"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--reuse", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        root = validate_repo(args.repo)
        if args.action == "plan":
            plan, state = stable_plan(root, args.base)
            result = {
                "status": "ERROR" if plan["unknown"] else "PLANNED",
                "check_ids": _expected_ids(plan),
                "base_sha": plan["base_sha"],
                "runtime_admission": False,
                "execution_status": "NOT_RUN",
            }
        elif args.action == "receipt":
            if args.receipt is None:
                raise ValueError("receipt required")
            plan, state = stable_plan(root, args.base)
            if plan["unknown"]:
                raise ValueError("unknown surface requires owner")
            result = receipts.validate_receipt(
                root,
                args.receipt,
                state,
                _expected_ids(plan),
            )
            if state != receipts.snapshot(root, base=args.base):
                raise ValueError("state changed during receipt validation")
        else:
            result = validate(root, base=args.base, reuse=args.reuse)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RecursionError,
        subprocess.SubprocessError,
    ):
        result = {
            "status": "ERROR",
            "reason": "check_dependency_or_state_unavailable",
            "runtime_admission": False,
        }
    result.update(
        runtime_admission=False, ci_acceptance=False, scope="local_post_change_only"
    )
    print(json.dumps(result))
    return 0 if result["status"] in {"PASS", "PLANNED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
