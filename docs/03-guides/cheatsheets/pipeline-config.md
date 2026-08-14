______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Pipeline Configuration Cheatsheet

Quick reference for creating and reviewing BioETL pipeline YAML configs.

**Issue:** #6536 · **Date:** 2026-07-28

## Table of contents

- [Config hierarchy](#config-hierarchy)
- [Required fields (ADR-025 / ADR-039)](#required-fields-adr-025-adr-039)
- [ADR compliance checklist](#adr-compliance-checklist)
- [Common patterns](#common-patterns)
- [Validation commands](#validation-commands)

## Config hierarchy

```text
configs/base/
  pipeline.yaml      # global pipeline defaults (when present)
  quality.yaml       # global DQ defaults (ADR-027)
  ...
configs/providers/{provider}.yaml     # provider-level settings + optional quality/filters
configs/entities/{provider}/{entity}.yaml   # entity pipeline (canonical runtime binding)
configs/composites/{entity}.yaml      # composite DAG (ADR-026)
configs/quality/     # governance / contracts / thresholds (not entity runtime YAML)
```

**Resolution order (conceptually):** base defaults → provider → entity (entity wins on conflict).
**Convention-based layout** (ADR-039 entity format + entity path conventions): no legacy path overrides for new pipelines.

| Layer | Path | Role |
| --- | --- | --- |
| Base | `configs/base/*` | Shared defaults (DQ, pipeline globals) |
| Provider | `configs/providers/{provider}.yaml` | Provider auth/HTTP/quality defaults |
| Entity | `configs/entities/{provider}/{entity}.yaml` | Runnable pipeline identity + sink/schema |
| Composite | `configs/composites/{entity}.yaml` | seed / enrichers / merge policy |

## Required fields (ADR-025 / ADR-039)

Minimal entity surface (see live examples under `configs/entities/chembl/`):

| Field | Purpose | ADR |
| --- | --- | --- |
| `pipeline.pipeline_name` | Stable pipeline id (`provider_entity`) | ADR-025 |
| `pipeline.provider` | Provider key | ADR-025 |
| `pipeline.entity_type` / top-level `entity` | Entity key | ADR-025 / ADR-039 |
| `pipeline.business_primary_keys` | Business PK columns | ADR-025 |
| `pipeline.sink.silver` | Silver write mode / idempotency | ADR-014, ADR-031 |
| `pipeline.sink.gold` | Gold enablement / mode | ADR-018 |
| `schema.column_groups` | Column ownership groups | ADR-037 family |
| `quality` (section or inherited) | version, thresholds, rules | ADR-027, ADR-045 |
| `filters` (section or inherited) | versioned filter hierarchy | ADR-028, ADR-050 |
| Contracts / primary key | Pandera/contract binding | ADR-045 |

**Silver determinism (ADR-014):** any Silver sink must define a stable ordering contract (`sort_by` or equivalent deterministic merge keys as required by current schema). If the schema omits `sort_by`, document the deterministic key set used by merge/upsert.

## ADR compliance checklist

Use when reviewing a PR that touches pipeline YAML:

- [ ] **ADR-014** Deterministic writes — Silver path has stable order/keys; no non-deterministic sort
- [ ] **ADR-025** Pipeline config unification — identity fields present; no ad-hoc alternate config trees
- [ ] **ADR-026** Composite — composites declare seed, enrichers, merge policy under `configs/composites/`
- [ ] **ADR-027** DQ externalization — quality rules in YAML hierarchy, not hardcoded in transformers
- [ ] **ADR-028** Filter externalization — filters in hierarchy; silver structural vs gold semantic boundary (ADR-050)
- [ ] **ADR-018** Gold strict validation — gold enabled paths use strict/fail-closed validation
- [ ] **ADR-039** Unified entity config format — entity YAML under `configs/entities/{provider}/`
- [ ] **ADR-029** Output metadata unification — metadata fields follow unified sidecar contract (not path overrides)

## Common patterns

### Standard entity skeleton

```yaml
version: 1.0.0
provider: chembl
entity: activity
pipeline:
  pipeline_name: chembl_activity
  provider: chembl
  entity_type: activity
  description: "..."
  business_primary_keys:
    - activity_id
  batch_size: 1000
  sink:
    silver:
      mode: merge
      idempotency_contract: merge_upsert
    gold:
      enabled: true
schema:
  column_groups:
    - name: system
      fields: [entity_id, content_hash, _run_id, ...]
    - name: business
      fields: [activity_id, ...]
```

### Composite (ADR-026)

```yaml
# configs/composites/publication.yaml (shape illustrative)
seed: chembl_publication
enrichers:
  - crossref_publication
  - openalex_publication
merge:
  policy: coalesce  # see domain composite policy
```

Join keys and qualified column naming follow ADR-026 composite conventions (`provider.entity.field` style where configured).

### Provider quality defaults

Prefer `configs/base/quality.yaml` + provider YAML `#quality` overrides rather than duplicating full rule sets per entity.

## Validation commands

```bash
# List registered pipelines
bioetl config list-pipelines

# Show resolved config
bioetl config show chembl_activity
bioetl config show chembl_activity --format json

# Validate entity config
bioetl config validate chembl_activity

# DQ rules for entity
bioetl dq validate --entity chembl.activity --show-rules
```

Detailed guide: [pipeline-configuration.md](../pipeline-configuration.md).

## See also

- [Data Quality Rules Cheatsheet](data-quality-rules.md)
- [ADR Decision Matrix](adr-matrix.md)
- [CLI Commands](cli-commands.md)
- ADRs: [ADR-025](../../02-architecture/decisions/ADR-025-pipeline-config-unification.md), [ADR-026](../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md), [ADR-027](../../02-architecture/decisions/ADR-027-dq-rules-externalization.md), [ADR-028](../../02-architecture/decisions/ADR-028-filter-rules-externalization.md), [ADR-014](../../02-architecture/decisions/ADR-014-deterministic-writes.md)
