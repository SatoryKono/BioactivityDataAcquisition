[CmdletBinding()]
param(
    [string]$BaseUrl = "",
    [string]$Username = "",
    [string]$Password = "",
    [string]$PlaywrightBrowsersPath = "",
    [string]$OutputDir = "",
    [double]$TimeoutSeconds = 60.0,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Show-Usage {
    @"
Usage:
  powershell -ExecutionPolicy Bypass -File scripts/ops/observability/grafana/render_all_grafana_screenshots.ps1

Options:
  -BaseUrl                 Grafana base URL. Default: GRAFANA_BASE_URL or http://localhost:3000
  -Username                Grafana username. Default: GRAFANA_USERNAME or admin
  -Password                Grafana password. Default: GRAFANA_PASSWORD or changeme
  -PlaywrightBrowsersPath  Browser cache path. Default: PLAYWRIGHT_BROWSERS_PATH or %TEMP%\playwright-browsers
  -OutputDir               Screenshot output dir. Default: reports/observability/grafana/screenshots
  -TimeoutSeconds          Per-dashboard timeout. Default: 60
  -Help                    Show this help.

This helper assumes the screenshot runtime has already been bootstrapped with:
  scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.ps1
"@
}

if ($Help) {
    Show-Usage
    exit 0
}

$ScriptDir = Split-Path -Parent $PSCommandPath
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\..\..\.."))
$ToolsRoot = if ($env:BIOETL_TOOLS_DIR) { $env:BIOETL_TOOLS_DIR } else { Join-Path $env:LOCALAPPDATA "bioetl-tools" }
$NodeToolsRoot = Join-Path $ToolsRoot "nodejs"

function Ensure-Directory {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

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

$ResolvedBaseUrl = if ($BaseUrl) { $BaseUrl } elseif ($env:GRAFANA_BASE_URL) { $env:GRAFANA_BASE_URL } else { "http://localhost:3000" }
$ResolvedUsername = if ($Username) { $Username } elseif ($env:GRAFANA_USERNAME) { $env:GRAFANA_USERNAME } else { "admin" }
$ResolvedPassword = if ($Password) { $Password } elseif ($env:GRAFANA_PASSWORD) { $env:GRAFANA_PASSWORD } else { "changeme" }
$ResolvedBrowsersPath = if ($PlaywrightBrowsersPath) {
    $PlaywrightBrowsersPath
} elseif ($env:PLAYWRIGHT_BROWSERS_PATH) {
    $env:PLAYWRIGHT_BROWSERS_PATH
} else {
    Join-Path $env:TEMP "playwright-browsers"
}
$ResolvedOutputDir = if ($OutputDir) { $OutputDir } else { "reports/observability/grafana/screenshots" }
$NodeToolchain = Resolve-NodeToolchain
$PythonCommand = Resolve-PythonCommand
$PlaywrightScript = Join-Path $ScriptDir "rerender_grafana_screenshots.cjs"

$env:GRAFANA_BASE_URL = $ResolvedBaseUrl
$env:GRAFANA_USERNAME = $ResolvedUsername
$env:GRAFANA_PASSWORD = $ResolvedPassword
$env:PLAYWRIGHT_BROWSERS_PATH = $ResolvedBrowsersPath
$env:GRAFANA_SCREENSHOT_OUTPUT_DIR = $ResolvedOutputDir
$env:GRAFANA_SCREENSHOT_TIMEOUT_MS = [string][int]($TimeoutSeconds * 1000)

Write-Host "Rendering all shipped Grafana dashboards..."
Write-Host "Using Node toolchain source: $($NodeToolchain.Source)"
Write-Host "Base URL: $ResolvedBaseUrl"
Write-Host "Username: $ResolvedUsername"
Write-Host "Browsers path: $ResolvedBrowsersPath"
Write-Host "Output dir: $ResolvedOutputDir"

Push-Location $RepoRoot
try {
    & $NodeToolchain.NodeExe $PlaywrightScript

    if ($LASTEXITCODE -ne 0) {
        throw "Playwright dashboard render failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Completed full Grafana screenshot render."
Write-Host "Manifest:"
Write-Host "  $ResolvedOutputDir\\render-manifest.json"
