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

AI-oriented setup/check commands under `launchers/codex/` act as compatibility
facades that delegate to `scripts/ai/codex/`.

## Internal-only zones

- `support/load_repo_env.sh`
- `support/skills/`

## Legacy maintenance zone

Use the files under `maintenance/` only for bounded maintainer workflows. They
remain available for historical repeatability and curated issue/PR waves, not
as the basis for new public command surfaces.

## Canonical docs

See [docs/05-operations/tooling/scripts-ops/INDEX.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/05-operations/tooling/scripts-ops/INDEX.md).
For project-memory tooling, see [scripts/memory/README.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/memory/README.md).
For MCP operational tooling, see [scripts/ai/mcp/__main__.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/__main__.py).
For Codex setup/check tooling, see [scripts/ai/codex/README.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex/README.md).
For Vibe launch tooling, see [scripts/ai/vibe/README.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/vibe/README.md).
