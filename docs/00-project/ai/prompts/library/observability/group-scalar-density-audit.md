---
id: prompt.observability.group-scalar-density-audit
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - REPO
  - SCOPE
  - MODE
  - LANGUAGE
  - ALLOW_ISSUE_WRITE
  - MONITORING
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/finding-schema.md
  - fragments/bi-check-schema.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
related_ssot:
  - AGENTS.md
  - docs/01-requirements/DASHBOARD_REQUIREMENTS.md
  - docs/03-guides/dashboards/contracts/layout-budgets.yaml
  - scripts/engineering/qa/report_dashboard_scalar_density.py
  - tests/integration/test_dashboard_geometry_and_purpose_contracts.py
  - tests/integration/test_grafana_layout_and_metadata.py
  - docs/03-guides/dashboards/design-system.md
anti_patterns:
  - Counting timeseries/table/text values (runtime-dependent) into density
  - Treating a large single-value stat as dense because it is "data"
  - Converting a stat into a table purely to evade the metric
  - Editing gridPos without updating pinned layout tests or re-checking DASH-FIT / first-screen / no-overlap / visual-semantics
  - Raising any debt budget or adding an ungoverned allowlist entry
  - Data/first-screen FAIL from a screenshot alone
tags: [observability, dashboard, grafana, density, scalar, audit, operator]
summary: Re-measure scalar information density per panel group vs first screen (DASH-DENSITY-002) and rank groups that must be made denser
max_body_lines: 150
---

# Group scalar information-density audit (DASH-DENSITY-002)

Re-evaluate **scalar information density** for every panel group of each shipped
dashboard and identify the groups that must be made denser than the first screen.

**Metric** (`DASH-DENSITY-002`, REQUIREMENTS §5.4):
`ρ(surface) = Σ values / Σ (gridPos.w × gridPos.h)` over **scalar** panels only
(`stat`/`gauge`/`bargauge`). One value per reduced scalar; a multi-value scalar
(`reduceOptions.values = true`) counts its non-hidden targets. **Exclude**
`timeseries`/`table`/`text`/`row` — their value count is runtime-dependent.

**Invariant:** for every group (a `row`) with ≥1 scalar panel,
`ρ_group > ρ_first_screen` of the same dashboard. First screen = root, non-row
scalar panels with `gridPos.y < 18` (`FIRST_WINDOW_Y`).

Skill: **observability-dashboard**. Static metric — **no monitoring/render** needed.

## Params

| Param | Default |
| --- | --- |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `SCOPE` | `grafana/dashboards` (or uid/path list) |
| `MODE` | `survey` (also: `propose-patches`) |
| `LANGUAGE` | `ru` |
| `ALLOW_ISSUE_WRITE` | `false` |
| `MONITORING` | `false` (not needed; static) |

## Method

1. **Inventory groups:** each `type:"row"` + its scalar children (measured within
   the parent row). Also collect first-screen scalar panels (`y < 18`, root, non-row).
2. **Survey (source of truth):**
   `python -m scripts.engineering.qa report-dashboard-scalar-density --json`
   (Windows: `.\.venv-win\Scripts\python.exe -m ...`). It emits per-group `ρ`,
   first-screen `ρ`, and `PASS` / `FAIL` / `n/a`, and writes
   `reports/quality/dashboard-scalar-density.{json,md}`.
3. **Verify by hand on ≥1 group:** list its scalar panels with `area = w×h` and
   value counts; recompute `ρ`. Never report a number without the panel list as
   evidence (evidence-contract).
4. **Classify each group:**
   - `PASS` — `ρ_group > ρ_first`
   - `FAIL` — `ρ_group ≤ ρ_first` → **needs higher density**
   - `n/a` — no scalar panels in the group, or the first screen has none (exempt)
5. **Rank FAIL groups** by density gap `ρ_first − ρ_group` (largest first), then by
   wasted scalar area (`Σ area` at low `ρ`).

## Identify groups needing higher density

For each `FAIL` group emit a finding (finding-schema, PROVEN only):

- dashboard `uid` + `row id/title`
- `scalar_count`, `Σ area`, `ρ_group`, `ρ_first`, `gap`
- sparsest panels (largest area for one value), each with `path:line`
- proposed remediation (below) + expected `ρ` after fix

## Remediation options (`MODE=propose-patches`)

Raise `ρ_group` above `ρ_first` by either:

- **Consolidate** N single-value stats into one compact `table`/`bargauge`
  (many values, one footprint) — highest-leverage fix; or
- **Shrink** oversized scalar cards (`24×6` / `12×6` → `6×4`).

Constraints (MUST re-verify; do not break):

- update the **pinned** coordinates in `tests/integration/test_grafana_layout_and_metadata.py`;
- keep `DASH-FIT-001/002/003`, the first-screen contract, no-overlap/no-gap,
  `check-dashboard-visual-semantics`, and PromQL/query governance green;
- **debt budgets unchanged**; use the governed `scalar_density` allowlist
  (`owner + rationale + retire_when`) only for a justified single-headline-scalar
  exception.
- After a dashboard's groups all `PASS`, enroll its uid in
  `scalar_density_enforced_uids` (`layout-budgets.yaml`) to lock it.

## Output

```text
reports/quality/dashboard-scalar-density.{json,md}      # survey artifact
reports/audit/bi-dashboard/scalar-density-findings.json # FAIL groups (PROVEN)
```

Optional proposed patches under the same tree when `MODE=propose-patches`.

## Stop

- All groups `PASS`/`n/a` → `NO_ACTIONABLE_FINDINGS`.
- No shell to run the survey → compute `ρ` statically from JSON geometry and
  record the blocker; **never invent** value counts for `timeseries`/`table`.
- Do not apply geometry edits without re-running the pinned layout tests and the
  DASH-FIT / first-screen / visual-semantics gates.

## Related

- `prompt.observability.dashboard-audit-cycle` — full cyclic audit (`density` contour)
- `prompt.observability.bi-dashboard-acceptance` — visual/layout/data acceptance
- `prompt.observability.dashboard-panel-audit` — per-panel render/fill defects
