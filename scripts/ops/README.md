# scripts/ops

`scripts/ops/` now separates stable executable tooling from internal helper
assets and bounded maintenance scripts.

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
- checks and wrappers such as `check_mcp.sh`, `check_neo4j_mcp.sh`,
  `mcp_*_wrapper.{sh,ps1}`
- setup/bootstrap commands such as `setup_agents.sh`, `setup_plugins.sh`,
  `setup_skills.sh`
- supported Python commands exposed through `python -m scripts.ops`

## Internal-only zones

- `support/load_repo_env.{sh,ps1}`
- `support/docker_cli_resolver.sh`
- `script-codex/helper/ensure-codex-cli.sh`

## Legacy maintenance zone

Use the files under `maintenance/` only for bounded maintainer workflows. They
remain available for historical repeatability and curated issue/PR waves, not
as the basis for new public command surfaces.

## Canonical docs

See [docs/05-operations/tooling/scripts-ops/INDEX.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/05-operations/tooling/scripts-ops/INDEX.md).
