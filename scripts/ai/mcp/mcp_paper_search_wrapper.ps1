#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

& docker mcp gateway run --servers paper-search --transport stdio
exit $LASTEXITCODE
