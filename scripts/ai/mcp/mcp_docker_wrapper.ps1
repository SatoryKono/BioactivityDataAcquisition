#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

& docker mcp gateway run --servers docker --transport stdio
exit $LASTEXITCODE
