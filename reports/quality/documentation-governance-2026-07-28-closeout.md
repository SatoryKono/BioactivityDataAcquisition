# DOC-GOV-00..09 Closeout — 2026-07-28

| Field | Value |
| --- | --- |
| Epic | #6872 DOC-GOV-00 |
| Children | #6873 #6875 #6879 #6884 #6885 #6886 #6887 #6888 #6889 |
| Branch | `main` |
| Mode | documentation governance only |

## Delivered

### DOC-GOV-01 (#6873) — Relocate docs/reports evidence mass

- Bulk packs moved to `reports/docs-evidence/` (~30 MB / ~1181 files).
- Thin curated surface retained under `docs/reports/evidence/` (INDEX, README,
  project-test-health, legacy-compat, package-topology, technical-debt).
- `docs/reports/README.md` + `index.md` rebaselined as map-only.

### DOC-GOV-02 (#6875) — Diagram PNG/SVG retention

- Policy: `docs/02-architecture/diagrams/governance/render-retention.md`
- ADR-040 + POL-LLM-DIAGRAMS-001 updated.
- Tracked PNG baselines removed from git index (SVG retained for drift gate).
- `.gitignore`: `docs/02-architecture/diagrams/**/png/**`

### DOC-GOV-03 (#6879) — AI py-code-bot drift

- Global/local mirror skills reduced to **DEPRECATED TOMBSTONE**.
- Catalogs already mark deprecated; AGENTS remains authority.

### DOC-GOV-04 (#6884) — DQ 0.50 vs 0.20 narrative

- Fixed `dq-configuration.md` first table (`0.25` → **`0.50`** SSOT).
- Runbook + data-layers multi-default narrative retained/linked.

### DOC-GOV-05 (#6885) — data-layers + composites

- `data-layers.md` last verified → 2026-07-28; links DQ + composites.
- New `docs/04-reference/pipelines/composites.md`.
- Architecture index row for composites.

### DOC-GOV-06 (#6886) — CI workflow map

- New `docs/05-operations/ci-workflow-map.md` (38 workflows).

### DOC-GOV-07 (#6887) — ADR banners + MkDocs excludes

- Strong SUPERSEDED banners on ADR-003 / ADR-008.
- MkDocs excludes: `05-engineering/**`, `reports/evidence/**`, diagram png.

### DOC-GOV-08 (#6888) — Archive plans/engineering

- Plans thinned to active backlog + README; supporting → `docs/99-archive/plans/`.
- Engineering closeouts → `docs/99-archive/engineering/`; stub README left.
- `repo_structure_catalog.yaml` plans allowlist reduced to active backlog.

### DOC-GOV-09 (#6889) — Drift gates / ownership KPI

- Ownership table in `NORMATIVE_SOURCES.md`.
- Docs verification gate notes for drift + KPI.
- `report_docs_kpi.py` reports `docs/reports/` file count + size_mb.

## Verification

- `pytest tests/architecture/test_governance_freshness_protocol.py tests/architecture/test_docs_root_surface_governance_alignment.py` → green
- PNG tracked count after untrack: 0
- SVG remains tracked for PR drift

## Constraints honored

- No RULES/ADR/contract deletion
- Prefer relocate/archive
- No tech-debt budget growth
- Domain purity / composition DI not touched
