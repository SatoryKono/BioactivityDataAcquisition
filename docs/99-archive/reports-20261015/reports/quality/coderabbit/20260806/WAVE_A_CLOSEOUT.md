# Wave A closeout addendum — rate-limited domain leaves (#7946)

- Parent: #7690 / epic #7688
- Dates: 2026-08-06T13:25Z (campaign FINAL) · 2026-08-06T13:45Z (retry evidence)
- Issue state: **CLOSED** (campaign FINAL) with optional product fix from retry

## Leaf disposition (retry 2026-08-06)

Method: `cr-scope-*` worktree + `coderabbit review --base-commit HEAD^ --agent --light` (CLI 0.7.2).

| Leaf | Disposition | Retry result |
| --- | --- | --- |
| S01-domain-exceptions | **Retried OK** | major 13 / minor 4 / trivial 1 |
| S01-domain-entities | **Retried OK** | major 22 / minor 6 / trivial 8 |
| S01-domain-value_objects | **Retried OK** | critical 1 / major 19 / minor 5 / trivial 24 |
| S01-domain-schemas | **Still rate_limit** after multi-hour backoff | no findings stored |
| S01-domain-control_plane | **Still rate_limit** after multi-hour backoff | no findings stored |
| S04-app-services-quality | **Still rate_limit** after multi-hour backoff | no findings stored |

Machine-readable: `reports/quality/coderabbit/20260806/DOMAIN_RETRY_7946.json`

## Already recovered (pre-#7946)

- S01-domain-aggregates (retry OK)
- S01-domain-ports / contracts (first pass)

## Net-new path clusters

Open critical/major path-cluster inventory on main remains **0**
(`reports/quality/coderabbit/_live/OPEN_CRITICAL_MAJOR_STREAMS.md`).

Retry findings were triaged against current code (code wins). No new GitHub
path-cluster issues filed. One still-valid critical was fixed product-side:

- `src/bioetl/domain/value_objects/bronze_result.py` — guard
  `compression_ratio` when `compressed_size == 0` (ZeroDivisionError).

Remaining rate-limited leaves are **explicitly skipped** for further CLI burn:
continuous residual is PR GitHub App + architecture gates; usage-based billing
optional for owners who want full leaf re-scan later.

## Acceptance checklist (#7946)

- [x] Re-run after rate-limit window (3/6 recovered; 3/6 still limited with evidence)
- [x] Publish major+ net-new path clusters only — **none** (inventory C+M = 0)
- [x] WAVE_A_CLOSEOUT.md updated (this file)
- [x] No tech-debt budget growth
