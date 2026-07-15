#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-DockerEngineBin {
    $candidates = @()
    $dockerDesktopDefault = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"

    foreach ($name in @("docker", "docker.exe")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) {
            $candidates += $command.Source
        }
    }

    if (Test-Path $dockerDesktopDefault) {
        $candidates += $dockerDesktopDefault
    }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        try {
            & $candidate version *> $null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
            continue
        }
    }

    throw "Docker Engine CLI not found or not working. Install Docker or enable WSL integration."
}

function Resolve-DockerMcpGatewayBin {
    $candidates = @()
    $dockerDesktopDefault = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
    if (Test-Path $dockerDesktopDefault) { $candidates += $dockerDesktopDefault }
    $dockerExe = Get-Command docker.exe -ErrorAction SilentlyContinue
    if ($dockerExe) { $candidates += $dockerExe.Source }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        try {
            & $candidate mcp gateway --help *> $null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        } catch { continue }
    }
    throw "Docker Desktop MCP gateway is unavailable; no incompatible CLI fallback was used."
}

function Resolve-DockerBin {
    return Resolve-DockerEngineBin
}
