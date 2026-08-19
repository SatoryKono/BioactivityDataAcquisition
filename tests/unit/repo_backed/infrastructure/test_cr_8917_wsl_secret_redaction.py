"""Repository-backed WSL secret-redaction regression for #8917."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.repo_backed


def test_wsl_startup_does_not_pass_password_on_python_argv() -> None:
    script = Path("scripts/memory/setup/wsl_startup.sh").read_text(encoding="utf-8")
    assert 'python3 - "$file_path" "$key" "$value"' not in script
    assert "BIOETL_ENV_UPSERT_VALUE" in script
    assert 'os.environ["BIOETL_ENV_UPSERT_VALUE"]' in script
