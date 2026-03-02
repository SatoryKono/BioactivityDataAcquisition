# pk-issue — Primary Key Mismatch Issue Creator

*Priority: critical | Version: 1.0 | Aligned with RULES.md v5.23*

---

## Goal

Detect primary key mismatches between documentation (`{{docs_file}}`) and configuration (`{{cfg_file}}`) for a given `{{source}}`, and create a GitHub Issue with precise line references, ownership, and a test plan.

---

## Input

| Parameter | Source | Example |
|-----------|--------|---------|
| `{{source}}` | User argument | `chembl/activity`, `uniprot/protein` |
| `{{docs_file}}` | `docs/04-reference/pipelines/{{provider}}/` | Spec with PK reference |
| `{{cfg_file}}` | `configs/pipelines/{{provider}}/{{entity}}.yaml` | Pipeline config with `primary_keys` |

Additionally check:
- `src/bioetl/application/pipelines/{{provider}}/{{entity}}_transformer.py` — PK in `_transform_impl`
- `src/bioetl/domain/entities/{{provider}}.py` — PK in entity dataclass
- `src/bioetl/domain/schemas/{{provider}}/{{entity}}.py` — PK in Pandera schema
- `src/bioetl/domain/contracts/gold/{{provider}}.py` — PK in Gold schema

---

## Output

A GitHub Issue created via `gh issue create`.

---

## Algorithm

### 1. Extract PKs from all layers

```
pk_docs  = parse docs spec → Section 1 "Primary Key" or Section 4.1 "Entity ID"
pk_cfg   = parse configs/pipelines → primary_keys field
pk_code  = parse transformer → _get_required_field() or compute_entity_id()
pk_entity = parse domain entity → first field after primary key comment
pk_schema = parse Pandera schema → Field(nullable=False) that is PK
```

### 2. Compare

```python
all_pks = {pk_docs, pk_cfg, pk_code, pk_entity, pk_schema}
if len(all_pks) > 1:
    MISMATCH DETECTED
```

### 3. Build Issue

```markdown
## Title
PK mismatch: {{source}} — {{pk_summary}}

## Labels
data-contract, bug, critical

## Body

### Problem

Primary key for `{{source}}` is inconsistent across layers:

| Layer | File | Line | PK Value |
|-------|------|------|----------|
| Docs | {{docs_file}} | L{{line}} | `{{pk_docs}}` |
| Config | {{cfg_file}} | L{{line}} | `{{pk_cfg}}` |
| Transformer | {{transformer_file}} | L{{line}} | `{{pk_code}}` |
| Entity | {{entity_file}} | L{{line}} | `{{pk_entity}}` |
| Schema | {{schema_file}} | L{{line}} | `{{pk_schema}}` |

### Expected

All layers MUST use the same primary key: `{{canonical_pk}}`

The canonical PK is determined by:
1. Pipeline config (`primary_keys`) — source of truth for runtime
2. Transformer code — must match config
3. All other layers follow

### Impact

- **Silver merge:** Uses PK for Delta Lake MERGE ON clause
- **Content hash:** PK is part of entity_id computation
- **Gold schema:** PK validated as non-nullable
- **Data integrity:** Mismatch causes duplicate/orphan records

### Root Cause

{{describe which layer deviated and likely reason}}

### Fix Plan

- [ ] Update `{{file_to_fix}}` line {{line}} to use `{{canonical_pk}}`
- [ ] Run: `pytest tests/unit/application/pipelines/{{provider}}/ -v`
- [ ] Run: `pytest tests/architecture/ -v`
- [ ] Verify Silver MERGE works: `python -m bioetl run {{provider}} {{entity}} --dry-run`

### Owner

{{infer from git blame of the divergent file}}

### Test Plan

```bash
# Verify PK consistency
grep -n "primary_keys" configs/pipelines/{{provider}}/{{entity}}.yaml
grep -n "{{canonical_pk}}" src/bioetl/application/pipelines/{{provider}}/{{entity}}_transformer.py
grep -n "{{canonical_pk}}" src/bioetl/domain/entities/{{provider}}.py

# Run affected tests
pytest tests/unit/application/pipelines/{{provider}}/test_{{entity}}_transformer.py -v
pytest tests/architecture/ -v
```
```

---

## Commit & PR Convention (`{{C}}`)

- **Issue:** `gh issue create -t 'PK mismatch: {{source}}' -l data-contract,bug,critical`
- **Fix branch:** `fix/{{source}}-pk` (e.g., `fix/chembl-activity-pk`)

---

## Example

For `chembl/activity` where docs say `cid` but config says `activity_id`:

```
gh issue create \
  -t "PK mismatch: chembl/activity — cid != activity_id" \
  -l "data-contract,bug,critical" \
  -b "$(cat <<'EOF'
### Problem
Primary key for chembl/activity is inconsistent:

| Layer | File | Line | PK Value |
|-------|------|------|----------|
| Docs | 05-activity-spec.md | L12 | `cid` |
| Config | activity.yaml | L24 | `activity_id` |
| Transformer | activity_transformer.py | L42 | `activity_id` |

### Fix Plan
- [ ] Update 05-activity-spec.md L12 to use `activity_id`
EOF
)"
```

---

## Constraints

- MUST verify each file and line reference exists before creating the issue.
- If no mismatch is found, report "PK consistent for {{source}}" and do NOT create an issue.
- Do NOT auto-fix. This prompt only creates the issue for tracking.
- The canonical PK is always the one in `configs/pipelines/` (runtime source of truth).
