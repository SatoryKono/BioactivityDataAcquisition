______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Diagram Render Retention Policy (ADR-040)

Implements DOC-GOV-02 / #6875. Complements
[ADR-040](../../decisions/ADR-040-diagram-governance.md) and
[policy.md](policy.md).

## Normative sources

| Artifact | Role | Git policy |
| --- | --- | --- |
| `docs/02-architecture/diagrams/**/*.mmd` | Canonical Mermaid sources | **Tracked** (required) |
| `docs/02-architecture/diagrams/views/**/*.mermaid` | Decomposed views | **Tracked** (required) |
| Sibling `**/svg/*.svg` | Rendered vector baselines for source-vs-render drift | **Tracked** (required for PR drift gate) |
| Sibling `**/png/*.png` | Raster previews (300 DPI) | **Not tracked** — generate locally or via CI artifacts |
| Targeted CI render artifacts | Operator/review evidence | Ephemeral workflow artifacts |

## Rules

1. **Sources are SSOT.** Edit `.mmd` / `.mermaid` only; never hand-edit PNG/SVG
   as the sole change without regenerating from source.
2. **SVG stays in git** so `check-diagram-drift` can require sibling SVG updates
   when sources change on PRs (see `.github/workflows/docs.yml`).
3. **PNG is render-only.** Contributors regenerate PNG via
   `bash docs/02-architecture/diagrams/tooling/render.sh` when needed for local
   review. CI full-corpus rendering is disabled; targeted render jobs may upload artifacts.
4. **Do not re-commit bulk PNG baselines** under
   `docs/02-architecture/diagrams/**/png/` (gitignored after DOC-GOV-02).
5. **MkDocs** may link SVG; missing local PNG must not block `mkdocs build`
   (link severity already relaxed for rendered images).

## Operator commands

```bash
# Lint sources (ADR-040)
python -m scripts.diagrams lint

# Render SVG+PNG for a changed directory
bash docs/02-architecture/diagrams/tooling/render.sh --dir docs/02-architecture/diagrams/architecture
```

## LFS note

Git LFS is optional for future SVG growth. Prefer keeping SVG tracked as plain
git binaries while corpus size stays acceptable (~25 MB). Revisit LFS only if
SVG mass exceeds clone budgets; do not use LFS for canonical `.mmd` text.

## Explicit non-goals (residuals)

| Item | Decision | Rationale |
| --- | --- | --- |
| Untrack bulk SVG / full CI-only SVG | **Declined** | PR `check-diagram-drift` requires tracked sibling SVG when sources change; SVG is primary SSOT render surface |
| Keep curated PNG in git for nightly | **Declined** | Nightly `render.sh` then `--require-png` on `png-compatibility.txt`; no git PNG needed |

## Acceptance

- [x] Policy documented and linked from ADR-040 / diagram governance policy
- [x] Tracked PNG baselines removed from git index (including curated smoke set)
- [x] SVG retained for drift gate (bulk SVG untrack explicitly declined)
- [x] CI continues to produce PNG artifacts on render jobs
