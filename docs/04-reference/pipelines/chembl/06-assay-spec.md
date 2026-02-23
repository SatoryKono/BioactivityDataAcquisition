# ChEMBL Assay Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.21*

----------------------------------------------------------------------

## 1. Identification

| Parameter        | Value                                         |
| ---------------- | --------------------------------------------- |
| **Pipeline ID**  | `chembl_assay`                                |
| **Provider**     | ChEMBL (EBI)                                  |
| **Entity**       | assay                                         |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/assay` |
| **Library**      | `chembl-webresource-client`                   |
| **Rate Limit**   | None (polite usage recommended)               |
| **Health Check** | `/chembl/api/data/status`                     |
| **Auth Type**    | None (public API)                             |

----------------------------------------------------------------------

## 2. Business Context

### 2.1. Entity Purpose

Assays represent **experimental protocols** used to measure bioactivity:

- **Experimental methods**: Binding assays, functional assays, ADMET tests
- **Target context**: Links experiments to biological targets
- **Data provenance**: Source publications and curators
- **Quality metadata**: Confidence scores and relationship types

### 2.2. Use Cases

1. **Protocol Analysis**: Understand experimental conditions for activities
1. **Assay Selection**: Choose appropriate assays for screening
1. **Data Quality Assessment**: Filter by confidence and relationship type
1. **Cell-based vs Biochemical**: Compare assay types

### 2.3. Entity Relationships

```
assay
    │
    ├──FK──► target.target-id (M:1, optional)
    │
    ├──FK──► document.publication-id (M:1, optional)
    │
    ├──FK──► cell-line.cell-id (M:1, optional)
    │
    ├──◄──FK──activity.assay-id (1:M)
    │
    └──◄──FK──assay-parameters (1:M)
```

### 2.4. Load Strategy

| Parameter            | Value                           |
| -------------------- | ------------------------------- |
| **Strategy**         | `incremental` with input filter |
| **Estimated Volume** | ~1.5M records total             |
| **Batch Size**       | 20 (filter batch)               |

----------------------------------------------------------------------

## 3. Extraction (Bronze Layer)

### 3.1. Complete API Fields

| #   | API Field                    | JSON Type | Nullable | Description                |
| --- | ---------------------------- | --------- | -------- | -------------------------- |
| 1   | `assay-id`                   | string    | No       | Primary key                |
| 2   | `description`                | string    | Yes      | Assay description          |
| 3   | `assay-type`                 | string    | Yes      | B/F/A/T/P/U                |
| 4   | `assay-test-type`            | string    | Yes      | In vivo/vitro/ex vivo      |
| 5   | `assay-category`             | string    | Yes      | screening/confirmatory/... |
| 6   | `assay-organism`             | string    | Yes      | Organism                   |
| 7   | `assay-tax-id`               | integer   | Yes      | NCBI Taxonomy ID           |
| 8   | `assay-strain`               | string    | Yes      | Strain                     |
| 9   | `assay-tissue`               | string    | Yes      | Tissue                     |
| 10  | `assay-cell-type`            | string    | Yes      | Cell type                  |
| 11  | `assay-subcellular-fraction` | string    | Yes      | Subcellular fraction       |
| 12  | `target-id`                  | string    | Yes      | FK to target               |
| 13  | `relationship-type`          | string    | Yes      | D/H/M/N/S/U                |
| 14  | `relationship-description`   | string    | Yes      | Relationship desc          |
| 15  | `confidence-score`           | integer   | Yes      | 0-9 score                  |
| 16  | `confidence-description`     | string    | Yes      | Confidence desc            |
| 17  | `src-id`                     | integer   | Yes      | Source ID                  |
| 18  | `src-assay-id`               | string    | Yes      | Source assay ID            |
| 19  | `publication-id`             | string    | Yes      | FK to document             |
| 20  | `cell-id`                    | string    | Yes      | FK to cell-line            |
| 21  | `tissue-chembl-id`           | string    | Yes      | FK to tissue               |
| 22  | `bao-format`                 | string    | Yes      | BAO format ID              |
| 23  | `bao-label`                  | string    | Yes      | BAO label                  |
| 24  | `assay-classifications`      | array     | Yes      | Classifications            |
| 25  | `assay-parameters`           | array     | Yes      | Parameters                 |
| 26  | `variant-sequence`           | object    | Yes      | Variant info               |

----------------------------------------------------------------------

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter           | Value                    |
| ------------------- | ------------------------ |
| **Entity ID Field** | `assay-id`               |
| **ID Source**       | `from-api`               |
| **Format**          | ChEMBL ID (CHEMBL[0-9]+) |

### 4.2. Flattening Strategy

| Nested Path                  | Flattened Name          | Strategy       |
| ---------------------------- | ----------------------- | -------------- |
| `variant-sequence.accession` | `variant-accession`     | Extract scalar |
| `variant-sequence.mutation`  | `variant-mutation`      | Extract scalar |
| `variant-sequence.organism`  | `variant-organism`      | Extract scalar |
| `variant-sequence.tax-id`    | `variant-tax-id`        | Extract scalar |
| `variant-sequence.sequence`  | `variant-sequence`      | Extract scalar |
| `assay-classifications`      | `assay-classifications` | JSON string    |
| `assay-parameters`           | `assay-parameters`      | JSON string    |

----------------------------------------------------------------------

## 5. Validation

### 5.1. Pandera Schema

> Migration note: public Pandera contract uses canonical PK names; legacy aliases are accepted only during transition via ingestion/transform alias mapping and will be removed in the next major release.

```python
class AssaySchema(ETLRecordSchema):
    """Assay validation schema for Silver layer."""

    # === Primary Key ===
    assay-id: Series[str] = pa.Field(
        nullable=False,
        str-matches=r"^CHEMBL\d+$",
    )

    # === Description & Classification ===
    description: Series[str] | None = pa.Field(nullable=True)
    assay-type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["B", "F", "A", "T", "P", "U"],
    )
    assay-test-type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["In vivo", "In vitro", "Ex vivo"],
    )
    assay-category: Series[str] | None = pa.Field(
        nullable=True,
        isin=["screening", "confirmatory", "panel", "summary", "other"],
    )

    # === Biological Context ===
    assay-organism: Series[str] | None = pa.Field(nullable=True)
    assay-tax-id: Series[int] | None = pa.Field(nullable=True)
    assay-strain: Series[str] | None = pa.Field(nullable=True)
    assay-tissue: Series[str] | None = pa.Field(nullable=True)
    assay-cell-type: Series[str] | None = pa.Field(nullable=True)

    # === Target & Relationship ===
    target-id: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=r"^CHEMBL\d+$",
    )
    relationship-type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["D", "H", "M", "N", "S", "U"],
    )
    confidence-score: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        le=9,
    )

    # === Foreign Keys ===
    publication-id: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=r"^CHEMBL\d+$",
    )
    cell-id: Series[str] | None = pa.Field(nullable=True)
    tissue-chembl-id: Series[str] | None = pa.Field(nullable=True)

    # === Ontologies ===
    bao-format: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=r"^BAO:\d+$",
    )
    bao-label: Series[str] | None = pa.Field(nullable=True)

    # === Variant Information ===
    variant-accession: Series[str] | None = pa.Field(nullable=True)
    variant-mutation: Series[str] | None = pa.Field(nullable=True)
    variant-organism: Series[str] | None = pa.Field(nullable=True)
    variant-tax-id: Series[int] | None = pa.Field(nullable=True)

    # === Complex Fields ===
    assay-classifications: Series[str] | None = pa.Field(nullable=True)
    assay-parameters: Series[str] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### 5.2. Field Validation Matrix

| Field              | Type | Nullable | Constraints         | DQ Level |
| ------------------ | ---- | -------- | ------------------- | -------- |
| `assay-id`         | str  | No       | regex `^CHEMBL\d+$` | CRITICAL |
| `assay-type`       | str  | Yes      | isin [B,F,A,T,P,U]  | WARNING  |
| `confidence-score` | int  | Yes      | [0, 9]              | WARNING  |
| `target-id`        | str  | Yes      | regex `^CHEMBL\d+$` | INFO     |

----------------------------------------------------------------------

## 6. Pipeline Configuration

```yaml
pipeline-name: chembl_assay
provider: chembl
entity-type: assay
version: "1.2.0"

primary-keys: ["assay-id"]
silver-table: "chembl_assay"
gold-table: "chembl_assay"

gold-filters:
  required-fields:
    - description
  columns:
    confidence-score: [7, 8, 9]  # High confidence only

input-filter:
  enabled: true
  source-path: "data/input/assay.csv"
  column-name: "assay-id"
  filter-field: "assay-id"
  batch-size: 20
```

----------------------------------------------------------------------

## 7. Dependencies

### 7.1. Upstream

| Dependency      | Type     | Required    |
| --------------- | -------- | ----------- |
| ChEMBL API      | API      | Yes         |
| `chembl_target` | Pipeline | Recommended |

### 7.2. Downstream

| Consumer                  | Impact                |
| ------------------------- | --------------------- |
| `chembl_activity`         | FK reference          |
| `chembl_assay_parameters` | FK reference          |
| Protocol analysis         | Assay type statistics |
