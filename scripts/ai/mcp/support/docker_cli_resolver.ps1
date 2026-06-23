#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-DockerBin {
    $candidates = @()
    $dockerDesktopDefault = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"

    foreach ($name in @("docker.exe", "docker")) {
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

    throw "Docker CLI not found or not working. Install Docker Desktop or enable WSL integration."
}
