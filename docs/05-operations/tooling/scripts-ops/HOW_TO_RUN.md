# How to Run Codex

## Quick Start

### Option 1: Interactive Mode (Recommended for First Use)

From PowerShell in project root:

```powershell
wsl -- codex
```

Then type your prompt directly in the Codex terminal interface.

### Option 2: From WSL Terminal

Open WSL:

```powershell
wsl
```

Then run Codex:

```bash
cd <YOUR_WSL_REPO_PATH>
codex
```

Then type your prompt in the TUI.

## Example Prompts

Once Codex starts, try these:

```
analyze the data pipeline architecture
explain how the silver layer works
find performance bottlenecks in the ETL
create unit tests for ChemBLExtractor
generate docstrings for all public methods
debug the gold_sink_disabled warning
refactor the transformer class for performance
```

## Exiting Codex

Press `Ctrl+C` to exit the Codex interface.

## For Non-Interactive Scripts

If you need to automate Codex (not typical), the `codex exec` subcommand exists but requires proper terminal handling:

```bash
wsl -- codex exec --full-auto "your prompt here"
```

## Troubleshooting

### "stdin is not a terminal"

This happens when running Codex from a non-interactive shell. Use WSL's native terminal or PowerShell directly.

### "Codex CLI not found"

Reinstall:

```bash
wsl -- npm install -g @openai/codex
```

### "OpenAI API timeout"

Configure proxy (if behind corporate VPN):

```bash
wsl -- bash -c "source .wsl_proxy_env.sh && codex"
```

## Best Workflow

1. **Open PowerShell** in project root
1. **Start WSL**: `wsl`
1. **Navigate to project**: `cd <YOUR_WSL_REPO_PATH>`
1. **Start Codex**: `codex`
1. **Type your prompt** and press Enter
1. **Review the output**
1. **Type more prompts** in the same session (optional)
1. **Exit**: Press `Ctrl+C`

## Tips

- First API call takes 20-30 seconds (normal)
- Keep prompts focused and specific
- Ask follow-up questions in the same session
- Use `↑/↓` arrows to navigate prompt history
- Tab key provides auto-completion

______________________________________________________________________

See `CODEX_WSL_SETUP.md` for detailed information.
