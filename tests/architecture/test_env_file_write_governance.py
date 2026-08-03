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
"""Regression checks for local env-file write governance."""

from __future__ import annotations

from pathlib import Path
import re

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
OPT_IN = "BIOETL_CREATE_LOCAL_ENV_FILES"
ENV_FILE_TOKEN_PATTERN = re.compile(r"\.env(?:[A-Za-z0-9_.-]*)?")
ENV_WRITE_OPERATOR_PATTERN = re.compile(
    r"\b(?:cat|cp)\b\s*>?|\b(?:Set-Content|Out-File|Add-Content|Copy-Item|New-Item)\b"
)
SHELL_ENV_VAR_ASSIGNMENT_PATTERN = re.compile(
    r"^\s*(?:local\s+|declare\s+(?:-[A-Za-z]+\s+)?)?"
    r"([A-Za-z_][A-Za-z0-9_]*)=.*\.env",
    re.MULTILINE,
)
POWERSHELL_ENV_VAR_ASSIGNMENT_PATTERN = re.compile(
    r"^\s*\$([A-Za-z_][A-Za-z0-9_]*)\s*=.*\.env", re.MULTILINE
)
NON_MUTATING_DEFAULT_MARKERS = (
    "without BIOETL_CREATE_LOCAL_ENV_FILES=1",
    "rerun with BIOETL_CREATE_LOCAL_ENV_FILES=1",
    "не создает .env автоматически",
)

ENV_WRITE_SURFACES = (
    "scripts/ai/codex/setup.ps1",
    "scripts/ai/codex/run-codex.sh",
    "scripts/ai/gemini/run-gemini.sh",
    "scripts/ai/codex/helper/setup-env.sh",
    "scripts/ai/gemini/helper/setup-env.sh",
    "scripts/ai/codex/helper/check-env.ps1",
    "scripts/ai/gemini/run-gemini-docker.ps1",
    "scripts/ai/vibe/helper/setup-env.sh",
    "scripts/memory/setup/wsl_startup.sh",
)


def _env_file_variable_names(text: str, *, suffix: str) -> set[str]:
    if suffix == ".ps1":
        pattern = POWERSHELL_ENV_VAR_ASSIGNMENT_PATTERN
    else:
        pattern = SHELL_ENV_VAR_ASSIGNMENT_PATTERN
    return {match.group(1) for match in pattern.finditer(text)}


def _line_references_env_file(line: str, env_var_names: set[str]) -> bool:
    if ENV_FILE_TOKEN_PATTERN.search(line):
        return True
    return any(f"${name}" in line or f"${{{name}}}" in line for name in env_var_names)


def _script_can_write_env_file(path: Path, text: str) -> bool:
    env_var_names = _env_file_variable_names(text, suffix=path.suffix)
    return any(
        ENV_WRITE_OPERATOR_PATTERN.search(line)
        and _line_references_env_file(line, env_var_names)
        for line in text.splitlines()
    )


def _iter_detected_env_write_surfaces() -> tuple[str, ...]:
    surfaces: list[str] = []
    for path in sorted((ROOT / "scripts").rglob("*")):
        if path.suffix not in {".sh", ".ps1"}:
            continue
        text = path.read_text(encoding="utf-8")
        if _script_can_write_env_file(path, text):
            surfaces.append(path.relative_to(ROOT).as_posix())
    return tuple(surfaces)


def test_env_file_write_surface_list_matches_script_scan() -> None:
    """Every script-level .env* write path must be explicitly governed."""
    detected = set(_iter_detected_env_write_surfaces())
    expected = set(ENV_WRITE_SURFACES)

    assert detected == expected, (
        "Detected .env* write surfaces must match the explicit governance list.\n"
        f"Unexpected: {sorted(detected - expected)}\n"
        f"Missing from scan: {sorted(expected - detected)}"
    )


@pytest.mark.parametrize("relative_path", ENV_WRITE_SURFACES)
def test_env_file_writes_require_explicit_local_opt_in(relative_path: str) -> None:
    """Scripts that can write .env* files must expose an explicit opt-in gate."""
    text = (ROOT / relative_path).read_text(encoding="utf-8")

    assert OPT_IN in text, f"{relative_path} must gate .env writes with {OPT_IN}=1"
    assert any(marker in text for marker in NON_MUTATING_DEFAULT_MARKERS), (
        f"{relative_path} must document non-mutating default behavior"
    )


def test_memory_wsl_startup_does_not_upsert_env_local_without_opt_in() -> None:
    """Existing .env.local files are still machine-local and must not be mutated by default."""
    text = (ROOT / "scripts/memory/setup/wsl_startup.sh").read_text(encoding="utf-8")

    assert "ENV_FILE_WRITE_ALLOWED=0" in text
    assert 'if [[ "${BIOETL_CREATE_LOCAL_ENV_FILES:-0}" == "1" ]]; then' in text
    assert "if [[ ${ENV_FILE_WRITE_ALLOWED} -eq 1 ]]; then" in text
    assert text.index("if [[ ${ENV_FILE_WRITE_ALLOWED} -eq 1 ]]; then") < text.index(
        'upsert_env_local "$ENV_LOCAL" "NEO4J_URI"'
    )
