"""Lock AUD-009: B-scope coverage exclusions stay annotated and bounded."""

from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "bioetl"
ISSUE_MARKER = "(#10534"

# (path, allowed pragma count): lazy-export hooks are covered by behavioral
# tests, so only declaration-only stubs and defensive guards may remain.
ALLOWED_PRAGMAS = {
    "src/bioetl/application/composite/runner_pkg/runner_merge_stage_dispatch_mixin.py": 3,
    "src/bioetl/application/composite/runner_pkg/runner_stage_support_dispatch_mixin.py": 4,
    "src/bioetl/application/core/record_processor_config.py": 1,
}
COVERED_NO_PRAGMA = (
    "src/bioetl/application/core/wiring/lazy_export_hooks.py",
    "src/bioetl/composition/lazy_exports.py",
    "src/bioetl/composition/runtime_builders/_run_manifest_refs.py",
    "src/bioetl/composition/runtime_builders/inputs_resolver.py",
)
B_SCOPES = ("application", "interfaces", "composition")


def _pragma_lines(path: Path) -> list[str]:
    return [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if "pragma: no cover" in line
    ]


@pytest.mark.architecture
def test_b_scope_pragma_budget_is_not_exceeded() -> None:
    total = 0
    for scope in B_SCOPES:
        for path in sorted((SRC / scope).rglob("*.py")):
            total += len(_pragma_lines(path))
    allowed = sum(ALLOWED_PRAGMAS.values())
    assert total <= allowed, (
        f"B-scope exclusions grew: {total} > {allowed} "
        "(AUD-009 forbids new pragma exclusions)"
    )


@pytest.mark.architecture
def test_b_scope_pragmas_match_allowlist_and_carry_issue_link() -> None:
    offenders: list[str] = []
    for scope in B_SCOPES:
        for path in sorted((SRC / scope).rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            pragma_lines = _pragma_lines(path)
            if not pragma_lines:
                continue
            if rel not in ALLOWED_PRAGMAS:
                offenders.append(f"{rel}: unexpected exclusion file")
                continue
            if len(pragma_lines) != ALLOWED_PRAGMAS[rel]:
                offenders.append(
                    f"{rel}: {len(pragma_lines)} exclusions, "
                    f"expected {ALLOWED_PRAGMAS[rel]}"
                )
            for line in pragma_lines:
                if ISSUE_MARKER not in line or "review" not in line:
                    offenders.append(f"{rel}: missing issue link: {line.strip()}")
    assert offenders == []


@pytest.mark.architecture
def test_covered_lazy_hooks_carry_no_pragma() -> None:
    offenders = [
        rel
        for rel in COVERED_NO_PRAGMA
        if _pragma_lines(ROOT / rel)
    ]
    assert offenders == []
