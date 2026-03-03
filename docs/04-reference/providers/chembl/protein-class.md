# Пайплайн: ChEMBL Protein Class

**Имя пайплайна:** `chembl_protein_class`
**Провайдер:** `chembl`
**Сущность:** `protein-class`
**Версия схемы:** 1.2.0

---

## 1. Описание

Пайплайн извлекает иерархическую классификацию белков из API ChEMBL. Справочная таблица (~1,500 записей) содержит классы ферментов, типы рецепторов и другие категории белков. Используется для аннотации таргетов.

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `protein-class-id` | `int` | Уникальный идентификатор класса |
| `parent-id` | `int` | ID родительского класса (иерархия) |

### Иерархия

| Поле | Тип | Описание |
|------|-----|----------|
| `class-level` | `int` | Уровень в иерархии (1 = корень) |
| `sort-order` | `int` | Порядок сортировки внутри уровня |

### Классификация

| Поле | Тип | Описание |
|------|-----|----------|
| `pref_name` | `str` | Предпочтительное название |
| `short-name` | `str` | Короткое название |
| `protein-class-desc` | `str` | Описание класса |
| `definition` | `str` | Определение класса |

### Метаданные

| Поле | Тип | Описание |
|------|-----|----------|
| `downgraded` | `int` | Флаг устаревшей записи (0/1) |
| `replaced-by` | `int` | ID заменяющего класса |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/protein_class_transformer.py`

### Entity ID

```python
entity_id = f"chembl:{protein-class-id}"
```

### Иерархическая структура

```
parent-id → protein-class-id
```

Корневые классы имеют `parent-id = None`.

---

## 4. Валидация

### DQ-правила

1. **`protein-class-id`** — обязательное (primary key)
2. **`pref_name`** — обязательное (название класса)

### Gold-фильтры

- Обязательные поля: `pref_name`
- Фильтр `downgraded = 0` — исключение устаревших записей

---

## 5. Использование CLI

```bash
# Полная загрузка (справочная таблица)
bioetl run --pipeline chembl_protein_class

# С ограничением
bioetl run --pipeline chembl_protein_class --limit 500
```

---

## 6. Стратегия загрузки

**Full load** — справочная таблица загружается полностью при каждом запуске. Входной фильтр отключён (`input-filter.enabled: false`).

---

## 7. Партиционирование

Silver-таблица партиционируется по полю `class-level` для оптимизации иерархических запросов.

Gold-таблица сортируется по `class-level`, `sort-order`, `protein-class-id`.

---

## 8. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/protein_class.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/protein_class_transformer.py` |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/_pipelines.py` |

---

*Последнее обновление: 2026-01-06*
