# Plan Governance Issue Drafts Index

These files are publish-ready GitHub issue drafts created from the
2026-05-31 tech-debt blueprint refresh and reconciliation pass.

## Purpose

The issue pack covers **planning/governance drift**, not the already-open
implementation backlog under:

- `#4811` / `#4812-#4828`
- `#4764` / `#4765-#4772`
- `#4610` / `#4700-#4706`

Use this pack to close the remaining gap between:

- GitHub source-of-truth issue state
- local `.github/ISSUES/*` mirrors
- local `docs/plans/*` execution snapshots

## Publish Order

1. `PLAN-001-Sync-Tech-Debt-Zero-Epic-Mirror-With-GitHub-State.md`
2. `PLAN-002-Archive-Closed-Streams-D-E-In-Local-Tech-Debt-Planning-Surfaces.md`
3. `PLAN-003-Rebaseline-Tech-Debt-Planning-Metrics-And-Week-0-Assumptions.md`

## Notes

- These drafts are intentionally **governance-only** and should not be merged
  into the implementation streams as hidden scope.
- GitHub issue state remains the source of truth when a local mirror conflicts
  with the repository draft.
- Local `gh` CLI is not available in this workspace, so publication should use
  GitHub UI or an authenticated external workflow.
