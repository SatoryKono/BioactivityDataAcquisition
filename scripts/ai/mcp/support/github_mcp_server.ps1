# Official github/github-mcp-server launch policy for BioETL GitHub MCP (#10262).
# The retired npx package @modelcontextprotocol/server-github is not a fallback.

$script:BioetlGithubMcpDefaultToolsets = "context,issues,pull_requests,repos,users,actions,code_security,dependabot,notifications"
$script:BioetlGithubMcpDefaultExcludeTools = "create_or_update_file,push_files,delete_file,fork_repository,create_repository,merge_pull_request,actions_run_trigger"

function Set-BioetlGithubMcpPolicyEnv {
    if (-not $env:GITHUB_TOOLSETS) {
        $env:GITHUB_TOOLSETS = $script:BioetlGithubMcpDefaultToolsets
    }
    if (-not $env:GITHUB_EXCLUDE_TOOLS) {
        $env:GITHUB_EXCLUDE_TOOLS = $script:BioetlGithubMcpDefaultExcludeTools
    }
    if (-not $env:GITHUB_LOCKDOWN_MODE) {
        $env:GITHUB_LOCKDOWN_MODE = "true"
    }
}

function Resolve-BioetlGithubMcpToken {
    # One token path: existing PAT, else GITHUB_TOKEN alias, else `gh auth token`.
    # Never overwrite a configured PAT and never print the secret.
    if ($env:GITHUB_PERSONAL_ACCESS_TOKEN) {
        [Console]::Error.WriteLine("github MCP token path: GITHUB_PERSONAL_ACCESS_TOKEN")
        return
    }
    if ($env:GITHUB_TOKEN) {
        $env:GITHUB_PERSONAL_ACCESS_TOKEN = $env:GITHUB_TOKEN
        [Console]::Error.WriteLine("github MCP token path: GITHUB_TOKEN alias")
        return
    }
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if ($gh) {
        $token = & gh auth token 2>$null
        if ($token) {
            $env:GITHUB_PERSONAL_ACCESS_TOKEN = [string]$token
            [Console]::Error.WriteLine("github MCP token path: gh auth token")
            return
        }
    }
    throw "GitHub MCP requires one token path: GITHUB_PERSONAL_ACCESS_TOKEN, GITHUB_TOKEN alias, or gh auth token. Do not commit secrets."
}

function Resolve-BioetlGithubMcpServerBin {
    foreach ($candidate in @($env:BIOETL_GITHUB_MCP_SERVER, $env:GITHUB_MCP_SERVER_BIN)) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
        throw "GitHub MCP binary path is set but not a file: $candidate"
    }

    foreach ($commandName in @("github-mcp-server.exe", "github-mcp-server")) {
        $cmd = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source) {
            return [string]$cmd.Source
        }
    }

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
            return $candidate
        }
    }
    throw "official github-mcp-server binary not found. Install https://github.com/github/github-mcp-server and set BIOETL_GITHUB_MCP_SERVER. The retired npx package @modelcontextprotocol/server-github is not used."
}

function Get-BioetlGithubMcpStdioArgs {
    $argsList = [System.Collections.Generic.List[string]]::new()
    $argsList.Add("stdio") | Out-Null
    $argsList.Add("--toolsets") | Out-Null
    $argsList.Add([string]$env:GITHUB_TOOLSETS) | Out-Null
    if ($env:GITHUB_EXCLUDE_TOOLS) {
        $argsList.Add("--exclude-tools") | Out-Null
        $argsList.Add([string]$env:GITHUB_EXCLUDE_TOOLS) | Out-Null
    }
    switch -Regex ([string]$env:GITHUB_LOCKDOWN_MODE) {
        "^(?i:0|false|no|off)$" { }
        default {
            $argsList.Add("--lockdown-mode") | Out-Null
        }
    }
    return , $argsList.ToArray()
}
