# Documentation Audit Report (BioETL v6.1.x governance sync)

## Summary

- Date: 2026-06-25
- Scope: canonical governance sync for `RULES.md`, `REQUIREMENTS.md`, active security guidance, traceability evidence, and executable governance artifacts tied to issues #5609, #5611, #5612, #5613, #5614, #5615
- Overall status: targeted governance defects confirmed and resolved in active owner surfaces; remaining work moved to verification artifacts instead of normative ambiguity

## Inventory

- Docs scanned: active governance surfaces under `docs/00-project/**`, `docs/01-requirements/**`, selected `docs/03-guides/**`, `docs/05-operations/**`, `README.md`, `.github/SECURITY.md`, and committed governance artifacts under `reports/quality/**`
- Entry points (README.md, mkdocs.yml): `README.md`, `mkdocs.yml`

## Findings by severity

### Critical

- None confirmed in current `main`

### High

- `docs/01-requirements/REQUIREMENTS.md` summary table still published `139 MUST`, even though the live corpus contains 156 requirements with one explicit `MAY`
- `docs/01-requirements/REQUIREMENTS.md` still contained stale observability wording that implied `run_id` belongs in Prometheus metrics and still used legacy hyphenated metric names
- `.github/SECURITY.md` still documented exact dependency pinning and a placeholder disclosure contact, both conflicting with the current canonical governance baseline

### Medium

- `docs/00-project/RULES.md` already reflected most ADR-048 / ADR-050 governance deltas, but did not state the pipeline-ID conflict guardrail explicitly in the owner surface
- `docs/00-project/RULES.md` required an explicit naming guardrail that `UnifiedHTTPClient` is the only sanctioned runtime HTTP abstraction unless a future ADR drives a controlled rename
- `docs/00-project/glossary.md` pointed to a stale `RULES.md` section anchor for pipeline naming conventions

### Low

- No active `CONTRIBUTING.md` was present, so the historical import-direction conflict did not require remediation in current `main`
- The historical missing-file defect for `.codex/agents/CODEX-RUNTIME.md` remains resolved and was intentionally not reopened

## Proposed changes (prioritized)

1. Update `docs/00-project/RULES.md` and `docs/01-requirements/REQUIREMENTS.md` first, because they are the canonical owner surfaces.
1. Synchronize active security guidance in `.github/SECURITY.md` with mixed dependency policy and real private disclosure flow.
1. Publish a repo-friendly traceability crosswalk and validation evidence so future governance drift can be audited without re-deriving the 156-entry corpus manually.

## Required decisions

- None for this closure batch; the confirmed defects were resolvable against current runtime, ADR, and gate evidence without introducing new semantics

## Updated files (if changes applied)

- `docs/00-project/RULES.md`
- `docs/00-project/glossary.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `.github/SECURITY.md`
- `docs/00-project/governance/governance-sync-audit-2026-06-25.md`
- `docs/01-requirements/traceability/requirements-traceability-crosswalk.csv`

## Dead or orphan docs (candidates)

- No new archive candidates were promoted by this sync
- Historical `CODEX-RUNTIME` remediation notes should remain historical only; current runtime source is already present under `.codex/**`

## Verification

- RULES.md and REQUIREMENTS.md sync: restored for summary counts, observability wording, pipeline-ID policy, and HTTP abstraction naming
- ADR alignment (ADR-010, ADR-014, ADR-017): revalidated; no contradictory owner-surface wording remained after the update
- Link check: pending execution in the post-change validation step
