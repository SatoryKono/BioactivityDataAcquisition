______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Tutorial: Debug Data in Bronze / Silver / Gold

**Issue:** #6540
**SSOT:** [data-layers.md](../../02-architecture/data-layers.md), ADR-014, ADR-018,
[pipeline-failure-dq](../../05-operations/runbooks/pipeline-failure-dq.md)

## Investigation workflow

1. Identify **layer** (logs, exception type, quarantine category).
2. Inspect **control-plane** artifacts (`run_manifest`, effective config, ledger)
   before mutating data.
3. Sample the smallest batch that reproduces the issue.
4. Fix **source of truth** (schema/profile/config/code) — do not hand-edit Silver
   outside pipeline write semantics.

## Bronze (raw, append-only)

**Path:** `data/output/bronze/{provider}/{entity}/{date}/` (JSONL + zstd).

| Symptom | Checks |
| --- | --- |
| Empty Bronze | HTTP/adapter errors, rate limit, pre-write filters |
| Parse/encoding errors | First/last JSONL lines; UTF-8 |
| Missing run linkage | Sidecar meta vs run_manifest |
| “Lost” historical raw | Append-only — check earlier dates/runs |

## Silver (normalized Delta)

**Path:** `data/output/silver/{provider}/{entity}/`

| Symptom | Checks |
| --- | --- |
| Upsert no-op | `content_hash` unchanged; sort contract (ADR-014) |
| Pandera fail | Domain schema vs normalization profile |
| DQ hard fail | Hierarchical **0.50** vs Silver-request **0.20** — [dq-configuration](../dq-configuration.md) |
| Filter rejects | Silver filter quarantine category |

## Gold (strict consumer contract)

| Symptom | Checks |
| --- | --- |
| Strict validation fail | ADR-018 Gold contracts |
| Downstream mismatch | Gold schema vs consumer expectation |
| History surprises | Confirm history/SCD is actually configured |

## Tools

- Pandera schemas + gold contracts under `src/bioetl/domain/`
- Quarantine inspect CLI ([quarantine tutorial](quarantine-system.md))
- Metrics series ([metrics-monitoring](../metrics-monitoring.md))
- [replay-guide.md](../replay-guide.md)

## Related

- [DQ investigation procedures](../../05-operations/dq-investigation-procedures.md)
- [common-errors](../../05-operations/troubleshooting/common-errors.md)
