______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Tutorial: Working with the Quarantine System

**Issue:** #6542
**SSOT runbook:** [quarantine-management.md](../../05-operations/runbooks/quarantine-management.md)
**Aggregate:** ADR-051

## Why quarantine exists

Failed rows (DQ / schema / filter rejects) are isolated so disposition is
explicit. Quarantine is **not** a second Bronze and not silent drop storage.

## Workflow

```text
failure detected → classify → quarantine write → investigate → remediate → replay/purge
```

1. **Identify** — logs / metrics / DQ report show quarantine growth.
2. **Inspect**
   ```bash
   bioetl quarantine inspect --pipeline <pipeline-name> --limit 20
   ```
3. **Classify** — schema vs completeness vs filter rejection vs semantic rule.
4. **Remediate** — source data, profile, schema, or transformer (not thresholds first).
5. **Replay** when safe
   ```bash
   bioetl quarantine replay --pipeline <pipeline-name>
   ```
6. **Purge** only under retention policy
   ```bash
   bioetl quarantine purge --pipeline <pipeline-name> --older-than-days 30
   ```

## Investigation tips

| Signal | Meaning |
| --- | --- |
| Same `error_code` burst | Source or schema drift |
| Single outliers | Inspect Bronze payload |
| `FILTERED_OUT_SILVER` | Filter policy (not always bad data) |
| Spike after deploy | Profile/transformer regression |

## Monitoring

- DQ / Silver reject explorer panels
- Sequence: `docs/02-architecture/diagrams/sequence/05-quarantine-handling-sequence.mmd`

## Related

- [debug medallion tutorial](debug-medallion-layers.md)
- [DQ investigation procedures](../../05-operations/dq-investigation-procedures.md)
