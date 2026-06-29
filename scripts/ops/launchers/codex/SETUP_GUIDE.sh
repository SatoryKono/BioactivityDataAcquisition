#!/usr/bin/env bash
# Codex launcher quick start guide

cat << 'EOF'

╔════════════════════════════════════════════════════════════════════════════╗
║                          CODEX LAUNCHER SETUP                             ║
║                                                                            ║
║  Two launchers are now available:                                         ║
║                                                                            ║
║  1. scripts\ops\launchers\codex\codex.bat                                 ║
║     • Default launcher - includes full MCP setup                          ║
║     • Use this for full features with MCP (filesystem, memory, fetch)     ║
║     • May be slower on first run (30-60s depending on system)             ║
║                                                                            ║
║  2. scripts\ops\launchers\codex\codex-fast.bat                            ║
║     • Fast launcher - skips MCP validation                                ║
║     • Use this for quick interactive sessions                             ║
║     • ~3-5 seconds startup (no MCP setup delays)                          ║
║     • MCP servers still work if pre-configured                            ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

TROUBLESHOOTING:

Q: Codex exits immediately after launching
A: This was due to WSL/MCP setup timeouts. Now fixed with:
   • Reduced MCP timeout from 60s → 15s
   • Added CODEX_SKIP_MCP_SETUP mode
   • Use codex-fast.bat for instant startup

Q: MCP servers not working?
A: Run full setup:
   set CODEX_FORCE_MCP_SETUP=1
   scripts\ops\launchers\codex\codex.bat

Q: Slow npm/apt operations in WSL?
A: Common on first runs. The cache helps after the first execution.
   Use codex-fast.bat to skip setup and work while caching initializes.

Q: How to verify setup?
A: Run:
   scripts\ops\launchers\codex\codex.bat doctor

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ENVIRONMENT VARIABLES (optional overrides):

CODEX_SKIP_MCP_SETUP=1      Skip MCP initialization (faster startup)
CODEX_FORCE_MCP_SETUP=1     Force full MCP validation (slower but thorough)
BIOETL_WSL_DISTRO=Ubuntu    Use specific WSL distro (default: system default)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILES MODIFIED:
  • scripts/ops/launchers/codex/codex.sh       (optimized for fast startup)
  • scripts/ai/codex/helper/ensure-mcp.sh      (reduced timeout: 30s → 15s)
  • scripts/ops/launchers/codex/codex-fast.bat (NEW - fast launcher)

EOF
