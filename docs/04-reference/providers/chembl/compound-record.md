# Пайплайн: ChEMBL Compound Record

**Имя пайплайна:** `chembl_compound_record`
**Провайдер:** `chembl`
**Сущность:** `compound-record`
**Версия схемы:** 1.2.0

---

## 1. Описание

Пайплайн извлекает записи соединений (compound records) из API ChEMBL. Compound record связывает молекулу с документом (публикацией), содержа оригинальное название соединения, как оно упоминается в первоисточнике.

**Назначение:** Сопоставление молекул с публикациями и отслеживание оригинальных наименований соединений в научной литературе.

---

## 2. Ключевые поля

### Первичный ключ

| Поле | Тип | Описание |
|------|-----|----------|
| `record-id` | `int` | Уникальный идентификатор записи (суррогатный ключ ChEMBL) |

### Внешние ключи

| Поле | Тип | Описание |
|------|-----|----------|
| `molecule-chembl-id` | `str` | FK → Molecule (например, `CHEMBL25`) |
| `document-chembl-id` | `str` | FK → Publication (например, `CHEMBL1121421`) |
| `src-id` | `int` | FK → Source (источник данных) |

### Данные из источника

| Поле | Тип | Описание |
|------|-----|----------|
| `compound-key` | `str \| None` | Оригинальный ключ соединения в документе |
| `compound-name` | `str \| None` | Оригинальное название соединения в документе |
| `src-compound-id` | `str \| None` | ID соединения в исходной базе данных |

---

## 3. Связи с другими сущностями

```
Compound Record (M:1) → Molecule
Compound Record (M:1) → Publication
Compound Record (M:1) → Source
```

**Граф зависимостей:**
- Для полного анализа рекомендуется сначала загрузить `chembl_molecule` и `chembl_publication`
- `src-id` ссылается на источник данных ChEMBL (1 = ChEMBL)

---

## 4. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/compound_record_transformer.py`

### Логика трансформации

1. **Primary ID:** `record-id` (int, обязательный)
2. **Нормализация строк:** Все строковые поля обрабатываются через `normalize-to-string()` — trim whitespace, NULL для пустых строк
3. **Преобразование типов:** `record-id` и `src-id` преобразуются через `safe-int()`

### Entity ID

```python
entity-id = f"chembl:{record-id}"
```

---

## 5. Валидация

### DQ-правила

| Поле | Правило | Описание |
|------|---------|----------|
| `record-id` | `>= 1` | Положительное целое число |
| `molecule-chembl-id` | `^CHEMBL\d+$` | Regex для формата ChEMBL ID |
| `document-chembl-id` | `^CHEMBL\d+$` | Regex для формата ChEMBL ID |
| `src-id` | `>= 1` | Положительное целое число |

### Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок | WARNING |
| Hard | > 20% ошибок | FAIL BATCH |

---

## 6. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline chembl_compound_record

# С ограничением количества записей
bioetl run --pipeline chembl_compound_record --limit 1000

# Полная перезагрузка
bioetl run --pipeline chembl_compound_record --run-type rebuild

# Dry-run (без записи)
bioetl run --pipeline chembl_compound_record --dry-run
```

---

## 7. Фильтрация по Gold

### Обязательные поля для Gold

Записи проходят в Gold слой только при наличии:
- `molecule-chembl-id`
- `document-chembl-id`

Конфигурируется в `configs/entities/chembl/compound_record.yaml`:

```yaml
gold_filters:
  required_fields:
    - molecule-chembl-id
    - document-chembl-id
```

---

## 8. Сортировка

### Silver

| Столбец | Порядок |
|---------|---------|
| `record-id` | ASC |

### Gold

| Столбец | Порядок |
|---------|---------|
| `molecule-chembl-id` | ASC |
| `document-chembl-id` | ASC |
| `record-id` | ASC |

---

## 9. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/compound_record.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/compound_record_transformer.py` |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/_pipelines.py` |
| Сущность | `src/bioetl/domain/entities/chembl_compound_record.py` |
| Схема | `src/bioetl/domain/schemas/chembl/compound_record.py` |

---

## 10. Примеры данных

### Bronze (сырые данные из API)

```json
{
  "record-id": 1234567,
  "molecule-chembl-id": "CHEMBL25",
  "document-chembl-id": "CHEMBL1121421",
  "compound-key": "Aspirin",
  "compound-name": "acetylsalicylic acid",
  "src-id": 1,
  "src-compound-id": null
}
```

### Silver (нормализованные данные)

| record-id | molecule-chembl-id | document-chembl-id | compound-key | compound-name | src-id |
|-----------|--------------------|--------------------|--------------|---------------|--------|
| 1234567 | CHEMBL25 | CHEMBL1121421 | Aspirin | acetylsalicylic acid | 1 |

---

*Последнее обновление: 2025-01-05*
