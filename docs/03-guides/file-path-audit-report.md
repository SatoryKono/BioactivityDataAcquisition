______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# BioETL File Path Audit Report

*Audit Date: 2026-01-21*
*Auditor: Claude Code*
*Reference Documentation: local-storage-layout.md, RULES.md §2.1*

______________________________________________________________________

## Executive Summary

This audit verifies that BioETL's file path patterns and naming conventions in the codebase
match the documented specifications in `local-storage-layout.md` and `RULES.md`.

**Overall Result: PASS (Discrepancies Fixed)**

| Layer       | Path Pattern | File Naming | Metadata | DQ Reports | Status   |
| ----------- | ------------ | ----------- | -------- | ---------- | -------- |
| Bronze      | ✅ Match     | ✅ Match    | ✅ Match | ✅ Match   | **PASS** |
| Silver      | ✅ Match     | ✅ Match    | ✅ Match | ✅ Match   | **PASS** |
| Gold        | ✅ Match     | ✅ Match    | ✅ Match | ✅ Match   | **PASS** |
| Checkpoints | ✅ Fixed     | ✅ Match    | N/A      | N/A        | **PASS** |
| Quarantine  | ✅ Fixed     | ✅ Match    | N/A      | N/A        | **PASS** |

______________________________________________________________________

## 1. Bronze Layer

### 1.1. Path Pattern

| Aspect      | Documented                                       | Implementation              | Status   |
| ----------- | ------------------------------------------------ | --------------------------- | -------- |
| Path        | `data/output/bronze/{provider}/{entity}/{date}/` | `bronze_writer.py:451-452`  | ✅ Match |
| Date format | `YYYY-MM-DD`                                     | `date.strftime("%Y-%m-%d")` | ✅ Match |

**Code Reference:**

```python
# bronze_writer.py:448-452
date - str = date.strftime("%Y-%m-%d")
relative - path = (
    f"{provider}/{entity}/{date-str}/batch-{date-str}-{batch-id}.jsonl.zst"
)
```

### 1.2. Data File Naming

| Aspect     | Documented                                | Implementation             | Status   |
| ---------- | ----------------------------------------- | -------------------------- | -------- |
| Compressed | `batch-{YYYY-MM-DD}-{batch-id}.jsonl.zst` | Same pattern               | ✅ Match |
| JSON copy  | `batch-{YYYY-MM-DD}-{batch-id}.jsonl`     | `bronze_writer.py:652-653` | ✅ Match |

### 1.3. Sidecar Files

| File Type | Documented                                        | Implementation             | Status   |
| --------- | ------------------------------------------------- | -------------------------- | -------- |
| Metadata  | `{provider}-{entity}-metadata.yaml`               | `metadata_writer.py:45-47` | ✅ Match |
| DQ Report | `batch-{date}-{provider}-{entity}-dq-report.json` | `dq_report_writer.py:89`   | ✅ Match |

______________________________________________________________________

## 2. Silver Layer

### 2.1. Path Pattern

| Aspect    | Documented                                | Implementation                      | Status   |
| --------- | ----------------------------------------- | ----------------------------------- | -------- |
| Path      | `data/output/silver/{provider}/{entity}/` | `Settings.silver-path` + table-name | ✅ Match |
| Structure | Delta Lake with `_delta_log/`             | `write-deltalake()` creates this    | ✅ Match |

**Code Reference:**

```python
# -base.py:345-347
@property
def silver-path(self) -> Path:
    return self.data-dir / "output" / "silver"
```

### 2.2. Sidecar Files

| File Type | Documented                                  | Implementation             | Status   |
| --------- | ------------------------------------------- | -------------------------- | -------- |
| Metadata  | `{provider}-{entity}-metadata.yaml`         | `metadata_writer.py:45-47` | ✅ Match |
| DQ Report | `silver-{provider}-{entity}-dq-report.json` | `dq_report_writer.py:129`  | ✅ Match |

______________________________________________________________________

## 3. Gold Layer

### 3.1. Path Pattern

| Aspect    | Documented                              | Implementation                    | Status   |
| --------- | --------------------------------------- | --------------------------------- | -------- |
| Path      | `data/output/gold/{provider}/{entity}/` | `Settings.gold-path` + table-name | ✅ Match |
| Structure | Delta Lake with `_delta_log/`           | `write-deltalake()` creates this  | ✅ Match |

**Code Reference:**

```python
# -base.py:349-352
@property
def gold-path(self) -> Path:
    return self.data-dir / "output" / "gold"
```

### 3.2. Sidecar Files

| File Type | Documented                                | Implementation             | Status   |
| --------- | ----------------------------------------- | -------------------------- | -------- |
| Metadata  | `{provider}-{entity}-metadata.yaml`       | `metadata_writer.py:45-47` | ✅ Match |
| DQ Report | `gold-{provider}-{entity}-dq-report.json` | `dq_report_writer.py:129`  | ✅ Match |

______________________________________________________________________

## 4. Checkpoints ✅

### 4.1. Path Pattern (Fixed)

| Aspect      | Documented                       | Implementation             | Status   |
| ----------- | -------------------------------- | -------------------------- | -------- |
| Path        | `data/output/checkpoints/`       | `data/output/checkpoints/` | ✅ Match |
| File naming | `{pipeline-name}.json`           | `local_checkpoint.py:187`  | ✅ Match |
| Composite   | `composite-{name}-{run-id}.json` | Documented only            | ℹ️ Info  |

**Code (`-base.py:354-357`):**

```python
@property
def checkpoint-path(self) -> Path:
    return self.data-dir / "output" / "checkpoints"
```

**Resolution:** Documentation updated to match code. All checkpoints are correctly placed inside `data/output/` per ADR-025.

______________________________________________________________________

## 5. Quarantine ✅

### 5.1. Path Pattern (Fixed)

| Aspect     | Documented                                  | Implementation                      | Status   |
| ---------- | ------------------------------------------- | ----------------------------------- | -------- |
| Path       | `data/output/quarantine/common.quarantine/` | `data/output/quarantine/`           | ✅ Match |
| Table name | `common.quarantine`                         | `base-path` passed directly         | ✅ Match |
| Structure  | Delta Lake                                  | `unified.py` uses `write-deltalake` | ✅ Match |

**Code (`-base.py:359-362`):**

```python
@property
def quarantine-path(self) -> Path:
    return self.data-dir / "output" / "quarantine"
```

**Resolution:** Documentation updated to match code. Quarantine is correctly placed inside `data/output/` per ADR-025.

______________________________________________________________________

## 6. CSV Export

### 6.1. Path Pattern

| Aspect      | Documented                               | Implementation        | Status   |
| ----------- | ---------------------------------------- | --------------------- | -------- |
| File naming | `{table-name}.csv`                       | `csv_exporter.py:270` | ✅ Match |
| Location    | Configured via `csv-export.path` in YAML | `storage_factory.py`  | ✅ Match |

______________________________________________________________________

## 7. Metadata Writer Filename Generation

**Verification of `-get-metadata-filename()` function:**

```python
# metadata_writer.py:34-47
def -get-metadata-filename(provider: str | None, entity: str | None) -> str:
    if provider and entity:
        return f"{provider}-{entity}-metadata.yaml"  # ✅ Matches docs
    return METADATA-FILENAME  # Fallback: "-metadata.yaml"
```

All layers correctly use this function for consistent metadata naming.

______________________________________________________________________

## 8. DQ Report Writer Filename Generation

**Verification of `-build-layer-filename()` function:**

```python
# dq_report_writer.py:106-133
def -build-layer-filename(...) -> str:
    if provider and entity:
        return f"{layer}-{provider}-{entity}-dq-report{extension}"  # ✅ Matches docs
    # ... fallback logic
```

### Bronze DQ Reports

```python
# dq_report_writer.py:88-89
if provider and entity and date - str:
    filename = (
        f"batch-{date-str}-{provider}-{entity}-dq-report{extension}"  # ✅ Matches docs
    )
```

______________________________________________________________________

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

______________________________________________________________________

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

______________________________________________________________________

## 11. Audit Checklist Summary

### Bronze Layer

- [x] Path: `bronze/{provider}/{entity}/{date}/`
- [x] Data files: `batch-{date}-{batch-id}.jsonl.zst`
- [x] JSON copy: `batch-{date}-{batch-id}.jsonl`
- [x] Metadata: `{provider}-{entity}-metadata.yaml`
- [x] DQ Report: `batch-{date}-{provider}-{entity}-dq-report.json`

### Silver Layer

- [x] Path: `silver/{provider}/{entity}/`
- [x] Delta Lake structure (`_delta_log/`)
- [x] Metadata: `{provider}-{entity}-metadata.yaml`
- [x] DQ Report: `silver-{provider}-{entity}-dq-report.json`

### Gold Layer

- [x] Path: `gold/{provider}/{entity}/`
- [x] Delta Lake structure (`_delta_log/`)
- [x] Metadata: `{provider}-{entity}-metadata.yaml`
- [x] DQ Report: `gold-{provider}-{entity}-dq-report.json`

### System Files

- [x] Checkpoint naming: `{pipeline-name}.json`
- [x] Checkpoint path: `data/output/checkpoints/` (documentation updated)
- [x] Quarantine structure: Delta Lake table
- [x] Quarantine path: `data/output/quarantine/` (documentation updated)

______________________________________________________________________

*End of Audit Report*
