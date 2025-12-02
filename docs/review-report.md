# Отчёт о ревью документации и структуры проекта

## Резюме

Проведён анализ документации проекта BioETL, выявлены критические несоответствия между документацией и реальным состоянием кодовой базы, битые ссылки, противоречия в правилах и возможности для снижения дублирования.

**Ключевые проблемы:**
1. Критическое несоответствие: roadmap утверждает реализацию компонентов, но код отсутствует
2. Битые ссылки на несуществующие файлы в правилах и документации
3. Дублирование определений полей в конфигах пайплайнов
4. Несоответствие путей к документации в разных источниках

---

## 1. Ошибки и противоречия

### 1.1. Несоответствие статусов в roadmap

**Файл:** `docs/architecture/00-duplication-reduction-roadmap.md`

**Проблема:** В разделе "✅ Реализовано в архитектуре" указаны компоненты как "Задокументировано", но фактически код отсутствует (`src/bioetl/` пуст).

**Найденные утверждения:**
- `PipelineBase` — "✅ Задокументировано" (строка 9)
- `ChemblBasePipeline` — "✅ Задокументировано" (строка 10)
- `UnifiedAPIClient` — "✅ Задокументировано" (строка 11)
- `UnifiedOutputWriter` — "✅ Задокументировано" (строка 12)
- `BaseChemblNormalizer` — "✅ Задокументировано" (строка 13)

**Исправление:**
Изменить статус с "✅ Задокументировано" на "⏳ Задокументировано, требует реализации" или разделить на две колонки: "Документация" и "Код".

### 1.2. Битые ссылки на несуществующие файлы

#### 1.2.1. Ссылка на `docs/00-styleguide/`

**Файлы с ошибками:**
- `.cursor/rules/13-documentation-standards.mdc` (строка 49): `docs/00-styleguide/10-documentation-standards.md` и `docs/00-styleguide/00-naming-conventions.md`
- `.cursor/rules/11-abc-default-impl-policy.mdc` (строка 58): `docs/00-styleguide/01-new-entity-implementation-policy.md`
- `.cursor/rules/12-entity-naming-policy.mdc` (строка 80): `docs/00-styleguide/02-new-entity-naming-policy.md`

**Проблема:** Директория `docs/00-styleguide/` не существует. Правила ссылаются на несуществующие файлы.

**Исправление:**
- Вариант 1: Создать структуру `docs/00-styleguide/` и переместить туда соответствующие документы
- Вариант 2: Обновить ссылки на существующие файлы:
  - `docs/00-styleguide/00-naming-conventions.md` → `docs/project/00-rules-summary.md` (раздел 1)
  - `docs/00-styleguide/01-new-entity-implementation-policy.md` → `docs/project/00-rules-summary.md` (раздел 2) или `.cursor/rules/11-abc-default-impl-policy.mdc`
  - `docs/00-styleguide/02-new-entity-naming-policy.md` → `.cursor/rules/12-entity-naming-policy.mdc`
  - `docs/00-styleguide/10-documentation-standards.md` → `.cursor/rules/13-documentation-standards.mdc`

**Рекомендация:** Вариант 2 (обновить ссылки), так как правила уже консолидированы в `.cursor/rules/` и `docs/project/00-rules-summary.md`.

#### 1.2.2. Ссылка на `docs/project/01-new-entity-implementation-policy.md`

**Файл:** `docs/architecture/00-duplication-reduction-roadmap.md` (строка 221)

**Проблема:** Файл не существует.

**Исправление:** Заменить на `docs/project/00-rules-summary.md` (раздел 2) или `.cursor/rules/11-abc-default-impl-policy.mdc`.

#### 1.2.3. Несоответствие путей к ABC Index

**Файлы:**
- `docs/project/00-rules-summary.md` (строка 25): `docs/reference/abc/index.md` ✅
- `.cursor/rules/13-documentation-standards.mdc` (строка 32): `docs/ABC_INDEX.md` ❌

**Проблема:** В правилах документации указан путь `docs/ABC_INDEX.md`, но фактически файл находится в `docs/reference/abc/INDEX.md`.

**Исправление:** В `.cursor/rules/13-documentation-standards.mdc` заменить `docs/ABC_INDEX.md` на `docs/reference/abc/INDEX.md`.

### 1.3. Противоречия в описании структуры документации

**Файл:** `docs/project/00-rules-summary.md` (строка 87)

**Проблема:** Указан путь `docs/reference/pipelines/<provider>/<entity>/NN-<entity>-<provider>-<topic>.md`, но фактически документация находится в `docs/02-pipelines/<provider>/<entity>/NN-<entity>-<provider>-<topic>.md`.

**Исправление:** Заменить `docs/reference/pipelines/` на `docs/02-pipelines/` в строке 87.

### 1.4. Терминологические несоответствия

**Файл:** `docs/architecture/00-duplication-reduction-roadmap.md` (строка 42)

**Проблема:** Указан путь `docs/reference/core/00-pipeline-base.md`, но фактически файл находится в `docs/02-pipelines/00-pipeline-base.md`.

**Исправление:** Обновить путь на `docs/02-pipelines/00-pipeline-base.md` или переместить файл в `docs/reference/core/`.

---

## 2. Дублирование информации

### 2.1. Дублирование описания правил

**Проблема:** Правила проекта описаны в нескольких местах:
- `docs/project/00-rules-summary.md` — сводка
- `.cursor/rules/*.mdc` — детальные правила
- `docs/architecture/00-duplication-reduction-roadmap.md` — ссылки на правила

**Рекомендация:** Чётко определить иерархию:
- `.cursor/rules/*.mdc` — источники истины для правил
- `docs/project/00-rules-summary.md` — краткая сводка с ссылками на детальные правила
- Остальные документы — ссылаются на сводку

### 2.2. Дублирование полей в конфигах пайплайнов

**Проблема:** Общие поля повторяются в конфигах разных пайплайнов:

**Примеры дублирования:**
- `target_chembl_id` — в `activity.yaml`, `assay.yaml`
- `document_chembl_id` — в `activity.yaml`, `assay.yaml`, `document.yaml`
- `molecule_chembl_id` — в `activity.yaml`
- `assay_chembl_id` — в `activity.yaml`

**Анализ:**
- `activity.yaml`: 268 строк, содержит поля для activity, assay, molecule, target, document
- `assay.yaml`: 97 строк, содержит поля для assay, target, document
- `target.yaml`: 61 строка, содержит поля для target
- `document.yaml`: 120 строк, содержит поля для document

**Рекомендация:** Создать базовые профили полей для общих сущностей:

```yaml
# configs/profiles/chembl_fields/target_fields.yaml
fields:
  - name: target_chembl_id
    data_type: string
    is_nullable: false
    is_filterable: true
    description: ChEMBL ID таргета
  # ... остальные поля target

# configs/profiles/chembl_fields/document_fields.yaml
fields:
  - name: document_chembl_id
    data_type: string
    is_nullable: false
    is_filterable: true
    description: ChEMBL ID документа
  # ... остальные поля document
```

Затем в конфигах пайплайнов использовать механизм `extends` или `import`:

```yaml
# configs/pipelines/chembl/activity.yaml
extends: chembl_default
import_fields:
  - chembl_fields/target_fields
  - chembl_fields/document_fields
  - chembl_fields/molecule_fields
  - chembl_fields/assay_fields

# Специфичные поля activity
fields:
  - name: activity_id
    # ...
```

**Альтернатива:** Если механизм `import` не поддерживается, создать базовый профиль `chembl_common_fields.yaml` с общими полями и наследовать его в пайплайновых конфигах.

---

## 3. Архитектура и дублирование кода

### 3.1. Анализ текущей архитектуры

**Сильные стороны:**
- ✅ Механизм профилей конфигураций (`extends`) реализован и работает
- ✅ Чёткая иерархия документации компонентов
- ✅ План унификации через базовые классы и ABC

**Слабые стороны:**
- ❌ Код отсутствует, невозможно оценить реальное дублирование
- ❌ Документация описывает компоненты, которые не реализованы
- ❌ Нет механизма переиспользования полей в конфигах

### 3.2. Рекомендации по архитектуре

#### 3.2.1. Унификация конфигураций полей

**Проблема:** Дублирование определений полей в YAML-конфигах.

**Решение:** Ввести механизм композиции полей:

1. **Вариант A: Базовые профили полей** (рекомендуется)
   - Создать `configs/profiles/chembl_fields/` с профилями для каждой сущности
   - Использовать механизм `extends` или добавить поддержку `import_fields` в `ConfigResolver`

2. **Вариант B: Единый профиль общих полей**
   - Создать `configs/profiles/chembl_common_fields.yaml`
   - Наследовать в пайплайновых конфигах через `extends`

**Преимущества Варианта A:**
- Гибкость: можно импортировать только нужные наборы полей
- Модульность: изменения в полях одной сущности не затрагивают другие
- Соответствие принципу DRY

#### 3.2.2. Базовые схемы Pandera

**Рекомендация:** Реализовать `BaseChemblSchema` для общих полей (как описано в `docs/project/04-architecture-and-duplication-reduction.md`, раздел 6):

```python
class BaseChemblSchema(pa.DataFrameModel):
    chembl_release: Series[str] = pa.Field(regex=r"^\d+$")
    extracted_at: Series[datetime] = pa.Field(coerce=True)
    hash_row: Series[str] = pa.Field(str_length=64)
```

Это устранит дублирование определений метаданных в схемах.

#### 3.2.3. Унификация пайплайнов

**Рекомендация:** При реализации кода следовать плану из roadmap:
1. Реализовать `PipelineBase` с оркестрацией стадий
2. Реализовать `ChemblBasePipeline` для общих операций ChEMBL
3. Использовать композицию вместо дублирования логики

---

## 4. Предложения по исправлениям

### 4.1. Немедленные исправления (критичные)

1. **Обновить статусы в roadmap** (`docs/architecture/00-duplication-reduction-roadmap.md`):
   - Изменить "✅ Задокументировано" на "⏳ Задокументировано, код отсутствует"
   - Добавить колонку "Статус кода" для разделения документации и реализации

2. **Исправить битые ссылки:**
   - В `.cursor/rules/13-documentation-standards.mdc`: заменить `docs/00-styleguide/` на актуальные пути
   - В `.cursor/rules/11-abc-default-impl-policy.mdc`: заменить ссылку на `docs/00-styleguide/01-new-entity-implementation-policy.md`
   - В `.cursor/rules/12-entity-naming-policy.mdc`: заменить ссылку на `docs/00-styleguide/02-new-entity-naming-policy.md`
   - В `docs/architecture/00-duplication-reduction-roadmap.md`: заменить `docs/project/01-new-entity-implementation-policy.md`
   - В `.cursor/rules/13-documentation-standards.mdc`: заменить `docs/ABC_INDEX.md` на `docs/reference/abc/INDEX.md`

3. **Исправить пути в правилах:**
   - В `docs/project/00-rules-summary.md`: заменить `docs/reference/pipelines/` на `docs/02-pipelines/`

### 4.2. Улучшения структуры (высокий приоритет)

1. **Создать механизм переиспользования полей в конфигах:**
   - Добавить поддержку `import_fields` в `ConfigResolver` или использовать `extends` для профилей полей
   - Создать `configs/profiles/chembl_fields/` с профилями для каждой сущности

2. **Унифицировать пути к документации:**
   - Определить единую структуру: `docs/02-pipelines/` для pipeline docs, `docs/reference/` для reference docs
   - Обновить все ссылки на единый стандарт

### 4.3. Долгосрочные улучшения (средний приоритет)

1. **Реализовать базовые компоненты** согласно roadmap
2. **Создать `BaseChemblSchema`** для устранения дублирования в схемах
3. **Добавить автоматическую проверку битых ссылок** в CI

---

## 5. Чеклист для проверки

После исправлений проверить:

- [ ] Все ссылки в документации ведут на существующие файлы
- [ ] Статусы в roadmap соответствуют реальному состоянию
- [ ] Пути к документации единообразны во всех файлах
- [ ] Дублирование полей в конфигах устранено или минимизировано
- [ ] Правила проекта ссылаются на актуальные источники

---

## 6. Связанные документы

- `docs/project/00-rules-summary.md` — сводка правил
- `docs/architecture/00-duplication-reduction-roadmap.md` — roadmap снижения дублирования
- `.cursor/rules/` — детальные правила проекта
- `configs/pipelines/chembl/` — конфигурации пайплайнов

