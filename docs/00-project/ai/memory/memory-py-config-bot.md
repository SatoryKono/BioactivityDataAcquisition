# Memory: py-config-bot

*Статус: internal-only (agent memory)*

*Version: 1.0.1 | Date: 2026-04-06 | Parent: agent-memory.md*

> **Focus**: YAML config creation/update, DQ rules, filter rules, composite pipelines, ADR compliance.

______________________________________________________________________

## 1. Identity & Scope

- **Role**: Sole owner of `configs/` directory
- **Write zone**: `configs/`
- **Output artifacts**: `04a-config-log.md`
- **ID system**: `CFG-001`, `CFG-002`, ...
- **Model**: sonnet

## Evidence Anchors

For claims about config-tree layout or repo organization, consult:

- `docs/reports/evidence/project-file-structure/SUMMARY.md`
- `docs/reports/evidence/project-file-structure/04-decisions/SUMMARY.md`
- `docs/reports/evidence/project-package-topology/SUMMARY.md`

Do not propose repo/package restructuring from config sprawl alone without evidence beyond file count or directory breadth.

## Debt Tracking During Config Edits

When config changes affect governance or tracked code areas:

- distinguish `exemption debt` from `hotspot inventory`;
- verify whether the change impacts `configs/quality/debt_scorecard.yaml` or
  `configs/quality/architecture_metric_exemptions.yaml`;
- never add a new exemption without required metadata;
- mention debt outcome for touched files or config surfaces:
  `improved`, `unchanged`, or `worsened`.

______________________________________________________________________

## 2. Config Hierarchy

```
configs/
├── base/
│   ├── pipeline.yaml               # Global pipeline defaults
│   └── quality.yaml                # Global quality defaults
├── entities/
│   └── {provider}/
│       └── {entity}.yaml           # Pipeline config
├── composites/
│   └── {entity}.yaml               # Composite pipeline config
└── providers/
    └── {provider}.yaml             # API source + provider quality/filters
```

**Merge order**: `base/*.yaml -> providers/{provider}.yaml -> entities/{provider}/{entity}.yaml -> inline (deprecated)`

______________________________________________________________________

## 3. ADR Compliance Rules

| ADR     | Rule                                                    | Verification                                                                                             |
| ------- | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| ADR-014 | `sort_by` MUST be present in Silver sink                | `grep -A3 "sort_by" configs/entities/{p}/{e}.yaml`                                                       |
| ADR-025 | Pipeline Config Unification (required fields)           | `python scripts/schema/config_gap_analysis.py -v`                                                        |
| ADR-026 | Composite: `seed`, `enrichers`, `merge` sections        | Review structure                                                                                         |
| ADR-027 | DQ hierarchy: base/provider/entity unified sections     | `grep -rn "^quality:" configs/providers configs/entities --include="*.yaml"`                             |
| ADR-028 | Filter hierarchy: base/provider/entity unified sections | `grep -rn "^filters:" configs/providers configs/entities --include="*.yaml"`                             |
| ADR-029 | Convention-based Config (auto-computed paths)           | Don't set legacy `dq_config_file` / `filter_config_file` path overrides unless compatibility requires it |

______________________________________________________________________

## 4. Config Templates

### A. Pipeline Config (Standard)

```yaml
# configs/entities/{provider}/{entity}.yaml
version: "1.0.0"
provider: {provider}
entity: {entity}

pipeline:
  pipeline_name: {provider}_{entity}
  provider: {provider}
  entity_type: {entity}
  business_primary_keys: [{entity}_id]
  sink:
    silver:
      sort_by: [entity_id, {entity}_id]
    gold:
      enabled: true

schema:
  column_groups:
    - name: system
      fields: [entity_id, content_hash]
    - name: business
      fields: [{entity}_id]

quality:
  version: "1.0.0"
  provider: {provider}
  entity: {entity}

filters:
  version: "1.0.0"
  provider: {provider}
  entity: {entity}

contracts:
  primary_key:
    business: [{entity}_id]
```

### B. Provider-Level Quality Defaults

```yaml
# configs/providers/{provider}.yaml
version: "1.0.0"
provider: {provider}

source:
  rate_limit:
    requests_per_second: 5
    burst: 10

quality:
  version: "1.0.0"
  provider: {provider}
  thresholds:
    soft_fail: 0.05
    hard_fail: 0.20
```

### C. Filter Hierarchy

```yaml
# Filter defaults live in:
# - configs/base/pipeline.yaml#filter_defaults
# - configs/providers/{provider}.yaml#filters
# - configs/entities/{provider}/{entity}.yaml#filters
```

### D. Composite Pipeline Config

```yaml
# configs/composites/{name}.yaml
composite:
  name: composite_{entity}
  version: "1.0.0"
  seed:
    pipeline: {provider}_{entity}
    output_keys: [{entity}_id, doi]
    silver_table: silver/{provider}/{entity}
  enrichers:
    - pipeline: {enricher_provider}_{entity}
      join_keys: [doi]
      optional: false
      timeout_seconds: 300
  merge:
    strategy: left_outer
    conflict_resolution: explicit_rules
    field_priorities:
      title: [seed, {enricher_provider}]
      abstract: [{enricher_provider}, seed]
```

______________________________________________________________________

## 5. Composite Pipeline Rules

### Join Keys

- Stable identifiers: `doi`, `pmid`, `pmc_id`, `uniprot_accession`
- DO NOT use `title` as join key (only fallback)

### Column Naming (ADR-026 v2)

- Format: `{provider}.{entity}.{field}`
- Exceptions: join keys, system columns

### Column Ordering (Semantic Groups)

1. System (`entity_id`, `content_hash`, `_run_id`, ...)
1. Identifiers (`doi`, `pmid`, ...)
1. Title -> Abstract -> Authors -> Journal -> Dates -> Metrics -> Classification -> URLs -> Other

______________________________________________________________________

## 6. Validation Checklists

### Before Creating/Updating

```bash
uv run python docs/00-project/ai/agents/scripts/py-config-bot-1.py -v
find configs/ -path "*/{provider}/*" -name "*.yaml" | sort
cat configs/base/pipeline.yaml 2>/dev/null
cat configs/providers/{provider}.yaml 2>/dev/null
```

### After Creating/Updating

```bash
# YAML syntax
uv run python -c "import yaml; yaml.safe_load(open('configs/entities/{provider}/{entity}.yaml', encoding='utf-8'))"

# Gap analysis (0 critical)
uv run python docs/00-project/ai/agents/scripts/py-config-bot-1.py -v

# sort_by present (ADR-014)
grep -A3 "sort_by" configs/entities/{provider}/{entity}.yaml

# No legacy explicit path overrides (ADR-029)
grep -n "dq_config_file\|filter_config_file" configs/entities/{provider}/{entity}.yaml

# Unified entity config contains quality/filters sections
grep -n "^quality:\|^filters:" configs/entities/{provider}/{entity}.yaml
```

### Unified Script Commands (schema/config validation)

```bash
# Schema invariants — обязательно после изменения configs
python -m scripts.schema check-invariants --verbose
python -m scripts.schema check-config-paths

# Config validation (all pipeline configs)
python -m scripts.schema validate-configs

# Gap analysis (unified)
python -m scripts.schema analyze-gaps

# Pipeline schema generation (check mode)
python -m scripts.schema generate-pipeline --check
python -m scripts.schema generate-artifacts --check
python -m scripts.schema generate-pubtype --check
```

______________________________________________________________________

## 7. New Entity Scaffolding (Config Part)

When creating a new entity, generate:

1. `configs/entities/{provider}/{entity}.yaml` — unified entity config
1. Update `configs/providers/{provider}.yaml` only if provider-level source/quality/filter defaults are needed
1. Composite config only if the entity participates in multi-provider merge flows

______________________________________________________________________

## 8. Integration with Other Agents

| Event                                   | Action                                                                              |
| --------------------------------------- | ----------------------------------------------------------------------------------- |
| orchestrator: new entity scaffolding    | -> config-bot creates unified entity config and provider overrides only when needed |
| orchestrator: RF-\* with config changes | -> config-bot updates affected configs                                              |
| py-audit-bot: config gap findings       | -> config-bot remediates gaps                                                       |
| py-plan-bot: composite pipeline task    | -> config-bot creates composite config                                              |
| Config created/updated                  | -> py-test-bot (config tests)                                                       |
| Config validated                        | -> py-audit-bot (final, type=config)                                                |

______________________________________________________________________

## 9. Key Files for Config

| What                     | Path                                                                                             |
| ------------------------ | ------------------------------------------------------------------------------------------------ |
| Pipeline/filter defaults | `configs/base/pipeline.yaml`                                                                     |
| DQ defaults              | `configs/base/quality.yaml`                                                                      |
| Provider configs         | `configs/providers/{provider}.yaml`                                                              |
| Unified entity configs   | `configs/entities/{provider}/{entity}.yaml`                                                      |
| Composite configs        | `configs/composites/{entity}.yaml`                                                               |
| Gap analysis script      | `docs/00-project/ai/agents/scripts/py-config-bot-1.py`                                           |
| Config loader code       | `src/bioetl/composition/bootstrap/runtime/config_loader.py`, `src/bioetl/infrastructure/config/` |

______________________________________________________________________

## 10. Providers Reference

ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, SemanticScholar

Common entity types per provider:

- ChEMBL: activity, molecule, target, mechanism, assay
- PubChem: compound, bioassay
- UniProt: protein
- PubMed: publication
- CrossRef: publication (enricher)
- OpenAlex: work (enricher)

______________________________________________________________________

*This memory file is specific to py-config-bot. For general project context see `agent-memory.md`.*
