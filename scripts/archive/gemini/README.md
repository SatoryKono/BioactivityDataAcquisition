# Gemini Consolidated - Single Entry Point

## 🎯 Overview

All Gemini setup and execution scripts consolidated into **`scripts/gemini/`** with a single entry point: **`./scripts/gemini`**

---

## 🚀 Quick Start

### First Time

```bash
cd E:\g-drive\05_AI\github\BioactivityDataAcquisition2

# Initialize
bash scripts/gemini/gemini setup

# Sync profiles from Codex
bash scripts/gemini/gemini sync

# Launch interactive menu
bash scripts/gemini/gemini
```

### From Windows PowerShell

```powershell
cd E:\g-drive\05_AI\github\BioactivityDataAcquisition2
wsl bash scripts/gemini/gemini
```

### From Windows Terminal (Recommended)

```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2
bash scripts/gemini/gemini
```

---

## 📁 Directory Structure

```
scripts/gemini/
├── gemini                    ← MAIN ENTRY POINT (dispatcher)
├── lib/
│   ├── utils.sh             ← Shared utilities
│   ├── setup.sh             ← Environment initialization
│   ├── sync.sh              ← Profile sync
│   ├── status.sh            ← Status reporting
│   ├── reset.sh             ← Reset environment
│   ├── chat.sh              ← Chat mode
│   ├── interactive.sh       ← Interactive menu
│   └── tasks/
│       ├── review.sh        ← Code review task
│       ├── test.sh          ← Test generation task
│       ├── config.sh        ← Config audit task
│       ├── architecture.sh  ← Architecture analysis
│       └── debug.sh         ← Debug/fix task
└── docs/
    ├── 00-START-HERE.md     ← Start here!
    ├── README-INTERACTIVE.md
    ├── INTERACTIVE-USAGE.md
    ├── CHEAT-SHEET.md
    ├── INTERACTIVE-MODE.md
    └── GEMINI-WSL-SETUP.md
```

---

## 💻 Commands

### Main Entry Point

```bash
bash scripts/gemini/gemini [command] [options]
```

### Available Commands

```
interactive       Launch interactive menu (default)
setup            Initialize environment
sync             Sync profiles from Codex
chat [profile]   Chat with agent profile
review [scope]   Create code review task
test [%] [scope] Create test generation task
config [scope]   Create configuration audit task
architecture [f] Create architecture analysis task
debug [issue]    Create debug/fix task
status           Show environment status
reset            Clear memory and reinitialize
help             Show help
version          Show version info
```

### Quick Examples

```bash
# Interactive menu (default)
bash scripts/gemini/gemini

# Setup
bash scripts/gemini/gemini setup

# Chat with specific profile
bash scripts/gemini/gemini chat py-review-orchestrator

# Code review for staged changes
bash scripts/gemini/gemini review staged

# Generate tests with 90% coverage for domain
bash scripts/gemini/gemini test 90 domain

# Config audit
bash scripts/gemini/gemini config all

# Architecture analysis (debt focus)
bash scripts/gemini/gemini architecture debt

# Debug a specific issue
bash scripts/gemini/gemini debug "AttributeError in loader"

# Check status
bash scripts/gemini/gemini status
```

---

## 🏗️ Architecture

### Single Entry Point: `gemini`

```bash
gemini [command] [args]
  ↓
Dispatches to appropriate lib/ script
  ↓
lib/{command}.sh or lib/tasks/{task}.sh
  ↓
Executes with shared utils (lib/utils.sh)
```

### Shared Utilities (`lib/utils.sh`)

- Color printing functions
- Path management (project root, .gemini home, etc.)
- Environment validation
- Profile listing
- Session file creation

### Modular Scripts (`lib/*.sh`)

Each script is **self-contained**:
- Sources utils.sh for shared functions
- Handles its own logic
- Creates output files (sessions, tasks)
- Independent error handling

### Task Scripts (`lib/tasks/*.sh`)

Each task type creates a **structured markdown file**:
- Code review task → `review-{ts}.md`
- Test generation → `test-gen-{ts}.md`
- Config audit → `config-audit-{ts}.md`
- Architecture analysis → `arch-analysis-{ts}.md`
- Debug/fix → `debug-{ts}.md`

All output saved to: `docs/00-project/ai/sessions/`

---

## 🎯 Main Menu Modes (Interactive)

From: `bash scripts/gemini/gemini` or `bash scripts/gemini/gemini interactive`

```
1. 💬 Interactive Chat Mode
   • Select agent profile
   • Type prompts/questions
   • Get real-time responses
   • Output: chat-{ts}.log

2. 📋 Task/Work Mode
   • Code Review
   • Configuration Audit
   • Test Generation
   • Architecture Analysis
   • Debug/Fix
   • Custom Profile
   • Output: task-{ts}.md

3. 🔍 Code Review Mode
   • Quick review shortcuts

4. 📊 Analysis Mode
   • Data flow, dependencies, coverage

5. ⚙️ Configuration & Maintenance
   • Setup, Sync, Status, Reset

6. 📚 Help & Documentation
   • Guides, Profiles, Sessions

7. 🚪 Exit
```

---

## 📊 File Organization

### Before (Scattered)
```
scripts/ai/
├── gemini-interactive.sh
├── quick-gemini.sh
├── setup-gemini-wsl.sh
├── sync-agents-codex-to-gemini.sh
├── launch-gemini.sh
├── gemini.ps1
└── (6 doc files)
```

### After (Consolidated)
```
scripts/gemini/
├── gemini                    ← Single entry point
├── lib/
│   ├── utils.sh             ← Shared (sourced by all)
│   ├── setup.sh
│   ├── sync.sh
│   ├── status.sh
│   ├── reset.sh
│   ├── chat.sh
│   ├── interactive.sh
│   └── tasks/
│       ├── review.sh
│       ├── test.sh
│       ├── config.sh
│       ├── architecture.sh
│       └── debug.sh
└── docs/
    └── (6 doc files)
```

**Benefits:**
- ✓ Single entry point (`./scripts/gemini/gemini`)
- ✓ Modular library structure (`lib/`)
- ✓ Clear task organization (`tasks/`)
- ✓ Shared utilities (`utils.sh`)
- ✓ Documented organization

---

## 🔄 Workflow Example

### Create Code Review Task

```bash
bash scripts/gemini/gemini review staged
```

**Flow:**
1. Entry point `gemini` script received `review staged`
2. Dispatcher calls `cmd_review()` with args
3. `cmd_review()` calls `lib/tasks/review.sh staged`
4. `review.sh` sources `lib/utils.sh`
5. Uses `get_sessions_dir()`, `create_session_file()`, etc.
6. Creates `review-{ts}.md` task file
7. Prints success message with file path

---

## ✨ Features

### Single Entry Point
- ✓ One command: `bash scripts/gemini/gemini`
- ✓ All functionality accessible from one place
- ✓ Discoverability via `help` subcommand

### Modular Architecture
- ✓ `lib/utils.sh` — shared functions (DRY principle)
- ✓ `lib/{command}.sh` — independent commands
- ✓ `lib/tasks/{task}.sh` — task templates
- ✓ Easy to extend with new commands

### Clear Organization
- ✓ Library scripts in `lib/`
- ✓ Task scripts in `lib/tasks/`
- ✓ Documentation in `docs/`
- ✓ Entry point at root

### Session Management
- ✓ All output to `docs/.../ai/sessions/`
- ✓ Timestamped files
- ✓ Browsable from menu
- ✓ Accessible programmatically

---

## 📚 Documentation

All documentation files included in `scripts/gemini/docs/`:

- **00-START-HERE.md** — 2-minute overview (START HERE!)
- **README-INTERACTIVE.md** — Quick start + workflows
- **INTERACTIVE-USAGE.md** — Complete 20-minute guide
- **CHEAT-SHEET.md** — Fast reference
- **INTERACTIVE-MODE.md** — Quick summary
- **GEMINI-WSL-SETUP.md** — Technical details

Access from menu: **Help → View Setup Guide**

---

## 🔧 System Requirements

- ✓ Windows 10/11 with WSL2
- ✓ WSL distro (Ubuntu 20.04+)
- ✓ bash
- ✓ Node.js (MCP servers) — auto-installed by setup
- ✓ UV (fetch MCP) — auto-installed by setup

---

## 🎓 Learning Path

### 5 Minutes
1. Read: `scripts/gemini/docs/00-START-HERE.md`
2. Run: `bash scripts/gemini/gemini setup`
3. Run: `bash scripts/gemini/gemini sync`
4. Run: `bash scripts/gemini/gemini` (interactive menu)

### 20 Minutes
1. Try: Chat mode (menu 1)
2. Try: Task mode (menu 2) - each task type
3. Review: Session files in `docs/.../ai/sessions/`
4. Read: `scripts/gemini/docs/INTERACTIVE-USAGE.md`

### Advanced
1. Study: `lib/utils.sh` (shared functions)
2. Explore: Individual lib scripts
3. Customize: Add new commands if needed
4. Extend: Create new task types

---

## 📍 Migration Notes

If you were using old paths:

**Old:**
```bash
bash scripts/ai/gemini-interactive.sh
bash scripts/ai/quick-gemini.sh status
```

**New:**
```bash
bash scripts/gemini/gemini              # interactive
bash scripts/gemini/gemini status       # status
```

**Old scripts still available in `scripts/ai/` but deprecated.**

---

## ✅ Checklist

- [x] Single entry point created (`gemini`)
- [x] Library structure organized (`lib/`)
- [x] Task commands implemented (`lib/tasks/`)
- [x] Utilities extracted (`lib/utils.sh`)
- [x] All functionality preserved
- [x] Documentation maintained
- [x] Session management working
- [x] Ready for production use

---

## 🚀 Next Steps

1. **Run setup:**
   ```bash
   bash scripts/gemini/gemini setup
   ```

2. **Sync profiles:**
   ```bash
   bash scripts/gemini/gemini sync
   ```

3. **Launch interactive:**
   ```bash
   bash scripts/gemini/gemini
   ```

4. **Create alias (optional):**
   ```bash
   alias gemini='bash /path/to/scripts/gemini/gemini'
   ```

---

**Status:** ✅ Complete - Single consolidated entry point ready!

**Created:** 2026-04-14  
**Version:** 1.0 (Consolidated)
