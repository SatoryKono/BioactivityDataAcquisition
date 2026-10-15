## Source

- Campaign epic: #8592
- Wave: A
- leaf_id: `S01-domain-control_plane`
- BASE_SHA: `8f34de1cf14126908cba8326905b3ee224719537`
- Campaign artifact: `reports/quality/coderabbit/20260811/BLOCKERS.md`

## Confirmed blocker

The original sequential CodeRabbit CLI campaign returned `rate_limit` for
`S01-domain-control_plane` on the initial review and both bounded retries.
A later leaf-only retry completed at `2026-08-11T13:22:00.836474+00:00` with
`status=error`, `exit_code=1`, and `elapsed_s=60.9`. Its terminal NDJSON event
was a recoverable connection failure: `Connection failed: WebSocket closed`.
No `finding` event was returned, so no product defect or finding-to-issue
mapping was inferred from this unaudited scope.

Campaign state was rechecked after `HEAD` changed. The exact-cover matrix
remains valid and immutable at
`BASE_SHA=8f34de1cf14126908cba8326905b3ee224719537`; the leaf has 32 files and is
under the 300-file cap. Current `main` must win during later triage if a
successful review returns findings.

## Impact

This leaf remains unaudited, so the CR-FULL exact-cover campaign cannot satisfy
its completion gate until a later sequential retry succeeds.

## Constraints

- Do not run CodeRabbit scopes in parallel on the same API key.
- Keep each review leaf at or below 300 tracked files.
- Do not substitute invented findings for a blocked review.
- Do not grow technical-debt or quality budgets.

## Acceptance checklist

- [x] Retry only `S01-domain-control_plane` sequentially after a bounded
  cooldown.
- [ ] Confirm against current main (code wins).
- [ ] Produce `review_A_S01-domain-control_plane.log` with terminal status `ok`.
- [x] Normalize the retry result (zero returned finding events).
- [x] Map the continuing campaign blocker to GitHub issue #8603.
- [ ] Triage and create/link one GitHub issue for every accepted problem after
  a successful review.
- [x] Do **not** grow tech-debt / quality budgets.

## Evidence

- `reports/quality/coderabbit/20260811/run_summary.json`
- `reports/quality/coderabbit/20260811/progress.json`
- `reports/quality/coderabbit/20260811/review_A_S01-domain-control_plane.log`

This issue is a campaign blocker, not a product-code finding.
