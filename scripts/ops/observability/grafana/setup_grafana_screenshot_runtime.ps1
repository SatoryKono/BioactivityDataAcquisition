[CmdletBinding()]
param(
    [switch]$Smoke,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Show-Usage {
    @"
Usage:
  powershell -ExecutionPolicy Bypass -File scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.ps1 [-Smoke]

Options:
  -Smoke   Run a non-GUI screenshot smoke command after setup.
  -Help    Show this help.

Environment:
  NPM_CONFIG_CACHE          npm cache directory. Default: %TEMP%\npm-cache
  PLAYWRIGHT_BROWSERS_PATH  Browser download directory. Default: %TEMP%\playwright-browsers
  UV_CACHE_DIR              uv cache directory for smoke command. Default: %TEMP%\uv-cache
  BIOETL_TOOLS_DIR          Local tool cache root. Default: %LOCALAPPDATA%\bioetl-tools
  GRAFANA_BASE_URL          Optional smoke target. Default from rerender-grafana.
  GRAFANA_USERNAME          Optional smoke auth. Default from rerender-grafana.
  GRAFANA_PASSWORD          Optional smoke auth. Default from rerender-grafana.
"@
}

if ($Help) {
    Show-Usage
    exit 0
}

$ScriptDir = Split-Path -Parent $PSCommandPath
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\..\..\.."))

$NpmCache = if ($env:NPM_CONFIG_CACHE) { $env:NPM_CONFIG_CACHE } else { Join-Path $env:TEMP "npm-cache" }
$PlaywrightBrowsersPath = if ($env:PLAYWRIGHT_BROWSERS_PATH) { $env:PLAYWRIGHT_BROWSERS_PATH } else { Join-Path $env:TEMP "playwright-browsers" }
$UvCacheDir = if ($env:UV_CACHE_DIR) { $env:UV_CACHE_DIR } else { Join-Path $env:TEMP "uv-cache" }
$ToolsRoot = if ($env:BIOETL_TOOLS_DIR) { $env:BIOETL_TOOLS_DIR } else { Join-Path $env:LOCALAPPDATA "bioetl-tools" }
$NodeToolsRoot = Join-Path $ToolsRoot "nodejs"
$GrafanaBaseUrl = if ($env:GRAFANA_BASE_URL) { $env:GRAFANA_BASE_URL } else { "http://localhost:3000" }
$GrafanaUsername = if ($env:GRAFANA_USERNAME) { $env:GRAFANA_USERNAME } else { "admin" }
$GrafanaPassword = if ($env:GRAFANA_PASSWORD) { $env:GRAFANA_PASSWORD } else { "changeme" }

function Ensure-Directory {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )

    Write-Host $Label
    $global:LASTEXITCODE = 0
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

Ensure-Directory -Path $NpmCache
Ensure-Directory -Path $PlaywrightBrowsersPath
Ensure-Directory -Path $UvCacheDir
Ensure-Directory -Path $NodeToolsRoot

function Get-LatestNodeLtsWinX64Release {
    $indexUrl = "https://nodejs.org/dist/index.json"
    $releases = Invoke-RestMethod -Uri $indexUrl
    $release = $releases |
        Where-Object { $_.lts -and $_.files -contains "win-x64-zip" } |
        Select-Object -First 1
    if (-not $release) {
        throw "Could not resolve a Windows x64 Node.js LTS release from $indexUrl."
    }
    return $release
}

function Resolve-PortableNodeToolchain {
    $release = Get-LatestNodeLtsWinX64Release
    $version = [string]$release.version
    $baseName = "node-$version-win-x64"
    $installDir = Join-Path $NodeToolsRoot $baseName
    $nodeExe = Join-Path $installDir "node.exe"
    $npmCmd = Join-Path $installDir "npm.cmd"

    if (-not ((Test-Path -LiteralPath $nodeExe) -and (Test-Path -LiteralPath $npmCmd))) {
        $zipName = "$baseName.zip"
        $downloadUrl = "https://nodejs.org/dist/$version/$zipName"
        $zipPath = Join-Path $env:TEMP $zipName
        $extractRoot = Join-Path $env:TEMP ("bioetl-node-extract-" + [System.Guid]::NewGuid().ToString("N"))

        Write-Host "Downloading portable Node.js LTS from $downloadUrl..."
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath
        Ensure-Directory -Path $extractRoot
        Expand-Archive -LiteralPath $zipPath -DestinationPath $extractRoot -Force

        $expandedDir = Join-Path $extractRoot $baseName
        if (-not (Test-Path -LiteralPath $expandedDir)) {
            throw "Downloaded Node.js archive did not contain $baseName."
        }

        if (Test-Path -LiteralPath $installDir) {
            Remove-Item -LiteralPath $installDir -Recurse -Force
        }
        Move-Item -LiteralPath $expandedDir -Destination $installDir
        Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $extractRoot -Recurse -Force -ErrorAction SilentlyContinue
    }

    return @{
        NodeExe = $nodeExe
        NpmCmd = $npmCmd
        Source = "portable-nodejs"
        InstallDir = $installDir
    }
}

function Resolve-NodeToolchain {
    $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
    $npmCommand = Get-Command npm -ErrorAction SilentlyContinue
    if ($nodeCommand -and $npmCommand) {
        return @{
            NodeExe = $nodeCommand.Source
            NpmCmd = $npmCommand.Source
            Source = "path"
            InstallDir = ""
        }
    }

    $portable = Resolve-PortableNodeToolchain
    $env:Path = "$($portable.InstallDir);$env:Path"
    return $portable
}

function Resolve-PythonCommand {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }

    $repoVenvPython = Join-Path $RepoRoot ".venv-win\Scripts\python.exe"
    if (Test-Path -LiteralPath $repoVenvPython) {
        return $repoVenvPython
    }

    throw "Could not find 'python' on PATH or .venv-win\\Scripts\\python.exe in the repository."
}

$NodeToolchain = Resolve-NodeToolchain
$PythonCommand = Resolve-PythonCommand
Write-Host "Using Node toolchain source: $($NodeToolchain.Source)"
Write-Host "Using Python command: $PythonCommand"
Write-Host "Using Grafana base URL: $GrafanaBaseUrl"
Write-Host "Using Grafana username: $GrafanaUsername"

Push-Location $RepoRoot
try {
    Invoke-Step -Label "Installing repo-local Node dependencies..." -Action {
        $env:NPM_CONFIG_CACHE = $NpmCache
        $env:NPM_CONFIG_INCLUDE = "dev"
        $env:NPM_CONFIG_PRODUCTION = "false"
        $env:npm_config_production = "false"
        $env:NODE_ENV = "development"
        if (Test-Path -LiteralPath (Join-Path $RepoRoot "package-lock.json")) {
            & $NodeToolchain.NpmCmd ci --include=dev --no-bin-links
        }
        else {
            & $NodeToolchain.NpmCmd install --include=dev --no-bin-links
        }
    }

    Invoke-Step -Label "Installing Playwright Chromium runtime into $PlaywrightBrowsersPath..." -Action {
        if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot "node_modules/playwright/cli.js"))) {
            throw "Playwright CLI is missing after dependency install. Ensure repo-local devDependencies were installed before browser bootstrap."
        }
        $env:PLAYWRIGHT_BROWSERS_PATH = $PlaywrightBrowsersPath
        & $NodeToolchain.NodeExe node_modules/playwright/cli.js install chromium
    }

    Invoke-Step -Label "Running headless Chromium launch smoke..." -Action {
        $env:PLAYWRIGHT_BROWSERS_PATH = $PlaywrightBrowsersPath
        $launchSmokeScript = @"
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  await browser.close();
})().catch((error) => {
  console.error(String(error && error.message ? error.message : error));
  process.exit(1);
});
"@
        & $NodeToolchain.NodeExe -e $launchSmokeScript
    }

    if ($Smoke) {
        Invoke-Step -Label "Running screenshot smoke against rerender-grafana..." -Action {
            $env:PLAYWRIGHT_BROWSERS_PATH = $PlaywrightBrowsersPath
            $env:GRAFANA_BASE_URL = $GrafanaBaseUrl
            $env:GRAFANA_USERNAME = $GrafanaUsername
            $env:GRAFANA_PASSWORD = $GrafanaPassword
            & $PythonCommand -m scripts.ops rerender-grafana --uids bioetl-control-plane-v1 --timeout-seconds 30 --fallback playwright
        }
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Grafana screenshot runtime is ready."
Write-Host "PowerShell example:"
Write-Host "  `$env:PLAYWRIGHT_BROWSERS_PATH = '$PlaywrightBrowsersPath'"
Write-Host "  `$env:GRAFANA_BASE_URL = '$GrafanaBaseUrl'"
Write-Host "  `$env:GRAFANA_USERNAME = '$GrafanaUsername'"
Write-Host "  `$env:GRAFANA_PASSWORD = '$GrafanaPassword'"
Write-Host "  & '$PythonCommand' -m scripts.ops rerender-grafana --uids bioetl-control-plane-v1"
