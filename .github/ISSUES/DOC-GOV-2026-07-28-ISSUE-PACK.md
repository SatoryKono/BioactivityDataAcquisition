# Documentation Governance Issue Pack — 2026-07-28

**Audit:** `reports/grok/review_docs_architecture_audit_20260728_FULL.md`
**Inventory:** `reports/grok/docs_architecture_audit_inventory_20260728.json`
**Branch:** `main`
**Mode:** documentation governance only — no architecture code refactor unless a doc fix requires a one-line accuracy note

## Snapshot (evidence)

| Signal | Value |
| --- | --- |
| Overall docs architecture score | ~70/100 |
| `docs/` files (scan) | ~3068 |
| `docs/reports/` | ~1221 files / ~15 MB (non-canonical mass) |
| Diagram renders | ~150–170 MB PNG/SVG |
| AI mirrors | ~224 MD under `docs/00-project/ai/` |
| Active prose 00–05 | ~7.9 MB |
| ADRs | 52 (2 superseded) |
| RULES | v6.1.4 |

## Goals

1. Reduce documentation noise ~50% without deleting protected SSOT (RULES, NORMATIVE, ADR, contracts, runbooks).
2. Fix critical drift (AI mirrors, DQ threshold narrative, aging architecture docs).
3. Close coverage gaps (composites ref, CI workflow map).
4. Harden docs governance gates.

## Constraints

1. **Do not delete** RULES, NORMATIVE_SOURCES, REQUIREMENTS, ADRs, canonical contracts, active runbooks, layer architecture docs, diagram **sources** (`.mmd`).
2. Code wins over docs; ADR wins over overview prose.
3. Prefer relocate/archive over rewrite.
4. No tech-debt **budget growth** in quality configs.
5. Do not reopen closed ARCH-* epics unless regression.

## Issue codes

## Issue codes — published

| Code | Pri | Issue | URL |
|------|-----|------:|-----|
| DOC-GOV-00 | meta | #6872 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6872 |
| DOC-GOV-01 | P0 | #6873 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6873 |
| DOC-GOV-02 | P0 | #6875 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6875 |
| DOC-GOV-03 | P0 | #6879 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6879 |
| DOC-GOV-04 | P0 | #6884 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6884 |
| DOC-GOV-05 | P1 | #6885 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6885 |
| DOC-GOV-06 | P1 | #6886 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6886 |
| DOC-GOV-07 | P1 | #6887 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6887 |
| DOC-GOV-08 | P2 | #6888 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6888 |
| DOC-GOV-09 | P2 | #6889 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6889 |

Publish record: `reports/quality/documentation-governance-2026-07-28-issue-publish.json`


| Code | Pri | Theme |
|------|-----|-------|
| DOC-GOV-00 | meta | Epic |
| DOC-GOV-01 | P0 | Relocate `docs/reports/evidence` mass out of published SSOT surface |
| DOC-GOV-02 | P0 | Diagram render retention / LFS / CI-artifact policy (ADR-040) |
| DOC-GOV-03 | P0 | AI mirror cleanup (py-code-bot + ownership drift) |
| DOC-GOV-04 | P0 | DQ multi-default threshold narrative SSOT (0.50 vs 0.20) |
| DOC-GOV-05 | P1 | Refresh `data-layers.md` + composite entity reference page |
| DOC-GOV-06 | P1 | CI/GHA workflow map (38 workflows) |
| DOC-GOV-07 | P1 | Superseded ADR banners + MkDocs exclude for non-canonical trees |
| DOC-GOV-08 | P2 | Archive plans/engineering closeouts; dual-lane nav hygiene |
| DOC-GOV-09 | P2 | Docs drift gates / ownership KPI (Phase 4 hardening) |
