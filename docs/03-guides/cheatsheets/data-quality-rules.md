______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Data Quality Rules Reference

Operator and config-author reference for BioETL DQ hierarchy, thresholds, and investigation.

**Issue:** #6537 · **Normative:** [RULES.md](../../00-project/RULES.md) §2.1 / §2.8 · **ADRs:** [ADR-027](../../02-architecture/decisions/ADR-027-dq-rules-externalization.md), [ADR-038](../../02-architecture/decisions/ADR-038-enum-externalization.md), [ADR-045](../../02-architecture/decisions/ADR-045-dq-contract-system.md)

## Table of contents

- [DQ hierarchy (ADR-027)](#dq-hierarchy-adr-027)
- [Thresholds](#thresholds)
- [Rule categories](#rule-categories)
- [Invalid-row disposition](#invalid-row-disposition)
- [Common patterns](#common-patterns)
- [Investigation procedures](#investigation-procedures)

## DQ hierarchy (ADR-027)

```text
configs/base/quality.yaml
        ↓ overrides
configs/providers/{provider}.yaml  # optional quality: block
        ↓ overrides
configs/entities/{provider}/{entity}.yaml  # optional quality: block
        ↓ runtime
DQ loader / Pandera contracts / write-time validation
```

| Layer | Path | Role |
| --- | --- | --- |
| Base | `configs/base/quality.yaml` | Global thresholds, common field validations |
| Provider | `configs/providers/*.yaml` | Provider-wide tightening/loosening |
| Entity | `configs/entities/.../*.yaml` | Entity-specific rules |
| Contracts | `configs/quality/`, domain contracts | Contract registry / DSL (ADR-045) |

**Do not** hardcode business DQ rules in transformers when they belong in YAML hierarchy.

## Thresholds

From `configs/base/quality.yaml` (verify live file if defaults change):

| Key | Default (base) | Meaning |
| --- | ---: | --- |
| `thresholds.soft_fail` | `0.05` | Soft breach → warn / report path |
| `thresholds.hard_fail` | `0.50` | Hard breach → fail batch / stop path |
| `strict_validation` | `false` | When true, stricter fail-closed behavior |
| `invalid_record_policy` | `quarantine` | Preferred disposition for invalid records |

Provider/entity YAML may override thresholds; document why in PR when raising fail budgets.

## Rule categories

| Category | Examples | Typical config |
| --- | --- | --- |
| Completeness | required fields, non-null PK | `type: required`, `nullable: false` |
| Validity | regex, numeric ranges, ISO timestamps | `type: pattern`, range rules |
| Uniqueness | business PK / content_hash | schema + merge contracts |
| Consistency | cross-field rules | `common_cross_field_validations` |
| Enum / ontology | controlled vocab | ADR-038 YAML enums |
| Timeliness | date windows / freshness | entity-specific rules |

Base example (`content_hash`, `_ingestion_ts`) lives in `configs/base/quality.yaml`.

## Invalid-row disposition

Normative (RULES §2.1 / rules-summary):

1. Exact **final** DataFrame is validated after last transform and **immediately before write**.
2. Any post-validation transform requires **re-validation**.
3. Invalid Silver rows **MUST NOT** be silently dropped: stop write **or** route to `common.quarantine`.
4. Gold validation is **strict / fail-closed**.

See: [quarantine runbook](../../05-operations/runbooks/quarantine-management.md), [pipeline-failure-dq](../../05-operations/runbooks/pipeline-failure-dq.md).

## Common patterns

### Required field

```yaml
- field: activity_id
  type: required
  nullable: false
  error_message: "activity_id is required"
```

### Pattern (ISO timestamp)

```yaml
- field: _ingestion_ts
  type: pattern
  pattern: '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
  nullable: false
```

### CLI inspection

```bash
bioetl dq validate --entity chembl.activity
bioetl dq validate --entity chembl.activity --show-rules
bioetl dq validate --entity chembl.activity --strict
```

## Investigation procedures

1. **Locate failure**
   - Pipeline logs: `dq_`, Pandera `SchemaError`, exit code DQ threshold (see CLI cheatsheet exit codes).
   - `bioetl diagnostics --pipeline <name> --quarantine`
2. **Identify failing records**
   - Report samples when `report.include_sample_failures: true` (base quality).
   - Quarantine table `common.quarantine` + [quarantine CLI](cli-commands.md).
3. **Classify**
   - Source drift vs config bug vs threshold too tight vs legit bad data.
4. **Remediate**
   - Fix source/transform; **or** add justified rule/threshold change in YAML hierarchy; **or** quarantine + replay.
5. **Never** “skip invalid rows” without quarantine or fail path.

Detailed framework: [dq-framework.md](../dq-framework.md), [dq-configuration.md](../dq-configuration.md).

## See also

- [Pipeline Config Cheatsheet](pipeline-config.md)
- [Troubleshooting common errors](../../05-operations/troubleshooting/common-errors.md)
- [ADR-027](../../02-architecture/decisions/ADR-027-dq-rules-externalization.md) · [ADR-045](../../02-architecture/decisions/ADR-045-dq-contract-system.md)
