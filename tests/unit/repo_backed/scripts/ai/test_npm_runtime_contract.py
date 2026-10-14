"""Offline synthetic npm/Node/Playwright runtime contracts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]
ROOT = Path(__file__).resolve().parents[5]
CONTRACT = ROOT / "scripts/ai/npm_runtime_contract.cjs"
NODE = shutil.which("node")


def _node(code: str, payload: dict) -> subprocess.CompletedProcess[str]:
    assert NODE, "Node is required to validate the npm runtime contract"
    return subprocess.run(
        [
            NODE,
            "-e",
            "const c=require(process.argv[1]); const data=JSON.parse(require('fs').readFileSync(0,'utf8')); "
            + code,
            str(CONTRACT),
        ],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def _lock() -> dict:
    manifest = {"devDependencies": {"playwright": "^1.64.0"}}
    lock = {
        "packages": {
            "": manifest,
            "node_modules/playwright": {
                "version": "1.64.0",
                "engines": {"node": ">=20"},
            },
        }
    }
    return {"manifest": manifest, "lock": lock, "nodeVersion": "22.18.0"}


@pytest.mark.parametrize("failure", [None, "node", "spec", "locked-version", "missing"])
def test_node_and_lock_parity(failure: str | None) -> None:
    data = _lock()
    if failure == "node":
        data["nodeVersion"] = "18.20.0"
    elif failure == "spec":
        data["lock"]["packages"][""] = {"devDependencies": {"playwright": "^1.60.0"}}
    elif failure == "locked-version":
        data["lock"]["packages"]["node_modules/playwright"]["version"] = "1.60.0"
    elif failure == "missing":
        del data["lock"]["packages"]["node_modules/playwright"]
    result = _node("c.validateLock(data.manifest, data.lock, data.nodeVersion);", data)
    assert (result.returncode == 0) == (failure is None), result.stderr


@pytest.mark.parametrize("failure", [None, "package", "core", "browser", "missing"])
def test_actual_browser_contract(failure: str | None) -> None:
    data = {
        "expectedVersion": "1.64.0",
        "installedVersion": "1.64.0",
        "coreVersion": "1.64.0",
        "expectedBrowserVersion": "145.0.1",
        "browserVersion": "145.0.1",
        "executableExists": True,
    }
    if failure == "package":
        data["installedVersion"] = "1.60.0"
    elif failure == "core":
        data["coreVersion"] = "1.60.0"
    elif failure == "browser":
        data["browserVersion"] = "140.0.1"
    elif failure == "missing":
        data["executableExists"] = False
    result = _node("c.validateBrowser(data);", data)
    assert (result.returncode == 0) == (failure is None), result.stderr


def test_current_root_lock_satisfies_manifest_and_engines() -> None:
    data = {
        "manifest": json.loads((ROOT / "package.json").read_text(encoding="utf-8")),
        "lock": json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8")),
        "nodeVersion": "22.18.0",
    }
    result = _node("c.validateLock(data.manifest, data.lock, data.nodeVersion);", data)
    assert result.returncode == 0, result.stderr
    data["nodeVersion"] = "22.11.0"
    rejected = _node(
        "c.validateLock(data.manifest, data.lock, data.nodeVersion);", data
    )
    assert rejected.returncode != 0
    assert ">=22.12.0" in rejected.stderr


def test_filesystem_runtime_and_diagnostic_pins_match_lock() -> None:
    lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    version = lock["packages"]["node_modules/@modelcontextprotocol/server-filesystem"][
        "version"
    ]
    for name in ("mcp_filesystem_wrapper.sh", "mcp_filesystem_wrapper.ps1", "check.sh"):
        source = (ROOT / "scripts/ai/mcp" / name).read_text(encoding="utf-8")
        assert f"@modelcontextprotocol/server-filesystem@{version}" in source
        assert "2026.1.14" not in source


def test_both_setup_platforms_enforce_preinstall_contract() -> None:
    for suffix in ("sh", "ps1"):
        source = (
            ROOT
            / f"scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.{suffix}"
        ).read_text(encoding="utf-8")
        assert "npm_runtime_contract.cjs" in source
    source = (
        ROOT / "scripts/ops/observability/grafana/capture_grafana_screenshots_docker.sh"
    ).read_text(encoding="utf-8")
    assert (
        'BROWSER_CACHE="bioetl-playwright-${PLAYWRIGHT_VERSION}-${IMAGE_DIGEST:0:16}"'
        in source
    )
    assert "if [[ ! -d" not in source
    assert (
        source.index("playwright install chromium")
        < source.index("--browser /tmp/node_modules")
        < source.index("node /work/capture.js")
    )
    assert "PLAYWRIGHT_BROWSERS_PATH=/bioetl-browsers" in source


@pytest.mark.parametrize("browser_version", ["145.0.1", "140.0.1"])
def test_container_preflight_on_synthetic_installed_runtime(
    tmp_path: Path, browser_version: str
) -> None:
    """Exercise the actual async entry point without Docker/Grafana or browsers."""
    data = _lock()
    for name in ("manifest", "lock"):
        filename = "package.json" if name == "manifest" else "package-lock.json"
        (tmp_path / filename).write_text(json.dumps(data[name]), encoding="utf-8")
    modules = tmp_path / "node_modules"
    playwright = modules / "playwright"
    core = modules / "playwright-core"
    playwright.mkdir(parents=True)
    core.mkdir()
    (playwright / "package.json").write_text(
        json.dumps({"version": "1.64.0", "main": "index.js"}), encoding="utf-8"
    )
    (core / "package.json").write_text(
        json.dumps({"version": "1.64.0"}), encoding="utf-8"
    )
    (core / "browsers.json").write_text(
        json.dumps({"browsers": [{"name": "chromium", "browserVersion": "145.0.1"}]}),
        encoding="utf-8",
    )
    executable = tmp_path / "synthetic-chromium"
    executable.touch()
    (playwright / "index.js").write_text(
        "module.exports={chromium:{executablePath:()=>"
        + json.dumps(str(executable))
        + ",launch:async()=>({version:()=>"
        + json.dumps(browser_version)
        + ",close:async()=>{}})}};",
        encoding="utf-8",
    )
    result = subprocess.run(
        [NODE, str(CONTRACT), str(tmp_path), "--browser", str(modules)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) == (browser_version == "145.0.1"), result.stderr
    if browser_version != "145.0.1":
        assert "Chromium version mismatch" in result.stderr


def test_powershell_filesystem_executes_locked_pin() -> None:
    powershell = (
        shutil.which("pwsh")
        or shutil.which("pwsh.exe")
        or shutil.which("powershell.exe")
    )
    if not powershell and os.name != "nt":
        pytest.skip(
            "PowerShell is optional on non-Windows; actual Windows launch has separate evidence"
        )
    assert powershell, "PowerShell is required for the actual Windows launch contract"
    script = ROOT / "scripts/ai/mcp/mcp_filesystem_wrapper.ps1"
    code = (
        "function global:npx { $args -join '|'; $global:LASTEXITCODE=0 }; $global:LASTEXITCODE=0; & '"
        + str(script).replace("'", "''")
        + "'"
    )
    result = subprocess.run(
        [powershell, "-NoProfile", "-Command", code],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "@modelcontextprotocol/server-filesystem@2026.8.31" in result.stdout


def test_shell_filesystem_executes_locked_pin(tmp_path: Path) -> None:
    git = shutil.which("git")
    assert git
    bash = (
        str(Path(git).parents[1] / "bin/bash.exe")
        if os.name == "nt"
        else shutil.which("bash")
    )
    assert bash
    npx = tmp_path / "npx"
    npx.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@"\n', encoding="utf-8")
    npx.chmod(0o755)
    fake_bin = str(tmp_path)
    if os.name == "nt":
        fake_bin = "/" + tmp_path.drive[0].lower() + tmp_path.as_posix()[2:]
    script = ROOT / "scripts/ai/mcp/mcp_filesystem_wrapper.sh"
    result = subprocess.run(
        [
            bash,
            "-c",
            'export PATH="$1:$PATH"; exec bash "$2"',
            "fixture",
            fake_bin,
            str(script),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "@modelcontextprotocol/server-filesystem@2026.8.31" in result.stdout


def test_root_npm_lock_graph_clean_install_parity(tmp_path: Path) -> None:
    """Use npm's resolver as well as direct dependency/engine assertions."""
    npm = shutil.which("npm.cmd") if os.name == "nt" else shutil.which("npm")
    assert npm, "npm is required for the root dependency contract"
    for name in ("package.json", "package-lock.json"):
        shutil.copyfile(ROOT / name, tmp_path / name)
    result = subprocess.run(
        [npm, "ci", "--ignore-scripts", "--dry-run", "--no-audit", "--no-fund"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("preflight_success", [True, False])
def test_docker_capture_preflight_does_not_require_host_node(
    tmp_path: Path, preflight_success: bool
) -> None:
    """Docker-only hosts validate in the image; failures never reach capture."""
    git = shutil.which("git")
    assert git
    bash = (
        str(Path(git).parents[1] / "bin/bash.exe")
        if os.name == "nt"
        else shutil.which("bash")
    )
    assert bash
    docker = tmp_path / "docker"
    docker.write_text(
        '#!/usr/bin/env bash\nprintf "call\\n" >> "$FIXTURE_DOCKER_LOG"\n'
        'if [[ "$*" == *"--playwright-version"* ]]; then\n'
        + (
            'printf "1.64.0\\n"\n'
            if preflight_success
            else 'echo "Unsupported Node in image" >&2\nexit 42\n'
        )
        + 'else\nprintf "capture\\n" >> "$FIXTURE_DOCKER_LOG"\nfi\n',
        encoding="utf-8",
    )
    docker.chmod(0o755)
    node = tmp_path / "node"
    node.write_text(
        '#!/usr/bin/env bash\necho "Host Node must not run" >&2\nexit 99\n',
        encoding="utf-8",
    )
    node.chmod(0o755)
    fake_bin = str(tmp_path)
    if os.name == "nt":
        fake_bin = "/" + tmp_path.drive[0].lower() + tmp_path.as_posix()[2:]
    log = tmp_path / "docker.log"
    log_path = str(log)
    if os.name == "nt":
        log_path = "/" + log.drive[0].lower() + log.as_posix()[2:]
    env = {
        **os.environ,
        "GRAFANA_PASSWORD": "fixture-only",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN": "",
        "FIXTURE_DOCKER_LOG": log_path,
    }
    script = (
        ROOT / "scripts/ops/observability/grafana/capture_grafana_screenshots_docker.sh"
    )
    result = subprocess.run(
        [
            bash,
            "-c",
            'export PATH="$1:$PATH"; exec bash "$2" "$3"',
            "fixture",
            fake_bin,
            str(script),
            str(tmp_path / "screenshots"),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) == preflight_success, result.stderr
    recorded = log.read_text(encoding="utf-8")
    assert ("capture" in recorded) == preflight_success
    assert recorded.count("call") == (2 if preflight_success else 1)
    assert "Host Node must not run" not in result.stderr


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("compatible-path", "path"),
        ("old-path", "portable-nodejs"),
        ("incompatible-portable", None),
    ],
)
def test_powershell_resolves_only_engine_compatible_toolchain(
    tmp_path: Path, mode: str, expected: str | None
) -> None:
    powershell = (
        shutil.which("pwsh")
        or shutil.which("pwsh.exe")
        or shutil.which("powershell.exe")
    )
    if not powershell and os.name != "nt":
        pytest.skip("Optional PowerShell is unavailable on this Linux host")
    assert powershell, "PowerShell is required for the Windows resolver contract"
    setup = (
        ROOT / "scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.ps1"
    )
    script = r"""
$ErrorActionPreference = 'Stop'
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($env:FIXTURE_SETUP, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw 'Setup script syntax failed' }
$ast.FindAll({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -in @('Test-NodeToolchain','Resolve-NodeToolchain')}, $true) | ForEach-Object { Invoke-Expression $_.Extent.Text }
$RepoRoot = $env:FIXTURE_ROOT
function Get-Command { [CmdletBinding()] param([string]$Name) [pscustomobject]@{Source='fixture-old-node'} }
function fixture-old-node { $global:LASTEXITCODE = if ($env:FIXTURE_MODE -eq 'compatible-path') { 0 } else { 1 } }
function fixture-portable-node { $global:LASTEXITCODE = if ($env:FIXTURE_MODE -eq 'incompatible-portable') { 1 } else { 0 } }
function Resolve-PortableNodeToolchain { return @{NodeExe='fixture-portable-node';NpmCmd='fixture-npm';Source='portable-nodejs';InstallDir=$env:FIXTURE_ROOT} }
try { $selected = Resolve-NodeToolchain; Write-Output ('SELECTED=' + $selected.Source) } catch { Write-Output $_.Exception.Message; exit 1 }
"""
    result = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
        env={
            **os.environ,
            "FIXTURE_SETUP": str(setup),
            "FIXTURE_ROOT": str(tmp_path),
            "FIXTURE_MODE": mode,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    if expected is None:
        assert result.returncode != 0
        assert "Portable Node/manifest/lock runtime contract failed" in result.stdout
    else:
        assert result.returncode == 0, result.stderr
        assert f"SELECTED={expected}" in result.stdout
