# Gemini Interactive Mode - Cheat Sheet

## 🚀 Launch Commands

### PowerShell (Windows)
```powershell
.\scripts\ai\gemini.ps1              # Interactive menu
.\scripts\ai\gemini.ps1 setup        # Initialize
.\scripts\ai\gemini.ps1 sync         # Sync profiles
.\scripts\ai\gemini.ps1 status       # Check status
```

### Bash (WSL)
```bash
bash scripts/ai/gemini-interactive.sh    # Interactive menu
bash scripts/ai/setup-gemini-wsl.sh      # Initialize
bash scripts/ai/sync-agents-codex-to-gemini.sh  # Sync profiles
```

---

## 📋 Main Menu Quick Reference

| Option | Mode | Use Case |
|--------|------|----------|
| **1** | 💬 Chat | Ask questions, explore, debug interactively |
| **2** | 📋 Task | Create formal task file for Gemini |
| **3** | 🔍 Review | Quick code review |
| **4** | 📊 Analysis | Data flow, dependencies, coverage |
| **5** | ⚙️ Maintenance | Setup, sync, reset, update MCP |
| **6** | 📚 Help | Docs, guides, session history |
| **7** | 🚪 Exit | Close menu |

---

## 🎯 Task Types (Mode 2)

```
1. Code Review (py-review-orchestrator)
   ├─ Scope: Staged | File | Directory | Project
   └─ Focus: Architecture | Tests | Style | All

2. Config Audit (py-config-bot)
   ├─ Scope: Configs | All | Specific
   └─ Check: YAML | Medallion | Loading strategies

3. Test Generation (py-test-swarm)
   ├─ Target: 85% (default)
   └─ Scope: Application | Domain | All

4. Architecture Analysis (py-architecture-debt-bot)
   ├─ Focus: Debt | Dependencies | Layers | Ports
   └─ Check: Hexagonal pattern, isolation

5. Debug/Fix (py-debug-bot)
   ├─ Issue: [describe]
   └─ File: [optional path]

6. Custom Profile
   ├─ Select: Profile
   └─ Task: [describe]
```

---

## 📁 Files Created/Modified

### First Setup
```
✓ .gemini/config.toml
✓ .gemini/settings.json
✓ .gemini/agents/GEMINI-RUNTIME.md
✓ docs/.../ai/memory/gemini-memory.json
✓ docs/.../ai/sessions/
```

### After Sync
```
✓ .gemini/agents/py-review-orchestrator.md
✓ .gemini/agents/py-test-swarm.md
✓ .gemini/agents/py-config-bot.md
✓ .gemini/agents/py-audit-bot.md
✓ .gemini/agents/py-debug-bot.md
✓ .gemini/agents/py-architecture-debt-bot.md
... (9 total profiles)
```

### Session Output
```
docs/00-project/ai/sessions/
├── chat-{ts}.log              (Chat mode)
├── review-{ts}.md             (Code review task)
├── config-audit-{ts}.md       (Config audit task)
├── test-gen-{ts}.md           (Test generation task)
├── arch-analysis-{ts}.md      (Architecture analysis)
└── debug-{ts}.md              (Debug/fix task)
```

---

## 🎪 Typical Workflows

### 📝 Code Review
```
Menu: 2 (Task) → 1 (Review) → Staged → Architecture
→ Task file: sessions/review-{ts}.md
→ Share with Gemini + GEMINI.md
→ Get review report
```

### ✅ Generate Tests
```
Menu: 2 (Task) → 3 (Test) → 90 (coverage) → domain
→ Task file: sessions/test-gen-{ts}.md
→ Gemini generates pytest code
→ Add tests to tests/
```

### 💬 Quick Chat
```
Menu: 1 (Chat) → Select profile → Ask questions → exit
→ Session: sessions/chat-{ts}.log
→ Share insights with team
```

### 🔍 Architecture Analysis
```
Menu: 2 (Task) → 4 (Architecture) → Dependencies
→ Task file: sessions/arch-analysis-{ts}.md
→ Gemini analyzes hexagonal pattern
→ Get recommendations
```

---

## 🔑 Key Shortcuts in Chat Mode

```
Type this     What happens
exit          Exit chat, save session
quit          Exit chat, save session
help          (not supported, type 'exit' to exit)
ctrl+c        Terminate current session
```

---

## 📍 Directory Structure

```
.
├── .gemini/
│   ├── config.toml
│   ├── settings.json
│   ├── .env.sh
│   └── agents/
│       ├── GEMINI-RUNTIME.md
│       └── py-*.md (9 profiles)
│
├── docs/
│   └── 00-project/
│       └── ai/
│           ├── memory/
│           │   └── gemini-memory.json
│           └── sessions/
│               ├── chat-*.log
│               └── *-*.md
│
└── scripts/
    └── ai/
        ├── gemini-interactive.sh          ← Main launcher
        ├── quick-gemini.sh
        ├── setup-gemini-wsl.sh
        ├── sync-agents-codex-to-gemini.sh
        ├── launch-gemini.sh
        ├── gemini.ps1
        └── README-INTERACTIVE.md
```

---

## 🛠️ Common Tasks

### Setup (First Time)
```bash
bash scripts/ai/setup-gemini-wsl.sh
bash scripts/ai/sync-agents-codex-to-gemini.sh
bash scripts/ai/gemini-interactive.sh
```

### Check Status
```bash
.\scripts\ai\gemini.ps1 status          (PowerShell)
bash scripts/ai/quick-gemini.sh status  (Bash)
```

### Resync Profiles
```bash
bash scripts/ai/sync-agents-codex-to-gemini.sh
```

### Clear Memory & Reset
```
Menu: 5 (Maintenance) → 4 (Clear Memory)
or
bash scripts/ai/setup-gemini-wsl.sh
```

### Update MCP Servers
```
Menu: 5 (Maintenance) → 5 (Update MCP)
Edit: .gemini/settings.json
```

---

## 🎨 Color Codes in Menu

```
🟢 Green  ✓  ← Success messages
🔴 Red    ✗  ← Error messages
🟡 Yellow ⚠  ← Warnings
🔵 Blue   ▶  ← Section headers
🟣 Magenta    ← Gemini responses
🔷 Cyan   ℹ  ← Info messages
```

---

## 📊 Profile Selection

| Profile | Role | Best For |
|---------|------|----------|
| py-review-orchestrator | default | Code reviews, orchestration |
| py-test-swarm | default | Test generation |
| py-audit-bot | research | Read-only analysis |
| py-config-bot | implementation | Config work |
| py-debug-bot | implementation | Bug fixes |
| py-architecture-debt-bot | default | Architecture analysis |
| py-plan-bot | default | Planning |
| py-doc-bot | implementation | Documentation |

---

## 🔄 Session Workflow

```
Chat Mode                Task Mode
─────────────           ──────────────
1. Select profile       1. Select task
2. Type prompt          2. Choose scope
3. Get response         3. Answer questions
4. Ask follow-ups   →   4. Task file created
5. Type 'exit'          5. Share with Gemini
6. Session logged       6. Get results
```

---

## ⚡ Quick Wins

### Win 1: Get Code Review
```
→ Menu: 2 (Task) → 1 (Review)
→ Done in 30 seconds
→ Task file ready to share
```

### Win 2: Chat Session
```
→ Menu: 1 (Chat) → Select profile
→ Ask questions naturally
→ All logged automatically
```

### Win 3: Check Setup
```
→ Menu: 5 (Maintenance) → 3 (Status)
→ Instant health check
```

### Win 4: Find Sessions
```
→ Menu: 6 (Help) → 5 (Recent Sessions)
→ Browse 10 latest
→ Open in editor
```

---

## 🚨 Troubleshooting Cheat Sheet

| Problem | Solution |
|---------|----------|
| Env check failed | `bash scripts/ai/setup-gemini-wsl.sh` |
| No profiles | `bash scripts/ai/sync-agents-codex-to-gemini.sh` |
| WSL not found | Use WSL terminal, not PowerShell |
| MCP error | Check Node.js: `which node` |
| Memory lost | `rm gemini-memory.json && setup-gemini-wsl.sh` |
| No sessions | `mkdir -p docs/.../ai/sessions` |

---

## 📚 Documentation Map

```
README-INTERACTIVE.md
  └─ Start here (overview + quick start)

INTERACTIVE-USAGE.md
  └─ Complete guide with examples

INTERACTIVE-MODE.md
  └─ Quick reference

GEMINI-WSL-SETUP.md
  └─ Detailed setup + troubleshooting

GEMINI.md
  └─ Project constraints + standards
```

---

## 🎓 Learning Path

### Beginner
1. Read: README-INTERACTIVE.md
2. Run: `bash scripts/ai/setup-gemini-wsl.sh`
3. Try: Menu 1 (Chat Mode)
4. Explore: Menu 6 (Help)

### Intermediate
1. Study: INTERACTIVE-USAGE.md
2. Try: Menu 2 (Task Mode) with each task type
3. Review: sessions/ directory
4. Share: Task files with team

### Advanced
1. Customize: .gemini/settings.json (MCP servers)
2. Create: Custom agent profiles
3. Extend: Add new task types
4. Monitor: Memory file, session performance

---

## 💡 Pro Tips

1. **Wide terminal:** 100+ columns for menu formatting
2. **Windows Terminal:** Better than PowerShell ISE
3. **WSL tab:** Keep one terminal for Gemini sessions
4. **Archive sessions:** `mkdir -p archive && mv sessions/*.log archive/`
5. **Ctrl+Shift+C/V:** Copy/paste in Windows Terminal
6. **Review GEMINI.md:** Loaded by all profiles
7. **Tab completion:** `bash scripts/ai/` then Tab
8. **Alias shortcuts:** Add to `.bashrc` for quick launch

---

## 🔗 Quick Links

- **Setup:** `.gemini/config.toml`, `.gemini/settings.json`
- **Memory:** `docs/00-project/ai/memory/gemini-memory.json`
- **Sessions:** `docs/00-project/ai/sessions/`
- **Profiles:** `.gemini/agents/py-*.md`
- **Constraints:** `GEMINI.md`
- **Reference:** `.codex/agents/CODEX-RUNTIME.md`

---

## ⏱️ Expected Timings

| Action | Time |
|--------|------|
| Setup (first time) | 30-60s |
| Sync profiles | 5-10s |
| Launch menu | 2-3s |
| Chat startup | 3-5s |
| Task creation | <1s |
| Gemini response | 5-30s (depends on query) |

---

**Last Updated:** 2026-04-14
**Status:** Ready for use ✓
