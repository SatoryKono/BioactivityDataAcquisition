# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Behavioral contracts for cross-platform MCP support and wrapper scripts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
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
AST_GREP_SH = MCP_DIR / "mcp_ast_grep_wrapper.sh"
MCP_GOVERNANCE = ROOT / "docs" / "00-project" / "ai" / "mcp-governance.md"


def _resolve_powershell() -> str | None:
    """Prefer real PowerShell executables over broken ``pwsh.bat`` shims."""
    for candidate in (
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
    ):
        if candidate and not candidate.lower().endswith((".bat", ".cmd")):
            return candidate
    return None


POWERSHELL = _resolve_powershell()
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


def _skip_if_wsl_service_is_unavailable(
    result: subprocess.CompletedProcess[str],
) -> None:
    """Skip Windows-only probes when WSL fails before Bash can start."""
    # A process launched inside WSL returns a POSIX status in the 0..255 range.
    # Windows reports a launcher/service failure as signed or unsigned DWORD -1;
    # its localized UTF-16 diagnostic is not stable enough to match reliably.
    if result.returncode in {-1, 4294967295}:
        pytest.skip("WSL service is unavailable before the Bash probe can start")


def _run_bash(
    script: str, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    run_env = env or _clean_env()
    # On Windows the default ``bash`` is often WSL. Write the probe to a file so
    # ``$`` / ``$?`` expansions are not mangled by interop layers, and use
    # ``env -i`` so host/WSL PATH/HOME installs cannot leak into uvx contracts.
    if os.name == "nt" and shutil.which("wsl") is not None:
        import tempfile

        fd, raw_script_path = tempfile.mkstemp(prefix="bioetl-bash-", suffix=".sh")
        os.close(fd)
        script_path = Path(raw_script_path)
        normalized = (
            "#!/usr/bin/env bash\n"
            "set +e\n" + script.replace("\r\n", "\n").replace("\r", "\n") + "\n"
        )
        script_path.write_bytes(normalized.encode("utf-8"))
        try:
            subprocess.run(
                ["wsl", "chmod", "+x", _bash_path(script_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            # Always keep a minimal POSIX PATH so ``env -i`` can still find bash
            # utilities even when a test injects a Windows-only PATH value.
            raw_path = run_env.get("PATH", "/usr/bin:/bin")
            # Windows PATH uses ';' while POSIX PATH uses ':'. Never split on
            # ':' first — that corrupts drive letters like ``E:\...``.
            if ";" in raw_path or "\\" in raw_path:
                separators = [part for part in raw_path.split(";") if part]
            else:
                separators = [part for part in raw_path.split(":") if part]
            path_parts: list[str] = []
            for part in separators:
                is_windows_path = "\\" in part or (
                    len(part) >= 2 and part[1] == ":" and part[0].isalpha()
                )
                if is_windows_path:
                    try:
                        path_parts.append(_bash_path(Path(part)))
                    except OSError:
                        continue
                else:
                    path_parts.append(part)
            if "/usr/bin" not in path_parts:
                path_parts.extend(["/usr/bin", "/bin"])
            path_value = ":".join(path_parts)
            allow_keys = {
                "PATH",
                "HOME",
                "LOCALAPPDATA",
                "BIOETL_REPO_ENV_LOADED",
                "BIOETL_ENV_FILE",
                "BIOETL_UVX_DIRECT_NETWORK",
                "BIOETL_TEST_CAPTURE",
                "BIOETL_TEST_EXIT_CODE",
                "BIOETL_TEST_PYTHON_PROBE",
                "BIOETL_MCP_VALIDATE_ONLY",
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "ALL_PROXY",
                "NO_PROXY",
                "http_proxy",
                "https_proxy",
                "all_proxy",
                "no_proxy",
                "KEEP_ME",
                "XDG_DATA_HOME",
                "NEO4J_URI",
                "NEO4J_USERNAME",
                "NEO4J_PASSWORD",
                "NEO4J_DATABASE",
                "NEO4J_AUTH",
                "CONTEXT7_API_KEY",
                "CONTEXT7_API_TOKEN",
                "UPSTASH_CONTEXT7_API_KEY",
                "EXECUTION_MODE",
                "ADR_PATH",
            }
            assignments = [f"PATH={path_value}"]
            for key in sorted(allow_keys - {"PATH"}):
                if key not in run_env:
                    continue
                value = run_env[key]
                # Skip Windows drive paths that are invalid inside WSL except PATH.
                if "\\" in value or (len(value) >= 2 and value[1] == ":"):
                    try:
                        value = _bash_path(Path(value))
                    except OSError:
                        continue
                assignments.append(f"{key}={value}")
            command = [
                "wsl",
                "env",
                "-i",
                *assignments,
                "/bin/bash",
                "--noprofile",
                "--norc",
                _bash_path(script_path),
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            _skip_if_wsl_service_is_unavailable(result)
            return result
        finally:
            script_path.unlink(missing_ok=True)
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", script],
        cwd=ROOT,
        env=run_env,
        text=True,
        capture_output=True,
        check=False,
    )


def _bash_path(path: Path) -> str:
    """Return a path form that the selected bash runtime can open.

    On Windows the active ``bash`` is often WSL, which expects ``/mnt/<drive>/...``
    rather than raw ``E:\\...`` or Git-Bash ``/e/...`` forms.
    """
    resolved = path.resolve()
    if os.name != "nt":
        return str(resolved)
    try:
        result = subprocess.run(
            ["wslpath", "-u", str(resolved)],
            text=True,
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        posix = resolved.as_posix()
        if len(posix) >= 2 and posix[1] == ":":
            return f"/mnt/{posix[0].lower()}{posix[2:]}"
        return posix
    return result.stdout.strip()


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


def _powershell_python_path() -> str:
    """Return a Python executable usable by the selected PowerShell runtime."""
    if os.name == "nt" or not str(POWERSHELL).lower().endswith(".exe"):
        return _powershell_path(Path(sys.executable))

    windows_python = ROOT / ".venv-win" / "Scripts" / "python.exe"
    if not windows_python.is_file():
        pytest.skip("Windows Python is required for the scoped uvx contract on WSL")
    return _powershell_path(windows_python)


def _run_powershell_command(
    command: str, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL is not None
    try:
        result = subprocess.run(
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
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.skip(f"PowerShell command timed out in this environment: {exc}")
    if any(
        marker in result.stderr
        for marker in ("UtilBindVsockAnyPort", "UtilAcceptVsock")
    ):
        pytest.skip("Windows PowerShell interop is unavailable in this WSL session")
    return result


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
    try:
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
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.skip(
            f"PowerShell wrapper execution timed out in this environment: {exc}"
        )
    if any(
        marker in result.stderr
        for marker in ("UtilBindVsockAnyPort", "UtilAcceptVsock")
    ):
        pytest.skip("Windows PowerShell interop is unavailable in this WSL session")
    return result


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
    content = """#!/usr/bin/env bash
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
"""
    # Always write LF endings so WSL shebang execution works from /mnt/e.
    path.write_bytes(content.replace("\r\n", "\n").encode("utf-8"))
    path.chmod(0o755)
    if os.name == "nt" and shutil.which("wsl") is not None:
        # DrvFs often ignores POSIX mode bits unless chmod is applied from WSL.
        subprocess.run(
            ["wsl", "chmod", "+x", _bash_path(path)],
            check=False,
            capture_output=True,
            text=True,
        )


def _bash_lf_script(path: Path) -> str:
    """Return a WSL path to an LF-normalized copy of ``path`` when needed."""
    if os.name != "nt" or shutil.which("wsl") is None:
        return _bash_path(path)
    raw = path.read_bytes()
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if normalized == raw:
        return _bash_path(path)
    fd, tmp_name = tempfile.mkstemp(prefix="bioetl-lf-", suffix=path.suffix or ".sh")
    os.close(fd)
    tmp_path = Path(tmp_name)
    tmp_path.write_bytes(normalized)
    subprocess.run(
        ["wsl", "chmod", "+x", _bash_path(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    return _bash_path(tmp_path)


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
    # Linux pwsh only discovers PATH scripts when the executable bit is set.
    try:
        path.chmod(path.stat().st_mode | 0o755)
    except OSError:
        pass


def _powershell_path_separator() -> str:
    """Return PATH separator matching the selected PowerShell runtime."""
    if os.name == "nt":
        return ";"
    # Windows PowerShell interop from WSL still expects ';' separators.
    if POWERSHELL is not None and str(POWERSHELL).lower().endswith(".exe"):
        return ";"
    return ":"


def _windows_wrapper_env(
    fixture_dir: Path,
    capture_file: Path,
    **updates: str | None,
) -> dict[str, str]:
    windows_dir = _powershell_path(fixture_dir)
    sep = _powershell_path_separator()
    if sep == ";":
        path_value = f"{windows_dir};C:\\Windows\\System32;C:\\Windows"
        join = "\\"
    else:
        # Linux CI runs pwsh with POSIX PATH semantics; keep fakes discoverable.
        path_value = f"{windows_dir}:/usr/bin:/bin"
        join = "/"
    env = _clean_env(
        PATH=path_value,
        USERPROFILE=windows_dir,
        UV_CACHE_DIR=f"{windows_dir}{join}uv-cache",
        UV_TOOL_DIR=f"{windows_dir}{join}uv-tools",
        DENO_DIR=f"{windows_dir}{join}deno-cache",
        NPM_CONFIG_CACHE=f"{windows_dir}{join}npm-cache",
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
    env = _clean_env(PATH=f"{_bash_path(fake_bin)}:/usr/bin:/bin")

    result = _run_bash(
        f"source {shlex.quote(_bash_path(UV_RESOLVER_SH))}; bioetl_resolve_uvx_bin",
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == _bash_path(fake_uvx)


@BASH_MARK
def test_bash_uv_resolver_finds_uv_sibling(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_uv = fake_bin / "uv"
    fake_uvx = fake_bin / "uvx"
    _write_bash_launcher(fake_uv)
    _write_bash_launcher(fake_uvx)
    # Put only a ``uv`` wrapper on PATH; keep ``uvx`` as a true sibling of the
    # resolved uv binary so the dirname(...)/uvx branch is exercised without
    # overriding the special ``command`` builtin.
    path_bin = tmp_path / "path-bin"
    path_bin.mkdir()
    uv_wrapper = path_bin / "uv"
    uv_wrapper.write_text(
        f'#!/usr/bin/env bash\nexec {shlex.quote(_bash_path(fake_uv))} "$@"\n',
        encoding="utf-8",
    )
    uv_wrapper.chmod(0o755)
    if os.name == "nt" and shutil.which("wsl") is not None:
        subprocess.run(
            [
                "wsl",
                "chmod",
                "+x",
                _bash_path(uv_wrapper),
                _bash_path(fake_uv),
                _bash_path(fake_uvx),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    # PATH must resolve ``uv`` through the wrapper, but sibling detection uses
    # the real ``uv`` path printed by a tiny probe below.
    env = _clean_env(PATH=f"{_bash_path(path_bin)}:/usr/bin:/bin")
    script = (
        f"source {shlex.quote(_bash_path(UV_RESOLVER_SH))}; "
        # Force sibling path: pretend command -v uv returns the real uv path
        # while uvx is not on PATH.
        f"command() {{ "
        f'if [ "$1" = "-v" ] && [ "$2" = "uvx" ]; then return 1; fi; '
        f'if [ "$1" = "-v" ] && [ "$2" = "uv" ]; then '
        f"printf '%s\\n' {shlex.quote(_bash_path(fake_uv))}; return 0; fi; "
        f"return 1; }}; "
        f"enable -n command 2>/dev/null || true; "
        "bioetl_resolve_uvx_bin"
    )

    result = _run_bash(script, env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == _bash_path(fake_uvx)


@BASH_MARK
def test_bash_uv_resolver_uses_home_fallback(tmp_path: Path) -> None:
    fake_uvx = tmp_path / ".local" / "bin" / "uvx"
    fake_uvx.parent.mkdir(parents=True)
    _write_bash_launcher(fake_uvx)
    env = _clean_env(
        PATH="/usr/bin:/bin",
        HOME=_bash_path(tmp_path),
        LOCALAPPDATA="",
    )

    result = _run_bash(
        f"source {shlex.quote(_bash_path(UV_RESOLVER_SH))}; bioetl_resolve_uvx_bin",
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == _bash_path(fake_uvx)


@BASH_MARK
def test_bash_uv_resolver_reports_unavailable(tmp_path: Path) -> None:
    env = _clean_env(
        PATH="/usr/bin:/bin",
        HOME=_bash_path(tmp_path),
        LOCALAPPDATA=None,
    )
    # Keep the probe on one line so Windows/WSL argument marshalling cannot
    # mangle multi-line $? / $() expansions.
    script = (
        f"source {shlex.quote(_bash_path(UV_RESOLVER_SH))}; "
        "out=$(bioetl_resolve_uvx_bin); code=$?; "
        'printf \'%s\\n%s\\n\' "$out" "$code"'
    )

    result = _run_bash(script, env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["uvx", "1"]


@BASH_MARK
def test_bash_uv_resolver_handles_unset_home() -> None:
    # Isolate from the host/WSL home uvx install when HOME is unset.
    env = _clean_env(
        PATH="/usr/bin:/bin",
        HOME=None,
        LOCALAPPDATA=None,
        XDG_DATA_HOME="/tmp/bioetl-no-xdg",
    )

    result = _run_bash(
        f"source {shlex.quote(_bash_path(UV_RESOLVER_SH))}; bioetl_resolve_uvx_bin",
        env=env,
    )

    assert result.returncode == 1
    assert result.stdout == "uvx\n"


@BASH_MARK
def test_bash_uv_network_bypass_requires_explicit_opt_in() -> None:
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
source {shlex.quote(_bash_path(UV_RESOLVER_SH))}
bioetl_enable_uvx_network_bypass
printf '%s\n' "${{HTTP_PROXY}}" "${{https_proxy}}"
export BIOETL_UVX_DIRECT_NETWORK=1
bioetl_enable_uvx_network_bypass
printf '%s\n' "$NO_PROXY" "$no_proxy" "${{HTTP_PROXY-unset}}" \
  "${{https_proxy-unset}}" "$KEEP_ME"
"""

    result = _run_bash(script, env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "http://proxy.invalid",
        "http://proxy.invalid",
        "*",
        "*",
        "unset",
        "unset",
        "preserved",
    ]


@POWERSHELL_MARK
@pytest.mark.parametrize(
    ("mock_functions", "expected"),
    [
        (
            # PATH probes run first; Test-Path must not be always-true or the first
            # PATH entry wins. Only accept the Get-Command Source candidate.
            "function Get-Command { param($Name, $ErrorAction) "
            "if ($Name -eq 'uvx') { [pscustomobject]@{Source='C:\\fake\\uvx.exe'} } }\n"
            "function Test-Path { param($LiteralPath, $Path, $ErrorAction) "
            "$LiteralPath -eq 'C:\\fake\\uvx.exe' }\n"
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
        (
            "function Get-Command { param($Name, $ErrorAction) $null }\n"
            "function Test-Path { param($LiteralPath, $Path, $ErrorAction) "
            "$LiteralPath -like '*Python312*uvx.exe' }\n"
            "function Resolve-Path { param($LiteralPath) "
            "[pscustomobject]@{Path=$LiteralPath} }",
            "Python312\\Scripts\\uvx.exe",
        ),
        (
            "function Get-Command { param($Name, $ErrorAction) $null }\n"
            "function Test-Path { param($LiteralPath, $Path, $ErrorAction) "
            "$LiteralPath -like '*Python311*uvx.exe' }\n"
            "function Resolve-Path { param($LiteralPath) "
            "[pscustomobject]@{Path=$LiteralPath} }",
            "Python311\\Scripts\\uvx.exe",
        ),
        (
            "function Get-Command { param($Name, $ErrorAction) $null }\n"
            "function Test-Path { param($LiteralPath, $Path, $ErrorAction) "
            "$LiteralPath -like '*.local*bin*uvx.exe' }\n"
            "function Resolve-Path { param($LiteralPath) "
            "[pscustomobject]@{Path=$LiteralPath} }",
            ".local\\bin\\uvx.exe",
        ),
        (
            "function Get-Command { param($Name, $ErrorAction) $null }\n"
            "function Test-Path { param($LiteralPath, $Path, $ErrorAction) "
            "$LiteralPath -like '*.cargo*bin*uvx.exe' }\n"
            "function Resolve-Path { param($LiteralPath) "
            "[pscustomobject]@{Path=$LiteralPath} }",
            ".cargo\\bin\\uvx.exe",
        ),
    ],
)
def test_powershell_uv_resolver_candidate_paths(
    mock_functions: str, expected: str
) -> None:
    if sys.platform != "win32":
        pytest.skip(
            "Windows-path uvx candidate contracts require Windows PowerShell path semantics"
        )
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
def test_powershell_uv_network_bypass_requires_explicit_opt_in() -> None:
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
$preservedHttpProxy=$env:HTTP_PROXY
$env:BIOETL_UVX_DIRECT_NETWORK='1'
Enable-BioetlUvxNetworkBypass
[ordered]@{{
  preserved_http_proxy=$preservedHttpProxy
  no_proxy_value=$env:NO_PROXY
  http_proxy_value=[Environment]::GetEnvironmentVariable('HTTP_PROXY')
  https_proxy_value=[Environment]::GetEnvironmentVariable('https_proxy')
  keep_value=$env:KEEP_ME
}} | ConvertTo-Json -Compress
"""

    result = _run_powershell_command(command)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "preserved_http_proxy": "http://proxy.invalid",
        "no_proxy_value": "*",
        "http_proxy_value": None,
        "https_proxy_value": None,
        "keep_value": "preserved",
    }


@POWERSHELL_MARK
def test_powershell_uv_network_bypass_is_scoped_to_package_resolution(
    windows_fixture_dir: Path,
) -> None:
    fake_uvx = windows_fixture_dir / "uvx.ps1"
    resolution_capture = windows_fixture_dir / "resolution-env.json"
    server_capture = windows_fixture_dir / "server-env.json"
    fake_uvx.write_text(
        """[ordered]@{
    https_proxy=$env:HTTPS_PROXY
    no_proxy=$env:NO_PROXY
    arguments=@($args)
} | ConvertTo-Json -Compress | Set-Content -LiteralPath $env:BIOETL_RESOLUTION_CAPTURE
$pythonIndex = [Array]::IndexOf($args, 'python')
$trampoline = $args[$pythonIndex + 2]
$command = $args[$pythonIndex + 3]
$commandArguments = @($args[($pythonIndex + 4)..($args.Count - 1)])
& $env:BIOETL_TEST_PYTHON -c $trampoline $command @commandArguments
exit $LASTEXITCODE
""",
        encoding="utf-8",
        newline="",
    )
    server_script = (
        "import json, os, pathlib, sys; "
        "pathlib.Path(sys.argv[1]).write_text(json.dumps({"
        "'https_proxy': os.environ.get('HTTPS_PROXY'), "
        "'no_proxy': os.environ.get('NO_PROXY')}), encoding='utf-8')"
    )
    helper = _ps_quote(_powershell_path(UV_RESOLVER_PS1))
    command = f"""
. {helper}
$env:HTTPS_PROXY='http://proxy.invalid'
$env:NO_PROXY='localhost'
$env:BIOETL_UVX_DIRECT_NETWORK='1'
$env:BIOETL_RESOLUTION_CAPTURE={_ps_quote(_powershell_path(resolution_capture))}
$env:BIOETL_TEST_PYTHON={_ps_quote(_powershell_python_path())}
Invoke-BioetlUvxWithScopedBypass `
  -UvxPath {_ps_quote(_powershell_path(fake_uvx))} `
  -Package 'example-package==1.0' `
  -Command {_ps_quote(_powershell_python_path())} `
  -CommandArguments @('-c', {_ps_quote(server_script)}, {_ps_quote(_powershell_path(server_capture))})
[ordered]@{{
  https_proxy=$env:HTTPS_PROXY
  no_proxy=$env:NO_PROXY
}} | ConvertTo-Json -Compress
"""

    result = _run_powershell_command(command)

    assert result.returncode == 0, result.stderr
    resolution = json.loads(resolution_capture.read_text(encoding="utf-8"))
    assert resolution["https_proxy"] is None
    assert resolution["no_proxy"] == "*"
    assert resolution["arguments"][:3] == [
        "--from",
        "example-package==1.0",
        "python",
    ]
    expected_original = {
        "https_proxy": "http://proxy.invalid",
        "no_proxy": "localhost",
    }
    assert result.stderr == ""
    assert server_capture.is_file(), (result.stdout, result.stderr, resolution)
    assert json.loads(server_capture.read_text(encoding="utf-8")) == expected_original
    assert json.loads(result.stdout) == expected_original


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

    result = _run_bash(f"bash {shlex.quote(_bash_lf_script(FETCH_SH))}", env=env)

    assert result.returncode == 17
    assert result.stdout == ""
    captured = capture_file.read_text(encoding="utf-8").splitlines()
    # WSL may report the launcher path in /mnt/<drive>/... form.
    assert captured[0] in {
        f"executable={fake_uvx}",
        f"executable={_bash_path(fake_uvx)}",
        f"executable={fake_uvx.as_posix()}",
    }
    assert captured[1:7] == [
        "arg=--python",
        "arg=3.13",
        "arg=--with",
        "arg=mcp<2",
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
    assert "arg=--with" in captured
    assert "arg=mcp<2" in captured
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
        "mcp<2",
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
@pytest.mark.parametrize("explicit_credentials", [False, True])
@pytest.mark.parametrize(
    "neo4j_auth", ["example-user", "/example-pass", "example-user/"]
)
def test_neo4j_wrapper_rejects_malformed_combined_auth(
    neo4j_auth: str,
    explicit_credentials: bool,
) -> None:
    env = _clean_env(
        NEO4J_AUTH=neo4j_auth,
        NEO4J_USERNAME="explicit-user" if explicit_credentials else None,
        NEO4J_PASSWORD="explicit-password" if explicit_credentials else None,
        BIOETL_MCP_VALIDATE_ONLY="1",
    )

    result = _run_bash(f"bash {shlex.quote(_bash_lf_script(NEO4J_CYPHER_SH))}", env=env)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "NEO4J_AUTH must use non-empty username/password format" in result.stderr
    assert neo4j_auth not in result.stderr


@BASH_MARK
def test_neo4j_wrapper_rejects_malformed_auth_loaded_from_repo_env(
    tmp_path: Path,
) -> None:
    env_fixture = tmp_path / "mcp-auth-fixture.txt"
    env_fixture.write_text("NEO4J_AUTH=loaded-without-delimiter\n", encoding="utf-8")
    env = _clean_env(
        BIOETL_REPO_ENV_LOADED=None,
        BIOETL_ENV_FILE=str(env_fixture),
        BIOETL_MCP_VALIDATE_ONLY="1",
    )

    result = _run_bash(f"bash {shlex.quote(_bash_lf_script(NEO4J_CYPHER_SH))}", env=env)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "NEO4J_AUTH must use non-empty username/password format" in result.stderr
    assert "loaded-without-delimiter" not in result.stderr


@BASH_MARK
@pytest.mark.parametrize(
    "neo4j_auth", ["example-user/example-pass", "example-user/example/pass"]
)
def test_neo4j_wrapper_accepts_valid_combined_auth(neo4j_auth: str) -> None:
    env = _clean_env(
        NEO4J_AUTH=neo4j_auth,
        BIOETL_MCP_VALIDATE_ONLY="1",
    )

    result = _run_bash(f"bash {shlex.quote(_bash_lf_script(NEO4J_CYPHER_SH))}", env=env)

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

    result = _run_bash(
        f"bash {shlex.quote(_bash_lf_script(NEO4J_CYPHER_SH))} --example", env=env
    )

    assert result.returncode == 0, result.stderr
    captured = capture_file.read_text(encoding="utf-8")
    assert "neo4j_username=explicit-user" in captured
    assert "neo4j_password=explicit-password" in captured
    assert "packed-password" not in captured
    assert "arg=@alanse/mcp-neo4j-server@0.2.0" in captured
    assert "arg=--example" in captured


def test_neo4j_wrappers_pin_server_and_forward_arguments() -> None:
    shell_source = NEO4J_CYPHER_SH.read_text(encoding="utf-8")
    powershell_source = (MCP_DIR / "mcp_neo4j_cypher_wrapper.ps1").read_text(
        encoding="utf-8"
    )

    assert '"@alanse/mcp-neo4j-server@0.2.0" "$@"' in shell_source
    assert '"@alanse/mcp-neo4j-server@0.2.0" @args' in powershell_source


def test_mutmut_git_dependency_is_pinned_consistently() -> None:
    pattern = re.compile(r"git\+https://github\.com/wdm0006/mutmut-mcp@([0-9a-f]{40})")
    commits = []
    for wrapper in (MUTMUT_SH, MUTMUT_PS1):
        match = pattern.search(wrapper.read_text(encoding="utf-8"))
        assert match is not None, f"missing immutable pin in {wrapper}"
        commits.append(match.group(1))

    assert commits == [MUTMUT_COMMIT, MUTMUT_COMMIT]
    governance = MCP_GOVERNANCE.read_text(encoding="utf-8")
    assert MUTMUT_COMMIT in governance
    assert "Immutable pin обновляется только отдельным reviewed change" in governance


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
    assert "arg=mcp-adr-analysis-server@2.6.14" in captured
    assert "arg=--stdio" not in captured
    assert f"execution_mode={execution_mode or 'prompt-only'}" in captured
    assert "ignore_scripts=true" in captured
    assert any(
        line.startswith("project_path=") and line != "project_path="
        for line in captured
    )
    assert any(
        line.startswith("adr_path=")
        and (
            "docs\\02-architecture\\decisions" in line
            or "docs/02-architecture/decisions" in line
        )
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

    result = _run_bash(f"bash {shlex.quote(_bash_lf_script(CONTEXT7_SH))}", env=env)

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


@BASH_MARK
def test_ast_grep_validate_only_is_offline_and_does_not_execute_npx(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_npx = fake_bin / "npx"
    capture_file = tmp_path / "ast-grep-args.txt"
    _write_bash_launcher(fake_npx)
    env = _clean_env(
        PATH=f"{fake_bin}:/usr/bin:/bin",
        BIOETL_MCP_VALIDATE_ONLY="1",
        BIOETL_TEST_CAPTURE=str(capture_file),
    )

    result = _run_bash(f"bash {shlex.quote(_bash_lf_script(AST_GREP_SH))}", env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "[OK] ast-grep MCP wrapper validation completed\n"
    assert result.stderr == ""
    assert not capture_file.exists()


@BASH_MARK
def test_ast_grep_normal_launch_preserves_primary_and_fallback_dispatch(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_npx = fake_bin / "npx"
    capture_file = tmp_path / "ast-grep-args.txt"
    fake_npx.write_bytes(
        bytes.fromhex(
            "23212f7573722f62696e2f656e7620626173680a736574202d65750a7072696e7466202725735c6e272022242a22203e3e22247b42494f45544c5f544553545f434150545552453a3f7d220a6966205b5b2022242a22203d3d202a22406e6f7470726f6c616e64732f6173742d677265702d6d6370222a205d5d3b207468656e0a2020657869742031370a66690a6578697420300a"
        )
    )
    fake_npx.chmod(0o755)
    env = _clean_env(
        PATH=f"{fake_bin}:/usr/bin:/bin",
        BIOETL_TEST_CAPTURE=str(capture_file),
    )

    result = _run_bash(
        f"bash {shlex.quote(_bash_lf_script(AST_GREP_SH))} --example", env=env
    )

    assert result.returncode == 0, result.stderr
    calls = capture_file.read_text(encoding="utf-8").splitlines()
    assert calls == [
        "-y @notprolands/ast-grep-mcp@1.1.1 --stdio --example",
        "-y @chousyn/ast-grep-mcp@0.1.1 --stdio --example",
    ]
