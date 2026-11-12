"""Explicit local post-change checks, not native lifecycle or CI admission.

Existing pre-commit/pytest/CI owners retain their full validation duties.
Only state-bound, timeless static observations may be reused for 60 seconds.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import sys
import subprocess
from collections.abc import Callable
import time
from typing import Any

from scripts.engineering.repo import hook_receipts as receipts
from scripts.engineering.repo import hook_runtime
from scripts.engineering.repo.check_no_partial_tree import (
    resolve_revision,
    validate_repo,
)
from scripts.engineering.repo.process_deadline import run_owned


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
                "grafana/",
                "docs/03-guides/dashboards/",
                "scripts/ops/observability/grafana/",
                "tests/integration/_dashboard",
                "tests/integration/_grafana_test_support",
                "tests/helpers",
                "tests/integration/test_dashboard",
            )
        )
        or path
        in {
            "docs/01-requirements/DASHBOARD_REQUIREMENTS.md",
            "docker-compose.yml",
            "docker-compose.monitoring.yml",
            "pyproject.toml",
            "uv.lock",
            "pytest.ini",
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
        ("src/", "tests/", "docs/", "grafana/", "scripts/", ".github/")
    ) or path in {".pre-commit-config.yaml", "pyproject.toml", "uv.lock", "pytest.ini"}


def _check_rules() -> list[tuple[Callable[[str], bool], Check]]:
    return [
        (
            _runtime_input,
            Check(
                "runtime-parity",
                _python("scripts/ai/junie/check_junie_mirror.py", "--check"),
                cacheable=True,
            ),
        ),
        (
            _runtime_input,
            Check(
                "runtime-source-contract",
                _python("scripts/ai/codex/doctor.py", "static", "--no-write"),
                cacheable=True,
            ),
        ),
        (
            _docs_input,
            Check(
                "docs-cleanup-inventory",
                _python("-m", "scripts.docs", "generate-cleanup-inventory", "--check"),
                cacheable=True,
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
                cacheable=True,
            ),
        ),
        (
            lambda path: path == ".pre-commit-config.yaml",
            Check(
                "precommit-config",
                _python("-m", "pre_commit", "validate-config"),
                cacheable=True,
            ),
        ),
        (
            lambda path: path.startswith(".github/"),
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
                _python("-m", "ruff", "check", "--", *python_files),
                cacheable=True,
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
        ".github/",
        ".codex/",
        ".junie/",
        ".devin/",
        ".opencode/",
        "grafana/",
        "reports/",
        "data/",
    )
    root_files = {
        "README.md",
        "CONTRIBUTING.md",
        "AGENTS.md",
        "mkdocs.yml",
        "pyproject.toml",
        "uv.lock",
        "pytest.ini",
        "Makefile",
        ".pre-commit-config.yaml",
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
    cached: bool,
    started: float,
    timeout: float,
) -> list[dict[str, Any]]:
    rows = []
    for check in checks:
        if cached and check.cacheable:
            row = _row(check, "PASS", 0, 0, reused=True)
        else:
            row = _execute(
                check, root, directory, timeout - (time.monotonic() - started)
            )
        rows.append(row)
        if row["status"] != "PASS":
            break
    return rows


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
    plan = build_plan(root, base)
    if plan["unknown"]:
        return {
            "status": "ERROR",
            "reason": "unknown_surface_requires_owner",
            "runtime_admission": False,
        }
    state = receipts.snapshot(root, base=plan["base_sha"])
    checks = plan["checks"]
    static = [c for c in checks if c.cacheable]
    cached = False
    if reuse is not None:
        verdict = receipts.validate_receipt(
            root, reuse, state, [c.id for c in static], for_reuse=True
        )
        cached = verdict["status"] == "PASS"
        if not cached and verdict["reason"] == "receipt_unavailable_or_invalid":
            return {
                "status": "ERROR",
                "reason": "invalid_cache_receipt",
                "runtime_admission": False,
            }
    directory = receipts.receipt_directory(root)
    directory.mkdir(exist_ok=True)
    core = [
        Check(name, tuple(argv))
        for name, argv in hook_runtime._guard_commands(root, "pre-commit", b"")
    ]
    rows = _execute_plan(root, directory, [*core, *checks], cached, started, timeout)
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
    cache_path = None
    if passed and static:
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
        "cache": "HIT" if cached else "MISS",
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
            plan = build_plan(root, args.base)
            result = {
                "status": "ERROR" if plan["unknown"] else "PLANNED",
                "check_ids": ["tree", "budgets", *[c.id for c in plan["checks"]]],
                "base_sha": plan["base_sha"],
                "runtime_admission": False,
                "execution_status": "NOT_RUN",
            }
        elif args.action == "receipt":
            if args.receipt is None:
                raise ValueError("receipt required")
            plan = build_plan(root, args.base)
            if plan["unknown"]:
                raise ValueError("unknown surface requires owner")
            result = receipts.validate_receipt(
                root,
                args.receipt,
                receipts.snapshot(root, base=plan["base_sha"]),
                ["tree", "budgets", *[c.id for c in plan["checks"]]],
            )
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
