"""Architecture guardrails for the pretest memory validation phase."""

from __future__ import annotations

from pathlib import Path

import yaml


def test_pretest_guardrails_script_runs_memory_phase() -> None:
    script = Path("scripts/engineering/dev/pretest_guardrails.sh").read_text(
        encoding="utf-8"
    )

    assert "run_memory_checks()" in script
    assert "memory-validate" in script
    assert '"$PYTHON_BIN" -m memory.tooling.validate' in script
    assert "memory-refresh-smoke" in script
    assert '"$PYTHON_BIN" -m memory.tooling.refresh_all' in script
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
