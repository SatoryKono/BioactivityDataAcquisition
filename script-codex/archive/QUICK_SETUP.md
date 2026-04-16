# Codex CLI Quick Setup — Fast Path

For the fastest setup without waiting for package manager updates, run these commands directly in WSL:

## Option 1: Quick Setup (No sudo required)

```bash
# Open WSL terminal and run:

# 1. Check if Node.js is installed
node --version
npm --version

# If not installed, run:
# sudo apt-get update && sudo apt-get install -y nodejs npm

# 2. Install Codex CLI manually
mkdir -p ~/.cache/tools/codex-cli/npm-global
export NPM_CONFIG_PREFIX=~/.cache/tools/codex-cli/npm-global
npm install -g @openai/codex@latest

# 3. Test it works
~/.cache/tools/codex-cli/npm-global/bin/codex --version

# 4. Then use it
~/.cache/tools/codex-cli/npm-global/bin/codex -C $(pwd) "analyze the pipeline"
```

## Option 2: Use Existing Scripts (May take time)

From PowerShell:
```powershell
.\scripts\ops\setup-codex-wsl.bat
```

This runs the full setup which includes:
- System updates (apt-get) — can be slow
- Node.js installation (if needed)
- Codex CLI installation
- Proxy configuration

## Option 3: Check Current Status

From WSL:
```bash
node --version
npm --version
ls -la ~/.cache/tools/codex-cli/npm-global/bin/codex 2>/dev/null && echo "Codex installed" || echo "Codex not installed"
```

## Option 4: Manual Installation (Fastest)

If you already have Node.js and npm:

```bash
# From any directory in WSL:
mkdir -p ~/.cache/tools/codex-cli/npm-global
export NPM_CONFIG_PREFIX=~/.cache/tools/codex-cli/npm-global
npm install -g @openai/codex@latest

# Test
~/.cache/tools/codex-cli/npm-global/bin/codex --version

# Use with repo
./scripts/ops/codex.sh "your prompt"
```

## Troubleshooting

**If `node` command not found:**
```bash
sudo apt-get update
sudo apt-get install -y nodejs npm
```

**If npm install is slow:**
- Check internet connection: `curl https://www.google.com`
- Try using a different npm registry:
  ```bash
  npm config set registry https://registry.npmjs.org/
  npm install -g @openai/codex@latest
  ```

**If permission errors:**
```bash
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
export PATH=~/.npm-global/bin:$PATH
npm install -g @openai/codex@latest
```

## Using Codex

Once installed, from PowerShell:

```powershell
.\scripts\ops\codex.bat "analyze the pipeline"
.\scripts\ops\codex-exec.bat "refactor code"
```

Or from WSL:

```bash
./scripts/ops/codex.sh "analyze the pipeline"
./scripts/ops/codex-exec.sh "refactor code"
```

That's it! Codex is ready to use.
