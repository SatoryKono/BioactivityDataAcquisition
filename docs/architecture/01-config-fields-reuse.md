# 01 Config Fields Reuse

## Проблема

В конфигурациях пайплайнов ChEMBL наблюдается дублирование определений полей для связанных сущностей:

- `target_chembl_id` — повторяется в `activity.yaml`, `assay.yaml`
- `document_chembl_id` — повторяется в `activity.yaml`, `assay.yaml`, `document.yaml`
- `molecule_chembl_id` — повторяется в `activity.yaml`
- `assay_chembl_id` — повторяется в `activity.yaml`

**Текущее состояние:**
- `activity.yaml`: 276 строк (включает поля activity, assay, molecule, target, document)
- `assay.yaml`: 97 строк (включает поля assay, target, document)
- `target.yaml`: 61 строка (только поля target)
- `document.yaml`: 120 строк (только поля document)
- `molecule.yaml`: 115 строк (только поля molecule)

## Решение

### Вариант A: Профили полей (рекомендуется)

Создать отдельные профили для полей каждой сущности и использовать механизм композиции.

**Структура:**
```
configs/
  profiles/
    chembl_fields/
      target_fields.yaml
      document_fields.yaml
      molecule_fields.yaml
      assay_fields.yaml
```

**Пример `configs/profiles/chembl_fields/target_fields.yaml`:**
```yaml
# Target Fields Profile
# Общие поля для сущности target

fields:
  - name: target_chembl_id
    data_type: string
    is_nullable: false
    is_filterable: true
    description: ChEMBL ID таргета

  - name: target_pref_name
    data_type: string
    is_nullable: true
    is_filterable: false
    description: Название таргета

  - name: target_organism
    data_type: string
    is_nullable: true
    is_filterable: true
    description: Организм таргета

  - name: target_tax_id
    data_type: integer
    is_nullable: true
    is_filterable: true
    description: NCBI TaxID таргета
```

**Использование в пайплайновых конфигах:**

Требуется расширение `ConfigResolver` для поддержки `import_fields`:

```yaml
# configs/pipelines/chembl/activity.yaml
extends: chembl_default
import_fields:
  - chembl_fields/target_fields
  - chembl_fields/document_fields
  - chembl_fields/molecule_fields
  - chembl_fields/assay_fields

entity_name: activity
endpoint: /activity
primary_key: activity_id

# Специфичные поля activity
fields:
  - name: activity_id
    data_type: integer
    is_nullable: false
    is_filterable: false
    description: Внутренний ID активности
  # ... остальные поля activity
```

**Преимущества:**
- Модульность: изменения в полях одной сущности не затрагивают другие
- Гибкость: можно импортировать только нужные наборы полей
- Соответствие принципу DRY
- Легко добавлять новые поля в профиль

### Вариант B: Единый профиль общих полей

Если механизм `import_fields` сложно реализовать, создать единый профиль с общими полями.

**Пример `configs/profiles/chembl_common_fields.yaml`:**
```yaml
# ChEMBL Common Fields Profile
# Общие поля для всех ChEMBL-пайплайнов

common_fields:
  target:
    - name: target_chembl_id
      data_type: string
      is_nullable: false
      is_filterable: true
      description: ChEMBL ID таргета
    # ... остальные поля target

  document:
    - name: document_chembl_id
      data_type: string
      is_nullable: false
      is_filterable: true
      description: ChEMBL ID документа
    # ... остальные поля document
```

**Использование:**
```yaml
# configs/pipelines/chembl/activity.yaml
extends: chembl_default
extends_fields: chembl_common_fields

entity_name: activity
# ...
```

**Недостатки:**
- Менее гибко: все пайплайны получают все общие поля
- Сложнее поддерживать: изменения затрагивают все пайплайны

## Рекомендация по реализации

**Предпочтительный вариант:** Вариант A (профили полей)

**Шаги реализации:**
1. Создать структуру `configs/profiles/chembl_fields/`
2. Выделить общие поля из существующих конфигов в профили
3. Расширить `ConfigResolver` для поддержки `import_fields` (или использовать существующий механизм `extends` с вложенными профилями)
4. Обновить пайплайновые конфиги для использования профилей полей
5. Удалить дублированные определения полей из пайплайновых конфигов

**Альтернатива (если `import_fields` недоступен):**
- Использовать вложенные `extends`: создать промежуточные профили, которые наследуют базовый профиль и добавляют поля

```yaml
# configs/profiles/chembl_activity_base.yaml
extends: chembl_default
extends_fields: chembl_common_fields

# configs/pipelines/chembl/activity.yaml
extends: chembl_activity_base
# только специфичные поля activity
```

## Метрики успеха

После реализации:
- Количество строк в `activity.yaml` должно сократиться с 276 до ~150
- Количество строк в `assay.yaml` должно сократиться с 97 до ~60
- Изменение поля `target_chembl_id` должно происходить в одном месте
- Добавление нового поля в профиль должно автоматически применяться ко всем использующим его пайплайнам

## Related Documents

- `docs/project/04-architecture-and-duplication-reduction.md` — общие принципы снижения дублирования
- `configs/README.md` — архитектура конфигураций
- `docs/guides/configuration.md` — работа с конфигурациями

