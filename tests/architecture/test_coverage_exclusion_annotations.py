"""Lock AUD-009: B-scope coverage exclusions stay annotated and bounded."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "bioetl"
ISSUE_MARKER = "(#10534"
REVIEW_DATE_RE = re.compile(r"review\s+\d{4}-\d{2}-\d{2}")

# Only the defensive ContentHashPolicyGroup guard may remain excluded.
# Runner dispatch mixins no longer carry NotImplementedError stubs; host
# methods resolve through Protocol + MRO to covered implementations.
ALLOWED_PRAGMAS = {
    "src/bioetl/application/core/record_processor_config.py": 1,
}
COVERED_NO_PRAGMA = (
    "src/bioetl/application/core/wiring/lazy_export_hooks.py",
    "src/bioetl/composition/lazy_exports.py",
    "src/bioetl/composition/runtime_builders/_run_manifest_refs.py",
    "src/bioetl/composition/runtime_builders/inputs_resolver.py",
    "src/bioetl/application/composite/runner_pkg/runner_merge_stage_dispatch_mixin.py",
    "src/bioetl/application/composite/runner_pkg/runner_stage_support_dispatch_mixin.py",
)
# Acceptance for #10534: runner host paths exercised by focused tests.
RUNNER_PATH_COVERAGE_ANCHORS = (
    "tests/unit/application/composite/test_runner_observability_mixin.py",
    "tests/unit/application/composite/test_runner_fsm.py",
    "tests/unit/application/composite/test_runner_required_flag.py",
    "tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py",
    "tests/integration/application/core/test_record_processor.py",
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
                if ISSUE_MARKER not in line or REVIEW_DATE_RE.search(line) is None:
                    offenders.append(f"{rel}: missing issue link/date: {line.strip()}")
    assert offenders == []


@pytest.mark.architecture
def test_covered_lazy_hooks_carry_no_pragma() -> None:
    offenders = [rel for rel in COVERED_NO_PRAGMA if _pragma_lines(ROOT / rel)]
    assert offenders == []


@pytest.mark.architecture
def test_issue_10534_runner_path_coverage_anchors_exist() -> None:
    missing = [
        rel for rel in RUNNER_PATH_COVERAGE_ANCHORS if not (ROOT / rel).is_file()
    ]
    assert missing == [], (
        "AUD-009/#10534 runner-path coverage anchors missing:\n"
        + "\n".join(missing)
    )
