# Пайплайн: ChEMBL Assay Parameters

**Имя пайплайна:** `chembl_assay_parameters`
**Провайдер:** `chembl`
**Сущность:** `assay-parameters`
**Версия схемы:** 1.2.0

---

## 1. Описание

Пайплайн извлекает данные о параметрах экспериментальных анализов из API ChEMBL. Параметры включают условия эксперимента: концентрации, температуру, pH, время инкубации и другие экспериментальные переменные.

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `assay-param-id` | `int` | Уникальный идентификатор параметра |
| `assay-chembl-id` | `str` | ChEMBL ID связанного анализа |

### Тип параметра

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | `str` | Тип параметра (нормализованный к uppercase) |

**Известные типы параметров:**
- `CONC` — концентрация
- `PH` — кислотность
- `TEMP` — температура
- `TIME` — время
- `CELL-COUNT` — количество клеток
- `SERUM` — сыворотка
- `DOSE` — доза
- `VOLUME` — объём
- `WAVELENGTH` — длина волны
- `PERCENT` — процент
- `PRESSURE` — давление
- `HUMIDITY` — влажность
- `PASSAGE` — пассаж
- `CELL-DENSITY` — плотность клеток
- `INCUBATION` — инкубация

### Сырые значения

| Поле | Тип | Описание |
|------|-----|----------|
| `value` | `float` | Числовое значение |
| `text-value` | `str` | Текстовое значение |
| `relation` | `str` | Отношение (=, <, >, etc.) |
| `units` | `str` | Единицы измерения |
| `comments` | `str` | Комментарии |

### Стандартизированные значения

| Поле | Тип | Описание |
|------|-----|----------|
| `standard-value` | `float` | Стандартизированное числовое значение |
| `standard-text-value` | `str` | Стандартизированное текстовое значение |
| `standard-type` | `str` | Стандартизированный тип |
| `standard-relation` | `str` | Стандартизированное отношение |
| `standard-units` | `str` | Стандартизированные единицы |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/assay-parameters-transformer.py`

### Entity ID

```python
entity-id = f"chembl:{assay-param-id}"
```

### Нормализация типа

```python
type = param-type.upper() if param-type else "UNKNOWN"
```

---

## 4. Валидация

### DQ-правила

1. **`assay-param-id`** — обязательное (primary key)
2. **`assay-chembl-id`** — обязательное (foreign key)
3. **`type`** — обязательное

### Gold-фильтры

- Обязательные поля: `assay-chembl-id`, `type`

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl_assay_parameters

# С ограничением
bioetl run chembl_assay_parameters --limit 1000

# С входным фильтром
bioetl run chembl_assay_parameters --input-filter data/input/assay-parameters.csv
```

---

## 6. Партиционирование

Silver-таблица партиционируется по полю `type` для оптимизации запросов по типу параметра.

---

## 7. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/assay-parameters.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/assay-parameters-transformer.py` |
| Пайплайн | `src/bioetl/application/pipelines/chembl/assay-parameters.py` |

---

*Последнее обновление: 2026-01-06*
