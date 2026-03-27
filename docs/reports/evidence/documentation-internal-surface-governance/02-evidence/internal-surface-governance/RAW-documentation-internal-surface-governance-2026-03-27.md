# Raw Evidence Snapshot: documentation-internal-surface-governance

Date: 2026-03-27
Status: active

## Sources reviewed

- `docs/00-project/index.md`
- `docs/00-project/governance/07-doc-nav-policy.md`
- `docs/05-operations/deployment/deployment-guide.md`
- `docs/05-operations/deployment/k8s-summary.md`
- `docs/reports/evidence/INDEX.md`
- `mkdocs.yml`
- `scripts/ops/deploy-bioetl.sh`
- `./.venv/Scripts/python.exe -m scripts.docs check-links --links --specs --configs`
- `./.venv/Scripts/python.exe -m scripts.docs check-drift --ports --classes`
- `./.venv/Scripts/python.exe -m mkdocs build --strict --site-dir /tmp/site_evidence_refresh_check`

## Working observations

- The current governance surface no longer treats `plans/**` and `reports/**`
  as a broad internal-published MkDocs area; policy now classifies both as
  `internal + repo-only`, and `mkdocs.yml` excludes them from publication.
- The project hub still provides explicit discoverability for these repo-only
  surfaces by pointing readers to repository paths for `plans/`, `reports/`,
  and the top-level AI docs map.
- The factual doc-sync layer is green on the current tree:
  - `check-links --links --specs --configs`: pass
  - `check-drift --ports --classes`: pass
  - `mkdocs build --strict`: pass
- The remaining strict-build verbosity is excluded-surface information, not
  broken links or missing nav documents.
- Experimental deployment docs are now aligned with the helper script via the
  shared `BIOETL_IMAGE_REGISTRY` / `BIOETL_IMAGE_TAG` override model and
  placeholder `REPLACE_IMAGE_TAG` guidance.
- Mixed RU/EN wording still exists across some internal surfaces, but nothing
  in the current guard layer treats it as correctness drift.

## Option candidates

### Option A: Promote `docs/00-project/ai/README.md` into nav now

- Pros:
  - improves discoverability for readers who only scan MkDocs nav
  - reduces one remaining link-only entry surface
- Cons:
  - weakens the current curated repo-path/index-first model
  - still solves convenience more than correctness

### Option B: Keep AI and extended surfaces as curated repo-path entrypoints

- Pros:
  - matches the current `published` vs `repo-only` split
  - keeps nav focused on active normative docs
- Cons:
  - preserves some one-click discoverability friction for new readers

### Option C: Reopen a broad documentation remediation wave immediately

- Pros:
  - could remove more residual wording and publication noise
- Cons:
  - current evidence shows factual sync is already green
  - likely creates low-signal churn relative to the remaining issues

### Option D: Keep repo-only surfaces strict, but continue guard-based refresh

- Pros:
  - preserves traceability without over-publishing internal material
  - relies on repeatable guard outputs rather than large editorial waves
- Cons:
  - requires discipline to keep repository-path references fresh

### Option E: Launch a dedicated RU/EN normalization wave

- Pros:
  - improves stylistic consistency
  - may reduce readability friction in some internal clusters
- Cons:
  - current evidence still frames this as readability debt, not governance debt
  - creates broad low-signal churn

## Working impression

- Option B currently fits the AI/discoverability question best.
- Option D currently fits the publication/governance question best.
- Option E remains unjustified as an immediate wave.
