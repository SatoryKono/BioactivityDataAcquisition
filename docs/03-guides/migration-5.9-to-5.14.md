# Migration Guide: 5.9 → 5.14

**Target versions:** 5.9.0 → 5.14.0
**Release dates:** 2026-01-06 → 2026-02-09
**Migration time:** ~15-30 minutes
**Breaking changes:** ⚠️ **YES** (Publication schema fields renamed)

---

## Overview

Versions 5.10-5.14 introduce significant enhancements to publication validation, composite pipelines, and schema standardization. Most changes are backward-compatible, but **publication field renames** require data migration.

**Key changes:**
- ✅ Publication field standardization (5.14.0) — **BREAKING**
- ✅ Comprehensive publication validation system (5.13.0)
- ✅ Composite activity pipeline (5.11.0)
- ✅ UniProt extended fields (5.10.0)

---

## Breaking Changes

### 🔴 Publication Field Renames (5.14.0)

**Affected providers:** All 5 publication providers (ChEMBL, PubMed, CrossRef, OpenAlex, Semantic Scholar)

**Changes:**

| Old Field Name | New Field Name | Reason |
|----------------|----------------|--------|
| `citation-count` | `citations-received` | Semantic clarity (incoming vs outgoing) |
| `author-orcid-list` | `author-orcids` | Naming consistency |

**Impact:**
- ❌ Silver layer queries using old field names will fail
- ❌ Gold layer reports may break if not updated
- ✅ Bronze layer unaffected (raw data preserved)

**Migration steps:**

#### Step 1: Update SQL queries

```sql
-- BEFORE (5.9)
SELECT
    document-chembl-id,
    citation-count,
    author-orcid-list
FROM chembl.publication;

-- AFTER (5.14)
SELECT
    document-chembl-id,
    citations-received,
    author-orcids
FROM chembl.publication;
```

#### Step 2: Update DQ configs

If you have custom DQ rules referencing these fields:

```yaml
# configs/quality/entities/chembl/publication.yaml

# BEFORE (5.9)
- field: citation-count
  validation: range
  min: 0

# AFTER (5.14)
- field: citations-received
  validation: range
  min: 0
```

#### Step 3: Rebuild Gold layer

```bash
# Rebuild all publication pipelines
bioetl run --pipeline chembl-publication --run-type rebuild --yes
bioetl run --pipeline pubmed-publication --run-type rebuild --yes
bioetl run --pipeline crossref-publication --run-type rebuild --yes
bioetl run --pipeline openalex-publication --run-type rebuild --yes
bioetl run --pipeline semanticscholar-publication --run-type rebuild --yes
```

**Automation:**
```bash
# Rebuild all publication providers
for provider in chembl pubmed crossref openalex semanticscholar; do
    bioetl run --pipeline ${provider}-publication --run-type rebuild --yes
done
```

**Estimated time:** ~30-60 minutes per provider (depending on data volume)

---

## New Features

### 1. Publication Validation System (5.13.0)

**Purpose:** Comprehensive 5-level validation strategy for publication data quality.

**Validation levels:**

| Level | Description | Tests | Default |
|-------|-------------|-------|---------|
| **Base** | Pandera schema validation (types, regex, nullable) | 329 | ✅ Enabled |
| **Structural** | Cross-field consistency (page ordering, year matching) | 16 | ✅ Enabled |
| **External** | HTTP-based ID verification with upstream providers | 16 | ❌ Disabled |
| **Logical** | Range constraints and invariants | 12 | ✅ Enabled |
| **Semantic** | NLP-based text consistency (title-abstract similarity) | 13 | ❌ Disabled |

**Usage:**

```bash
# Balanced mode (default) - Base + Structural + Logical
bioetl run --pipeline pubmed-publication

# Strict mode - All 5 levels
bioetl run --pipeline pubmed-publication --validation-mode strict

# Fast mode - Base only
bioetl run --pipeline pubmed-publication --validation-mode fast
```

**DQ flags in Silver:**
- `-dq-error`: FAIL (blocking) — record rejected
- `-dq-warn`: WARN (quarantine) — record flagged for manual review

**Documentation:**
- [ADR-033: Publication Validation Strategy](../02-architecture/decisions/ADR-033-publication-validation-strategy.md)
- [Publication Validation Guide](publication-validation-guide.md)
- [Operational Runbook](../05-operations/runbooks/publication-validation-runbook.md)

---

### 2. Composite Activity Pipeline (5.11.0)

**Purpose:** Combine ChEMBL activity data with compound record metadata in a single Gold table.

**Structure:**
- **Seed:** `chembl_activity` (bioactivity measurements)
- **Dependency:** `chembl-compound-record` (compound metadata, optional)
- **Join:** LEFT OUTER join on `molecule-chembl-id`

**Usage:**

```bash
# Run composite pipeline
bioetl run-composite --composite activity

# With limits (testing)
bioetl run-composite --composite activity --seed-limit 1000
```

**Output:** `data/gold/composite-activity/`

**Configuration:** `configs/pipelines/composite/activity.yaml`

**Documentation:** [ADR-026: Composite Pipeline Pattern](../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)

---

### 3. UniProt Extended Fields (5.10.0)

**Added 22 new fields** to UniProt protein pipeline:

**Taxonomy:**
- `superkingdom`, `phylum`, `genus`

**Gene Ontology:**
- `molecular-function`, `cellular-component`

**Structural Features:**
- `topology`, `transmembrane`, `intramembrane`, `signal-peptide`, `propeptide`

**PTM Features:**
- `glycosylation`, `lipidation`, `disulfide-bond`, `modified-residue`
- `phosphorylation`, `acetylation`, `ubiquitination`

**Isoforms:**
- `isoform-names`, `isoform-ids`, `isoform-synonyms`

**Reactions:**
- `reactions`, `reaction-ec-numbers`

**Usage:**

```bash
# Rebuild UniProt to get new fields
bioetl run --pipeline uniprot-protein --run-type rebuild --yes
```

**Data availability:** Fields populated only for entries with relevant data (nullable).

---

## Configuration Changes

### 1. Deprecated Parameter Migration (5.12.0)

**Change:** `column-groups-file` → `data-schema-file`

**Affected configs:** 21 pipeline configs across all providers

**Migration:**

```yaml
# BEFORE (5.9)
silver-config:
  column-groups-file: configs/schemas/chembl/activity.yaml

# AFTER (5.14)
silver-config:
  data-schema-file: configs/schemas/chembl/activity.yaml
```

**Note:** Old parameter still works (deprecated warning), will be removed in 6.0.

---

### 2. Composite Pipeline Output Paths (5.12.0)

**Change:** Removed redundant explicit output paths — now auto-computed.

**Before (5.9):**
```yaml
# configs/pipelines/composite/activity.yaml
output:
  gold-path: data/gold/composite-activity
```

**After (5.14):**
```yaml
# configs/pipelines/composite/activity.yaml
# output.gold-path removed — auto-computed as:
# data/gold/composite-{pipeline-name}/
```

**Impact:** No action required — convention-based paths work automatically.

---

## Validation Enhancements

### 1. ORCID Format Validation (5.14.0)

**Added:** ORCID regex validation in `PublicationBaseSchema`

```python
# Pattern: ^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$
# Valid:   0000-0001-2345-678X
# Invalid: 0000000123456789
```

**Impact:** Records with malformed ORCIDs will be flagged in `-dq-warn`.

---

### 2. MIN-PUBLICATION-YEAR Change (5.14.0)

**Change:** Lowered from 1800 → 1500

**Reason:** Support for historical publications (e.g., Renaissance era scientific texts)

**Impact:** Publications dated 1500-1800 now pass validation.

---

### 3. ISSN Regex Constant (5.14.0)

**Added:** `ISSN-PATTERN` in `domain/schemas/constants.py`

```python
ISSN-PATTERN = r"^\d{4}-\d{3}[\dX]$"
# Valid:   1234-567X
# Invalid: 12345678
```

---

## CLI Changes

### 1. Entry Point Update

**Old (5.9):**
```bash
python -m bioetl.main run --pipeline chembl_activity
```

**New (5.14):**
```bash
# Preferred (via setuptools entry point)
bioetl run --pipeline chembl_activity

# Or development mode
python -m bioetl.interfaces.cli run --pipeline chembl_activity
```

**Note:** Old entry point still works but is considered legacy.

---

### 2. Validation Mode Flag (5.13.0)

**New flag:** `--validation-mode {strict,balanced,fast}`

```bash
# Enable all 5 validation levels
bioetl run --pipeline pubmed-publication --validation-mode strict
```

---

## Testing Changes

### 1. Generated Tests (5.13.0)

**Added:** 471 auto-generated tests for publication validation

**Location:** `tests-generated/`

**Run:**
```bash
pytest tests-generated/test-validation-base-*.py
pytest tests-generated/test-validation-structural-*.py
```

---

### 2. VCR Cassettes

**No breaking changes** — all existing VCR cassettes remain valid.

---

## Performance Impact

| Change | Impact | Notes |
|--------|--------|-------|
| Publication validation | +5-10% overhead | Only Base+Structural enabled by default |
| Composite pipelines | Neutral | Eliminates redundant Gold writes |
| UniProt extended fields | +2-3% overhead | Minimal (20 new fields) |

---

## Rollback Plan

If issues arise after upgrade:

### Option 1: Downgrade

```bash
# Downgrade to 5.9.0
pip install bioetl==5.9.0

# Restore old data
# (assuming you backed up before rebuild)
rm -rf data/silver/chembl.publication
cp -r backup/data/silver/chembl.publication data/silver/
```

### Option 2: Disable New Features

```bash
# Disable validation levels
export BIOETL-VALIDATION-MODE=fast  # Base only

# Skip composite pipelines
# (use individual pipelines instead)
```

---

## Migration Checklist

- [ ] **Backup data** (especially Silver layer)
  ```bash
  tar -czf bioetl-backup-$(date +%Y%m%d).tar.gz data/silver/ data/gold/
  ```

- [ ] **Upgrade package**
  ```bash
  pip install --upgrade bioetl==5.14.0
  ```

- [ ] **Update SQL queries** (replace `citation-count`, `author-orcid-list`)

- [ ] **Update custom DQ configs** (if using old field names)

- [ ] **Rebuild publication Gold layers**
  ```bash
  for provider in chembl pubmed crossref openalex semanticscholar; do
      bioetl run --pipeline ${provider}-publication --run-type rebuild --yes
  done
  ```

- [ ] **Test queries** (verify new field names work)
  ```sql
  SELECT citations-received, author-orcids FROM chembl.publication LIMIT 10;
  ```

- [ ] **Update documentation** (if you have custom docs referencing old fields)

- [ ] **Run test suite**
  ```bash
  bioetl health check
  pytest tests/integration/
  ```

---

## Getting Help

**Issues:** [GitHub Issues](https://github.com/SatoryKono/BioactivityDataAcquisition2/issues)

**Documentation:**
- [CHANGELOG.md](../../CHANGELOG.md) — Full release notes
- [RULES.md](../00-project/RULES.md) — Project governance
- [ADRs](../02-architecture/decisions/) — Architecture decisions

**Support:** Create an issue with:
- BioETL version
- Python version
- Error message or unexpected behavior
- Steps to reproduce

---

## Summary

**Mandatory actions:**
1. ✅ Update SQL queries (field renames)
2. ✅ Rebuild publication Gold layers
3. ✅ Update custom DQ configs (if any)

**Optional actions:**
1. ⚪ Explore publication validation system
2. ⚪ Test composite activity pipeline
3. ⚪ Rebuild UniProt for extended fields

**Estimated migration time:**
- Minimal setup: 15 minutes (code update + query fixes)
- With data rebuild: 30-60 minutes per provider

**Compatibility:**
- Python: 3.11+ (unchanged)
- Dependencies: See `pyproject.toml` for updated versions
- Operating systems: Linux, macOS, Windows (unchanged)
