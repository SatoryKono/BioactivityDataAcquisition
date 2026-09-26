# Domain Composite Config Importer Map

Generated for issue `#5255` closeout from the working tree after the
2026-06-16 technical-debt audit.

## Scope

- Public seam: `bioetl.domain.composite.config`
- Split-internal prefix: `bioetl.domain.composite.config_*`
- Scan roots: `src/`, `tests/`
- Policy: no growth from this baseline without an explicit compatibility
  review. The public seam remains sanctioned; split-internal imports should stay
  confined to owner modules and the reviewed residual importer below.

## Baseline Counts

| Import class | Source files | Test files | Policy |
| --- | ---: | ---: | --- |
| Public facade importers | 80 | 38 | No growth; migrate only when canonical replacement exists. |
| Split-internal importers | 7 | 3 | No growth; owner package plus reviewed residual only. |

## Owner Map

| Owner lane | Public facade importers | Split-internal importers | Closeout rule |
| --- | ---: | ---: | --- |
| `src/bioetl/domain/composite/**` | 1 | 6 | Owning package may import split internals. |
| `src/bioetl/application/composite/**` | 48 | 0 | Public seam imports allowed; no split internals. |
| `src/bioetl/composition/bootstrap/runtime/**` | 19 | 0 | Public seam imports allowed while runtime builder migration proceeds. |
| Other first-party source | 12 | 1 | Public seam allowed; split-internal residual must not grow. |
| Tests | 38 | 3 | Split-internal tests must remain dedicated facade/parser coverage. |

## Reviewed Residual Split-Internal Importer

- `src/bioetl/infrastructure/schemas/pipeline_config.py`

This residual importer is retained only as a schema-boundary source-of-truth
bridge. Any additional split-internal importer outside
`src/bioetl/domain/composite/**` must fail architecture review.

## Enforcement

The baseline is enforced by
`tests/architecture/test_domain_composite_config_importer_map.py`.
