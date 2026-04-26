______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: ChEMBL Molecule

**Имя пайплайна:** `chembl_molecule`
**Провайдер:** `chembl`
**Сущность:** `molecule`
**Версия схемы:** 1.2.0

______________________________________________________________________

## 1. Описание

Пайплайн извлекает данные о химических соединениях из API ChEMBL. Каждая запись содержит информацию о структуре молекулы, физико-химических свойствах и идентификаторах.

______________________________________________________________________

## 2. Ключевые поля

### Идентификаторы

| Поле            | Тип   | Описание                                      |
| --------------- | ----- | --------------------------------------------- |
| `molecule_id`   | `str` | Уникальный ChEMBL ID (например, `CHEMBL25`)   |
| `pref_name`     | `str` | Предпочтительное название                     |
| `max_phase`     | `int` | Максимальная фаза клинических испытаний (0-4) |
| `molecule_type` | `str` | Тип молекулы (Small molecule, Protein, etc.)  |

### Структурные данные

| Поле               | Тип   | Описание                    |
| ------------------ | ----- | --------------------------- |
| `canonical_smiles` | `str` | Каноническая SMILES-формула |
| `standard_inchi`   | `str` | Стандартный InChI           |
| `inchi_key`        | `str` | Ключ InChI                  |

### Физико-химические свойства

| Поле                   | Тип     | Описание                                |
| ---------------------- | ------- | --------------------------------------- |
| `logp`                 | `float` | Расчётный LogP                          |
| `mw_freebase`          | `float` | Молекулярная масса свободного основания |
| `molecular_weight`     | `float` | Полная молекулярная масса               |
| `hba_count`            | `int`   | Акцепторы водородных связей             |
| `hbd_count`            | `int`   | Доноры водородных связей                |
| `polar_surface_area`   | `float` | Полярная площадь поверхности            |
| `rotatable_bond_count` | `int`   | Вращающиеся связи                       |
| `ro5_violation_count`  | `int`   | Нарушения правила Липински              |
| `heavy_atom_count`     | `int`   | Тяжёлые атомы                           |
| `aromatic_ring_count`  | `int`   | Ароматические кольца                    |
| `qed_score`            | `float` | QED (drug-likeness)                     |

### Иерархия

| Поле                         | Тип   | Описание                 |
| ---------------------------- | ----- | ------------------------ |
| `hierarchy_parent_chembl_id` | `str` | ID родительской молекулы |
| `hierarchy_active_chembl_id` | `str` | ID активной формы        |
| `hierarchy_child_chembl_id`  | `str` | ID дочерней молекулы     |

______________________________________________________________________

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/molecule_transformer.py`

### Развёртывание вложенных структур

- `molecule_hierarchy` → `hierarchy_*` поля
- `molecule_properties` → канонические поля свойств (`logp`, `molecular_weight`, и т.д.)
- `molecule_structures` → структурные поля (`canonical_smiles`, `standard_inchi`, `inchi_key`)

### Entity ID

```python
entity_id = f"chembl:{molecule_id}"
```

______________________________________________________________________

## 4. Валидация

### DQ-правила

1. **`molecule_id`** — обязательное, regex `^CHEMBL\d+$`
1. **`canonical_smiles`** — рекомендуется для анализа

### Пороги ошибок

| Порог | Условие      | Действие   |
| ----- | ------------ | ---------- |
| Soft  | > 5% ошибок  | WARNING    |
| Hard  | > 20% ошибок | FAIL BATCH |

______________________________________________________________________

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline chembl_molecule

# С ограничением
bioetl run --pipeline chembl_molecule --limit 1000

# Полная перезагрузка
bioetl run --pipeline chembl_molecule --run-type rebuild
```

______________________________________________________________________

## 6. Связанные файлы

| Компонент    | Путь                                                              |
| ------------ | ----------------------------------------------------------------- |
| Конфигурация | `configs/entities/chembl/molecule.yaml`                           |
| Трансформер  | `src/bioetl/application/pipelines/chembl/molecule_transformer.py` |
| Сущность     | `src/bioetl/domain/entities/chembl_structures_molecules.py`       |

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_molecule_v1.0.json](../../contracts/gold/chembl_molecule_v1.0.json)              |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

______________________________________________________________________

## Compliance

| Контроль          | Статус | Evidence                                                                                 |
| ----------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Runtime alignment | Pass   | Активные config/code paths перечислены в разделах `Трансформация` и `Связанные файлы`    |
| Contract linkage  | Pass   | [chembl_molecule_v1.0.json](../../contracts/gold/chembl_molecule_v1.0.json)              |
| API governance    | Pass   | См. [API Compliance](#api-compliance)                                                    |

______________________________________________________________________

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
