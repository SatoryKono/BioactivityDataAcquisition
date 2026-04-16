# scripts/ops index

## Stable executable zones

- Top-level `*.sh`, `*.ps1`, `*.bat`, and selected `*.py` files are the stable
  executable/operator-facing surface.
- `python -m scripts.ops --help` lists the supported facade commands.

## Support helpers

- `script-codex/helper/ensure-codex-cli.sh`
- `support/docker_cli_resolver.sh`
- `support/load_repo_env.sh`
- `support/load_repo_env.ps1`

These helper assets are intentionally internal and should be referenced by
wrappers rather than documented as primary user commands.

## Maintenance helpers

- `maintenance/` contains one-off issue, PR, and wave utilities.

## Documentation

Canonical operational docs for `scripts/ops` now live under:

- [docs/05-operations/tooling/scripts-ops/INDEX.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/05-operations/tooling/scripts-ops/INDEX.md)
