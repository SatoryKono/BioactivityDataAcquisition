# UniProt ID Mapping Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.22*

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
| UniProtKB-AC-ID | PDB | Structure data |
| UniProtKB-AC-ID | RefSeq-Protein | Sequence data |
| Gene-Name | UniProtKB | Gene-based search |
| EMBL | UniProtKB | Sequence→Protein |

---

## 3. Extraction (Bronze Layer)

### 3.1. API Request Flow

```python
import httpx

# Step 1: Submit mapping job
submit-url = "https://rest.uniprot.org/idmapping/run"
job-response = await client.post(submit-url, data={
    "from": "ChEMBL",
    "to": "UniProtKB",
    "ids": ",".join(chembl_target-ids)  # Max 100,000 IDs
})
job-id = job-response.json()["jobId"]

# Step 2: Poll for results
status-url = f"https://rest.uniprot.org/idmapping/status/{job-id}"
while True:
    status = await client.get(status-url)
    if status.json().get("results"):
        break
    await asyncio.sleep(1)

# Step 3: Fetch results with pagination
results-url = f"https://rest.uniprot.org/idmapping/results/{job-id}"
results = await client.get(results-url)
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
| ID not found | Empty results | Set `mapping-status = "not-found"` |
| Multiple matches | Array of entries | Store as JSON array |
| Obsolete ID | May have redirect | Follow redirect |

---

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter | Value |
|-----------|-------|
| **Entity ID Field** | `target-id` (input ChEMBL target ID) |
| **ID Source** | `from-input` |
| **Format** | ChEMBL ID (CHEMBL[0-9]+) |

### 4.2. Output Fields

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `target-id` | str | Input | Source ChEMBL target ID |
| `uniprot-accession` | str | API | Mapped UniProt accession |
| `uniprot-entry-name` | str | API | Entry name |
| `mapping-status` | str | Derived | found/not-found/multiple/error |
| `organism-scientific` | str | API | Scientific organism name |
| `organism-common` | str | API | Common organism name |
| `taxonomy-id` | int | API | NCBI Taxonomy ID |
| `protein-name` | str | API | Recommended protein name |
| `gene-primary` | str | API | Primary gene name |
| `sequence-length` | int | API | Protein sequence length |
| `sequence-mass` | int | API | Molecular weight in Daltons |
| `reviewed` | bool | API | True if Swiss-Prot (reviewed) |
| `annotation-score` | int | API | Quality score 1-5 |
| `all-mappings` | str | API | JSON array if multiple |

### 4.3. Content Hash Specification

```python
# Fields included in hash
hash-fields = [
    "target-id",
    "uniprot-accession",
    "mapping-status",
]

# Algorithm
content-hash = sha256(f"uniprot{canonical-json(filtered-record)}")
```

---

## 5. Validation

### 5.1. Schema

```python
class UniprotIdMappingSchema(ETLRecordSchema):
    """UniProt ID Mapping validation schema for Silver layer."""

    # === Primary Key (Input ID) ===
    target-id: Series[str] = pa.Field(
        nullable=False,
        str-matches=r"^CHEMBL\d+$",
        description="Source ChEMBL target ID",
    )

    # === Mapping Result ===
    uniprot-accession: Series[str] | None = pa.Field(
        nullable=True,
        description="Mapped UniProt accession (null if not-found)",
    )
    uniprot-entry-name: Series[str] | None = pa.Field(
        nullable=True,
        description="UniProt entry name",
    )
    mapping-status: Series[str] = pa.Field(
        nullable=False,
        isin=["found", "not-found", "multiple", "error"],
        description="Mapping result status",
    )

    # === Organism & Taxonomy ===
    organism-scientific: Series[str] | None = pa.Field(
        nullable=True,
        description="Scientific organism name",
    )
    organism-common: Series[str] | None = pa.Field(
        nullable=True,
        description="Common organism name",
    )
    taxonomy-id: Series[int] | None = pa.Field(nullable=True, ge=1)

    # === Protein Metadata ===
    protein-name: Series[str] | None = pa.Field(
        nullable=True,
        description="Recommended protein name",
    )
    gene-primary: Series[str] | None = pa.Field(
        nullable=True,
        description="Primary gene name",
    )
    sequence-length: Series[int] | None = pa.Field(nullable=True, ge=1)
    sequence-mass: Series[int] | None = pa.Field(nullable=True, ge=1)
    reviewed: Series[bool] | None = pa.Field(
        nullable=True,
        description="True if Swiss-Prot (reviewed)",
    )
    annotation-score: Series[int] | None = pa.Field(
        nullable=True, ge=1, le=5,
        description="Quality score 1-5",
    )

    # === Multiple Mappings ===
    all-mappings: Series[str] | None = pa.Field(
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
| Soft | 30% not-found | Warning, continue |
| Hard | 80% not-found | Fail batch |

**Note:** Higher thresholds because many ChEMBL targets may not have UniProt mappings (organism targets, cell lines, etc.)

---

## 6. Output Schemas

### 6.1. Bronze

**Note:** ID Mapping doesn't write Bronze (data comes from API, not raw files).

### 6.2. Silver

```
Path: silver/uniprot/idmapping/
Format: Delta Lake (delta-rs)
Mode: Merge on [target-id]
Partition: None
Retention: Permanent
```

### 6.3. Gold

```
Path: gold/uniprot/idmapping/
Format: Delta Lake
Mode: Overwrite
```

**Gold Filter:** All records pass (including not-found for tracking)

---

## 7. Pipeline Configuration

```yaml
# configs/entities/uniprot/idmapping.yaml

pipeline-name: uniprot_idmapping
provider: uniprot
entity-type: idmapping
version: "1.1.0"
description: "Maps ChEMBL target IDs to UniProt accessions via UniProt ID Mapping API"

primary-keys: ["target-id"]
silver-table: "uniprot_idmapping"
gold-table: "uniprot_idmapping"

source:
  type: file
  load-strategy: full
  input-path: data/input/target.csv
  api:
    base-url: https://rest.uniprot.org
    from-db: ChEMBL
    to-db: UniProtKB

dq-overrides:
  soft-fail-threshold: 0.30  # 30% not-found acceptable
  hard-fail-threshold: 0.80  # 80% not-found triggers failure

sink:
  bronze:
    enabled: false  # No Bronze for ID mapping
  silver:
    path: "data/output/silver"
    primary-key: ["target-id"]
    partition-by: []
  gold:
    path: "data/output/gold"

gold-filters:
  required-fields:
    - target-id
    - mapping-status

input-filter:
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

| Scenario | `mapping-status` | Notes |
|----------|------------------|-------|
| ID found | `found` | Normal case |
| ID not in DB | `not-found` | Expected for non-protein targets |
| Multiple matches | `multiple` | Store all in `all-mappings` |
| API error | `error` | Retry or quarantine |
