# Binary-safe stdio relay to a Windows-local TCP endpoint.
param([Parameter(Mandatory = $true)][int]$Port)
$ErrorActionPreference = 'Stop'
$client = [System.Net.Sockets.TcpClient]::new('127.0.0.1', $Port)
$stream = $client.GetStream()
$stdin = [Console]::OpenStandardInput()
$stdout = [Console]::OpenStandardOutput()
$up = $stdin.CopyToAsync($stream)
$down = $stream.CopyToAsync($stdout)
[System.Threading.Tasks.Task]::WaitAny([System.Threading.Tasks.Task[]]@($up, $down)) | Out-Null
$client.Close()
