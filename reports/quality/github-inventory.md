# GitHub Inventory (issues #10120, #10121, #10122)

Generated: 2026-09-05
Branch: fix/github-p1-p2-batch-10120-10125

## 1. Workflows count 49 vs 30

| Source | Count |
|---|---|
| local .github/workflows/*.yml (git ls-files) | 49 |
| API GET /repos/.../actions/workflows (enabled) | 30 |
| delta (disabled + reusable) | 19 |

Note: API returns enabled workflows; local includes reusable and disabled (e.g., temporary-main-telemetry-refresh-9973.yml removed in this PR).

## 2. Retention inventory (rg -n retention-days)

| retention | count | bytes | notes |
|---|---|---|---|
| 1 | 8 | - | noisy sharded logs, docker 1d |
| 3 | 12 | - | deprecated legacy, migrate to 1 or 7 |
| 7 | 22 | - | default |
| 14 | 18 | - | telemetry 14d |
| 30 | 11 | - | coverage 30d |

Policy: configs/quality/retention-policy.yaml (default 7, allowed 1/7/14/30, deprecated 3). Trivy cache type=gha verified in docker.yml:144.

## 3. Duplicates on: push+pull_request (before fix)

| workflow | before on | after on |
|---|---|---|
| e2e-matrix-health.yml | push [main,master,develop] + pull_request [main,master,develop] + schedule | push [main] + schedule |
| dashboard-first-window-noscroll.yml | push [main,master,develop] + pull_request [main,master,develop] | push [main] |
| port-contracts.yml | push [main,master,develop] paths + pull_request [main,master,develop] paths | push [main] paths |
| mutation-testing.yml | push [main,master] paths + pull_request paths | push [main] paths |

Evidence: wsl grep -n on: .github/workflows/*.yml and gh api runs head_sha length reduces only for duplicates.

## 4. Temporary workflow removal

- Removed .github/workflows/temporary-main-telemetry-refresh-9973.yml (leftover, not in pr-required decision matrix)
- Verified git ls-files no longer lists it; PR without ruleset enforcement change.

## 5. Ruleset enforcement check

- gh api repos/SatoryKono/BioactivityDataAcquisition/rulesets --jq .[].enforcement remains disabled (ruleset 13643213)
- No ruleset mutation in this PR.

## 6. Labels

- .github/labels.yml not created (no owner process per #10125). Sync via actions/label-sync or manual; documented in .github/CONTRIBUTING.md.
- gh label list consistency via API (209 labels per governance doc).

