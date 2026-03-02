# xwalk — Field-level Crosswalk Generator

*Priority: critical | Version: 1.0 | Aligned with RULES.md v5.23*

---

## Goal

Generate a field-level crosswalk (MD table + CSV) for a given `{{source}}` (provider or provider/entity), mapping every field across three layers: **docs** (pipeline spec), **cfg** (YAML configs), and **code** (Python transformers, schemas, entities).

---

## Input

| Parameter | Source | Example |
|-----------|--------|---------|
| `{{source}}` | User argument | `chembl`, `chembl/activity`, `uniprot` |
| `{{docs}}` | `docs/04-reference/pipelines/{{provider}}/` | `*-spec.md` files |
| `{{cfg}}` | `configs/pipelines/{{provider}}/{{entity}}.yaml` + `configs/schemas/{{provider}}/{{entity}}.yaml` + `configs/sources/{{provider}}.yaml` | YAML configs |
| `{{code}}` | `src/bioetl/application/pipelines/{{provider}}/{{entity}}_transformer.py` + `src/bioetl/domain/schemas/{{provider}}/{{entity}}.py` + `src/bioetl/domain/entities/{{provider}}.py` + `src/bioetl/domain/contracts/gold/{{provider}}.py` | Python source |

---

## Output

Two artifacts per entity:

1. **Markdown table** — embedded in PR body
2. **CSV file** — `docs/04-reference/pipelines/{{provider}}/{{entity}}-xwalk.csv`

### Column Schema (`{{cols}}`)

| Column | Description |
|--------|-------------|
| `field` | Canonical field name (snake_case) |
| `doc_spec` | Presence in spec MD (section ref or `MISSING`) |
| `cfg_pipeline` | Presence in pipeline YAML |
| `cfg_schema` | Presence in schema YAML |
| `code_transformer` | Presence in transformer `.py` (file:line) |
| `code_entity` | Presence in domain entity `.py` (file:line) |
| `code_gold_schema` | Presence in Gold Pandera schema (file:line) |
| `api_endpoint` | API endpoint or path the field comes from |
| `json_type` | JSON type from API (`string`, `integer`, `number`, `boolean`, `object`, `array`) |
| `nullable` | `true`/`false` |
| `primary_key` | `true`/`false` |
| `notes` | See `{{notes}}` below |

### Notes Vocabulary (`{{notes}}`)

| Tag | Meaning |
|-----|---------|
| `MISSING_DOC` | Field exists in code/cfg but not in docs spec |
| `MISSING_CFG` | Field exists in docs/code but not in config |
| `MISSING_CODE` | Field exists in docs/cfg but not in code |
| `PK_MISMATCH` | Primary key differs between layers |
| `TYPE_MISMATCH` | Type differs between layers |
| `NULLABLE_MISMATCH` | Nullability differs between layers |
| `RENAME` | Field was renamed (e.g., `cid` -> `molecule_id`) |
| `NESTED` | Flattened from nested JSON structure |
| `DENORM` | Denormalized from related entity |
| `DERIVED` | Computed field (content_hash, entity_id) |
| `OK` | Fully synchronized across all layers |

---

## Algorithm

1. **One row = one field.** Every unique field name found in any layer gets exactly one row.
2. **Pointer format:** `file::method` or `file::line` (e.g., `activity_transformer.py::_transform_impl` or `activity_transformer.py::42`).
3. **API endpoint (EP):** Extract from docs spec section "API Request" or source config `base_url` + entity path.
4. **Architecture checks:**
   - Verify transformer is in `application/pipelines/` (ARCH-001 compliant)
   - Verify Gold schema is in `domain/contracts/gold/` or `domain/schemas/`
   - Verify entities are in `domain/entities/`
   - Verify primary_keys in pipeline config match transformer logic
5. **Sort** by: primary_key desc, then field name asc.
6. **Dedup:** If the same field appears under different names (rename), merge into one row with `RENAME` note.

---

## Execution Steps

```
1. Parse {{source}} → determine provider + entity list
   - If {{source}} = "chembl" → all entities in configs/pipelines/chembl/
   - If {{source}} = "chembl/activity" → single entity

2. For each entity:
   a. Read docs spec → extract API field table (section 3.x)
   b. Read pipeline config → extract primary_keys, fields
   c. Read schema config → extract column_groups, field definitions
   d. Read transformer code → extract field references from _transform_impl
   e. Read domain entity → extract dataclass fields
   f. Read Gold schema → extract Pandera Field definitions

3. Build unified field set = union(docs_fields, cfg_fields, code_fields)

4. For each field, check presence in each layer → fill columns

5. Flag mismatches in Notes column

6. Generate MD table + CSV
```

---

## Commit & PR Convention (`{{C}}`)

- **Branch:** `xwalk/{{source}}`
- **PR title:** `docs(xwalk): {{source}} field crosswalk`
- **Labels:** `docs`, `xwalk`, `data-contract`

---

## Example

For `chembl/activity`, the crosswalk row for `activity_id`:

| field | doc_spec | cfg_pipeline | cfg_schema | code_transformer | code_entity | code_gold_schema | api_endpoint | json_type | nullable | primary_key | notes |
|-------|----------|-------------|------------|-----------------|-------------|-----------------|--------------|-----------|----------|-------------|-------|
| `activity_id` | 05-activity-spec.md::3.2 | activity.yaml::primary_keys | activity.yaml | activity_transformer.py::_transform_impl | chembl.py::ChemblActivity | chembl.py::ActivityGoldSchema | `/chembl/api/data/activity` | integer | false | true | OK |

For a renamed field like `cid` -> `molecule_id`:

| field | doc_spec | ... | notes |
|-------|----------|-----|-------|
| `molecule_id` | spec.md::3.2 (as `cid`) | ... | `RENAME: cid→molecule_id` |

---

## Constraints

- Do NOT fabricate file paths or line numbers. Verify each pointer with actual file reads.
- If a layer artifact does not exist, note `[FILE NOT FOUND]` in the corresponding column.
- Architecture invariants (ARCH-001, ARCH-008) MUST be respected when analyzing code locations.
- Output MUST be deterministic: same input → same output (sorted, deduped).
