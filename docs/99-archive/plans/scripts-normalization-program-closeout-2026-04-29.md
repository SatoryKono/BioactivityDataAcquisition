# Scripts Normalization Program Closeout 2026-04-29

## Scope

This note closes the April 2026 scripts normalization and cleanup program.

It aggregates the end state reached by the wrapper caller-matrix work, the
retained-surface audits, the inventory reclassification waves, and the
temporary-diagnostic TTL execution waves.

## Final Inventory State

Current inventory snapshot:

- `scripts=354`
- `active=325`
- `supporting=29`
- `temporary_diagnostic=0`
- `orphan=0`
- `unknown=0`
- `legacy=0`

## Program Outcomes

### 1. Low-risk wrapper cleanup is complete

Removed or fully closed:

- historical docs wrappers
- dev MCP setup wrappers
- thin repo shell wrappers
- thin Windows/WSL convenience tails
- dead one-shot troubleshooting helpers

### 2. Canonical router surface is stabilized

Retained canonical public Python/domain routers include:

- `python -m scripts.docs`
- `python -m scripts.diagrams`
- `python -m scripts.schema`
- `python -m scripts.engineering.dev`
- `python -m scripts.engineering.repo`
- `python -m scripts.engineering.ci`
- `python -m scripts.engineering.qa`
- `python -m scripts.engineering.diagnostics`
- `python -m scripts.engineering.baselines`
- `python -m scripts.ops`
- `python -m scripts.ops.data`
- `python -m scripts.ai`
- `python -m scripts.ai.mcp`

Compatibility-only Python surface retired after the later 2026-05-21 caller
audit:

- `python -m scripts.ai.vibe`

The canonical Vibe dispatch surface is `python -m scripts.ai vibe`.

### 3. Retained high-risk surfaces are now explicit

The following are not cleanup backlog anymore:

- `scripts/docs/build_docs_site.sh`
- retained `scripts/ops/launchers/codex/*`
- `scripts/ai/codex/run-codex.*`
- `scripts/ai/mcp/*_wrapper.*`
- retained `supporting` helper/compatibility modules

These surfaces now require dedicated parity/redesign work, not generic delete
waves.

### 4. Temporary diagnostics are fully resolved

The former `temporary_diagnostic` bucket converged to:

- delete dead helpers
- promote documented operator/setup commands into `active`
- move shims/helpers into `supporting`

No unresolved TTL diagnostic queue remains.

## Boundary Decisions

### Active

`active` now means a maintained workflow surface with sufficient operational,
test, script, or documented usage to justify continued support.

### Supporting

`supporting` now means an intentional retained helper or compatibility surface,
not an unresolved cleanup tail.

### No unresolved cleanup classes remain

The inventory no longer contains:

- `orphan`
- `unknown`
- `legacy`
- `temporary_diagnostic`

This is the key program end state.

## Reading Order

For detailed wave history, use these supporting notes:

- `scripts-cli-wrapper-caller-matrix-2026-04-28.md`
- `docs/99-archive/plans/docs-cli-wrapper-closeout-2026-04-28.md`
- `docs/99-archive/plans/build-docs-site-parity-audit-2026-04-29.md`
- `mcp-wrapper-deep-audit-2026-04-29.md`
- `repo-governance-wrapper-closeout-2026-04-29.md`
- `scripts-supporting-retained-set-closeout-2026-04-29.md`
- `docs/99-archive/plans/temporary-diagnostic-program-closeout-2026-04-29.md`

## Follow-Up

Future scripts work should not reopen a generic cleanup program.

The only justified next moves are:

- caller-audit-driven deprecation of a specific surface
- parity/redesign work for retained transport/contract layers
- explicit lifecycle reclassification when a helper becomes operational
- governance maintenance when docs/catalog/tests need sync
