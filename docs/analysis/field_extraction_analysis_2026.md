# Анализ извлекаемых полей пайплайнов BioETL (Январь 2026)

## 1. Сводный отчет

| Пайплайн | Сущность | Статус | Основные проблемы |
|----------|----------|--------|-------------------|
| **PubChem** | Compound | 🔴 Критично | Трансформер игнорирует ~30 полей схемы (физико-химические свойства, 3D, стереохимия). |
| **PubMed** | Publication | 🟠 Внимание | Не извлекаются даты Completed/Revised, потеря связи Автор-Аффилиация. |
| **UniProt** | Target | 🟡 Улучшение | Не извлекаются даты создания/модификации записи и последовательности. |
| **ChEMBL** | Molecule, Activity | 🟢 OK | Соответствует схеме. Декларативный маппинг. |
| **CrossRef** | Publication | 🟢 OK | Соответствует схеме. Сложные поля (ISSN, Domain) извлекаются корректно. |
| **OpenAlex** | Publication | 🟢 OK | Соответствует схеме. |
| **S2** | Publication | 🟢 OK | Соответствует схеме (TLDR, Influential citations присутствуют). |

## 2. Детальный анализ проблемных зон

### PubChem
*   **Файл:** `src/bioetl/application/pipelines/pubchem/transformer.py`
*   **Проблема:** Метод `_transform_impl` создает словарь `business_data` только с базовыми полями (`cid`, `smiles`, `inchi`, `weight`, `formula`).
*   **Упущено:** Поля из `src/bioetl/domain/schemas/pubchem/compound.py`: `xlogp`, `tpsa`, `complexity`, `charge`, `heavy_atom_count`, `h_bond_donor_count`, `h_bond_acceptor_count`, `rotatable_bond_count`, `atom_stereo_count` (и другие stereo), `volume_3d`, `conformer_count_3d`, `feature_*_3d`.
*   **Решение:** Необходимо расширить извлечение, добавив маппинг этих полей из входного JSON (обычно находятся в секции `props` или корневых атрибутах ответа PUG REST).

### PubMed
*   **Файл:** `src/bioetl/application/pipelines/pubmed/transformer.py`
*   **Проблема:** Поля `date_completed` и `date_revised` явно установлены в `None`.
*   **Решение:** Извлечь даты из XML путей `MedlineCitation/DateCompleted` и `MedlineCitation/DateRevised`.

### UniProt
*   **Файл:** `src/bioetl/application/pipelines/uniprot/transformer.py`
*   **Проблема:** Отсутствует маппинг для полей дат.
*   **Решение:**
    *   `sequence_modified` -> из `sequence.lastModified` (нужен парсинг даты).
    *   `entry_created` -> из `entryAudit.firstPublicDate`.
    *   `entry_modified` -> из `entryAudit.lastAnnotationUpdateDate`.

---

## 3. Промпты для модификации

### Промпт 1: Исправление PubChem (Full Extraction)

```text
Задача: Модифицировать трансформер PubChem для полного извлечения полей согласно схеме Silver.

Контекст:
В настоящее время `PubChemCompoundTransformer` (src/bioetl/application/pipelines/pubchem/transformer.py) извлекает только базовые идентификаторы (CID, InChI, SMILES) и массу. Однако схема `PubchemMoleculeSchema` (src/bioetl/domain/schemas/pubchem/compound.py) определяет более 30 дополнительных полей, включая физико-химические свойства (XLogP, TPSA), топологию (H-bonds, Rotatable bonds), стереохимию и 3D-дескрипторы. Эти данные приходят в "сыром" Bronze-записи (ответ PUG REST), но игнорируются трансформером.

Требования:
1. Изучить файл схемы `src/bioetl/domain/schemas/pubchem/compound.py`, чтобы составить полный список целевых полей.
2. Изучить структуру входной записи `BronzeRecord` в `src/bioetl/application/pipelines/pubchem/transformer.py` (предполагая стандартную структуру PUG REST JSON, где свойства лежат в `props` или `count` секциях).
3. Переписать метод `_transform_impl` (или добавить вспомогательные методы извлечения), чтобы заполнить ВСЕ поля, определенные в схеме.
4. Особое внимание уделить:
   - Computed Properties: `xlogp`, `tpsa`, `complexity`, `charge`.
   - Counting Properties: `heavy_atom_count`, `h_bond_donor_count`, `h_bond_acceptor_count`, `rotatable_bond_count`.
   - Stereochemistry: `atom_stereo_count`, `bond_stereo_count`, `defined/undefined` варианты.
   - 3D Properties: `volume_3d`, `conformer_count_3d`, и 3D-фичи (`feature_acceptor_count_3d` и т.д.).
5. Обеспечить корректное приведение типов (int/float) и обработку отсутствующих значений (None), так как не все соединения имеют 3D-структуру или вычисленные свойства.
6. Использовать `flatten_nested_dict` или аналогичные утилиты, если свойства в JSON глубоко вложены, но стараться сохранять плоскую структуру `business_data` для соответствия сущности `PubchemMolecule`.

Цель: Устранить потерю данных и обеспечить 100% покрытие схемы PubChem на этапе трансформации.
```

### Промпт 2: Исправление PubMed (Dates & Metadata)

```text
Задача: Добавить извлечение дат завершения процессинга и ревизии в трансформер PubMed.

Контекст:
В файле `src/bioetl/application/pipelines/pubmed/transformer.py`, метод `_extract_date_data` возвращает `None` для полей `date_completed` и `date_revised` с комментарием, что они труднодоступны. Однако эти даты критичны для отслеживания версионности записей MEDLINE и присутствуют в стандартном XML (элементы `<DateCompleted>` и `<DateRevised>` внутри `<MedlineCitation>`). Схема `PubMedPublicationSchema` требует эти поля.

Требования:
1. Модифицировать `src/bioetl/application/pipelines/pubmed/extractors/date.py` (или создать новый метод в трансформере), добавив логику парсинга элементов `DateCompleted` и `DateRevised`.
   - Структура XML обычно: `<DateCompleted><Year>...</Year><Month>...</Month><Day>...</Day></DateCompleted>`.
2. Обновить `src/bioetl/application/pipelines/pubmed/transformer.py`:
   - В методе `_extract_business_data` (или вызываемом им `_extract_date_data`) использовать новую логику для извлечения этих дат.
   - Преобразовать их в объекты `datetime.date` или ISO-строки (YYYY-MM-DD), как того требует сущность/схема.
3. Убедиться, что при отсутствии дат код не падает, а возвращает `None`.
4. Проверить, что извлечение происходит из закешированного `_cached_xml_root` (или `medline` элемента), чтобы не парсить XML повторно.

Цель: Обеспечить заполнение полей `date_completed` и `date_revised` в Silver-слое для корректного аудита записей PubMed.
```

### Промпт 3: Исправление UniProt (Audit Dates)

```text
Задача: Реализовать извлечение дат аудита и модификации последовательности для UniProt.

Контекст:
Трансформер UniProt (`src/bioetl/application/pipelines/uniprot/transformer.py`) и схема (`UniprotTargetSchema`) рассинхронизированы в части метаданных дат. Схема определяет поля `entry_created`, `entry_modified` и `sequence_modified`, но трансформер их не извлекает, хотя API UniProt предоставляет эту информацию в объекте `entryAudit` и атрибутах последовательности.

Требования:
1. Модифицировать `src/bioetl/application/pipelines/uniprot/transformer.py`:
   - В методе `_add_core_identifiers` (или новом методе `_add_audit_data`) добавить извлечение:
     - `entry_created` <- `entryAudit.firstPublicDate`
     - `entry_modified` <- `entryAudit.lastAnnotationUpdateDate`
     - `entry_version` <- `entryAudit.entryVersion`
   - В методе `_add_sequence_data` добавить извлечение:
     - `sequence_modified` <- `sequence.lastModified` (или из атрибутов sequence объекта).
2. Реализовать парсинг строковых дат (обычно YYYY-MM-DD) в формат `datetime.date`, требуемый схемой.
3. Убедиться, что поля добавляются в словарь `business_data` с ключами, соответствующими `UniprotTarget` dataclass.
4. Проверить файл `src/bioetl/application/pipelines/uniprot/extractors/utils.py` на наличие полезных утилит для дат, при необходимости добавить туда функцию `parse_uniprot_date`.

Цель: Обеспечить полноту метаданных аудита в Silver-таблицах UniProt.
```
