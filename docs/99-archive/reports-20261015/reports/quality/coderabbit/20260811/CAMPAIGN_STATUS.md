# CAMPAIGN_STATUS — CR-FULL 20260811

| Field | Value |
| --- | --- |
| Campaign | `CR-FULL-20260811` |
| Parent issue | #8592 |
| BASE_SHA | `8f34de1cf14126908cba8326905b3ee224719537` |
| Matrix leaves | 87 |
| Exact cover | `coverage_ok=True` (assignment) |
| Review terminal status | **partial** |
| Closeout UTC | `2026-08-11T18:34:24.375445+00:00` |
| Campaign status | `partial_complete_with_service_residual` |

## Leaf execution

| Status | Count |
| --- | ---: |
| ok (findings returned) | 5 |
| error | 70 |
| missing from progress.json | 12 |
| Total matrix leaves | 87 |

### Successful leaves (ok)
- `S01-domain-aggregates`
- `S01-domain-behavior`
- `S01-domain-composite`
- `S01-domain-config`
- `S01-domain-contracts`

### Service residual
- Connection/rate-limit failures dominate non-ok leaves (CodeRabbit CLI WebSocket closed / rate_limit).
- Logs exist under `review_*.log` for all 87 leaves; most are connection errors without finding events.
- **Do not invent findings** for blocked leaves.
- Residual tracker: #8603 (originally control_plane; residual now covers service-blocked exact-cover gap).

## Findings triage

| Triage status | Count |
| --- | ---: |
| confirm | 71 |
| reject | 63 |
| split_parent | 10 |
| duplicate | 1 |
| **total normalized** | **145** |

### Accepted severity (`confirm`)
`{'major': 43, 'minor': 24, 'critical': 3, 'trivial': 1}`

## Issues / streams

| Stream | Issue | Findings |
| --- | ---: | ---: |
| domain-behavior | #8643 | 37 |
| domain-other | #8644 | 31 |
| domain-aggregates | #8645 | 3 |

Maps: `ISSUES_MAP.json`, `ISSUES_CREATED.md`, `STREAMS.md`

## Deliverables checklist

- [x] `00-preflight.md` and exact-cover scope matrix
- [x] review log or blocker evidence for every leaf (logs present; blockers documented)
- [x] `FINDINGS.md`, `FINDINGS.jsonl`, `TRIAGE.md`, `DE_DUPE_MAP.json`
- [x] one created/linked issue for each accepted finding (via stream issues #8643–#8645)
- [x] `ISSUES_MAP.json` and `ISSUES_CREATED.md`
- [x] 3 exclusive implementation streams (`STREAMS.md`)
- [x] ground-truth posture: code/contracts outrank CR; rejects documented in TRIAGE
- [x] `FINAL.md` and `CAMPAIGN_STATUS.md`
- [ ] Exact-cover all leaves terminal `ok` — **NOT achieved** (service residual)

## Residual risk

1. **82 leaves** without successful finding extraction due to CodeRabbit service errors.
2. Re-run campaign leaves only when CLI auth/service is healthy (sequential, same API key).
3. Implementation of #8643–#8645 requires re-validation on current `main` (code wins).
4. No tech-debt budget increases authorized by this closeout.
