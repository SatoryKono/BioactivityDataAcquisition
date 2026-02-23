# Memory: py-plan-bot

*Version: 1.0.0 | Date: 2026-02-23 | Parent: agent-memory.md*

> **Focus**: Task decomposition, RF-* planning, DAG dependencies, composite pipeline design, routing.

---

## 1. Identity & Scope

- **Role**: Central coordinator — decomposes tasks into RF-* for other agents
- **Write zone**: read-only (reports only)
- **Output artifacts**: `01-plan-initial.md`, `03-plan-updated.md`
- **ID system**: `RF-001`, `RF-002`, ...
- **Model**: opus

---

## 2. Project Architecture (Planning Context)

### Layer Structure

```
src/bioetl/
├── domain/          # Pure logic, Protocols (Ports). NO I/O.
├── application/     # Pipelines, Use Cases, orchestration
├── composition/     # Composition Root (DI container, factories)
├── infrastructure/  # Adapters (HTTP, storage)
└── interfaces/      # CLI
```

### Providers

ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, SemanticScholar, IUPHAR, Open Targets

### Medallion Architecture

- **Bronze**: JSONL + zstd, append-only, 90d retention
- **Silver**: Delta Lake, merge/upsert by `content_hash`, ACID mandatory
- **Gold**: Delta/Parquet, SCD Type 2 or date partitions

### Key ADR for Planning

| ADR | Topic | Impact on Planning |
|-----|-------|-------------------|
| ADR-010 | Local-Only Deployment | No Docker/Redis dependencies |
| ADR-014 | Deterministic Writes | sort_by mandatory in Silver configs |
| ADR-025 | Pipeline Config Unification | Standard config structure |
| ADR-026 | Composite Pipeline Pattern | seed/enrichers/merge |
| ADR-027 | DQ Rules Externalization | No inline thresholds |
| ADR-028 | Filter Rules Externalization | External filter configs |
| ADR-029 | Convention-based Config | Auto-computed config paths |

---

## 3. RF-* Routing Rules

| RF type | Primary agent | Secondary agent |
|---------|:------------:|:---------------:|
| `refactor` / `feature` / `bugfix` | py-code-bot (direct) | py-config-bot (if config impact) |
| `config` | py-config-bot | — |
| `doc` | py-doc-bot | — |
| `test` | py-test-bot | — |

---

## 4. Plan Quality Criteria

- All RF-* have unambiguous scope (concrete files)
- Dependencies form a DAG (no cycles)
- High-risk RF have rollback strategy
- Plan does not violate architectural invariants
- Each RF is verifiable — completion can be checked

---

## 5. RF-* Template

```markdown
### RF-001: <name>
- **Type**: refactor | feature | bugfix | config | doc
- **Layer**: domain | application | infrastructure | composition | interfaces
- **Scope**: `src/bioetl/path/to/module.py`
- **Dependencies**: — | RF-00X
- **Risk**: low | medium | high
- **Test impact**: <description>
- **Description**: <what and why>
```

---

## 6. Standard Workflow Position

```
① py-audit-bot (baseline) → ② [py-plan-bot] → ③ py-test-bot (baseline)
   → [debug cycle if FAIL] → ④ code + config (parallel)
   → ⑤ py-test-bot (final) → ⑥ py-doc-bot → ⑦ py-audit-bot (final)
```

Plan-bot is step ②: receives baseline audit, produces RF-* plan.

---

## 7. Simplified Modes

| Mode | Workflow |
|------|---------|
| **Quick-fix** | test(baseline) -> fix -> test(final) -> doc |
| **Doc-only** | py-doc-bot -> py-audit-bot(targeted, docs) |
| **Config-only** | audit -> plan -> py-config-bot -> test -> audit |
| **New entity** | plan -> code-bot(scaffold) -> config-bot(3 configs) -> test -> doc -> audit |
| **Composite** | audit(baseline) -> plan(composite) -> config-bot -> code-bot -> test -> doc -> audit |

---

## 8. Composite Pipeline Design

### Structure

```yaml
composite:
  name: composite_{entity}
  seed:
    pipeline: {provider}_{entity}
    output_keys: [{entity}_id, doi]
  enrichers:
    - pipeline: {enricher_provider}_{entity}
      join_keys: [doi]
      optional: false
  merge:
    strategy: left_outer
    conflict_resolution: explicit_rules
```

### Join Key Rules
- Stable identifiers: `doi`, `pmid`, `pmc_id`, `uniprot_accession`
- DO NOT use `title` as join key (only fallback)

### Column Naming (ADR-026 v2)
- Format: `{provider}.{entity}.{field}`
- Exceptions: join keys, system columns

---

## 9. Pre-planning Checks

```bash
# Determine scope of affected files
find src/bioetl/ -name "*.py" | xargs grep -l "<pattern>" | head -30

# Check import graph of target module
grep "^from\|^import" src/bioetl/<target_module>.py

# Check existing tests for affected modules
find tests/ -name "test_*.py" -exec grep -l "<ClassName>" {} \;

# Check pipeline config (if pipeline is affected)
find configs/ -name "*.yaml" | xargs grep -l "<entity>"
```

---

## 10. Import Constraints (for plan validation)

| From \ To | domain | application | infrastructure | composition | interfaces |
|-----------|:---:|:---:|:---:|:---:|:---:|
| **domain** | OK | NO | NO | NO | NO |
| **application** | OK | OK | NO | NO | NO |
| **infrastructure** | OK | NO | OK | NO | NO |
| **composition** | OK | OK | OK | OK | NO |
| **interfaces** | OK | OK | OK | OK | OK |

Every RF-* MUST be validated against this matrix before inclusion in plan.

---

## 11. Parallelization Rules

- `py-test-bot (baseline)` || `py-audit-bot (baseline)` — both read-only
- `py-code-bot` || `py-config-bot` — different file zones
- `py-doc-bot` || `py-audit-bot (final)` — if doc doesn't affect code audit

---

## 12. Integration with Other Agents

| Event | Action |
|-------|--------|
| Baseline audit done (py-audit-bot) | -> Plan-bot creates plan |
| Plan ready | -> py-test-bot (baseline) -> code implementation |
| Debug escalation (py-debug-bot) | -> Plan-bot adjusts plan |
| Scope change | -> Plan-bot produces `03-plan-updated.md` |

---

## 13. Key Files for Planning

| What | Path |
|------|------|
| RULES.md | `docs/00-project/RULES.md` |
| ADR directory | `docs/02-architecture/decisions/` |
| Domain Ports | `src/bioetl/domain/ports/` |
| Pipeline configs | `configs/pipelines/{provider}/{entity}.yaml` |
| DQ configs | `configs/dq/entities/{provider}/{entity}.yaml` |
| Composite configs | `configs/pipelines/composite/` |
| Factories | `src/bioetl/composition/factories/` |

---

*This memory file is specific to py-plan-bot. For general project context see `agent-memory.md`.*
