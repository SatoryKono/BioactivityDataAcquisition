# MkDocs Material Migration Track (2026-03-03)

*Status: active planning artifact (internal-published)*

## Objective

Mitigate forward-compatibility risk around MkDocs/Material while preserving current strict-docs quality gates.

## Trigger

`bash scripts/build_docs_site.sh --strict` is green, but Material emits a compatibility advisory for MkDocs 2.0.

## Owner and Cadence

- Owner: Documentation/Governance maintainers
- Cadence: weekly checkpoint until decision is accepted
- Reporting channel: `docs/reports/documentation-audit-2026-03-03-exhaustive.md`

## Strategy

1. **Stabilize current baseline (now)**
   - Keep current docs pipeline green (`check_doc_links`, KPI, strict build).
   - Keep nav-growth and orphan guardrails enforced.

2. **Evaluate migration paths (by 2026-03-17)**
   - Path A: pin current MkDocs-compatible stack for medium-term stability.
   - Path B: migrate to vendor-recommended static-site stack.
   - Compare effort/risk for CI, search, mkdocstrings, Mermaid, and navigation behavior.

3. **Decide and ratify (by 2026-03-24)**
   - Record final direction in an ADR or governance update.
   - Assign implementation owner and target release window.

4. **Execute in controlled rollout (target window 2026-03-24..2026-04-21)**
   - Prepare a compatibility branch.
   - Run full docs and architecture test suite.
   - Merge only with strict-build green and no KPI regressions.

## Acceptance Criteria

- Chosen path documented and approved.
- CI keeps passing on strict docs build.
- No increase in `orphan_candidates`.
- `not_in_nav` remains at or below current level unless explicitly approved.
