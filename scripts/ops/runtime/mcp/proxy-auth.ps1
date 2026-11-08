# Process-scoped compatibility helper for Windows PowerShell 5.1 and 7.
# The key is inherited by the child in env, never placed into argv/DryRun.
function Invoke-WithMcpProxyAuth {
    [CmdletBinding()]
    param(
        [AllowEmptyString()][string]$ApiKey,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )
    $previous = [Environment]::GetEnvironmentVariable('MCP_PROXY_API_KEY', 'Process')
    try {
        $value = if ([string]::IsNullOrWhiteSpace($ApiKey)) { $null } else { $ApiKey }
        [Environment]::SetEnvironmentVariable('MCP_PROXY_API_KEY', $value, 'Process')
        & $Action
    } finally {
        [Environment]::SetEnvironmentVariable('MCP_PROXY_API_KEY', $previous, 'Process')
    }
}
