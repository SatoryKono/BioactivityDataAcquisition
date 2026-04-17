#!/usr/bin/env bash

# Quick reference card for Gemini consolidated setup

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                    🧬 GEMINI CONSOLIDATED - QUICK REFERENCE 🧬              ║
║                                                                              ║
║                          Single Entry Point Setup                            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 SINGLE ENTRY POINT

  bash scripts/gemini/gemini [command] [options]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 MAIN COMMANDS

  gemini                    Launch interactive menu (default)
  gemini setup              Initialize environment
  gemini sync               Sync profiles from Codex
  gemini status             Check environment status
  gemini help               Show help
  gemini version            Show version

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 CHAT MODE

  gemini chat                         Chat with default profile (py-review-orchestrator)
  gemini chat py-test-swarm          Chat with specific profile
  gemini chat py-config-bot          Any profile available

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 TASK COMMANDS

  gemini review staged                Code review for staged changes
  gemini review file path/to/file    Code review for specific file
  gemini review directory path/dir   Code review for directory
  gemini review project              Code review entire project

  gemini test 85                     Test generation, 85% coverage (default)
  gemini test 90 domain              Test generation, 90% coverage, domain scope
  gemini test 85 all                 Test generation, all scopes

  gemini config all                  Configuration audit, all configs
  gemini config configs              Configuration audit, configs only
  gemini config specific             Configuration audit, specific

  gemini architecture debt           Architecture analysis, technical debt focus
  gemini architecture dependencies   Architecture analysis, dependency focus
  gemini architecture layers         Architecture analysis, layer isolation
  gemini architecture ports          Architecture analysis, port coverage

  gemini debug                       Debug/fix task (prompts for details)
  gemini debug "Issue description"  Debug/fix task with description

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 DIRECTORY STRUCTURE

  scripts/gemini/
  ├── gemini                          ← MAIN ENTRY POINT
  ├── lib/
  │   ├── utils.sh                   ← Shared utilities (sourced by all)
  │   ├── setup.sh
  │   ├── sync.sh
  │   ├── status.sh
  │   ├── reset.sh
  │   ├── chat.sh
  │   ├── interactive.sh             ← Full menu system
  │   └── tasks/
  │       ├── review.sh
  │       ├── test.sh
  │       ├── config.sh
  │       ├── architecture.sh
  │       └── debug.sh
  └── docs/
      └── (6 documentation files)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ QUICK WORKFLOWS

  FIRST TIME:
    bash scripts/gemini/gemini setup
    bash scripts/gemini/gemini sync
    bash scripts/gemini/gemini

  CODE REVIEW:
    bash scripts/gemini/gemini review staged
    [share file + GEMINI.md with Gemini]

  GENERATE TESTS:
    bash scripts/gemini/gemini test 90 domain
    [share file with Gemini]

  QUICK CHAT:
    bash scripts/gemini/gemini chat
    [ask questions, type 'exit']

  CHECK STATUS:
    bash scripts/gemini/gemini status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 OUTPUT LOCATIONS

  Session Files:  docs/00-project/ai/sessions/
  Memory File:    docs/00-project/ai/memory/gemini-memory.json
  Config:         .gemini/config.toml
  MCP Settings:   .gemini/settings.json
  Profiles:       .gemini/agents/py-*.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎪 INTERACTIVE MENU (FROM: bash scripts/gemini/gemini)

  1. 💬 Interactive Chat Mode
  2. 📋 Task/Work Mode (6 task types)
  3. 🔍 Code Review Mode
  4. 📊 Analysis Mode
  5. ⚙️  Configuration & Maintenance
  6. 📚 Help & Documentation
  7. 🚪 Exit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 DOCUMENTATION

  Start Here:        scripts/gemini/docs/00-START-HERE.md
  Complete Guide:    scripts/gemini/docs/INTERACTIVE-USAGE.md
  Quick Reference:   scripts/gemini/docs/CHEAT-SHEET.md
  Setup Details:     scripts/gemini/docs/GEMINI-WSL-SETUP.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 FEATURES

  ✓ Single entry point (no more scattered scripts)
  ✓ Modular library structure
  ✓ Shared utilities (DRY principle)
  ✓ 9+ agent profiles
  ✓ 6 predefined task types
  ✓ Interactive menu system
  ✓ Session logging
  ✓ Memory persistence
  ✓ 21 MCP servers
  ✓ Full documentation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 GET STARTED NOW

  1. bash scripts/gemini/gemini setup
  2. bash scripts/gemini/gemini sync
  3. bash scripts/gemini/gemini
  4. Select: 1 (Chat Mode)
  5. Ask: A question
  6. Type: exit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: ✅ Complete - Consolidated and ready!
Version: 1.0
Created: 2026-04-14

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF
