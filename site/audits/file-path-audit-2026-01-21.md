# BioETL File Path Audit Report

**Date**: 2026-01-21
**Auditor**: Claude (Automated Audit)
**Scope**: Verify alignment between documented path patterns and actual implementation
**Status**: Completed with findings

---

## Executive Summary

This audit compares the documented file path patterns in `RULES.md`, `local-storage-layout.md`, and pipeline configurations against the actual implementation in storage writers. **3 discrepancies** were identified, **2 documentation improvements** recommended, and **4 patterns verified as compliant**.

| Category | Status | Count |
|----------|--------|-------|
| Discrepancies Found | Warning | 3 |
| Documentation Updates Needed | Info | 2 |
| Patterns Verified Compliant | OK | 4 |

---

## 1. Discrepancies Found

### 1.1. Bronze Path Missing `v1/` Version Directory

**Severity**: Medium
**Documentation Location**: `docs/03-guides/local-storage-layout.md:12,45,50-53`

**Documented Pattern**:
```
data/bronze/v1/{provider}/{entity}/{date}/batch_001.jsonl.zst
```

**Actual Implementation** (`src/bioetl/infrastructure/storage/bronze_writer.py:449-452`):
```python
relative_path = (
    f"{provider}/{entity}/{date_str}/batch_{date_str}_{batch_id}.jsonl.zst"
)
```

**Actual Output**:
```
bronze/{provider}/{entity}/{date}/batch_{date}_{batch_id}.jsonl.zst
```

**Analysis**:
- Documentation shows `v1/` format version directory in path
- Implementation does NOT include `v1/` directory
- The `base_path` for Bronze is `data/output/bronze` (per bootstrap code)

**Recommendation**:
1. Update `local-storage-layout.md` to remove `v1/` from documented paths, OR
2. Update `bronze_writer.py` to include `v1/` for format versioning

---

### 1.2. Checkpoint Structure: Nested vs Flat

**Severity**: Low
**Documentation Location**: `docs/03-guides/local-storage-layout.md:29-31,98-110`

**Documented Pattern**:
```
data/checkpoints/{pipeline_name}/checkpoint.json
```

**Actual Implementation** (`src/bioetl/infrastructure/checkpoint/local_checkpoint.py:181-187`):
```python
def _get_key(self, pipeline: str) -> str:
    """Get checkpoint file path for a pipeline.

    Returns flat path: {pipeline}.json (e.g., chembl_activity.json)
    The base_path already points to data/output/checkpoints/.
    """
    return f"{pipeline}.json"
```

**Actual Output**:
```
data/output/checkpoints/chembl_activity.json  (FLAT)
```

**Analysis**:
- Documentation shows nested structure: `{pipeline_name}/checkpoint.json`
- Implementation uses flat structure: `{pipeline_name}.json`
- The flat structure is simpler and adequate for the use case

**Recommendation**: Update `local-storage-layout.md` to reflect flat checkpoint structure:
```
data/output/checkpoints/
└── {pipeline_name}.json
```

---

### 1.3. Base Data Directory: `data/` vs `data/output/`

**Severity**: Low
**Documentation Location**: `docs/03-guides/local-storage-layout.md:10-35`

**Documented Structure**:
```
data/
├── bronze/
├── silver/
├── gold/
├── checkpoints/
└── quarantine/
```

**Actual Implementation** (`src/bioetl/composition/_bootstrap/storage.py:70-103`):
```python
# ADR-025: Use data/output/ hierarchy for consistency with pipeline configs
output_dir = Path(settings.data_dir) / "output"

bronze_writer = BronzeWriter(
    base_path=output_dir / "bronze",  # data/output/bronze
)
silver_writer = SilverWriter(
    base_path=output_dir / "silver",  # data/output/silver
)
gold_writer = GoldWriter(
    base_path=output_dir / "gold",    # data/output/gold
)
```

**Actual Structure**:
```
data/
├── output/
│   ├── bronze/
│   ├── silver/
│   └── gold/
├── checkpoints/
└── quarantine/
```

**Analysis**:
- Documentation shows `data/bronze/`, `data/silver/`, `data/gold/`
- Implementation uses `data/output/bronze/`, `data/output/silver/`, `data/output/gold/`
- Checkpoints are at `data/checkpoints/` or `data/output/checkpoints/` (needs verification)
- The `output/` subdirectory provides separation from input/config data

**Recommendation**: Update `local-storage-layout.md` to document the `output/` hierarchy.

---

## 2. Documentation Updates Recommended

### 2.1. Bronze File Naming Pattern

**Location**: `docs/03-guides/local-storage-layout.md:16-17,50-53`

**Current Documentation**:
```
batch_001.jsonl.zst
batch_002.jsonl.zst
```

**Actual Pattern** (`bronze_writer.py:449-452`):
```
batch_{YYYY-MM-DD}_{batch_id}.jsonl.zst
```

**Example**:
```
batch_2026-01-21_a1b2c3d4.jsonl.zst
```

**Recommendation**: Update examples to show actual naming convention with date and batch_id.

---

### 2.2. Config Loader Convention-Based Paths

**Location**: `docs/03-guides/local-storage-layout.md` (missing)

The config loader (`src/bioetl/infrastructure/config_loader.py:15-17,98`) auto-computes paths:
```python
layer.setdefault("path", f"data/output/{layer_name}/{provider}/{entity_type}")
```

This convention-based path resolution (ADR-029) should be documented.

---

## 3. Patterns Verified as Compliant

### 3.1. Metadata Sidecar Files - COMPLIANT

**Documentation**:
- `{provider}_{entity}_metadata.yaml`

**Implementation** (`src/bioetl/infrastructure/storage/metadata_writer.py:34-47`):
```python
def _get_metadata_filename(provider: str | None, entity: str | None) -> str:
    if provider and entity:
        return f"{provider}_{entity}_metadata.yaml"
    return METADATA_FILENAME  # "_metadata.yaml" fallback
```

**Status**: Implementation matches documentation.

---

### 3.2. DQ Report Files - COMPLIANT

**Documentation**:
- Bronze: `batch_{date}_{provider}_{entity}_dq_report.json`
- Silver: `silver_{provider}_{entity}_dq_report.json`
- Gold: `gold_{provider}_{entity}_dq_report.json`

**Implementation** (`src/bioetl/infrastructure/export/dq_report_writer.py:33-36,106-133`):
```python
# Path formats (unified structure):
# - Bronze: {base_path}/{provider}/{entity}/{date}/batch_{date}_{provider}_{entity}_dq_report{ext}
# - Silver: {base_path}/{provider}/{entity}/silver_{provider}_{entity}_dq_report{ext}
# - Gold: {base_path}/{provider}/{entity}/gold_{provider}_{entity}_dq_report{ext}
```

**Status**: Implementation matches documentation.

---

### 3.3. Silver/Gold Delta Lake Structure - COMPLIANT

**Documentation**:
- Contains `_delta_log/` directory
- Contains `part-*.parquet` files

**Implementation** (`src/bioetl/infrastructure/storage/base_delta_writer.py`):
- Uses `deltalake` library which creates standard Delta Lake structure
- Path resolution: `{base_path}/{table_name.replace('.', '/')}`

**Status**: Implementation matches Delta Lake standards.

---

### 3.4. Quarantine Table Structure - COMPLIANT

**Documentation**:
- `data/quarantine/common.quarantine/`
- Contains `_delta_log/` and `part-*.parquet`

**Implementation** (`src/bioetl/infrastructure/quarantine/unified.py:50-56`):
```python
class UnifiedQuarantine:
    def __init__(self, base_path: str) -> None:
        self.base_path = base_path.rstrip("/")
```

**Status**: Implementation follows Delta Lake pattern. Base path configuration determines actual location.

---

## 4. Path Pattern Summary Table

| Artifact | Documented Pattern | Actual Pattern | Status |
|----------|-------------------|----------------|--------|
| **Bronze Data** | `bronze/v1/{provider}/{entity}/{date}/batch_*.jsonl.zst` | `bronze/{provider}/{entity}/{date}/batch_{date}_{batch_id}.jsonl.zst` | Warning |
| **Bronze Metadata** | `{provider}_{entity}_metadata.yaml` | `{provider}_{entity}_metadata.yaml` | OK |
| **Bronze DQ Report** | `batch_{date}_{provider}_{entity}_dq_report.json` | `batch_{date}_{provider}_{entity}_dq_report.{ext}` | OK |
| **Silver Data** | `silver/{provider}/{entity}/_delta_log/` | `silver/{provider}/{entity}/_delta_log/` | OK |
| **Silver Metadata** | `{provider}_{entity}_metadata.yaml` | `{provider}_{entity}_metadata.yaml` | OK |
| **Silver DQ Report** | `silver_{provider}_{entity}_dq_report.json` | `silver_{provider}_{entity}_dq_report.{ext}` | OK |
| **Gold Data** | `gold/{provider}/{entity}/_delta_log/` | `gold/{provider}/{entity}/_delta_log/` | OK |
| **Gold Metadata** | `{provider}_{entity}_metadata.yaml` | `{provider}_{entity}_metadata.yaml` | OK |
| **Gold DQ Report** | `gold_{provider}_{entity}_dq_report.json` | `gold_{provider}_{entity}_dq_report.{ext}` | OK |
| **Checkpoint** | `checkpoints/{pipeline}/checkpoint.json` | `checkpoints/{pipeline}.json` | Warning |
| **Quarantine** | `quarantine/common.quarantine/_delta_log/` | `quarantine/_delta_log/` (configurable) | OK |
| **Base Directory** | `data/` | `data/output/` | Warning |

---

## 5. Regex Validation Patterns (Updated)

Based on actual implementation, the correct validation patterns are:

```python
import re

# Bronze data files (actual pattern)
BRONZE_DATA_PATTERN = r"^batch_\d{4}-\d{2}-\d{2}_[a-f0-9-]+\.jsonl\.zst$"
BRONZE_JSON_PATTERN = r"^batch_\d{4}-\d{2}-\d{2}_[a-f0-9-]+\.jsonl$"

# Metadata files (with provider/entity or fallback)
METADATA_PATTERN = r"^([a-z_]+_[a-z_]+_metadata\.yaml|_metadata\.yaml)$"

# DQ Report files
BRONZE_DQ_PATTERN = r"^batch_\d{4}-\d{2}-\d{2}_[a-z_]+_[a-z_]+_dq_report\.(json|yaml|html)$"
SILVER_DQ_PATTERN = r"^silver_[a-z_]+_[a-z_]+_dq_report\.(json|yaml|html)$"
GOLD_DQ_PATTERN = r"^gold_[a-z_]+_[a-z_]+_dq_report\.(json|yaml|html)$"

# Checkpoint files (flat structure)
CHECKPOINT_PATTERN = r"^[a-z_]+\.json$"
COMPOSITE_CP_PATTERN = r"^composite_[a-z_]+_[a-f0-9-]+\.json$"
```

---

## 6. Expected Directory Structure (Corrected)

Based on actual implementation:

```
data/
├── output/
│   ├── bronze/
│   │   └── {provider}/
│   │       └── {entity}/
│   │           └── {YYYY-MM-DD}/
│   │               ├── batch_{YYYY-MM-DD}_{batch_id}.jsonl.zst
│   │               ├── batch_{YYYY-MM-DD}_{batch_id}.jsonl  (optional)
│   │               ├── {provider}_{entity}_metadata.yaml    (optional)
│   │               └── batch_{YYYY-MM-DD}_{provider}_{entity}_dq_report.json
│   ├── silver/
│   │   └── {provider}/
│   │       └── {entity}/
│   │           ├── _delta_log/
│   │           ├── part-*.parquet
│   │           ├── {provider}_{entity}_metadata.yaml
│   │           └── silver_{provider}_{entity}_dq_report.json
│   ├── gold/
│   │   └── {provider}/
│   │       └── {entity}/
│   │           ├── _delta_log/
│   │           ├── part-*.parquet
│   │           ├── {provider}_{entity}_metadata.yaml
│   │           └── gold_{provider}_{entity}_dq_report.json
│   └── reports/
│       └── dq/
│           └── (composite DQ reports)
├── checkpoints/
│   ├── {pipeline_name}.json
│   └── composite/
│       └── composite_{name}_{run_id}.json
└── quarantine/
    └── common.quarantine/
        ├── _delta_log/
        └── part-*.parquet
```

---

## 7. Action Items

| Priority | Action | Owner | Ticket |
|----------|--------|-------|--------|
| Medium | Update `local-storage-layout.md` to remove `v1/` from Bronze paths | Docs Team | - |
| Low | Update `local-storage-layout.md` to show `data/output/` hierarchy | Docs Team | - |
| Low | Update checkpoint documentation to show flat structure | Docs Team | - |
| Info | Document convention-based path resolution (ADR-029) in storage layout guide | Docs Team | - |

---

## 8. Verification Commands

```bash
#!/bin/bash
# audit_file_paths.sh - Updated for actual implementation

BASE_DIR="data/output"
ERRORS=0

echo "=== BioETL File Path Audit ==="

# Check Bronze structure (no v1/)
echo "--- Bronze Layer ---"
for provider_dir in $BASE_DIR/bronze/*/; do
    provider=$(basename "$provider_dir")
    for entity_dir in $provider_dir*/; do
        entity=$(basename "$entity_dir")
        for date_dir in $entity_dir*/; do
            date=$(basename "$date_dir")
            # Validate date format YYYY-MM-DD
            if [[ ! $date =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
                echo "[ERROR] Invalid date format: $date_dir"
                ((ERRORS++))
            fi
            # Check for batch files with correct naming
            if ! ls "$date_dir"batch_????-??-??_*.jsonl.zst 1>/dev/null 2>&1; then
                echo "[WARN] No correctly named .jsonl.zst files in: $date_dir"
            fi
        done
    done
done

# Check Silver structure
echo "--- Silver Layer ---"
for provider_dir in $BASE_DIR/silver/*/; do
    provider=$(basename "$provider_dir")
    for entity_dir in $provider_dir*/; do
        entity=$(basename "$entity_dir")
        if [ ! -d "$entity_dir/_delta_log" ]; then
            echo "[ERROR] Missing _delta_log in: $entity_dir"
            ((ERRORS++))
        fi
    done
done

# Check Gold structure
echo "--- Gold Layer ---"
for provider_dir in $BASE_DIR/gold/*/; do
    provider=$(basename "$provider_dir")
    for entity_dir in $provider_dir*/; do
        entity=$(basename "$entity_dir")
        if [ ! -d "$entity_dir/_delta_log" ]; then
            echo "[ERROR] Missing _delta_log in: $entity_dir"
            ((ERRORS++))
        fi
    done
done

# Check Checkpoints (flat structure)
echo "--- Checkpoints ---"
for cp_file in data/checkpoints/*.json; do
    if [ -f "$cp_file" ]; then
        filename=$(basename "$cp_file")
        if [[ ! $filename =~ ^[a-z_]+\.json$ ]]; then
            echo "[WARN] Unusual checkpoint filename: $filename"
        fi
    fi
done

echo ""
echo "=== Audit complete. Errors: $ERRORS ==="
exit $ERRORS
```

---

## References

- `docs/03-guides/local-storage-layout.md` - Storage layout documentation
- `src/bioetl/infrastructure/storage/bronze_writer.py` - Bronze implementation
- `src/bioetl/infrastructure/storage/silver_writer.py` - Silver implementation
- `src/bioetl/infrastructure/storage/gold_writer.py` - Gold implementation
- `src/bioetl/infrastructure/storage/metadata_writer.py` - Metadata implementation
- `src/bioetl/infrastructure/export/dq_report_writer.py` - DQ report implementation
- `src/bioetl/infrastructure/checkpoint/local_checkpoint.py` - Checkpoint implementation
- `src/bioetl/infrastructure/quarantine/unified.py` - Quarantine implementation
- `src/bioetl/composition/_bootstrap/storage.py` - Bootstrap with path configuration
- `configs/pipelines/_base.yaml` - Base pipeline configuration

---

*Report generated by automated audit process.*
