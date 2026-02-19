# Audit: Composite Schemas — Field Groups, TRASH, Alias Chaos

**Date:** 2026-02-17
**Scope:** `configs/schemas/composite/**`
**Status:** WARN (score 6.8/10)

---

## Executive Summary

Audit of `configs/schemas/composite/` reveals **3 critical issues**, **5 high-severity issues**, and **8 medium-severity issues**. The primary problems are:

1. **Alias chaos** — legacy and canonical field names coexist as separate base-names in `field-groups/publication.yaml`, creating ghost columns after alias resolution
2. **TRASH group** contains fields that arguably belong elsewhere (language, license-url) while missing fields that should be trash
3. **Two parallel publication schemas** (`publication.yaml` column-groups vs `field-groups/publication.yaml`) with semantic drift between them

The `assay.yaml` and `molecule.yaml` composite schemas are clean and well-structured.

---

## 1. Files Audited

| File | Lines | Status |
|------|-------|--------|
| `configs/schemas/composite/assay.yaml` | 252 | PASS |
| `configs/schemas/composite/molecule.yaml` | 260 | PASS |
| `configs/schemas/composite/publication.yaml` | 355 | WARN |
| `configs/schemas/composite/field-groups/publication.yaml` | 572 | WARN |

Supporting files cross-referenced:
- `src/bioetl/domain/value-objects/publication-field-groups.py` (Python enum + mapping)
- `src/bioetl/domain/composite/field-groups.py` (FieldGroupRegistry)
- `src/bioetl/application/composite/merger.py` (MergeService consumption)
- All 5 provider schemas (`chembl/`, `crossref/`, `openalex/`, `pubmed/`, `semanticscholar/`)

---

## 2. Problematic Field Groups

### 2.1 TRASH Group — Audit

**Location:** `field-groups/publication.yaml` lines 535–572

Current TRASH fields:

| base-name | Provider(s) | Issue |
|-----------|-------------|-------|
| `content-domain-crossmark-restriction` | crossref | OK — CrossRef internal metadata |
| `content-domain-domains` | crossref | OK — CrossRef internal metadata |
| `content-hash` | all 5 | **PROBLEM** — system field, not business data; should be in `system` group |
| `language` | crossref, openalex, pubmed | **QUESTIONABLE** — has analytical value for multilingual corpora |
| `license-url` | crossref | **QUESTIONABLE** — relevant for OA/licensing analytics |
| `medline-pgn` | pubmed | OK — redundant with page-first/page-last |
| `src-id` | chembl | OK — ChEMBL-internal source identifier |

**Fields missing from TRASH that should be there:**

| base-name | Current Group | Issue |
|-----------|--------------|-------|
| `author-details` | Python: TRASH, YAML: **missing entirely** | 3-way inconsistency |
| `venue` | bibliography | SemanticScholar legacy field, superseded by `journal` |
| `journal-full-title` | bibliography | ChEMBL-only legacy, overlaps `journal` |
| `journal-title` | bibliography (YAML only) | PubMed-only legacy, overlaps `journal-name` |
| `journal-abbrev` | bibliography (YAML only) | PubMed-only legacy, overlaps `journal-name-short` |
| `issn-list` | bibliography | Redundant JSON blob, `issn`/`issn-print`/`issn-electronic` are canonical |
| `document-chembl-id` | id-and-status | Legacy alias for `publication-id`, should not coexist |
| `pub-date` | date-and-places | Legacy PubMed field, `publication-date` is canonical |

### 2.2 `id-and-status` Group — Overloaded

This group has become a catch-all (30+ fields in YAML). Fields that belong elsewhere:

| base-name | Should Be | Reason |
|-----------|-----------|--------|
| `fields-of-study` | terms-and-keywords-and-topics | Subject classification, not identifier |
| `is-oa` | open-access (new group) or bibliography | OA status flag |
| `oa-status` | open-access (new group) or bibliography | OA status detail |
| `open-access-url` | open-access (new group) or bibliography | OA access link |
| `publication-type` | publication-types | Type classification, not identifier |
| `publication-status` | date-and-places or bibliography | Workflow status, not identifier |

---

## 3. Alias Chaos — Duplicate base-names

### 3.1 Pre-alias / Post-alias Duplication

The `field-groups/publication.yaml` contains BOTH legacy and canonical names as separate `base-name` entries. After provider-level alias resolution (e.g., `doi → publication-doi`), the legacy columns no longer exist in the data, making these entries **ghost columns**.

| Legacy base-name | Canonical base-name | Providers with both | Risk |
|-----------------|---------------------|---------------------|------|
| `doi` | `publication-doi` | all 5 | **CRITICAL** — double-counting |
| `pmid` | `publication-pmid` | chembl, openalex, pubmed, s2 | **CRITICAL** — double-counting |
| `pmc-id` | `publication-pmc-id` | pubmed | HIGH — ghost column |
| `year` | `publication-year` | all 5 | **CRITICAL** — double-counting |
| `keywords` | `subject-keywords` | openalex, pubmed, s2 | HIGH — semantic overlap |
| `mesh-terms` | `subject-mesh` | openalex, pubmed | HIGH — semantic overlap |
| `topics` | `subject-topics` | openalex | MEDIUM — single provider |
| `pages` | `page-range` | crossref, pubmed, s2 | MEDIUM — both may exist |
| `journal-title` | `journal-name` | pubmed | MEDIUM — single provider |
| `mesh` | `subject-mesh` | openalex | MEDIUM — 3-way overlap |
| `type` | `publication-type` | crossref, openalex | HIGH — generic name |
| `pub-date` | `publication-date` | pubmed | MEDIUM — legacy |

### 3.2 Three-way Field Overlap Examples

**MeSH data:**
- `mesh` (openalex raw) → terms-and-keywords
- `mesh-terms` (openalex, pubmed) → terms-and-keywords
- `subject-mesh` (openalex, pubmed) → terms-and-keywords

All three track the same MeSH vocabulary data from the same providers.

**Journal naming:**
- `journal` — canonical (all providers)
- `journal-name` — pubmed, openalex, semanticscholar
- `journal-full-title` — chembl only
- `journal-title` — pubmed only
- `journal-name-short` — crossref, pubmed
- `journal-iso-abbrev` — pubmed
- `journal-abbrev` — pubmed

Seven base-names for journal nomenclature across 5 providers.

### 3.3 Python ↔ YAML Inconsistencies

| Field | Python (`FIELD-TO-GROUP-MAPPING`) | YAML (`field-groups/publication.yaml`) | YAML (`publication.yaml`) |
|-------|-----------------------------------|---------------------------------------|--------------------------|
| `author-details` | TRASH | **MISSING** | author-identifiers group |
| `publication-doi` | **MISSING** | id-and-status | identifiers-doi group |
| `publication-pmid` | **MISSING** | id-and-status | identifiers-pmid group |
| `publication-pmc-id` | **MISSING** | id-and-status | pmc-identifiers group |
| `journal-name` | **MISSING** | bibliography | journal group |
| `journal-title` | **MISSING** | bibliography | **MISSING** |
| `journal-abbrev` | **MISSING** | bibliography | **MISSING** |
| `mesh` | terms-and-keywords | terms-and-keywords | **MISSING** |
| `keywords` | **MISSING** | terms-and-keywords | **MISSING** |
| `topics` | **MISSING** | terms-and-keywords | **MISSING** |
| `type` | **MISSING** | publication-types | **MISSING** |
| `pages` | **MISSING** | bibliography | **MISSING** |
| `venue` | bibliography | bibliography | **MISSING** |
| `issn-list` | bibliography (YAML) | bibliography | **MISSING** |

---

## 4. Impact on Silver/Gold Layers

### 4.1 Silver Layer Impact

- **Storage waste**: Duplicate columns (`doi` + `publication-doi`) inflate parquet files
- **Schema confusion**: Consumers don't know which column to use
- **No data corruption**: Silver is append-only with all fields included
- **Risk**: LOW (Silver is forensic/debugging layer)

### 4.2 Gold Layer Impact

- **`include-in-gold: true` on `id-and-status`** propagates ALL misplaced fields to Gold
- `fields-of-study` appears in Gold as an "identifier" — misleading for analytics
- `publication-type` appears in Gold via `id-and-status` AND `publication-types` — potential duplication
- **`content-hash`** is marked TRASH, correctly excluded — but it's a system field, not business trash
- **`language`** excluded from Gold — may be wanted for multilingual analysis
- **`license-url`** excluded from Gold — may be wanted for OA analysis
- **Risk**: MEDIUM (Gold schema drift affects downstream analytics)

### 4.3 MergeService Behavior

From `application/composite/merger.py`:
```python
# Trash filtering happens AFTER merge, BEFORE Gold write
if self.-field-group-registry is not None:
    trash-cols = self.-field-group-registry.get-trash-columns(df.columns)
    df = df.drop(trash-cols)
```

System columns (`-*`) are **never** considered trash — `content-hash` (no underscore prefix) is correctly excluded. But the default-group=TRASH means **any unmapped field falls to trash and is silently dropped from Gold**.

---

## 5. Proposed Changes

### 5.1 Normalize Alias Pairs (CRITICAL — eliminate ghost columns)

Remove legacy `base-name` entries from `field-groups/publication.yaml`. Keep only canonical names.

```yaml
# REMOVE these base-names (ghost columns after alias resolution):
- doi          → keep only publication-doi
- pmid         → keep only publication-pmid  (add if missing)
- pmc-id       → keep only publication-pmc-id (add if missing)
- year         → keep only publication-year
- document-chembl-id → keep only publication-id
```

**Diff — `field-groups/publication.yaml`:**
```diff
  # Remove doi (lines 61-67)
-     - base-name: doi
-       columns:
-         - chembl.publication.doi
-         - crossref.publication.doi
-         - openalex.publication.doi
-         - pubmed.publication.doi
-         - semanticscholar.publication.doi

  # Remove document-chembl-id (lines 49-51)
-     - base-name: document-chembl-id
-       columns:
-         - chembl.publication.document-chembl-id

  # Remove year (lines 508-514)
-     - base-name: year
-       columns:
-         - chembl.publication.year
-         - crossref.publication.year
-         - openalex.publication.year
-         - pubmed.publication.year
-         - semanticscholar.publication.year

  # Add publication-year to date-and-places (currently missing)
+     - base-name: publication-year
+       columns:
+         - chembl.publication.publication-year
+         - crossref.publication.publication-year
+         - openalex.publication.publication-year
+         - pubmed.publication.publication-year
+         - semanticscholar.publication.publication-year
```

### 5.2 Consolidate MeSH/Keywords/Topics Triplicates (HIGH)

```diff
  # REMOVE mesh (openalex raw, superseded by subject-mesh):
-     - base-name: mesh
-       columns:
-         - openalex.publication.mesh

  # REMOVE mesh-terms (superseded by subject-mesh after alias resolution):
-     - base-name: mesh-terms
-       columns:
-         - openalex.publication.mesh-terms
-         - pubmed.publication.mesh-terms

  # KEEP subject-mesh as canonical

  # REMOVE keywords (superseded by subject-keywords after alias resolution):
-     - base-name: keywords
-       columns:
-         - openalex.publication.keywords
-         - pubmed.publication.keywords
-         - semanticscholar.publication.keywords

  # KEEP subject-keywords as canonical

  # REMOVE topics (superseded by subject-topics after alias resolution):
-     - base-name: topics
-       columns:
-         - openalex.publication.topics

  # KEEP subject-topics as canonical
```

### 5.3 Consolidate Journal Naming (HIGH)

```diff
  # KEEP: journal (canonical, all providers)
  # KEEP: journal-name (PubMed/OpenAlex/S2 display name)
  # KEEP: journal-name-short (CrossRef/PubMed abbreviation)
  # KEEP: journal-iso-abbrev (PubMed ISO)

  # MOVE to TRASH (redundant legacy):
-     - base-name: journal-full-title    # → journal covers this
-       columns:
-         - chembl.publication.journal-full-title

-     - base-name: journal-title         # → journal-name covers this
-       columns:
-         - pubmed.publication.journal-title

-     - base-name: journal-abbrev        # → journal-name-short covers this
-       columns:
-         - pubmed.publication.journal-abbrev
```

### 5.4 Fix `id-and-status` Overloading (MEDIUM)

```diff
  # Move fields-of-study to terms-and-keywords-and-topics:
  # In id-and-status group:
-     - base-name: fields-of-study
-       columns:
-         - semanticscholar.publication.fields-of-study

  # In terms-and-keywords-and-topics group:
+     - base-name: fields-of-study
+       columns:
+         - semanticscholar.publication.fields-of-study

  # Move publication-type to publication-types:
  # In id-and-status group:
-     - base-name: publication-type
-       columns:
-         - chembl.publication.publication-type
-         - pubmed.publication.publication-type

  # In publication-types group:
+     - base-name: publication-type
+       columns:
+         - chembl.publication.publication-type
+         - pubmed.publication.publication-type
```

### 5.5 Reclassify TRASH Group (MEDIUM)

```diff
  # Move content-hash to system (not business data, not trash):
  # In trash group:
-     - base-name: content-hash
-       ...

  # In a new 'system' group or remove from field-groups entirely
  # (system fields are handled separately by MergeService)

  # Consider promoting language to a proper group:
  # If multilingual analytics are needed:
-     - base-name: language        # from trash
+     # Move to bibliography or a new 'metadata' group

  # Consider promoting license-url:
-     - base-name: license-url     # from trash
+     # Move to a new 'open-access' group alongside is-oa, oa-status
```

### 5.6 Add Missing `author-details` to YAML (MEDIUM)

```diff
  # In trash group (consistent with Python mapping):
+     - base-name: author-details
+       columns:
+         - crossref.publication.author-details
```

### 5.7 Sync Python FIELD-TO-GROUP-MAPPING (MEDIUM)

Add missing canonical field names to `publication-field-groups.py`:

```diff
  FIELD-TO-GROUP-MAPPING = {
      ...
+     "publication-doi": PublicationFieldGroup.ID-AND-STATUS,
+     "publication-pmid": PublicationFieldGroup.ID-AND-STATUS,
+     "publication-pmc-id": PublicationFieldGroup.ID-AND-STATUS,
+     "journal-name": PublicationFieldGroup.BIBLIOGRAPHY,
+     "journal-title": PublicationFieldGroup.TRASH,       # legacy
+     "journal-abbrev": PublicationFieldGroup.TRASH,       # legacy
+     "keywords": PublicationFieldGroup.TERMS-AND-KEYWORDS-AND-TOPICS,
+     "topics": PublicationFieldGroup.TERMS-AND-KEYWORDS-AND-TOPICS,
+     "mesh": PublicationFieldGroup.TERMS-AND-KEYWORDS-AND-TOPICS,
+     "pages": PublicationFieldGroup.BIBLIOGRAPHY,
+     "type": PublicationFieldGroup.PUBLICATION-TYPES,
+     "issn-list": PublicationFieldGroup.BIBLIOGRAPHY,
+     "pub-date": PublicationFieldGroup.DATE-AND-PLACES,   # (already present)
      ...
  }
```

---

## 6. Breaking Change Risk Assessment

| Change | Breaking Risk | Mitigation |
|--------|--------------|------------|
| Remove `doi` base-name from field-groups YAML | **LOW** — ghost column, doesn't exist post-alias | Verify with test: `pytest tests/unit/infrastructure/config/test-field-group-loader.py` |
| Remove `year` base-name from field-groups YAML | **LOW** — ghost column, doesn't exist post-alias | Same |
| Remove `mesh`/`mesh-terms`/`keywords`/`topics` | **MEDIUM** — if any consumer queries by legacy name | Add to `field-aliases` in `publication.yaml` for backward compat |
| Move `fields-of-study` to different group | **LOW** — only affects column ordering | Gold output columns unchanged |
| Move `publication-type` to `publication-types` group | **LOW** — field still in Gold, just reordered | No downstream schema change |
| Move `content-hash` out of TRASH | **MEDIUM** — changes Gold inclusion if moved to non-trash group | Keep in TRASH or create dedicated `system` group with `include-in-gold: false` |
| Add entries to Python `FIELD-TO-GROUP-MAPPING` | **NONE** — additive change | Run `mypy --strict` to verify |
| Remove `journal-full-title`/`journal-title`/`journal-abbrev` | **MEDIUM** — if downstream reports use these | Deprecate first, add to `field-aliases` |
| Promote `language` from TRASH | **HIGH** — adds column to Gold output | Requires Gold schema version bump |
| Promote `license-url` from TRASH | **HIGH** — adds column to Gold output | Requires Gold schema version bump |

### Overall Breaking Risk: **MEDIUM**

Most changes are additive (Python mapping) or remove ghost columns (YAML cleanup). The riskiest changes involve promoting fields from TRASH to Gold, which should be gated behind a schema version bump.

---

## 7. Recommended Action Priority

| Priority | Action | Effort |
|----------|--------|--------|
| P0 | Remove ghost alias pairs (doi/year/pmid/pmc-id) from field-groups YAML | Small |
| P0 | Add `author-details` to YAML TRASH group | Small |
| P0 | Sync Python FIELD-TO-GROUP-MAPPING with canonical names | Small |
| P1 | Consolidate MeSH/keywords/topics triplicates | Medium |
| P1 | Fix `id-and-status` overloading | Medium |
| P1 | Consolidate journal naming (7 → 4 fields) | Medium |
| P2 | Reclassify `content-hash` as system, not trash | Small |
| P2 | Evaluate `language`/`license-url` for Gold promotion | Decision needed |
| P3 | Unify the two publication YAML schemas (column-groups vs field-groups) | Large |

---

## 8. Assay / Molecule Schemas — No Issues

Both `assay.yaml` and `molecule.yaml` are well-structured:
- No TRASH group (molecule uses `complex-fields` excluded from Gold)
- No alias duplication
- Clear conflict resolution tables
- Proper join key documentation
- No ghost columns

---

*Generated by: py-audit-bot | Session: composite-schemas-audit-2026-02-17*
