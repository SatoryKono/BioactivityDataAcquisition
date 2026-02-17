# docs-PR — Documentation Sync PR Generator

*Priority: medium | Version: 1.0 | Aligned with RULES.md v5.19*

---

## Goal

Generate a PR that synchronizes documentation (`docs/04-reference/pipelines/`) with the actual pipeline configs (`configs/`) and code (`src/bioetl/`), ensuring docs accurately reflect the implemented data contracts.

---

## Input

| Parameter | Source | Example |
|-----------|--------|---------|
| `{{source}}` | User argument | `chembl`, `chembl/activity`, `all` |
| `{{cfg}}` | `configs/pipelines/{{provider}}/{{entity}}.yaml` | Pipeline config |
| `{{docs}}` | `docs/04-reference/pipelines/{{provider}}/` | Spec markdown files |

---

## Output

- **PR** with documentation diffs
- Updated spec files where configs/code diverge from docs

---

## Algorithm

For each entity in `{{source}}`:

### 1. Extract ground truth from config + code

```
cfg_truth:
  - primary_keys       ← configs/pipelines/{{provider}}/{{entity}}.yaml
  - batch_size         ← same
  - gold_filters       ← same or configs/filters/entities/{{provider}}/{{entity}}.yaml
  - dq_overrides       ← same or configs/quality/entities/{{provider}}/{{entity}}.yaml
  - sink config        ← same

code_truth:
  - transformer fields ← src/bioetl/application/pipelines/{{provider}}/{{entity}}_transformer.py
  - entity fields      ← src/bioetl/domain/entities/{{provider}}.py
  - schema fields      ← src/bioetl/domain/schemas/{{provider}}/{{entity}}.py
  - gold schema        ← src/bioetl/domain/contracts/gold/{{provider}}.py
  - API endpoint       ← src/bioetl/infrastructure/adapters/{{provider}}/client.py
```

### 2. Compare with docs spec

Check each spec section:

| Section | Compare Against | Key Fields |
|---------|----------------|------------|
| 1. Identification | source config | API endpoint, rate limit, auth |
| 3. Extraction | code + cfg | API fields table, nested structures |
| 4. Transformation | transformer code | field normalization, flattening |
| 5. Validation | schema + DQ config | Pandera schema, DQ thresholds |
| 6. Output | pipeline config | paths, formats, partition |
| 8. Configuration | pipeline config | YAML block in spec matches actual file |

### 3. Generate diffs

For each mismatch:

```markdown
### {{entity}}: Section N — {{section_name}}

**Current (docs):**
> primary_keys: ["cid"]

**Expected (config/code):**
> primary_keys: ["molecule_id"]

**File refs:**
- Config: configs/pipelines/{{provider}}/{{entity}}.yaml:24
- Code: {{entity}}_transformer.py:42
```

### 4. Apply fixes

Update the docs spec file to match config/code ground truth.

---

## Architecture Compliance

- Docs MUST reflect the actual code structure (Hexagonal Architecture)
- API endpoint in docs MUST match `configs/sources/{{provider}}.yaml` `base_url` + entity path
- Field tables in docs MUST include all fields from transformer's `_transform_impl`
- Pandera schema in docs MUST match `domain/schemas/` or `domain/contracts/gold/`
- Primary keys in docs MUST match `configs/pipelines/{{provider}}/{{entity}}.yaml`

---

## Commit & PR Convention (`{{C}}`)

- **Branch:** `docs-sync/{{source}}`
- **PR title:** `docs({{source}}): sync specs with config and code`
- **Labels:** `docs`
- **PR body:**
  ```markdown
  ## Summary
  - Synchronized {{N}} spec files for {{source}}
  - Fixed {{M}} field mismatches
  - Updated {{K}} primary key references

  ## Changes
  {{list of changed files with brief description}}

  ## Verification
  - [ ] All primary_keys match configs/pipelines/
  - [ ] All API endpoints match configs/sources/
  - [ ] All field tables match transformer code
  ```

---

## Example

For `chembl/activity` where docs say `primary_keys: ["cid"]` but config says `primary_keys: ["activity_id"]`:

```diff
- | **Primary Key** | `cid` |
+ | **Primary Key** | `activity_id` |
```

---

## Constraints

- Do NOT modify config or code files. This prompt only updates docs.
- Preserve the existing spec structure (section numbering, formatting).
- If a spec file does not exist for an entity, create it following the template in `docs/04-reference/templates/` or the pattern of existing specs.
- Mark any fields in docs that cannot be verified against code as `[UNVERIFIED]`.
