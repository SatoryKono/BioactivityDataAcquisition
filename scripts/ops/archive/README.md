# scripts/archive

Archived scripts that were superseded by canonical tooling in top-level
`script-*` directories.

Current archived items:

- `ops/run-codex` → replaced by `script-codex/run-codex.sh`
- `ops/codex-login.sh` → replaced by `script-codex/run-codex.sh login`
- `ops/codex-login.ps1` → replaced by `script-codex/run-codex.ps1 login`
- `ops/codex-device-login.sh` → replaced by `script-codex/run-codex.sh device-login`
- `ops/codex-device-login.ps1` → replaced by `script-codex/run-codex.ps1 device-login`
- `ops/mistral.bat` → replaced by `script-mistrallvibe/run-vibe.ps1`
- `ops/mistral-exec.bat` → replaced by `script-mistrallvibe/run-vibe.ps1 --prompt ...`
- `ops/mistral.sh` → replaced by `script-mistrallvibe/run-vibe.sh`
- `ops/mistral-exec.sh` → replaced by `script-mistrallvibe/run-vibe.sh --prompt ...`
- `ops/setup_mistral_vibe.sh` → replaced by `script-mistrallvibe/helper/setup-env.sh`

Archive policy:

- Files are moved here only after checking that active repository references
  and user-facing docs have a supported replacement path.
- Legacy compatibility wrappers may remain outside the archive when the
  replacement changes the required host shell or operating-system surface.
