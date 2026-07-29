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
"""Architecture checks for consolidated dev test runner wrappers."""

from __future__ import annotations

import pytest

from tests.helpers import repo_root, run_repo_python


pytestmark = pytest.mark.architecture

SUPPORTED_DEV_TEST_WRAPPERS = {
    "scripts/engineering/dev/run_tests.sh": 'dirname "$0")/../../..',
    "scripts/engineering/dev/test_changed.sh": 'dirname "$0")/../../..',
    "scripts/engineering/dev/run_tests.ps1": 'Join-Path $PSScriptRoot "../../.."',
}


def test_run_tests_backend_help_works() -> None:
    """Canonical backend should provide help output with zero exit code.

    ``run_tests.py help`` exits before heavy imports (see early-exit guard in the
    script). Keep the subprocess budget well under the suite pytest-timeout so a
    hung child fails the helper quickly instead of the whole PyCharm run.
    """
    root = repo_root()
    result = run_repo_python(
        "scripts/engineering/dev/run_tests.py",
        "help",
        cwd=root,
        timeout=30.0,
    )
    assert result.returncode == 0, result.stderr
    assert "BioETL Test Runner" in result.stdout


def test_sh_wrapper_delegates_to_backend() -> None:
    """Bash wrapper must stay a thin facade over the Python backend."""
    root = repo_root()
    content = (root / "scripts/engineering/dev/run_tests.sh").read_text(
        encoding="utf-8"
    )
    assert "scripts/engineering/dev/run_tests.py" in content
    assert 'dirname "$0")/../../..' in content


def test_ps1_wrapper_delegates_to_backend() -> None:
    """PowerShell wrapper must stay a thin facade over the Python backend."""
    root = repo_root()
    content = (root / "scripts/engineering/dev/run_tests.ps1").read_text(
        encoding="utf-8"
    )
    assert "scripts/engineering/dev/run_tests.py" in content
    assert 'Join-Path $PSScriptRoot "../../.."' in content


def test_changed_wrapper_delegates_to_backend_changed_command() -> None:
    """Legacy changed-tests wrapper must stay a thin facade over run_tests.py."""
    root = repo_root()
    content = (root / "scripts/engineering/dev/test_changed.sh").read_text(
        encoding="utf-8"
    )
    assert "scripts/engineering/dev/run_tests.py changed" in content
    assert 'dirname "$0")/../../..' in content


def test_supported_dev_test_wrappers_resolve_repo_root_from_script_location() -> None:
    """Developer wrappers must not depend on caller cwd or nested checkout depth."""
    root = repo_root()
    for rel_path, root_resolution_snippet in SUPPORTED_DEV_TEST_WRAPPERS.items():
        content = (root / rel_path).read_text(encoding="utf-8")
        assert root_resolution_snippet in content, rel_path
        assert "scripts/engineering/dev/run_tests.py" in content, rel_path
