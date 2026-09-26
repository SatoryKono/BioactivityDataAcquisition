# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
