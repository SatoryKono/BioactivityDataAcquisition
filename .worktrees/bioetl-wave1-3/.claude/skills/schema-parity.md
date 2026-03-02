# /schema-parity

Проверка соответствия Silver↔Gold Pandera-схем и primary key coverage в BioETL.

## Использование

```
/schema-parity [action] [target]
```

**Действия:**
- `check` — проверить parity Silver vs Gold (по умолчанию)
- `baseline` — показать/обновить baseline known differences
- `matrix` — вывести матрицу Entity → Silver Schema → Gold Contract
- `drift` — найти schema drift (новые расхождения vs baseline)

**Target (опционально):**
- `all` — все провайдеры (по умолчанию)
- `{provider}` — конкретный провайдер

**Примеры:**
```
/schema-parity                              # проверить все
/schema-parity check chembl                 # только ChEMBL
/schema-parity baseline --update            # обновить baseline
/schema-parity matrix pubmed               # матрица для PubMed
/schema-parity drift                       # найти новый drift
```

---

## Инструкции для Claude

### Действие: `check` (по умолчанию)

**Шаг 1:** Запустить скрипт проверки:
```bash
uv run python src/tools/verify_schema_parity.py --data-dir configs/ 2>&1
```

**Шаг 2:** Если скрипт не запускается, выполнить проверку вручную:

1. Прочитать все Gold schemas из `src/bioetl/domain/contracts/gold/`
2. Прочитать все Silver schemas из `src/bioetl/infrastructure/schemas/silver/`
3. Для каждой пары (Silver, Gold) одного entity:
   - Извлечь набор полей Silver schema
   - Извлечь набор полей Gold contract
   - Найти: поля в Silver но не в Gold, поля в Gold но не в Silver
   - Проверить primary key coverage

**Шаг 3:** Сравнить с baseline:
```bash
cat src/tools/schema_parity_baseline.json
```

Новые расхождения (не в baseline) = BLOCKING.
Известные расхождения (в baseline) = WARNING.

**Шаг 4:** Отчёт:
```
Schema Parity Report
====================
Date: YYYY-MM-DD

| Provider | Entity | Silver Fields | Gold Fields | Missing in Gold | Extra in Gold | PK Coverage | Status |
|----------|--------|:------------:|:-----------:|:---------------:|:-------------:|:-----------:|:------:|
| chembl | activity | 45 | 42 | 3 | 0 | ✅ | ⚠️ |

New mismatches (not in baseline): N → BLOCKING
Known mismatches (in baseline): M → WARNING
```

### Действие: `baseline`

Показать текущий baseline:
```bash
cat src/tools/schema_parity_baseline.json | python -m json.tool
```

При `--update`:
```bash
uv run python src/tools/verify_schema_parity.py --update-baseline
```

### Действие: `matrix`

Для указанного провайдера построить полную матрицу:

1. Domain Entity (`src/bioetl/domain/entities/{provider}.py`) → перечислить поля
2. Silver Schema (`src/bioetl/infrastructure/schemas/silver/`) → перечислить колонки
3. Gold Contract (`src/bioetl/domain/contracts/gold/{provider}.py`) → перечислить поля
4. Показать трёхстороннюю матрицу соответствия

### Действие: `drift`

Найти новые расхождения, отсутствующие в baseline:
```bash
uv run python src/tools/verify_schema_parity.py --strict 2>&1
```

Только новые mismatches = report.
