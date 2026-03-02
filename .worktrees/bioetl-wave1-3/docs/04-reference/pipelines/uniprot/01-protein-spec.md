# UniProt Protein Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.22*

----------------------------------------------------------------------

## 1. Identification

| Parameter        | Value                                 |
| ---------------- | ------------------------------------- |
| **Pipeline ID**  | `uniprot_protein`                     |
| **Provider**     | UniProt (EBI/SIB/PIR)                 |
| **Entity**       | protein                               |
| **API Endpoint** | `https://rest.uniprot.org/uniprotkb/` |
| **Library**      | `unipressed` (async)                  |
| **Rate Limit**   | 100 req/sec (with API key)            |
| **Health Check** | `/rest/beta/health`                   |
| **Auth Type**    | API Key (optional)                    |

----------------------------------------------------------------------

## 2. Business Context

### 2.1. Entity Purpose

UniProt proteins are **curated protein entries** with comprehensive annotations:

- **Protein sequences**: Primary amino acid sequences
- **Functional annotations**: Function, pathway, subcellular location
- **Cross-references**: Links to ChEMBL, DrugBank, GO terms
- **Species context**: Organism and taxonomy information
- **Quality tiers**: Swiss-Prot (reviewed) vs TrEMBL (unreviewed)

### 2.2. Use Cases

1. **Target Identification**: Find drug targets with ChEMBL links
1. **Sequence Analysis**: Access protein sequences for alignment
1. **Functional Annotation**: Understand protein functions
1. **Drug-Target Networks**: Build networks via cross-references
1. **Species Translation**: Compare orthologs across organisms

### 2.3. Entity Relationships

```
uniprot_protein
    │
    ├──► chembl_target (via chembl-ids cross-ref)
    │
    ├──► drugbank (via drugbank-ids cross-ref)
    │
    └──► GO terms (via go-terms)
```

----------------------------------------------------------------------

## 3. Extraction (Bronze Layer)

### 3.1. API Request

```python
from unipressed import UniProtkbClient

client = UniProtkbClient()
# Search by accession or query
results = await client.search(
    query="accession:P00533",
    fields=[
        "accession",
        "id",
        "protein-name",
        "gene-names",
        "organism-name",
        "organism-id",
        "sequence",
        "length",
        "cc-function",
        "cc-pathway",
        "xref-chembl",
        "xref-drugbank",
    ],
)
```

### 3.2. Complete API Fields

| #   | API Field             | JSON Type | Nullable | Description            |
| --- | --------------------- | --------- | -------- | ---------------------- |
| 1   | `primaryAccession`    | string    | No       | Primary accession (PK) |
| 2   | `uniProtkbId`         | string    | No       | Entry name             |
| 3   | `entryType`           | string    | Yes      | Swiss-Prot/TrEMBL      |
| 4   | `secondaryAccessions` | array     | Yes      | Secondary accessions   |
| 5   | `proteinDescription`  | object    | Yes      | Protein names          |
| 6   | `genes`               | array     | Yes      | Gene names             |
| 7   | `organism`            | object    | Yes      | Organism info          |
| 8   | `sequence`            | object    | Yes      | Sequence data          |
| 9   | `features`            | array     | Yes      | Sequence features      |
| 10  | `comments`            | array     | Yes      | Functional annotations |
| 11  | `dbreferences`        | array     | Yes      | Cross-references       |
| 12  | `keywords`            | array     | Yes      | UniProt keywords       |

### 3.3. Nested Structure: proteinDescription

| Field                                | Type   | Description              |
| ------------------------------------ | ------ | ------------------------ |
| `recommendedName.fullName.value`     | string | Recommended protein name |
| `alternativeNames[*].fullName.value` | array  | Alternative names        |
| `ecNumbers[*].value`                 | array  | EC numbers               |

### 3.4. Nested Structure: organism

| Field            | Type    | Description       |
| ---------------- | ------- | ----------------- |
| `scientificName` | string  | Scientific name   |
| `commonName`     | string  | Common name       |
| `taxonId`        | integer | NCBI Taxonomy ID  |
| `lineage`        | array   | Taxonomic lineage |

### 3.5. Nested Structure: sequence

| Field       | Type    | Description         |
| ----------- | ------- | ------------------- |
| `value`     | string  | Amino acid sequence |
| `length`    | integer | Sequence length     |
| `molWeight` | integer | Molecular weight    |
| `crc64`     | string  | CRC64 checksum      |

----------------------------------------------------------------------

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter           | Value                          |
| ------------------- | ------------------------------ |
| **Entity ID Field** | `accession` (primaryAccession) |
| **ID Source**       | `from-api`                     |
| **Format**          | UniProt accession pattern      |

### 4.2. Flattening Strategy

| Nested Path                                         | Flattened Name        | Strategy         |
| --------------------------------------------------- | --------------------- | ---------------- |
| `proteinDescription.recommendedName.fullName.value` | `protein-name`        | Extract scalar   |
| `proteinDescription.ecNumbers[*].value`             | `protein-ec-numbers`  | JSON array       |
| `genes[0].geneName.value`                           | `gene-primary`        | Extract first    |
| `genes[*].synonyms[*].value`                        | `gene-synonyms`       | JSON array       |
| `organism.scientificName`                           | `organism-scientific` | Extract scalar   |
| `organism.commonName`                               | `organism-common`     | Extract scalar   |
| `organism.taxonId`                                  | `taxonomy-id`         | Extract scalar   |
| `sequence.value`                                    | `sequence`            | Extract scalar   |
| `sequence.length`                                   | `sequence-length`     | Extract scalar   |
| `sequence.molWeight`                                | `sequence-mass`       | Extract scalar   |
| `dbreferences[type=ChEMBL]`                         | `chembl-ids`          | Filter & extract |
| `dbreferences[type=DrugBank]`                       | `drugbank-ids`        | Filter & extract |

----------------------------------------------------------------------

## 5. Validation

### 5.1. Pandera Schema

> Migration note: public Pandera contract uses canonical PK names; legacy aliases are accepted only during transition via ingestion/transform alias mapping and will be removed in the next major release.

```python
class UniprotTargetSchema(ETLRecordSchema):
    """UniProt Target validation schema for Silver layer."""

    # === Primary Key ===
    accession: Series[str] = pa.Field(
        nullable=False,
        description="UniProt primary accession (PK)",
    )

    @pa.check("accession", name="accession-format")
    def -check-accession(cls, series):
        pattern = (
            r"^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]"
            r"([A-Z][A-Z0-9]{2}[0-9]){1,2}$"
        )
        return series.str.match(pattern)

    entry-name: Series[str] = pa.Field(nullable=False)
    entry-type: Series[str] | None = pa.Field(
        nullable=True,
        isin=ENTRY-TYPES,  # Swiss-Prot/TrEMBL
    )

    # === Protein Names ===
    protein-name: Series[str] | None = pa.Field(nullable=True)
    protein-ec-numbers: Series[str] | None = pa.Field(nullable=True)  # JSON

    # === Gene Names ===
    gene-primary: Series[str] | None = pa.Field(nullable=True)
    gene-synonyms: Series[str] | None = pa.Field(nullable=True)  # JSON

    # === Organism ===
    organism-scientific: Series[str] | None = pa.Field(nullable=True)
    organism-common: Series[str] | None = pa.Field(nullable=True)
    taxonomy-id: Series[int] | None = pa.Field(nullable=True, ge=1)

    # === Sequence ===
    sequence: Series[str] = pa.Field(nullable=False)

    @pa.check("sequence", name="sequence-format")
    def -check-sequence(cls, series):
        return series.str.match(r"^[ACDEFGHIKLMNPQRSTVWY]+$")

    sequence-length: Series[int] = pa.Field(nullable=False, ge=1)
    sequence-mass: Series[int] | None = pa.Field(nullable=True, ge=1)

    # === Evidence ===
    protein-existence: Series[str] | None = pa.Field(
        nullable=True,
        isin=PROTEIN-EXISTENCE-LEVELS,
    )
    annotation-score: Series[int] | None = pa.Field(
        nullable=True,
        ge=1,
        le=5,
    )
    reviewed: Series[bool] = pa.Field(nullable=False)

    # === Functional Annotation ===
    function-comment: Series[str] | None = pa.Field(nullable=True)  # JSON
    catalytic-activity: Series[str] | None = pa.Field(nullable=True)  # JSON
    pathway: Series[str] | None = pa.Field(nullable=True)  # JSON
    subcellular-location: Series[str] | None = pa.Field(nullable=True)  # JSON
    disease-involvement: Series[str] | None = pa.Field(nullable=True)  # JSON

    # === Cross-References ===
    go-terms: Series[str] | None = pa.Field(nullable=True)  # JSON
    chembl-ids: Series[str] | None = pa.Field(nullable=True)  # JSON
    drugbank-ids: Series[str] | None = pa.Field(nullable=True)  # JSON

    # === Features & Keywords ===
    features: Series[str] | None = pa.Field(nullable=True)  # JSON
    keywords: Series[str] | None = pa.Field(nullable=True)  # JSON

    class Config:
        strict = True
        ordered = True
        coerce = True
```

### 5.2. Field Validation Matrix

| Field             | Type | Nullable | Constraints           | DQ Level |
| ----------------- | ---- | -------- | --------------------- | -------- |
| `accession`       | str  | No       | UniProt format        | CRITICAL |
| `entry-name`      | str  | No       | format `XXX-SPECIES`  | CRITICAL |
| `sequence`        | str  | No       | amino acid chars only | CRITICAL |
| `sequence-length` | int  | No       | >= 1                  | CRITICAL |
| `taxonomy-id`     | int  | Yes      | >= 1                  | WARNING  |
| `reviewed`        | bool | No       | -                     | INFO     |

----------------------------------------------------------------------

## 6. Cross-Provider Mapping

| This Entity Field | Maps To       | Provider | Field                        |
| ----------------- | ------------- | -------- | ---------------------------- |
| `accession`       | ChEMBL        | ChEMBL   | `target-component.accession` |
| `chembl-ids[*]`   | ChEMBL        | ChEMBL   | `target-id`                  |
| `drugbank-ids[*]` | DrugBank      | DrugBank | `drugbank-id`                |
| `taxonomy-id`     | NCBI Taxonomy | NCBI     | `tax-id`                     |

----------------------------------------------------------------------

## 7. Pipeline Configuration

```yaml
pipeline-name: uniprot_protein
provider: uniprot
entity-type: protein
version: "1.2.0"

primary-keys: ["accession"]
silver-table: "uniprot_protein"
gold-table: "uniprot_protein"

source-file: ../../sources/uniprot.yaml

gold-filters:
  required-fields:
    - protein-name
    - sequence
  columns:
    reviewed: [true]  # Swiss-Prot only

sink:
  bronze:
    path: "data/output/bronze"
  silver:
    path: "data/output/silver"
    primary-key: ["accession"]
    partition-by: []
  gold:
    path: "data/output/gold"

input-filter:
  enabled: true
  source-path: "data/input/protein.csv"
  column-name: "accession"
  filter-field: "accession"
  batch-size: 100  # Higher for UniProt
```

----------------------------------------------------------------------

## 8. Dependencies

### 8.1. Upstream

| Dependency          | Type     | Required                      |
| ------------------- | -------- | ----------------------------- |
| UniProt REST API    | API      | Yes                           |
| `uniprot_idmapping` | Pipeline | Optional (for ChEMBL→UniProt) |

### 8.2. Downstream

| Consumer               | Impact                          |
| ---------------------- | ------------------------------- |
| Target annotation      | Protein function/pathway data   |
| Cross-database linking | ChEMBL/DrugBank integration     |
| Sequence analysis      | Protein sequences for alignment |
