Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$rootDir = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$vscodeMcpPath = Join-Path $rootDir ".vscode/mcp.json"
$githubMcpPackage = "@modelcontextprotocol/server-github@2025.4.8"

Write-Host "[1/3] Writing VS Code MCP config: $vscodeMcpPath"
New-Item -ItemType Directory -Force -Path (Split-Path $vscodeMcpPath -Parent) | Out-Null

@'
{
  "servers": {
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github@2025.4.8"
      ]
    }
  }
}
'@ | Set-Content -Path $vscodeMcpPath -Encoding UTF8

$codexCmd = Get-Command codex -ErrorAction SilentlyContinue
if (-not $codexCmd) {
    Write-Host "[2/3] Codex CLI not found. Skipping Codex MCP registration."
    Write-Host "[3/3] Done."
    exit 0
}

Write-Host "[2/3] Checking Codex MCP server registration: github"
$githubMcpExists = $false
try {
    & codex mcp get github *> $null
    if ($LASTEXITCODE -eq 0) {
        $githubMcpExists = $true
    }
}
catch {
    $githubMcpExists = $false
}

if ($githubMcpExists) {
    Write-Host "      github MCP already registered in Codex."
}
else {
    & codex mcp add github -- npx -y $githubMcpPackage
    Write-Host "      github MCP registered in Codex."
}

Write-Host "[3/3] Done."
Write-Host "Set GITHUB_PERSONAL_ACCESS_TOKEN in your shell before using GitHub MCP tools."
