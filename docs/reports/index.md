# Reports Index (Non-Normative)

This directory now serves as the curated repo-only reports surface. It is
**non-normative**: authoritative guidance lives in the canonical documentation
sets.

Canonical sources:

- docs/02-architecture — ADRs, architecture policies, and reference diagrams
- docs/03-guides — implementation and operational guides
- docs/04-reference — pipeline, provider, and contract specifications

## Publication Hygiene Note

- `docs/reports/` is a **repo-only** surface and is excluded from MkDocs.
- Reports, evidence packs, and derived summaries are intended for situational
  analysis and decision support.
- They may be more detailed or more current about a local investigation, but
  they still do not replace canonical project guidance in `docs/00-05`.
- Dated reports reused for current planning should carry a short freshness or
  rebaseline note when later waves change their live interpretation.
- top-level `reports/` remains the working area for
  generated and iteration-heavy outputs before curation.
- `docs/reports/` is intentionally narrower than `reports/`: it should act as a
  curated map, not as a second copy of raw working output families.

## Boundary Contract

Use the following routing rule before adding a new report-like artifact:

- current instructions / operator workflow / contract guidance -> `docs/00-05/`
- curated repo-only evidence, synthesis, or bounded internal memo -> `docs/reports/`
- generated, iterative, model-specific, or tool-heavy working output -> `reports/`
- historical retained context -> `docs/99-archive/`

`docs/reports/` SHOULD contain curated entrypoints and bounded artefacts.
It SHOULD NOT absorb raw review dumps or act as a second working-output tree.

## Main Entry Points

- this index page — short orientation note for the repo-only reports surface
- [`evidence/INDEX.md`](evidence/INDEX.md) — curated evidence, synthesis, decisions, risks, and roadmaps
- [`../../reports/README.md`](../../reports/README.md) — working-output taxonomy,
  retention, and cleanup rules for repo-root `reports/`
- [`docs/plans/README.md`](../plans/README.md) — active planning artifacts
- [`docs/99-archive/README.md`](../99-archive/README.md) — archive index for historical/superseded plans and baselines

## Recent Bounded Reports

- [`great-expectations-spike-2026-04-01.md`](great-expectations-spike-2026-04-01.md)
  — recommendation memo for issue `#2595` on whether Great Expectations should
  be adopted alongside the existing `Pandera` and DQ stack
- `docs-link-check-report.json` — generated repo-only docs link-quality report
  produced by `scripts/docs/check_doc_links.py --report-json ...` and uploaded
  in CI as the `docs-link-check-report` artifact
- `docs-parity-report.json` — generated repo-only config/spec parity report
  produced by `scripts/docs_parity_check.py`
- `../../reports/quality/sonar_baseline_report.json` — generated Sonar baseline
  report covering current quarantine size, wave mapping for `#3106-#3109`, and
  live Sonar status when a token-backed CI run is available

## Reading Pattern

- Start here if you need the current reports-surface map.
- Jump to `evidence/INDEX.md` if you need research traceability or decision
  support artifacts.
- Jump to `reports/README.md` if you need to decide whether a working report
  should stay in `reports/{LLM}/`, be consolidated into `reports/plans/` or a
  shared artefact family, or be staged in `reports/trash/`.
- Jump to `docs/plans/README.md` if you need active execution/backlog context.
- Jump to `docs/99-archive/README.md` only for historical context.

Use reports for situational evidence and derived outputs; always cross-check
canonical docs before applying any changes.
