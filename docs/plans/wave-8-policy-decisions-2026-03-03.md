# Wave-8 Policy Decisions (2026-03-03)

*Status: proposal (policy-only, no automatic execution)*

## Objective

Define explicit policy decisions for the remaining `outside nav` backlog after wave-7 curated cleanup.

## Current State Snapshot

- Total docs: `676`
- In nav: `640`
- Outside nav: `36`
- Orphans: `0`
- Residual buckets:
  - `99-archive/**`: `33` files
  - `skills/global/.system/**`: `3` files

## Decision Package A: `99-archive/**` (33 files)

### Option A1 (Recommended): Keep non-nav as `archive`

- Keep current policy unchanged.
- Rationale:
  - preserves clean public navigation;
  - avoids mixing historical artifacts with active guidance;
  - aligns with governance (`archive` class is intentionally non-nav).
- KPI impact:
  - `outside nav`: no change (`36`)
  - orphans: no change (`0`)

### Option A2: Partial promotion (index-only discoverability)

- Add one curated index page in active nav that links to archive groups.
- Keep archive leaf files non-nav.
- Rationale:
  - improves discoverability without full nav noise.
- KPI impact:
  - `outside nav`: no change (`36`)
  - orphans: no change (`0`)

### Option A3: Full promotion of archive leaf files

- Move most/all `99-archive/**` files into nav.
- Rationale:
  - maximum click-discoverability.
- Risks:
  - large nav bloat;
  - weak signal-to-noise for current contributors;
  - higher maintenance overhead.
- KPI impact:
  - `outside nav`: potentially down to `3`
  - orphans: likely unchanged
- Recommendation: not advised under current publication policy.

## Decision Package B: `skills/global/.system/**` (3 files)

### Option B1 (Recommended): Keep non-nav as `internal-generated`

- Keep `.system` skill docs excluded from nav.
- Rationale:
  - they are internal/system implementation details;
  - current policy already classifies them as `internal-generated`;
  - avoids exposing low-level system internals in routine docs navigation.
- KPI impact:
  - `outside nav`: no change (`36`)
  - orphans: no change (`0`)

### Option B2: Promote selected `.system` docs

- Promote only high-utility pages (for example installer usage).
- Rationale:
  - easier operator onboarding for skill bootstrap workflows.
- Risks:
  - may blur boundary between repository-local skills and global/system runtime.
- KPI impact:
  - `outside nav`: `36 -> 35..33` (depending on promoted files)
  - orphans: no change (`0`) if links preserved

## Recommended Policy Baseline (Wave-8)

1. Accept **A1** for `99-archive/**`.
2. Accept **B1** for `skills/global/.system/**`.
3. Keep current KPI targets unchanged (`<=120` directional, `<=135` hard limit, `orphans=0`).

Expected result:
- preserve current stable state (`outside nav = 36`, `orphans = 0`);
- avoid nav inflation and policy churn;
- defer any further reduction to explicit governance change.

## If Governance Chooses Reduction Below 36

1. Apply **B2** first (small, low-risk impact up to `-3`).
2. Re-run safety gates:
   - `scripts/check_doc_links.py`
   - `scripts/report_docs_kpi.py --fail-on-breach`
   - `python -m mkdocs build --strict`
3. Reassess whether archive policy should change before considering any `99-archive/**` promotion.
