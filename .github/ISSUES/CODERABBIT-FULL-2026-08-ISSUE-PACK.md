# CodeRabbit Full Residual Campaign — Issue Pack 2026-08

**Published:** 2026-08-05  
**Epic:** [#7688](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7688)  
**Source plan:** Exhaustive CodeRabbit review plan (agent session 2026-08-05)  
**Normative playbook:** `docs/03-guides/coderabbit-audit-playbook.md`  
**Config:** `.coderabbit.yaml` (`profile: assertive`)  
**CI:** `.github/workflows/coderabbit.yml`  
**Launcher:** `scripts/ops/run-coderabbit-reviews.sh`

## Precedence (do not invert)

1. Code / domain contracts / config  
2. Accepted ADRs + RULES  
3. Architecture tests and quality gates  
4. CodeRabbit findings (must map to evidence above)

**Conflict rule:** code wins. **Never** grow tech-debt budgets to silence CR.

## Published issues

| Code | Pri | Issue | URL |
|------|-----|------:|-----|
| CR-FULL (meta) | P1 | #7688 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7688 |
| CR-FULL-00 | P0 | #7689 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7689 |
| CR-FULL-01 | P1 | #7690 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7690 |
| CR-FULL-02 | P1 | #7691 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7691 |
| CR-FULL-03 | P1 | #7692 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7692 |
| CR-FULL-04 | P1 | #7693 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7693 |
| CR-FULL-05 | P2 | #7694 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7694 |
| CR-FULL-06 | P2 | #7695 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7695 |
| CR-FULL-07 | P1 | #7696 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7696 |
| CR-FULL-08 | P2 | #7697 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7697 |
| CR-FULL-09 | P2 | #7698 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7698 |

## Recommended order

```text
#7689 (preflight) ──┬── #7698 (secret/workflow, parallel OK)
                    │
                    ▼
        #7690 → #7691 → #7692 → #7693 → #7694 → #7695
        (CLI scopes sequential; rate limits)
                    │
                    ▼
                 #7696 FINDINGS triage + net-new issues only
                    │
                    ▼
              implement P0/P1 (one_issue_one_pr)
                    │
                    ▼
                 #7697 re-audit + FINAL.md + tag
```

## Scope matrix reminder (≤~300 files / run)

| Wave | Issue | Paths (split further if needed) |
|------|------:|-----------------------------------|
| A | #7690 | domain, composition, app-core, control_plane, adapters |
| B | #7691 | pipelines, storage slices, `configs/quality/**` |
| C | #7692 | adapters HTTP/resilience |
| D | #7693 | security + workflows + `tests/security` |
| E | #7694 | normative docs + grafana + dashboard guides |
| F | #7695 | `tests/architecture` + hot unit/integration subsets |

Launcher topics (optional complement):

1. architecture-boundaries  
2. adapters-resilience  
3. pipelines-determinism  
4. security  
5. contracts-docs-drift  

## Artifacts (expected)

```text
reports/quality/coderabbit/YYYYMMDD/
  00-preflight.md
  review_<scope>.log
  FINDINGS.md
  TRIAGE.md
  FINAL.md
```

## Hard constraints

1. Do not CLI-review entire monorepo in one shot.  
2. Sequential scopes (rate limits).  
3. WSL/Linux preferred for CLI on Windows.  
4. Reject style-only / speculative findings without gate evidence.  
5. De-dupe vs prior ARCH-CR / CODERABBIT-REAUDIT packs and open GRA issues.  
6. No quality/debt budget growth.

## Prior history (do not re-open without regression)

- `.github/ISSUES/ARCH-CR-2026-07-28-ISSUE-PACK.md`  
- `.github/ISSUES/ARCH-CR2-2026-07-29-ISSUE-PACK.md`  
- `.github/ISSUES/CODERABBIT-REAUDIT-2026-07-27-ISSUE-PACK.md` (#6706–#6715)  
- `reports/quality/architecture-coderabbit-2026-07-*`

## Labels used

`architecture`, `technical-debt`, `quality`, `governance`, `enhancement`,
`priority:high` / `priority:medium`, `audit-tooling`, `testing`,
`architecture-tests`, `documentation`, `docs-drift`, `observability`,
`data-quality`, `reproducibility`, `security`, `ci`
