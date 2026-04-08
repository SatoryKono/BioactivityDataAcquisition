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
Windows through the WSL wrappers in `scripts/ops/`.

______________________________________________________________________

## What Is Configured

- Project-local Vibe config: `.vibe/config.toml`
- WSL interactive launcher: `scripts/ops/mistral.sh`
- WSL prompt-mode launcher: `scripts/ops/mistral-exec.sh`
- Windows interactive launcher: `scripts/ops/mistral.bat`
- Windows prompt-mode launcher: `scripts/ops/mistral-exec.bat`
- WSL installer helper: `scripts/ops/setup_mistral_vibe.sh`

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
bash scripts/ops/setup_mistral_vibe.sh
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
bash scripts/ops/mistral.sh
bash scripts/ops/mistral.sh "inspect the failing architecture tests"
bash scripts/ops/mistral-exec.sh "fix the failing architecture test" --max-turns 5
```

From Windows PowerShell / CMD:

```cmd
scripts\ops\mistral.bat
scripts\ops\mistral.bat "inspect the failing architecture tests"
scripts\ops\mistral-exec.bat "fix the failing architecture test" --max-turns 5
```

The wrappers pass `--workdir` with the repository root so Vibe starts in
the correct project context regardless of the current shell directory.
On Windows they probe `Ubuntu` first, then `Debian`, by attempting to start
the distro directly. Set `BIOETL_WSL_DISTRO` explicitly if you use a different
name.

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
