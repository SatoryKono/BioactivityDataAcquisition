# Codex Setup — Two Options

## Issue: Sudo Password Required

If you see the setup asking for a sudo password, you have two options:

---

## Option 1: Use No-Sudo Setup (Recommended)

This version skips the apt-get update step and goes straight to installing Codex.

**From PowerShell:**

```powershell
.\scripts\ops\setup-codex-nosudo.ps1
```

This assumes you already have Node.js and npm installed.

**If Node.js is not installed:**

Open WSL and run:
```bash
sudo apt-get install -y nodejs npm
```

Then run the setup again:
```powershell
.\scripts\ops\setup-codex-nosudo.ps1
```

---

## Option 2: Manual Setup (Fastest)

**Open WSL terminal directly and run:**

```bash
# 1. Check Node.js
node --version
npm --version

# 2. If not installed, install it
sudo apt-get install -y nodejs npm

# 3. Create directory for Codex
mkdir -p ~/.cache/tools/codex-cli/npm-global

# 4. Set npm prefix
export NPM_CONFIG_PREFIX=~/.cache/tools/codex-cli/npm-global

# 5. Install Codex
npm install -g @openai/codex@latest

# 6. Test
~/.cache/tools/codex-cli/npm-global/bin/codex --version
```

Done! Then use from PowerShell:
```powershell
.\scripts\ops\codex.bat "hello"
```

---

## Option 3: Full Setup with Sudo (Original)

If you want the full setup (system updates + everything):

**From PowerShell:**

```powershell
.\scripts\ops\setup-codex-wsl.bat
```

When prompted for password, enter your WSL user's password.

---

## Which Option Should I Choose?

| Option | Best For | Time | Requires |
|--------|----------|------|----------|
| **1: No-Sudo** | Most users | 2-3 min | Nothing (assumes Node.js exists) |
| **2: Manual** | Learning | 2-3 min | Opening WSL terminal |
| **3: Full** | Clean setup | 5-10 min | Sudo password |

---

## Quick Decision

**If you already have Node.js installed:**
```powershell
.\scripts\ops\setup-codex-nosudo.ps1
```

**If you don't have Node.js:**
1. Open WSL
2. Run: `sudo apt-get install -y nodejs npm`
3. Then: `.\scripts\ops\setup-codex-nosudo.ps1` (from PowerShell)

**If you want everything automatic:**
- Use Option 3 and provide your sudo password when prompted

---

## After Setup

Once installation completes, test Codex:

```powershell
.\scripts\ops\codex.bat "hello"
```

You're ready to go! 🚀
