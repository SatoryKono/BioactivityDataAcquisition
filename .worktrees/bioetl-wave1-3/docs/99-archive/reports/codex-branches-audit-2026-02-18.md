# Аудит Codex-веток — 2026-02-18

> **Дата:** 2026-02-18 09:00–09:26 MSK
> **Базовая ветка:** `main` (6b056eb)
> **Всего веток:** 18 | **Уникальных файлов:** ~267 | **Суммарно:** +12 962 LOC

---

## 1. Инвентаризация веток

| # | Ветка | +/- LOC | Тип | Краткое описание |
|---|-------|---------|-----|------------------|
| 1 | `codex/add-content-hash-configuration-section` | +421/−8 | Config + Code | `content-hash.include/exclude` секции во все schema YAML |
| 2 | `codex/revise-meta-fields-and-add-technical-fields` | +175/−3 | Code + Policy | Расширение мета-полей (`-lookup-method`, `-original-id`, `-source`), identity policy |
| 3 | `codex/refactor-primary-keys-separation-in-configs` | +415/−220 | Config + Schema | Разделение `primary-keys` → `business-primary-keys` + `technical-primary-key` |
| 4 | `codex/define-canonical-schema-source-and-generate-artifacts` | +563/−1 | Code + CI | Генератор schema artifacts (Pandera registry), ADR-036, CI gate |
| 5 | `codex/create-dataframemodel-classes-and-tests` | +215/−28 | Code + Tests | DataFrameModel для composite Gold, `strict="filter"` |
| 6 | `codex/expand-dq-report-schema` | +148/−5 | Code | DQ report provenance: `config-path`, `layer`, `severity`, `decision` |
| 7 | `codex/update-yaml-config-files-with-field-groups` | +946/−15 | Config | `column-groups` (system/business/dq) + silver/gold include-groups |
| 8 | `codex/document-nullability-rules-for-pipelines` | +553/−9 | Config + Code | `key-nullability` policy → quality configs + silver writer validation |
| 9 | `codex/update-schema-configs-and-ci-rules` | +664/−62 | Config + CI | `schema-file` поле в pipeline configs + validation script |
| 10 | `codex/generate-nullable/type-matrix` | +760/−61 | Tools + Docs | Инвентарь JSON field typing, CI gate |
| 11 | `codex/create-legacy-to-canonical-mapping-table` | +195/−50 | Code + ADR | Publication alias mapping (legacy→canonical), ADR-024 update |
| 12 | `codex/create-yaml-configuration-for-pipelines` | +570/−70 | Config + Code | Pipeline contract policy YAML (rename-map, hash-include, merge-keys) |
| 13 | `codex/map--composite--fields-to-baseoutputmetadata` | +307/−32 | Code | Composite metadata → `CompositeOutputExt`, `CompositeSchemaValidationMetadata` |
| 14 | `codex/add-composite-schemas-and-contracts` | +431/−4 | Config + Code | Composite activity/target schemas, 3 новых Pandera класса |
| 15 | `codex/add-hash-policy-document-and-machine-readable-file` | +254/−0 | Config + Policy | Machine-readable hash policy (YAML), snapshot stability tests |
| 16 | `codex/conduct-data-schema-audit-…-pbn8h6` | +2262/−0 | Docs only | Аудит-отчёт (analysis/) |
| 17 | `codex/conduct-data-schema-audit-…-oaswve` | +1468/−0 | Docs only | Аудит-отчёт (architecture/) |
| 18 | `codex/conduct-data-schema-audit-…` | +1615/−0 | Docs only | Аудит-отчёт (archive/) |

---

## 2. Тематические группы

### A. Content Hash & Identity Policy (ветки 1, 2, 15)

**Цель:** Формализовать политику вычисления `content-hash`.

| Ветка | Что делает | Файлы |
|-------|-----------|-------|
| #1 | Добавляет `content-hash.include/exclude` во все schema YAML | 24 schema YAML, `identity-service.py`, `transformations.py`, `config-loader.py` |
| #2 | Расширяет мета-поля, policy doc, `-`-prefix exclusion | `constants.py`, `transformations.py`, RULES.md |
| #15 | Machine-readable hash policy YAML + snapshot tests | `configs/hash-policy/`, тесты |

**Конфликт:** #1 и #2 оба правят `transformations.py` (дополняемый — `content-hash` секция vs `-`-prefix exclusion).
**Перекрытие:** #1 и #15 оба описывают hash include/exclude, но в разных форматах (#1 — секция в schema YAML, #15 — отдельный `hash-policy/` YAML).
**Решение:** Объединить в один, выбрать единый source of truth для hash policy.

---

### B. Schema YAML Configuration (ветки 1, 7, 9)

**Цель:** Обогатить `configs/schemas/{provider}/{entity}.yaml` дополнительными секциями.

| Ветка | Добавляет секцию | Конфликт |
|-------|-----------------|----------|
| #1 | `content-hash:` | Вставка перед `column-groups` |
| #7 | `column-groups:` (развёрнутые) | Заменяет `column-groups: []` |
| #9 | `column-groups:` (другая структура) + silver/gold | Заменяет `column-groups: []` |

**КОНФЛИКТ (CRITICAL):** Ветки #7 и #9 обе заменяют `column-groups: []` на **разные** структуры:
- #7: `system`, `business`, `dq` группы с explicit field lists + `silver.include-groups`
- #9: `system`, `identifiers`, `business` + pattern matching (`^(?!-|.*-id$).+`)

**Файлов в конфликте:** 15 schema YAML (все provider/entity).
**Решение:** Выбрать ОДНУ структуру column-groups, смёржить #1 как дополнительную секцию.

---

### C. Pipeline Config Restructuring (ветки 3, 9, 12)

**Цель:** Расширить `configs/pipelines/{provider}/{entity}.yaml`.

| Ветка | Что добавляет | Файлы |
|-------|--------------|-------|
| #3 | `business-primary-keys`, `technical-primary-key` | 23 pipeline YAML + `pipeline.json` schema |
| #9 | `schema-file` поле (ссылка на schema YAML) | 23 pipeline YAML + `pipeline.json` schema |
| #12 | Новые `configs/contracts/pipelines/` YAML (rename-map, hash) | 21 новых YAML + `base-transformer.py` |

**Конфликт:** #3 и #9 оба правят `configs/-schema/pipeline.json` и все 23 pipeline YAML.
**Перекрытие:** #12 дублирует hash include/exclude (пересекается с группой A).
**Решение:** Последовательно мёржить #3 → #9, разрешая конфликты в pipeline configs. #12 интегрировать после группы A.

---

### D. Composite Pipeline (ветки 5, 13, 14)

**Цель:** Расширить schema и metadata для composite entities.

| Ветка | Что делает | Ключевые файлы |
|-------|-----------|----------------|
| #5 | `strict="filter"` + descriptions в существующих composite schemas | `composite.py`, `storage-adapter.py` |
| #13 | Composite metadata fields → `CompositeOutputExt` | `metadata-coordinator.py`, `metadata.py`, `gold-writer.py` |
| #14 | 3 новых composite schemas (Activity, Assay, Target) + YAML configs | `composite.py`, `storage-adapter.py` |

**КОНФЛИКТ:** #5 и #14 оба правят `composite.py`:
- #5 меняет существующие классы (`strict="filter"`, добавляет descriptions)
- #14 добавляет новые классы (`CompositeActivityGoldSchema`, `CompositeAssayGoldSchema`, `CompositeTargetGoldSchema`) но оставляет `strict=False`

**КОНФЛИКТ:** #5 и #14 оба правят `storage-adapter.py`.
**Решение:** Мёржить #14 → #5 (новые классы + strict="filter" для всех).

---

### E. DQ & Metadata (ветки 6, 8, 13)

**Цель:** Расширить DQ framework и metadata tracking.

| Ветка | Что делает | Ключевые файлы |
|-------|-----------|----------------|
| #6 | Rule provenance в DQ report | `dq-report.py`, `metadata.py`, `metadata-coordinator.py` |
| #8 | Key nullability policy в quality configs | `silver-writer.py`, `dq-config.py`, 21 quality config |
| #13 | Composite output metadata | `metadata.py`, `metadata-coordinator.py` |

**Конфликт:** #6 и #13 оба правят `metadata.py`, `metadata-coordinator.py`, тесты metadata.
**Перекрытие:** #6 и #8 оба правят `dq-report.py`.
**Решение:** #8 независим, мёржить первым. #6 и #13 мёржить последовательно.

---

### F. Schema Generation & CI (ветки 4, 10)

**Цель:** Автогенерация schema artifacts + CI governance gates.

| Ветка | Что делает | CI файлы |
|-------|-----------|----------|
| #4 | `generate-schema-artifacts.py` → Pandera registry, ADR-036 | `schema-governance.yml` |
| #10 | `generate-json-field-typing-inventory.py` → type matrix | `schema-governance.yml` |

**Конфликт:** оба правят `.github/workflows/schema-governance.yml`.
**Решение:** Мёржить последовательно, добавляя оба job в один workflow.

---

### G. Publication Aliases (ветка 11) — изолированная

Добавляет `publication-aliases.py` service, обновляет ADR-024, правит `publication-transformer.py`.
Пересечение с #12 только в `publication-transformer.py`.

---

### H. Аудит-отчёты (ветки 16, 17, 18) — ДУБЛИКАТЫ

Три варианта одного аудит-отчёта в разных директориях:
- `docs/analysis/schema-audit-2026-02-18.md` (+2262)
- `docs/02-architecture/schema-audit-20260218.md` (+1468)
- `docs/99-archive/reports/audit-2026-02-18/schema-audit-report.md` (+1615)

**Решение:** Оставить ОДИН (архивный #18), остальные — DROP.

---

## 3. Матрица конфликтов

```
Файл                                          Ветки             Severity
─────────────────────────────────────────────────────────────────────────
configs/schemas/*/**.yaml (×15)               #1, #7, #9        CRITICAL
  → column-groups: три РАЗНЫЕ структуры
composite.py                                  #5, #14           HIGH
  → strict="filter" vs новые классы + strict=False
storage-adapter.py                            #5, #8, #14       HIGH
  → три разных расширения
metadata.py + metadata-coordinator.py         #6, #13           HIGH
  → rule provenance vs composite metadata
configs/-schema/pipeline.json                 #3, #9            MEDIUM
  → разные новые required fields
configs/pipelines/*/**.yaml (×23)             #3, #9            MEDIUM
  → разные новые поля (PKs vs schema-file)
transformations.py                            #1, #2            MEDIUM
  → content-hash config vs --prefix exclusion
dq-report.py                                  #6, #8            MEDIUM
  → provenance fields vs nullability
.github/workflows/schema-governance.yml       #4, #10           LOW
  → два разных CI job
RULES.md                                      #2, #3            LOW
  → разные секции (meta fields vs PK docs)
publication-transformer.py                    #11, #12          LOW
  → alias compat vs contract policy
```

---

## 4. План консолидации

### Фаза 0: Triage — Drop дубликатов
- **DROP** ветки #16 (`pbn8h6`) и #17 (`oaswve`) — дубликаты аудит-отчёта
- **KEEP** #18 (`conduct-data-schema-audit-for-bioetl-pipelines`) → cherry-pick отчёт в архив

### Фаза 1: Schema Foundation (→ feature branch `schema-governance-phase1`)

**Порядок merge (sequential):**

```
1.  #7  update-yaml-config-files-with-field-groups   ← BASE: column-groups структура
    ↓   DISCARD #9 column-groups (конфликтует, менее детальная)
    ↓   Из #9 взять ТОЛЬКО: schema-file поле в pipeline configs + validation script

2.  #1  add-content-hash-configuration-section        ← content-hash секция поверх #7
    ↓   Конфликт в schema YAML: тривиальный (разные секции файла)

3.  #2  revise-meta-fields-and-add-technical-fields   ← мета-поля + identity policy
    ↓   Конфликт transformations.py: merge обоих изменений

4.  #15 add-hash-policy-document-and-machine-readable ← hash policy YAML (дополняет #1)
```

**Результат:** Единая schema structure + content hash policy + meta fields.

### Фаза 2: Pipeline Config Restructuring (→ `schema-governance-phase2`)

**На базе Фазы 1:**

```
5.  #3  refactor-primary-keys-separation-in-configs   ← business/technical PK split
    ↓
6.  #9  update-schema-configs-and-ci-rules            ← CHERRY-PICK: schema-file + CI
    ↓   НЕ брать column-groups (уже из #7)

7.  #12 create-yaml-configuration-for-pipelines       ← contract policy YAML
    ↓   Проверить: hash-include/exclude не дублирует #1/#15
```

**Результат:** Pipeline configs с PK separation + schema links + contract policies.

### Фаза 3: Composite & DQ (→ `schema-governance-phase3`)

**На базе Фазы 2:**

```
8.  #14 add-composite-schemas-and-contracts           ← новые composite schemas
    ↓
9.  #5  create-dataframemodel-classes-and-tests        ← strict="filter" + descriptions
    ↓   ПРИМЕНИТЬ strict="filter" ко ВСЕМ классам (#14 оставил strict=False)

10. #13 map--composite--fields-to-baseoutputmetadata  ← composite metadata
    ↓
11. #6  expand-dq-report-schema                       ← DQ provenance
    ↓   Конфликт metadata.py: merge composite + provenance fields

12. #8  document-nullability-rules-for-pipelines      ← nullability policy
```

**Результат:** Полная composite pipeline support + DQ framework.

### Фаза 4: Generation & Governance (→ `schema-governance-phase4`)

**На базе Фазы 3:**

```
13. #4  define-canonical-schema-source-and-generate    ← schema artifact generator
    ↓
14. #10 generate-nullable/type-matrix                  ← field typing inventory
    ↓   Конфликт schema-governance.yml: merge оба job

15. #11 create-legacy-to-canonical-mapping-table       ← publication aliases
```

**Результат:** CI governance pipeline + publication compatibility.

### Фаза 5: Documentation (→ `schema-governance-phase5`)

```
16. #18 conduct-data-schema-audit-for-bioetl-pipelines ← архивный аудит-отчёт
```

---

## 5. Оценка рисков

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| Schema YAML merge conflicts (#1/#7/#9) | Высокая | Высокое | Выбрать #7 как base, cherry-pick из #9 |
| composite.py semantic conflict (#5/#14) | Высокая | Среднее | #14 first, apply #5 strict="filter" ко всем |
| Pipeline JSON schema incompatibility (#3/#9) | Средняя | Среднее | Sequential merge, validate JSON schema |
| Hash policy duplication (#1/#12/#15) | Средняя | Низкое | Выбрать canonical source, удалить дубли |
| metadata.py triple-edit (#6/#8/#13) | Средняя | Среднее | Sequential merge с тестами |
| CI workflow merge (#4/#10) | Низкая | Низкое | Тривиальный merge двух job |

---

## 6. Рекомендации

1. **НЕ мёржить все 18 веток по отдельности** — гарантированы конфликты и несогласованность
2. **Создать 4-5 консолидированных feature branches** по фазам выше
3. **Ветки #16, #17 — полностью DROP**, #18 оставить как единственный аудит-отчёт
4. **Ветки #7 и #9** — выбрать #7 column-groups (более детальная), из #9 cherry-pick только CI + schema-file
5. **В composite.py** — применить `strict="filter"` из #5 ко ВСЕМ schema классам (включая новые из #14)
6. **Запускать тесты после каждой фазы**: `pytest tests/architecture/ -v && pytest tests/contract/ -v`
7. **Ожидаемое время:** ~2-3 часа на ручную консолидацию всех фаз

---

*Сгенерировано: Claude Code, 2026-02-18*
