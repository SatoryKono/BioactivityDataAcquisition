# Merge Plan: 4 ветки с содержательными изменениями

**Дата:** 2026-02-20
**Автор:** Claude Code

---

## Граф зависимостей

```
main
 └── data-normalization-comparison-kK6Pp  (17 коммитов, база)
      │
      ├──[PR #2181]──► audit-config-files-7li0g  (+8 уникальных коммитов)
      │                    │
      │                    └──► document-pipeline-enums-y4nVS  (+6 уникальных коммитов)
      │
      └──► standardize-molecule-fields-OFKKu  (+1 уникальный коммит)
```

**Ключевое открытие:** ветки НЕ являются независимыми. Они образуют цепочку:

- `data-normalization` — базовая ветка, предок для всех остальных
- `audit-config-files` — надмножество `data-normalization` (уже включает её через PR #2181)
- `document-pipeline-enums` — надмножество `audit-config-files` (включает все коммиты)
- `standardize-molecule-fields` — ответвление от `data-normalization` с 1 уникальным коммитом

---

## Оптимальный порядок merge

### Вариант A: Минимальный (рекомендуемый) — 2 merge вместо 4

| Шаг | Ветка | Действие | Обоснование |
|-----|-------|----------|-------------|
| 1 | `document-pipeline-enums-y4nVS` | **MERGE** | Содержит ВСЕ коммиты из `data-normalization` и `audit-config-files` + 6 своих |
| 2 | `standardize-molecule-fields-OFKKu` | **MERGE** | Только 1 уникальный коммит (field alias registry) |
| — | `data-normalization-comparison-kK6Pp` | **SKIP** | Полностью содержится в `document-pipeline-enums` |
| — | `audit-config-files-7li0g` | **SKIP** | Полностью содержится в `document-pipeline-enums` |

### Вариант B: Последовательный — 4 merge (если нужен гранулярный review)

| Шаг | Ветка | Уникальных коммитов |
|-----|-------|---------------------|
| 1 | `data-normalization-comparison-kK6Pp` | 17 |
| 2 | `audit-config-files-7li0g` | 8 (после шага 1 — fast-forward) |
| 3 | `document-pipeline-enums-y4nVS` | 6 (после шага 2 — fast-forward) |
| 4 | `standardize-molecule-fields-OFKKu` | 1 (конфликты минимальны после шага 1) |

---

## Шаг 1: Merge `document-pipeline-enums-y4nVS` (28 коммитов)

### Что входит

Объединяет работу из трёх веток:

**Из data-normalization (RF-NORM-01..07):**
- Анализ расхождений в нормализации между провайдерами
- `domain/value_objects/inchi.py` — InChI value object
- `domain/value_objects/molecular_descriptors.py` — Molecular descriptors
- `domain/schemas/common/molecule_base.py` — Base molecule schema
- `domain/registry/field_aliases.py` — Field alias registry
- `domain/schemas/constants.py` — Canonical validation bounds
- Исправление CrossRef `entity_type: work` → `publication`

**Из audit-config-files:**
- `domain/ports/data_normalization.py` — Normalization port
- `domain/services/data_normalization_service.py` — Normalization service
- `application/pipelines/common/base_publication_transformer.py` — Base transformer
- Удаление 17 root-артефактов, очистка `.github/root-allowlist.txt`
- Удаление `isort` и `detect-secrets` из `.pre-commit-config.yaml`
- Консолидация YAML-конфигов

**Уникальные (enum externalization, ADR-035):**
- `configs/enums/chembl.yaml` — ChEMBL enum SSOT (164 строки)
- `tests/unit/domain/schemas/test_constants_yaml.py` — 173 строки sync-тестов
- `docs/02-architecture/decisions/ADR-035-enum-externalization.md`
- Домен остаётся pure Python, YAML только для reference

### Конфликты с main

| Файл | Тип | Сложность |
|------|-----|-----------|
| `CHANGELOG.md` | Оба добавили записи | Низкая — объединить записи |
| `configs/pipelines/crossref/publication.yaml` | schema_file reference | Низкая — сохранить main |
| `docs/00-project/ARCHITECTURE_AUDIT_2026-02-16.md` | Разные метрики | Низкая — взять newer |
| `configs/schemas/composite/field_groups/publication.yaml` | Структура | Низкая |

**Сложность разрешения:** НИЗКАЯ — все конфликты в документации и конфигах.

### Риски

| Риск | Severity | Митигация |
|------|----------|-----------|
| CrossRef entity_type change (work→publication) | HIGH | Существующие данные silver/crossref/work/ не будут видны. Нужна миграция |
| Удаление isort из pre-commit | MEDIUM | Проверить, нет ли зависимости в CI |
| Удаление 9 test-файлов | MEDIUM | Проверить coverage ≥85% |
| 11 VCR-файлов в корне repo | LOW | Уже исправлено в последнем коммите |

### Команды merge

```bash
git checkout main
git merge origin/claude/document-pipeline-enums-y4nVS --no-ff -m "Merge: enum externalization, normalization unification, config audit"
# Разрешить конфликты в CHANGELOG.md и configs/
# Затем:
pytest tests/architecture/ -v
pytest --cov=src/bioetl --cov-fail-under=85
mypy --strict src/bioetl/
```

---

## Шаг 2: Merge `standardize-molecule-fields-OFKKu` (1 уникальный коммит)

### Что входит

Единственный уникальный коммит: `8b23e5234 feat: add canonical field alias registry for molecule field normalization (RF-NORM-01)`

- `configs/pipelines/composite/molecule.yaml` — 37 строк `field_aliases` секции
- `application/composite/column_renamer.py` — параметр `field_aliases` в `rename_dataframe()`
- `application/composite/merger.py` — интеграция aliases в merge
- `tests/unit/application/composite/test_column_renamer.py` — 7 новых тестов
- `tests/unit/domain/registry/test_field_aliases.py` — 39 тестов

### Конфликты после шага 1

| Файл | Ожидание |
|------|---------|
| `domain/registry/field_aliases.py` | Возможен — обе ветки добавляют этот файл |
| `domain/registry/__init__.py` | Вероятен — оба модифицируют exports |
| `CHANGELOG.md` | Вероятен — дополнительные записи |

**Сложность:** НИЗКАЯ-СРЕДНЯЯ — один коммит, изменения сфокусированы на field alias registry.

### Команды merge

```bash
git merge origin/claude/standardize-molecule-fields-OFKKu --no-ff -m "Merge: canonical field alias registry for molecule normalization"
# Разрешить конфликты в field_aliases.py (взять более полную версию)
pytest tests/unit/domain/registry/ -v
pytest tests/unit/application/composite/ -v
```

---

## Post-merge чеклист

### Обязательные проверки

```bash
# 1. Архитектурные тесты
pytest tests/architecture/ -v

# 2. Coverage ≥85%
pytest --cov=src/bioetl --cov-fail-under=85

# 3. Type checking
mypy --strict src/bioetl/

# 4. Lint
ruff check src/bioetl/

# 5. YAML-Python enum sync
pytest tests/unit/domain/schemas/test_constants_yaml.py -v

# 6. Field alias tests
pytest tests/unit/domain/registry/test_field_aliases.py -v

# 7. Contract schemas
pytest tests/contract/ -v
```

### Ручные проверки

- [ ] Убедиться, что VCR-файлы НЕ в корне репозитория
- [ ] Проверить, что `run_extract.bat` нужен (или удалить)
- [ ] Документировать миграцию CrossRef данных (silver/crossref/work/ → publication/)
- [ ] Обновить developer guide если isort удалён из workflow
- [ ] Проверить что `reproduce_error.py` действительно не нужен

### Ветки после merge

После успешного merge можно удалить все 4 ветки:
```bash
git push origin --delete claude/data-normalization-comparison-kK6Pp
git push origin --delete claude/audit-config-files-7li0g
git push origin --delete claude/document-pipeline-enums-y4nVS
git push origin --delete claude/standardize-molecule-fields-OFKKu
```

---

## Сводная таблица

| Метрика | Значение |
|---------|---------|
| Всего уникальных коммитов | 32 (17 + 8 + 6 + 1) |
| Новых файлов | ~15 |
| Изменённых файлов | ~70 |
| Удалённых файлов | ~12 |
| Новых тестов | ~250 строк |
| Новой документации | ~1500 строк |
| Ожидаемых конфликтов | 5-8 файлов (все разрешимые) |
| Оптимальное кол-во merge операций | **2** |
