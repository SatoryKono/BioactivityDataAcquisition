# PubChem Compound Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.21*

----------------------------------------------------------------------

## 1. Identification

| Parameter        | Value                                               |
| ---------------- | --------------------------------------------------- |
| **Pipeline ID**  | `pubchem-compound`                                  |
| **Provider**     | PubChem (NCBI)                                      |
| **Entity**       | compound                                            |
| **API Endpoint** | `https://pubchem.ncbi.nlm.nih.gov/rest/pug/`        |
| **Library**      | `pubchempy` (sync, requires executor)               |
| **Rate Limit**   | 5 req/sec                                           |
| **Health Check** | `/compound/cid/2244/property/MolecularFormula/JSON` |
| **Auth Type**    | None (public API)                                   |

----------------------------------------------------------------------

## 2. Business Context

### 2.1. Entity Purpose

PubChem compounds are **chemical structures** with computed descriptors:

- **Chemical structures**: SMILES, InChI, InChI Key
- **Molecular properties**: Weight, formula, LogP, PSA
- **Stereochemistry**: Defined/undefined stereocenters
- **3D properties**: Volume, conformers
- **Cross-database linking**: InChI Key enables ChEMBL mapping

### 2.2. Use Cases

1. **Structure Enrichment**: Add computed properties to ChEMBL molecules
1. **Property Calculation**: Access pre-computed descriptors
1. **3D Modeling**: Use 3D conformer data
1. **Compound Search**: Find by structure or property ranges

### 2.3. Entity Relationships

```
pubchem-compound
    │
    └──► chembl-molecule (via inchi-key)
```

----------------------------------------------------------------------

## 3. Extraction (Bronze Layer)

### 3.1. API Request

```python
import pubchempy as pcp

# Sync library - wrapped in executor
compound = pcp.Compound.from-cid(cid)
# Or batch:
compounds = pcp.get-compounds(cid-list, namespace="cid")
```

### 3.2. Complete API Fields

| #   | API Field                  | Type  | Nullable | Description                 |
| --- | -------------------------- | ----- | -------- | --------------------------- |
| 1   | `CID`                      | int   | No       | Compound ID (PK)            |
| 2   | `CanonicalSMILES`          | str   | Yes      | Canonical SMILES            |
| 3   | `IsomericSMILES`           | str   | Yes      | SMILES with stereochemistry |
| 4   | `InChI`                    | str   | Yes      | InChI identifier            |
| 5   | `InChIKey`                 | str   | Yes      | InChI Key (27 chars)        |
| 6   | `MolecularFormula`         | str   | Yes      | Molecular formula           |
| 7   | `MolecularWeight`          | float | Yes      | Molecular weight            |
| 8   | `ExactMass`                | float | Yes      | Exact mass                  |
| 9   | `MonoisotopicMass`         | float | Yes      | Monoisotopic mass           |
| 10  | `IUPACName`                | str   | Yes      | IUPAC name                  |
| 11  | `XLogP`                    | float | Yes      | Computed LogP               |
| 12  | `TPSA`                     | float | Yes      | Topological PSA             |
| 13  | `Complexity`               | float | Yes      | Complexity score            |
| 14  | `Charge`                   | int   | Yes      | Formal charge               |
| 15  | `HBondDonorCount`          | int   | Yes      | H-bond donors               |
| 16  | `HBondAcceptorCount`       | int   | Yes      | H-bond acceptors            |
| 17  | `RotatableBondCount`       | int   | Yes      | Rotatable bonds             |
| 18  | `HeavyAtomCount`           | int   | Yes      | Heavy atoms                 |
| 19  | `AtomStereoCount`          | int   | Yes      | Total stereocenters         |
| 20  | `DefinedAtomStereoCount`   | int   | Yes      | Defined stereocenters       |
| 21  | `UndefinedAtomStereoCount` | int   | Yes      | Undefined stereocenters     |
| 22  | `BondStereoCount`          | int   | Yes      | E/Z bonds                   |
| 23  | `DefinedBondStereoCount`   | int   | Yes      | Defined E/Z                 |
| 24  | `UndefinedBondStereoCount` | int   | Yes      | Undefined E/Z               |
| 25  | `IsotopeAtomCount`         | int   | Yes      | Isotopic atoms              |
| 26  | `CovalentUnitCount`        | int   | Yes      | Covalent units              |
| 27  | `Volume3D`                 | float | Yes      | 3D volume                   |
| 28  | `ConformerCount3D`         | int   | Yes      | 3D conformers               |

----------------------------------------------------------------------

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter           | Value                              |
| ------------------- | ---------------------------------- |
| **Entity ID Field** | `molecule-id` (derived from `CID`) |
| **ID Source**       | `from-api`                         |
| **Format**          | String (stringified CID)           |

### 4.2. Field Normalization

| Field              | Normalization   | Before              | After             |
| ------------------ | --------------- | ------------------- | ----------------- |
| `cid`              | Cast to int     | `2244`              | `2244`            |
| `molecular-weight` | round(10)       | `180.157123456789`  | `180.1571234568`  |
| `xlogp`            | round(2)        | `1.31456`           | `1.31`            |
| `canonical-smiles` | RDKit canonical | -                   | Normalized SMILES |
| `inchi-key`        | Validate format | `BSYNRYMUTXBXSQ...` | Validated         |

----------------------------------------------------------------------

## 5. Validation

### 5.1. Pandera Schema

```python
class PubchemMoleculeSchema(ETLRecordSchema):
    """PubChem Molecule validation schema for Silver layer."""

    # === Primary Key ===
    molecule-id: Series[str] = pa.Field(nullable=False)

    # === Structural Identifiers ===
    canonical-smiles: Series[str] | None = pa.Field(nullable=True)
    isomeric-smiles: Series[str] | None = pa.Field(nullable=True)
    inchi: Series[str] | None = pa.Field(nullable=True)

    @pa.check("inchi", name="inchi-format")
    def -check-inchi(cls, series):
        return series.isna() | series.str.startswith("InChI=")

    inchi-key: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=INCHI-KEY-REGEX-PATTERN,
    )

    # === Nomenclature ===
    molecular-formula: Series[str] | None = pa.Field(nullable=True)
    iupac-name: Series[str] | None = pa.Field(nullable=True)

    # === Physical Properties ===
    molecular-weight: Series[float] | None = pa.Field(
        nullable=True,
        ge=0.0,
        le=100000.0,
    )
    exact-mass: Series[float] | None = pa.Field(nullable=True, ge=0)

    # === Computed Descriptors ===
    xlogp: Series[float] | None = pa.Field(nullable=True, ge=-20, le=20)
    tpsa: Series[float] | None = pa.Field(nullable=True, ge=0)
    complexity: Series[float] | None = pa.Field(nullable=True, ge=0)
    charge: Series[int] | None = pa.Field(nullable=True, ge=-10, le=10)

    # === Atom/Bond Counts ===
    heavy-atom-count: Series[int] | None = pa.Field(nullable=True, ge=1, le=500)
    h-bond-donor-count: Series[int] | None = pa.Field(nullable=True, ge=0, le=50)
    h-bond-acceptor-count: Series[int] | None = pa.Field(nullable=True, ge=0, le=50)
    rotatable-bond-count: Series[int] | None = pa.Field(nullable=True, ge=0, le=100)

    # === Stereochemistry ===
    atom-stereo-count: Series[int] | None = pa.Field(nullable=True, ge=0)
    defined-atom-stereo-count: Series[int] | None = pa.Field(nullable=True, ge=0)
    undefined-atom-stereo-count: Series[int] | None = pa.Field(nullable=True, ge=0)
    bond-stereo-count: Series[int] | None = pa.Field(nullable=True, ge=0)
    covalent-unit-count: Series[int] | None = pa.Field(nullable=True, ge=1)

    # === 3D Properties ===
    volume-3d: Series[float] | None = pa.Field(nullable=True, ge=0)
    conformer-count-3d: Series[int] | None = pa.Field(nullable=True, ge=0)

    class Config:
        strict = True
        ordered = True
        coerce = True
```

----------------------------------------------------------------------

## 6. Cross-Provider Mapping

| This Entity Field | Maps To          | Provider | Field                          |
| ----------------- | ---------------- | -------- | ------------------------------ |
| `inchi-key`       | ChEMBL           | ChEMBL   | `structure-standard-inchi-key` |
| `molecule-id`     | PubChem BioAssay | PubChem  | CID                            |

----------------------------------------------------------------------

## 7. Pipeline Configuration

```yaml
pipeline-name: pubchem-compound
provider: pubchem
entity-type: compound
version: "1.2.0"

primary-keys: ["molecule-id"]
silver-table: "pubchem-compound"
gold-table: "pubchem-compound"

source:
  type: api
  batch-size: 100  # PubChem allows batch requests

sink:
  bronze:
    path: "data/output/bronze"
  silver:
    path: "data/output/silver"
    primary-key: ["molecule-id"]
    partition-by: []
  gold:
    path: "data/output/gold"

input-filter:
  enabled: true
  source-path: "data/input/compound.csv"
  column-name: "cid"
  filter-field: "cid"
  batch-size: 100
```

----------------------------------------------------------------------

## 8. Special Considerations

### 8.1. Sync Library Handling

PubChemPy is synchronous. BioETL wraps it using `BaseSyncAdapter`:

```python
class PubChemAdapter(BaseSyncAdapter):
    async def fetch(self, cids: list[int]) -> list[dict]:
        # Wrapped in executor
        return await self.-run-in-executor(pcp.get-compounds, cids, namespace="cid")
```

### 8.2. Rate Limiting

- **Hard limit**: 5 requests/second
- **Batch size**: Up to 100 CIDs per request
- **Recommendation**: Use batch requests to maximize throughput
