# Temporary Diagnostic TTL Wave 2 Closeout 2026-04-29

## Scope

This note records the second bounded execution wave against the
`temporary_diagnostic` bucket, focused on zero-reference convenience and local
repair helpers from the cheaper review buckets.

## Deleted

- `scripts/ai/codex/launch-interactive.ps1`
- `scripts/engineering/dev/bash/WSL_COMMANDS.sh`
- `scripts/engineering/dev/bash/entrypoint.sh`
- `scripts/engineering/dev/bash/test-driver-via-docker.sh`
- `scripts/engineering/dev/bash/warp-setup.sh`
- `scripts/engineering/dev/powershell/FixHypothesisDb.ps1`

Reason:

- each file had `reference_count=0` in the current inventory snapshot
- no maintained docs, tests, router mappings, or governance contracts still
  required these exact helper paths as live operational surface
- remaining mentions were limited to lifecycle or root-review governance data,
  which were updated to the new live baseline

## Governance Sync

The root-hygiene review registry was updated so it no longer points to deleted
canonical helper targets that are no longer part of the live scripts surface.

## Updated Inventory Baseline

After this wave:

- `scripts=357`
- `active=319`
- `supporting=27`
- `temporary_diagnostic=11`
- `orphan=0`
- `unknown=0`
- `legacy=0`

## Remaining TTL Focus

The remaining `temporary_diagnostic` bucket is now concentrated in:

- AI / MCP smoke helpers
- `.setup_wsl_codex.sh`
- memory / observability smoke helpers
- Neo4j / Docker / health troubleshooting surfaces

The next TTL wave should stay bounded and decide whether the remaining smoke
helpers are worth promotion or deletion before touching the heavier Neo4j
operator bucket.
