# Codex WSL Setup Guide

> Canonical root-governance note:
> former root `CODEX_WSL_SETUP.md` guidance was retired in July 2026. Keep
> active WSL setup guidance here and archive status-only setup notes under
> `docs/99-archive/root-status-artifacts/ai-runtime-setup/`.

This guide explains how to run Codex AI assistant from Windows Subsystem for Linux (WSL) in this project.

## Overview

Codex is an AI-powered code assistant. Running it from WSL provides:

- Native Linux environment compatibility
- Easier dependency management
- Direct file system access
- Better Node.js/npm integration

## Prerequisites

✅ Required:

- WSL2 with Ubuntu distro installed
- Windows 10/11 with WSL2 support
- Docker Desktop (optional, for some features)

⚠️ Network Access:

- OpenAI API access (requires internet/VPN)
- For corporate VPN: Windows proxy needs to be bridged to WSL

## Step 1: Initial WSL Setup (One-Time)

### 1.1 Verify WSL2 is installed

From PowerShell:

```powershell
wsl -l -v
```

You should see Ubuntu with version 2. If not:

```powershell
# Install WSL2 (if not present)
wsl --install -d Ubuntu
```

### 1.2 Launch WSL and verify environment

```powershell
# Enter WSL Debian
wsl -d Debian

# Inside WSL, verify basic tools
bash --version
```

## Step 2: Install Codex in WSL

### Option A: Automated Setup (Recommended)

From your project root in WSL:

```bash
# Enter WSL
wsl

# Navigate to your project
cd <YOUR_WSL_REPO_PATH>

# Run the setup script
bash ./scripts/ai/codex/helper/setup-wsl.sh
```

This script will:

1. Update package manager
1. Install Node.js + npm (if missing)
1. Install Codex CLI globally
1. Configure WSL proxy for API access

### Option B: Manual Setup

If automated setup fails:

```bash
# Update package manager
sudo apt-get update
sudo apt-get install -y nodejs npm

# Install Codex globally
npm install -g @openai/codex

# Verify installation
codex --version
```

## Step 3: Configure API Access (VPN/Network)

### For Direct Internet Access

If you have direct internet in WSL, Codex will work automatically.

Test:

```bash
curl -I https://api.openai.com
```

### For Corporate VPN (Windows Proxy)

If behind a proxy, configure the WSL proxy bridge:

#### Step 3.1: Start Windows proxy (from PowerShell)

```powershell
# From project root in PowerShell
cd e:\g-drive\05_AI\github\BioactivityDataAcquisition

# Option A: Use pre-built proxy
.\scripts\ops\start-wsl-proxy.bat

# Option B: Start manually
python .\scripts\ops\wsl_proxy.py
```

This starts a proxy on `0.0.0.0:3128` that routes through Windows VPN.

#### Step 3.2: Configure WSL to use the proxy

In WSL:

```bash
# Automatic (recommended):
source scripts/engineering/dev/bash/.wsl_proxy_env.sh

# Or manual:
export http_proxy=http://$(ip route show default | awk '{print $3}'):3128
export https_proxy=http://$(ip route show default | awk '{print $3}'):3128
```

To make this permanent, add to `~/.bashrc`:

```bash
echo "source /path/to/repo/scripts/engineering/dev/bash/.wsl_proxy_env.sh" >> ~/.bashrc
```

Test connectivity:

```bash
curl -I https://api.openai.com
# Should return HTTP/1.1 200 OK
```

## Step 4: Verify Codex Installation

```bash
# Check Codex is available
codex --version

# Test basic invocation
codex --help
```

## Usage

### From PowerShell (Windows)

```powershell
# Navigate to project
cd e:\g-drive\05_AI\github\BioactivityDataAcquisition

# Interactive mode
.\scripts\ops\codex.bat

# With a prompt
.\scripts\ops\codex.bat "analyze the ChemBL parser"

# Auto-execution
.\scripts\ops\codex-exec.bat "fix all TODO comments"
```

### From WSL (Direct)

```bash
# Navigate to project
cd <YOUR_WSL_REPO_PATH>

# Interactive mode
./scripts/ops/launchers/codex/codex.sh

# With a prompt
./scripts/ops/launchers/codex/codex.sh "explain the data pipeline"

# Auto-execution
./scripts/ops/launchers/codex/codex-exec.sh "refactor the transformer class"
```

### New WSL Wrapper (Windows)

```powershell
# From PowerShell in project root
.\scripts\ops\codex-wsl.bat

# With prompt
.\scripts\ops\codex-wsl.bat "analyze pipeline performance"
```

## Script Files Explained

| File                               | Purpose                      | Platform           |
| ---------------------------------- | ---------------------------- | ------------------ |
| `codex.bat`                        | Original launcher (via WSL2) | Windows PowerShell |
| `codex.sh`                         | WSL bash launcher            | WSL2 (bash)        |
| `codex-exec.sh`                    | Auto-execution launcher      | WSL2 (bash)        |
| `codex-exec.bat`                   | Original auto-exec launcher  | Windows PowerShell |
| `codex-wsl.bat`                    | Modern WSL wrapper           | Windows PowerShell |
| `scripts/ai/codex/helper/setup-wsl.sh` | Installation script          | WSL2 (bash)        |
| `wsl_proxy.py`                     | HTTP proxy bridge            | Windows (Python)   |
| `start-wsl-proxy.bat`              | Proxy launcher               | Windows PowerShell |
| `scripts/engineering/dev/bash/.wsl_proxy_env.sh`                | Proxy environment setup      | WSL2 (bash)        |

## Common Usage Examples

### Code Analysis

```bash
./scripts/ops/launchers/codex/codex.sh "explain the data transformation pipeline"
./scripts/ops/launchers/codex/codex.sh "identify performance bottlenecks in the ETL"
./scripts/ops/launchers/codex/codex.sh "review security of data access patterns"
```

### Refactoring & Optimization

```bash
./scripts/ops/launchers/codex/codex.sh "refactor ChemBL extractor for vectorized operations"
./scripts/ops/launchers/codex/codex.sh "optimize database queries in bioetl/database.py"
./scripts/ops/launchers/codex/codex.sh "add error handling to all data loading functions"
```

### Code Generation

```bash
./scripts/ops/launchers/codex/codex.sh "generate Pydantic models for bronze layer"
./scripts/ops/launchers/codex/codex.sh "create comprehensive unit tests for ChemBLExtractor"
./scripts/ops/launchers/codex/codex.sh "add docstrings to all public methods"
```

### Debugging

```bash
./scripts/ops/launchers/codex/codex.sh "debug the gold_sink_disabled warning"
./scripts/ops/launchers/codex/codex.sh "fix the health_check_degraded issue during startup"
./scripts/ops/launchers/codex/codex.sh "analyze the chimbl_degraded_mode behavior"
```

### With Auto-Execution

```bash
./scripts/ops/launchers/codex/codex-exec.sh "fix all TODO comments in the codebase"
./scripts/ops/launchers/codex/codex-exec.sh "add type hints to bioetl module"
```

## Troubleshooting

### "Codex not found"

```bash
# Check installation
which codex
command -v codex

# Reinstall
npm install -g @openai/codex

# Verify
npm list -g @openai/codex
```

### "OpenAI API unreachable" or timeout

Check proxy configuration:

```bash
# Test Windows host connectivity
ping $(ip route show default | awk '{print $3}')

# Test proxy
timeout 2 bash -c "echo > /dev/tcp/$(ip route show default | awk '{print $3}')/3128"

# If fails, restart proxy on Windows:
# PowerShell: .\scripts\ops\start-wsl-proxy.bat
```

### "Permission denied" on scripts

Make scripts executable:

```bash
chmod +x ./scripts/ops/launchers/codex/codex.sh
chmod +x ./scripts/ops/launchers/codex/codex-exec.sh
chmod +x ./scripts/ai/codex/helper/setup-wsl.sh
```

### WSL distro not found

```powershell
# List available distros
wsl -l -v

# Install Ubuntu
wsl --install -d Ubuntu

# Set as default
wsl -s Ubuntu
```

### Node.js/npm issues in WSL

```bash
# Check versions
node --version
npm --version

# Update npm
npm install -g npm@latest

# Clear cache if needed
npm cache clean --force
```

### Path issues in WSL

Codex scripts auto-detect the Windows repo path and convert to WSL format (`<WSL_MOUNT>/e/...`).

If paths don't work:

```bash
# Verify WSL can access project
ls -la <YOUR_WSL_REPO_PATH>

# Check current directory
pwd

# Ensure proper path format
echo $PWD
```

## Advanced Configuration

### Custom Codex Config

Codex looks for `~/.codex/config.toml`:

```toml
[openai]
model = "gpt-4"
temperature = 0.7

[sandbox]
policy = "read-only"

[editor]
no_alternate_screen = true
```

### Custom Model Selection

```bash
# Use o3 model (if available)
./scripts/ops/launchers/codex/codex.sh -c model="o3" "analyze performance"

# Use gpt-4-turbo
./scripts/ops/launchers/codex/codex.sh -c model="gpt-4-turbo" "generate tests"
```

### Sandbox Modes

```bash
# Read-only (safe, no changes)
./scripts/ops/launchers/codex/codex.sh -s read-only "review the code"

# Workspace write (Codex can modify files)
./scripts/ops/launchers/codex/codex.sh -s workspace-write "refactor and apply changes"
```

## Best Practices

1. **Start simple**: Test with basic analysis before complex refactoring
1. **Use read-only first**: Explore unfamiliar code with `-s read-only`
1. **Review before applying**: Always check Codex output before accepting changes
1. **Test after changes**: Run unit tests after Codex modifies code
1. **Use version control**: Commit before running Codex, easy to revert if needed
1. **Keep sessions focused**: Ask related follow-ups in same session
1. **Document decisions**: Save important Codex outputs/reasoning

## Next Steps

1. Run setup: `bash ./scripts/ai/codex/helper/setup-wsl.sh`
1. Test: `./scripts/ops/launchers/codex/codex.sh "explain this pipeline"`
1. Explore: Try the examples in Common Usage Examples section
1. Integrate: Add Codex to your workflow for code reviews, refactoring, etc.

## Files Modified by This Setup

- `scripts/ops/launchers/codex/codex.sh` (new) - WSL bash launcher
- `scripts/ops/launchers/codex/codex-exec.sh` (new) - WSL auto-exec launcher
- `scripts/ops/launchers/codex/codex-wsl.bat` (new) - Modern Windows wrapper
- `scripts/ai/codex/helper/setup-wsl.sh` (new) - Installation script

Original files remain unchanged:

- `scripts/ops/launchers/codex/codex.bat` - Original Windows launcher
- `scripts/ops/launchers/codex/codex-exec.bat` - Original auto-exec
- `scripts/ops/runtime/wsl/wsl_proxy.py` - HTTP proxy bridge
- `scripts/engineering/dev/bash/.wsl_proxy_env.sh` - Proxy environment config

______________________________________________________________________

**For more info:** See `CODEX_SETUP.md` and `CODEX_QUICK_REF.md` in `scripts/ops/`
