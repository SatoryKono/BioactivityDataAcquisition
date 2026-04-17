#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

& docker mcp gateway run --servers context7 --transport stdio
exit $LASTEXITCODE
