# Gemini Interactive Mode - Complete Usage Guide

## Overview

Gemini Interactive Mode provides a **menu-driven interface** for launching Gemini agent sessions from WSL with full project context, MCP integration, and session management.

**Key Features:**
- ✓ Interactive menu navigation
- ✓ Agent profile selection
- ✓ Multiple task modes (review, config, test, etc.)
- ✓ Automatic session logging
- ✓ Environment validation
- ✓ Memory persistence
- ✓ MCP server integration

---

## Installation & First Run

### 1. Windows PowerShell (Recommended)

From PowerShell in project root:

```powershell
.\scripts\ai\gemini.ps1 setup
.\scripts\ai\gemini.ps1 sync
.\scripts\ai\gemini.ps1
```

### 2. WSL Bash

From WSL terminal in project root:

```bash
bash scripts/ai/setup-gemini-wsl.sh
bash scripts/ai/sync-agents-codex-to-gemini.sh
bash scripts/ai/gemini-interactive.sh
```

### 3. Windows Terminal (Preferred)

Open Windows Terminal, select WSL tab:

```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2
bash scripts/ai/gemini-interactive.sh
```

---

## Main Menu

```
╔════════════════════════════════════════════════════════════════════╗
║                 🧬 GEMINI INTERACTIVE LAUNCHER                    ║
╚════════════════════════════════════════════════════════════════════╝

▶ Main Menu

  1. 💬 Interactive Chat Mode
  2. 📋 Task/Work Mode
  3. 🔍 Code Review Mode
  4. 📊 Analysis Mode
  5. ⚙️  Configuration & Maintenance
  6. 📚 Help & Documentation
  7. 🚪 Exit

Select option [1-7]:
```

---

## Mode 1: Interactive Chat Mode

### What It Does
- Select an agent profile
- Start interactive conversation with Gemini
- All inputs/outputs logged to session file
- Type `exit` or `quit` to end

### Step-by-Step

```
Select option [1-7]: 1

▶ Available Agent Profiles

   1. py-review-orchestrator       Code review orchestration
   2. py-test-swarm                Test generation & coverage
   3. py-config-bot                Configuration audit
   4. py-architecture-debt-bot     Architecture analysis
   5. py-debug-bot                 Debug & fix tasks
   6. py-audit-bot                 Read-only audits

   0. << Back to Main Menu

Select profile [0-9]: 1
```

### Chat Session Example

```
▶ Chat Mode - py-review-orchestrator

✓ Session log: /mnt/.../docs/.../ai/sessions/chat-1713100200.log
ℹ Type 'exit' or 'quit' to end session

----------------------------------------

You> Review the domain layer for type hints compliance

Gemini (py-review-orchestrator)>
  [Processing with profile: py-review-orchestrator]
  [Using MCP: .gemini/settings.json]
  [Query: Review the domain layer for type hints compliance]

You> Check if all value objects have __eq__ and __hash__

Gemini (py-review-orchestrator)>
  [Analysis in progress...]

You> exit

✓ Session saved to: .../chat-1713100200.log
```

### Session File Location
`docs/00-project/ai/sessions/chat-{timestamp}.log`

---

## Mode 2: Task/Work Mode

### Available Tasks

#### a) Code Review
```
▶ Task/Work Mode

  1. Code Review (py-review-orchestrator)
  2. Configuration Audit (py-config-bot)
  3. Test Generation (py-test-swarm)
  4. Architecture Analysis (py-architecture-debt-bot)
  5. Data Engineering (py-debug-bot)
  6. Custom Profile

Select task [0-6]: 1
```

**Scope Options:**
1. Staged changes (`git diff --staged`)
2. Specific file (provide path)
3. Directory (provide path)
4. Entire project

**Review Focus:**
- architecture → Hexagonal pattern, layer isolation, ports
- tests → Coverage ≥85%, test quality, fixtures
- style → Code style, naming, formatting
- all → Comprehensive review

**Output:** `docs/.../sessions/review-{timestamp}.md`

#### b) Configuration Audit
```
Select task [0-6]: 2
Audit scope (configs/all/specific) [all]: configs
```

**Checks:**
- YAML syntax and structure
- Medallion architecture alignment
- Data loading strategies (null vs full_scan_only)
- Parameter validation

**Output:** `docs/.../sessions/config-audit-{timestamp}.md`

#### c) Test Generation
```
Select task [0-6]: 3
Target coverage (%) [85]: 90
Scope (src/bioetl/application, src/bioetl/domain, all) [application]: domain
```

**Generates:**
- Unit tests for domain logic
- Integration test templates
- VCR cassettes for HTTP calls
- Test fixtures in `tests/fixtures/`

**Output:** `docs/.../sessions/test-gen-{timestamp}.md`

#### d) Architecture Analysis
```
Select task [0-6]: 4

Analysis focus:
  1. Technical debt
  2. Dependency violations
  3. Layer isolation
  4. Port coverage

Select focus [1-4]: 3
```

**Analysis Areas:**
- Layer isolation (domain → application → infrastructure)
- Port contracts (all external deps abstracted)
- Dependency injection (constructor injection only)
- Domain purity (no I/O in domain)

**Output:** `docs/.../sessions/arch-analysis-{timestamp}.md`

#### e) Debug/Fix Task
```
Select task [0-6]: 5
Issue/Bug description: AttributeError in data loading pipeline
Affected file/module (optional): src/bioetl/infrastructure/adapters/loader.py
```

**Creates:**
- Issue description
- Affected file scope
- Fix implementation
- Test updates

**Output:** `docs/.../sessions/debug-{timestamp}.md`

#### f) Custom Profile
```
Select task [0-6]: 6

Available Agent Profiles
  1. py-review-orchestrator
  2. py-test-swarm
  ...

Select profile (by number): 2
Task description: Generate integration tests for Neo4j adapter
```

**Output:** `docs/.../sessions/custom-{timestamp}.md`

---

## Mode 3: Code Review Mode (Quick)

Quick shortcuts without task file creation:

```
Select option [1-7]: 3

▶ Code Review Mode (Quick)

  1. Review staged changes
  2. Review specific file
  3. Review directory
  0. << Back to Main Menu

Select [0-3]: 1
```

**Best for:** Quick, ad-hoc reviews without formal task file.

---

## Mode 4: Analysis Mode

Specialized analysis tools:

```
Select option [1-7]: 4

▶ Analysis Mode

  1. Data Flow Analysis (medallion architecture)
  2. Dependency Analysis
  3. Test Coverage Analysis
  4. Performance Analysis
  0. << Back to Main Menu

Select [0-4]: 1
```

---

## Mode 5: Configuration & Maintenance

### Initialize Gemini Environment
```
Runs: scripts/ai/setup-gemini-wsl.sh

Creates:
  - .gemini/agents/ and .gemini/skills/
  - .gemini/config.toml
  - .gemini/settings.json
  - docs/.../ai/memory/gemini-memory.json
  - docs/.../ai/sessions/

Validates:
  - MCP server configuration
  - Node.js availability
  - UV availability
```

### Sync Agent Profiles
```
Runs: scripts/ai/sync-agents-codex-to-gemini.sh

Copies from .codex/agents/ to .gemini/agents/:
  ✓ py-audit-bot.md
  ✓ py-architecture-debt-bot.md
  ✓ py-config-bot.md
  ✓ py-debug-bot.md
  ✓ py-doc-bot.md
  ✓ py-plan-bot.md
  ✓ py-test-bot.md
  ✓ py-test-swarm.md
  ✓ py-review-orchestrator.md
```

### View Environment Status
```
Shows:
  ✓ Gemini Home location
  ✓ Config file status
  ✓ MCP settings status
  ✓ Memory file status
  ✓ Total agent profiles
  ✓ Total sessions
```

### Clear Memory & Reset
```
⚠ Warning: This will clear all memory

Deletes: gemini-memory.json
Reinitializes: Full Gemini environment
Use when: Fresh start needed, memory corrupted
```

### Update MCP Servers
```
Edit: .gemini/settings.json

Modify:
  - MCP server versions
  - Command paths
  - Environment variables
  - New servers

Then restart Gemini.
```

---

## Mode 6: Help & Documentation

### View Setup Guide
```
Opens: scripts/ai/GEMINI-WSL-SETUP.md
Shows: Complete setup instructions
```

### View Agent Profiles
```
Lists: All available py-* profiles
Shows: Profile names (descriptions from headers)
```

### View Project Constraints
```
Opens: GEMINI.md
Shows: Architecture rules, coding standards, governance
```

### View MCP Configuration
```
Opens: .gemini/settings.json
Shows: All configured MCP servers
```

### List Recent Sessions
```
Shows: Last 10 sessions with timestamps
Browse: Open session file to review
```

---

## Session Files & Management

### Location
```
docs/00-project/ai/sessions/
```

### File Types

| Pattern | Type | Content |
|---------|------|---------|
| `chat-{ts}.log` | Chat | Conversation transcript |
| `review-{ts}.md` | Task | Code review report |
| `config-audit-{ts}.md` | Task | Config audit report |
| `test-gen-{ts}.md` | Task | Generated tests |
| `arch-analysis-{ts}.md` | Task | Architecture analysis |
| `debug-{ts}.md` | Task | Debug/fix work |
| `custom-{ts}.md` | Task | Custom work |

### Example Session Timeline
```
2026-04-14 10:05:12  chat-1713100200.log
2026-04-14 10:12:34  review-1713100300.md
2026-04-14 10:15:56  config-audit-1713100400.md
2026-04-14 10:22:11  test-gen-1713100500.md
2026-04-14 10:28:45  arch-analysis-1713100600.md
```

### Accessing Sessions
1. From Help menu → "List Recent Sessions"
2. Or browse directly: `docs/00-project/ai/sessions/`
3. Open with: `less`, `cat`, or text editor

---

## Quick Commands

### PowerShell

```powershell
# Launch interactive menu
.\scripts\ai\gemini.ps1

# Setup
.\scripts\ai\gemini.ps1 setup

# Sync profiles
.\scripts\ai\gemini.ps1 sync

# Status
.\scripts\ai\gemini.ps1 status

# Help
.\scripts\ai\gemini.ps1 help
```

### Bash (WSL)

```bash
# Launch interactive menu
bash scripts/ai/gemini-interactive.sh

# Quick commands
bash scripts/ai/quick-gemini.sh interactive
bash scripts/ai/quick-gemini.sh status
bash scripts/ai/quick-gemini.sh help

# Setup
bash scripts/ai/setup-gemini-wsl.sh

# Sync
bash scripts/ai/sync-agents-codex-to-gemini.sh
```

---

## Workflow Examples

### Example 1: Code Review Session

```
Goal: Review staged changes for architecture compliance

1. Launch: .\scripts\ai\gemini.ps1

2. Select: 2 (Task/Work Mode)

3. Select: 1 (Code Review)

4. Scope: 1 (Staged changes)

5. Focus: "architecture"

6. Task file created: sessions/review-{ts}.md

7. Share with Gemini:
   - Load GEMINI.md for constraints
   - Reference .gemini/agents/py-review-orchestrator.md
   - Analyze staged changes
   - Generate report
```

### Example 2: Test Coverage Generation

```
Goal: Generate missing tests for domain layer to reach 90% coverage

1. Launch: bash scripts/ai/gemini-interactive.sh

2. Select: 2 (Task/Work Mode)

3. Select: 3 (Test Generation)

4. Target: 90
5. Scope: src/bioetl/domain

6. Task file created: sessions/test-gen-{ts}.md

7. Share with Gemini:
   - Reference GEMINI.md section 5 (Testing)
   - Load py-test-swarm profile
   - Generate pytest code
   - Include VCR fixtures
   - Create test files
```

### Example 3: Interactive Architecture Brainstorm

```
Goal: Discuss potential improvements to medallion pipeline

1. Launch: .\scripts\ai\gemini.ps1

2. Select: 1 (Interactive Chat)

3. Profile: py-architecture-debt-bot

4. Chat:
   You> How can we optimize the bronze→silver merge strategy?
   Gemini> [response]
   
   You> What about checkpointing for fault tolerance?
   Gemini> [response]
   
   You> Show an example implementation
   Gemini> [code example]
   
   You> exit

5. Session logged: chat-{ts}.log
```

---

## Environment Setup (First Time)

### Prerequisites
- ✓ WSL (Windows Subsystem for Linux) installed
- ✓ bash available in WSL
- ✓ Node.js (for MCP servers) — or let setup install it
- ✓ UV (for fetch MCP) — or let setup install it

### Quick Setup (Recommended)

**From Windows PowerShell:**
```powershell
cd E:\g-drive\05_AI\github\BioactivityDataAcquisition2
.\scripts\ai\gemini.ps1 setup
.\scripts\ai\gemini.ps1 sync
.\scripts\ai\gemini.ps1
```

**From WSL bash:**
```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2
bash scripts/ai/setup-gemini-wsl.sh
bash scripts/ai/sync-agents-codex-to-gemini.sh
bash scripts/ai/gemini-interactive.sh
```

---

## Troubleshooting

### Issue: "Environment check failed"

**Solution:**
```bash
bash scripts/ai/setup-gemini-wsl.sh
```

### Issue: "No profiles found"

**Solution:**
```bash
bash scripts/ai/sync-agents-codex-to-gemini.sh
```

### Issue: "WSL not available"

**Solution:**
- Ensure WSL2 installed: `wsl --version`
- Run commands in WSL terminal, not PowerShell

### Issue: "MCP servers not connecting"

**Solution:**
```bash
# Check Node.js
which node npm

# Check UV
which uvx

# If missing, install in WSL:
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs

curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Issue: "Memory file not persisting"

**Solution:**
```bash
rm -f docs/00-project/ai/memory/gemini-memory.json
bash scripts/ai/setup-gemini-wsl.sh
```

### Issue: "Sessions not saving"

**Solution:**
```bash
mkdir -p docs/00-project/ai/sessions
chmod 777 docs/00-project/ai/sessions
```

---

## Tips & Best Practices

### Terminal Setup
- Use **Windows Terminal** with WSL profile for best experience
- Maximize terminal width (100+ columns) for menu formatting
- Use **Ctrl+Shift+C/V** for copy/paste in Windows Terminal

### Session Management
- Review `sessions/` directory regularly
- Archive old sessions: `mkdir -p archive && mv sessions/*.log archive/`
- Create notes files alongside sessions for context

### Profile Selection
- **py-review-orchestrator** — Use for code reviews, orchestration
- **py-test-swarm** — Use for test generation
- **py-config-bot** — Use for configuration work
- **py-audit-bot** — Use for read-only analysis
- **py-debug-bot** — Use for bug fixes

### MCP Context
- All MCP servers load automatically via `.gemini/settings.json`
- Memory persists in `gemini-memory.json`
- Filesystem MCP mounts entire project root

### Performance
- First launch may take 15-30s to initialize MCP servers
- Subsequent launches faster (servers cached)
- Long task processing depends on model response time

---

## Next Steps

1. **First time:**
   ```bash
   bash scripts/ai/setup-gemini-wsl.sh
   ```

2. **Launch interactive:**
   ```bash
   bash scripts/ai/gemini-interactive.sh
   ```

3. **Try Chat Mode:**
   - Select profile
   - Ask questions
   - Type `exit` to end

4. **Try Task Mode:**
   - Select code review
   - Choose staged changes
   - Let it create task file

5. **Review results:**
   - Check `sessions/` directory
   - Open task file from menu (Help → List Recent Sessions)

---

## References

- `.gemini/config.toml` — Runtime config
- `.gemini/settings.json` — MCP servers
- `.gemini/agents/GEMINI-RUNTIME.md` — Agent role mapping
- `GEMINI.md` — Project constraints
- `scripts/ai/GEMINI-WSL-SETUP.md` — Detailed setup
- `docs/00-project/ai/` — Shared AI utilities
