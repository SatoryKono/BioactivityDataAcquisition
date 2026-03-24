# Reports Index (Non-Normative)

This directory now serves as the curated internal reports surface. It is
**non-normative**: authoritative guidance lives in the canonical documentation
sets.

Canonical sources:
- docs/02-architecture — ADRs, architecture policies, and reference diagrams
- docs/03-guides — implementation and operational guides
- docs/04-reference — pipeline, provider, and contract specifications

## Publication Hygiene Note

- `docs/reports/` is an **internal-published** surface.
- Reports, evidence packs, and derived summaries are intended for situational
  analysis and decision support.
- They may be more detailed or more current about a local investigation, but
  they still do not replace canonical project guidance in `docs/00-05`.
- Dated reports reused for current planning should carry a short freshness or
  rebaseline note when later waves change their live interpretation.

## Main Entry Points

- [`README.md`](README.md) — short orientation note for the reports directory itself
- [`evidence/INDEX.md`](evidence/INDEX.md) — curated evidence, synthesis, decisions, risks, and roadmaps
- [`docs/plans/README.md`](../plans/README.md) — active planning artifacts
- [`docs/99-archive/README.md`](../99-archive/README.md) — archive index for historical/superseded plans and baselines

## Reading Pattern

- Start here if you need the current reports-surface map.
- Jump to `evidence/INDEX.md` if you need research traceability or decision
  support artifacts.
- Jump to `docs/plans/README.md` if you need active execution/backlog context.
- Jump to `docs/99-archive/README.md` only for historical context.

Use reports for situational evidence and derived outputs; always cross-check
canonical docs before applying any changes.
