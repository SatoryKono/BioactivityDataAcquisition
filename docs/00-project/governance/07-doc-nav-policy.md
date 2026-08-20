______________________________________________________________________

Version: 1.9.2
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-04'

______________________________________________________________________

# Documentation Navigation Policy

______________________________________________________________________

## Purpose

Define explicit navigation rules for documentation zones so that:

- normative pages stay discoverable in `mkdocs.yml`;
- internal and archive materials remain controlled;
- growth of non-nav pages is tracked via baseline guardrails.

For current project guidance, the active published docs in `docs/00-05` remain
the source of truth. Materials in `docs/99-archive/**` preserve historical
traceability, but they are not normative for current project behavior.

______________________________________________________________________

## 1. Zone Model (Path Prefix -> Status -> Nav Rule)

| Path Prefix                                                                                                                                                                | Status                                                    | Nav Rule                                                                                                                                                                     | Required Entrypoint                                                                               |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `docs/00-project/**`, `docs/01-requirements/**`, `docs/02-architecture/**`, `docs/03-guides/**`, `docs/04-reference/**`, `docs/05-engineering/**`, `docs/05-operations/**` | `published`                                               | MUST be represented in primary nav (except explicit internal/archived subsections); published specialist families MAY be nested under a broader reference branch instead of owning a separate top-level tab | Section index page in nav                                                                         |
| `docs/00-project/ai/agents/**`                                                                                                                                             | `internal-published` + `internal`                         | Curated entrypoints MAY be shown only under `Internal / Extended -> Agents`; bulk profiles/aliases MAY remain non-nav                                                        | [docs/00-project/ai/agents/README.md](../ai/agents/README.md)                                     |
| `docs/00-project/ai/memory/**`                                                                                                                                             | `internal-published` + `internal` + `repo-only`           | Shared entrypoints MAY be shown under `Internal / Extended`; excluded README pages and specialized memory docs MAY remain repo-only/non-nav                                  | [docs/00-project/ai/memory/agent-memory.md](../ai/memory/agent-memory.md)                         |
| `docs/00-project/ai/prompts/**`                                                                                                                                            | `internal-published` + `internal-generated` + `repo-only` | Curated prompt indexes MAY be shown under `Internal / Extended`; collected/raw prompt copies and excluded overview pages MAY remain repo-only/non-nav                        | [docs/00-project/ai/prompts/README.md](../ai/prompts/README.md) |
| `docs/00-project/ai/skills/**`                                                                                                                                             | `internal-published`                                      | MAY be shown only under `Internal / Extended -> Skills`                                                                                                                      | [docs/00-project/ai/skills/README.md](../ai/skills/README.md)                                     |
| `docs/D-*.md`                                                                                                                                                              | `repo-only` + `draft-sync`                                | MUST stay outside MkDocs publication; each file MUST point to a canonical successor in `docs/00-05`                                                                          | Machine-readable catalog `configs/quality/repo_structure_catalog.yaml`                            |
| `docs/plans/**`                                                                                                                                                            | `internal` + `repo-only`                                  | Working plans MAY remain outside MkDocs publication; surface them from published docs only as repository paths or curated summaries when needed                              | Repository path `docs/plans/README.md`                                                            |
| `docs/reports/**`                                                                                                                                                          | `internal` + `repo-only`                                  | Curated evidence/report artifacts MAY stay outside MkDocs publication; published docs SHOULD reference them as repository paths or summarized findings rather than nav pages | Repository path `docs/reports/index.md`                                                           |
| `reports/**`                                                                                                                                                               | `repo-only`                                               | Repo-root generated/evidence outputs stay outside MkDocs publication and are surfaced only via repository paths, curated summaries, or published evidence indexes            | Repository path `reports/README.md`                                                               |
| `docs/99-archive/**`                                                                                                                                                       | `archive`                                                 | SHOULD remain non-nav by default; archive entrypoints SHOULD be linked as repository-path historical indexes rather than current-site navigation unless governance explicitly promotes them | Repository path `docs/99-archive/README.md` (or equivalent archive index)                         |

Notes:

- active project guidance comes from published docs in `docs/00-05`;
- `docs/99-archive/**` remains historical context only and does not override active guidance, even when curated entries are visible in nav;
- `docs/99-archive/README.md` is the stable repository-path landing page for archive discovery; it is not a required MkDocs nav page.
- `internal-generated` documents (for example large generated index/variant sets) are allowed outside nav.
- Path-classified bulk families MAY rely on their zone-level rule and entrypoint
  instead of per-file frontmatter.
- Non-nav documents MUST NOT be used as the primary source of architecture or operational policy.
- Package maps outside `docs/` (for example `src/**/README.md`) are
  `code-navigation-only` surfaces and intentionally stay outside MkDocs nav.

______________________________________________________________________

## 2. Mandatory Rules

1. Every new document MUST be classified as `published`, `internal-published`, `internal`, `repo-only`, `archive`, or `internal-generated`, either by per-file frontmatter or by an explicit ratified path-family rule in governance.
1. `published` documents MUST have a stable nav path in `mkdocs.yml`.
1. `internal-published` documents SHOULD be grouped under `Internal / Extended` when they are intentionally published in MkDocs.
1. `archive` documents MUST include an explicit historical/superseded disclaimer.
1. Any intentional growth of non-nav documents MUST update the baseline file `scripts/engineering/baselines/not_in_nav_baseline.txt`.

______________________________________________________________________

## 3. Guardrails and Validation

```bash
# Full docs checks (links + legacy + nav + baseline growth)
uv run python -m scripts.docs check-links

# Optional focused checks
uv run python -m scripts.docs check-links --not-in-nav-growth
uv run python -m scripts.docs build-site --strict
```

If non-nav growth is intentional:

1. Regenerate baseline list:

```bash
uv run python - <<'PY'
from scripts.docs.checks.check_links import (
    NOT_IN_NAV_BASELINE_FILE,
    get_not_in_nav_docs,
)

docs = get_not_in_nav_docs()
NOT_IN_NAV_BASELINE_FILE.write_text("\n".join(docs) + "\n", encoding="utf-8")
PY
```

2. Re-run `uv run python -m scripts.docs check-links`.
1. Include a short rationale in PR/commit message (why growth is expected).

______________________________________________________________________

## 4. Ownership

- Primary owner: Documentation/governance maintainers.
- Enforcement: CI checks (`python -m scripts.docs check-links`, MkDocs strict build, docs architecture tests).
- Review requirement: Changes to nav policy or baseline MUST be explicitly reviewed.
- `python -m scripts.docs check-links` MUST enforce path contracts for:
  - `REQUIREMENTS.md` -> `docs/01-requirements/REQUIREMENTS.md`;
  - governance links -> `docs/00-project/governance/**`.

______________________________________________________________________

## 5. KPI and Weekly Control

Current KPI model for docs outside nav:

- Directional target: `not_in_nav <= 120` by `2026-12-31`.
- Blocking hard limit: `not_in_nav <= 135`.
- Blocking orphan budget: `orphan_candidates <= 0`.

Weekly CI control:

- Workflow: `.github/workflows/docs-kpi-weekly.yml`
- Commands:
  - `uv run python -m scripts.docs check-drift --runtime-mirrors --freshness`
  - `uv run python -m scripts.docs check-kpi`
- Outputs:
  - `reports/docs-kpi/docs-kpi-weekly.json`
  - `reports/docs-kpi/docs-kpi-weekly.md`
  - GitHub Step Summary section

Failure policy:

- Weekly job fails if any blocking KPI is breached:
  - hard limit exceeded,
  - orphan budget exceeded,
  - growth above baseline detected.

______________________________________________________________________

## 6. Curated Cleanup Playbook

`Curated cleanup` means reducing `not_in_nav` by targeted publication of high-value internal docs while keeping archive/generated bulk outside primary navigation.

### 6.1 Classification Matrix

| Class                | Typical Paths                                                                                                      | Default Action                                                                                               |
| -------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `published`          | policy, requirements, active runbooks                                                                              | MUST be in primary nav                                                                                       |
| `internal-published` | curated `docs/00-project/ai/{agents,memory,prompts,skills}/**`, architecture extras, other stable internal mirrors | SHOULD be in `Internal / Extended`                                                                           |
| `repo-only`          | `docs/plans/**`, `docs/reports/**`, excluded AI entrypoints                                                        | SHOULD stay outside MkDocs and be referenced as repository paths                                             |
| `internal-generated` | generated indexes/variants (for example some diagram artifact indexes)                                             | MAY stay outside nav, but MUST be linked from an index                                                       |
| `archive`            | `99-archive/**`                                                                                                    | SHOULD stay outside nav by default; curated archive entrypoints MAY appear with explicit historical labeling |

Wave-9 note (2026-03-31):

- bulk non-nav backlog is currently dominated by path-governed families rather
  than misclassified active docs;
- primary residual buckets are:
  - `docs/00-project/ai/skills/local/**`
  - `docs/00-project/ai/agents/agents/**`
  - `docs/00-project/ai/prompts/collected/**`
  - `docs/00-project/ai/skills/_references/**`
  - `reports/**` / `reports/evidence/**`
- these buckets SHOULD be managed by curated entrypoints and path policy, not
  by forcing frontmatter onto every generated or operational artifact.

### 6.2 Selection Criteria (for nav promotion)

A document SHOULD be promoted when at least two criteria are true:

1. Used as a recurring operational/design reference.
1. Needed for onboarding or cross-team discoverability.
1. Stabilized (not a short-lived scratch artifact).
1. Has low maintenance risk if exposed in nav.

### 6.3 Execution Loop

1. Compute current state:
   - `uv run python -m scripts.docs check-kpi`
1. Classify each outside-nav cluster (`archive`, `internal-generated`, `internal-published`, `repo-only`).
1. Promote a small curated batch to nav (`Internal / Extended` first).
1. Ensure every non-promoted cluster has a discoverable index entrypoint.
1. Re-run:
   - `uv run python -m scripts.docs check-links`
   - `uv run python -m scripts.docs build-site --strict`
1. Update baseline only when growth is intentional and justified.

### 6.4 Historical Backlog Snapshot (2026-03-03, wave-7)

- `outside nav`: `36`
- dominant buckets:
  - `99-archive`: `33` (`archive`, intentional)
  - `skills`: `3` (system skill docs)

Freshness note (2026-03-28):

- This snapshot is retained for wave-7 traceability only and is not the current
  KPI baseline.
- Use the live output of `scripts.docs check-kpi` (or the current CI artifact)
  for present-state counts before making nav decisions.

Interpretation:

- further reduction SHOULD focus on explicit policy decisions for remaining `00-project/ai/skills/global/.system/**`;
- `99-archive/**` should remain out of nav unless governance policy changes.

Implementation note:

- docs KPI and nav-growth checks ignore generated local site artifacts (`docs/site/**`, `.mkdocs-site-tmp/**`).
- `docs/00-project/ai/skills/global/.system/**` is treated as `internal-generated` and SHOULD remain non-nav.
- docs KPI checks ignore generated documentation export artifacts:
  - `docs/exports/*.merged.md`
  - `docs/reports/docs-export-report-YYYY-MM-DD-HHMMSS.md`
- architecture sync checks (`tests/architecture/test_documentation_sync.py`) exclude generated docs artifacts from active-doc drift rules and validate them via dedicated generated-doc gates.
- `docs/00-project/ai/skills/local/nci-analysis/references/**` is published in nav (wave-7 curated promotion).

### 6.5 Wave-8 Ratified Decisions (2026-03-03)

Ratified baseline for residual non-nav backlog:

1. `99-archive/**` remains non-nav by default (`archive`).
1. `00-project/ai/skills/global/.system/**` remains non-nav by default (`internal-generated`).
1. Any deviation requires explicit governance revision.

Wave-9 ratification (2026-03-31):
4\. `docs/00-project/ai/agents/agents/**` remains non-nav by default as a bulk
path-classified family (`internal-generated`).
5\. `docs/00-project/ai/prompts/collected/**` remains non-nav by default as
`repo-only` / `internal-generated`.
6\. `docs/00-project/ai/skills/_references/**` and unpublished bulk
`docs/00-project/ai/skills/local/**` reference families remain non-nav by
default as `internal-generated`.
7\. `reports/**` and `reports/evidence/**` remain repo-only by default and are
governed through repository entrypoints / curated summaries rather than MkDocs nav.

Wave-10 ratification (2026-04-04):
8\. `docs/00-project/ai/README.md`, `docs/00-project/ai/agents/CLAUDE.md`,
`docs/00-project/ai/agents/orchestration/**`,
`docs/00-project/ai/agents/runtime/orchestration/**`,
`docs/00-project/ai/agents/policy/SPECIALIST_PROFILE_TEMPLATE.md`,
`docs/00-project/ai/memory/README.md`, `docs/00-project/ai/memory/memory-*.md`,
`docs/00-project/ai/skills/SKILLS-CATALOG.md`, and
`docs/00-project/ai/skills/global/.system/**` remain non-nav by default as
repo-only or internal-generated AI support surfaces.
9\. `mkdocs.yml` SHOULD mirror these ratified path families in `not_in_nav`
when they are intentionally excluded from primary nav, so docs tooling and
governance classify the same AI families consistently.

Decision record:

- retained in this policy revision; no separate archived `wave-8` decision file is currently kept in the repository

______________________________________________________________________

## Related Documents

- [Documentation Publication Policy](06-doc-publication-policy.md)
- [File Policy](03-file-policy.md)
- [RULES](../RULES.md)
