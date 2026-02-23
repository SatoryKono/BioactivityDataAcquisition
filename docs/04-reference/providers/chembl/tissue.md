# Пайплайн: ChEMBL Tissue

**Имя пайплайна:** `chembl_tissue`
**Провайдер:** `chembl`
**Сущность:** `tissue`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает данные о тканях и анатомических локациях из API ChEMBL. Ткани используются как контекст для описания условий экспериментов (assays). Сущность Tissue имеет связь 1:N с Assay (через FK `assay.tissue-id`).

**Источник данных:** ChEMBL REST API, эндпоинт `/tissue`

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `tissue-id` | `str` | Уникальный ChEMBL ID ткани (PK, формат `CHEMBL\d+`) |
| `pref-name` | `str` | Предпочтительное название ткани |

### Онтологические ссылки

| Поле | Тип | Описание |
|------|-----|----------|
| `bto-id` | `str` | Brenda Tissue Ontology ID (формат: `BTO:0000000`) |
| `caloha-id` | `str` | CALIPHO tissue ID (формат: `TS-0000`) |
| `efo-id` | `str` | EFO ontology ID (формат: `EFO:0000000`) |
| `uberon-id` | `str` | UBERON anatomy ontology ID (формат: `UBERON:0000000`) |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/tissue-transformer.py`

### Нормализация данных

- **pref-name:** Строка нормализуется через `normalize-to-string()` (strip whitespace)
- **Онтологические ID:** Пустые строки и whitespace преобразуются в `NULL`
- **tissue-id:** Валидируется через regex `^CHEMBL\d+$`

### Entity ID

```python
entity-id = f"chembl:{tissue-id}"
```

---

## 4. Валидация

### DQ-правила

1. **`tissue-id`** — обязательное, формат `^CHEMBL\d+$`
2. **`pref-name`** — обязательное, длина 1-200 символов
3. **`bto-id`** — если указан, формат `^BTO:\d{7}$`
4. **`caloha-id`** — если указан, формат `^TS-\d{4}$`
5. **`efo-id`** — если указан, формат `^EFO:\d{7}$`
6. **`uberon-id`** — если указан, формат `^UBERON:\d{7}$`

### Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок | WARNING |
| Hard | > 20% ошибок | FAIL BATCH |

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl_tissue

# С ограничением количества записей
bioetl run chembl_tissue --limit 500

# Полная перезагрузка
bioetl run chembl_tissue --run-type rebuild
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/tissue.yaml` |
| DQ Rules | `configs/quality/entities/chembl/tissue.yaml` |
| Схема | `configs/schemas/chembl/tissue.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/tissue-transformer.py` |

---

## 7. Связи с другими сущностями

```
Tissue (tissue-id)
    └── Assay (tissue-id FK) [1:N]
        └── Activity [1:N]
```

---

## 8. Примеры данных

### Bronze (raw JSON)

```json
{
  "tissue-chembl-id": "CHEMBL3638186",
  "pref-name": "Liver",
  "bto-id": "BTO:0000759",
  "caloha-id": "TS-0564",
  "efo-id": "EFO:0000887",
  "uberon-id": "UBERON:0002107"
}
```

### Silver (нормализованный)

| tissue-id | pref-name | bto-id | uberon-id |
|-----------|-----------|--------|-----------|
| CHEMBL3638186 | Liver | BTO:0000759 | UBERON:0002107 |

---

*Последнее обновление: 2026-02-17*
