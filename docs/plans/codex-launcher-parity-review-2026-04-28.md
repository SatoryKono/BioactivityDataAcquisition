# Codex Launcher Parity Review 2026-04-28

*Status: Supporting operational context*
*Date: 2026-04-28*

Freshness note: the thin compatibility wrappers in this note
(`codex-headless*`, `diagnose-codex-wsl*`, `setup_agents.sh`,
`setup_skills.sh`) were removed on 2026-04-28 after the caller matrix reached
`governance-only`. This note remains as the rationale for retaining the
bootstrap transport adapters and `setup_plugins.sh`.

## Purpose

This note classifies the `scripts/ops/launchers/codex/*` surface for the
scripts CLI consolidation wave. Its purpose is to separate removable
compatibility wrappers from launchers and setup helpers that still carry
distinct transport or bootstrap semantics.

This is a supporting parity-review artifact, not a deletion batch.

## Scope

Reviewed surfaces:

- `scripts/ops/launchers/codex/codex.sh`
- `scripts/ops/launchers/codex/codex-exec.sh`
- `scripts/ops/launchers/codex/codex.bat`
- `scripts/ops/launchers/codex/codex-exec.bat`
- `scripts/ops/launchers/codex/codex-headless.sh`
- `scripts/ops/launchers/codex/diagnose-codex-wsl.sh`
- `scripts/ops/launchers/codex/setup_agents.sh`
- `scripts/ops/launchers/codex/setup_plugins.sh`
- `scripts/ops/launchers/codex/setup_skills.sh`

Primary evidence sources:

- `tests/architecture/test_codex_launcher_bootstrap.py`
- `tests/architecture/test_ops_ai_setup_scripts.py`
- the launcher bodies under `scripts/ops/launchers/codex/`
- the canonical `scripts/ai/codex/*` targets they delegate to

Out of scope for this note:

- blanket cleanup of `scripts/ai/mcp/*_wrapper.*`
- `scripts/docs/check_doc_links.py`
- body-level redesign of generated MCP config contracts

## Classification

| Path | Classification | Evidence summary | Current action |
| --- | --- | --- | --- |
| `scripts/ops/launchers/codex/codex.sh` | local bootstrap transport adapter | resolves repo root, calls `scripts/ai/codex/helper/ensure-codex-cli.sh`, exports local npm prefix, execs `codex -C "$REPO_ROOT"` | retain |
| `scripts/ops/launchers/codex/codex-exec.sh` | local bootstrap transport adapter | same bootstrap path as `codex.sh`, but execs `codex exec --full-auto -C "$REPO_ROOT"` | retain |
| `scripts/ops/launchers/codex/codex.bat` | Windows WSL transport adapter | delegates to `scripts/ops/launchers/codex/codex.sh` through WSL path conversion | retain |
| `scripts/ops/launchers/codex/codex-exec.bat` | Windows WSL transport adapter | delegates to `scripts/ops/launchers/codex/codex-exec.sh` through WSL path conversion | retain |
| `scripts/ops/launchers/codex/codex-headless.sh` | thin compatibility wrapper | direct `exec bash "$REPO_ROOT/scripts/ai/codex/headless.sh" "$@"` | removed after governance-only state |
| `scripts/ops/launchers/codex/diagnose-codex-wsl.sh` | thin compatibility wrapper | direct `exec bash "$REPO_ROOT/scripts/ai/codex/diagnose_wsl.sh" "$@"` | removed after governance-only state |
| `scripts/ops/launchers/codex/setup_agents.sh` | thin compatibility facade | direct delegation to `scripts/ai/codex/setup_agents.sh` | removed after governance-only state |
| `scripts/ops/launchers/codex/setup_skills.sh` | thin compatibility facade | direct delegation to `scripts/ai/codex/setup_skills.sh` | removed after governance-only state |
| `scripts/ops/launchers/codex/setup_plugins.sh` | runtime bootstrap helper | repo-root resolution, venv/runtime selection, Windows Git path fallback, `--pytest-only` semantics, cache/stamp management | retain |

## Findings

1. `codex.sh` and `codex-exec.sh` are not normal wrappers. They are the
   operator-facing launch path that guarantees repo-local Codex CLI bootstrap.

2. The Windows `.bat` entrypoints are not redundant with the Bash files. They
   are the Windows-to-WSL transport layer that preserves the supported launcher
   contract for native Windows users.

3. `codex-headless.sh`, `diagnose-codex-wsl.sh`, `setup_agents.sh`, and
   `setup_skills.sh` were genuinely thin wrappers. They were removed once the
   repo caller matrix reached `governance-only` and the tested contracts were
   moved to canonical `scripts/ai/codex/*` entrypoints.

4. `setup_plugins.sh` is not a trivial alias. It carries bootstrap behavior
   that is currently tested and referenced as an ops-facing helper surface.

## Immediate Refactor Rules

- Do not batch-delete `scripts/ops/launchers/codex/*`.
- Treat `codex.sh`, `codex-exec.sh`, `codex.bat`, `codex-exec.bat`, and
  `setup_plugins.sh` as retained runtime surfaces.
- Keep `codex-headless`, `diagnose-codex-wsl`, `setup-agents`, and
  `setup-skills` available only through the router-backed canonical
  `scripts/ai/codex/*` commands, not through dedicated thin wrapper files.
- Keep `scripts/ops/__main__.py` help and the wrapper caller matrix aligned
  with this classification.

## Next Safe Moves

1. Keep the wrapper caller matrix current so removed thin wrappers stay gone.
2. Run a separate parity review before changing `codex.sh`, `codex-exec.sh`, or
   `setup_plugins.sh`, because those files carry behavior beyond delegation.
