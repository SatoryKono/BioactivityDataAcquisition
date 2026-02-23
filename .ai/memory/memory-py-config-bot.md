# Memory: py-config-bot

*Version: 1.0.0 | Date: 2026-02-23 | Parent: agent-memory.md*

> **Focus**: YAML config creation/update, DQ rules, filter rules, composite pipelines, ADR compliance.

---

## 1. Identity & Scope

- **Role**: Sole owner of `configs/` directory
- **Write zone**: `configs/`
- **Output artifacts**: `04a-config-log.md`
- **ID system**: `CFG-001`, `CFG-002`, ...
- **Model**: sonnet

---

## 2. Config Hierarchy

```
configs/
├── pipelines/
│   ├── _defaults.yaml              # Global defaults
│   ├── {provider}/
│   │   └── {entity}.yaml           # Pipeline config
│   └── composite/
│       └── {name}.yaml             # Composite pipeline config
├── dq/  (or quality/)
│   ├── _defaults.yaml              # DQ global defaults
│   ├── providers/
│   │   └── {provider}.yaml         # DQ provider defaults
│   └── entities/
│       └── {provider}/
│           └── {entity}.yaml       # DQ rules per entity
├── filter/  (or filters/)
│   ├── _defaults.yaml              # Filter global defaults
│   └── entities/
│       └── {provider}/
│           └── {entity}.yaml       # Filter rules per entity
└── sources/
    └── {provider}.yaml             # API source config
```

**Merge order**: `_defaults.yaml -> providers/{provider}.yaml -> entities/{provider}/{entity}.yaml -> inline (deprecated)`

---

## 3. ADR Compliance Rules

| ADR | Rule | Verification |
|-----|------|-------------|
| ADR-014 | `sort_by` MUST be present in Silver sink | `grep -A3 "sort_by" configs/pipelines/{p}/{e}.yaml` |
| ADR-025 | Pipeline Config Unification (required fields) | `python scripts/config_gap_analysis.py -v` |
| ADR-026 | Composite: `seed`, `enrichers`, `merge` sections | Review structure |
| ADR-027 | DQ Rules Externalization: NO inline thresholds | `grep "soft_fail_threshold" configs/pipelines/` |
| ADR-028 | Filter Rules Externalization | External filter configs |
| ADR-029 | Convention-based Config (auto-computed paths) | Don't set `dq_config_file` / `filter_config_file` explicitly |

---

## 4. Config Templates

### A. Pipeline Config (Standard)

```yaml
# configs/pipelines/{provider}/{entity}.yaml
pipeline_name: {provider}_{entity}
provider: {provider}
entity_type: {entity}
version: "1.0.0"

primary_keys: [{entity}_id]
silver_table: {provider}_{entity}
gold_table: {provider}_{entity}

sink:
  bronze:
    path: data/output/bronze/{provider}/{entity}
  silver:
    path: data/output/silver/{provider}/{entity}
    primary_key: [{entity}_id]
    sort_by:                    # MUST (ADR-014)
      columns: [{entity}_id]
      ascending: true
  gold:
    path: data/output/gold/{provider}/{entity}
    sort_by:                    # MUST (ADR-014)
      columns: [{entity}_id]
      ascending: true
```

### B. DQ Rules (Externalized)

```yaml
# configs/quality/entities/{provider}/{entity}.yaml
entity: {entity}
provider: {provider}
version: "1.0.0"

thresholds:
  soft_fail: 0.05
  hard_fail: 0.20

rules:
  - name: "{entity}_id_not_null"
    field: "{entity}_id"
    check: "not_null"
    severity: critical
  - name: "content_hash_not_null"
    field: "content_hash"
    check: "not_null"
    severity: critical
```

### C. Filter Rules (Externalized)

```yaml
# configs/filters/entities/{provider}/{entity}.yaml
entity: {entity}
provider: {provider}
version: "1.0.0"

gold_filters:
  required_fields:
    - {entity}_id
    - content_hash
```

### D. Composite Pipeline Config

```yaml
# configs/pipelines/composite/{name}.yaml
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

---

## 5. Composite Pipeline Rules

### Join Keys
- Stable identifiers: `doi`, `pmid`, `pmc_id`, `uniprot_accession`
- DO NOT use `title` as join key (only fallback)

### Column Naming (ADR-026 v2)
- Format: `{provider}.{entity}.{field}`
- Exceptions: join keys, system columns

### Column Ordering (Semantic Groups)
1. System (`entity_id`, `content_hash`, `_run_id`, ...)
2. Identifiers (`doi`, `pmid`, ...)
3. Title -> Abstract -> Authors -> Journal -> Dates -> Metrics -> Classification -> URLs -> Other

---

## 6. Validation Checklists

### Before Creating/Updating

```bash
python scripts/config_gap_analysis.py -v
find configs/ -path "*/{provider}/*" -name "*.yaml" | sort
cat configs/pipelines/_defaults.yaml 2>/dev/null
cat configs/sources/{provider}.yaml 2>/dev/null
```

### After Creating/Updating

```bash
# YAML syntax
python -c "import yaml; yaml.safe_load(open('configs/pipelines/{provider}/{entity}.yaml'))"

# Gap analysis (0 critical)
python scripts/config_gap_analysis.py -v

# sort_by present (ADR-014)
grep -A3 "sort_by" configs/pipelines/{provider}/{entity}.yaml

# No inline DQ thresholds (ADR-027)
grep -n "soft_fail_threshold\|hard_fail_threshold" configs/pipelines/{provider}/{entity}.yaml

# DQ externalized config exists
test -f configs/quality/entities/{provider}/{entity}.yaml && echo "OK" || echo "MISSING"
```

---

## 7. New Entity Scaffolding (Config Part)

When creating a new entity, generate 3 configs:

1. `configs/pipelines/{provider}/{entity}.yaml` — pipeline config
2. `configs/dq/entities/{provider}/{entity}.yaml` (or `quality/`) — DQ rules
3. `configs/filter/entities/{provider}/{entity}.yaml` (or `filters/`) — filter rules

---

## 8. Integration with Other Agents

| Event | Action |
|-------|--------|
| py-code-bot: new entity scaffolding | -> config-bot creates pipeline + DQ + filter |
| py-code-bot: RF-* with config changes | -> config-bot updates affected configs |
| py-audit-bot: config gap findings | -> config-bot remediates gaps |
| py-plan-bot: composite pipeline task | -> config-bot creates composite config |
| Config created/updated | -> py-test-bot (config tests) |
| Config validated | -> py-audit-bot (final, type=config) |

---

## 9. Key Files for Config

| What | Path |
|------|------|
| Pipeline defaults | `configs/pipelines/_defaults.yaml` |
| Source configs | `configs/sources/{provider}.yaml` |
| DQ defaults | `configs/dq/_defaults.yaml` or `configs/quality/_defaults.yaml` |
| Gap analysis script | `scripts/config_gap_analysis.py` |
| Config loader code | `src/bioetl/application/` or `src/bioetl/composition/` |

---

## 10. Providers Reference

ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, SemanticScholar, IUPHAR, Open Targets

Common entity types per provider:
- ChEMBL: activity, molecule, target, mechanism, assay
- PubChem: compound, bioassay
- UniProt: protein
- PubMed: publication
- CrossRef: publication (enricher)
- OpenAlex: work (enricher)

---

*This memory file is specific to py-config-bot. For general project context see `agent-memory.md`.*
