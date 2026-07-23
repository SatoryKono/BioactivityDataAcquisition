"""Cross-shell contracts for repository environment loading and aliases."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

ROOT = Path(__file__).resolve().parents[6]
BASH_LOADER = ROOT / "scripts" / "ops" / "support" / "load_repo_env.sh"
POWERSHELL_LOADER = ROOT / "scripts" / "ai" / "mcp" / "support" / "load_repo_env.ps1"
POWERSHELL = (
    shutil.which("pwsh") or shutil.which("powershell") or shutil.which("powershell.exe")
)
POWERSHELL_MARK = pytest.mark.skipif(
    POWERSHELL is None,
    reason="PowerShell is required for loader parity contracts",
)

ENV_NAMES = (
    "BIOETL_ENV_FILE",
    "BIOETL_REPO_ENV_LOADED",
    "BIOETL_SKIP_ENV_LOCAL",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "NEO4J_AUTH",
    "NEO4J_USERNAME",
    "NEO4J_PASSWORD",
)


def _clean_env(**updates: str | None) -> dict[str, str]:
    env = {
        name: value
        for name, value in os.environ.items()
        if name not in ENV_NAMES and not name.startswith("NEO4J_")
    }
    for name, value in updates.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _bash_path(path: Path) -> str:
    """Return a path form that Git Bash / WSL bash can source on Windows."""
    resolved = path.resolve()
    if os.name != "nt":
        return str(resolved)

    wslpath = shutil.which("wslpath")
    if wslpath is not None:
        result = subprocess.run(
            [wslpath, "-u", str(resolved)],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

    cygpath = shutil.which("cygpath")
    if cygpath is not None:
        result = subprocess.run(
            [cygpath, "-u", str(resolved)],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix()[len(resolved.drive) :]
    wsl_candidate = f"/mnt/{drive}{tail}"
    probe = subprocess.run(
        ["bash", "-c", f"test -e {shlex.quote(wsl_candidate)}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if probe.returncode == 0:
        return wsl_candidate
    return f"/{drive}{tail}"


def _run_bash(
    body: str, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    selected_env = env or _clean_env()
    # WSL bash often does not inherit Windows process env cleanly; inject the
    # contract-relevant variables into the shell command itself.
    setup: list[str] = []
    tracked_names = set(ENV_NAMES) | {
        name for name in selected_env if name.startswith("NEO4J_")
    }
    for name in sorted(tracked_names):
        if name in selected_env:
            value = selected_env[name]
            if name == "BIOETL_ENV_FILE":
                value = _bash_path(Path(value))
            setup.append(f"export {name}={shlex.quote(value)}")
        else:
            setup.append(f"unset {name}")
    setup.append(f"source {shlex.quote(_bash_path(BASH_LOADER))}")
    setup.append(body)
    return subprocess.run(
        ["bash", "-c", "\n".join(setup)],
        cwd=ROOT,
        env=selected_env,
        text=True,
        capture_output=True,
        check=False,
    )


def _powershell_path(path: Path) -> str:
    if os.name == "nt" or not str(POWERSHELL).lower().endswith(".exe"):
        return str(path)
    result = subprocess.run(
        ["wslpath", "-w", str(path)],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _run_powershell(
    body: str, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL is not None
    selected_env = env or _clean_env()
    setup: list[str] = []
    for name in ENV_NAMES:
        if name in selected_env:
            setup.append(f"$env:{name}={_ps_quote(selected_env[name])}")
        else:
            setup.append(f"Remove-Item 'Env:{name}' -ErrorAction SilentlyContinue")
    setup.append(f". {_ps_quote(_powershell_path(POWERSHELL_LOADER))}")
    setup.append(body)
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "; ".join(setup),
        ],
        cwd=ROOT,
        env=selected_env,
        text=True,
        capture_output=True,
        check=False,
    )
    if "UtilBindVsockAnyPort" in result.stderr:
        pytest.skip("Windows PowerShell interop is unavailable in this WSL session")
    return result


def _bash_printenv(*names: str) -> str:
    """Print env values via printenv (WSL bash -c can fail to expand $VAR)."""
    parts = [
        f'printenv {shlex.quote(name)} 2>/dev/null || printf "%s\\n" "unset"'
        for name in names
    ]
    return "; ".join(parts)


def _bash_values(result: subprocess.CompletedProcess[str]) -> tuple[str, str]:
    assert result.returncode == 0, result.stderr
    username, password = result.stdout.splitlines()
    return username, password


def _powershell_values(result: subprocess.CompletedProcess[str]) -> tuple[str, str]:
    assert result.returncode == 0, result.stderr
    username, password = result.stdout.splitlines()
    return username, password


def test_bash_keeps_openai_and_openrouter_credentials_separate() -> None:
    result = _run_bash(
        "normalize_repo_env_aliases; "
        + _bash_printenv("OPENAI_API_KEY", "OPENROUTER_API_KEY"),
        env=_clean_env(
            OPENAI_API_KEY="synthetic-openai-key",
            OPENROUTER_API_KEY=None,
        ),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["synthetic-openai-key", "unset"]


@POWERSHELL_MARK
def test_powershell_keeps_openai_and_openrouter_credentials_separate() -> None:
    result = _run_powershell(
        "Normalize-BioetlRepoEnvAliases; "
        "[Console]::Out.WriteLine($env:OPENAI_API_KEY); "
        "[Console]::Out.WriteLine($(if ($env:OPENROUTER_API_KEY) "
        "{ $env:OPENROUTER_API_KEY } else { 'unset' }))",
        env=_clean_env(
            OPENAI_API_KEY="synthetic-openai-key",
            OPENROUTER_API_KEY=None,
        ),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["synthetic-openai-key", "unset"]


@pytest.mark.parametrize(
    ("openai_key", "openrouter_key"),
    [("synthetic-openai-key", "synthetic-openrouter-key")],
)
def test_bash_preserves_distinct_provider_credentials(
    openai_key: str, openrouter_key: str
) -> None:
    result = _run_bash(
        "normalize_repo_env_aliases; "
        + _bash_printenv("OPENAI_API_KEY", "OPENROUTER_API_KEY"),
        env=_clean_env(
            OPENAI_API_KEY=openai_key,
            OPENROUTER_API_KEY=openrouter_key,
        ),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [openai_key, openrouter_key]


@pytest.mark.parametrize(
    ("auth", "expected"),
    [
        ("fixture-user/fixture-password", ("fixture-user", "fixture-password")),
        ("fixture-user/password/with/slash", ("fixture-user", "password/with/slash")),
    ],
)
def test_bash_neo4j_auth_normalization(auth: str, expected: tuple[str, str]) -> None:
    result = _run_bash(
        "normalize_repo_env_aliases && "
        + _bash_printenv("NEO4J_USERNAME", "NEO4J_PASSWORD"),
        env=_clean_env(NEO4J_AUTH=auth),
    )

    assert _bash_values(result) == expected


@POWERSHELL_MARK
@pytest.mark.parametrize(
    ("auth", "expected"),
    [
        ("fixture-user/fixture-password", ("fixture-user", "fixture-password")),
        ("fixture-user/password/with/slash", ("fixture-user", "password/with/slash")),
    ],
)
def test_powershell_neo4j_auth_normalization(
    auth: str, expected: tuple[str, str]
) -> None:
    result = _run_powershell(
        "Normalize-BioetlRepoEnvAliases; "
        "[Console]::Out.WriteLine($env:NEO4J_USERNAME); "
        "[Console]::Out.WriteLine($env:NEO4J_PASSWORD)",
        env=_clean_env(NEO4J_AUTH=auth),
    )

    assert _powershell_values(result) == expected


@pytest.mark.parametrize("auth", ["fixture-user", "/fixture-password", "fixture-user/"])
@pytest.mark.parametrize("explicit_credentials", [False, True])
def test_bash_rejects_malformed_neo4j_auth_without_leaking(
    auth: str, explicit_credentials: bool
) -> None:
    result = _run_bash(
        "normalize_repo_env_aliases",
        env=_clean_env(
            NEO4J_AUTH=auth,
            NEO4J_USERNAME="explicit-user" if explicit_credentials else None,
            NEO4J_PASSWORD="explicit-password" if explicit_credentials else None,
        ),
    )

    assert result.returncode != 0
    assert "NEO4J_AUTH must use non-empty username/password format" in result.stderr
    assert auth not in result.stdout + result.stderr


@POWERSHELL_MARK
@pytest.mark.parametrize("auth", ["fixture-user", "/fixture-password", "fixture-user/"])
@pytest.mark.parametrize("explicit_credentials", [False, True])
def test_powershell_rejects_malformed_neo4j_auth_without_leaking(
    auth: str, explicit_credentials: bool
) -> None:
    result = _run_powershell(
        "Normalize-BioetlRepoEnvAliases",
        env=_clean_env(
            NEO4J_AUTH=auth,
            NEO4J_USERNAME="explicit-user" if explicit_credentials else None,
            NEO4J_PASSWORD="explicit-password" if explicit_credentials else None,
        ),
    )

    assert result.returncode != 0
    assert "NEO4J_AUTH must use non-empty username/password format" in result.stderr
    assert auth not in result.stdout + result.stderr


def test_bash_explicit_neo4j_credentials_take_precedence() -> None:
    result = _run_bash(
        "normalize_repo_env_aliases && "
        + _bash_printenv("NEO4J_USERNAME", "NEO4J_PASSWORD"),
        env=_clean_env(
            NEO4J_AUTH="packed-user/packed-password",
            NEO4J_USERNAME="explicit-user",
            NEO4J_PASSWORD="explicit-password",
        ),
    )

    assert _bash_values(result) == ("explicit-user", "explicit-password")


@POWERSHELL_MARK
def test_powershell_explicit_neo4j_credentials_take_precedence() -> None:
    result = _run_powershell(
        "Normalize-BioetlRepoEnvAliases; "
        "[Console]::Out.WriteLine($env:NEO4J_USERNAME); "
        "[Console]::Out.WriteLine($env:NEO4J_PASSWORD)",
        env=_clean_env(
            NEO4J_AUTH="packed-user/packed-password",
            NEO4J_USERNAME="explicit-user",
            NEO4J_PASSWORD="explicit-password",
        ),
    )

    assert _powershell_values(result) == ("explicit-user", "explicit-password")


def test_bash_loader_reads_explicit_fixture_and_skips_local_overlay(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture.envdata"
    fixture.write_text("NEO4J_AUTH=file-user/file/password\n", encoding="utf-8")
    result = _run_bash(
        "load_repo_env_if_present && "
        + _bash_printenv("NEO4J_USERNAME", "NEO4J_PASSWORD"),
        env=_clean_env(
            BIOETL_ENV_FILE=str(fixture),
            BIOETL_SKIP_ENV_LOCAL="1",
        ),
    )

    assert _bash_values(result) == ("file-user", "file/password")


@POWERSHELL_MARK
def test_powershell_loader_reads_explicit_fixture_and_skips_local_overlay(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture.envdata"
    fixture.write_text("NEO4J_AUTH=file-user/file/password\n", encoding="utf-8")
    result = _run_powershell(
        f"Import-BioetlRepoEnv -RepoRoot {_ps_quote(_powershell_path(ROOT))}; "
        "[Console]::Out.WriteLine($env:NEO4J_USERNAME); "
        "[Console]::Out.WriteLine($env:NEO4J_PASSWORD)",
        env=_clean_env(
            BIOETL_ENV_FILE=_powershell_path(fixture),
            BIOETL_SKIP_ENV_LOCAL="1",
        ),
    )

    assert _powershell_values(result) == ("file-user", "file/password")


def test_loader_sources_govern_missing_credentials_and_local_skip_consistently() -> (
    None
):
    shell_source = BASH_LOADER.read_text(encoding="utf-8")
    powershell_source = POWERSHELL_LOADER.read_text(encoding="utf-8")

    assert 'env_local_file=""' in shell_source
    assert (
        '$envLocalFile = if ($env:BIOETL_SKIP_ENV_LOCAL -eq "1")' in powershell_source
    )
    assert 'if [[ -z "${NEO4J_AUTH:-}"' in shell_source
    assert "if ($env:NEO4J_AUTH" in powershell_source
