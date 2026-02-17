# bot-xwalk — Automated Crosswalk Refresh

*Priority: medium | Version: 1.0 | Aligned with RULES.md v5.19*

---

## Goal

Automatically refresh the crosswalk CSV (`{{csv}}`) by re-running the `01-xwalk.md` logic, then sort, dedup, and commit the result as a PR. Designed for automation via `workflow_dispatch` or scheduled runs.

---

## Input

| Parameter | Source | Example |
|-----------|--------|---------|
| `{{source}}` | Argument or "all" | `chembl`, `all` |
| `{{csv}}` | `docs/04-reference/pipelines/{{provider}}/{{entity}}-xwalk.csv` | Existing CSV(s) |

If `{{source}}` = `all`, iterate over all providers in `configs/sources/`.

---

## Output

- **Commit** with updated CSV file(s)
- **PR** with diff summary

---

## Algorithm

### 1. Enumerate targets

```bash
# If source = "all"
for provider_cfg in configs/sources/*.yaml; do
    provider=$(basename "$provider_cfg" .yaml)
    for entity_cfg in configs/pipelines/"$provider"/*.yaml; do
        entity=$(basename "$entity_cfg" .yaml)
        # Skip _base.yaml
        [[ "$entity" == "_base" ]] && continue
        targets+=("$provider/$entity")
    done
done

# If source = specific provider
# targets = all entities for that provider

# If source = provider/entity
# targets = just that one
```

### 2. For each target, execute xwalk logic

Re-apply the algorithm from `01-xwalk.md`:

```
1. Read docs spec → extract field table
2. Read pipeline config → extract primary_keys, fields
3. Read schema config → extract field definitions
4. Read transformer → extract field references
5. Read domain entity → extract dataclass fields
6. Read Gold schema → extract Pandera fields
7. Build unified field set
8. Fill coverage columns
9. Flag mismatches
```

### 3. Sort and dedup

```python
# Sort order:
# 1. primary_key=true first
# 2. Then alphabetically by field name

# Dedup:
# If same field appears multiple times (e.g., from nested + flat),
# merge into single row with NESTED/RENAME note
```

### 4. Write CSV

```python
import csv

COLUMNS = [
    "field", "doc_spec", "cfg_pipeline", "cfg_schema",
    "code_transformer", "code_entity", "code_gold_schema",
    "api_endpoint", "json_type", "nullable", "primary_key", "notes"
]

with open(csv_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(sorted_rows)
```

### 5. Diff and commit

```bash
# Check if anything changed
git diff --stat docs/04-reference/pipelines/

# If changes exist:
git add docs/04-reference/pipelines/**/*-xwalk.csv
git commit -m "chore(xwalk): refresh crosswalk for {{source}}"
```

### 6. Create PR

```bash
gh pr create \
  --title "chore(xwalk): refresh crosswalk for {{source}}" \
  --body "$(cat <<'EOF'
## Summary
Automated crosswalk refresh for {{source}}.

## Changes
{{list of updated CSV files}}

## Statistics
| Provider | Entity | Fields | Mismatches | New | Removed |
|----------|--------|--------|------------|-----|---------|
| ... | ... | ... | ... | ... | ... |

## Triggered by
{{workflow_dispatch / schedule / manual}}
EOF
)"
```

---

## Architecture Compliance

- CSV files MUST be in `docs/04-reference/pipelines/{{provider}}/`
- Field names MUST be snake_case
- Notes vocabulary MUST follow `01-xwalk.md` `{{notes}}` tags
- Sort order MUST be deterministic (primary_key desc, field asc)

---

## Commit & PR Convention (`{{C}}`)

- **Trigger:** `workflow_dispatch` or manual invocation
- **Branch:** `bot/xwalk`
- **PR title:** `chore(xwalk): refresh crosswalk for {{source}}`
- **Labels:** `automation`, `docs`

---

## Idempotency

Running this prompt twice with the same codebase MUST produce identical output. This is enforced by:

1. Deterministic sort (primary_key desc, then field name asc)
2. Deterministic dedup (first occurrence wins for rename merges)
3. Deterministic notes (alphabetically sorted tags if multiple)
4. No timestamps in CSV content (timestamps only in commit message)

---

## Example

For `{{source}}` = `chembl`:

```
$ bot-xwalk chembl

Processing chembl/activity... 30 fields, 2 mismatches
Processing chembl/molecule... 25 fields, 0 mismatches
Processing chembl/target... 15 fields, 1 mismatch
...

Updated 12 CSV files:
  docs/04-reference/pipelines/chembl/activity-xwalk.csv
  docs/04-reference/pipelines/chembl/molecule-xwalk.csv
  ...

Total: 180 fields across 12 entities, 3 mismatches found.
```

---

## Constraints

- MUST be idempotent: same input → same CSV output.
- Only process entities that have both a pipeline config AND a transformer.
- Skip `_base.yaml` and other non-entity config files.
- If a provider has no docs specs, still generate xwalk from cfg+code (with `MISSING_DOC` notes).
- Do NOT modify any source code or config files. Only CSV files in docs/ are written.
