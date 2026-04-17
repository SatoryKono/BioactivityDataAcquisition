# ✅ Codex WSL Setup — Installation Complete

## Status: READY TO USE ✓

All components installed and verified successfully.

## What's Installed

```
✓ Node.js v18.19.1
✓ npm 9.2.0
✓ Codex CLI v0.118.0
✓ WSL2 Ubuntu integration
✓ Project path accessibility
```

## Quick Start Commands

### From PowerShell (Windows)

```powershell
# Navigate to project
cd e:\g-drive\05_AI\github\BioactivityDataAcquisition2

# Interactive mode
.\scripts\ops\codex-wsl.bat

# With a prompt (analysis example)
.\scripts\ops\codex-wsl.bat "analyze the data pipeline architecture"

# Auto-execute example
.\scripts\ops\codex-exec.bat "add docstrings to all public functions"
```

### From WSL Terminal (Linux)

```bash
# Navigate to project
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2

# Interactive mode
./scripts/ops/launchers/codex/codex.sh

# With a prompt
./scripts/ops/launchers/codex/codex.sh "explain the ChemBL data extraction"

# Auto-execute
./scripts/ops/launchers/codex/codex-exec.sh "refactor the transformer class"
```

## Useful Examples

### Code Analysis & Understanding
```bash
./scripts/ops/launchers/codex/codex.sh "explain how the silver layer transformations work"
./scripts/ops/launchers/codex/codex.sh "show me the data flow from bronze to gold layer"
./scripts/ops/launchers/codex/codex.sh "what are the performance bottlenecks in this pipeline"
```

### Code Generation & Improvement
```bash
./scripts/ops/launchers/codex/codex.sh "generate comprehensive unit tests for ChemBLExtractor"
./scripts/ops/launchers/codex/codex.sh "create Pydantic models for the bronze layer schema"
./scripts/ops/launchers/codex/codex.sh "add comprehensive error handling to data loaders"
```

### Debugging & Problem Solving
```bash
./scripts/ops/launchers/codex/codex.sh "debug the gold_sink_disabled warning"
./scripts/ops/launchers/codex/codex.sh "explain why health_check_degraded happens on startup"
./scripts/ops/launchers/codex/codex.sh "analyze the chimbl_degraded_mode behavior"
```

### Refactoring & Optimization
```bash
./scripts/ops/launchers/codex/codex.sh "optimize database queries for better performance"
./scripts/ops/launchers/codex/codex.sh "refactor compound transformer for vectorized operations"
./scripts/ops/launchers/codex/codex.sh "improve memory efficiency in the data pipeline"
```

## Files Available

### Executable Scripts
- `codex.sh` - Interactive/prompt launcher
- `codex-exec.sh` - Auto-execution launcher
- `codex-wsl.bat` - Windows wrapper
- `script-codex/helper/setup-wsl.sh` - Setup script (already run)
- `script-codex/helper/verify-setup.sh` - Verification script
- `script-codex/helper/test-basic.sh` - Basic functionality test

### Documentation
- `00_START_HERE.md` - Visual overview
- `CODEX_WSL_SETUP.md` - Comprehensive guide
- `CODEX_WSL_QUICK_REF.md` - Quick reference
- `INDEX.md` - File index
- `SETUP_CHECKLIST.md` - Installation checklist
- `WSL_SETUP_SUMMARY.md` - Session summary

## Keyboard Shortcuts (Interactive Mode)

| Key | Action |
|-----|--------|
| `Ctrl+C` | Exit |
| `Ctrl+L` | Clear screen |
| `↑/↓` | Navigate history |
| `Tab` | Auto-complete |
| `Enter` | Submit prompt |

## Troubleshooting

### "Codex not found" (unlikely, but just in case)
```bash
bash ./script-codex/helper/setup-wsl.sh
```

### "API timeout" (if behind corporate VPN)
```bash
# Start Windows proxy from PowerShell
.\scripts\ops\start-wsl-proxy.bat

# Then in WSL, configure proxy
source .wsl_proxy_env.sh

# Test connectivity
curl -I https://api.openai.com
```

### "Permission denied" on scripts
```bash
# In WSL, make scripts executable
chmod +x ./scripts/ops/launchers/codex/codex.sh
chmod +x ./scripts/ops/launchers/codex/codex-exec.sh
```

## Advanced Options

### Use Different Model
```bash
./scripts/ops/launchers/codex/codex.sh -c model="o3" "analyze code"
```

### Read-Only Sandbox (Safe Exploration)
```bash
./scripts/ops/launchers/codex/codex.sh -s read-only "review this code"
```

### Enable Web Search
```bash
./scripts/ops/launchers/codex/codex.sh --search "research ETL best practices"
```

## Important Notes

1. **First API call takes time**: 20-30 seconds is normal as Codex connects to OpenAI
2. **Always review output**: Before accepting changes from auto-exec mode
3. **Keep working directory correct**: Run commands from project root
4. **Git first**: Commit before major refactoring via Codex
5. **Test after changes**: Run tests after code modifications

## Next Steps

1. **Try a simple analysis**
   ```bash
   wsl -- bash ./scripts/ops/launchers/codex/codex.sh "what is this project about?"
   ```

2. **Read the documentation**
   - Quick: `docs/05-operations/tooling/scripts-ops/CODEX_WSL_QUICK_REF.md`
   - Full: `docs/05-operations/tooling/scripts-ops/CODEX_WSL_SETUP.md`

3. **Integrate into your workflow**
   - Use for code reviews
   - Use for generating tests
   - Use for refactoring
   - Use for documentation

4. **Explore examples**
   - See examples above
   - See `CODEX_WSL_QUICK_REF.md` for more

## Support Resources

- **Quick commands**: `CODEX_WSL_QUICK_REF.md`
- **Setup help**: `CODEX_WSL_SETUP.md` § Troubleshooting
- **Overview**: `00_START_HERE.md`
- **Verification**: `bash ./script-codex/helper/verify-setup.sh`
- **Testing**: `bash ./script-codex/helper/test-basic.sh`

## Configuration

Default Codex config: `~/.codex/config.toml`

To customize:
```toml
[openai]
model = "gpt-4"
temperature = 0.7

[sandbox]
policy = "read-only"  # Safe by default
```

## Environment Variables (WSL)

The setup script configured:
- `http_proxy` / `https_proxy` - For VPN access
- `PATH` - Includes Node.js and npm
- Project root - Auto-detected

To manually configure proxy in future sessions:
```bash
source .wsl_proxy_env.sh
```

---

## Summary

✅ Installation complete
✅ All dependencies verified
✅ Codex CLI ready
✅ Project path accessible
✅ API connectivity confirmed

You're ready to use Codex for code analysis, generation, and refactoring!

**Start with:** `./scripts/ops/launchers/codex/codex.sh "analyze the project"`
