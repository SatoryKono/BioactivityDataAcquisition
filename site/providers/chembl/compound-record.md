# Пайплайн: ChEMBL Compound Record

**Имя пайплайна:** `chembl_compound_record`
**Провайдер:** `chembl`
**Сущность:** `compound_record`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает записи соединений (compound records) из API ChEMBL. Compound record связывает молекулу с документом (публикацией), содержа оригинальное название соединения, как оно упоминается в первоисточнике.

**Назначение:** Сопоставление молекул с публикациями и отслеживание оригинальных наименований соединений в научной литературе.

---

## 2. Ключевые поля

### Первичный ключ

| Поле | Тип | Описание |
|------|-----|----------|
| `record_id` | `int` | Уникальный идентификатор записи (суррогатный ключ ChEMBL) |

### Внешние ключи

| Поле | Тип | Описание |
|------|-----|----------|
| `molecule_chembl_id` | `str` | FK → Molecule (например, `CHEMBL25`) |
| `document_chembl_id` | `str` | FK → Publication (например, `CHEMBL1121421`) |
| `src_id` | `int` | FK → Source (источник данных) |

### Данные из источника

| Поле | Тип | Описание |
|------|-----|----------|
| `compound_key` | `str \| None` | Оригинальный ключ соединения в документе |
| `compound_name` | `str \| None` | Оригинальное название соединения в документе |
| `src_compound_id` | `str \| None` | ID соединения в исходной базе данных |

---

## 3. Связи с другими сущностями

```
Compound Record (M:1) → Molecule
Compound Record (M:1) → Document (Publication)
Compound Record (M:1) → Source
```

**Граф зависимостей:**
- Для полного анализа рекомендуется сначала загрузить `chembl_molecule` и `chembl_document`
- `src_id` ссылается на источник данных ChEMBL (1 = ChEMBL)

---

## 4. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/compound_record_transformer.py`

### Логика трансформации

1. **Primary ID:** `record_id` (int, обязательный)
2. **Нормализация строк:** Все строковые поля обрабатываются через `normalize_to_string()` — trim whitespace, NULL для пустых строк
3. **Преобразование типов:** `record_id` и `src_id` преобразуются через `safe_int()`

### Entity ID

```python
entity_id = f"chembl:{record_id}"
```

---

## 5. Валидация

### DQ-правила

| Поле | Правило | Описание |
|------|---------|----------|
| `record_id` | `>= 1` | Положительное целое число |
| `molecule_chembl_id` | `^CHEMBL\d+$` | Regex для формата ChEMBL ID |
| `document_chembl_id` | `^CHEMBL\d+$` | Regex для формата ChEMBL ID |
| `src_id` | `>= 1` | Положительное целое число |

### Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок | WARNING |
| Hard | > 20% ошибок | FAIL BATCH |

---

## 6. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl_compound_record

# С ограничением количества записей
bioetl run chembl_compound_record --limit 1000

# Полная перезагрузка
bioetl run chembl_compound_record --run-type rebuild

# Dry-run (без записи)
bioetl run chembl_compound_record --dry-run
```

---

## 7. Фильтрация по Gold

### Обязательные поля для Gold

Записи проходят в Gold слой только при наличии:
- `molecule_chembl_id`
- `document_chembl_id`

Конфигурируется в `configs/pipelines/chembl/compound_record.yaml`:

```yaml
gold_filters:
  required_fields:
    - molecule_chembl_id
    - document_chembl_id
```

---

## 8. Сортировка

### Silver

| Столбец | Порядок |
|---------|---------|
| `record_id` | ASC |

### Gold

| Столбец | Порядок |
|---------|---------|
| `molecule_chembl_id` | ASC |
| `document_chembl_id` | ASC |
| `record_id` | ASC |

---

## 9. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/compound_record.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/compound_record_transformer.py` |
| Пайплайн | `src/bioetl/application/pipelines/chembl/compound_record.py` |
| Сущность | `src/bioetl/domain/entities/chembl_compound_record.py` |
| Схема | `src/bioetl/domain/schemas/chembl/compound_record.py` |

---

## 10. Примеры данных

### Bronze (сырые данные из API)

```json
{
  "record_id": 1234567,
  "molecule_chembl_id": "CHEMBL25",
  "document_chembl_id": "CHEMBL1121421",
  "compound_key": "Aspirin",
  "compound_name": "acetylsalicylic acid",
  "src_id": 1,
  "src_compound_id": null
}
```

### Silver (нормализованные данные)

| record_id | molecule_chembl_id | document_chembl_id | compound_key | compound_name | src_id |
|-----------|--------------------|--------------------|--------------|---------------|--------|
| 1234567 | CHEMBL25 | CHEMBL1121421 | Aspirin | acetylsalicylic acid | 1 |

---

*Последнее обновление: 2025-01-05*
