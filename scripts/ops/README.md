# scripts/ops

`scripts/ops/` now separates stable executable tooling from internal helper
assets and bounded maintenance scripts. Neo4j project-memory tooling lives
under `scripts/memory/`, while canonical AI-facing setup and MCP operational
scripts live under `scripts/ai/`.

## Structure

- Top-level files are the supported executable/operator-facing entrypoints.
- `support/` contains helper scripts sourced by top-level wrappers.
- `maintenance/` contains one-off PR/issue wave helpers retained for
  repeatability, not promoted as stable automation.
- Canonical operational docs live under
  `docs/05-operations/tooling/scripts-ops/`.

## Stable entrypoints

- launchers such as `codex.sh`, `codex.bat`
- canonical Mistral Vibe wrappers live under `script-mistrallvibe/`
- setup/bootstrap commands such as `setup_plugins.sh`
- supported non-memory Python commands exposed through `python -m scripts.ops`

AI-oriented setup/check commands retained in this directory now act as
compatibility facades that delegate to `scripts/ai/codex/`.

## Internal-only zones

- `support/load_repo_env.sh`
- `script-codex/helper/ensure-codex-cli.sh`

## Legacy maintenance zone

Use the files under `maintenance/` only for bounded maintainer workflows. They
remain available for historical repeatability and curated issue/PR waves, not
as the basis for new public command surfaces.

## Canonical docs

See [docs/05-operations/tooling/scripts-ops/INDEX.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/05-operations/tooling/scripts-ops/INDEX.md).
For project-memory tooling, see [scripts/memory/README.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/memory/README.md).
For MCP operational tooling, see [scripts/ai/mcp/__main__.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/__main__.py).
For Codex setup/check tooling, see [scripts/ai/codex/README.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex/README.md).
