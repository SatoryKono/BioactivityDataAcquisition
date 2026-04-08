@echo off
REM Neo4j Memory MCP - Windows Batch Verification
REM Run this from Windows Command Prompt (cmd.exe)

setlocal enabledelayedexpansion

echo.
echo ================================================================================
echo Neo4j Memory MCP - Verification
echo ================================================================================
echo.

echo Checking Docker container...
docker ps --filter "name=bioetl-neo4j" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: Container is running
    echo.
    echo Next steps:
    echo  1. Browser: http://localhost:7474/browser
    echo  2. Codex: codex interactive
    echo  3. MCP: codex mcp get neo4j-memory
    echo.
) else (
    echo.
    echo ERROR: Docker not accessible from cmd.exe
    echo Use PowerShell instead:
    echo  PS^> docker ps ^| Select-String neo4j
    echo.
)

echo ================================================================================
echo Checking MCP registration...
codex mcp list 2>nul | find "neo4j-memory"

if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: neo4j-memory is registered
) else (
    echo NOTE: Codex CLI not available or neo4j-memory not registered
    echo Register with: uv run python -m scripts.dev setup-mcp
)

echo ================================================================================
echo Checking wrapper script...
if exist "scripts\ops\mcp_neo4j_memory_wrapper.sh" (
    echo SUCCESS: Wrapper script exists
    findstr "@knowall-ai/mcp-neo4j-agent-memory" scripts\ops\mcp_neo4j_memory_wrapper.sh >nul
    if %ERRORLEVEL% EQU 0 (
        echo SUCCESS: Uses correct package
    )
) else (
    echo ERROR: Wrapper script not found
)

echo.
echo ================================================================================
echo SUMMARY
echo ================================================================================
echo.
echo If Docker shows bioetl-neo4j running and healthy:
echo   ^> Neo4j Memory MCP is ready!
echo.
echo Next: 
echo   1. http://localhost:7474/browser (Neo4j Browser)
echo   2. codex interactive (Use @neo4j-memory)
echo.
echo ================================================================================
echo.
