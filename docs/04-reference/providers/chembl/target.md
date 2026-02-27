# Пайплайн: ChEMBL Target

**Имя пайплайна:** `chembl-target`
**Провайдер:** `chembl`
**Сущность:** `target`
**Версия схемы:** 1.2.0

---

## 1. Описание

Пайплайн извлекает данные о биологических мишенях из API ChEMBL. Мишени включают белки, нуклеиновые кислоты и другие биомолекулы, на которые направлено действие лекарств.

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `target-chembl-id` | `str` | Уникальный ChEMBL ID мишени |
| `pref-name` | `str` | Предпочтительное название |
| `target-type` | `str` | Тип мишени (SINGLE PROTEIN, PROTEIN COMPLEX, etc.) |

### Таксономия

| Поле | Тип | Описание |
|------|-----|----------|
| `organism` | `str` | Название организма |
| `tax-id` | `int` | NCBI Taxonomy ID |
| `species-group-flag` | `bool` | Флаг группы видов |

### Компоненты мишени

| Поле | Тип | Описание |
|------|-----|----------|
| `component-accessions` | `list[str]` | UniProt accessions |
| `component-ids` | `list[int]` | ID компонентов |
| `component-types` | `list[str]` | Типы компонентов |
| `component-organisms` | `list[str]` | Организмы компонентов |

### Связи

| Поле | Тип | Описание |
|------|-----|----------|
| `cross-references` | `list[str]` | Кросс-ссылки на внешние БД |
| `target-synonyms` | `list[str]` | Синонимы названия |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/target-transformer.py`

### Агрегация компонентов

Компоненты мишени (`target-components`) агрегируются в списки:
- `component-accessions`, `component-ids`, `component-types`
- `component-organisms`

### Entity ID

```python
entity-id = f"chembl:{target-chembl-id}"
```

---

## 4. Валидация

### DQ-правила

1. **`target-chembl-id`** — обязательное
2. **`target-type`** — должен быть валидным типом

### Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок | WARNING |
| Hard | > 20% ошибок | FAIL BATCH |

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl-target

# С ограничением
bioetl run chembl-target --limit 500

# Полная перезагрузка
bioetl run chembl-target --run-type rebuild
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/target.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/target-transformer.py` |
| Сущность | `src/bioetl/domain/entities.py` |

---

*Последнее обновление: 2025-12-27*
