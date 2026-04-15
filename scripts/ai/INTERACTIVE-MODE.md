# Gemini Interactive Mode - Quick Reference

## Launch Interactive Menu

```bash
bash scripts/ai/gemini-interactive.sh
```

or

```bash
bash scripts/ai/quick-gemini.sh interactive
```

---

## Main Menu Options

### 1. 💬 Interactive Chat Mode
- Select any agent profile (py-audit-bot, py-review-orchestrator, etc.)
- Start interactive conversation with Gemini
- Type `exit` or `quit` to end session
- All conversations logged to `docs/00-project/ai/sessions/chat-*.log`

**Best for:**
- Exploratory questions
- Incremental guidance
- Back-and-forth debugging

---

### 2. 📋 Task/Work Mode
Create structured task files for specific work:

#### a) Code Review (py-review-orchestrator)
- Scope: staged changes | file | directory | project
- Focus: architecture | tests | style | all
- Output: Markdown report in `sessions/review-*.md`

#### b) Configuration Audit (py-config-bot)
- Audit YAML configs
- Validate medallion architecture
- Check loading strategies
- Output: Audit report

#### c) Test Generation (py-test-swarm)
- Target coverage %
- Scope (application/domain/all)
- Generate pytest tests + fixtures
- Output: Test implementations

#### d) Architecture Analysis (py-architecture-debt-bot)
- Focus: technical debt | dependencies | layers | ports
- Check hexagonal pattern
- Validate layer isolation
- Output: Analysis report

#### e) Debug/Fix Task (py-debug-bot)
- Describe issue
- Specify affected file/module
- Generate fix implementation
- Output: Fixed code

#### f) Custom Profile
- Select any available profile
- Describe task
- Output: Custom task file

---

### 3. 🔍 Code Review Mode (Quick)
Quick shortcuts for reviewing code:
- Staged changes
- Specific file
- Directory tree

---

### 4. 📊 Analysis Mode
Quick analysis tools:
- Data flow analysis
- Dependency analysis
- Test coverage analysis
- Performance analysis

---

### 5. ⚙️ Configuration & Maintenance

#### Initialize Gemini Environment
```
Runs: scripts/ai/setup-gemini-wsl.sh
Creates: .gemini/ structure, memory file, validates MCP
```

#### Sync Agent Profiles
```
Runs: scripts/ai/sync-agents-codex-to-gemini.sh
Copies: py-* profiles from .codex/ to .gemini/
```

#### View Environment Status
```
Shows: Configuration paths, MCP status, session count
Verifies: All files exist and are accessible
```

#### Clear Memory & Reset
```
Deletes: gemini-memory.json
Reinitializes: Full Gemini environment
Use when: Fresh start needed or memory corrupted
```

#### Update MCP Servers
```
Edit: .gemini/settings.json
Modify: MCP server versions or configurations
```

---

### 6. 📚 Help & Documentation

#### View Setup Guide
```
Shows: GEMINI-WSL-SETUP.md (full setup instructions)
```

#### View Agent Profiles
```
Lists: Available py-* profiles with descriptions
```

#### View Project Constraints
```
Shows: GEMINI.md (architecture rules, coding standards)
```

#### View MCP Configuration
```
Shows: .gemini/settings.json (MCP servers)
```

#### List Recent Sessions
```
Shows: Last 10 sessions with timestamps
Browse: Session contents
```

---

## Session Files

All sessions saved to: `docs/00-project/ai/sessions/`

### Chat Sessions
- **Filename:** `chat-{timestamp}.log`
- **Format:** Plain text transcript
- **Content:** User inputs and Gemini responses

### Task Sessions
- **Filename:** `{task-type}-{timestamp}.md`
- **Format:** Markdown with task description
- **Content:** Task spec + execution results

### Examples
```
chat-1713100200.log          # Chat session
review-1713100300.md         # Code review task
config-audit-1713100400.md   # Config audit
test-gen-1713100500.md       # Test generation
arch-analysis-1713100600.md  # Architecture analysis
debug-1713100700.md          # Debug/fix task
quick-review-1713100800.md   # Quick review
```

---

## Quick Commands

### Status Check
```bash
bash scripts/ai/quick-gemini.sh status
```

### Setup (if needed)
```bash
bash scripts/ai/quick-gemini.sh setup
```

### Sync Profiles
```bash
bash scripts/ai/quick-gemini.sh sync
```

### Help
```bash
bash scripts/ai/quick-gemini.sh help
```

---

## Workflow Example

### Typical Code Review Session

```
1. Launch interactive menu
   $ bash scripts/ai/gemini-interactive.sh

2. Select: 2 (Task/Work Mode)

3. Select: 1 (Code Review)

4. Choose scope: 1 (Staged changes)

5. Enter focus: "architecture"

6. Review generated task file in sessions/review-*.md

7. Share file with Gemini + GEMINI.md context

8. Review outputs and iterate
```

### Typical Chat Session

```
1. Launch interactive menu
   $ bash scripts/ai/gemini-interactive.sh

2. Select: 1 (Interactive Chat)

3. Choose profile: py-review-orchestrator

4. Type questions/prompts interactively

5. Type "exit" when done

6. Session logged to sessions/chat-*.log
```

---

## Environment Variables

After first setup, source these:

```bash
source .gemini/.env.sh
```

This sets:
- `GEMINI_HOME` — Config root
- `GEMINI_CONFIG` — Runtime config path
- `GEMINI_MCP_SETTINGS` — MCP servers path
- `GEMINI_MEMORY_FILE` — Persistent memory

---

## Troubleshooting

### "Environment check failed"
```bash
bash scripts/ai/setup-gemini-wsl.sh
```

### "No profiles found"
```bash
bash scripts/ai/sync-agents-codex-to-gemini.sh
```

### "MCP servers not connecting"
- Check Node.js: `which node`
- Check UV: `which uvx`
- Verify WSL paths in `.gemini/settings.json`

### "Memory file not persisting"
```bash
rm -f docs/00-project/ai/memory/gemini-memory.json
bash scripts/ai/setup-gemini-wsl.sh
```

---

## Tips

- **Keep terminal wide:** Menus format best at 100+ columns
- **Use Tab completion:** `bash scripts/ai/` then Tab
- **Review GEMINI.md:** Loaded profiles reference it
- **Check sessions dir:** All work saved automatically
- **Reuse session files:** Copy and modify for similar tasks

---

## Next Steps

1. Run setup:
   ```bash
   bash scripts/ai/setup-gemini-wsl.sh
   ```

2. Launch interactive:
   ```bash
   bash scripts/ai/gemini-interactive.sh
   ```

3. Select option **1** (Chat) or **2** (Task)

4. Follow on-screen prompts
