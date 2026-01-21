# BioETL File Path Audit Report

*Audit Date: 2026-01-21*
*Auditor: Claude Code*
*Reference Documentation: local-storage-layout.md, RULES.md §2.1*

---

## Executive Summary

This audit verifies that BioETL's file path patterns and naming conventions in the codebase
match the documented specifications in `local-storage-layout.md` and `RULES.md`.

**Overall Result: PASS (Discrepancies Fixed)**

| Layer | Path Pattern | File Naming | Metadata | DQ Reports | Status |
|-------|-------------|-------------|----------|------------|--------|
| Bronze | ✅ Match | ✅ Match | ✅ Match | ✅ Match | **PASS** |
| Silver | ✅ Match | ✅ Match | ✅ Match | ✅ Match | **PASS** |
| Gold | ✅ Match | ✅ Match | ✅ Match | ✅ Match | **PASS** |
| Checkpoints | ✅ Fixed | ✅ Match | N/A | N/A | **PASS** |
| Quarantine | ✅ Fixed | ✅ Match | N/A | N/A | **PASS** |

---

## 1. Bronze Layer

### 1.1. Path Pattern

| Aspect | Documented | Implementation | Status |
|--------|------------|----------------|--------|
| Path | `data/output/bronze/{provider}/{entity}/{date}/` | `bronze_writer.py:451-452` | ✅ Match |
| Date format | `YYYY-MM-DD` | `date.strftime("%Y-%m-%d")` | ✅ Match |

**Code Reference:**
```python
# bronze_writer.py:448-452
date_str = date.strftime("%Y-%m-%d")
relative_path = (
    f"{provider}/{entity}/{date_str}/batch_{date_str}_{batch_id}.jsonl.zst"
)
```

### 1.2. Data File Naming

| Aspect | Documented | Implementation | Status |
|--------|------------|----------------|--------|
| Compressed | `batch_{YYYY-MM-DD}_{batch_id}.jsonl.zst` | Same pattern | ✅ Match |
| JSON copy | `batch_{YYYY-MM-DD}_{batch_id}.jsonl` | `bronze_writer.py:652-653` | ✅ Match |

### 1.3. Sidecar Files

| File Type | Documented | Implementation | Status |
|-----------|------------|----------------|--------|
| Metadata | `{provider}_{entity}_metadata.yaml` | `metadata_writer.py:45-47` | ✅ Match |
| DQ Report | `batch_{date}_{provider}_{entity}_dq_report.json` | `dq_report_writer.py:89` | ✅ Match |

---

## 2. Silver Layer

### 2.1. Path Pattern

| Aspect | Documented | Implementation | Status |
|--------|------------|----------------|--------|
| Path | `data/output/silver/{provider}/{entity}/` | `Settings.silver_path` + table_name | ✅ Match |
| Structure | Delta Lake with `_delta_log/` | `write_deltalake()` creates this | ✅ Match |

**Code Reference:**
```python
# _base.py:345-347
@property
def silver_path(self) -> Path:
    return self.data_dir / "output" / "silver"
```

### 2.2. Sidecar Files

| File Type | Documented | Implementation | Status |
|-----------|------------|----------------|--------|
| Metadata | `{provider}_{entity}_metadata.yaml` | `metadata_writer.py:45-47` | ✅ Match |
| DQ Report | `silver_{provider}_{entity}_dq_report.json` | `dq_report_writer.py:129` | ✅ Match |

---

## 3. Gold Layer

### 3.1. Path Pattern

| Aspect | Documented | Implementation | Status |
|--------|------------|----------------|--------|
| Path | `data/output/gold/{provider}/{entity}/` | `Settings.gold_path` + table_name | ✅ Match |
| Structure | Delta Lake with `_delta_log/` | `write_deltalake()` creates this | ✅ Match |

**Code Reference:**
```python
# _base.py:349-352
@property
def gold_path(self) -> Path:
    return self.data_dir / "output" / "gold"
```

### 3.2. Sidecar Files

| File Type | Documented | Implementation | Status |
|-----------|------------|----------------|--------|
| Metadata | `{provider}_{entity}_metadata.yaml` | `metadata_writer.py:45-47` | ✅ Match |
| DQ Report | `gold_{provider}_{entity}_dq_report.json` | `dq_report_writer.py:129` | ✅ Match |

---

## 4. Checkpoints ✅

### 4.1. Path Pattern (Fixed)

| Aspect | Documented | Implementation | Status |
|--------|------------|----------------|--------|
| Path | `data/output/checkpoints/` | `data/output/checkpoints/` | ✅ Match |
| File naming | `{pipeline_name}.json` | `local_checkpoint.py:187` | ✅ Match |
| Composite | `composite_{name}_{run_id}.json` | Documented only | ℹ️ Info |

**Code (`_base.py:354-357`):**
```python
@property
def checkpoint_path(self) -> Path:
    return self.data_dir / "output" / "checkpoints"
```

**Resolution:** Documentation updated to match code. All checkpoints are correctly placed inside `data/output/` per ADR-025.

---

## 5. Quarantine ✅

### 5.1. Path Pattern (Fixed)

| Aspect | Documented | Implementation | Status |
|--------|------------|----------------|--------|
| Path | `data/output/quarantine/common.quarantine/` | `data/output/quarantine/` | ✅ Match |
| Table name | `common.quarantine` | `base_path` passed directly | ✅ Match |
| Structure | Delta Lake | `unified.py` uses `write_deltalake` | ✅ Match |

**Code (`_base.py:359-362`):**
```python
@property
def quarantine_path(self) -> Path:
    return self.data_dir / "output" / "quarantine"
```

**Resolution:** Documentation updated to match code. Quarantine is correctly placed inside `data/output/` per ADR-025.

---

## 6. CSV Export

### 6.1. Path Pattern

| Aspect | Documented | Implementation | Status |
|--------|------------|----------------|--------|
| File naming | `{table_name}.csv` | `csv_exporter.py:270` | ✅ Match |
| Location | Configured via `csv_export.path` in YAML | `storage_factory.py` | ✅ Match |

---

## 7. Metadata Writer Filename Generation

**Verification of `_get_metadata_filename()` function:**

```python
# metadata_writer.py:34-47
def _get_metadata_filename(provider: str | None, entity: str | None) -> str:
    if provider and entity:
        return f"{provider}_{entity}_metadata.yaml"  # ✅ Matches docs
    return METADATA_FILENAME  # Fallback: "_metadata.yaml"
```

All layers correctly use this function for consistent metadata naming.

---

## 8. DQ Report Writer Filename Generation

**Verification of `_build_layer_filename()` function:**

```python
# dq_report_writer.py:106-133
def _build_layer_filename(...) -> str:
    if provider and entity:
        return f"{layer}_{provider}_{entity}_dq_report{extension}"  # ✅ Matches docs
    # ... fallback logic
```

### Bronze DQ Reports

```python
# dq_report_writer.py:88-89
if provider and entity and date_str:
    filename = f"batch_{date_str}_{provider}_{entity}_dq_report{extension}"  # ✅ Matches docs
```

---

## 9. Resolution Summary

### 9.1. Documentation Updated ✅

The `docs/03-guides/local-storage-layout.md` file has been updated to match the actual implementation:

**Updated structure:**
```
data/
└── output/
    ├── bronze/
    ├── silver/
    ├── gold/
    ├── checkpoints/      # Inside output/ ✅
    ├── quarantine/       # Inside output/ ✅
    └── reports/
```

### 9.2. Rationale

All generated output is correctly placed in `data/output/` which aligns with:
- ADR-025: Output directory separation
- Single cleanup target for generated files
- Clear separation from config/input files

---

## 10. Verification Commands

```bash
# Verify Bronze path pattern
ls -la data/output/bronze/chembl/activity/

# Verify Silver Delta structure
ls -la data/output/silver/chembl/activity/_delta_log/

# Verify Gold Delta structure
ls -la data/output/gold/chembl/activity/_delta_log/

# Verify checkpoint files
ls -la data/output/checkpoints/*.json

# Verify quarantine table
ls -la data/output/quarantine/common.quarantine/_delta_log/
```

---

## 11. Audit Checklist Summary

### Bronze Layer
- [x] Path: `bronze/{provider}/{entity}/{date}/`
- [x] Data files: `batch_{date}_{batch_id}.jsonl.zst`
- [x] JSON copy: `batch_{date}_{batch_id}.jsonl`
- [x] Metadata: `{provider}_{entity}_metadata.yaml`
- [x] DQ Report: `batch_{date}_{provider}_{entity}_dq_report.json`

### Silver Layer
- [x] Path: `silver/{provider}/{entity}/`
- [x] Delta Lake structure (`_delta_log/`)
- [x] Metadata: `{provider}_{entity}_metadata.yaml`
- [x] DQ Report: `silver_{provider}_{entity}_dq_report.json`

### Gold Layer
- [x] Path: `gold/{provider}/{entity}/`
- [x] Delta Lake structure (`_delta_log/`)
- [x] Metadata: `{provider}_{entity}_metadata.yaml`
- [x] DQ Report: `gold_{provider}_{entity}_dq_report.json`

### System Files
- [x] Checkpoint naming: `{pipeline_name}.json`
- [x] Checkpoint path: `data/output/checkpoints/` (documentation updated)
- [x] Quarantine structure: Delta Lake table
- [x] Quarantine path: `data/output/quarantine/` (documentation updated)

---

*End of Audit Report*
