"""Architecture guardrails for the pretest memory validation phase."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml


pytestmark = pytest.mark.architecture


def test_pretest_guardrails_script_runs_memory_phase() -> None:
    script = Path("scripts/engineering/dev/pretest_guardrails.sh").read_text(
        encoding="utf-8"
    )

    assert "run_memory_checks()" in script
    assert "memory-validate" in script
    assert '"$PYTHON_BIN" -m memory.tooling.validate' in script
    assert "memory-workflow-smoke" in script
    assert '"$PYTHON_BIN" -m memory.tooling.workflow smoke' in script
    assert "memory-refresh-smoke" in script
    assert '"$PYTHON_BIN" -m memory.tooling.refresh_all' in script
    assert "--rag-build-scope full" in script
    assert "memory-rag-manifest-validate" in script
    assert '"$PYTHON_BIN" -m memory.rag.validation' in script
    assert '"$MEMORY_TMP_OUTPUT/rag/manifests"' in script
    assert "--require-build-scope full" in script
    assert "TMP_DIR" not in script
    assert "memory-prune-dry-run" in script
    assert '"$PYTHON_BIN" -m memory.tooling.prune --json' in script
    assert "run_memory_checks" in script.split("main() {", 1)[1]


def test_pretest_guardrails_profiles_enable_memory_checks() -> None:
    config = yaml.safe_load(
        Path("configs/quality/pretest_guardrails.yaml").read_text(encoding="utf-8")
    )

    profiles = config["profiles"]
    for profile_name in ("light", "governance", "full", "strict"):
        assert profiles[profile_name]["run_memory_checks"] is True


def test_pretest_guardrails_default_mode_is_read_only_check() -> None:
    script = Path("scripts/engineering/dev/pretest_guardrails.sh").read_text(
        encoding="utf-8"
    )

    assert 'MODE="check"' in script
    assert "check: validate only (default)" in script
    assert "[pretest-guardrails][write] auto mode enabled" in script


def test_pretest_guardrails_inventory_sync_is_auto_mode_only() -> None:
    script = Path("scripts/engineering/dev/pretest_guardrails.sh").read_text(
        encoding="utf-8"
    )
    repo_checks = script.split("run_repo_checks() {", 1)[1].split(
        "run_docs_identity_checks() {", 1
    )[0]

    assert 'if [[ "$MODE" == "auto" ]]; then' in repo_checks
    assert repo_checks.count("inventory-sync-final") == 1
