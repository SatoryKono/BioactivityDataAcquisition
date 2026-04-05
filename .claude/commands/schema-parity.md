______________________________________________________________________

## description: Проверка Silver↔Gold schema parity и primary key coverage. Действия: check, baseline, matrix, drift. Пример: /schema-parity check chembl

# /schema-parity

Проверка соответствия Silver↔Gold Pandera-схем и primary key coverage.

## Использование

```
/schema-parity [action] [target]
```

**Действия:** `check` (default), `baseline`, `matrix`, `drift`
**Target:** `all` (default), `{provider}`

______________________________________________________________________

## Инструкции

### `check` (default)

1. Run parity script:

```bash
uv run python src/tools/verify_schema_parity.py --data-dir configs/ 2>&1
```

2. If script fails, manual check:

   - Gold schemas: `src/bioetl/domain/contracts/gold/`
   - Silver schemas: `src/bioetl/infrastructure/schemas/silver/`
   - Compare field sets per entity, check PK coverage

1. Compare with baseline:

```bash
cat src/tools/schema_parity_baseline.json
```

New mismatches (not in baseline) = BLOCKING. Known = WARNING.

4. Report:

```
| Provider | Entity | Silver Fields | Gold Fields | Missing in Gold | Extra in Gold | PK Coverage | Status |
```

### `baseline`

```bash
cat src/tools/schema_parity_baseline.json | python -m json.tool
# --update:
uv run python src/tools/verify_schema_parity.py --update-baseline
```

### `matrix`

For provider: extract fields from Domain Entity → Silver Schema → Gold Contract. Show 3-way correspondence.

### `drift`

```bash
uv run python src/tools/verify_schema_parity.py --strict 2>&1
```

Only new mismatches = report.
