______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-07'

______________________________________________________________________

# Mistral Vibe: Setup and Usage via WSL2

Guide for running Mistral Vibe in this repository from WSL2 or from
Windows through the preferred router `python -m scripts.ai vibe`, the
canonical launchers in `scripts/ai/vibe/`, or the retained compatibility
wrappers in `scripts/ai/mistrallvibe/`.

______________________________________________________________________

## What Is Configured

- Project-local Vibe config: `.vibe/config.toml`
- Canonical WSL launcher: `scripts/ai/vibe/launch.sh`
- Canonical Windows PowerShell launcher: `scripts/ai/vibe/launch.ps1`
- Compatibility WSL launcher: `scripts/ai/mistrallvibe/run-vibe.sh`
- Compatibility Windows PowerShell launcher: `scripts/ai/mistrallvibe/run-vibe.ps1`
- Compatibility setup helper: `scripts/ai/mistrallvibe/helper/setup-env.sh`

The project-local config is discovered automatically by Vibe before
`~/.vibe/config.toml`, which keeps repository-specific defaults local to
BioETL.

______________________________________________________________________

## Install

The official Mistral docs currently recommend installing `mistral-vibe`
either through the published install script or via package tooling:

```bash
curl -LsSf https://mistral.ai/vibe/install.sh | bash
```

Alternative:

```bash
python3 -m pip install --user mistral-vibe
```

Repository compatibility helper:

```bash
bash scripts/ai/mistrallvibe/helper/setup-env.sh
```

Official references:

- Mistral Vibe install guide: <https://docs.mistral.ai/mistral-vibe/introduction/install>
- Mistral Vibe quickstart: <https://docs.mistral.ai/mistral-vibe/introduction/quickstart>
- Mistral Vibe configuration: <https://docs.mistral.ai/mistral-vibe/introduction/configuration>

______________________________________________________________________

## API Key

Set `MISTRAL_API_KEY` before the first run, or launch `vibe --setup` and
let the CLI persist the credential in `~/.vibe/.env`.

Example:

```bash
export MISTRAL_API_KEY="your_mistral_api_key"
```

______________________________________________________________________

## Launch

Preferred public entrypoint:

```bash
python -m scripts.ai vibe
python -m scripts.ai vibe "inspect the failing architecture tests"
python -m scripts.ai vibe --prompt "fix the failing architecture test" --max-turns 5
```

From WSL/Linux:

```bash
bash scripts/ai/vibe/launch.sh
bash scripts/ai/vibe/launch.sh "inspect the failing architecture tests"
bash scripts/ai/vibe/launch.sh --prompt "fix the failing architecture test" --max-turns 5
```

Compatibility wrapper:

```bash
bash scripts/ai/mistrallvibe/run-vibe.sh
bash scripts/ai/mistrallvibe/run-vibe.sh "inspect the failing architecture tests"
bash scripts/ai/mistrallvibe/run-vibe.sh --prompt "fix the failing architecture test" --max-turns 5
```

From Windows PowerShell:

```powershell
pwsh -File .\scripts\ai\vibe\launch.ps1
pwsh -File .\scripts\ai\vibe\launch.ps1 "inspect the failing architecture tests"
```

Compatibility wrapper:

```powershell
.\scripts\ai\mistrallvibe\run-vibe.ps1
.\scripts\ai\mistrallvibe\run-vibe.ps1 "inspect the failing architecture tests"
```

From Windows CMD:

```cmd
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\ai\vibe\launch.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\ai\vibe\launch.ps1 "inspect the failing architecture tests"
```

The wrappers pass `--workdir` with the repository root so Vibe starts in
the correct project context regardless of the current shell directory.

If `vibe` is not found in a fresh shell after installation, source the uv
user-tool environment once:

```bash
source ~/.local/bin/env
```

______________________________________________________________________

## Repository Defaults

The repository ships `.vibe/config.toml` with conservative defaults:

```toml
active_model = "devstral-2"
enable_auto_update = false
```

If you need a different provider or model alias, edit `.vibe/config.toml`
or your user config according to the Mistral configuration guide.
