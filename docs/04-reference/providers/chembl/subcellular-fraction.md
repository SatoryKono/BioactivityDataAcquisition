______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: ChEMBL Subcellular Fraction

**Имя пайплайна:** `chembl_subcellular_fraction`
**Провайдер:** `chembl`
**Сущность:** `subcellular_fraction`
**Версия схемы:** 1.0.0

______________________________________________________________________

## 1. Описание

Пайплайн извлекает данные о субклеточных фракциях из API ChEMBL. Субклеточные фракции представляют собой специфические клеточные компартменты (митохондрии, ядро, микросомы и т.д.), используемые в экспериментах.

Это **производная сущность** (derived entity), извлекаемая из поля `assay_subcellular_fraction` записей `chembl_assay`.

**Источник данных:** ChEMBL REST API, производная таблица из `assay`

______________________________________________________________________

## 2. Ключевые поля

### Идентификаторы

| Поле                   | Тип   | Описание                               |
| ---------------------- | ----- | -------------------------------------- |
| `subcellular_fraction` | `str` | Название фракции (PK, нормализованное) |

### Статистика

| Поле               | Тип   | Описание                                       |
| ------------------ | ----- | ---------------------------------------------- |
| `assay_count`      | `int` | Количество ассеев, использующих данную фракцию |
| `example_assay_id` | `str` | Ссылка на пример ассея                         |

______________________________________________________________________

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/subcellular_fraction_transformer.py`

### Основные операции

1. Извлечение уникальных значений `assay_subcellular_fraction` из данных ассеев
1. Подсчёт количества ассеев для каждой фракции
1. Выбор примера ассея для каждой фракции

______________________________________________________________________

## 4. Конфигурация

| Параметр      | Путь                                                                 |
| ------------- | -------------------------------------------------------------------- |
| Entity config | `configs/entities/chembl/subcellular_fraction.yaml`                  |
| Pipeline spec | `docs/04-reference/pipelines/chembl/14-subcellular-fraction-spec.md` |

______________________________________________________________________

## 5. Применение

- **Компартментный анализ**: Изучение эффектов лекарств на митохондриальные или микросомальные ферменты
- **Обогащение ассеев**: Группировка ассеев по используемой субклеточной фракции
- **Справочная таблица**: Уникальный список фракций для фильтрации и анализа

______________________________________________________________________

## 6. Связи

| Связь    | Сущность       | Описание                              |
| -------- | -------------- | ------------------------------------- |
| Источник | `chembl_assay` | Фракции извлекаются из записей ассеев |

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                              |
| -------------------- | --------------------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_subcellular_fraction_v1.0.json](../../contracts/gold/chembl_subcellular_fraction_v1.0.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                                  |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)            |

## Compliance

| Контроль          | Статус | Evidence                                                                                                       |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                       |
| Runtime alignment | Pass   | Активный config/runtime surface задокументирован в разделах `Конфигурация`, `Трансформация`, `Связанные файлы` |
| Contract linkage  | Pass   | [chembl_subcellular_fraction_v1.0.json](../../contracts/gold/chembl_subcellular_fraction_v1.0.json)            |
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
