#!/usr/bin/env pwsh
# Official github/github-mcp-server launch policy for BioETL GitHub MCP (#10262).
# The retired npx package @modelcontextprotocol/server-github is not a fallback.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")

$defaultToolsets = "context,issues,pull_requests,repos,users,actions,code_security,dependabot,notifications"
$defaultExcludeTools = "create_or_update_file,push_files,delete_file,fork_repository,create_repository,merge_pull_request,actions_run_trigger"

# One token path: existing PAT, else GITHUB_TOKEN alias, else `gh auth token`.
# Never overwrite a configured PAT, never print the secret, and never set
# process GITHUB_TOKEN from PAT (parent gh must keep hosts.yml; #10298).
if ($env:GITHUB_PERSONAL_ACCESS_TOKEN) {
    [Console]::Error.WriteLine("github MCP token path: GITHUB_PERSONAL_ACCESS_TOKEN")
} elseif ($env:GITHUB_TOKEN) {
    $env:GITHUB_PERSONAL_ACCESS_TOKEN = $env:GITHUB_TOKEN
    [Console]::Error.WriteLine("github MCP token path: GITHUB_TOKEN alias")
} else {
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if ($gh) {
        $token = & gh auth token 2>$null
        if ($token) {
            $env:GITHUB_PERSONAL_ACCESS_TOKEN = [string]$token
            [Console]::Error.WriteLine("github MCP token path: gh auth token")
        }
    }
}

Test-McpRequiredToken `
    -Name "GITHUB_PERSONAL_ACCESS_TOKEN" `
    -MinLength 20 `
    -Purpose "GitHub MCP" `
    -AllowedPrefixes @("ghp_", "github_pat_", "gho_", "ghu_", "ghs_", "ghr_")

if (-not $env:GITHUB_TOOLSETS) {
    $env:GITHUB_TOOLSETS = $defaultToolsets
}
if (-not $env:GITHUB_EXCLUDE_TOOLS) {
    $env:GITHUB_EXCLUDE_TOOLS = $defaultExcludeTools
}
if (-not $env:GITHUB_LOCKDOWN_MODE) {
    $env:GITHUB_LOCKDOWN_MODE = "true"
}

$env:GITHUB_EXCLUDE_TOOLS = (@(($env:GITHUB_EXCLUDE_TOOLS -split ',') + ($defaultExcludeTools -split ',')) | Select-Object -Unique) -join ','
Exit-McpValidateOnly -ServerName "github"

$githubMcpBin = $null
foreach ($candidate in @($env:BIOETL_GITHUB_MCP_SERVER, $env:GITHUB_MCP_SERVER_BIN)) {
    if ([string]::IsNullOrWhiteSpace($candidate)) {
        continue
    }
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        throw "GitHub MCP binary path is set but not a file: $candidate"
    }
    $githubMcpBin = (Resolve-Path -LiteralPath $candidate).Path
    break
}
if (-not $githubMcpBin) {
    foreach ($commandName in @("github-mcp-server.exe", "github-mcp-server")) {
        $cmd = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source) {
            $githubMcpBin = [string]$cmd.Source
            break
        }
    }
}
if (-not $githubMcpBin) {
    $homeCandidates = @()
    if ($env:USERPROFILE) {
        $homeCandidates += (Join-Path $env:USERPROFILE "tools\bin\github-mcp-server.exe")
        $homeCandidates += (Join-Path $env:USERPROFILE "tools\bin\github-mcp-server")
    }
    if ($env:LOCALAPPDATA) {
        $homeCandidates += (Join-Path $env:LOCALAPPDATA "Programs\github-mcp-server\github-mcp-server.exe")
    }
    foreach ($candidate in $homeCandidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $githubMcpBin = $candidate
            break
        }
    }
}
if (-not $githubMcpBin) {
    throw "official github-mcp-server binary not found. Install https://github.com/github/github-mcp-server and set BIOETL_GITHUB_MCP_SERVER. The retired npx package @modelcontextprotocol/server-github is not used."
}

if ($env:BIOETL_GITHUB_MCP_ACCESS -eq 'read-write' -and -not $env:BIOETL_GITHUB_MCP_SHA256) {
    throw 'read-write requires an explicitly approved BIOETL_GITHUB_MCP_SHA256'
}
if ($env:BIOETL_GITHUB_MCP_SHA256) {
    if ($env:BIOETL_GITHUB_MCP_SHA256 -notmatch '^[a-fA-F0-9]{64}$' -or
        (Get-FileHash -LiteralPath $githubMcpBin -Algorithm SHA256).Hash -ne $env:BIOETL_GITHUB_MCP_SHA256) {
        throw 'GitHub MCP executable digest does not match approved identity'
    }
}
$stdioArgs = [System.Collections.Generic.List[string]]::new()
$stdioArgs.Add("stdio") | Out-Null
switch ($env:BIOETL_GITHUB_MCP_ACCESS) {
    { [string]::IsNullOrWhiteSpace($_) -or $_ -eq 'read-only' } { $stdioArgs.Add('--read-only') | Out-Null }
    'read-write' { }
    default { throw 'BIOETL_GITHUB_MCP_ACCESS must be read-only or read-write' }
}
$stdioArgs.Add("--toolsets") | Out-Null
$stdioArgs.Add([string]$env:GITHUB_TOOLSETS) | Out-Null
if ($env:GITHUB_EXCLUDE_TOOLS) {
    $stdioArgs.Add("--exclude-tools") | Out-Null
    $stdioArgs.Add([string]$env:GITHUB_EXCLUDE_TOOLS) | Out-Null
}
switch -Regex ([string]$env:GITHUB_LOCKDOWN_MODE) {
    "^(?i:0|false|no|off)$" { }
    default { $stdioArgs.Add("--lockdown-mode") | Out-Null }
}

# Limit the native child's environment while preserving PowerShell's stdio
# forwarding. A ProcessStartInfo without explicit stream pumps loses MCP I/O.
$allowedEnv = @('PATH', 'HOME', 'USERPROFILE', 'SYSTEMROOT', 'WINDIR',
    'TEMP', 'TMP', 'TMPDIR', 'LANG', 'LC_ALL', 'SSL_CERT_FILE', 'SSL_CERT_DIR',
    'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'GITHUB_PERSONAL_ACCESS_TOKEN', 'GITHUB_HOST')
$removedEnv = @{}
Get-ChildItem Env: | ForEach-Object {
    if ($_.Name -notin $allowedEnv) {
        $removedEnv[$_.Name] = $_.Value
        Remove-Item -LiteralPath "Env:$($_.Name)"
    }
}
try {
    & $githubMcpBin @($stdioArgs.ToArray())
    $childExitCode = $LASTEXITCODE
} finally {
    foreach ($key in $removedEnv.Keys) {
        [Environment]::SetEnvironmentVariable($key, $removedEnv[$key], 'Process')
    }
}
exit $childExitCode
