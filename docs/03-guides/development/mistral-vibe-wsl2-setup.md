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
Windows through the canonical wrappers in `script-mistrallvibe/`.

______________________________________________________________________

## What Is Configured

- Project-local Vibe config: `.vibe/config.toml`
- Canonical WSL launcher: `script-mistrallvibe/run-vibe.sh`
- Canonical Windows PowerShell launcher: `script-mistrallvibe/run-vibe.ps1`
- Canonical setup helper: `script-mistrallvibe/helper/setup-env.sh`

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

Repository helper:

```bash
bash script-mistrallvibe/helper/setup-env.sh
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

From WSL/Linux:

```bash
bash script-mistrallvibe/run-vibe.sh
bash script-mistrallvibe/run-vibe.sh "inspect the failing architecture tests"
bash script-mistrallvibe/run-vibe.sh --prompt "fix the failing architecture test" --max-turns 5
```

From Windows PowerShell:

```powershell
.\script-mistrallvibe\run-vibe.ps1
.\script-mistrallvibe\run-vibe.ps1 "inspect the failing architecture tests"
```

From Windows CMD:

```cmd
powershell -NoProfile -ExecutionPolicy Bypass -File .\script-mistrallvibe\run-vibe.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\script-mistrallvibe\run-vibe.ps1 "inspect the failing architecture tests"
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
