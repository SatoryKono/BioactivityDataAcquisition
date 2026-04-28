# scripts/ops

`scripts/ops/` now separates stable executable tooling into clear subdomains.
Neo4j project-memory tooling lives under `scripts/memory/`, while canonical
AI-facing setup and MCP operational scripts live under `scripts/ai/`.

## Structure

- `launchers/` contains operator-facing launcher entrypoints and setup helpers.
- `runtime/` contains deployment, health, docker, WSL, and Neo4j runtime helpers.
- `observability/` contains Grafana/operator-facing observability utilities.
- `maintenance/` contains bounded Git/GitHub/security maintainer workflows.
- `support/` contains helper/support utilities that are not promoted as primary
  entrypoints.
- Canonical operational docs live under
  `docs/05-operations/tooling/scripts-ops/`.

## Stable entrypoints

- launchers under `launchers/codex/`
- setup/bootstrap commands such as `launchers/codex/setup_plugins.sh`
- supported non-memory Python commands exposed through `python -m scripts.ops`

The Codex launcher cluster is intentionally mixed:

- `launchers/codex/codex.sh` and `codex-exec.sh` are retained local bootstrap
  transport adapters. They are not thin wrappers because they ensure the
  repo-local Codex CLI and runtime prefix wiring before launch.
- `launchers/codex/setup_plugins.sh` is a retained bootstrap helper with its
  own runtime-selection and `--pytest-only` behavior.
- `python -m scripts.ops codex-headless`, `diagnose-codex-wsl`, `setup-agents`,
  and `setup-skills` now dispatch directly to canonical `scripts/ai/codex/`
  targets through the router; the old thin wrappers were removed once they
  reached governance-only status.

## Internal-only zones

- `support/load_repo_env.sh` is the shared repository environment loader used by
  ops helpers and MCP wrapper compatibility paths.
- `support/skills/`

## Legacy maintenance zone

Use the files under `maintenance/` only for bounded maintainer workflows. They
remain available for historical repeatability and curated issue/PR waves, not
as the basis for new public command surfaces.

## Canonical docs

See [docs/05-operations/tooling/scripts-ops/INDEX.md](/mnt/wsl/docker-desktop-bind-mounts/Ubuntu/ccd98afae0adb4ee090bbfed89f354b31936eafe0874d43825bf3cb903f3bd1d/docs/05-operations/tooling/scripts-ops/INDEX.md).
For project-memory tooling, see [scripts/memory/README.md](/mnt/wsl/docker-desktop-bind-mounts/Ubuntu/ccd98afae0adb4ee090bbfed89f354b31936eafe0874d43825bf3cb903f3bd1d/scripts/memory/README.md).
For MCP operational tooling, see [scripts/ai/mcp/__main__.py](/mnt/wsl/docker-desktop-bind-mounts/Ubuntu/ccd98afae0adb4ee090bbfed89f354b31936eafe0874d43825bf3cb903f3bd1d/scripts/ai/mcp/__main__.py).
For Codex setup/check tooling, see [scripts/ai/codex/README.md](/mnt/wsl/docker-desktop-bind-mounts/Ubuntu/ccd98afae0adb4ee090bbfed89f354b31936eafe0874d43825bf3cb903f3bd1d/scripts/ai/codex/README.md).
For Vibe launch tooling, see [scripts/ai/vibe/README.md](/mnt/wsl/docker-desktop-bind-mounts/Ubuntu/ccd98afae0adb4ee090bbfed89f354b31936eafe0874d43825bf3cb903f3bd1d/scripts/ai/vibe/README.md).
For the current launcher classification used by the scripts consolidation wave,
see [codex-launcher-parity-review-2026-04-28.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/codex-launcher-parity-review-2026-04-28.md).
