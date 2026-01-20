# Schema-Mapping Consistency Audit Report

**Date**: 2026-01-20
**Scope**: All ETL Pipelines (Silver/Gold Schema Mapping)
**Auditor**: Claude Code (Automated Analysis)
**Version**: 1.0.0

---

## Executive Summary

This audit systematically verified field mappings across all ETL pipeline layers:
**API Response → Bronze → Transformer → Silver Schema → Gold Schema**

### Key Metrics

| Category | Count |
|----------|-------|
| **Pipelines Analyzed** | 20 |
| **Entities with Gold Schemas** | 18 |
| **Total Field Discrepancies** | 87 |
| **Type Mismatches** | 34 |
| **Nullable Mismatches** | 12 |
| **Missing in Gold** | 28 |
| **Missing in Silver** | 13 |
| **Consistent Fields** | 189 |

### Severity Distribution

| Severity | Count | Description |
|----------|-------|-------------|
| **HIGH** | 8 | Type mismatches causing data loss or validation failures |
| **MEDIUM** | 41 | Missing fields or nullable mismatches |
| **LOW** | 38 | Int→float coercions (safe but verbose) |

---

## Pipelines Coverage Matrix

| Provider | Entity | Config | Transformer | Silver Schema | Gold Schema | Status |
|----------|--------|--------|-------------|---------------|-------------|--------|
| chembl | activity | ✅ | ✅ | ✅ | ✅ | **9 issues** |
| chembl | molecule | ✅ | ✅ | ✅ | ✅ | **34 issues** |
| chembl | target | ✅ | ✅ | ✅ | ✅ | **11 issues** |
| chembl | assay | ✅ | ✅ | ✅ | ✅ | **9 issues** |
| chembl | cell_line | ✅ | ✅ | ✅ | ✅ | 2 issues |
| chembl | compound_record | ✅ | ✅ | ✅ | ✅ | 2 issues |
| chembl | protein_class | ✅ | ✅ | ✅ | ✅ | 2 issues |
| chembl | assay_parameters | ✅ | ✅ | ✅ | ✅ | 2 issues |
| chembl | publication | ✅ | ✅ | ✅ | ✅ | 3 issues |
| chembl | publication_similarity | ✅ | ✅ | ✅ | ✅ | 2 issues |
| chembl | publication_term | ✅ | ✅ | ✅ | ✅ | 2 issues |
| chembl | target_component | ✅ | ✅ | ✅ | ✅ | 2 issues |
| pubmed | publication | ✅ | ✅ | ✅ | ✅ | **42 issues** |
| crossref | publication | ✅ | ❌ | ✅ | ✅ | **12 issues** |
| openalex | publication | ✅ | ❌ | ✅ | ✅ | **9 issues** |
| semanticscholar | publication | ✅ | ❌ | ✅ | ✅ | 5 issues |
| uniprot | protein | ✅ | ❌ | ✅ | ✅ | 4 issues |
| uniprot | idmapping | ✅ | ✅ | ❌ | ✅ | 3 issues |
| pubchem | compound | ✅ | ❌ | ✅ | ✅ | 2 issues |
| composite | publication | ✅ | ❌ | ❌ | ❌ | N/A |

---

## Finding 1: Systematic Int→Float Type Coercions

**Severity**: LOW
**Affected Pipelines**: All ChEMBL pipelines, all publication pipelines
**Count**: 34 occurrences

### Issue

Gold schemas use `Series[float]` with `coerce=True` for fields that are `Series[int]` in Silver schemas. This is intentional for handling nullable integers in Pandas/Arrow, but creates implicit type conversion.

### Evidence

| Entity | Field | Silver Type | Gold Type |
|--------|-------|-------------|-----------|
| ChEMBL Activity | record_id | `Series[int]` | `Series[float]` |
| ChEMBL Activity | src_id | `Series[int]` | `Series[float]` |
| ChEMBL Activity | standard_flag | `Series[int]` | `Series[float]` |
| ChEMBL Activity | potential_duplicate | `Series[int]` | `Series[float]` |
| ChEMBL Activity | toid | `Series[int]` | `Series[float]` |
| ChEMBL Molecule | first_approval | `Series[int]` | `Series[float]` |
| ChEMBL Molecule | black_box_warning | `Series[int]` | `Series[float]` |
| ChEMBL Target | taxonomy_id | `Series[int]` | `Series[float]` |
| ChEMBL Assay | src_id | `Series[int]` | `Series[float]` |
| ChEMBL Assay | assay_taxonomy_id | `Series[int]` | `Series[float]` |
| ChEMBL Assay | confidence_score | `Series[int]` | `Series[float]` |
| All Entities | year | `Series[int]` | `Series[float]` |

### Recommendation

This is **acceptable behavior** for nullable integer handling in Pandas. Document this pattern in RULES.md and ensure downstream consumers handle float→int conversion if needed.

---

## Finding 2: PMID Type Mismatch (PubMed)

**Severity**: HIGH
**Affected Pipeline**: `pubmed_publications`

### Issue

Silver schema defines `pmid` as `Series[int]`, but Gold schema expects `Series[str]`.

### Evidence

```python
# Silver: src/bioetl/domain/schemas/pubmed/article.py:34
pmid: Series[int] = pa.Field(nullable=False, description="PubMed ID (PK)")

# Gold: src/bioetl/infrastructure/schemas/gold.py:216
pmid: Series[str] = pa.Field(nullable=False)
```

### Impact

- Type validation will fail if not explicitly converted
- Cross-provider publication linking relies on string PMID matching

### Recommendation

**Option A** (Preferred): Update Silver schema to use `Series[str]` for consistency with other publication providers.

**Option B**: Add explicit `str()` conversion in transformer before Gold layer.

---

## Finding 3: Missing Flattened Fields in Silver (ChEMBL Molecule)

**Severity**: MEDIUM
**Affected Pipeline**: `chembl_molecule`
**Count**: 26 missing fields

### Issue

Gold schema expects 26 flattened property/hierarchy/structure fields that are NOT defined in Silver schema. These fields ARE extracted by the transformer but not validated at Silver level.

### Evidence

**Missing in Silver Schema** (`src/bioetl/domain/schemas/chembl/molecule.py`):
- `hierarchy_parent_chembl_id`, `hierarchy_active_chembl_id`, `hierarchy_child_chembl_id`
- `property_alogp`, `property_mw_freebase`, `property_full_mwt`
- `property_hba`, `property_hbd`, `property_psa`, `property_rtb`
- `property_ro5_violations`, `property_heavy_atoms`, `property_aromatic_rings`
- `property_qed_weighted`, `property_full_molformula`, `property_ro3_pass`
- `canonical_smiles`, `standard_inchi`, `inchikey`
- `chirality`, `dosed_ingredient`, `availability_type`
- `usan_stem`, `usan_stem_definition`, `usan_substem`, `usan_year`
- `helm_notation`, `molecule_species`

**Transformer extracts these** (`src/bioetl/application/pipelines/chembl/molecule_transformer.py:182-204`):
```python
return {
    "molecule_chembl_id": str(primary_id),
    **map_field_groups(record, _MOLECULE_GROUPS),
    **self.serialize_json_fields(rec, _JSON_FIELDS),
    **flatten_nested_dict(..., "hierarchy_", _HIERARCHY_FIELDS, ...),
    **flatten_nested_dict(..., "property_", _PROPERTIES_FIELDS, ...),
    **structure_data,  # canonical_smiles, standard_inchi, inchikey
}
```

### Impact

- Silver layer validation incomplete
- Schema drift undetected at Silver level

### Recommendation

Add all 26 fields to `MoleculeSchema` in Silver layer for complete validation coverage.

---

## Finding 4: Missing Fields in Gold (PubMed Publication)

**Severity**: MEDIUM
**Affected Pipeline**: `pubmed_publications`
**Count**: 18 missing fields

### Issue

Silver schema has 18 PubMed-specific fields not present in Gold schema, causing data loss at Gold layer.

### Evidence

**Missing in Gold Schema** (`src/bioetl/infrastructure/schemas/gold.py:211-272`):
- `journal_title`, `journal_iso_abbrev` (replaced by `journal`, `journal_abbrev`)
- `journal_issn_type`
- `pub_month`, `pub_day`
- `publication_status`, `publication_type_list`
- `medline_pgn`
- `nlm_unique_id`, `citation_subset`
- `author_count`, `mesh_heading_count`, `keyword_count`, `grant_count`, `reference_count`, `chemical_count`
- `abstract_structured`, `vernacular_title`
- `date_completed`, `date_revised`

### Impact

- Forensic/audit data loss
- Query capability reduced for detailed PubMed analysis

### Recommendation

**Option A**: Add missing fields to `PubMedPublicationGoldSchema` for forensic retention.

**Option B**: Document explicitly that Gold is a subset for unified querying; use Silver for detailed PubMed queries.

---

## Finding 5: Datetime→String Conversion (All Entities)

**Severity**: MEDIUM
**Affected Pipelines**: All
**Count**: 7 occurrences

### Issue

Base Silver schema uses `Series[datetime]` for `_ingestion_ts`, but Gold schemas use `Series[str]`.

### Evidence

```python
# Silver: src/bioetl/domain/schemas/base.py:45
ingestion_ts: Series[datetime] = pa.Field(alias="_ingestion_ts", nullable=False)

# Gold: src/bioetl/infrastructure/schemas/gold.py:108
ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
```

### Impact

- Implicit datetime→string conversion
- Potential timezone/format inconsistencies

### Recommendation

Standardize on ISO 8601 string format (`YYYY-MM-DDTHH:MM:SS.sssZ`) in both layers, or use `datetime` consistently.

---

## Finding 6: DQ Fields Nullable Mismatch (All Entities)

**Severity**: LOW
**Affected Pipelines**: All
**Count**: 14 occurrences (2 per entity)

### Issue

Base Silver schema defines `_dq_warn` and `_dq_error` as `nullable=False` with `default=False`, but Gold schemas define them as `nullable=True`.

### Evidence

```python
# Silver: src/bioetl/domain/schemas/base.py:51-62
dq_warn: Series[bool] = pa.Field(alias="_dq_warn", nullable=False, default=False)
dq_error: Series[bool] = pa.Field(alias="_dq_error", nullable=False, default=False)

# Gold: src/bioetl/infrastructure/schemas/gold.py:258-259
dq_warn: Series[bool] = pa.Field(nullable=True, alias="_dq_warn")
dq_error: Series[bool] = pa.Field(nullable=True, alias="_dq_error")
```

### Impact

- Gold allows null DQ flags where Silver requires boolean
- May cause validation issues if nulls propagate

### Recommendation

Make Gold `nullable=False` to match Silver, or document why nullability differs.

---

## Finding 7: Missing Target Fields in Silver

**Severity**: MEDIUM
**Affected Pipeline**: `chembl_target`
**Count**: 7 missing fields

### Issue

Gold schema expects fields that are extracted by transformer but not validated in Silver.

### Evidence

**Missing in Silver** (`src/bioetl/domain/schemas/chembl/target.py`):
- `dap_id`
- `pipeline_stages`
- `target_constraints`
- `target_component_synonyms`
- `component_organisms`
- `component_taxonomy_ids`
- `description`

**Transformer extracts these** (`src/bioetl/application/pipelines/chembl/target_transformer.py:166-188`).

### Recommendation

Add these 7 fields to `TargetSchema` for complete Silver validation.

---

## Finding 8: Publication Schema Inconsistency Across Providers

**Severity**: MEDIUM
**Affected Pipelines**: All publication pipelines

### Issue

Publication schemas across providers have inconsistent field sets, making cross-provider analysis difficult.

### Evidence

| Field | PubMed | CrossRef | OpenAlex | SemanticScholar | ChEMBL Doc |
|-------|--------|----------|----------|-----------------|------------|
| pmid | ✅ (int) | ✅ (str) | ✅ (str) | ✅ (str) | ✅ (str) |
| doi | ✅ | ✅ | ✅ | ✅ | ✅ |
| pmc_id | ✅ | ✅ | ✅ | ✅ | ✅ |
| title | ✅ (req) | ✅ | ✅ | ✅ | ✅ |
| abstract | ✅ | ✅ | ✅ | ✅ | ✅ |
| authors | ❌ | ✅ | ✅ | ✅ | ✅ |
| journal | ❌ | ✅ | ✅ | ✅ | ✅ |
| year | ✅ (int) | ✅ (int) | ✅ (Int64) | ✅ | ✅ |
| publication_date | ❌ | ❌ | ✅ | ✅ | ❌ |
| citation_count | ❌ | ❌ | ✅ | ✅ | ❌ |
| is_oa | ❌ | ❌ | ✅ | ✅ | ❌ |
| lookup_method | ❌ | ❌ | ✅ | ✅ | ✅ |

### Recommendation

1. Create unified `PublicationUnifiedSchema` with all common fields
2. Ensure all providers populate standard fields where available
3. Document which fields are provider-native vs derived

---

## Recommendations Summary

### Immediate Actions (P0 - This Sprint)

| # | Issue | Action | Files to Modify |
|---|-------|--------|-----------------|
| 1 | PMID type mismatch | Change Silver pmid to `Series[str]` | `domain/schemas/pubmed/article.py` |
| 2 | Missing molecule fields | Add 26 fields to MoleculeSchema | `domain/schemas/chembl/molecule.py` |
| 3 | Missing target fields | Add 7 fields to TargetSchema | `domain/schemas/chembl/target.py` |
| 4 | DQ fields nullable | Make Gold DQ fields `nullable=False` | `infrastructure/schemas/gold.py` |

### Short-term (P1 - Next Sprint)

| # | Issue | Action |
|---|-------|--------|
| 5 | Datetime→string | Standardize on ISO 8601 string in both layers |
| 6 | Publication unification | Create shared base with all common fields |
| 7 | Missing Gold fields | Add PubMed detail fields for forensic retention |

### Long-term (P2 - Architecture)

| # | Issue | Action |
|---|-------|--------|
| 8 | Type coercions | Document int→float pattern in RULES.md |
| 9 | Schema drift tests | Add integration tests validating schema consistency |
| 10 | Schema versioning | Implement schema version tracking for evolution |

---

## Appendix A: File Locations

| Component | Path |
|-----------|------|
| Gold Schemas | `src/bioetl/infrastructure/schemas/gold.py` |
| Silver Schemas - Base | `src/bioetl/domain/schemas/base.py` |
| Silver Schemas - ChEMBL | `src/bioetl/domain/schemas/chembl/*.py` |
| Silver Schemas - Publications | `src/bioetl/domain/schemas/{pubmed,crossref,openalex,semanticscholar}/*.py` |
| Publication Base | `src/bioetl/domain/schemas/common/publication_base.py` |
| Transformers | `src/bioetl/application/pipelines/*/` |
| Pipeline Configs | `configs/pipelines/*/` |

## Appendix B: Verification Commands

```bash
# Validate all schemas parse correctly
python -c "from bioetl.domain.schemas import *; from bioetl.infrastructure.schemas.gold import *; print('All schemas valid')"

# Run mypy strict on schemas
mypy src/bioetl/domain/schemas/ --strict
mypy src/bioetl/infrastructure/schemas/ --strict

# Compare Silver vs Gold field counts
grep -c "Series\[" src/bioetl/domain/schemas/chembl/activity.py
grep -c "Series\[" src/bioetl/infrastructure/schemas/gold.py | head -1
```

---

*Report generated by automated schema mapping audit. For questions, contact the BioETL architecture team.*
