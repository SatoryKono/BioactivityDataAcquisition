______________________________________________________________________

Version: 1.0.0
Status: template
Class: internal
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# <Provider> <Entity> Pipeline Specification

**Pipeline ID:** `<provider_entity>`
**Provider:** `<provider>`
**Entity:** `<entity>`
**Runtime posture:** `<ADR-010 local-only note>`

## Identification

| Parameter             | Value                  |
| --------------------- | ---------------------- |
| Pipeline ID           | `<provider_entity>`    |
| Provider              | `<provider>`           |
| Entity                | `<entity>`             |
| Business primary keys | `<[field_a, field_b]>` |
| Loading strategy      | \`\<full_scan_only     |
| Gold status           | \`\<enabled            |

## Active Runtime Contract

- The spec MUST describe the current runtime, not historical intent.
- Active config paths MUST be listed.
- If Gold is disabled, the spec MUST say so explicitly.

## Source Files

| Component       | Path                                                                  |
| --------------- | --------------------------------------------------------------------- |
| Entity config   | `configs/entities/<provider>/<entity>.yaml`                           |
| Provider config | `configs/providers/<provider>.yaml`                                   |
| Transformer     | `src/bioetl/application/pipelines/<provider>/<entity>_transformer.py` |
| Adapter(s)      | `src/bioetl/infrastructure/adapters/<provider>/`                      |
| Contracts       | `src/bioetl/domain/contracts/gold/`                                   |

## ETL Flow

### Extract

- Source API, files, or upstream system MUST be identified.
- Request strategy, pagination, and rate limiting SHOULD be stated.

### Transform

- Canonical field groups MUST be summarized.
- Validation, normalization, and deduplication rules SHOULD be listed.

### Load

| Layer  | Status      | Format      | Mode       | Target   |
| ------ | ----------- | ----------- | ---------- | -------- |
| Bronze | \`\<enabled | disabled>\` | `<format>` | `<mode>` |
| Silver | \`\<enabled | disabled>\` | `<format>` | `<mode>` |
| Gold   | \`\<enabled | disabled>\` | `<format>` | `<mode>` |

## Validation and Quality

- Required fields MUST be listed or linked.
- DQ thresholds MUST reference the active policy/config source.
- Quarantine versus hard-fail behavior SHOULD be explicit.

## Operational Notes

- Resume, rebuild, and backfill behavior MUST be described when supported.
- Known failure modes SHOULD link to a runbook.
- Observability signals MAY be summarized if they are operationally relevant.

## CLI

```bash
bioetl config list-pipelines
bioetl run --pipeline <provider_entity>
bioetl run --pipeline <provider_entity> --limit 100
bioetl run --pipeline <provider_entity> --resume
```

## Compliance

| Control       | Requirement                                                   | Status   | Evidence |
| ------------- | ------------------------------------------------------------- | -------- | -------- |
| Runtime truth | Spec MUST match active config and current code paths          | \`\<pass | fail>\`  |
| Storage       | Silver MUST use Delta Lake; Gold behavior MUST be explicit    | \`\<pass | fail     |
| Contracts     | Gold contract link SHOULD exist when Gold schema is published | \`\<pass | fail     |
| Recovery      | Related runbook SHOULD be linked for failure handling         | \`\<pass | fail     |
| Governance    | Normative statements MUST use RFC 2119 keywords where binding | \`\<pass | fail>\`  |

## References

- `configs/entities/<provider>/<entity>.yaml`
- `configs/providers/<provider>.yaml`
- `docs/04-reference/providers/<provider>/<entity>.md`
- `docs/05-operations/runbooks/<related-runbook>.md`
