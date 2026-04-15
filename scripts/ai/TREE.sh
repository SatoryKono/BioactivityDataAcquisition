#!/bin/bash
# tree-gemini-interactive.sh
# Quick visual tree of Gemini Interactive installation

cat << 'EOF'

╔═══════════════════════════════════════════════════════════════════════════════╗
║                 🧬 GEMINI INTERACTIVE MODE - FILE STRUCTURE 🧬               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

BioactivityDataAcquisition2/
│
├── .gemini/                                        [CONFIG ROOT]
│   ├── config.toml                                 • Runtime config
│   ├── settings.json                               • MCP servers (21 servers)
│   ├── .env.sh                                     • Environment setup (created by setup)
│   └── agents/
│       ├── GEMINI-RUNTIME.md                       • Agent role mapping
│       └── py-*.md (9 profiles)                    • Synced from Codex
│
├── docs/00-project/ai/
│   ├── memory/
│   │   └── gemini-memory.json                      • Persistent memory file
│   └── sessions/                                   [OUTPUT DIRECTORY]
│       ├── chat-1713100200.log                     • Chat transcripts
│       ├── review-1713100300.md                    • Code review tasks
│       ├── config-audit-1713100400.md             • Config audit tasks
│       ├── test-gen-1713100500.md                 • Test generation tasks
│       ├── arch-analysis-1713100600.md            • Architecture analysis
│       ├── debug-1713100700.md                    • Debug/fix tasks
│       └── ...more session files...
│
├── scripts/ai/                                     [LAUNCHER & DOCS ROOT]
│   ├── 00-START-HERE.md ⭐ START HERE!
│   ├── README-INTERACTIVE.md                       • Setup + Quick start
│   ├── INTERACTIVE-USAGE.md                        • Complete usage guide
│   ├── INTERACTIVE-MODE.md                         • Quick reference
│   ├── CHEAT-SHEET.md                              • Fast lookup
│   ├── GEMINI-WSL-SETUP.md                         • Technical setup
│   │
│   ├── gemini-interactive.sh ⭐ MAIN LAUNCHER
│   │   └─ Interactive menu (21.6 KB)
│   │      • Menu system (7 modes)
│   │      • Chat mode (live conversation)
│   │      • Task mode (6 types)
│   │      • Environment check
│   │      • Session logging
│   │
│   ├── quick-gemini.sh
│   │   └─ Quick commands (3.7 KB)
│   │      • interactive, review, chat, task
│   │      • status, setup, sync, help
│   │
│   ├── gemini.ps1 ⭐ WINDOWS LAUNCHER
│   │   └─ PowerShell wrapper (6.4 KB)
│   │      • Cross-platform launch
│   │      • WSL integration
│   │      • Colored output
│   │      • Status check
│   │
│   ├── setup-gemini-wsl.sh
│   │   └─ Environment setup (3.4 KB)
│   │      • Create .gemini/ structure
│   │      • Initialize memory
│   │      • Validate MCP servers
│   │      • Setup .env.sh
│   │
│   ├── sync-agents-codex-to-gemini.sh
│   │   └─ Profile sync (1.2 KB)
│   │      • Copy 9 profiles from Codex
│   │      • Maintain compatibility
│   │
│   └── launch-gemini.sh
│       └─ Profile launcher (2.2 KB)
│          • Load specific profiles
│          • Role assignment
│          • Context passing
│
└── GEMINI.md                                       • Project constraints
                                                    • Architecture rules

═══════════════════════════════════════════════════════════════════════════════

📊 QUICK STATS

Scripts:         6 executable files (~40 KB total)
Documentation:   6 guides + this tree (~60 KB total)
Configuration:   3 config files (.gemini/)
Output:          Unlimited session files (docs/.../ai/sessions/)

═══════════════════════════════════════════════════════════════════════════════

🚀 HOW TO USE

From PowerShell:
  .\scripts\ai\gemini.ps1

From WSL Bash:
  bash scripts/ai/gemini-interactive.sh

From Windows Terminal (RECOMMENDED):
  → Open Terminal
  → Select WSL tab
  → bash scripts/ai/gemini-interactive.sh

═══════════════════════════════════════════════════════════════════════════════

📚 DOCUMENTATION ROADMAP

1️⃣  START HERE (2 min)
    → scripts/ai/00-START-HERE.md

2️⃣  QUICK START (5 min)
    → scripts/ai/README-INTERACTIVE.md

3️⃣  COMPLETE GUIDE (20 min)
    → scripts/ai/INTERACTIVE-USAGE.md

4️⃣  QUICK REFERENCE (anytime)
    → scripts/ai/CHEAT-SHEET.md

5️⃣  TECHNICAL DETAILS
    → scripts/ai/GEMINI-WSL-SETUP.md

═══════════════════════════════════════════════════════════════════════════════

🎯 MAIN MENU OPTIONS

┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. 💬 INTERACTIVE CHAT MODE                                                │
│    • Select agent profile                                                  │
│    • Type questions/prompts                                               │
│    • Get real-time responses                                              │
│    • Output: chat-{timestamp}.log                                         │
│                                                                            │
│ 2. 📋 TASK/WORK MODE                                                      │
│    • Code Review (staged/file/directory/project)                          │
│    • Configuration Audit                                                   │
│    • Test Generation (target %)                                           │
│    • Architecture Analysis                                                │
│    • Debug/Fix Task                                                        │
│    • Custom Profile                                                        │
│    • Output: {task-type}-{timestamp}.md                                   │
│                                                                            │
│ 3. 🔍 CODE REVIEW MODE                                                    │
│    • Quick review shortcuts                                               │
│                                                                            │
│ 4. 📊 ANALYSIS MODE                                                       │
│    • Data flow, dependencies, coverage, performance                       │
│                                                                            │
│ 5. ⚙️  CONFIGURATION & MAINTENANCE                                        │
│    • Setup, Sync, Status, Reset, Update MCP                               │
│                                                                            │
│ 6. 📚 HELP & DOCUMENTATION                                                │
│    • Guides, Profiles, Constraints, Sessions                              │
│                                                                            │
│ 7. 🚪 EXIT                                                                 │
│    • Close menu                                                            │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════

⚡ QUICK WORKFLOWS

CHAT SESSION (30 seconds):
  1. Launch → 1 (Chat) → Select profile → Ask → Type 'exit'

CODE REVIEW (1 minute):
  1. Launch → 2 (Task) → 1 (Review) → Choose scope → Done!

TEST GENERATION (1-2 minutes):
  1. Launch → 2 (Task) → 3 (Test) → Enter coverage → Done!

═══════════════════════════════════════════════════════════════════════════════

✅ INITIALIZATION CHECKLIST

[ ] Read: scripts/ai/00-START-HERE.md (2 min)
[ ] Run: bash scripts/ai/setup-gemini-wsl.sh (1 min)
[ ] Run: bash scripts/ai/sync-agents-codex-to-gemini.sh (1 min)
[ ] Launch: bash scripts/ai/gemini-interactive.sh (now!)
[ ] Try: Chat mode with any profile
[ ] Explore: Other menu options

═══════════════════════════════════════════════════════════════════════════════

🔗 KEY DIRECTORIES

.gemini/                     → Configuration root
docs/.../ai/memory/          → Persistent memory
docs/.../ai/sessions/        → Session output (chat + tasks)
scripts/ai/                  → Launchers + documentation

═══════════════════════════════════════════════════════════════════════════════

📞 QUICK HELP

"How do I launch?"           → bash scripts/ai/gemini-interactive.sh
"Where are my sessions?"     → docs/00-project/ai/sessions/
"How do I...create a task?"  → Menu 2, select task type
"I'm stuck"                  → Read scripts/ai/00-START-HERE.md
"Need quick ref?"            → See scripts/ai/CHEAT-SHEET.md
"Full guide?"                → Read scripts/ai/INTERACTIVE-USAGE.md

═══════════════════════════════════════════════════════════════════════════════

Status: ✅ COMPLETE - Ready for use!

Created: 2026-04-14
Version: 1.0 (Production Ready)

═══════════════════════════════════════════════════════════════════════════════

EOF
