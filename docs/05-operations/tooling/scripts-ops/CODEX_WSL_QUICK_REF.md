# Codex WSL Quick Reference

## One-Time Setup

```bash
# From WSL in project root
bash ./script-codex/helper/setup-wsl.sh

# If issues, configure proxy manually:
source .wsl_proxy_env.sh
curl -I https://api.openai.com  # Test
```

## Usage from PowerShell (Windows)

```powershell
# Navigate to project
cd e:\g-drive\05_AI\github\BioactivityDataAcquisition

# Interactive mode (new WSL wrapper)
.\scripts\ops\codex-wsl.bat

# With prompt
.\scripts\ops\codex-wsl.bat "analyze the pipeline"

# Or use original launchers
.\scripts\ops\codex.bat                    # Interactive
.\scripts\ops\codex.bat "fix the parser"   # With prompt
.\scripts\ops\codex-exec.bat "refactor"    # Auto-exec
```

## Usage from WSL Terminal

```bash
# Navigate to project
cd <YOUR_WSL_REPO_PATH>

# Interactive
./scripts/ops/launchers/codex/codex.sh

# With prompt
./scripts/ops/launchers/codex/codex.sh "analyze pipeline"

# Auto-execution
./scripts/ops/launchers/codex/codex-exec.sh "fix all TODOs"
```

## Common Prompts

| Task               | Command                                                                            |
| ------------------ | ---------------------------------------------------------------------------------- |
| **Analyze Code**   | `./scripts/ops/launchers/codex/codex.sh "explain the ChemBL data extraction"`      |
| **Find Issues**    | `./scripts/ops/launchers/codex/codex.sh "identify performance bottlenecks in ETL"` |
| **Generate Tests** | `./scripts/ops/launchers/codex/codex.sh "create unit tests for transformers"`      |
| **Refactor**       | `./scripts/ops/launchers/codex/codex.sh "optimize database queries"`               |
| **Add Docs**       | `./scripts/ops/launchers/codex/codex.sh "generate docstrings for all methods"`     |
| **Debug**          | `./scripts/ops/launchers/codex/codex.sh "debug the gold_sink_disabled warning"`    |
| **Auto-Apply**     | `./scripts/ops/launchers/codex/codex-exec.sh "add type hints everywhere"`          |

## Troubleshooting Checklist

| Problem              | Solution                                                                       |
| -------------------- | ------------------------------------------------------------------------------ |
| `Codex not found`    | Run: `bash ./script-codex/helper/setup-wsl.sh`                                 |
| `OpenAI timeout`     | Source proxy: `source .wsl_proxy_env.sh` then `curl -I https://api.openai.com` |
| `WSL not found`      | From PowerShell: `wsl -l -v` then `wsl --install -d Ubuntu`                    |
| `Permission denied`  | `chmod +x ./scripts/ops/launchers/codex/codex.sh`                              |
| `No internet in WSL` | Start Windows proxy: `.\scripts\ops\start-wsl-proxy.bat`                       |
| `Connection refused` | Restart Docker Desktop (if VPN-related)                                        |

## Files Created

- `scripts/ops/launchers/codex/codex.sh` - WSL bash launcher
- `scripts/ops/launchers/codex/codex-exec.sh` - WSL auto-exec launcher
- `scripts/ops/launchers/codex/codex-wsl.bat` - Modern Windows wrapper
- `script-codex/helper/setup-wsl.sh` - Installation script
- `docs/05-operations/tooling/scripts-ops/CODEX_WSL_SETUP.md` - Full guide (this document)

## Keyboard Shortcuts (Interactive Mode)

| Key      | Action             |
| -------- | ------------------ |
| `Ctrl+C` | Exit               |
| `Ctrl+L` | Clear screen       |
| `↑/↓`    | History navigation |
| `Tab`    | Auto-complete      |
| `Enter`  | Submit             |

## Tips

1. **Test connectivity first**: `curl -I https://api.openai.com`
1. **Verify installation**: `codex --version`
1. **Start with read-only**: `./scripts/ops/launchers/codex/codex.sh -s read-only "analyze this"`
1. **Always review output**: Before accepting changes from auto-exec
1. **Keep project in sync**: Git commit before major refactoring via Codex
1. **Use working directory**: Always run from project root for context

______________________________________________________________________

For full documentation: `CODEX_WSL_SETUP.md` | `CODEX_SETUP.md` | `CODEX_QUICK_REF.md`
