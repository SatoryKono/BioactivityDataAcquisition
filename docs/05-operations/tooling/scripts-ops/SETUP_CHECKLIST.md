# ✅ Codex WSL Setup Checklist

## What Was Done

### ✅ Analysis Phase

- [x] Examined existing `codex.bat` scripts
- [x] Analyzed Windows batch launchers
- [x] Reviewed existing WSL proxy setup
- [x] Studied VPN/proxy configuration
- [x] Understood Codex CLI requirements

### ✅ Script Creation Phase

- [x] Created `codex.sh` - WSL bash launcher
- [x] Created `codex-exec.sh` - WSL auto-exec launcher
- [x] Created `scripts/ai/codex/helper/setup-wsl.sh` - Installation script
- [x] Created `scripts/ai/codex/helper/verify-setup.sh` - Verification script
- [x] Created `codex-wsl.bat` - Modern Windows wrapper

### ✅ Documentation Phase

- [x] Written `CODEX_WSL_SETUP.md` - Comprehensive guide
- [x] Written `CODEX_WSL_QUICK_REF.md` - Quick reference
- [x] Written `INDEX.md` - File index & reference
- [x] Written `WSL_SETUP_SUMMARY.md` - Session summary
- [x] Written `00_START_HERE.md` - Visual overview

## Files Created Summary

```
scripts/ops/
├── 📜 Executable Scripts (5)
│   ├── codex.sh                    Interactive & prompt launcher
│   ├── codex-exec.sh               Auto-execution launcher
│   ├── ../scripts/ai/codex/helper/setup-wsl.sh          Installation & setup
│   ├── ../scripts/ai/codex/helper/verify-setup.sh       Verification & diagnostics
│   └── codex-wsl.bat               Windows wrapper
│
└── 📚 Documentation (5)
    ├── 00_START_HERE.md            👈 Start here!
    ├── CODEX_WSL_SETUP.md          Comprehensive guide
    ├── CODEX_WSL_QUICK_REF.md      Quick reference card
    ├── INDEX.md                    File index
    └── WSL_SETUP_SUMMARY.md        Session summary
```

## Pre-Use Checklist

Before using Codex, ensure you have:

- [x] WSL2 installed with Debian distro

  ```powershell
  wsl -l -v
  ```

- [x] Access to project directory from WSL

  ```bash
  ls <YOUR_WSL_REPO_PATH>
  ```

- [x] Internet connectivity from WSL

  ```bash
  ping google.com
  # or behind proxy: curl -I https://api.openai.com
  ```

## Installation Checklist

Run these in order:

### Step 1: Run Setup Script

```bash
# From WSL:
bash ./scripts/ai/codex/helper/setup-wsl.sh

# From PowerShell:
wsl -d Debian -- bash ./scripts/ai/codex/helper/setup-wsl.sh
```

Progress checklist:

- [ ] Package manager updated
- [ ] Node.js installed (or verified)
- [ ] npm installed (or verified)
- [ ] Codex CLI installed (or updated)
- [ ] Proxy configuration checked
- [ ] Script completes with ✓ Setup Complete

### Step 2: Verify Installation

```bash
bash ./scripts/ai/codex/helper/verify-setup.sh
```

Verification checklist:

- [ ] WSL environment detected
- [ ] Node.js version shown
- [ ] npm version shown
- [ ] Codex CLI verified
- [ ] OpenAI API accessible
- [ ] Final status: ✓ Setup verification successful

### Step 3: Test Codex

```bash
./scripts/ops/launchers/codex/codex.sh --version
```

Test checklist:

- [ ] Command executes
- [ ] Version shown
- [ ] No errors

## Usage Checklist

### First Use - Interactive Mode

```bash
./scripts/ops/launchers/codex/codex.sh
```

Expected behavior:

- [ ] Codex TUI appears
- [ ] Can type prompts
- [ ] Can navigate with arrow keys
- [ ] Can exit with Ctrl+C

### Second Use - With Prompt

```bash
./scripts/ops/launchers/codex/codex.sh "analyze this codebase"
```

Expected behavior:

- [ ] Prompt is sent to Codex
- [ ] Analysis starts immediately
- [ ] Output is displayed
- [ ] Session completes normally

### Third Use - Auto-Execute

```bash
./scripts/ops/launchers/codex/codex-exec.sh "add docstrings to all functions"
```

Expected behavior:

- [ ] Codex runs in full-auto mode
- [ ] Changes are applied automatically
- [ ] No confirmation prompts
- [ ] Files are modified

## Common Commands Checklist

Test these commands to familiarize yourself:

```bash
# 1. Code Analysis
./scripts/ops/launchers/codex/codex.sh "explain the data pipeline"
- [ ] Generates explanation

# 2. Problem Identification
./scripts/ops/launchers/codex/codex.sh "find performance bottlenecks"
- [ ] Identifies issues

# 3. Code Generation
./scripts/ops/launchers/codex/codex.sh "create unit tests for the ChemBL parser"
- [ ] Generates test code

# 4. Refactoring
./scripts/ops/launchers/codex/codex.sh "optimize database queries"
- [ ] Suggests improvements

# 5. Auto-Apply
./scripts/ops/launchers/codex/codex-exec.sh "add type hints to bioetl module"
- [ ] Applies changes automatically
```

## Troubleshooting Checklist

If something doesn't work:

### "Codex not found"

- [ ] Run: `bash ./scripts/ai/codex/helper/setup-wsl.sh`
- [ ] Run: `bash ./scripts/ai/codex/helper/verify-setup.sh`
- [ ] Check: `which codex`
- [ ] Check: `npm list -g @openai/codex`

### "OpenAI timeout"

- [ ] Check: `curl -I https://api.openai.com`
- [ ] If fails, run: `source scripts/engineering/dev/bash/.wsl_proxy_env.sh`
- [ ] If still fails: Start proxy from Windows: `.\scripts\ops\start-wsl-proxy.bat`
- [ ] Then retry: `curl -I https://api.openai.com`

### "WSL distro not found"

- [ ] Run: `wsl -l -v`
- [ ] If Debian missing: `wsl --install -d Debian`
- [ ] Set default: `wsl -s Debian`

### "Permission denied"

- [ ] Check file is executable (in WSL, bash ignores permissions from Windows)
- [ ] Try explicit: `bash ./scripts/ops/launchers/codex/codex.sh`

### "Path not found"

- [ ] Verify project path exists in WSL:
  ```bash
  ls -d <YOUR_WSL_REPO_PATH>
  ```
- [ ] Ensure running from project directory:
  ```bash
  pwd
  ```

## Verification Completion Checklist

Final verification that everything works:

```bash
# 1. ✓ Setup completed
bash ./scripts/ai/codex/helper/setup-wsl.sh
# Should end with: ✓ Setup Complete!

# 2. ✓ Verification passed
bash ./scripts/ai/codex/helper/verify-setup.sh
# Should show all green ✓ marks

# 3. ✓ Interactive works
./scripts/ops/launchers/codex/codex.sh
# Type 'exit' or Ctrl+C to quit

# 4. ✓ One-shot works
./scripts/ops/launchers/codex/codex.sh "explain this project"
# Should show analysis output

# 5. ✓ Auto-exec works (optional, use caution)
./scripts/ops/launchers/codex/codex-exec.sh "analyze code quality"
# Should apply changes automatically
```

## Documentation Reading Checklist

Read documentation in this order:

- [ ] **00_START_HERE.md** (5 min)

  - Visual overview
  - Quick start guide
  - Common examples

- [ ] **CODEX_WSL_SETUP.md** (20 min)

  - Detailed prerequisites
  - Step-by-step setup
  - Comprehensive troubleshooting
  - Best practices

- [ ] **CODEX_WSL_QUICK_REF.md** (5 min)

  - Commands cheat sheet
  - Common prompts
  - Shortcuts
  - Quick troubleshooting

- [ ] **INDEX.md** (5 min)

  - File reference
  - Improvements summary
  - Architecture overview

## Next Steps

1. **Start setup immediately**

   ```bash
   bash ./scripts/ai/codex/helper/setup-wsl.sh
   ```

1. **Verify after setup**

   ```bash
   bash ./scripts/ai/codex/helper/verify-setup.sh
   ```

1. **Try first command**

   ```bash
   ./scripts/ops/launchers/codex/codex.sh "what does this project do?"
   ```

1. **Read documentation**

   - Start with: `00_START_HERE.md`
   - Deep dive: `CODEX_WSL_SETUP.md`

1. **Integrate into workflow**

   - Use for code analysis
   - Use for refactoring
   - Use for generating tests
   - Use for documentation

## Success Criteria

You'll know it's working when:

- ✓ `bash ./scripts/ai/codex/helper/setup-wsl.sh` completes without errors
- ✓ `bash ./scripts/ai/codex/helper/verify-setup.sh` shows all green checkmarks
- ✓ `./scripts/ops/launchers/codex/codex.sh --version` shows Codex version
- ✓ `curl -I https://api.openai.com` returns HTTP 200
- ✓ `./scripts/ops/launchers/codex/codex.sh "hello"` generates a response from OpenAI
- ✓ All 5 new scripts exist and are accessible
- ✓ All 5 documentation files are readable

## Support Resources

If you get stuck:

1. **Quick help**: See `CODEX_WSL_QUICK_REF.md` § Troubleshooting Checklist
1. **Detailed help**: See `CODEX_WSL_SETUP.md` § Troubleshooting
1. **File overview**: See `INDEX.md` for file purposes
1. **Getting started**: See `00_START_HERE.md` for visual guide
1. **Run diagnostics**: `bash ./scripts/ai/codex/helper/verify-setup.sh`

______________________________________________________________________

**Status**: ✅ All files created and ready to use

**Next Action**: `bash ./scripts/ai/codex/helper/setup-wsl.sh`

**Estimated Time to Working Setup**: 5-10 minutes
