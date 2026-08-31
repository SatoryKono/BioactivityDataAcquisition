#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")
. (Join-Path $PSScriptRoot "support/uv_resolver.ps1")

if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $repoRoot ".cache/uv-cache"
}
if (-not $env:UV_TOOL_DIR) {
    $env:UV_TOOL_DIR = Join-Path $repoRoot ".cache/uv-tools"
}
New-Item -ItemType Directory -Force -Path $env:UV_CACHE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $env:UV_TOOL_DIR | Out-Null

Exit-McpValidateOnly -ServerName "mcp-code-interpreter"

# 1) Local Python module if installed (no Deno required)
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python -and $python.Source) {
    try {
        $pythonExe = $python.Source
        & $pythonExe -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('mcp_server_code_interpreter') else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            & $pythonExe -m mcp_server_code_interpreter
            exit $LASTEXITCODE
        }
    }
    catch {
        [Console]::Error.WriteLine(
            "mcp-code-interpreter: local Python module probe failed; falling back to uvx/Deno. $($_.Exception.Message)"
        )
    }
}

# 2) Canonical: PyPI mcp-run-python (sandboxed Python code execution MCP)
# mcp-run-python requires Deno, but the local Python module above does not.
$uvx = Resolve-BioetlUvxBin
if (Test-BioetlUvxAvailable) {
    # Deno setup only for mcp-run-python branch
    $denoBin = Join-Path $env:USERPROFILE ".deno\bin"
    if (Test-Path $denoBin) {
        $env:PATH = "$denoBin$([IO.Path]::PathSeparator)$env:PATH"
    }
    if (-not $env:DENO_DIR) {
        $env:DENO_DIR = Join-Path $env:USERPROFILE ".cache\deno"
    }
    New-Item -ItemType Directory -Force -Path $env:DENO_DIR | Out-Null

    if (-not (Get-Command deno -ErrorAction SilentlyContinue)) {
        [Console]::Error.WriteLine(
            "mcp-code-interpreter requires Deno for the mcp-run-python fallback."
        )
        [Console]::Error.WriteLine(
            "Install deno into %USERPROFILE%\.deno\bin (e.g. download"
        )
        [Console]::Error.WriteLine(
            "deno-x86_64-pc-windows-msvc.zip with curl --ssl-no-revoke)."
        )
        exit 1
    }

    # Mode is a positional arg: stdio | streamable-http | ...
    Invoke-BioetlUvxWithScopedBypass `
        -UvxPath $uvx `
        -Package "mcp-run-python==0.0.22" `
        -Command "mcp-run-python" `
        -CommandArguments @("stdio")
    exit $LASTEXITCODE
}

[Console]::Error.WriteLine("mcp-code-interpreter could not start.")
[Console]::Error.WriteLine(
    "Install uv (https://docs.astral.sh/uv/) so uvx is on PATH, then the wrapper"
)
[Console]::Error.WriteLine(
    "will run: uvx --from mcp-run-python==0.0.22 mcp-run-python stdio"
)
exit 1
