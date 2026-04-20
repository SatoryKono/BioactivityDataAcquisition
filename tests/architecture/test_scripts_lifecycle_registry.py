"""Architecture tests for scripts lifecycle registry coverage."""

from __future__ import annotations

import pytest
from tests.helpers import repo_root, run_repo_python


@pytest.mark.slow
@pytest.mark.timeout(300)
def test_scripts_lifecycle_registry_check_passes() -> None:
    """Lifecycle registry must cover all non-active scripts with valid entries."""
    root = repo_root()
    result = run_repo_python(
        "scripts/engineering/repo/check_scripts_inventory.py",
        "--check-lifecycle",
        "--forbid-evaluate-active",
        "--lifecycle-registry",
        "configs/quality/scripts_lifecycle_registry.json",
        cwd=root,
    )
    assert result.returncode == 0, (
        "Scripts lifecycle registry validation failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
    )
