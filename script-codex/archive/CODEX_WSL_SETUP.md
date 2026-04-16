# WSL Codex Setup & Usage Guide

## Overview

This guide covers setting up and running OpenAI's Codex CLI from WSL (Windows Subsystem for Linux) on Windows 11. The setup uses WSL2 as a backend while maintaining Windows compatibility through batch script wrappers.

## Architecture

```
Windows (PowerShell)
    ↓
codex.bat / codex-exec.bat (batch wrappers)
    ↓
WSL Distro (Ubuntu)
    ↓
codex.sh / codex-exec.sh (bash launchers)
    ↓
Node.js + npm (Codex CLI installation)
```

## Quick Start (5 minutes)

### Option 1: From Windows (PowerShell)

```powershell
# First-time setup (optional - auto-runs on first use)
.\scripts\ops\setup-codex-wsl.bat

# Run interactive Codex
.\scripts\ops\codex.bat

# Run with a prompt
.\scripts\ops\codex.bat "analyze the pipeline"

# Auto-execute without confirmations
.\scripts\ops\codex-exec.bat "refactor the parser"
```

### Option 2: From WSL Terminal

```bash
# First-time setup
bash ./scripts/ops/setup-wsl-codex-complete.sh

# Run interactive Codex
./scripts/ops/codex.sh

# Run with a prompt
./scripts/ops/codex.sh "analyze the pipeline"

# Auto-execute without confirmations
./scripts/ops/codex-exec.sh "refactor the parser"
```

## Setup Details

### Prerequisites

- **Windows 11** with WSL2 enabled
- **Docker Desktop** installed and running (for `docker.exe` access)
- **Ubuntu distro** installed in WSL (default: `Ubuntu`)

### What Gets Installed

The setup script installs:

1. **Node.js & npm** (if not already installed)
   - Required by Codex CLI
   - Installed via `apt-get` in WSL

2. **Codex CLI** (@openai/codex)
   - Installed to `.cache/tools/codex-cli/npm-global/`
   - Accessible via `${REPO_ROOT}/.cache/tools/codex-cli/npm-global/bin/codex`

3. **WSL Proxy Configuration** (optional)
   - Enables WSL to reach Windows services via proxy
   - Automatically detects Windows host IP
   - Can be auto-loaded in `~/.bashrc`

### Step-by-Step Setup

#### From Windows (PowerShell):

```powershell
cd /path/to/repo
.\scripts\ops\setup-codex-wsl.bat
```

The batch script will:
- Validate WSL2 distro accessibility
- Convert Windows paths to WSL paths
- Run the complete setup in WSL
- Display verification results

#### From WSL (Ubuntu terminal):

```bash
cd /path/to/repo
bash ./scripts/ops/setup-wsl-codex-complete.sh
```

The setup script will:
1. Verify WSL environment
2. Update package manager (with retries)
3. Install Node.js & npm (if missing)
4. Install/update Codex CLI
5. Verify Codex installation
6. Configure WSL proxy (optional)
7. Display next steps

### Manual Installation (if needed)

If the setup script fails, you can install manually from WSL:

```bash
# Update package manager
sudo apt-get update

# Install Node.js and npm
sudo apt-get install -y nodejs npm

# Install Codex globally or use ensure_codex_cli.sh
bash ./scripts/ops/support/ensure_codex_cli.sh --update
```

## Usage

### Interactive Mode

Start Codex and interact with it in your terminal:

**From Windows:**
```powershell
.\scripts\ops\codex.bat
```

**From WSL:**
```bash
./scripts/ops/codex.sh
```

### Command Mode (with prompt)

Run Codex with a specific prompt and exit:

**From Windows:**
```powershell
.\scripts\ops\codex.bat "analyze the ChemBL data pipeline"
```

**From WSL:**
```bash
./scripts/ops/codex.sh "analyze the ChemBL data pipeline"
```

### Auto-Execution Mode (no confirmations)

Run Codex in full-auto mode—it will execute suggested actions without asking:

**From Windows:**
```powershell
.\scripts\ops\codex-exec.bat "refactor the parser for performance"
```

**From WSL:**
```bash
./scripts/ops/codex-exec.sh "refactor the parser for performance"
```

### Update Codex

Update to the latest version:

**From Windows:**
```powershell
.\scripts\ops\codex.bat --update "your prompt"
```

**From WSL:**
```bash
./scripts/ops/codex.sh --update "your prompt"
```

### Help & Options

View available options:

**From Windows:**
```powershell
.\scripts\ops\codex.bat --help
```

**From WSL:**
```bash
./scripts/ops/codex.sh --help
```

## WSL Proxy Configuration

### Why Proxy?

WSL2 runs in an isolated network. If your environment requires a proxy to reach external APIs (Codex backend, npm registry, etc.), you need to configure it.

### Automatic Proxy Detection

The setup script automatically:
1. Detects the Windows host IP
2. Checks if proxy is accessible at `<host-ip>:3128`
3. Sets environment variables for the current session

### Manual Proxy Configuration

If automatic detection fails, configure manually:

```bash
# Get Windows host IP (run in WSL)
WIN_HOST_IP=$(/sbin/ip route show default | awk '{print $3}')
echo "Windows Host IP: $WIN_HOST_IP"

# Set proxy for current session
export http_proxy="http://${WIN_HOST_IP}:3128"
export https_proxy="http://${WIN_HOST_IP}:3128"

# Test proxy
curl -I http://example.com
```

### Permanent Proxy Configuration

Add to `~/.bashrc` to auto-load proxy on every WSL login:

```bash
echo 'source /path/to/repo/.wsl_proxy_env.sh' >> ~/.bashrc
source ~/.bashrc
```

Or manually:

```bash
# Get Windows host IP
WIN_HOST_IP=$(/sbin/ip route show default | awk '{print $3}')

# Add to .bashrc
cat >> ~/.bashrc <<EOF

# WSL Proxy Configuration
if [ -n "$WIN_HOST_IP" ]; then
  export http_proxy="http://${WIN_HOST_IP}:3128"
  export https_proxy="http://${WIN_HOST_IP}:3128"
  export HTTP_PROXY="\$http_proxy"
  export HTTPS_PROXY="\$https_proxy"
fi
EOF
```

### Start Proxy on Windows

If proxy is not running on Windows, start it:

**Option 1: PowerShell**
```powershell
python .\scripts\ops\wsl_proxy.py
```

**Option 2: Batch Script**
```cmd
.\scripts\ops\start-wsl-proxy.bat
```

The proxy listens on `localhost:3128` and routes WSL traffic through Windows network.

## Troubleshooting

### Issue: "WSL Distro not found"

**Symptom:** `wsl: Unknown distro. Run wsl --list to see available distros.`

**Solution:**
1. Check available distros: `wsl --list --verbose`
2. Update the distro name in scripts:
   - Edit `scripts/ops/codex.bat` and `codex-exec.bat`
   - Change `set "WSL_DISTRO=Ubuntu"` to your distro name (e.g., `Debian`, `Ubuntu-20.04`)

### Issue: "Node.js not found in WSL"

**Symptom:** `[ERROR] Node.js not found in PATH`

**Solution:**
```bash
# In WSL terminal
sudo apt-get update
sudo apt-get install -y nodejs npm
node --version
```

### Issue: "Codex binary not found"

**Symptom:** `[ERROR] Codex binary not found after installation`

**Solution:**
```bash
# In WSL, manually install Codex
bash ./scripts/ops/support/ensure_codex_cli.sh --update

# Verify
ls -la .cache/tools/codex-cli/npm-global/bin/codex
```

### Issue: "Codex API errors" / "Network timeout"

**Symptom:** Codex runs but fails on network requests

**Possible causes:**
1. Proxy not configured
2. Proxy not running on Windows
3. Docker Desktop not running

**Solution:**
```bash
# Check proxy
env | grep -i proxy

# If empty, enable proxy
source ./.wsl_proxy_env.sh

# Verify Docker Desktop is running (from Windows)
docker ps
```

### Issue: "Permission denied" on scripts

**Symptom:** `bash: ./codex.sh: Permission denied`

**Solution:**
```bash
# Make scripts executable
chmod +x ./scripts/ops/codex.sh
chmod +x ./scripts/ops/codex-exec.sh
chmod +x ./scripts/ops/setup-wsl-codex-complete.sh
```

## File Structure

```
scripts/ops/
├── codex.bat                           # Windows wrapper (interactive)
├── codex.sh                            # WSL launcher (interactive)
├── codex-exec.bat                      # Windows wrapper (auto-exec)
├── codex-exec.sh                       # WSL launcher (auto-exec)
├── setup-codex-wsl.bat                 # Windows setup launcher
├── setup-wsl-codex-complete.sh         # Complete WSL setup script
├── support/
│   └── ensure_codex_cli.sh             # Bootstrap helper (installs Codex)
├── wsl_proxy.py                        # Python proxy server
├── start-wsl-proxy.bat                 # Proxy launcher
└── README.md                           # This file
```

## Environment Variables

### Automatically Set by Launchers

- `NPM_CONFIG_PREFIX` - npm global prefix (`.cache/tools/codex-cli/npm-global`)
- `npm_config_prefix` - npm config (same as above)
- `PATH` - Extended with npm bin directory
- `http_proxy` / `https_proxy` - WSL proxy (if configured)

### Optional Overrides

```bash
# Use custom Codex version
export CODEX_NPM_PREFIX=/custom/path

# Use custom npm cache
export CODEX_NPM_CACHE=/custom/cache

# Enable verbose npm output
export npm_verbose=true
```

## Advanced Usage

### Run Codex on Specific Directory

```bash
# Use absolute path in repo
./scripts/ops/codex.sh "optimize the bioetl module" /path/to/bioetl

# Or change directory first
cd ./src/bioetl
../../scripts/ops/codex.sh "optimize this module"
```

### Use Different Node Version

If you have multiple Node versions installed:

```bash
# Use specific Node version
nvm use 18
./scripts/ops/codex.sh "your prompt"

# Or specify npm prefix
export NPM_CONFIG_PREFIX=/usr/local/nvm/versions/node/v18.0.0
./scripts/ops/codex.sh "your prompt"
```

### Debug Launcher Issues

```bash
# Run with verbose output
./scripts/ops/codex.sh --verbose "your prompt"

# Or manually trace
bash -x ./scripts/ops/codex.sh "your prompt"

# Check Codex version
bash ./scripts/ops/support/ensure_codex_cli.sh --print-bin | xargs -I {} {} --version
```

## Integration with CI/CD

### GitHub Actions

```yaml
name: Run Codex Analysis

on: [pull_request]

jobs:
  codex:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install Codex
        run: bash ./scripts/ops/support/ensure_codex_cli.sh --update
      
      - name: Run Codex Analysis
        run: ./scripts/ops/codex-exec.sh "analyze the pull request changes"
```

## References

- [Codex CLI Docs](https://platform.openai.com/docs/guides/codex)
- [WSL Documentation](https://learn.microsoft.com/en-us/windows/wsl/)
- [npm Documentation](https://docs.npmjs.com/)
- [Node.js Documentation](https://nodejs.org/en/docs/)

## Support

For issues or questions:
1. Check the **Troubleshooting** section above
2. Review `setup-wsl-codex-complete.sh` output for detailed error messages
3. Check Codex logs: `codex --verbose`
4. Verify Docker Desktop is running
5. Ensure WSL2 distro has internet access

---

**Last Updated:** 2024
