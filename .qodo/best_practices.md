# BioETL Qodo Best Practices

These guidelines are repo-specific review patterns for Qodo. Keep feedback
aligned with `AGENTS.md`, `docs/00-project/RULES.md`, accepted ADRs, executable
tests, and committed governance/config surfaces.

## Architecture Boundaries

Prefer:

- Keep dependency direction inward: `interfaces -> application -> domain`,
  `infrastructure -> domain`, `composition -> application + infrastructure`.
- Route concrete runtime wiring through composition-owned entrypoints.
- Treat `src/bioetl/composition/**` as the only place for concrete DI.

Avoid:

- Direct `interfaces -> infrastructure` imports.
- Domain imports from application, infrastructure, composition, or interfaces.
- Application imports of concrete infrastructure implementations.

## Domain Purity

Prefer:

- Pure domain logic with deterministic state transitions and explicit
  invariants.
- Aggregate behavior centered on `Batch`, `PipelineRun`, and
  `QuarantineEntry`.

Avoid:

- HTTP, filesystem access, pandas, or concrete adapters in `src/bioetl/domain/**`.
- Business logic hidden inside infrastructure adapters.

## HTTP and I/O

Prefer:

- `UnifiedHTTPClient` for provider/runtime HTTP behavior.
- Async-safe patterns and repository-approved abstractions.

Avoid:

- Direct HTTP client usage in adapters when the unified client already covers
  the use case.
- New bespoke networking wrappers that bypass the sanctioned HTTP surface.

## Medallion and Validation

Prefer:

- Bronze as immutable append-only JSONL without normalization.
- Silver normalization plus mandatory Pandera validation before write.
- Gold writes behind strict Pandera schema validation with fail-closed behavior.
- Deterministic merges by primary key and idempotent reruns.

Avoid:

- Writing Silver or Gold outputs without their required validation step.
- Duplicate-producing reruns or merge behavior that ignores primary keys.

## Governance and Change Discipline

Prefer:

- Small, reversible patches with targeted validation evidence.
- Updating contributor/governance docs when repo-facing behavior or guidance changes.
- Explicitly calling out manual-inspection-required items for portal or GitHub UI state.

Avoid:

- Increasing technical-debt budgets, exemptions, or governance thresholds.
- Editing `.env` files without explicit user approval.
- Inventing undocumented Qodo keys or unsupported repo-level schemas.
