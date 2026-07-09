______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-06'

______________________________________________________________________

# Data Contracts Current State

Current source of truth:

- Entity data contract YAML:
  `configs/contracts/{chembl,composite,crossref,openalex,pubchem,pubmed,semanticscholar,uniprot}/*.yaml`
- Error catalog contract: `configs/contracts/errors/error_catalog.yaml`
- Entity config schemas: `configs/entities/**/*.yaml`
- Gold domain contracts: `src/bioetl/domain/contracts/gold/`
- Contract identity model: `src/bioetl/domain/types/contract_identity.py`
- Contract rollout policy: `src/bioetl/domain/types/contract_rollout.py`
- Contract policy loading/validation:
  `src/bioetl/infrastructure/config/contract_policy_loader.py`,
  `src/bioetl/infrastructure/config/contract_policy_validation.py`
- DQ contract loading:
  `src/bioetl/infrastructure/config/dq_contract_config_loader.py`

## Contract Inventory

There are 27 active YAML entity data contracts, aligned one-to-one with the 27
entity pipeline configs. The error catalog at
`configs/contracts/errors/error_catalog.yaml` is a separate error-code taxonomy
contract and is not counted in the 27 entity data contracts.

| Provider | Contracts |
| --- | --- |
| ChEMBL | `activity`, `assay`, `assay_parameters`, `cell_line`, `compound_record`, `molecule`, `protein_class`, `publication`, `publication_similarity`, `publication_term`, `subcellular_fraction`, `target`, `target_component`, `target_protein_classification`, `tissue` |
| Composite | `activity`, `assay`, `molecule`, `publication`, `target` |
| CrossRef | `publication` |
| OpenAlex | `publication` |
| PubChem | `compound` |
| PubMed | `publication` |
| Semantic Scholar | `publication` |
| UniProt | `idmapping`, `protein` |

## Runtime Contract Chain

```mermaid
flowchart LR
    ContractYaml["entity contract YAML"]
    ErrorCatalog["error catalog contract"]
    EntityYaml["configs/entities/**/*.yaml"]
    Loader["infrastructure config loaders"]
    Policy["ContractRolloutPolicy / ContractIdentity"]
    Pipeline["application pipeline execution"]
    Writer["Silver/Gold writer policy"]
    Manifest["RunManifest code_provenance contract anchors"]
    DQ["DQ contract policy"]

    ContractYaml --> Loader
    ErrorCatalog --> Loader
    EntityYaml --> Loader
    Loader --> Policy
    Policy --> Pipeline
    Policy --> Writer
    Policy --> DQ
    Pipeline --> Manifest
```

## Boundary Rules

- Domain owns immutable contract value semantics and identity objects.
- Infrastructure owns YAML loading and Pydantic compatibility/runtime schema
  validation.
- Application consumes contract policies through injected services and ports.
- Composition wires the current contract policy into pipeline factory and writer
  construction.
- Prometheus metrics must not expose raw contract fingerprints, run IDs,
  manifest IDs, record IDs, hashes, filesystem paths, or raw error messages as
  labels.

## Regression Checks

Use these checks after contract or config documentation changes:

```bash
python -m pytest tests/architecture -q
python -m pytest tests/contract -q
python -m scripts.engineering.qa report-observability-metric-inventory --json
```

If a source-code change under `src/bioetl/**/*.py` affects module coverage
inventory, refresh `reports/quality/module-coverage-inventory.json` before
claiming architecture artifact currency.
