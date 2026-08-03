# Infrastructure Layer — Navigation Map

The infrastructure layer contains concrete implementations of ports and
framework-facing adapters. It may import domain contracts, but it must not
become the place where orchestration or dependency wiring is decided.

## Main Families

| Package                                                                                  | Responsibility                                                          |
| ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `adapters/`                                                                              | Provider clients, HTTP integrations, common adapter helpers, decorators |
| `storage/`                                                                               | Bronze/Silver/Gold storage implementations and storage support code     |
| `config/`                                                                                | YAML/config loading, normalization, and source resolution               |
| `observability/`                                                                         | Logger, metrics, tracing, and anomaly-detection implementations         |
| `checkpoint/`, `locking/`, `time/`, `system/`                                            | Runtime support services                                                |
| `quality/`, `validation/`, `audit/`, `errors/`, `security/`, `serialization/`, `export/` | Specialized implementation families                                     |

## Provider Adapters

Provider-specific code lives under `adapters/` by provider family:

- `chembl/`
- `crossref/`
- `openalex/`
- `pubchem/`
- `pubmed/`
- `semanticscholar/`
- `uniprot/`

Cross-provider utilities belong in `adapters/common/`, `adapters/http/`,
`adapters/input/`, or `adapters/decorators/` rather than in a provider leaf.

## What Does Not Belong Here

- Domain policy decisions
- High-level use-case orchestration
- Factory placement decisions that belong in `composition/`
