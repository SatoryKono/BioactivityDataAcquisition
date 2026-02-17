# Audit: Composite Schemas — Field Groups, TRASH, Alias Chaos

**Date:** 2026-02-17
**Scope:** `configs/schemas/composite/**`
**Status:** WARN (score 6.8/10)

---

## Executive Summary

Audit of `configs/schemas/composite/` reveals **3 critical issues**, **5 high-severity issues**, and **8 medium-severity issues**. The primary problems are:

1. **Alias chaos** — legacy and canonical field names coexist as separate base_names in `field_groups/publication.yaml`, creating ghost columns after alias resolution
2. **TRASH group** contains fields that arguably belong elsewhere (language, license_url) while missing fields that should be trash
3. **Two parallel publication schemas** (`publication.yaml` column_groups vs `field_groups/publication.yaml`) with semantic drift between them

The `assay.yaml` and `molecule.yaml` composite schemas are clean and well-structured.

---

## 1. Files Audited

| File | Lines | Status |
|------|-------|--------|
| `configs/schemas/composite/assay.yaml` | 252 | PASS |
| `configs/schemas/composite/molecule.yaml` | 260 | PASS |
| `configs/schemas/composite/publication.yaml` | 355 | WARN |
| `configs/schemas/composite/field_groups/publication.yaml` | 572 | WARN |

Supporting files cross-referenced:
- `src/bioetl/domain/value_objects/publication_field_groups.py` (Python enum + mapping)
- `src/bioetl/domain/composite/field_groups.py` (FieldGroupRegistry)
- `src/bioetl/application/composite/merger.py` (MergeService consumption)
- All 5 provider schemas (`chembl/`, `crossref/`, `openalex/`, `pubmed/`, `semanticscholar/`)

---

## 2. Problematic Field Groups

### 2.1 TRASH Group — Audit

**Location:** `field_groups/publication.yaml` lines 535–572

Current TRASH fields:

| base_name | Provider(s) | Issue |
|-----------|-------------|-------|
| `content_domain_crossmark_restriction` | crossref | OK — CrossRef internal metadata |
| `content_domain_domains` | crossref | OK — CrossRef internal metadata |
| `content_hash` | all 5 | **PROBLEM** — system field, not business data; should be in `system` group |
| `language` | crossref, openalex, pubmed | **QUESTIONABLE** — has analytical value for multilingual corpora |
| `license_url` | crossref | **QUESTIONABLE** — relevant for OA/licensing analytics |
| `medline_pgn` | pubmed | OK — redundant with page_first/page_last |
| `src_id` | chembl | OK — ChEMBL-internal source identifier |

**Fields missing from TRASH that should be there:**

| base_name | Current Group | Issue |
|-----------|--------------|-------|
| `author_details` | Python: TRASH, YAML: **missing entirely** | 3-way inconsistency |
| `venue` | bibliography | SemanticScholar legacy field, superseded by `journal` |
| `journal_full_title` | bibliography | ChEMBL-only legacy, overlaps `journal` |
| `journal_title` | bibliography (YAML only) | PubMed-only legacy, overlaps `journal_name` |
| `journal_abbrev` | bibliography (YAML only) | PubMed-only legacy, overlaps `journal_name_short` |
| `issn_list` | bibliography | Redundant JSON blob, `issn`/`issn_print`/`issn_electronic` are canonical |
| `document_chembl_id` | id_and_status | Legacy alias for `publication_id`, should not coexist |
| `pub_date` | date_and_places | Legacy PubMed field, `publication_date` is canonical |

### 2.2 `id_and_status` Group — Overloaded

This group has become a catch-all (30+ fields in YAML). Fields that belong elsewhere:

| base_name | Should Be | Reason |
|-----------|-----------|--------|
| `fields_of_study` | terms_and_keywords_and_topics | Subject classification, not identifier |
| `is_oa` | open_access (new group) or bibliography | OA status flag |
| `oa_status` | open_access (new group) or bibliography | OA status detail |
| `open_access_url` | open_access (new group) or bibliography | OA access link |
| `publication_type` | publication_types | Type classification, not identifier |
| `publication_status` | date_and_places or bibliography | Workflow status, not identifier |

---

## 3. Alias Chaos — Duplicate base_names

### 3.1 Pre-alias / Post-alias Duplication

The `field_groups/publication.yaml` contains BOTH legacy and canonical names as separate `base_name` entries. After provider-level alias resolution (e.g., `doi → publication_doi`), the legacy columns no longer exist in the data, making these entries **ghost columns**.

| Legacy base_name | Canonical base_name | Providers with both | Risk |
|-----------------|---------------------|---------------------|------|
| `doi` | `publication_doi` | all 5 | **CRITICAL** — double-counting |
| `pmid` | `publication_pmid` | chembl, openalex, pubmed, s2 | **CRITICAL** — double-counting |
| `pmc_id` | `publication_pmc_id` | pubmed | HIGH — ghost column |
| `year` | `publication_year` | all 5 | **CRITICAL** — double-counting |
| `keywords` | `subject_keywords` | openalex, pubmed, s2 | HIGH — semantic overlap |
| `mesh_terms` | `subject_mesh` | openalex, pubmed | HIGH — semantic overlap |
| `topics` | `subject_topics` | openalex | MEDIUM — single provider |
| `pages` | `page_range` | crossref, pubmed, s2 | MEDIUM — both may exist |
| `journal_title` | `journal_name` | pubmed | MEDIUM — single provider |
| `mesh` | `subject_mesh` | openalex | MEDIUM — 3-way overlap |
| `type` | `publication_type` | crossref, openalex | HIGH — generic name |
| `pub_date` | `publication_date` | pubmed | MEDIUM — legacy |

### 3.2 Three-way Field Overlap Examples

**MeSH data:**
- `mesh` (openalex raw) → terms_and_keywords
- `mesh_terms` (openalex, pubmed) → terms_and_keywords
- `subject_mesh` (openalex, pubmed) → terms_and_keywords

All three track the same MeSH vocabulary data from the same providers.

**Journal naming:**
- `journal` — canonical (all providers)
- `journal_name` — pubmed, openalex, semanticscholar
- `journal_full_title` — chembl only
- `journal_title` — pubmed only
- `journal_name_short` — crossref, pubmed
- `journal_iso_abbrev` — pubmed
- `journal_abbrev` — pubmed

Seven base_names for journal nomenclature across 5 providers.

### 3.3 Python ↔ YAML Inconsistencies

| Field | Python (`FIELD_TO_GROUP_MAPPING`) | YAML (`field_groups/publication.yaml`) | YAML (`publication.yaml`) |
|-------|-----------------------------------|---------------------------------------|--------------------------|
| `author_details` | TRASH | **MISSING** | author_identifiers group |
| `publication_doi` | **MISSING** | id_and_status | identifiers_doi group |
| `publication_pmid` | **MISSING** | id_and_status | identifiers_pmid group |
| `publication_pmc_id` | **MISSING** | id_and_status | pmc_identifiers group |
| `journal_name` | **MISSING** | bibliography | journal group |
| `journal_title` | **MISSING** | bibliography | **MISSING** |
| `journal_abbrev` | **MISSING** | bibliography | **MISSING** |
| `mesh` | terms_and_keywords | terms_and_keywords | **MISSING** |
| `keywords` | **MISSING** | terms_and_keywords | **MISSING** |
| `topics` | **MISSING** | terms_and_keywords | **MISSING** |
| `type` | **MISSING** | publication_types | **MISSING** |
| `pages` | **MISSING** | bibliography | **MISSING** |
| `venue` | bibliography | bibliography | **MISSING** |
| `issn_list` | bibliography (YAML) | bibliography | **MISSING** |

---

## 4. Impact on Silver/Gold Layers

### 4.1 Silver Layer Impact

- **Storage waste**: Duplicate columns (`doi` + `publication_doi`) inflate parquet files
- **Schema confusion**: Consumers don't know which column to use
- **No data corruption**: Silver is append-only with all fields included
- **Risk**: LOW (Silver is forensic/debugging layer)

### 4.2 Gold Layer Impact

- **`include_in_gold: true` on `id_and_status`** propagates ALL misplaced fields to Gold
- `fields_of_study` appears in Gold as an "identifier" — misleading for analytics
- `publication_type` appears in Gold via `id_and_status` AND `publication_types` — potential duplication
- **`content_hash`** is marked TRASH, correctly excluded — but it's a system field, not business trash
- **`language`** excluded from Gold — may be wanted for multilingual analysis
- **`license_url`** excluded from Gold — may be wanted for OA analysis
- **Risk**: MEDIUM (Gold schema drift affects downstream analytics)

### 4.3 MergeService Behavior

From `application/composite/merger.py`:
```python
# Trash filtering happens AFTER merge, BEFORE Gold write
if self._field_group_registry is not None:
    trash_cols = self._field_group_registry.get_trash_columns(df.columns)
    df = df.drop(trash_cols)
```

System columns (`_*`) are **never** considered trash — `content_hash` (no underscore prefix) is correctly excluded. But the default_group=TRASH means **any unmapped field falls to trash and is silently dropped from Gold**.

---

## 5. Proposed Changes

### 5.1 Normalize Alias Pairs (CRITICAL — eliminate ghost columns)

Remove legacy `base_name` entries from `field_groups/publication.yaml`. Keep only canonical names.

```yaml
# REMOVE these base_names (ghost columns after alias resolution):
- doi          → keep only publication_doi
- pmid         → keep only publication_pmid  (add if missing)
- pmc_id       → keep only publication_pmc_id (add if missing)
- year         → keep only publication_year
- document_chembl_id → keep only publication_id
```

**Diff — `field_groups/publication.yaml`:**
```diff
  # Remove doi (lines 61-67)
-     - base_name: doi
-       columns:
-         - chembl.publication.doi
-         - crossref.publication.doi
-         - openalex.publication.doi
-         - pubmed.publication.doi
-         - semanticscholar.publication.doi

  # Remove document_chembl_id (lines 49-51)
-     - base_name: document_chembl_id
-       columns:
-         - chembl.publication.document_chembl_id

  # Remove year (lines 508-514)
-     - base_name: year
-       columns:
-         - chembl.publication.year
-         - crossref.publication.year
-         - openalex.publication.year
-         - pubmed.publication.year
-         - semanticscholar.publication.year

  # Add publication_year to date_and_places (currently missing)
+     - base_name: publication_year
+       columns:
+         - chembl.publication.publication_year
+         - crossref.publication.publication_year
+         - openalex.publication.publication_year
+         - pubmed.publication.publication_year
+         - semanticscholar.publication.publication_year
```

### 5.2 Consolidate MeSH/Keywords/Topics Triplicates (HIGH)

```diff
  # REMOVE mesh (openalex raw, superseded by subject_mesh):
-     - base_name: mesh
-       columns:
-         - openalex.publication.mesh

  # REMOVE mesh_terms (superseded by subject_mesh after alias resolution):
-     - base_name: mesh_terms
-       columns:
-         - openalex.publication.mesh_terms
-         - pubmed.publication.mesh_terms

  # KEEP subject_mesh as canonical

  # REMOVE keywords (superseded by subject_keywords after alias resolution):
-     - base_name: keywords
-       columns:
-         - openalex.publication.keywords
-         - pubmed.publication.keywords
-         - semanticscholar.publication.keywords

  # KEEP subject_keywords as canonical

  # REMOVE topics (superseded by subject_topics after alias resolution):
-     - base_name: topics
-       columns:
-         - openalex.publication.topics

  # KEEP subject_topics as canonical
```

### 5.3 Consolidate Journal Naming (HIGH)

```diff
  # KEEP: journal (canonical, all providers)
  # KEEP: journal_name (PubMed/OpenAlex/S2 display name)
  # KEEP: journal_name_short (CrossRef/PubMed abbreviation)
  # KEEP: journal_iso_abbrev (PubMed ISO)

  # MOVE to TRASH (redundant legacy):
-     - base_name: journal_full_title    # → journal covers this
-       columns:
-         - chembl.publication.journal_full_title

-     - base_name: journal_title         # → journal_name covers this
-       columns:
-         - pubmed.publication.journal_title

-     - base_name: journal_abbrev        # → journal_name_short covers this
-       columns:
-         - pubmed.publication.journal_abbrev
```

### 5.4 Fix `id_and_status` Overloading (MEDIUM)

```diff
  # Move fields_of_study to terms_and_keywords_and_topics:
  # In id_and_status group:
-     - base_name: fields_of_study
-       columns:
-         - semanticscholar.publication.fields_of_study

  # In terms_and_keywords_and_topics group:
+     - base_name: fields_of_study
+       columns:
+         - semanticscholar.publication.fields_of_study

  # Move publication_type to publication_types:
  # In id_and_status group:
-     - base_name: publication_type
-       columns:
-         - chembl.publication.publication_type
-         - pubmed.publication.publication_type

  # In publication_types group:
+     - base_name: publication_type
+       columns:
+         - chembl.publication.publication_type
+         - pubmed.publication.publication_type
```

### 5.5 Reclassify TRASH Group (MEDIUM)

```diff
  # Move content_hash to system (not business data, not trash):
  # In trash group:
-     - base_name: content_hash
-       ...

  # In a new 'system' group or remove from field_groups entirely
  # (system fields are handled separately by MergeService)

  # Consider promoting language to a proper group:
  # If multilingual analytics are needed:
-     - base_name: language        # from trash
+     # Move to bibliography or a new 'metadata' group

  # Consider promoting license_url:
-     - base_name: license_url     # from trash
+     # Move to a new 'open_access' group alongside is_oa, oa_status
```

### 5.6 Add Missing `author_details` to YAML (MEDIUM)

```diff
  # In trash group (consistent with Python mapping):
+     - base_name: author_details
+       columns:
+         - crossref.publication.author_details
```

### 5.7 Sync Python FIELD_TO_GROUP_MAPPING (MEDIUM)

Add missing canonical field names to `publication_field_groups.py`:

```diff
  FIELD_TO_GROUP_MAPPING = {
      ...
+     "publication_doi": PublicationFieldGroup.ID_AND_STATUS,
+     "publication_pmid": PublicationFieldGroup.ID_AND_STATUS,
+     "publication_pmc_id": PublicationFieldGroup.ID_AND_STATUS,
+     "journal_name": PublicationFieldGroup.BIBLIOGRAPHY,
+     "journal_title": PublicationFieldGroup.TRASH,       # legacy
+     "journal_abbrev": PublicationFieldGroup.TRASH,       # legacy
+     "keywords": PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
+     "topics": PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
+     "mesh": PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
+     "pages": PublicationFieldGroup.BIBLIOGRAPHY,
+     "type": PublicationFieldGroup.PUBLICATION_TYPES,
+     "issn_list": PublicationFieldGroup.BIBLIOGRAPHY,
+     "pub_date": PublicationFieldGroup.DATE_AND_PLACES,   # (already present)
      ...
  }
```

---

## 6. Breaking Change Risk Assessment

| Change | Breaking Risk | Mitigation |
|--------|--------------|------------|
| Remove `doi` base_name from field_groups YAML | **LOW** — ghost column, doesn't exist post-alias | Verify with test: `pytest tests/unit/infrastructure/config/test_field_group_loader.py` |
| Remove `year` base_name from field_groups YAML | **LOW** — ghost column, doesn't exist post-alias | Same |
| Remove `mesh`/`mesh_terms`/`keywords`/`topics` | **MEDIUM** — if any consumer queries by legacy name | Add to `field_aliases` in `publication.yaml` for backward compat |
| Move `fields_of_study` to different group | **LOW** — only affects column ordering | Gold output columns unchanged |
| Move `publication_type` to `publication_types` group | **LOW** — field still in Gold, just reordered | No downstream schema change |
| Move `content_hash` out of TRASH | **MEDIUM** — changes Gold inclusion if moved to non-trash group | Keep in TRASH or create dedicated `system` group with `include_in_gold: false` |
| Add entries to Python `FIELD_TO_GROUP_MAPPING` | **NONE** — additive change | Run `mypy --strict` to verify |
| Remove `journal_full_title`/`journal_title`/`journal_abbrev` | **MEDIUM** — if downstream reports use these | Deprecate first, add to `field_aliases` |
| Promote `language` from TRASH | **HIGH** — adds column to Gold output | Requires Gold schema version bump |
| Promote `license_url` from TRASH | **HIGH** — adds column to Gold output | Requires Gold schema version bump |

### Overall Breaking Risk: **MEDIUM**

Most changes are additive (Python mapping) or remove ghost columns (YAML cleanup). The riskiest changes involve promoting fields from TRASH to Gold, which should be gated behind a schema version bump.

---

## 7. Recommended Action Priority

| Priority | Action | Effort |
|----------|--------|--------|
| P0 | Remove ghost alias pairs (doi/year/pmid/pmc_id) from field_groups YAML | Small |
| P0 | Add `author_details` to YAML TRASH group | Small |
| P0 | Sync Python FIELD_TO_GROUP_MAPPING with canonical names | Small |
| P1 | Consolidate MeSH/keywords/topics triplicates | Medium |
| P1 | Fix `id_and_status` overloading | Medium |
| P1 | Consolidate journal naming (7 → 4 fields) | Medium |
| P2 | Reclassify `content_hash` as system, not trash | Small |
| P2 | Evaluate `language`/`license_url` for Gold promotion | Decision needed |
| P3 | Unify the two publication YAML schemas (column_groups vs field_groups) | Large |

---

## 8. Assay / Molecule Schemas — No Issues

Both `assay.yaml` and `molecule.yaml` are well-structured:
- No TRASH group (molecule uses `complex_fields` excluded from Gold)
- No alias duplication
- Clear conflict resolution tables
- Proper join key documentation
- No ghost columns

---

*Generated by: py-audit-bot | Session: composite-schemas-audit-2026-02-17*
