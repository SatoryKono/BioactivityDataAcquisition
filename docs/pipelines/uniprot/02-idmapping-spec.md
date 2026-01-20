# UniProt ID Mapping Pipeline Specification

*Version 1.1.0 | Aligned with RULES.md v5.11*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `uniprot_idmapping` |
| **Provider** | UniProt (EBI/SIB/PIR) |
| **Entity** | idmapping |
| **API Endpoint** | `https://rest.uniprot.org/idmapping/` |
| **Library** | `httpx` (async) |
| **Rate Limit** | 100 req/sec |
| **Health Check** | Submit test job |
| **Auth Type** | None (public API) |

---

## 2. Business Context

### 2.1. Entity Purpose

ID Mapping enables **cross-database identifier translation**:

- **ChEMBL → UniProt**: Map ChEMBL target IDs to UniProt accessions
- **Gene → Protein**: Map gene names to protein accessions
- **External DBs**: Map to/from EMBL, RefSeq, PDB, etc.
- **Batch processing**: Efficient bulk mapping

### 2.2. Use Cases

1. **Target Integration**: Link ChEMBL targets to UniProt annotations
2. **ID Harmonization**: Standardize identifiers across databases
3. **Enrichment Pipelines**: Fetch UniProt data for ChEMBL targets
4. **Cross-Provider Linking**: Build unified identifier mappings

### 2.3. Supported Mapping Types

| From Database | To Database | Use Case |
|---------------|-------------|----------|
| ChEMBL | UniProtKB | Target enrichment |
| UniProtKB_AC-ID | PDB | Structure data |
| UniProtKB_AC-ID | RefSeq_Protein | Sequence data |
| Gene_Name | UniProtKB | Gene-based search |
| EMBL | UniProtKB | Sequence→Protein |

---

## 3. Extraction (Bronze Layer)

### 3.1. API Request Flow

```python
import httpx

# Step 1: Submit mapping job
submit_url = "https://rest.uniprot.org/idmapping/run"
job_response = await client.post(submit_url, data={
    "from": "ChEMBL",
    "to": "UniProtKB",
    "ids": ",".join(chembl_target_ids)  # Max 100,000 IDs
})
job_id = job_response.json()["jobId"]

# Step 2: Poll for results
status_url = f"https://rest.uniprot.org/idmapping/status/{job_id}"
while True:
    status = await client.get(status_url)
    if status.json().get("results"):
        break
    await asyncio.sleep(1)

# Step 3: Fetch results with pagination
results_url = f"https://rest.uniprot.org/idmapping/results/{job_id}"
results = await client.get(results_url)
```

### 3.2. Response Fields

| # | Field | JSON Type | Nullable | Description |
|---|-------|-----------|----------|-------------|
| 1 | `from` | string | No | Source ID |
| 2 | `to` | object | Yes | Mapped UniProt entry (full) |
| 3 | `to.primaryAccession` | string | Yes | UniProt accession |
| 4 | `to.uniProtkbId` | string | Yes | Entry name |
| 5 | `to.organism.taxonId` | int | Yes | Taxonomy ID |

### 3.3. Special Cases

| Case | Response | Handling |
|------|----------|----------|
| ID found | Full UniProt entry | Extract accession |
| ID not found | Empty results | Set `mapping_status = "not_found"` |
| Multiple matches | Array of entries | Store as JSON array |
| Obsolete ID | May have redirect | Follow redirect |

---

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter | Value |
|-----------|-------|
| **Entity ID Field** | `target_chembl_id` (input ID) |
| **ID Source** | `from_input` |
| **Format** | ChEMBL ID (CHEMBL[0-9]+) |

### 4.2. Output Fields

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `target_chembl_id` | str | Input | Source ChEMBL ID |
| `uniprot_accession` | str | API | Mapped UniProt accession |
| `uniprot_entry_name` | str | API | Entry name |
| `mapping_status` | str | Derived | found/not_found/multiple |
| `uniprot_organism` | str | API | Organism name |
| `uniprot_tax_id` | int | API | Taxonomy ID |
| `all_mappings` | str | API | JSON array if multiple |

### 4.3. Content Hash Specification

```python
# Fields included in hash
hash_fields = [
    "target_chembl_id",
    "uniprot_accession",
    "mapping_status",
]

# Algorithm
content_hash = sha256(f"uniprot{canonical_json(filtered_record)}")
```

---

## 5. Validation

### 5.1. Schema

```python
class UniprotIdMappingSchema(ETLRecordSchema):
    """UniProt ID Mapping validation schema for Silver layer."""

    # === Primary Key (Input ID) ===
    target_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="Source ChEMBL target ID",
    )

    # === Mapping Result ===
    uniprot_accession: Series[str] | None = pa.Field(
        nullable=True,
        description="Mapped UniProt accession (null if not_found)",
    )
    uniprot_entry_name: Series[str] | None = pa.Field(
        nullable=True,
        description="UniProt entry name",
    )
    mapping_status: Series[str] = pa.Field(
        nullable=False,
        isin=["found", "not_found", "multiple", "error"],
        description="Mapping result status",
    )

    # === Additional Metadata ===
    uniprot_organism: Series[str] | None = pa.Field(nullable=True)
    uniprot_tax_id: Series[int] | None = pa.Field(nullable=True, ge=1)
    all_mappings: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array for multiple mappings",
    )

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### 5.2. DQ Thresholds

| Threshold | Value | Action |
|-----------|-------|--------|
| Soft | 30% not_found | Warning, continue |
| Hard | 80% not_found | Fail batch |

**Note:** Higher thresholds because many ChEMBL targets may not have UniProt mappings (organism targets, cell lines, etc.)

---

## 6. Output Schemas

### 6.1. Bronze

**Note:** ID Mapping doesn't write Bronze (data comes from API, not raw files).

### 6.2. Silver

```
Path: silver/uniprot/idmapping/
Format: Delta Lake (delta-rs)
Mode: Merge on [target_chembl_id]
Partition: None
Retention: Permanent
```

### 6.3. Gold

```
Path: gold/uniprot/idmapping/
Format: Delta Lake
Mode: Overwrite
```

**Gold Filter:** All records pass (including not_found for tracking)

---

## 7. Pipeline Configuration

```yaml
# configs/pipelines/uniprot/idmapping.yaml

pipeline_name: uniprot_idmapping
provider: uniprot
entity_type: idmapping
version: "1.1.0"
description: "Maps ChEMBL target IDs to UniProt accessions"

primary_keys: ["target_chembl_id"]
silver_table: "uniprot_idmapping"
gold_table: "uniprot_idmapping"

source:
  type: file
  load_strategy: full
  input_path: data/input/target.csv
  api:
    base_url: https://rest.uniprot.org
    from_db: ChEMBL
    to_db: UniProtKB

dq_rules:
  soft_fail_threshold: 0.30  # 30% not_found acceptable
  hard_fail_threshold: 0.80  # 80% not_found triggers failure

sink:
  bronze:
    enabled: false  # No Bronze for ID mapping
  silver:
    path: "data/output/silver"
    primary_key: ["target_chembl_id"]
    partition_by: []
  gold:
    path: "data/output/gold"

gold_filters:
  required_fields:
    - target_chembl_id
    - mapping_status

input_filter:
  enabled: false  # Input CSV IS the source
```

---

## 8. Dependencies

### 8.1. Upstream

| Dependency | Type | Required |
|------------|------|----------|
| UniProt ID Mapping API | API | Yes |
| Input CSV with ChEMBL IDs | File | Yes |

### 8.2. Downstream

| Consumer | Impact |
|----------|--------|
| `uniprot_protein` | Provides accessions for protein fetch |
| Target enrichment | Enables ChEMBL→UniProt linking |
| Cross-provider analytics | ID harmonization |

---

## 9. Error Handling

### 9.1. API Errors

| Error | Handling |
|-------|----------|
| 400 Bad Request | Log, retry with smaller batch |
| 429 Too Many Requests | Exponential backoff |
| 500 Server Error | Retry up to 3 times |
| Job timeout | Retry with smaller batch |

### 9.2. Mapping Failures

| Scenario | `mapping_status` | Notes |
|----------|------------------|-------|
| ID found | `found` | Normal case |
| ID not in DB | `not_found` | Expected for non-protein targets |
| Multiple matches | `multiple` | Store all in `all_mappings` |
| API error | `error` | Retry or quarantine |
