# Reports (Non-Normative)

This folder now focuses on **curated internal evidence and report artifacts**.
Content here is **non-normative**; authoritative guidance remains in:
- docs/02-architecture (ADRs, policies, diagrams)
- docs/03-guides (implementation and operations guides)
- docs/04-reference (pipelines, providers, contracts)

## Surface Model

- `docs/reports/README.md` is the short orientation note for this directory.
- [`index.md`](index.md) is the main entry point for navigating the current
  reports surface.
- [`evidence/INDEX.md`](evidence/INDEX.md) is the detailed entry point for
  evidence packs, synthesis, decisions, risks, and roadmaps.

Primary retained surface:
- [`evidence/`](evidence/)

Planning material that is still active should live in:
- [`docs/plans/`](../plans/)

Historical planning/baseline material should live in:
- [`docs/99-archive/README.md`](../99-archive/README.md)

Difference from top-level [`reports/`](../../reports/README.md):
- `docs/reports/` contains curated repo-only artifacts kept for traceability.
- top-level `reports/` contains generated or working outputs that do not
  automatically become part of the retained documentation surface.

Use reports for situational evidence, decisions, and curated internal analysis.

`docs/reports/**` is a blocked cleanup zone in
`configs/quality/repo_structure_catalog.yaml`. Cleanup here must stay bounded
and curated; do not treat this directory as disposable generated output.
