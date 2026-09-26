______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: ChEMBL Compound Record

**Имя пайплайна:** `chembl_compound_record`
**Провайдер:** `chembl`
**Сущность:** `compound_record`
**Версия схемы:** 1.2.0

______________________________________________________________________

## 1. Описание

Пайплайн извлекает записи соединений (compound records) из API ChEMBL. Compound record связывает молекулу с документом (публикацией), содержа оригинальное название соединения, как оно упоминается в первоисточнике.

**Назначение:** Сопоставление молекул с публикациями и отслеживание оригинальных наименований соединений в научной литературе.

______________________________________________________________________

## 2. Ключевые поля

### Первичный ключ

| Поле        | Тип   | Описание                                                  |
| ----------- | ----- | --------------------------------------------------------- |
| `record_id` | `int` | Уникальный идентификатор записи (суррогатный ключ ChEMBL) |

### Внешние ключи

| Поле             | Тип   | Описание                                     |
| ---------------- | ----- | -------------------------------------------- |
| `molecule_id`    | `str` | FK → Molecule (например, `CHEMBL25`)         |
| `publication_id` | `str` | FK → Publication (например, `CHEMBL1121421`) |
| `src_id`         | `int` | FK → Source (источник данных)                |

### Данные из источника

| Поле              | Тип           | Описание                                     |
| ----------------- | ------------- | -------------------------------------------- |
| `compound_key`    | `str \| None` | Оригинальный ключ соединения в документе     |
| `compound_name`   | `str \| None` | Оригинальное название соединения в документе |
| `src_compound_id` | `str \| None` | ID соединения в исходной базе данных         |

______________________________________________________________________

## 3. Связи с другими сущностями

```
Compound Record (M:1) → Molecule
Compound Record (M:1) → Publication
Compound Record (M:1) → Source
```

**Граф зависимостей:**

- Для полного анализа рекомендуется сначала загрузить `chembl_molecule` и `chembl_publication`
- `src_id` ссылается на источник данных ChEMBL (1 = ChEMBL)

______________________________________________________________________

## 4. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/compound_record_transformer.py`

### Логика трансформации

1. **Primary ID:** `record_id` (int, обязательный)
1. **Нормализация строк:** Все строковые поля обрабатываются через `normalize_to_string()` — trim whitespace, NULL для пустых строк
1. **Преобразование типов:** `record_id` и `src_id` преобразуются через `safe_int()`

### Entity ID

```python
entity_id = f"chembl:{record_id}"
```

______________________________________________________________________

## 5. Валидация

### DQ-правила

| Поле             | Правило       | Описание                    |
| ---------------- | ------------- | --------------------------- |
| `record_id`      | `>= 1`        | Положительное целое число   |
| `molecule_id`    | `^CHEMBL\d+$` | Regex для формата ChEMBL ID |
| `publication_id` | `^CHEMBL\d+$` | Regex для формата ChEMBL ID |
| `src_id`         | `>= 1`        | Положительное целое число   |

### Пороги ошибок

| Порог | Условие      | Действие   |
| ----- | ------------ | ---------- |
| Soft  | > 5% ошибок  | WARNING    |
| Hard  | > 20% ошибок | FAIL BATCH |

______________________________________________________________________

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

______________________________________________________________________

## 7. Фильтрация по Gold

### Обязательные поля для Gold

Записи проходят в Gold слой только при наличии:

- `molecule_id`
- `publication_id`

Конфигурируется в `configs/entities/chembl/compound_record.yaml`:

```yaml
gold_filters:
  required_fields:
    - molecule_id
    - publication_id
```

______________________________________________________________________

## 8. Сортировка

### Silver

| Столбец     | Порядок |
| ----------- | ------- |
| `record_id` | ASC     |

### Gold

| Столбец          | Порядок |
| ---------------- | ------- |
| `molecule_id`    | ASC     |
| `publication_id` | ASC     |
| `record_id`      | ASC     |

______________________________________________________________________

## 9. Связанные файлы

| Компонент     | Путь                                                                     |
| ------------- | ------------------------------------------------------------------------ |
| Конфигурация  | `configs/entities/chembl/compound_record.yaml`                           |
| Трансформер   | `src/bioetl/application/pipelines/chembl/compound_record_transformer.py` |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/pipeline_types.py`              |
| Сущность      | `src/bioetl/domain/entities/chembl_compound_record.py`                   |
| Схема         | `src/bioetl/domain/schemas/chembl/compound_record.py`                    |

______________________________________________________________________

## 10. Примеры данных

### Bronze (сырые данные из API)

```json
{
  "record_id": 1234567,
  "molecule_chembl_id": "CHEMBL25",
  "publication_id": "CHEMBL1121421",
  "compound_key": "Aspirin",
  "compound_name": "acetylsalicylic acid",
  "src_id": 1,
  "src_compound_id": null
}
```

`document_chembl_id` remains a legacy upstream/source alias and is normalized to
`publication_id` by the current pipeline contract.

### Silver (нормализованные данные)

| record_id | molecule_id | publication_id | compound_key | compound_name        | src_id |
| --------- | ----------- | -------------- | ------------ | -------------------- | ------ |
| 1234567   | CHEMBL25    | CHEMBL1121421  | Aspirin      | acetylsalicylic acid | 1      |

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                    |
| -------------------- | ----------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_compound_record_v1.0.json](../../contracts/gold/chembl_compound_record_v1.0.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                        |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)  |

## Compliance

| Контроль          | Статус | Evidence                                                                                                       |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                       |
| Runtime alignment | Pass   | Активный config/runtime surface задокументирован в разделах `Конфигурация`, `Трансформация`, `Связанные файлы` |
| Contract linkage  | Pass   | [chembl_compound_record_v1.0.json](../../contracts/gold/chembl_compound_record_v1.0.json)                      |
| API governance    | Pass   | См. [API Compliance](#api-compliance)                                                                          |

## API Compliance

### Rate limits & retries

Официальная ChEMBL REST Web Services documentation не публикует числовой лимит запросов. EMBL-EBI Terms of Use разрешают ограничивать или отзывать доступ, если использование мешает работе сервиса. Клиент SHOULD использовать консервативный rate limiting и экспоненциальный backoff; точный retry budget — [неуточнено].

### 429 handling policy

Явная HTTP 429 policy в доступной официальной документации ChEMBL — [неуточнено]. При признаках throttling или блокировки клиент SHOULD снижать частоту запросов и прекращать burst-нагрузку.

### Authentication model

Read-only web services документированы как открытые REST endpoints; обязательная аутентификация для чтения в официальной документации не указана.

### ToS URL

- https://www.ebi.ac.uk/about/terms-of-use

### Data license

ChEMBL data are available under the Creative Commons Attribution-ShareAlike 3.0 Unported license (CC BY-SA 3.0).

### Personal data notes

Наборы данных ChEMBL по своей природе не ориентированы на персональные данные. EMBL-EBI Privacy Notice описывает обработку служебных данных доступа и журналов безопасности; API-specific guidance по персональным данным — [неуточнено].

### Official sources

- [ChEMBL REST Web Services](https://www.ebi.ac.uk/chembl/api/data/docs)
- [ChEMBL homepage / license statement](https://www.ebi.ac.uk/chembl/)
- [EMBL-EBI Terms of Use](https://www.ebi.ac.uk/about/terms-of-use)
- [EMBL-EBI Privacy Notice](https://www.ebi.ac.uk/about/privacy-notice)

*Последнее обновление: 2026-03-30*
