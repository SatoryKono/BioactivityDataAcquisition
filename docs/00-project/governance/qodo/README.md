# Qodo Governance Mirror

This directory is a human-readable mirror for BioETL's repo-level Qodo review
surfaces. It must not redefine runtime or governance behavior on its own.

## Authoritative Sources

Use these sources in the listed order when Qodo-related instructions appear to
conflict:

1. `AGENTS.md`
2. `docs/00-project/RULES.md`
3. Accepted ADRs in `docs/02-architecture/decisions/`
4. Executable governance and architecture surfaces:
   - `.importlinter`
   - `tests/architecture/**`
   - `.github/workflows/**`
5. Repo-level Qodo artifacts:
   - `.pr_agent.toml`
   - `best_practices.md`

## Repo-Level Qodo Surfaces

- `.pr_agent.toml`: repository-level Qodo configuration for GitHub review
  behavior and extra review instructions.
- `best_practices.md`: project-specific best-practice guidance consumed by Qodo
  rule enforcement paths.

## Important Local Distinctions

- `.qodo/mcp.json` is a local MCP runtime configuration surface. It is not the
  repository's Qodo review-policy source of truth.
- Refresh `.qodo/mcp.json` from the canonical generator with
  `python scripts\ai\codex\setup_mcp.py --qodo-only` when only the local Qodo
  Desktop MCP launch config needs to be updated.
- On Windows, Qodo Desktop must be able to resolve both
  `C:\Program Files\nodejs` and `%APPDATA%\npm` from the user `Path`, because
  the generated `.qodo/mcp.json` launches multiple servers via `npx`.
- Path-local supported files may be added later for narrower scope, but root
  files apply repository-wide by default.

## Manual Inspection Required

The following items are not proven by repository files alone and require manual
verification in Qodo Portal or GitHub UI:

- GitHub App installation and permissions
- organization-level or portal-level Qodo settings
- live branch protection / ruleset enforcement state

## Vendor Validation Notes

- `.pr_agent.toml` keys in this repository were validated against current Qodo
  configuration docs.
- `best_practices.md` is a documented supported file name in Qodo rule
  enforcement docs.
- The formerly root-level `pr_compliance_checklist.yaml` was removed after
  confirming that no tracked workflow, script, or configuration consumes it.
  Qodo Review Standards remain a portal/tooling concern and are not represented
  by a local root contract.

## Root Retention Revalidation

Last verified: 2026-07-16 for root hygiene issue #5999.

| Root surface | Owner contract | Current decision |
| --- | --- | --- |
| `.pr_agent.toml` | Qodo / PR-Agent repository-level configuration | Retain at root until review tooling is explicitly repointed. |
| `best_practices.md` | Qodo rule-enforcement guidance filename | Retain at root while vendor ingestion expects the documented filename. |
| `pr_compliance_checklist.yaml` | Retired local Qodo checklist surface | Absent from root baseline; do not restore without fresh tooling evidence. |
| `commitlint.config.mjs` | Commitlint workflow configuration | Retain at root while `.github/workflows/commit-lint.yml` uses this exact config path. |
| `mint.json` | Retired Mintlify root entrypoint | Absent from root baseline; do not restore without fresh tooling evidence and owner review. |

No root review/tooling file should move based only on naming preference. A move
requires tool-specific validation, updated workflows or external settings,
`.github/root-allowlist.txt` changes, and synchronized root-governance docs.
