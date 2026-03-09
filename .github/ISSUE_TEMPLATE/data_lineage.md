---
name: Schema-Watch / Data Lineage / DQ
about: Request schema-watch, data lineage tracking (OpenLineage), Pandera CI contracts, or Great Expectations DQ suites
labels: enhancement, data-quality, observability
---

## Category

<!-- Which capability does this issue address? (pick one)
- Schema-watch (detect column drift between runs)
- Data lineage emission (OpenLineage RunEvent)
- Pandera schema contract (CI fast gate)
- Great Expectations DQ suite (deep content checks)
- Custom OpenLineage facet
- Other / combination
-->

## Affected Pipeline / Entity

<!-- Which ETL pipeline or entity is in scope?
e.g. chembl/molecule, pubchem/compound, composite, All pipelines
-->

## Medallion Layer(s)

<!-- Bronze / Silver / Gold / All -->

## Problem Statement

<!-- Describe what schema drift, lineage gap, or data-quality blind spot this addresses.
Include concrete examples: missing column, type change, unexpected nulls, etc. -->

## Proposed Solution

<!-- How should this be implemented? Reference specific ports, layers, or adapters.
Code snippets (OpenLineage client, Pandera model, GE checkpoint) are welcome. -->

### OpenLineage RunEvent sketch (optional)

```python
# evt = RunEvent(
#     eventType=RunState.COMPLETE,
#     job=Job(namespace="bioetl", name="<provider>/<entity>"),
#     outputs=[Dataset(
#         namespace="warehouse",
#         name="silver.<table>",
#         facets={"schema": SchemaDatasetFacet(fields=[...])}
#     )]
# )
```

### Pandera schema model sketch (optional)

```python
# import pandera.polars as pa_pl
# import polars as pl
#
# class MySchema(pa_pl.DataFrameModel):
#     column_a: pa_pl.Series[str]
#     column_b: pa_pl.Series[float]
```

## Acceptance Criteria

- [ ] <!-- e.g. Pandera schema validates Silver DataFrame before Delta write; CI fails on drift -->
- [ ] <!-- e.g. OpenLineage RunEvent with SchemaDatasetFacet emitted per pipeline run -->
- [ ] <!-- e.g. File transport used in CI (no prod Marquez server required) -->
- [ ] <!-- e.g. Contract test added under tests/unit/ -->
- [ ] Architecture boundary tests still pass (no layer violations)

## Affected Architecture Layers

<!-- Domain / Application / Infrastructure / Composition / Interfaces / Configs / CI -->

## Alternatives Considered

<!-- Any other approaches or libraries you evaluated -->

## References

<!-- Links to ADRs, OpenLineage spec, Pandera docs, GE docs, or related issues/PRs
- OpenLineage spec: https://openlineage.io/docs/spec/
- Pandera Polars: https://pandera.readthedocs.io/en/stable/polars.html
-->
