# Documentation Navigation Policy

*Version: 1.4 (2026-03-03)*

----------------------------------------------------------------------

## Purpose

Define explicit navigation rules for documentation zones so that:
- normative pages stay discoverable in `mkdocs.yml`;
- internal and archive materials remain controlled;
- growth of non-nav pages is tracked via baseline guardrails.

----------------------------------------------------------------------

## 1. Zone Model (Path Prefix -> Status -> Nav Rule)

| Path Prefix | Status | Nav Rule | Required Entrypoint |
|---|---|---|---|
| `docs/00-project/**`, `docs/01-requirements/**`, `docs/02-architecture/**`, `docs/03-guides/**`, `docs/04-reference/**`, `docs/05-operations/**` | `published` | MUST be represented in primary nav (except explicit internal/archived subsections) | Section index page in nav |
| `docs/skills/**` | `internal-published` | MAY be shown only under `Internal / Extended -> Skills` | [docs/skills/README.md](../../skills/README.md) |
| `docs/plans/**` | `internal-published` | Curated pages MAY be shown under `Internal / Extended -> Plans` | [docs/plans/README.md](../../plans/README.md) or curated nav node |
| `docs/reports/**` | `internal-published` + `internal` | Curated pages MAY be in `Internal / Extended -> Reports`; bulk report artifacts MAY remain non-nav | [docs/reports/index.md](../../reports/index.md) |
| `docs/99-archive/**` | `archive` | MUST remain non-nav by default; historical context only | [docs/99-archive/README.md](../../99-archive/README.md) (or equivalent archive index) |

Notes:
- `internal-generated` documents (for example large generated index/variant sets) are allowed outside nav.
- Non-nav documents MUST NOT be used as the primary source of architecture or operational policy.

----------------------------------------------------------------------

## 2. Mandatory Rules

1. Every new document MUST be classified as `published`, `internal-published`, `internal`, `archive`, or `internal-generated`.
2. `published` documents MUST have a stable nav path in `mkdocs.yml`.
3. `internal-published` documents MUST be grouped under `Internal / Extended`.
4. `archive` documents MUST include an explicit historical/superseded disclaimer.
5. Any intentional growth of non-nav documents MUST update the baseline file `scripts/baselines/not_in_nav_baseline.txt`.

----------------------------------------------------------------------

## 3. Guardrails and Validation

```bash
# Full docs checks (links + legacy + nav + baseline growth)
./.venv/Scripts/python.exe scripts/check_doc_links.py

# Optional focused checks
./.venv/Scripts/python.exe scripts/check_doc_links.py --not-in-nav-growth
./.venv/Scripts/python.exe -m mkdocs build --strict
```

If non-nav growth is intentional:
1. Regenerate baseline list:
   `./.venv/Scripts/python.exe -c "from scripts.check_doc_links import get_not_in_nav_docs, NOT_IN_NAV_BASELINE_FILE; docs=get_not_in_nav_docs(); NOT_IN_NAV_BASELINE_FILE.write_text('\\n'.join(docs)+'\\n', encoding='utf-8')"`
2. Re-run `./.venv/Scripts/python.exe scripts/check_doc_links.py`.
3. Include a short rationale in PR/commit message (why growth is expected).

----------------------------------------------------------------------

## 4. Ownership

- Primary owner: Documentation/governance maintainers.
- Enforcement: CI checks (`check_doc_links`, MkDocs strict build, docs architecture tests).
- Review requirement: Changes to nav policy or baseline MUST be explicitly reviewed.
- `check_doc_links` MUST enforce path contracts for:
  - `REQUIREMENTS.md` -> `docs/01-requirements/REQUIREMENTS.md`;
  - governance links -> `docs/00-project/governance/**`.

----------------------------------------------------------------------

## 5. KPI and Weekly Control

Current KPI model for docs outside nav:

- Directional target: `not_in_nav <= 120` by `2026-06-30`.
- Blocking hard limit: `not_in_nav <= 135`.
- Blocking orphan budget: `orphan_candidates <= 0`.

Weekly CI control:

- Workflow: `.github/workflows/docs-kpi-weekly.yml`
- Script: `scripts/report_docs_kpi.py`
- Outputs:
  - `reports/docs-kpi/docs-kpi-weekly.json`
  - `reports/docs-kpi/docs-kpi-weekly.md`
  - GitHub Step Summary section

Failure policy:

- Weekly job fails if any blocking KPI is breached:
  - hard limit exceeded,
  - orphan budget exceeded,
  - growth above baseline detected.

----------------------------------------------------------------------

## 6. Curated Cleanup Playbook

`Curated cleanup` means reducing `not_in_nav` by targeted publication of high-value internal docs while keeping archive/generated bulk outside primary navigation.

### 6.1 Classification Matrix

| Class | Typical Paths | Default Action |
|---|---|---|
| `published` | policy, requirements, active runbooks | MUST be in primary nav |
| `internal-published` | selected `plans/**`, `reports/**`, `skills/**`, architecture extras | SHOULD be in `Internal / Extended` |
| `internal-generated` | generated indexes/variants (for example some diagram artifact indexes) | MAY stay outside nav, but MUST be linked from an index |
| `archive` | `99-archive/**` | MUST stay outside nav with archive disclaimer |

### 6.2 Selection Criteria (for nav promotion)

A document SHOULD be promoted when at least two criteria are true:

1. Used as a recurring operational/design reference.
2. Needed for onboarding or cross-team discoverability.
3. Stabilized (not a short-lived scratch artifact).
4. Has low maintenance risk if exposed in nav.

### 6.3 Execution Loop

1. Compute current state:
   - `./.venv/Scripts/python.exe scripts/report_docs_kpi.py`
2. Classify each outside-nav cluster (`archive`, `internal-generated`, `internal-published`).
3. Promote a small curated batch to nav (`Internal / Extended` first).
4. Ensure every non-promoted cluster has a discoverable index entrypoint.
5. Re-run:
   - `./.venv/Scripts/python.exe scripts/check_doc_links.py`
   - `./.venv/Scripts/python.exe -m mkdocs build --strict`
6. Update baseline only when growth is intentional and justified.

### 6.4 Current Backlog Snapshot (2026-03-03, wave-5)

- `outside nav`: `45`
- dominant buckets:
  - `99-archive`: `33` (`archive`, intentional)
  - `skills`: `12` (references/assets and system skill docs)

Interpretation:
- further reduction SHOULD focus on remaining `skills/**` reference pages;
- `99-archive/**` should remain out of nav unless governance policy changes.

Implementation note:
- docs KPI and nav-growth checks exclude generated local artifacts under `docs/site/**`.

----------------------------------------------------------------------

## Related Documents

- [Documentation Publication Policy](06-doc-publication-policy.md)
- [File Policy](03-file-policy.md)
- [RULES](../RULES.md)
