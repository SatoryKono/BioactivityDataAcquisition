# Documentation Cascade Audit Report

## Summary
- Date: 2026-03-27
- Scope: full repo documentation cascade audit for canonical docs entry points, MkDocs navigation/published surface, archive/internal surface boundaries, and repo-health documentation signals tied to active developer workflows.
- Overall status: completed with fixes applied.
- Result: no active documentation blockers remain in the repository docs surface after this pass.

## Inventory
- Markdown pages scanned under `docs/`: `1042`
- Canonical entry points reviewed: `README.md`, `mkdocs.yml`, `docs/INDEX.md`, `docs/00-project/index.md`, `docs/00-project/00-map.md`, `docs/00-project/TOOLS.md`
- Governance and architecture anchors reviewed:
  - `docs/00-project/governance/07-doc-nav-policy.md`
  - `docs/01-requirements/REQUIREMENTS.md`
  - `docs/00-project/RULES.md`
  - `docs/02-architecture/decisions/ADR-039-unified-entity-config-format.md`
- Baseline content claims verified:
  - providers in `configs/providers/*.yaml`: `7`
  - provider entity pipelines in `configs/entities/*/*.yaml`: `21`
  - composite pipelines in `configs/composites/*.yaml`: `5`
  - ADR files in `docs/02-architecture/decisions/ADR-*.md`: `45`

## Findings

### High
- The published docs surface still treated repo-only/archive surfaces as if they were normal published pages.
  - `mkdocs.yml` included a nav reference to excluded archive content.
  - top-level documentation entry points linked users to repo-only archive or AI surfaces with ordinary published-page links.
  - Impact: confusing published navigation, noisy MkDocs validation, and blurred boundary between canonical docs and repo-only/internal docs.
  - Status: fixed.

### Medium
- The scripts inventory manifest had drifted out of sync with the actual `scripts/` tree.
  - Impact: governance/documentation tooling reported stale repo-health metadata.
  - Status: fixed by regenerating `configs/quality/scripts_inventory_manifest.json`.

### Low
- No additional active low-severity documentation defects were confirmed after the final verification pass.

## Changes Applied
- Removed the excluded archive page from MkDocs nav:
  - `mkdocs.yml`
- Reframed repo-only/archive references as repository paths instead of published-page links:
  - `docs/INDEX.md`
  - `docs/00-project/index.md`
  - `docs/00-project/00-map.md`
  - `docs/00-project/TOOLS.md`
  - `docs/00-project/governance/07-doc-nav-policy.md`
  - `docs/02-architecture/decisions/ADR-039-unified-entity-config-format.md`
- Regenerated the scripts inventory manifest to eliminate repo-health drift:
  - `configs/quality/scripts_inventory_manifest.json`

## Verification
- Link/config/docs drift:
  - `./.venv/Scripts/python.exe -m scripts.docs check-links --links --specs --configs` — passed
  - `./.venv/Scripts/python.exe -m scripts.docs check-drift --ports --classes` — passed
- Repo-health/documentation-adjacent inventory:
  - `./.venv/Scripts/python.exe -m scripts.repo check-inventory --update` — applied
  - `./.venv/Scripts/python.exe -m scripts.repo check-inventory --check` — passed
  - inventory summary: `scripts=208 active=105 unknown=18 orphan=79 legacy=6`
- Published docs build:
  - `./.venv/Scripts/python.exe -m mkdocs build --strict` — passed
  - result: `Documentation built in 62.27 seconds`
- Additional low-signal doc hygiene:
  - `./.venv/Scripts/python.exe -m scripts.docs check-docstrings --summary` — passed
  - summary: `modules=100.0% classes=99.7% functions=95.5% (missing=163)`

## Residual Watchlist
- Internal/repo-only AI and report surfaces remain intentionally outside the canonical published docs surface.

## Updated Files
- `mkdocs.yml`
- `docs/INDEX.md`
- `docs/00-project/index.md`
- `docs/00-project/00-map.md`
- `docs/00-project/TOOLS.md`
- `docs/00-project/governance/07-doc-nav-policy.md`
- `docs/02-architecture/decisions/ADR-039-unified-entity-config-format.md`
- `configs/quality/scripts_inventory_manifest.json`
