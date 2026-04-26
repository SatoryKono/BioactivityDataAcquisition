# Gemini Setup - Complete

`scripts/ai/gemini` is configured as a Codex-style launcher surface backed by the managed Google Gemini CLI.

## What Is Installed

```text
scripts/ai/gemini/
├── run-gemini.ps1
├── run-gemini.sh
├── .env.gemini
└── helper/
    ├── check-env.ps1
    ├── check-env.sh
    ├── ensure-gemini-cli.sh
    ├── setup-env.sh
    └── run-gemini-impl.sh
```

The managed CLI runtime is created at:

```text
.cache/tools/gemini-cli/
```

It contains repo-local `node@22`, npm cache, the `@google/gemini-cli` package, and `GEMINI_CLI_HOME`.

## Commands

```bash
bash scripts/ai/gemini/run-gemini.sh check
bash scripts/ai/gemini/run-gemini.sh setup
bash scripts/ai/gemini/run-gemini.sh update
bash scripts/ai/gemini/run-gemini.sh
bash scripts/ai/gemini/run-gemini.sh prompt "inspect the repository"
bash scripts/ai/gemini/run-gemini.sh exec "fix a targeted issue"
```

PowerShell delegates to the same WSL launcher:

```powershell
.\scripts\ai\gemini\run-gemini.ps1 check
.\scripts\ai\gemini\run-gemini.ps1 setup
.\scripts\ai\gemini\run-gemini.ps1 "inspect the repository"
```

## Configuration

Edit `scripts/ai/gemini/.env.gemini`:

```bash
GEMINI_API_KEY=your-api-key-here
# GEMINI_MODEL=gemini-2.5-flash
```

## Codex Comparison

| Area             | Codex                    | Gemini                                     |
| ---------------- | ------------------------ | ------------------------------------------ |
| Runtime          | Managed npm CLI          | Managed npm CLI                            |
| Package          | `@openai/codex`          | `@google/gemini-cli`                       |
| Install root     | `.cache/tools/codex-cli` | `.cache/tools/gemini-cli`                  |
| Entrypoint       | `run-codex.sh` / `.ps1`  | `run-gemini.sh` / `.ps1`                   |
| Key              | `OPENAI_API_KEY`         | `GEMINI_API_KEY`                           |
| Interactive mode | `codex -C <repo>`        | `gemini` from repo root                    |
| Headless mode    | `codex exec --full-auto` | `gemini --prompt ... --approval-mode yolo` |

Both launchers are now thin wrappers around managed coding-agent CLIs.
