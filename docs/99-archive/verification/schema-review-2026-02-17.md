# Schema Coverage Review

> **Status:** Historical verification artifact (non-normative).
> Use this report as dated evidence only; current policy source of truth is `docs/00-project/RULES.md` and active ADRs.

*Generated: 2026-02-17 | Sync workflow Prompt 4 (schema-review)*

---

## Summary

| Provider/Entity | Transformer→Silver | Transformer→Entity | Silver→Gold | Issues |
|-----------------|-------------------|--------------------|----|--------|
| pubchem/compound | 38/38 (100%) | 38/38 (100%) | 12/38 (32%) | 1 dead DTO field; Gold is curated subset |
| uniprot/protein | 54/56 (96%) | 56/56 (100%) | 26/56 (46%) | 2 dead fields; 1 missing Silver field |
| uniprot/idmapping | 15/15 (100%) | 13/13 (100%) | 15/15 (100%) | Fully aligned |
| crossref/publication | 30/30 (100%) | 30/30 (100%) | 30/30 (100%) | Full passthrough |
| openalex/publication | 35/35 (100%) | 35/35 (100%) | 35/35 (100%) | Minor type mismatches |
| pubmed/publication | 42/42 (100%) | 42/42 (100%) | 42/42 (100%) | Triple publication-type pattern |
| semanticscholar/publication | 30/30 (100%) | 30/30 (100%) | 30/30 (100%) | `issue` missing from Silver schema |

---

## pubchem/compound

### Coverage: Silver 38 fields | Gold 12 fields (32% — by design)

**Silver Schema:** `PubchemMoleculeSchema` (`domain/schemas/pubchem/compound.py`)
**Gold Schema:** `PubChemCompoundGoldSchema` (`domain/contracts/gold/pubchem.py`)

**Gold fields:** `entity-id`, `molecule-id`, `molecular-formula`, `molecular-weight`, `canonical-smiles`, `isomeric-smiles`, `inchi`, `inchi-key`, `logp` (alias: `xlogp`), `polar-surface-area` (alias: `tpsa`), `iupac-name`, `content-hash`

**Issues:**
- `fingerprint` — dead field in `PubchemMoleculeRecord` DTO only, not in schema/entity/transformer. **LOW**
- Gold alias renames: `xlogp` → `logp`, `tpsa` → `polar-surface-area` — intentional Gold semantic renames
- 26 Silver-only fields (3D properties, stereo counts, etc.) — **by design**: Gold is curated subset

---

## uniprot/protein

### Coverage: Silver 56 fields | Gold 26 fields (46% — by design)

**Silver Schema:** Split across `-core.py`, `-annotations.py`, `-features.py`, `-xrefs.py`
**Gold Schema:** `UniProtProteinGoldSchema` (`domain/contracts/gold/uniprot.py`)

**Critical Issues:**
| # | Field | Issue | Severity |
|---|-------|-------|----------|
| 1 | `pharmaceutical-use` | DEAD FIELD — in entity + Silver schema but NEVER set by transformer | **HIGH** |
| 2 | `publication-count` | DEAD FIELD — in entity + Silver schema but NEVER set by transformer | **HIGH** |
| 3 | `gene-names` | Missing from all Silver sub-schemas; passes through unvalidated | **MEDIUM** |
| 4 | `entry-name` | Nullable mismatch: Silver=non-null, Gold=nullable | LOW |
| 5 | `reviewed` | Nullable mismatch: Silver=non-null, Gold=nullable | LOW |
| 6 | `organism-id` | In Gold but not in Silver (legacy alias from `taxonomy-id`) | LOW |

**~30 Silver-only fields** (taxonomy lineage, sequence data, modifications, cross-references) — **by design**

---

## uniprot/idmapping

### Coverage: Silver 15 fields | Gold 15 fields (100%)

Fully aligned. All fields pass through from Silver to Gold.

**Note:** `-dq-warn` field is unique to IDMapping Gold — explicitly non-nullable boolean for flagging `not-found` mappings. Intentional design.

---

## crossref/publication

### Coverage: Silver 30 | Gold 30 (100%)

Full passthrough. All transformer fields reach Gold.

**Minor:**
- `issn-list` derived during Silver record conversion (not in entity)
- `publisher` set implicitly via `**journal-info` spread — verify extractor includes it

---

## openalex/publication

### Coverage: Silver 35 | Gold 35 (100%)

Full passthrough.

**Minor type mismatches:**
- `institution-ids`, `institution-country-codes`: Silver=`Series[str]`, Gold=`Series[object]`
- `subject-mesh`, `subject-keywords`: Silver=`Series[str]`, Gold=`Series[object]`
- Entity uses `list[str]`, Silver expects JSON string, Gold allows list passthrough

---

## pubmed/publication

### Coverage: Silver 42 | Gold 42 (100%)

Full passthrough.

**Design notes:**
- Triple `publication-type` representation: singular (pipe-delimited), `publication-types` (list), `publication-type-list` (JSON string) — intentional forensic retention
- `citations-received` popped from Silver record (PubMed doesn't provide citation counts)
- `subject-mesh`, `chemicals`, etc.: Silver=`Series[str]` (JSON), Gold=`Series[object]` (list)

---

## semanticscholar/publication

### Coverage: Silver 30 | Gold 30 (100%)

Full passthrough.

**Issues:**
| # | Field | Issue | Severity |
|---|-------|-------|----------|
| 1 | `issue` | Missing from Silver schema; present in entity, transformer, and Gold | **MEDIUM** |
| 2 | `arxiv-id` | Explicitly popped from Silver record — by design | INFO |

---

## Cross-Provider Action Items

### Critical (HIGH)

1. **Remove or populate dead fields in uniprot/protein:**
   - `pharmaceutical-use` — either add extraction logic to transformer or remove from entity+schema
   - `publication-count` — either add count computation to `-add-counts()` or remove from entity+schema

### Medium

2. **Add `gene-names` to uniprot/protein Silver schema** — field exists in entity, transformer, and Gold but bypasses Silver validation
3. **Add `issue` to semanticscholar Silver schema** — field passes through unvalidated

### Low / Info

4. Nullable mismatches in uniprot/protein (entry-name, reviewed) — Gold is more permissive than Silver
5. Type mismatches (str vs object) across publication providers — functionally correct but semantically inconsistent
6. Dead `fingerprint` field in PubChem DTO — cleanup candidate

### By-Design Reductions (No Action)

| Provider | Silver→Gold Reduction | Reason |
|----------|----------------------|--------|
| pubchem/compound | 68% | Gold = curated chemical descriptors |
| uniprot/protein | 54% | Gold = drug-discovery focused fields |
| uniprot/idmapping | 0% | Full passthrough + `-dq-warn` |
| publication providers | 0% | Full passthrough (all 4 providers) |
