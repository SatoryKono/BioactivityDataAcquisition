# Compatibility Surface Issue Pack

Prepared: 2026-04-13
Repository: `SatoryKono/BioactivityDataAcquisition`

Notes:

- Duplicate-check searches against existing GitHub issues for `compatibility facade`, `measured-only`, `lineage`, and `compatibility surface` returned no matches at preparation time.
- Remote issue creation was not possible from this environment because no GitHub CLI or API token was available.

## Issue 1

Title: Enforce thin-facade policy for legacy lineage compatibility modules

Suggested labels: `architecture`, `tech-debt`, `compatibility`

Body:

```md
## Problem

Legacy lineage modules under `src/bioetl/application/services/` previously held duplicate implementations alongside the canonical `bioetl.application.services.lineage` package. That pattern turns a compatibility surface into a second logic surface and creates drift risk.

Representative files:
- `src/bioetl/application/services/metadata_assemblers.py`
- `src/bioetl/application/services/metadata_lineage_composite.py`
- `src/bioetl/application/services/metadata_lineage_fragments_bronze.py`
- `src/bioetl/application/services/metadata_lineage_nodes.py`

## Scope

- Audit all legacy lineage compatibility modules in `src/bioetl/application/services/`
- Ensure each legacy path is a thin re-export facade only
- Confirm no duplicate business logic remains outside `bioetl.application.services.lineage`
- Keep architecture boundaries unchanged

## Acceptance Criteria

- Every legacy lineage module contains only shim / re-export behavior
- No second implementation of lineage assembly remains in the flat services surface
- Targeted lineage/storage tests stay green
- Compatibility registry remains in sync after the change

## Risks

- Over-aggressive cleanup can break test patch targets or compatibility imports
- Partial migration can leave mixed logic and compatibility semantics in the same module
```

## Issue 2

Title: Add architecture guardrail against new first-party imports through measured-only compatibility seams

Suggested labels: `architecture`, `guardrails`, `compatibility`

Body:

```md
## Problem

Measured-only compatibility modules are intended to exist as compatibility surfaces, not as normal first-party import targets. Without a dedicated guardrail, new code can silently keep routing through legacy seams and expand transition debt.

Registry anchor:
- `configs/quality/compatibility_facade_inventory.yaml`

Existing guardrail anchor:
- `tests/architecture/test_compatibility_facade_inventory.py`

## Scope

- Add an architecture test that blocks new first-party imports of measured-only modules
- Keep retained public entrypoints separate from measured-only wrappers
- Allow only explicit, documented exceptions where needed

## Acceptance Criteria

- A failing test is produced when `src/` or ordinary tests import measured-only wrappers
- Retained public entrypoints are not incorrectly blocked by the same rule
- The rule is documented in compatibility-surface governance docs

## Risks

- Over-broad matching can block sanctioned entrypoints
- Under-specified exceptions can turn the rule into a noisy allowlist
```

## Issue 3

Title: Clarify retained-entrypoint vs measured-only policy in compatibility surface governance

Suggested labels: `docs`, `architecture`, `compatibility`

Body:

```md
## Problem

The compatibility surface currently mixes two different policy classes:
- retained public entrypoints
- measured-only wrappers

The distinction exists, but it needs to be made operationally explicit so readers and tests do not treat all compatibility rows the same way.

Primary docs:
- `docs/02-architecture/07-compatibility-facade-inventory.md`
- `docs/02-architecture/07-compatibility-facade-snapshot.md`

## Scope

- Tighten wording in compatibility docs
- Make the distinction between retained and measured-only explicit in governance language
- Align docs with the current registry and test behavior

## Acceptance Criteria

- Docs clearly state what is allowed for retained entrypoints
- Docs clearly state that measured-only wrappers are not normal import targets
- Snapshot, inventory, and tests use consistent terminology

## Risks

- Policy ambiguity leads to future registry drift
- Missing wording causes repeated review churn on the same seam class
```

## Issue 4

Title: Review and shrink measured-only compatibility surface in application services

Suggested labels: `tech-debt`, `compatibility`, `application-layer`

Body:

```md
## Problem

`src/bioetl/application/services/` now contains a broad measured-only compatibility surface across execution, control-plane, and lineage seams. Even when wrappers are thin, the maintenance cost grows with every extra compatibility path.

## Scope

- Review measured-only rows under `src/bioetl/application/services/`
- Classify each seam as `retain`, `promote`, or `remove`
- Define removal prerequisites where imports have already migrated
- Keep compatibility docs and tests synchronized

## Acceptance Criteria

- Every measured-only application-service seam has an explicit lifecycle decision
- Remove-ready seams are identified with exit criteria
- Registry and snapshot reflect the reduced or clarified surface

## Risks

- Premature removal can break hidden test or tooling imports
- Leaving the entire surface in place keeps transition debt effectively permanent
```

## Issue 5

Title: Eliminate test-generated drift in scripts inventory during compatibility snapshot checks

Suggested labels: `tooling`, `ci`, `compatibility`

Body:

```md
## Problem

Compatibility-surface validation can create incidental diff noise in `configs/quality/scripts_inventory_manifest.json`, even when no real inventory change is intended. That makes guardrail runs less trustworthy and introduces avoidable cleanup steps.

Observed artifact:
- `configs/quality/scripts_inventory_manifest.json`

## Scope

- Identify why compatibility-related test/check flows mutate the scripts inventory manifest
- Prevent generated-at or line-shift noise from creating unrelated git diffs
- Preserve legitimate inventory regeneration when explicitly requested

## Acceptance Criteria

- Compatibility-surface checks no longer mutate `scripts_inventory_manifest.json` as a side effect
- CI/local verification remains reproducible
- No manual revert is needed after a normal compatibility audit run

## Risks

- Fixing the symptom only can hide a deeper coupling between reporting pipelines
- Over-stabilizing generated files can suppress legitimate updates
```

## Issue 6

Title: Restore member drilldown for Neo4j duplication clusters used in compatibility and dead-code audits

Suggested labels: `observability`, `neo4j`, `audit-tooling`

Body:

```md
## Problem

Neo4j memory currently ranks top duplication clusters but does not always expose their member list. That makes duplication and compatibility-surface audits less explainable: the hotspot score is visible, but the concrete duplicated surface is not.

Relevant scripts:
- `scripts/memory/query.py`
- `scripts/memory/sync.py`

## Scope

- Investigate why some duplication clusters have scores but no `CONTAINS` member drilldown
- Fix the sync/query contract if needed
- Rebuild the relevant memory snapshot

## Acceptance Criteria

- Top duplication clusters can be expanded into concrete members
- Query behavior is consistent with sync semantics
- Compatibility/duplication audits can cite member-level evidence again

## Risks

- Query-side fixes alone may hide sync-side data loss
- Re-sync could change historical cluster IDs and require downstream adjustment
```

## Issue 7

Title: Add a ratchet for compatibility-surface growth

Suggested labels: `guardrails`, `architecture`, `tech-debt`

Body:

```md
## Problem

The measured-only compatibility surface can grow silently over time. Even when each addition is individually reasonable, the total maintenance cost and ambiguity increase if there is no explicit growth control.

Current generated companion:
- `docs/02-architecture/07-compatibility-facade-snapshot.md`

## Scope

- Introduce a ratchet or baseline check for compatibility-surface size
- Require explicit decision/update when the measured-only count increases
- Keep the ratchet compatible with intentional migrations

## Acceptance Criteria

- Growth in measured-only compatibility rows is detected automatically
- Intentional growth requires an explicit baseline or decision update
- Normal no-growth changes do not create review noise

## Risks

- Too-rigid ratchets can block legitimate staged migrations
- Too-soft ratchets provide little real governance value
```

## Issue 8

Title: Define lifecycle review workflow for measured-only compatibility seams

Suggested labels: `process`, `compatibility`, `tech-debt`

Body:

```md
## Problem

Measured-only seams have owners and review dates, but the practical review workflow is still too implicit. Without a clear review loop, compatibility wrappers risk becoming permanent storage for old paths.

Primary registry:
- `configs/quality/compatibility_facade_inventory.yaml`

## Scope

- Define what owners must verify at each compatibility review date
- Clarify decision outcomes: `retain`, `promote`, `remove`
- Document exit criteria for shrinking measured-only surfaces

## Acceptance Criteria

- Review cadence is documented and actionable
- Owners can tell when a seam should stay, be promoted, or be removed
- Compatibility surface gains a real retirement loop instead of passive tracking

## Risks

- Process without enforcement can decay into documentation-only governance
- Missing exit criteria will preserve wrappers indefinitely
```
