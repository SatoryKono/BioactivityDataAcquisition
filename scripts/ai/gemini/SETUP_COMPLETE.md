# Gemini Setup - Complete

`scripts/ai/gemini` is configured as a Codex-style launcher surface with a managed repo-local Python runtime.

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
    ├── gemini_client.py
    ├── setup-env.sh
    └── run-gemini-impl.sh
```

The managed SDK runtime is created at:

```text
.cache/tools/gemini-sdk/venv
```

## Commands

```bash
bash scripts/ai/gemini/run-gemini.sh check
bash scripts/ai/gemini/run-gemini.sh setup
bash scripts/ai/gemini/run-gemini.sh update
bash scripts/ai/gemini/run-gemini.sh
bash scripts/ai/gemini/run-gemini.sh prompt "what is AI?"
```

PowerShell delegates to the same WSL launcher:

```powershell
.\scripts\ai\gemini\run-gemini.ps1 check
.\scripts\ai\gemini\run-gemini.ps1 setup
.\scripts\ai\gemini\run-gemini.ps1 "what is AI?"
```

## Configuration

Edit `scripts/ai/gemini/.env.gemini`:

```bash
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-2.5-flash
```

## Codex Comparison

| Area | Codex | Gemini |
| --- | --- | --- |
| Runtime | Managed npm CLI | Managed Python SDK venv |
| Install root | `.cache/tools/codex-cli` | `.cache/tools/gemini-sdk` |
| Entrypoint | `run-codex.sh` / `.ps1` | `run-gemini.sh` / `.ps1` |
| Key | `OPENAI_API_KEY` | `GEMINI_API_KEY` |
| Repo agent mode | Yes, via Codex CLI | No, prompt/chat wrapper only |
| `exec` | Codex full-auto mode | Single-prompt alias only |

The launcher shape is aligned with Codex, but Gemini is intentionally not advertised as an auto-editing coding agent.
