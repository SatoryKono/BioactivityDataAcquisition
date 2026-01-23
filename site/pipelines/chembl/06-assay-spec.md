# ChEMBL Assay Pipeline Specification

*Version 1.1.0 | Aligned with RULES.md v5.12*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `chembl_assay` |
| **Provider** | ChEMBL (EBI) |
| **Entity** | assay |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/assay` |
| **Library** | `chembl_webresource_client` |
| **Rate Limit** | None (polite usage recommended) |
| **Health Check** | `/chembl/api/data/status.json` |
| **Auth Type** | None (public API) |

---

## 2. Business Context

### 2.1. Entity Purpose

Assays represent **experimental protocols** used to measure bioactivity:

- **Experimental methods**: Binding assays, functional assays, ADMET tests
- **Target context**: Links experiments to biological targets
- **Data provenance**: Source publications and curators
- **Quality metadata**: Confidence scores and relationship types

### 2.2. Use Cases

1. **Protocol Analysis**: Understand experimental conditions for activities
2. **Assay Selection**: Choose appropriate assays for screening
3. **Data Quality Assessment**: Filter by confidence and relationship type
4. **Cell-based vs Biochemical**: Compare assay types

### 2.3. Entity Relationships

```
assay
    │
    ├──FK──► target.target_chembl_id (M:1, optional)
    │
    ├──FK──► document.document_chembl_id (M:1, optional)
    │
    ├──FK──► cell_line.cell_chembl_id (M:1, optional)
    │
    ├──◄──FK──activity.assay_chembl_id (1:M)
    │
    └──◄──FK──assay_parameters (1:M)
```

### 2.4. Load Strategy

| Parameter | Value |
|-----------|-------|
| **Strategy** | `incremental` with input filter |
| **Estimated Volume** | ~1.5M records total |
| **Batch Size** | 20 (filter batch) |

---

## 3. Extraction (Bronze Layer)

### 3.1. Complete API Fields

| # | API Field | JSON Type | Nullable | Description |
|---|-----------|-----------|----------|-------------|
| 1 | `assay_chembl_id` | string | No | Primary key |
| 2 | `description` | string | Yes | Assay description |
| 3 | `assay_type` | string | Yes | B/F/A/T/P/U |
| 4 | `assay_test_type` | string | Yes | In vivo/vitro/ex vivo |
| 5 | `assay_category` | string | Yes | screening/confirmatory/... |
| 6 | `assay_organism` | string | Yes | Organism |
| 7 | `assay_tax_id` | integer | Yes | NCBI Taxonomy ID |
| 8 | `assay_strain` | string | Yes | Strain |
| 9 | `assay_tissue` | string | Yes | Tissue |
| 10 | `assay_cell_type` | string | Yes | Cell type |
| 11 | `assay_subcellular_fraction` | string | Yes | Subcellular fraction |
| 12 | `target_chembl_id` | string | Yes | FK to target |
| 13 | `relationship_type` | string | Yes | D/H/M/N/S/U |
| 14 | `relationship_description` | string | Yes | Relationship desc |
| 15 | `confidence_score` | integer | Yes | 0-9 score |
| 16 | `confidence_description` | string | Yes | Confidence desc |
| 17 | `src_id` | integer | Yes | Source ID |
| 18 | `src_assay_id` | string | Yes | Source assay ID |
| 19 | `document_chembl_id` | string | Yes | FK to document |
| 20 | `cell_chembl_id` | string | Yes | FK to cell_line |
| 21 | `tissue_chembl_id` | string | Yes | FK to tissue |
| 22 | `bao_format` | string | Yes | BAO format ID |
| 23 | `bao_label` | string | Yes | BAO label |
| 24 | `assay_classifications` | array | Yes | Classifications |
| 25 | `assay_parameters` | array | Yes | Parameters |
| 26 | `variant_sequence` | object | Yes | Variant info |

---

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter | Value |
|-----------|-------|
| **Entity ID Field** | `assay_chembl_id` |
| **ID Source** | `from_api` |
| **Format** | ChEMBL ID (CHEMBL[0-9]+) |

### 4.2. Flattening Strategy

| Nested Path | Flattened Name | Strategy |
|-------------|----------------|----------|
| `variant_sequence.accession` | `variant_accession` | Extract scalar |
| `variant_sequence.mutation` | `variant_mutation` | Extract scalar |
| `variant_sequence.organism` | `variant_organism` | Extract scalar |
| `variant_sequence.tax_id` | `variant_tax_id` | Extract scalar |
| `variant_sequence.sequence` | `variant_sequence` | Extract scalar |
| `assay_classifications` | `assay_classifications` | JSON string |
| `assay_parameters` | `assay_parameters` | JSON string |

---

## 5. Validation

### 5.1. Pandera Schema

```python
class AssaySchema(ETLRecordSchema):
    """Assay validation schema for Silver layer."""

    # === Primary Key ===
    assay_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
    )

    # === Description & Classification ===
    description: Series[str] | None = pa.Field(nullable=True)
    assay_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["B", "F", "A", "T", "P", "U"],
    )
    assay_test_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["In vivo", "In vitro", "Ex vivo"],
    )
    assay_category: Series[str] | None = pa.Field(
        nullable=True,
        isin=["screening", "confirmatory", "panel", "summary", "other"],
    )

    # === Biological Context ===
    assay_organism: Series[str] | None = pa.Field(nullable=True)
    assay_tax_id: Series[int] | None = pa.Field(nullable=True)
    assay_strain: Series[str] | None = pa.Field(nullable=True)
    assay_tissue: Series[str] | None = pa.Field(nullable=True)
    assay_cell_type: Series[str] | None = pa.Field(nullable=True)

    # === Target & Relationship ===
    target_chembl_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
    )
    relationship_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["D", "H", "M", "N", "S", "U"],
    )
    confidence_score: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        le=9,
    )

    # === Foreign Keys ===
    document_chembl_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
    )
    cell_chembl_id: Series[str] | None = pa.Field(nullable=True)
    tissue_chembl_id: Series[str] | None = pa.Field(nullable=True)

    # === Ontologies ===
    bao_format: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^BAO:\d+$",
    )
    bao_label: Series[str] | None = pa.Field(nullable=True)

    # === Variant Information ===
    variant_accession: Series[str] | None = pa.Field(nullable=True)
    variant_mutation: Series[str] | None = pa.Field(nullable=True)
    variant_organism: Series[str] | None = pa.Field(nullable=True)
    variant_tax_id: Series[int] | None = pa.Field(nullable=True)

    # === Complex Fields ===
    assay_classifications: Series[str] | None = pa.Field(nullable=True)
    assay_parameters: Series[str] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### 5.2. Field Validation Matrix

| Field | Type | Nullable | Constraints | DQ Level |
|-------|------|----------|-------------|----------|
| `assay_chembl_id` | str | No | regex `^CHEMBL\d+$` | CRITICAL |
| `assay_type` | str | Yes | isin [B,F,A,T,P,U] | WARNING |
| `confidence_score` | int | Yes | [0, 9] | WARNING |
| `target_chembl_id` | str | Yes | regex `^CHEMBL\d+$` | INFO |

---

## 6. Pipeline Configuration

```yaml
pipeline_name: chembl_assay
provider: chembl
entity_type: assay
version: "1.1.0"

primary_keys: ["assay_chembl_id"]
silver_table: "chembl_assay"
gold_table: "chembl_assay"

gold_filters:
  required_fields:
    - description
  columns:
    confidence_score: [7, 8, 9]  # High confidence only

input_filter:
  enabled: true
  source_path: "data/input/assay.csv"
  column_name: "assay_chembl_id"
  filter_field: "assay_chembl_id"
  batch_size: 20
```

---

## 7. Dependencies

### 7.1. Upstream

| Dependency | Type | Required |
|------------|------|----------|
| ChEMBL API | API | Yes |
| `chembl_target` | Pipeline | Recommended |

### 7.2. Downstream

| Consumer | Impact |
|----------|--------|
| `chembl_activity` | FK reference |
| `chembl_assay_parameters` | FK reference |
| Protocol analysis | Assay type statistics |
