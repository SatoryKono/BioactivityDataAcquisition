# schema-review — Schema Coverage Checklist

*Priority: medium | Version: 1.0 | Aligned with RULES.md v5.19*

______________________________________________________________________

## Goal

Review schema coverage for a given `{{source}}`: verify that every DataFrame column produced by the transformer is covered by both a Pandera schema and a Pydantic/dataclass entity, with correct types and constraints.

______________________________________________________________________

## Input

| Parameter      | Source                                                                    | Example                     |
| -------------- | ------------------------------------------------------------------------- | --------------------------- |
| `{{source}}`   | User argument                                                             | `chembl`, `chembl/activity` |
| schemas        | `src/bioetl/domain/schemas/{{provider}}/`                                 | Pandera DataFrameModel      |
| entities       | `src/bioetl/domain/entities/{{provider}}.py`                              | Dataclass entities          |
| gold contracts | `src/bioetl/domain/contracts/gold/{{provider}}.py`                        | Gold Pandera schemas        |
| transformers   | `src/bioetl/application/pipelines/{{provider}}/{{entity}}_transformer.py` | Field producers             |

______________________________________________________________________

## Output

A checklist in Markdown format, suitable for a PR body or review comment.

______________________________________________________________________

## Algorithm

### 1. Collect DataFrame columns from transformer

Parse each transformer's `_transform_impl` method to extract the `business_data` dict keys. These are the columns that will appear in the Silver DataFrame.

Also collect system columns added by `BaseTransformer`:

- `entity_id`, `content_hash`
- `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`

### 2. Collect schema fields

From Pandera schema (Silver):

```python
# src/bioetl/domain/schemas/{{provider}}/{{entity}}.py
class EntitySchema(pa.DataFrameModel):
    field_name: Series[type] = pa.Field(...)
```

From domain entity:

```python
# src/bioetl/domain/entities/{{provider}}.py
@dataclass
class Entity(BaseEntity):
    field_name: type
```

From Gold contract:

```python
# src/bioetl/domain/contracts/gold/{{provider}}.py
class EntityGoldSchema(pa.DataFrameModel):
    field_name: Series[type] = pa.Field(...)
```

### 3. Build coverage matrix

For each column in transformer output:

| Column  | Transformer | Silver Schema         | Entity                | Gold Schema           | Type Match  | Nullable Match | Notes |
| ------- | ----------- | --------------------- | --------------------- | --------------------- | ----------- | -------------- | ----- |
| `field` | `file:line` | `file:line` / MISSING | `file:line` / MISSING | `file:line` / MISSING | OK/MISMATCH | OK/MISMATCH    |       |

### 4. Check architectural compliance

- [ ] Silver schema is in `domain/schemas/` (not `infrastructure/`)
- [ ] Gold schema is in `domain/contracts/gold/`
- [ ] Entity is in `domain/entities/`
- [ ] Schema class naming: `{Entity}Schema` (Silver), `{Entity}GoldSchema` (Gold)
- [ ] All fields use proper Pandera types (not raw Python types)
- [ ] `int` fields that are nullable use `float` with `coerce=True` (EXC-007)

### 5. Generate checklist

```markdown
## Schema Review: {{source}}

### Coverage Summary

| Entity | Transformer Fields | Silver Schema | Entity | Gold Schema | Coverage |
|--------|-------------------|---------------|--------|-------------|----------|
| activity | 30 | 28/30 | 25/30 | 20/30 | 93% |

### Missing Fields

#### {{entity}}: Fields in transformer but NOT in Silver schema
- [ ] `new_field` — add to `{{provider}}/{{entity}}.py::EntitySchema`

#### {{entity}}: Fields in transformer but NOT in entity
- [ ] `new_field` — add to `domain/entities/{{provider}}.py::Entity`

#### {{entity}}: Fields in Silver but NOT in Gold
- [ ] `field_x` — intentional (denormalized) or add to Gold schema

### Type Mismatches

| Entity | Field | Transformer | Schema | Fix |
|--------|-------|-------------|--------|-----|
| activity | `tpsa` | `float` | MISSING | Add `tpsa: Series[float] = pa.Field(nullable=True)` |

### Architecture Compliance

- [x] All schemas in correct layers
- [x] Naming conventions followed
- [ ] **ISSUE:** `FooSchema` in `infrastructure/` — move to `domain/schemas/`
```

______________________________________________________________________

## Commit & PR Convention (`{{C}}`)

- **Branch:** `schema/{{source}}`
- **PR title:** `refactor(schema): {{source}} coverage gaps`
- **Labels:** `schema`

______________________________________________________________________

## Example

Adding `tpsa` field to ChEMBL molecule:

```
### chembl/molecule: Missing in Gold Schema

- [ ] `tpsa: Series[float] = pa.Field(nullable=True)` — add to ChemblMoleculeGoldSchema
  - Transformer: molecule_transformer.py:67
  - Silver schema: molecule.py:ChemblMoleculeSchema (present)
  - Gold schema: chembl.py:ChemblMoleculeGoldSchema (MISSING)
```

______________________________________________________________________

## Constraints

- Do NOT auto-fix schemas. This prompt produces a checklist only.
- Respect EXC-007: `int` → `float` coercion for nullable integer fields is intentional.
- Respect EXC-015: Config classes with defaults are valid.
- Fields starting with `_` are system/lineage fields — verify they follow `BaseTransformer` convention.
- If schema files don't exist, flag as `[SCHEMA FILE NOT FOUND]`.

## ADR Status Guardrail

- Перед выводами по ADR пересчитать baseline как фактическое количество файлов `docs/02-architecture/decisions/ADR-*.md` (не фиксировать число вручную).
- Разрешённые базовые статусы ADR: `Accepted`, `Superseded`, `Deprecated`, `Added`.
- `Superseded` НЕ считать автоматическим дефектом: это нормальная эволюция архитектуры при наличии ADR-замены/контекста.
- Дефектом считать только отсутствие статуса, невалидный статус или `Superseded` без связи с заменяющим ADR.
