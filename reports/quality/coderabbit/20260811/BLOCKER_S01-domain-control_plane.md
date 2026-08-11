## Source

- Campaign epic: #8592
- Wave: A
- leaf_id: `S01-domain-control_plane`
- BASE_SHA: `8f34de1cf14126908cba8326905b3ee224719537`
- Campaign artifact: `reports/quality/coderabbit/20260811/BLOCKERS.md`

## Confirmed blocker

The sequential CodeRabbit CLI campaign returned `rate_limit` for
`S01-domain-control_plane` on the initial review and on both bounded retries
(30 seconds and 60 seconds). No finding was inferred from the blocked scope.

## Impact

This leaf remains unaudited, so the CR-FULL exact-cover campaign cannot satisfy
its completion gate until a later sequential retry succeeds.

## Constraints

- Do not run CodeRabbit scopes in parallel on the same API key.
- Keep each review leaf at or below 300 tracked files.
- Do not substitute invented findings for a blocked review.
- Do not grow technical-debt or quality budgets.

## Acceptance checklist

- [ ] Retry `S01-domain-control_plane` sequentially after a bounded cooldown.
- [ ] Confirm against current main (code wins).
- [ ] Produce `review_A_S01-domain-control_plane.log` with terminal status `ok`.
- [ ] Normalize and triage every returned finding.
- [ ] Create or link one GitHub issue for every accepted problem.
- [ ] Do **not** grow tech-debt / quality budgets.

## Evidence

- `reports/quality/coderabbit/20260811/run_summary.json`
- `reports/quality/coderabbit/20260811/progress.json`
- `reports/quality/coderabbit/20260811/review_A_S01-domain-control_plane.log`

This issue is a campaign blocker, not a product-code finding.
