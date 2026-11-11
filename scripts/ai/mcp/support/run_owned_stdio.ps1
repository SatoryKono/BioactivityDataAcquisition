function Get-OwnedMcpLauncher {
    param(
        [Parameter(Mandatory)][string]$LauncherRelativePath,
        [Parameter(Mandatory)][string]$Policy,
        [Parameter(Mandatory)][string]$OwnerPathPattern,
        [string]$ProfilePattern = ""
    )
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw "Windows profile unavailable"
    }
    $localProfile = $env:LOCALAPPDATA
    if (-not $localProfile) {
        $localProfile = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
    }
    $path = Join-Path $localProfile $LauncherRelativePath
    $descriptor = Get-Item -LiteralPath $path
    if ($descriptor.PSIsContainer -or $descriptor.Length -gt 4096 -or
        ($descriptor.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Invalid launcher descriptor"
    }
    $launcher = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    if ($launcher.policy -ne $Policy -or
        $launcher.python -notmatch '^[A-Za-z]:[\\/].*[\\/]python\.exe$' -or
        $launcher.owner -notmatch $OwnerPathPattern -or
        -not (Test-Path -LiteralPath $launcher.python -PathType Leaf) -or
        -not (Test-Path -LiteralPath $launcher.owner -PathType Leaf) -or
        ($ProfilePattern -and $launcher.profile -notmatch $ProfilePattern)) {
        throw "Invalid launcher fields"
    }
    return $launcher
}

function Resolve-OwnedMcpLauncherOrExit {
    param(
        [Parameter(Mandatory)][string]$LauncherRelativePath,
        [Parameter(Mandatory)][string]$Policy,
        [Parameter(Mandatory)][string]$OwnerPathPattern,
        [Parameter(Mandatory)][string]$MissingOwnerMessage,
        [string]$ProfilePattern = ""
    )
    try {
        return Get-OwnedMcpLauncher `
            -LauncherRelativePath $LauncherRelativePath `
            -Policy $Policy `
            -OwnerPathPattern $OwnerPathPattern `
            -ProfilePattern $ProfilePattern
    } catch {
        [Console]::Error.WriteLine($MissingOwnerMessage)
        exit 1
    }
}

function Invoke-OwnedMcpStdio {
    param([Parameter(Mandatory)][string]$Python, [Parameter(Mandatory)][string]$Arguments)
    # Forward raw MCP frames without PowerShell's text pipeline.
    [Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $Python
    $start.Arguments = $Arguments
    $start.WorkingDirectory = (Get-Location).ProviderPath
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $adapter = [System.Diagnostics.Process]::Start($start)
    try {
        $clientInput = [Console]::OpenStandardInput()
        $clientOutput = [Console]::OpenStandardOutput()
        $adapterInput = $adapter.StandardInput.BaseStream
        $adapterOutput = $adapter.StandardOutput.BaseStream
        $requestBytes = New-Object byte[] 4096
        $responseBytes = New-Object byte[] 4096
        $requestRead = $clientInput.ReadAsync($requestBytes, 0, $requestBytes.Length)
        $responseRead = $adapterOutput.ReadAsync($responseBytes, 0, $responseBytes.Length)
        while ($true) {
            if ($responseRead.IsCompleted) {
                $count = $responseRead.GetAwaiter().GetResult()
                if ($count -eq 0) { break }
                $clientOutput.Write($responseBytes, 0, $count)
                $clientOutput.Flush()
                $responseRead = $adapterOutput.ReadAsync($responseBytes, 0, $responseBytes.Length)
            }
            if ($requestRead -and $requestRead.IsCompleted) {
                $count = $requestRead.GetAwaiter().GetResult()
                if ($count -eq 0) {
                    $adapter.StandardInput.Close()
                    $requestRead = $null
                } else {
                    $adapterInput.Write($requestBytes, 0, $count)
                    $adapterInput.Flush()
                    $requestRead = $clientInput.ReadAsync($requestBytes, 0, $requestBytes.Length)
                }
            }
            Start-Sleep -Milliseconds 10
        }
        $adapter.WaitForExit()
        return $adapter.ExitCode
    } finally {
        $adapter.Dispose()
    }
}
