# Пайплайн: ChEMBL Target

**Имя пайплайна:** `chembl_target`
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
| `target_id` | `str` | Уникальный ChEMBL ID мишени |
| `pref_name` | `str` | Предпочтительное название |
| `target_type` | `str` | Тип мишени (SINGLE PROTEIN, PROTEIN COMPLEX, etc.) |

### Таксономия

| Поле | Тип | Описание |
|------|-----|----------|
| `organism` | `str` | Название организма |
| `taxonomy_id` | `int` | NCBI Taxonomy ID |
| `species_group_flag` | `bool` | Флаг группы видов |

### Компоненты мишени

| Поле | Тип | Описание |
|------|-----|----------|
| `component_accessions` | `list[str]` | UniProt accessions |
| `component_ids` | `list[int]` | ID компонентов |
| `component_types` | `list[str]` | Типы компонентов |
| `component_descriptions` | `list[str]` | Описания компонентов |
| `component_relationships` | `list[str]` | Тип связи компонента с мишенью |

### Связи

| Поле | Тип | Описание |
|------|-----|----------|
| `cross_references` | `list[str]` | Кросс-ссылки на внешние БД |
| `target_component_synonyms` | `list[str]` | Синонимы названия |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/target_transformer.py`

### Агрегация компонентов

Компоненты мишени (`target_components`) агрегируются в списки:
- `component_accessions`, `component_ids`, `component_types`
- `component_descriptions`, `component_relationships`

### Entity ID

```python
entity_id = f"chembl:{target_id}"
```

---

## 4. Валидация

### DQ-правила

1. **`target_id`** — обязательное
2. **`target_type`** — должен быть валидным типом

### Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок | WARNING |
| Hard | > 20% ошибок | FAIL BATCH |

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline chembl_target

# С ограничением
bioetl run --pipeline chembl_target --limit 500

# Полная перезагрузка
bioetl run --pipeline chembl_target --run-type rebuild
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/target.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/target_transformer.py` |
| Сущность | `src/bioetl/domain/entities.py` |

---

*Последнее обновление: 2026-03-03*
