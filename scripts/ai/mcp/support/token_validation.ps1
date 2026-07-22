Set-StrictMode -Version Latest

function Write-McpTokenWarning {
    param([string]$Message)
    # Never write to PowerShell warning/output streams that can leak onto
    # process stdout — MCP stdio transport requires pure JSON on stdout.
    [Console]::Error.WriteLine("warning: $Message")
}

function Test-McpRequiredToken {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][int]$MinLength,
        [Parameter(Mandatory = $true)][string]$Purpose,
        [string[]]$AllowedPrefixes = @()
    )

    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrEmpty($value)) {
        throw "$Name is required for $Purpose. Configure it in the shell or local .env; do not commit secrets."
    }
    if ($value.Length -lt $MinLength) {
        throw "$Name for $Purpose is too short; expected at least $MinLength characters."
    }
    if ($AllowedPrefixes.Count -gt 0) {
        $matched = $false
        foreach ($prefix in $AllowedPrefixes) {
            if ($value.StartsWith($prefix, [StringComparison]::Ordinal)) {
                $matched = $true
                break
            }
        }
        if (-not $matched) {
            Write-McpTokenWarning "$Name for $Purpose has a non-standard prefix; verify token source and scopes."
        }
    }
}

function Test-McpOptionalToken {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][int]$MinLength,
        [Parameter(Mandatory = $true)][string]$Purpose,
        [string[]]$AllowedPrefixes = @()
    )

    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrEmpty($value)) {
        Write-McpTokenWarning "$Name is not set for $Purpose; continuing with unauthenticated or local-default behavior."
        return
    }
    if ($value.Length -lt $MinLength) {
        Write-McpTokenWarning "$Name for $Purpose is shorter than expected; verify the configured secret."
    }
    if ($AllowedPrefixes.Count -gt 0) {
        $matched = $false
        foreach ($prefix in $AllowedPrefixes) {
            if ($value.StartsWith($prefix, [StringComparison]::Ordinal)) {
                $matched = $true
                break
            }
        }
        if (-not $matched) {
            Write-McpTokenWarning "$Name for $Purpose has a non-standard prefix; verify token source and scopes."
        }
    }
}

function Test-McpNeo4jCredentials {
    param([Parameter(Mandatory = $true)][string]$Purpose)

    if (-not $env:NEO4J_URI) {
        Write-McpTokenWarning "NEO4J_URI is not set for $Purpose; wrapper will use its local default."
    }
    if (-not $env:NEO4J_USERNAME) {
        Write-McpTokenWarning "NEO4J_USERNAME is not set for $Purpose; wrapper will fail closed."
    }
    if (-not $env:NEO4J_PASSWORD) {
        Write-McpTokenWarning "NEO4J_PASSWORD is not set for $Purpose; wrapper will fail closed."
    } elseif ($env:NEO4J_PASSWORD -match "_secure_password$") {
        Write-McpTokenWarning "NEO4J_PASSWORD for $Purpose matches a legacy placeholder pattern; rotate it."
    }
}

function Exit-McpValidateOnly {
    param([Parameter(Mandatory = $true)][string]$ServerName)

    if ($env:BIOETL_MCP_VALIDATE_ONLY -eq "1") {
        Write-Output "[OK] $ServerName MCP wrapper validation completed"
        exit 0
    }
}
