# Gemini Interactive Mode - Complete Setup

## 📦 What's Installed

### Executable Scripts
```
scripts/ai/
├── gemini-interactive.sh          ← Main interactive launcher (21KB)
├── quick-gemini.sh                ← Quick command shortcuts (3.7KB)
├── setup-gemini-wsl.sh            ← Environment initialization
├── sync-agents-codex-to-gemini.sh ← Profile synchronization
├── launch-gemini.sh               ← Profile-based launcher
└── gemini.ps1                     ← PowerShell wrapper
```

### Configuration Files
```
.gemini/
├── config.toml                    ← Runtime configuration
├── settings.json                  ← MCP servers definition
└── agents/
    └── GEMINI-RUNTIME.md          ← Agent role mapping
```

### Documentation
```
scripts/ai/
├── GEMINI-WSL-SETUP.md            ← Detailed setup guide
├── INTERACTIVE-MODE.md            ← Interactive mode reference
└── INTERACTIVE-USAGE.md           ← Complete usage guide (this)
```

---

## 🚀 Quick Start

### Option 1: PowerShell (Recommended for Windows)

```powershell
cd E:\g-drive\05_AI\github\BioactivityDataAcquisition2
.\scripts\ai\gemini.ps1
```

### Option 2: WSL Bash

```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2
bash scripts/ai/gemini-interactive.sh
```

### Option 3: Windows Terminal (Preferred)

1. Open **Windows Terminal**
2. Select **Ubuntu** (or your WSL distro)
3. Run:
   ```bash
   cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2
   bash scripts/ai/gemini-interactive.sh
   ```

---

## 📋 Main Menu Options

```
┌─────────────────────────────────────────────┐
│ 🧬 GEMINI INTERACTIVE LAUNCHER - BioETL     │
└─────────────────────────────────────────────┘

1. 💬 Interactive Chat Mode
   → Chat with selected agent profile
   → Live conversation, logged to session file
   → Type 'exit' to end

2. 📋 Task/Work Mode
   → Create structured task for Gemini
   → Options: review | config | test | architecture | debug | custom
   → Auto-generates task markdown file

3. 🔍 Code Review Mode
   → Quick code review shortcuts
   → Options: staged | file | directory

4. 📊 Analysis Mode
   → Data flow | dependencies | coverage | performance
   → Quick analysis tools

5. ⚙️  Configuration & Maintenance
   → Setup | Sync | Status | Reset | MCP update

6. 📚 Help & Documentation
   → Setup guide | Profiles | Constraints | MCP config | Sessions

7. 🚪 Exit
```

---

## 💡 Common Workflows

### Workflow 1: Quick Chat with Reviewer

```bash
$ bash scripts/ai/gemini-interactive.sh

→ Select: 1 (Chat Mode)
→ Select: 1 (py-review-orchestrator)

You> Review src/bioetl/domain/model.py for type hints

Gemini (py-review-orchestrator)> [response]

You> Check if all dataclasses have __eq__

Gemini> [response]

You> exit
```

**Output:** `sessions/chat-{timestamp}.log`

---

### Workflow 2: Code Review Task

```bash
$ bash scripts/ai/gemini-interactive.sh

→ Select: 2 (Task Mode)
→ Select: 1 (Code Review)
→ Scope: 1 (Staged changes)
→ Focus: "architecture"
```

**Output:** `sessions/review-{timestamp}.md` (task file)

Then share this file with Gemini + GEMINI.md context for review.

---

### Workflow 3: Generate Missing Tests

```bash
$ bash scripts/ai/gemini-interactive.sh

→ Select: 2 (Task Mode)
→ Select: 3 (Test Generation)
→ Target coverage: 90
→ Scope: src/bioetl/domain
```

**Output:** `sessions/test-gen-{timestamp}.md` (task file)

Gemini generates pytest tests + fixtures to reach 90% coverage.

---

### Workflow 4: Architecture Analysis

```bash
$ bash scripts/ai/gemini-interactive.sh

→ Select: 2 (Task Mode)
→ Select: 4 (Architecture Analysis)
→ Focus: 2 (Dependency violations)
```

**Output:** `sessions/arch-analysis-{timestamp}.md`

Analyzes hexagonal pattern compliance, port contracts, layer isolation.

---

## 📁 Session Files

All work saved to: `docs/00-project/ai/sessions/`

| File Pattern | Type | Content |
|--------------|------|---------|
| `chat-*.log` | Chat | Conversation transcript |
| `review-*.md` | Task | Code review report |
| `config-audit-*.md` | Task | Config audit |
| `test-gen-*.md` | Task | Test generation task |
| `arch-analysis-*.md` | Task | Architecture analysis |
| `debug-*.md` | Task | Debug/fix work |

**Browse sessions from menu:** Help → List Recent Sessions

---

## 🔧 First-Time Setup

### Step 1: Initialize Environment

```bash
bash scripts/ai/setup-gemini-wsl.sh
```

**Creates:**
- `.gemini/` directory structure
- `gemini-memory.json` (persistent memory)
- `sessions/` directory for task files
- Validates MCP configuration

**Output:**
```
✓ Gemini Home: .gemini
✓ Config: config.toml
✓ MCP Settings: settings.json
✓ Node.js available
✓ UV available
✅ Gemini runtime setup complete!
```

### Step 2: Sync Agent Profiles

```bash
bash scripts/ai/sync-agents-codex-to-gemini.sh
```

**Copies:**
- `py-review-orchestrator.md`
- `py-test-swarm.md`
- `py-config-bot.md`
- `py-audit-bot.md`
- `py-debug-bot.md`
- `py-architecture-debt-bot.md`
- + others from `.codex/agents/` to `.gemini/agents/`

### Step 3: Launch Interactive Menu

```bash
bash scripts/ai/gemini-interactive.sh
```

You're ready! 🎉

---

## 🛠️ Quick Commands

### From PowerShell

```powershell
# Interactive menu (default)
.\scripts\ai\gemini.ps1

# Environment setup
.\scripts\ai\gemini.ps1 setup

# Sync profiles from Codex
.\scripts\ai\gemini.ps1 sync

# Show status
.\scripts\ai\gemini.ps1 status

# Help
.\scripts\ai\gemini.ps1 help
```

### From Bash

```bash
# Interactive menu
bash scripts/ai/gemini-interactive.sh

# Quick commands
bash scripts/ai/quick-gemini.sh interactive
bash scripts/ai/quick-gemini.sh status
bash scripts/ai/quick-gemini.sh help

# Setup
bash scripts/ai/setup-gemini-wsl.sh

# Sync profiles
bash scripts/ai/sync-agents-codex-to-gemini.sh
```

---

## 🔍 Environment Status

Check your Gemini setup:

```bash
# From PowerShell
.\scripts\ai\gemini.ps1 status

# From Bash
bash scripts/ai/quick-gemini.sh status
```

**Shows:**
- ✓ Gemini home location
- ✓ Config files (exist/missing)
- ✓ MCP settings loaded
- ✓ Memory file status
- ✓ Available profiles
- ✓ Total sessions

---

## 📚 Agent Profiles

**Available profiles** (synced from Codex):

- `py-review-orchestrator` — Code review orchestration
- `py-test-swarm` — Test generation & coverage
- `py-config-bot` — Configuration audit
- `py-architecture-debt-bot` — Architecture analysis
- `py-debug-bot` — Debug & fix tasks
- `py-audit-bot` — Read-only audits
- `py-plan-bot` — Planning & decomposition
- `py-doc-bot` — Documentation work
- + others

**Browse profiles from menu:** Help → View Agent Profiles

---

## 📖 Documentation

### Main Guides

1. **INTERACTIVE-USAGE.md** (this file)
   - Complete usage guide
   - All modes explained
   - Workflow examples
   - Troubleshooting

2. **INTERACTIVE-MODE.md**
   - Quick reference
   - Session file types
   - Tips & tricks

3. **GEMINI-WSL-SETUP.md**
   - Detailed setup
   - Configuration reference
   - MCP servers

4. **GEMINI.md**
   - Project constraints
   - Architecture rules
   - Coding standards
   - Governance

### Access from Menu

**Help → View Setup Guide** (scripts/ai/GEMINI-WSL-SETUP.md)
**Help → View Project Constraints** (GEMINI.md)

---

## ⚙️ Configuration

### Gemini Runtime Config

**File:** `.gemini/config.toml`

```toml
model = "gemini-3.5-pro"
sandbox_mode = "workspace-write"
streaming_enabled = true
web_search = "cached"
```

**Modify:**
- Change model version (gemini-pro, gemini-3.5-sonnet, etc.)
- Adjust sandbox/streaming settings

### MCP Servers

**File:** `.gemini/settings.json`

Includes:
- `memory` — Persistent context
- `filesystem` — Read/write project
- `neo4j-cypher` — Graph DB
- `docker` — Container operations
- `fetch` — HTTP requests
- `sequential-thinking` — Complex decomposition
- + others

**Modify from menu:** Maintenance → Update MCP Servers

---

## 🐛 Troubleshooting

### Problem: "Environment check failed"

```bash
bash scripts/ai/setup-gemini-wsl.sh
```

### Problem: "No profiles found"

```bash
bash scripts/ai/sync-agents-codex-to-gemini.sh
```

### Problem: "WSL not available"

- Run from WSL terminal, not PowerShell
- Check: `wsl --version`
- Or use WSL directly: `bash scripts/ai/gemini-interactive.sh`

### Problem: "MCP servers not connecting"

```bash
# Check Node.js
which node npm

# Check UV
which uvx

# Install if missing (in WSL)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs

curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Problem: "Memory file not persisting"

```bash
rm -f docs/00-project/ai/memory/gemini-memory.json
bash scripts/ai/setup-gemini-wsl.sh
```

### Problem: "Sessions not saving"

```bash
mkdir -p docs/00-project/ai/sessions
chmod 777 docs/00-project/ai/sessions
```

---

## 💻 System Requirements

- **Windows 10/11** with WSL2 (recommended)
- **WSL distro** (Ubuntu 20.04+)
- **bash** (in WSL)
- **Node.js** (for MCP servers) — script can install
- **UV** (for fetch MCP) — script can install

---

## 🎯 Next Steps

1. **First time:**
   ```bash
   bash scripts/ai/setup-gemini-wsl.sh
   ```

2. **Then:**
   ```bash
   bash scripts/ai/sync-agents-codex-to-gemini.sh
   ```

3. **Launch:**
   ```bash
   bash scripts/ai/gemini-interactive.sh
   ```

4. **Try Chat Mode:**
   - Select option 1
   - Choose profile
   - Ask questions
   - Type `exit`

5. **Try Task Mode:**
   - Select option 2
   - Choose task type
   - Follow prompts
   - Review generated task file

---

## 📞 Support

- **Setup issues:** See GEMINI-WSL-SETUP.md
- **Usage questions:** See INTERACTIVE-MODE.md
- **Constraints:** See GEMINI.md
- **MCP config:** Check .gemini/settings.json
- **Sessions:** Browse docs/00-project/ai/sessions/

---

## 📝 Version

- **Gemini Interactive Mode** v1.0
- **Created:** 2026-04-14
- **Project:** BioETL
- **Status:** Ready for production use

**Happy coding! 🧬**
