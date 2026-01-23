# Пайплайн: ChEMBL Assay Parameters

**Имя пайплайна:** `chembl_assay_parameters`
**Провайдер:** `chembl`
**Сущность:** `assay_parameters`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает данные о параметрах экспериментальных анализов из API ChEMBL. Параметры включают условия эксперимента: концентрации, температуру, pH, время инкубации и другие экспериментальные переменные.

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `assay_param_id` | `int` | Уникальный идентификатор параметра |
| `assay_chembl_id` | `str` | ChEMBL ID связанного анализа |

### Тип параметра

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | `str` | Тип параметра (нормализованный к uppercase) |

**Известные типы параметров:**
- `CONC` — концентрация
- `PH` — кислотность
- `TEMP` — температура
- `TIME` — время
- `CELL_COUNT` — количество клеток
- `SERUM` — сыворотка
- `DOSE` — доза
- `VOLUME` — объём
- `WAVELENGTH` — длина волны
- `PERCENT` — процент
- `PRESSURE` — давление
- `HUMIDITY` — влажность
- `PASSAGE` — пассаж
- `CELL_DENSITY` — плотность клеток
- `INCUBATION` — инкубация

### Сырые значения

| Поле | Тип | Описание |
|------|-----|----------|
| `value` | `float` | Числовое значение |
| `text_value` | `str` | Текстовое значение |
| `relation` | `str` | Отношение (=, <, >, etc.) |
| `units` | `str` | Единицы измерения |
| `comments` | `str` | Комментарии |

### Стандартизированные значения

| Поле | Тип | Описание |
|------|-----|----------|
| `standard_value` | `float` | Стандартизированное числовое значение |
| `standard_text_value` | `str` | Стандартизированное текстовое значение |
| `standard_type` | `str` | Стандартизированный тип |
| `standard_relation` | `str` | Стандартизированное отношение |
| `standard_units` | `str` | Стандартизированные единицы |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py`

### Entity ID

```python
entity_id = f"chembl:{assay_param_id}"
```

### Нормализация типа

```python
type = param_type.upper() if param_type else "UNKNOWN"
```

---

## 4. Валидация

### DQ-правила

1. **`assay_param_id`** — обязательное (primary key)
2. **`assay_chembl_id`** — обязательное (foreign key)
3. **`type`** — обязательное

### Gold-фильтры

- Обязательные поля: `assay_chembl_id`, `type`

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl_assay_parameters

# С ограничением
bioetl run chembl_assay_parameters --limit 1000

# С входным фильтром
bioetl run chembl_assay_parameters --input-filter data/input/assay_parameters.csv
```

---

## 6. Партиционирование

Silver-таблица партиционируется по полю `type` для оптимизации запросов по типу параметра.

---

## 7. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/assay_parameters.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py` |
| Пайплайн | `src/bioetl/application/pipelines/chembl/assay_parameters.py` |

---

*Последнее обновление: 2026-01-06*
