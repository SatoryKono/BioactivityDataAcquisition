# Codex Launcher Parity Refresh 2026-04-29

*Status: Supporting operational context*
*Date: 2026-04-29*

## Purpose

Refresh the retained `scripts/ops/launchers/codex/*` parity map after the
scripts normalization wave and after live inspection of the current launcher
bodies. This note exists because the earlier `2026-04-28` review correctly
froze the launcher cluster as a retained surface, but several Windows-facing
compatibility wrappers drifted away from live canonical targets.

## Findings

1. `codex.bat` remains the actual Windows-to-WSL bridge for interactive Codex
   launch. It resolves the repo root, converts it with `wslpath`, and delegates
   to `scripts/ops/launchers/codex/codex.sh`.
2. `codex-exec.bat` remains the Windows-to-WSL bridge for the full-auto path
   and delegates to `scripts/ops/launchers/codex/codex-exec.sh`.
3. `codex-wsl.bat` and `start-codex.bat` had drifted to a non-existent
   `scripts/ai/codex/launch.bat`. They are now explicit compatibility facades
   over `codex.bat`.
4. `verify-setup.bat` and `verify-setup.ps1` had drifted to non-existent
   `scripts/ai/codex/verify_setup.*` targets. They are now compatibility
   facades over the live canonical verification path:
   `scripts/ai/codex/run-codex.ps1 check`.
5. `setup_plugins.sh` still carries bootstrap/runtime semantics and remains out
   of scope for wrapper deletion.

## Updated Classification

| Path | Classification | Current action |
| --- | --- | --- |
| `scripts/ops/launchers/codex/codex.sh` | retained bootstrap transport adapter | retain |
| `scripts/ops/launchers/codex/codex-exec.sh` | retained bootstrap transport adapter | retain |
| `scripts/ops/launchers/codex/codex.bat` | retained Windows-to-WSL transport adapter | retain |
| `scripts/ops/launchers/codex/codex-exec.bat` | retained Windows-to-WSL transport adapter | retain |
| `scripts/ops/launchers/codex/codex-wsl.bat` | retained compatibility facade over `codex.bat` | retain |
| `scripts/ops/launchers/codex/start-codex.bat` | retained quick-start facade over `codex.bat` | retain |
| `scripts/ops/launchers/codex/verify-setup.bat` | retained verification facade over PowerShell check path | retain |
| `scripts/ops/launchers/codex/verify-setup.ps1` | retained verification facade over `run-codex.ps1 check` | retain |
| `scripts/ops/launchers/codex/setup_plugins.sh` | retained bootstrap/runtime helper | retain |

## Safe Rule

For this cluster, safe refactoring remains limited to:

- fixing stale delegation targets;
- extracting shared internal logic without changing public filenames;
- keeping router help, tests, and retained-wrapper docs aligned.

Surface deletion remains out of scope without a separate caller/parity wave.
