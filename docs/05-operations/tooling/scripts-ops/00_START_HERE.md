# Codex WSL Setup — Complete Overview

## 📋 What Was Analyzed

Your project has existing Windows-based Codex scripts:

```
./scripts/ops/
├── codex.bat           ← Original Windows launcher
├── codex-exec.bat      ← Original auto-exec launcher
├── start-codex.bat     ← Quick start wrapper
├── start-wsl-proxy.bat ← Proxy launcher
├── wsl_proxy.py        ← HTTP proxy bridge
├── CODEX_SETUP.md      ← Original setup guide
└── CODEX_QUICK_REF.md  ← Original quick reference
```

## ✨ What Was Created

### 4 New Executable Scripts

```
./scripts/ops/ + ./script-codex/
├── codex.sh                    ⭐ NEW - WSL bash launcher
├── codex-exec.sh              ⭐ NEW - WSL auto-exec launcher
├── ../script-codex/helper/setup-wsl.sh          ⭐ NEW - Installation & setup
├── ../script-codex/helper/verify-setup.sh       ⭐ NEW - Verification script
└── codex-wsl.bat              ⭐ NEW - Modern Windows wrapper
```

### 4 New Documentation Files

```
./scripts/ops/
├── CODEX_WSL_SETUP.md         ⭐ NEW - Detailed setup guide
├── CODEX_WSL_QUICK_REF.md     ⭐ NEW - Quick reference card
├── INDEX.md                   ⭐ NEW - File index
└── WSL_SETUP_SUMMARY.md       ⭐ NEW - This session summary
```

## 🚀 Quick Start (Choose One)

### Method 1: From PowerShell (Windows)

```powershell
# Step 1: Setup (one-time)
wsl -- bash ./script-codex/helper/setup-wsl.sh

# Step 2: Verify
wsl -- bash ./script-codex/helper/verify-setup.sh

# Step 3: Use it
.\scripts\ops\codex-wsl.bat "analyze the pipeline"
```

### Method 2: From WSL Terminal (Linux)

```bash
# Step 1: Setup (one-time)
bash ./script-codex/helper/setup-wsl.sh

# Step 2: Verify
bash ./script-codex/helper/verify-setup.sh

# Step 3: Use it
./scripts/ops/launchers/codex/codex.sh "analyze the pipeline"
```

### Method 3: Legacy Windows Scripts (Still Works)

```powershell
# Original launchers still work
.\scripts\ops\codex.bat
.\scripts\ops\codex-exec.bat "refactor code"
```

## 📊 Usage Comparison

| Scenario                 | Command                      | Platform   |
| ------------------------ | ---------------------------- | ---------- |
| **Interactive Analysis** | `./codex.sh`                 | WSL        |
| **One-Shot Analysis**    | `./codex.sh "analyze code"`  | WSL        |
| **Auto-Apply Changes**   | `./codex-exec.sh "refactor"` | WSL        |
| **Windows Interactive**  | `.\codex-wsl.bat`            | PowerShell |
| **Windows One-Shot**     | `.\codex-wsl.bat "analyze"`  | PowerShell |
| **Original Windows**     | `.\codex.bat`                | PowerShell |

## 📚 Documentation Map

```
Where to find what:

🟢 First Time Setup?
   → Read: CODEX_WSL_SETUP.md (comprehensive guide)

🟡 Need Quick Commands?
   → Read: CODEX_WSL_QUICK_REF.md (one-page reference)

🔵 Verify Installation?
   → Run: script-codex/helper/verify-setup.sh (automated checker)

🟣 Understand What's New?
   → Read: INDEX.md (file overview)
   → Read: WSL_SETUP_SUMMARY.md (session summary)

🔴 Troubleshooting?
   → Check: CODEX_WSL_SETUP.md § Troubleshooting

⚫ Original Info?
   → Read: CODEX_SETUP.md (original guide)
   → Read: CODEX_QUICK_REF.md (original quick ref)
```

## 🎯 File Purposes at a Glance

### Bash Scripts (Run from WSL)

| Script                                | Purpose                                   | Complexity |
| ------------------------------------- | ----------------------------------------- | ---------- |
| `codex.sh`                            | Launch Codex interactively or with prompt | Simple     |
| `codex-exec.sh`                       | Auto-execute changes (full-auto mode)     | Simple     |
| `script-codex/helper/setup-wsl.sh`    | Install all dependencies & configure      | Medium     |
| `script-codex/helper/verify-setup.sh` | Check installation & connectivity         | Medium     |

### Batch Scripts (Run from PowerShell)

| Script           | Purpose                        | Use Case             |
| ---------------- | ------------------------------ | -------------------- |
| `codex-wsl.bat`  | Modern wrapper for WSL scripts | Recommended          |
| `codex.bat`      | Original Windows launcher      | Legacy (still works) |
| `codex-exec.bat` | Original auto-exec launcher    | Legacy (still works) |

### Documentation (Read)

| Document                 | Length      | Best For                         |
| ------------------------ | ----------- | -------------------------------- |
| `CODEX_WSL_SETUP.md`     | ~9000 chars | Complete setup & troubleshooting |
| `CODEX_WSL_QUICK_REF.md` | ~3000 chars | Quick commands & examples        |
| `INDEX.md`               | ~5700 chars | File reference & reading order   |
| `WSL_SETUP_SUMMARY.md`   | ~6700 chars | This session overview            |

## 🔧 Key Features

✅ **One-Command Setup**

```bash
bash ./script-codex/helper/setup-wsl.sh
```

✅ **Automatic Verification**

```bash
bash ./script-codex/helper/verify-setup.sh
```

✅ **Multiple Execution Modes**

- Interactive (type prompts in TUI)
- Prompt-based (one-shot analysis)
- Auto-exec (full-auto with changes)

✅ **VPN/Proxy Support**

- Auto-detection of Windows proxy
- WSL proxy configuration
- Corporate firewall compatible

✅ **Better Error Messages**

- Clear diagnostics
- Actionable fixes
- Helpful suggestions

## 📦 What Gets Installed

The setup script installs:

```
✓ Node.js & npm (if missing)
✓ Codex CLI globally via npm
✓ Proxy configuration for VPN
✓ Environment variables for API access
```

## ✅ Verification Checklist

After setup, you should see:

```bash
$ bash ./script-codex/helper/verify-setup.sh

[1/5] Checking WSL environment...
✓ Running in WSL

[2/5] Checking Node.js...
✓ Node.js v18.17.0 installed

[3/5] Checking npm...
✓ npm 9.6.7 installed

[4/5] Checking Codex CLI...
✓ Codex CLI installed (v0.118.0)

[5/5] Checking OpenAI API connectivity...
✓ OpenAI API accessible

✓ Setup verification successful!
```

## 🎓 Common Usage Examples

### Analyze Code

```bash
./scripts/ops/launchers/codex/codex.sh "explain the ChemBL data extraction pipeline"
./scripts/ops/launchers/codex/codex.sh "identify performance bottlenecks in ETL"
```

### Generate Code

```bash
./scripts/ops/launchers/codex/codex.sh "create Pydantic models for bronze layer"
./scripts/ops/launchers/codex/codex.sh "generate unit tests for transformer classes"
```

### Refactor Code

```bash
./scripts/ops/launchers/codex/codex.sh "optimize database queries in bioetl/database.py"
./scripts/ops/launchers/codex/codex.sh "refactor compound transformer for vectorization"
```

### Debug Issues

```bash
./scripts/ops/launchers/codex/codex.sh "debug the gold_sink_disabled warning"
./scripts/ops/launchers/codex/codex.sh "explain why health_check_degraded occurs"
```

### Auto-Apply Changes

```bash
./scripts/ops/launchers/codex/codex-exec.sh "add type hints to all modules"
./scripts/ops/launchers/codex/codex-exec.sh "fix all TODO comments"
```

## 🏗️ Architecture

```
┌─ Windows PowerShell
│
├─ codex-wsl.bat ──────────────────────┐
├─ codex.bat (legacy) ─────────────────│ All routes to WSL2
├─ codex-exec.bat (legacy) ────────────│
│
└─ WSL2 (bash)
   │
   ├─ codex.sh ───────────┐
   ├─ codex-exec.sh ──────├─ npm/Node.js
   └─ script-codex/helper/setup-wsl.sh ─│
                          └─ Codex CLI → OpenAI API
```

## ⚙️ Configuration

### Default Configuration

- Works out-of-the-box for most setups
- Auto-detects Windows proxy if present
- No manual config needed (usually)

### Custom Configuration

If needed, edit `~/.codex/config.toml`:

```toml
[openai]
model = "gpt-4"
temperature = 0.7

[sandbox]
policy = "read-only"  # or "workspace-write"
```

## 🆘 If Something Goes Wrong

1. **Run the verifier first**

   ```bash
   bash ./script-codex/helper/verify-setup.sh
   ```

1. **Check the quick troubleshooting**

   ```
   See: CODEX_WSL_QUICK_REF.md § Troubleshooting Checklist
   ```

1. **Read the detailed guide**

   ```
   See: CODEX_WSL_SETUP.md § Troubleshooting
   ```

1. **Get diagnostics**

   ```bash
   which codex              # Where is Codex?
   codex --version          # Does it work?
   curl -I https://api.openai.com  # API access?
   ```

## 🎯 Next Steps

1. **Read documentation** (5 minutes)

   - Quick Read: `CODEX_WSL_QUICK_REF.md`
   - Full Read: `CODEX_WSL_SETUP.md`

1. **Run setup** (2 minutes)

   ```bash
   bash ./script-codex/helper/setup-wsl.sh
   ```

1. **Verify installation** (1 minute)

   ```bash
   bash ./script-codex/helper/verify-setup.sh
   ```

1. **Try it out** (1 minute)

   ```bash
   ./scripts/ops/launchers/codex/codex.sh "what is this project about?"
   ```

1. **Explore examples** (5-10 minutes)

   - Use examples from `CODEX_WSL_QUICK_REF.md`
   - Try different analysis types
   - Get familiar with the interface

## 📝 Summary

| Aspect                    | Status                                      |
| ------------------------- | ------------------------------------------- |
| **Analysis Complete**     | ✅ Yes                                      |
| **Scripts Created**       | ✅ 5 new scripts                            |
| **Documentation Written** | ✅ 4 detailed guides                        |
| **Ready to Use**          | ✅ Yes                                      |
| **Installation Required** | ✅ Yes (`script-codex/helper/setup-wsl.sh`) |

______________________________________________________________________

**Everything is ready. Start with:**

```bash
bash ./script-codex/helper/setup-wsl.sh
```

**Then verify with:**

```bash
bash ./script-codex/helper/verify-setup.sh
```

**Then use it:**

```bash
./scripts/ops/launchers/codex/codex.sh "analyze the pipeline"
```
