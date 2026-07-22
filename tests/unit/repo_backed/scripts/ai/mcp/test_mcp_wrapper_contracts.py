"""Behavioral contracts for cross-platform MCP support and wrapper scripts."""

from __future__ import annotations

import json
import hashlib
import os
import re
import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

ROOT = Path(__file__).resolve().parents[6]
MCP_DIR = ROOT / "scripts" / "ai" / "mcp"
TOKEN_VALIDATION_PS1 = MCP_DIR / "support" / "token_validation.ps1"
UV_RESOLVER_SH = MCP_DIR / "support" / "uv_resolver.sh"
UV_RESOLVER_PS1 = MCP_DIR / "support" / "uv_resolver.ps1"
FETCH_SH = MCP_DIR / "mcp_fetch_wrapper.sh"
FETCH_PS1 = MCP_DIR / "mcp_fetch_wrapper.ps1"
CHECK_SH = MCP_DIR / "check.sh"
CODE_INTERPRETER_PS1 = MCP_DIR / "mcp_code_interpreter_wrapper.ps1"
NEO4J_CYPHER_SH = MCP_DIR / "mcp_neo4j_cypher_wrapper.sh"
MUTMUT_SH = MCP_DIR / "mcp_mutmut_wrapper.sh"
MUTMUT_PS1 = MCP_DIR / "mcp_mutmut_wrapper.ps1"
ADR_ANALYSIS_PS1 = MCP_DIR / "mcp_adr_analysis_wrapper.ps1"
CONTEXT7_SH = MCP_DIR / "mcp_context7_wrapper.sh"
CONTEXT7_PS1 = MCP_DIR / "mcp_context7_wrapper.ps1"

POWERSHELL = (
    shutil.which("pwsh") or shutil.which("powershell") or shutil.which("powershell.exe")
)
POWERSHELL_MARK = pytest.mark.skipif(
    POWERSHELL is None,
    reason="PowerShell is required for the Windows MCP wrapper contracts",
)
BASH_MARK = pytest.mark.skipif(
    shutil.which("bash") is None,
    reason="bash is required for the shell MCP wrapper contracts",
)

CONTEXT7_PACKAGE = "@upstash/context7-mcp@3.2.4"
MUTMUT_COMMIT = "1e3b47ccaaa31f4c651d8e424b90d392d1c1ed90"
EXAMPLE_CONTEXT7_KEY = "example-context7-key"

POWERSHELL_WRAPPER_ENV_NAMES = (
    "PATH",
    "USERPROFILE",
    "UV_CACHE_DIR",
    "UV_TOOL_DIR",
    "DENO_DIR",
    "NPM_CONFIG_CACHE",
    "BIOETL_REPO_ENV_LOADED",
    "BIOETL_MCP_VALIDATE_ONLY",
    "BIOETL_TEST_CAPTURE",
    "BIOETL_TEST_EXIT_CODE",
    "BIOETL_TEST_PYTHON_PROBE",
    "CONTEXT7_API_KEY",
    "CONTEXT7_API_TOKEN",
    "UPSTASH_CONTEXT7_API_KEY",
    "EXECUTION_MODE",
    "ADR_PATH",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
)


def _clean_env(**updates: str | None) -> dict[str, str]:
    """Return an environment without inherited credentials or proxy settings."""
    sensitive_fragments = ("TOKEN", "API_KEY", "PASSWORD", "SECRET")
    proxy_names = {
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    }
    env = {
        name: value
        for name, value in os.environ.items()
        if not any(fragment in name for fragment in sensitive_fragments)
        and name not in proxy_names
        and not name.startswith("NEO4J_")
    }
    env["BIOETL_REPO_ENV_LOADED"] = "1"
    for name, value in updates.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _run_bash(
    script: str, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", script],
        cwd=ROOT,
        env=env or _clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def _powershell_path(path: Path) -> str:
    """Translate WSL paths for Windows PowerShell while preserving native paths."""
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


def _run_powershell_command(
    command: str, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL is not None
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        cwd=ROOT,
        env=env or _clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def _run_powershell_file(
    path: Path, *, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL is not None
    setup = []
    for name in POWERSHELL_WRAPPER_ENV_NAMES:
        if name in env:
            setup.append(f"$env:{name}={_ps_quote(env[name])}")
        else:
            setup.append(f"Remove-Item 'Env:{name}' -ErrorAction SilentlyContinue")
    setup.append(f"& {_ps_quote(_powershell_path(path))}")
    setup.append("exit $LASTEXITCODE")
    return subprocess.run(
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
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.fixture
def windows_fixture_dir(request: pytest.FixtureRequest) -> Iterator[Path]:
    """Create a Windows-addressable ignored directory for fake launchers."""
    base_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", request.node.originalname)
    node_hash = hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:12]
    safe_name = f"{base_name}-{node_hash}"
    path = ROOT / ".cache" / "mcp-contract-tests" / safe_name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _write_bash_launcher(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env bash
set -eu
capture_file="${BIOETL_TEST_CAPTURE:?}"
printf 'executable=%s\n' "$0" >"${capture_file}"
for argument in "$@"; do
  printf 'arg=%s\n' "${argument}" >>"${capture_file}"
done
if [[ -n "${CONTEXT7_API_KEY:-}" ]]; then
  printf 'context7_key_present=yes\n' >>"${capture_file}"
else
  printf 'context7_key_present=no\n' >>"${capture_file}"
fi
printf 'neo4j_username=%s\n' "${NEO4J_USERNAME:-}" >>"${capture_file}"
printf 'neo4j_password=%s\n' "${NEO4J_PASSWORD:-}" >>"${capture_file}"
exit "${BIOETL_TEST_EXIT_CODE:-0}"
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_windows_launcher(path: Path) -> None:
    path.write_text(
        """if ($env:BIOETL_TEST_PYTHON_PROBE -eq '1' -and $args[0] -eq '-c') {
    exit 0
}
"executable=$PSCommandPath" | Set-Content -LiteralPath $env:BIOETL_TEST_CAPTURE
foreach ($argument in $args) {
    "arg=$argument" | Add-Content -LiteralPath $env:BIOETL_TEST_CAPTURE
}
$keyState = if ($env:CONTEXT7_API_KEY) { 'yes' } else { 'no' }
"context7_key_present=$keyState" | Add-Content -LiteralPath $env:BIOETL_TEST_CAPTURE
"execution_mode=$env:EXECUTION_MODE" | Add-Content -LiteralPath $env:BIOETL_TEST_CAPTURE
"project_path=$env:PROJECT_PATH" | Add-Content -LiteralPath $env:BIOETL_TEST_CAPTURE
"adr_path=$env:ADR_PATH" | Add-Content -LiteralPath $env:BIOETL_TEST_CAPTURE
"ignore_scripts=$env:npm_config_ignore_scripts" | Add-Content -LiteralPath $env:BIOETL_TEST_CAPTURE
exit [int]$env:BIOETL_TEST_EXIT_CODE
""",
        encoding="utf-8",
        newline="",
    )


def _windows_wrapper_env(
    fixture_dir: Path,
    capture_file: Path,
    **updates: str | None,
) -> dict[str, str]:
    windows_dir = _powershell_path(fixture_dir)
    env = _clean_env(
        PATH=f"{windows_dir};C:\\Windows\\System32;C:\\Windows",
        USERPROFILE=windows_dir,
        UV_CACHE_DIR=f"{windows_dir}\\uv-cache",
        UV_TOOL_DIR=f"{windows_dir}\\uv-tools",
        DENO_DIR=f"{windows_dir}\\deno-cache",
        NPM_CONFIG_CACHE=f"{windows_dir}\\npm-cache",
        BIOETL_TEST_CAPTURE=_powershell_path(capture_file),
        BIOETL_TEST_EXIT_CODE="0",
    )
    for name, value in updates.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


@POWERSHELL_MARK
@pytest.mark.parametrize(
    ("command", "expected_warning"),
    [
        (
            "Remove-Item Env:OPTIONAL_TOKEN -ErrorAction SilentlyContinue; "
            "Test-McpOptionalToken -Name 'OPTIONAL_TOKEN' -MinLength 8 "
            "-Purpose 'test MCP'",
            "OPTIONAL_TOKEN is not set for test MCP",
        ),
        (
            "Remove-Item Env:NEO4J_URI,Env:NEO4J_USERNAME,Env:NEO4J_PASSWORD "
            "-ErrorAction SilentlyContinue; "
            "Test-McpNeo4jCredentials -Purpose 'test Neo4j MCP'",
            "NEO4J_PASSWORD is not set for test Neo4j MCP",
        ),
        (
            "$env:NEO4J_URI='bolt://example.invalid:7687'; "
            "$env:NEO4J_USERNAME='example-user'; "
            "$env:NEO4J_PASSWORD='example_secure_password'; "
            "Test-McpNeo4jCredentials -Purpose 'test Neo4j MCP'",
            "matches a legacy placeholder pattern",
        ),
    ],
)
def test_powershell_token_warnings_stay_on_stderr(
    command: str, expected_warning: str
) -> None:
    helper = _ps_quote(_powershell_path(TOKEN_VALIDATION_PS1))
    result = _run_powershell_command(f". {helper}; {command}")

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert expected_warning in result.stderr
    assert "example_secure_password" not in result.stdout


@BASH_MARK
def test_bash_uv_resolver_prefers_uvx_on_path(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_uvx = fake_bin / "uvx"
    _write_bash_launcher(fake_uvx)
    env = _clean_env(PATH=f"{fake_bin}:/usr/bin:/bin")

    result = _run_bash(
        f"source {shlex.quote(str(UV_RESOLVER_SH))}; bioetl_resolve_uvx_bin",
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(fake_uvx)


@BASH_MARK
def test_bash_uv_resolver_finds_uv_sibling(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_uv = fake_bin / "uv"
    fake_uvx = fake_bin / "uvx"
    _write_bash_launcher(fake_uv)
    _write_bash_launcher(fake_uvx)
    env = _clean_env(PATH="/usr/bin:/bin")
    script = f"""
source {shlex.quote(str(UV_RESOLVER_SH))}
command() {{
  if [[ "$1" == "-v" && "$2" == "uvx" ]]; then
    return 1
  fi
  if [[ "$1" == "-v" && "$2" == "uv" ]]; then
    printf '%s\n' {shlex.quote(str(fake_uv))}
    return 0
  fi
  builtin command "$@"
}}
bioetl_resolve_uvx_bin
"""

    result = _run_bash(script, env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(fake_uvx)


@BASH_MARK
def test_bash_uv_resolver_uses_home_fallback(tmp_path: Path) -> None:
    fake_uvx = tmp_path / ".local" / "bin" / "uvx"
    fake_uvx.parent.mkdir(parents=True)
    _write_bash_launcher(fake_uvx)
    env = _clean_env(PATH="/usr/bin:/bin", HOME=str(tmp_path), LOCALAPPDATA="")

    result = _run_bash(
        f"source {shlex.quote(str(UV_RESOLVER_SH))}; bioetl_resolve_uvx_bin",
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(fake_uvx)


@BASH_MARK
def test_bash_uv_resolver_reports_unavailable(tmp_path: Path) -> None:
    env = _clean_env(PATH="/usr/bin:/bin", HOME=str(tmp_path), LOCALAPPDATA="")
    script = f"""
source {shlex.quote(str(UV_RESOLVER_SH))}
resolved="$(bioetl_resolve_uvx_bin)"
status=$?
printf '%s\n%s\n' "${{resolved}}" "${{status}}"
"""

    result = _run_bash(script, env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["uvx", "1"]


@BASH_MARK
def test_bash_uv_network_bypass_removes_proxy_variables() -> None:
    env = _clean_env(
        HTTP_PROXY="http://proxy.invalid",
        HTTPS_PROXY="http://proxy.invalid",
        ALL_PROXY="http://proxy.invalid",
        http_proxy="http://proxy.invalid",
        https_proxy="http://proxy.invalid",
        all_proxy="http://proxy.invalid",
        KEEP_ME="preserved",
    )
    script = f"""
source {shlex.quote(str(UV_RESOLVER_SH))}
bioetl_enable_uvx_network_bypass
printf '%s\n' "$NO_PROXY" "$no_proxy" "${{HTTP_PROXY-unset}}" \
  "${{https_proxy-unset}}" "$KEEP_ME"
"""

    result = _run_bash(script, env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["*", "*", "unset", "unset", "preserved"]


@POWERSHELL_MARK
@pytest.mark.parametrize(
    ("mock_functions", "expected"),
    [
        (
            "function Get-Command { param($Name, $ErrorAction) "
            "if ($Name -eq 'uvx') { [pscustomobject]@{Source='C:\\fake\\uvx.exe'} } }\n"
            "function Test-Path { param($LiteralPath, $Path, $ErrorAction) $true }\n"
            "function Resolve-Path { param($LiteralPath) "
            "[pscustomobject]@{Path=$LiteralPath} }",
            "C:\\fake\\uvx.exe",
        ),
        (
            "function Get-Command { param($Name, $ErrorAction) "
            "if ($Name -eq 'uv') { [pscustomobject]@{Source='C:\\tools\\uv.exe'} } }\n"
            "function Test-Path { param($LiteralPath, $Path, $ErrorAction) "
            "$LiteralPath -eq 'C:\\tools\\uvx.exe' }\n"
            "function Resolve-Path { param($LiteralPath) "
            "[pscustomobject]@{Path=$LiteralPath} }",
            "C:\\tools\\uvx.exe",
        ),
        (
            "function Get-Command { param($Name, $ErrorAction) $null }\n"
            "function Test-Path { param($LiteralPath, $Path, $ErrorAction) "
            "$LiteralPath -like '*Python313*uvx.exe' }\n"
            "function Resolve-Path { param($LiteralPath) "
            "[pscustomobject]@{Path=$LiteralPath} }",
            "Python313\\Scripts\\uvx.exe",
        ),
    ],
)
def test_powershell_uv_resolver_candidate_paths(
    mock_functions: str, expected: str
) -> None:
    helper = _ps_quote(_powershell_path(UV_RESOLVER_PS1))
    command = (
        f". {helper}; {mock_functions}; "
        "[Console]::Out.WriteLine((Resolve-BioetlUvxBin))"
    )

    result = _run_powershell_command(command)

    assert result.returncode == 0, result.stderr
    assert expected in result.stdout.strip()


@POWERSHELL_MARK
def test_powershell_uv_resolver_reports_unavailable() -> None:
    helper = _ps_quote(_powershell_path(UV_RESOLVER_PS1))
    command = f"""
. {helper}
function Get-Command {{ param($Name, $ErrorAction) $null }}
function Test-Path {{ param($LiteralPath, $Path, $ErrorAction) $false }}
[Console]::Out.WriteLine((Resolve-BioetlUvxBin))
[Console]::Out.WriteLine((Test-BioetlUvxAvailable))
"""

    result = _run_powershell_command(command)

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["uvx", "False"]


@POWERSHELL_MARK
def test_powershell_uv_network_bypass_removes_proxy_variables() -> None:
    helper = _ps_quote(_powershell_path(UV_RESOLVER_PS1))
    command = f"""
. {helper}
$env:HTTP_PROXY='http://proxy.invalid'
$env:HTTPS_PROXY='http://proxy.invalid'
$env:ALL_PROXY='http://proxy.invalid'
$env:http_proxy='http://proxy.invalid'
$env:https_proxy='http://proxy.invalid'
$env:all_proxy='http://proxy.invalid'
$env:KEEP_ME='preserved'
Enable-BioetlUvxNetworkBypass
[ordered]@{{
  no_proxy_value=$env:NO_PROXY
  http_proxy_value=[Environment]::GetEnvironmentVariable('HTTP_PROXY')
  https_proxy_value=[Environment]::GetEnvironmentVariable('https_proxy')
  keep_value=$env:KEEP_ME
}} | ConvertTo-Json -Compress
"""

    result = _run_powershell_command(command)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "no_proxy_value": "*",
        "http_proxy_value": None,
        "https_proxy_value": None,
        "keep_value": "preserved",
    }


@BASH_MARK
def test_bash_fetch_wrapper_executes_resolved_uvx(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_uvx = fake_bin / "uvx"
    capture_file = tmp_path / "fetch-args.txt"
    _write_bash_launcher(fake_uvx)
    env = _clean_env(
        PATH=f"{fake_bin}:/usr/bin:/bin",
        UV_CACHE_DIR=str(tmp_path / "uv-cache"),
        UV_TOOL_DIR=str(tmp_path / "uv-tools"),
        BIOETL_TEST_CAPTURE=str(capture_file),
        BIOETL_TEST_EXIT_CODE="17",
    )

    result = _run_bash(shlex.quote(str(FETCH_SH)), env=env)

    assert result.returncode == 17
    assert result.stdout == ""
    captured = capture_file.read_text(encoding="utf-8").splitlines()
    assert captured[:5] == [
        f"executable={fake_uvx}",
        "arg=--python",
        "arg=3.13",
        "arg=--from",
        "arg=mcp-server-fetch==2025.4.7",
    ]
    assert "arg=mcp-server-fetch" in captured


@POWERSHELL_MARK
def test_powershell_fetch_wrapper_executes_resolved_uvx(
    windows_fixture_dir: Path,
) -> None:
    fake_uvx = windows_fixture_dir / "uvx.ps1"
    capture_file = windows_fixture_dir / "fetch-args.txt"
    _write_windows_launcher(fake_uvx)
    env = _windows_wrapper_env(
        windows_fixture_dir,
        capture_file,
    )

    result = _run_powershell_file(FETCH_PS1, env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    captured = capture_file.read_text(encoding="utf-8").splitlines()
    assert "arg=--python" in captured
    assert "arg=3.13" in captured
    assert "arg=--from" in captured
    assert "arg=mcp-server-fetch==2025.4.7" in captured
    assert "arg=mcp-server-fetch" in captured


def test_fetch_source_assertions_accept_and_reject_contract_fixtures() -> None:
    check_source = CHECK_SH.read_text(encoding="utf-8")
    patterns = re.findall(
        r'require_contains "\$fetch_wrapper_source" \'([^\']+)\'',
        check_source,
    )
    assert patterns == [
        "mcp-server-fetch==2025.4.7",
        "bioetl_resolve_uvx_bin",
        "--python 3.13",
    ]

    passing = " ".join(patterns)
    assert all(pattern in passing for pattern in patterns)
    for omitted in patterns:
        failing = " ".join(pattern for pattern in patterns if pattern != omitted)
        assert not all(pattern in failing for pattern in patterns)
    assert "uvx --python 3.13" not in patterns


@POWERSHELL_MARK
def test_code_interpreter_uses_local_python_without_deno(
    windows_fixture_dir: Path,
) -> None:
    fake_python = windows_fixture_dir / "python.ps1"
    capture_file = windows_fixture_dir / "python-args.txt"
    _write_windows_launcher(fake_python)
    env = _windows_wrapper_env(
        windows_fixture_dir,
        capture_file,
        BIOETL_TEST_PYTHON_PROBE="1",
    )

    result = _run_powershell_file(CODE_INTERPRETER_PS1, env=env)

    assert result.returncode == 0, result.stderr
    captured = capture_file.read_text(encoding="utf-8").splitlines()
    assert "arg=-m" in captured
    assert "arg=mcp_server_code_interpreter" in captured
    assert "Deno" not in result.stderr


@POWERSHELL_MARK
def test_code_interpreter_uvx_fallback_requires_deno(
    windows_fixture_dir: Path,
) -> None:
    _write_windows_launcher(windows_fixture_dir / "uvx.ps1")
    capture_file = windows_fixture_dir / "uvx-args.txt"
    env = _windows_wrapper_env(windows_fixture_dir, capture_file)

    result = _run_powershell_file(CODE_INTERPRETER_PS1, env=env)

    assert result.returncode != 0
    assert "requires Deno for the mcp-run-python fallback" in result.stderr
    assert not capture_file.exists()


@POWERSHELL_MARK
def test_code_interpreter_executes_uvx_when_deno_is_available(
    windows_fixture_dir: Path,
) -> None:
    _write_windows_launcher(windows_fixture_dir / "deno.ps1")
    _write_windows_launcher(windows_fixture_dir / "uvx.ps1")
    capture_file = windows_fixture_dir / "uvx-args.txt"
    env = _windows_wrapper_env(windows_fixture_dir, capture_file)

    result = _run_powershell_file(CODE_INTERPRETER_PS1, env=env)

    assert result.returncode == 0, result.stderr
    captured = capture_file.read_text(encoding="utf-8").splitlines()
    assert "arg=--from" in captured
    assert "arg=mcp-run-python==0.0.22" in captured
    assert "arg=mcp-run-python" in captured
    assert "arg=stdio" in captured


@BASH_MARK
@pytest.mark.parametrize(
    "neo4j_auth", ["example-user", "/example-pass", "example-user/"]
)
def test_neo4j_wrapper_rejects_malformed_combined_auth(neo4j_auth: str) -> None:
    env = _clean_env(
        NEO4J_AUTH=neo4j_auth,
        BIOETL_MCP_VALIDATE_ONLY="1",
    )

    result = _run_bash(shlex.quote(str(NEO4J_CYPHER_SH)), env=env)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "NEO4J_AUTH must use non-empty username/password format" in result.stderr
    assert neo4j_auth not in result.stderr


@BASH_MARK
@pytest.mark.parametrize(
    "neo4j_auth", ["example-user/example-pass", "example-user/example/pass"]
)
def test_neo4j_wrapper_accepts_valid_combined_auth(neo4j_auth: str) -> None:
    env = _clean_env(
        NEO4J_AUTH=neo4j_auth,
        BIOETL_MCP_VALIDATE_ONLY="1",
    )

    result = _run_bash(shlex.quote(str(NEO4J_CYPHER_SH)), env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "[OK] neo4j-cypher MCP wrapper validation completed\n"
    assert "example-pass" not in result.stderr


@BASH_MARK
def test_neo4j_explicit_credentials_take_precedence(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_npx = fake_bin / "npx"
    capture_file = tmp_path / "neo4j-env.txt"
    _write_bash_launcher(fake_npx)
    env = _clean_env(
        PATH=f"{fake_bin}:/usr/bin:/bin",
        NEO4J_AUTH="packed-user/packed-password",
        NEO4J_USERNAME="explicit-user",
        NEO4J_PASSWORD="explicit-password",
        BIOETL_TEST_CAPTURE=str(capture_file),
    )

    result = _run_bash(shlex.quote(str(NEO4J_CYPHER_SH)), env=env)

    assert result.returncode == 0, result.stderr
    captured = capture_file.read_text(encoding="utf-8")
    assert "neo4j_username=explicit-user" in captured
    assert "neo4j_password=explicit-password" in captured
    assert "packed-password" not in captured


def test_mutmut_git_dependency_is_pinned_consistently() -> None:
    pattern = re.compile(r"git\+https://github\.com/wdm0006/mutmut-mcp@([0-9a-f]{40})")
    commits = []
    for wrapper in (MUTMUT_SH, MUTMUT_PS1):
        match = pattern.search(wrapper.read_text(encoding="utf-8"))
        assert match is not None, f"missing immutable pin in {wrapper}"
        commits.append(match.group(1))

    assert commits == [MUTMUT_COMMIT, MUTMUT_COMMIT]


@POWERSHELL_MARK
@pytest.mark.parametrize("execution_mode", [None, "full"])
def test_adr_analysis_wrapper_startup_contract(
    windows_fixture_dir: Path,
    execution_mode: str | None,
) -> None:
    fake_npx = windows_fixture_dir / "npx.ps1"
    capture_file = windows_fixture_dir / "adr-args.txt"
    _write_windows_launcher(fake_npx)
    env = _windows_wrapper_env(
        windows_fixture_dir,
        capture_file,
        EXECUTION_MODE=execution_mode,
        ADR_PATH=None,
    )

    result = _run_powershell_file(ADR_ANALYSIS_PS1, env=env)

    assert result.returncode == 0, result.stderr
    captured = capture_file.read_text(encoding="utf-8").splitlines()
    assert "arg=-y" in captured
    assert "arg=mcp-adr-analysis-server" in captured
    assert "arg=--stdio" not in captured
    assert f"execution_mode={execution_mode or 'prompt-only'}" in captured
    assert "ignore_scripts=true" in captured
    assert any(
        line.startswith("project_path=") and line != "project_path="
        for line in captured
    )
    assert any(
        line.startswith("adr_path=") and "docs\\02-architecture\\decisions" in line
        for line in captured
    )


@BASH_MARK
@pytest.mark.parametrize("api_key", [None, EXAMPLE_CONTEXT7_KEY])
def test_bash_context7_uses_env_auth_without_argv(
    tmp_path: Path,
    api_key: str | None,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_npx = fake_bin / "npx"
    capture_file = tmp_path / "context7-args.txt"
    _write_bash_launcher(fake_npx)
    env = _clean_env(
        PATH=f"{fake_bin}:/usr/bin:/bin",
        CONTEXT7_API_KEY=api_key,
        NPM_CONFIG_CACHE=str(tmp_path / "npm-cache"),
        BIOETL_TEST_CAPTURE=str(capture_file),
    )

    result = _run_bash(shlex.quote(str(CONTEXT7_SH)), env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    captured = capture_file.read_text(encoding="utf-8")
    assert f"arg={CONTEXT7_PACKAGE}" in captured
    assert "arg=--api-key" not in captured
    assert EXAMPLE_CONTEXT7_KEY not in captured
    assert f"context7_key_present={'yes' if api_key else 'no'}" in captured
    if api_key is None:
        assert "CONTEXT7_API_KEY is not set" in result.stderr
    else:
        assert result.stderr == ""


@POWERSHELL_MARK
@pytest.mark.parametrize("api_key", [None, EXAMPLE_CONTEXT7_KEY])
def test_powershell_context7_uses_env_auth_without_argv(
    windows_fixture_dir: Path,
    api_key: str | None,
) -> None:
    fake_npx = windows_fixture_dir / "npx.ps1"
    capture_file = windows_fixture_dir / "context7-args.txt"
    _write_windows_launcher(fake_npx)
    env = _windows_wrapper_env(
        windows_fixture_dir,
        capture_file,
        CONTEXT7_API_KEY=api_key,
    )

    result = _run_powershell_file(CONTEXT7_PS1, env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    captured = capture_file.read_text(encoding="utf-8")
    assert f"arg={CONTEXT7_PACKAGE}" in captured
    assert "arg=--api-key" not in captured
    assert EXAMPLE_CONTEXT7_KEY not in captured
    assert f"context7_key_present={'yes' if api_key else 'no'}" in captured
    if api_key is None:
        assert "CONTEXT7_API_KEY is not set" in result.stderr
    else:
        assert result.stderr == ""


def test_context7_wrappers_pin_package_and_never_include_api_key_argv() -> None:
    for wrapper in (CONTEXT7_SH, CONTEXT7_PS1):
        source = wrapper.read_text(encoding="utf-8")
        assert CONTEXT7_PACKAGE in source
        assert "@latest" not in source
        assert "--api-key" not in source
