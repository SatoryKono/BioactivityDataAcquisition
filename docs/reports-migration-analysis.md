# Анализ обоснованности переноса docs/reports/ в reports/

**Дата:** 2026-08-08  
**Цель:** Проверить обоснованность переноса содержимого docs/reports/ в reports/ для консолидации

## Анализ текущего состояния

### docs/reports/ (Thin curated surface)

**Структура:**
```
docs/reports/
├── dashboard-ux-checks/    # UX проверки дашбордов
├── evidence/                # Thin curated manifests (freshness governance)
├── generated/               # Allowlisted generated inventories/matrices
├── gh-issues/               # GitHub issues related
├── index.md                 # Orientation
└── README.md                # Documentation
```

**Характеристики:**
- **Тип:** Thin curated map (не dump of working evidence)
- **Статус:** Blocked cleanup zone в `configs/quality/repo_structure_catalog.yaml`
- **Размер:** ~3.3 MB (преимущественно JSON/Markdown файлы)
- **Governance:** Curated cleanup only, не treat allowlisted manifests as disposable

### reports/ (Working outputs surface)

**Структура:**
```
reports/
├── ai/                      # AI outputs
├── architecture/            # Architecture test results
├── audit/                   # Audit results
├── codex/                   # Codex outputs
├── coverage/                # Coverage reports
├── docs-evidence/           # Bulk historical evidence packs
├── grafana/                 # Grafana related
├── logs/                    # Log files
├── observability/           # Observability reports
├── plans/                   # Planning reports
├── pytest/                  # Pytest results
├── quality/                 # Quality reports
├── review/                  # Review reports
├── root-hygiene/            # Root hygiene reports
├── semantic_pipeline_audit/ # Semantic pipeline audit
├── test-swarm/              # Test swarm results
├── test-telemetry/          # Test telemetry
├── tmp/                     # Temporary files
└── [много больших JSON файлов] # bp_full.json (67MB), bp_live.json (7.8MB), etc.
```

**Характеристики:**
- **Тип:** Working / model-specific / iterative outputs
- **Статус:** Blocked cleanup zone в `configs/quality/repo_structure_catalog.yaml`
- **Размер:** ~95 MB (включая большие JSON файлы)
- **Governance:** Bounded cleanup only

## Boundary Contract (из docs/reports/README.md)

```
- current instructions / operator workflow / contracts → docs/00-05/
- curated repo-only manifests → docs/reports/ (thin)
- bulk evidence / investigations → reports/docs-evidence/ or reports/{LLM}/
- historical retained context → docs/99-archive/
```

## Анализ использования

### docs/reports/ использование:
- ✅ Указан в `configs/quality/repo_structure_catalog.yaml` как blocked cleanup zone
- ✅ Указан в `configs/quality/generated_artifact_routing.yaml` для generated artifacts
- ✅ Указан в `configs/quality/root_hygiene_review_registry.yaml`
- ✅ Указан в `configs/quality/test_structural_watchlist_map.yaml`
- ✅ Указан в `src/memory/policy/exclusions.yaml`
- ✅ Указан в `src/memory/graph/mappings.yaml`
- ✅ Указан в `src/memory/catalog/source_registry.yaml`
- ✅ Указан в `src/memory/catalog/repo_zones.yaml`
- ✅ Используется в GitHub workflows (tests.yml, provider-contract-drift.yml)
- ✅ Используется в ISSUE_TEMPLATE (retention_sensitive_cleanup.yml)
- ❌ НЕ публикуется в MkDocs (в exclude_docs)

### reports/ использование:
- ✅ Указан в `configs/quality/repo_structure_catalog.yaml` как blocked cleanup zone
- ✅ Указан в ISSUE_TEMPLATE (retention_sensitive_cleanup.yml)
- ❌ НЕ публикуется в MkDocs (в exclude_docs)

## Обоснование против переноса

### 1. Разные типы контента и governance

**docs/reports/** - Thin curated surface:
- **Назначение:** Curated repo-only manifests
- **Governance:** Curated cleanup only
- **Тип:** Thin curated map, не dump of working evidence
- **Размер:** ~3.3 MB (manageable)
- **Примеры:** Generated inventories, curated manifests, UX checks

**reports/** - Working outputs surface:
- **Назначение:** Working / model-specific / iterative outputs
- **Governance:** Bounded cleanup only
- **Тип:** Bulk evidence, investigations, temporary files
- **Размер:** ~95 MB (включая большие JSON файлы)
- **Примеры:** Test results, AI outputs, temporary files, logs

### 2. Нарушение boundary contract

Перенос docs/reports/ в reports/ нарушит established boundary contract:

```
- curated repo-only manifests → docs/reports/ (thin)
- bulk evidence / investigations → reports/docs-evidence/ or reports/{LLM}/
```

Если перенести curated manifests в reports/, нарушится логическое разделение:
- Curated manifests смешаются с bulk evidence
- Thin curated surface смешивается с working outputs
- Governance boundaries становятся нечеткими

### 3. Разные cleanup policies

**docs/reports/** - Curated cleanup only:
- Не treat allowlisted manifests as disposable
- Do not reintroduce multi-MB bulk packs into this tree
- Строгий curated cleanup

**reports/** - Bounded cleanup only:
- Допускается bounded cleanup
- Содержит временные файлы и bulk evidence
- Менее строгая cleanup политика

### 4. Интеграционные зависимости

**docs/reports/** широко используется в конфигурационных файлах:
- `configs/quality/generated_artifact_routing.yaml` - 10 ссылок
- `configs/quality/test_structural_watchlist_map.yaml` - 3 ссылки
- `src/memory/**` - 4 ссылки
- GitHub workflows - 3 ссылки
- ISSUE_TEMPLATE - 2 ссылки

Перенос потребует обновления всех этих зависимостей.

### 5. MkDocs navigation

Обе директории НЕ публикуются в MkDocs (в exclude_docs), но docs/reports/ является частью docs/ структуры, что логично для curated documentation surface.

### 6. Memory cataloging

Обе директории catalogued в memory system:
- `src/memory/catalog/source_registry.yaml` - paths: ["docs/reports", "reports"]
- `src/memory/catalog/repo_zones.yaml` - paths: ["docs/reports", "reports", "site"]

Перенос потребует обновления memory cataloging.

## Аргументы ЗА перенос

1. **Консолидация:** Все отчеты в одном месте (reports/)
2. **Упрощение:** Одна директория reports/ вместо двух
3. **Уменьшение docs/**:** docs/ содержит только контент, не отчеты

## Аргументы ПРОТИВ переноса

1. **Нарушение boundary contract:** Разные типы контента имеют разные governance
2. **Разные cleanup policies:** Curated vs bounded cleanup
3. **Интеграционные зависимости:** Много ссылок в конфигурационных файлах
4. **Разные размеры:** docs/reports/ (3.3MB) vs reports/ (95MB)
5. **Разные типы контента:** Curated manifests vs working outputs
6. **Memory cataloging:** Обе директории уже catalogued отдельно

## Рекомендация

### НЕ ПЕРЕНОСИТЬ docs/reports/ в reports/

**Обоснование:**

1. **Нарушение boundary contract:**
   - docs/reports/ предназначен для curated repo-only manifests
   - reports/ предназначен для working outputs и bulk evidence
   - Перенос нарушит логическое разделение

2. **Разные governance модели:**
   - docs/reports/ - curated cleanup only
   - reports/ - bounded cleanup only
   - Смешивание создаст governance confusion

3. **Интеграционные зависимости:**
   - docs/reports/ широко используется в конфигурационных файлах
   - Перенос потребует обновления множества зависимостей

4. **Разные типы контента:**
   - docs/reports/ - thin curated manifests (3.3MB)
   - reports/ - working outputs, bulk evidence (95MB)
   - Перенос смешает curated и working content

5. **Memory cataloging:**
   - Обе директории уже catalogued отдельно
   - Система ожидает два отдельных пространства

### Альтернативные действия:

#### Вариант 1: ОСТАВИТЬ текущую структуру (рекомендуется)
```bash
# Сохранить разделение:
# docs/reports/ - curated repo-only manifests
# reports/ - working outputs and bulk evidence
```

#### Вариант 2: Уточнить boundary contract
```bash
# Если есть конкретные файлы в docs/reports/, которые должны быть в reports/
# Перенести только конкретные файлы, а не всю директорию
```

#### Вариант 3: Переименовать для ясности
```bash
# Если текущие названия вызывают путаницу
# Переименовать для большей ясности:
# docs/reports/ → docs/curated-manifests/
# reports/ → reports/working-outputs/
```

## Итоговый вывод

Перенос docs/reports/ в reports/ **НЕ обоснован** по следующим причинам:

1. **Нарушение boundary contract** - разные типы контента имеют разные governance
2. **Разные cleanup policies** - curated vs bounded cleanup
3. **Интеграционные зависимости** - много ссылок в конфигурационных файлах
4. **Разные типы контента** - curated manifests vs working outputs
5. **Разные размеры** - 3.3MB vs 95MB
6. **Memory cataloging** - система ожидает два отдельных пространства

**Текущая структура оптимальна:**
- `docs/reports/` - curated repo-only manifests (thin) ✅
- `reports/` - working outputs and bulk evidence ✅

**Boundary contract работает корректно:**
- Curated manifests → docs/reports/
- Bulk evidence → reports/docs-evidence/ or reports/{LLM}/
- Historical context → docs/99-archive/

Перенос создаст больше проблем, чем решит.
