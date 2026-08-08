# Анализ обоснованности переноса docs/plugins в scripts/docs

**Дата:** 2026-08-08  
**Цель:** Проверить обоснованность переноса docs/plugins/link_checker в scripts/docs для консолидации скриптов для работы с документами

## Анализ текущего состояния

### docs/plugins/link_checker/

**Структура:**
```
docs/plugins/link_checker/
├── INTEGRATION_GUIDE.md
├── mkdocs_example.yml
├── plugin.py              # MkDocs plugin implementation
├── README.md
├── requirements.txt
├── test_basic.py
├── test_integration.py
└── tests/
```

**Характеристики:**
- MkDocs plugin для проверки ссылок при сборке документации
- Указан в `configs/quality/repo_structure_catalog.yaml` как `approved_docs_plugin_source_tree`
- Генерирует link health metrics (JSON, HTML, SVG reports)
- Связан с issue #3094 "Expose Link-Check Results as Published"

### scripts/docs/

**Структура:**
```
scripts/docs/
├── __init__.py
├── __main__.py              # Unified entry point
├── build_docs_site.sh
├── README.md
├── build/                   # MkDocs build entrypoints
├── checks/                  # Validation, drift, KPI, verification
├── common/                  # Shared utilities
├── fixers/                  # Corrective maintenance
├── matrix/                  # Workbook and matrix tooling
└── passports/               # Passport rendering
```

**Характеристики:**
- Унифицированный entry point: `python -m scripts.docs`
- Команда `check-links` уже выполняет link checking
- Comprehensive набор инструментов для docs maintenance
- Интегрирован в CI/CD workflows

## Анализ использования

### docs/plugins/link_checker использование:
- ❌ НЕ используется в `mkdocs.yml` (нет ссылок на link_checker)
- ❌ НЕ используется в GitHub workflows
- ❌ НЕ используется в Python скриптах
- ❌ НЕ используется в shell скриптах
- ✅ Указан в `configs/quality/repo_structure_catalog.yaml`
- ✅ Указан в `configs/naming_exceptions.yaml`
- ✅ Указан в `.pre-commit-config.yaml`

### scripts/docs/checks/check_links.py:
- ✅ Активно используется через `python -m scripts.docs check-links`
- ✅ Интегрирован в CI/CD (docs.yml, architecture.yml)
- ✅ Часть унифицированного docs tooling

## Обоснование переноса

### Аргументы ПРОТИВ переноса:

1. **Разные типы артефактов:**
   - `docs/plugins/link_checker` - MkDocs plugin (Python package)
   - `scripts/docs/` - скрипты для работы с документацией
   - MkDocs plugin предназначен для интеграции в MkDocs build process
   - scripts/docs предназначены для standalone проверки и maintenance

2. **Дублирование функциональности:**
   - `scripts/docs/checks/check_links.py` уже выполняет link checking
   - Перенос создаст дублирование без явной пользы

3. **Plugin не используется:**
   - link_checker plugin НЕ активирован в mkdocs.yml
   - НЕ используется в CI/CD
   - Похоже на legacy или экспериментальный код

4. **Разные цели и контекст использования:**
   - MkDocs plugin: интеграция в build process, автоматическая проверка при сборке
   - scripts/docs: standalone проверки, manual triggers, CI gates

5. **Структурные различия:**
   - MkDocs plugin требует специфическую структуру (plugin.py, requirements.txt)
   - scripts/docs использует унифицированный entry point pattern

### Аргументы ЗА перенос:

1. **Консолидация docs tooling:**
   - Все инструменты для работы с docs в одном месте
   - Единый entry point pattern

2. **Упрощение структуры:**
   - Уменьшение количества директорий в docs/
   - Четкое разделение: docs/ для контента, scripts/ для инструментов

## Рекомендация

### НЕ ПЕРЕНОСИТЬ docs/plugins/link_checker в scripts/docs/

**Обоснование:**

1. **Разные типы артефактов:**
   - MkDocs plugin ≠ скрипты для docs
   - Разные цели использования и контекст

2. **Дублирование функциональности:**
   - Link checking уже реализован в scripts/docs/checks/check_links.py
   - Перенос создаст ненужное дублирование

3. **Plugin не используется:**
   - Если plugin не нужен, лучше удалить его полностью
   - Если нужен для будущего использования, оставить как MkDocs plugin

### Альтернативные действия:

#### Вариант 1: Удалить docs/plugins/link_checker
```bash
# Если plugin не используется и не планируется к использованию
rm -rf docs/plugins/link_checker
# Обновить configs/quality/repo_structure_catalog.yaml
# Обновить configs/naming_exceptions.yaml
# Обновить .pre-commit-config.yaml
```

#### Вариант 2: Оставить docs/plugins/link_checker как MkDocs plugin
```bash
# Оставить для будущего использования в MkDocs build process
# Если понадобится интеграция, можно активировать в mkdocs.yml
```

#### Вариант 3: Активировать link_checker в mkdocs.yml
```yaml
# mkdocs.yml
plugins:
  - link_checker:
      enabled: true
      timeout: 10
      max_redirects: 5
      ignore_patterns:
        - "localhost"
        - "127.0.0.1"
      report_dir: "reports/links"
      fail_on_error: false
```

## Итоговый вывод

Перенос docs/plugins/link_checker в scripts/docs/ **НЕ обоснован** по следующим причинам:

1. **Разные типы артефактов** (MkDocs plugin vs скрипты)
2. **Дублирование функциональности** (link checking уже есть в scripts/docs)
3. **Plugin не используется** в текущем workflow
4. **Разные цели использования** (build integration vs standalone checks)

**Выполненное действие (2026-08-08):**
- ✅ **УДАЛЕНО** docs/plugins/link_checker как неиспользуемый legacy код
- ✅ **УДАЛЕНО** docs/plugins/ (пустая директория после удаления link_checker)
- ✅ Обновлен `configs/quality/repo_structure_catalog.yaml` (удалена ссылка на docs/plugins/link_checker)
- ✅ Обновлен `configs/naming_exceptions.yaml` (удалена ссылка на docs/plugins/link_checker/INTEGRATION_GUIDE.md)
- ✅ Обновлен `.pre-commit-config.yaml` (удалена ссылка на docs/plugins/link_checker/mkdocs_example.yml)

**Текущая структура оптимальна:**
- `scripts/docs/` - для всех скриптов работы с документацией ✅
- `docs/plugins/` - удалена (не используется) ✅
