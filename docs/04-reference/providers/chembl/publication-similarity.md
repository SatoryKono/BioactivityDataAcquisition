______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: ChEMBL Publication Similarity

**Имя пайплайна:** `chembl_publication_similarity`
**Провайдер:** `chembl`
**Сущность:** `publication_similarity`
**Версия схемы:** 1.2.0

______________________________________________________________________

## 1. Описание

Пайплайн извлекает данные о сходстве публикаций (коэффициенты Танимото) из API ChEMBL. Используется для анализа связей между научными публикациями на основе молекулярного и таргетного сходства. Endpoint API остаётся `/document-similarity`.

______________________________________________________________________

## 2. Ключевые поля

### Идентификаторы

| Поле         | Тип   | Описание                                 |
| ------------ | ----- | ---------------------------------------- |
| `sim_id`     | `int` | Уникальный идентификатор записи сходства |
| `doc_1`      | `int` | ID первой публикации                     |
| `doc_2`      | `int` | ID второй публикации                     |
| `pubmed_id1` | `int` | PubMed ID первой публикации              |
| `pubmed_id2` | `int` | PubMed ID второй публикации              |

### Коэффициенты Танимото

| Поле       | Тип     | Описание                            |
| ---------- | ------- | ----------------------------------- |
| `tid_tani` | `float` | Коэффициент Танимото по таргетам    |
| `mol_tani` | `float` | Коэффициент Танимото по молекулам   |
| `avg_tani` | `float` | Среднее значение (вычисляемое)      |
| `max_tani` | `float` | Максимальное значение (вычисляемое) |

______________________________________________________________________

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/publication_similarity_transformer.py`

### Entity ID

```python
entity_id = f"chembl:{sim_id}"
```

### Вычисляемые метрики

```python
avg_tani = round((tid_tani + mol_tani) / 2, 6)
max_tani = round(max(tid_tani, mol_tani), 6)
```

Если один из коэффициентов отсутствует, используется доступное значение.

### Нормализация

`publication_similarity` не имеет отдельного `similarity_type` enum в текущей
schema/config surface. Тип сходства представлен числовыми metric columns:
`tid_tani`, `mol_tani`, `avg_tani`, `max_tani`. Нормализация профиля
канонизирует `pubmed_id1` и `pubmed_id2` как PMID, `sim_id`/`doc_1`/`doc_2`
как integer-like fields, и Tanimoto metrics как finite float semantics.
Если отдельный controlled vocabulary field появится в будущей schema, его нужно
добавить в `configs/enums/chembl.yaml`, Pandera schema и normalization profile
одним изменением.

______________________________________________________________________

## 4. Валидация

### DQ-правила

1. **`sim_id`** — обязательное
1. **`doc_1`**, **`doc_2`** — обязательные (foreign keys)

### Gold-фильтры

- `max_tani >= 0.5` — только значимые связи попадают в Gold
- Обязательные поля: `sim_id`, `doc_1`, `doc_2`

______________________________________________________________________

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline chembl_publication_similarity

# С ограничением
bioetl run --pipeline chembl_publication_similarity --limit 1000
```

______________________________________________________________________

## 6. Связанные файлы

| Компонент     | Путь                                                                            |
| ------------- | ------------------------------------------------------------------------------- |
| Конфигурация  | `configs/entities/chembl/publication_similarity.yaml`                           |
| Трансформер   | `src/bioetl/application/pipelines/chembl/publication_similarity_transformer.py` |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/_pipelines.py`                         |

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_publication_similarity_v1.0.json](../../contracts/gold/chembl_publication_similarity_v1.0.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                                      |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)                |

## Compliance

| Контроль          | Статус | Evidence                                                                                                       |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                       |
| Runtime alignment | Pass   | Активный config/runtime surface задокументирован в разделах `Конфигурация`, `Трансформация`, `Связанные файлы` |
| Contract linkage  | Pass   | [chembl_publication_similarity_v1.0.json](../../contracts/gold/chembl_publication_similarity_v1.0.json)        |
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
