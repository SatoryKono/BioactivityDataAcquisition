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
