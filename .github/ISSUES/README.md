# GitHub Issues for Technical Debt Reduction

Этот каталог содержит готовые markdown-файлы для создания GitHub issues на основе технического аудита BioETL.

## Как использовать

Каждый файл в этом каталоге — это готовый контент для GitHub issue. Для создания issue:

1. Откройте файл с описанием issue
2. Скопируйте содержимое между `---` маркерами (frontmatter) и концом файла
3. Создайте новую GitHub issue в репозитории
4. Вставьте скопированный контент
5. Установите labels согласно frontmatter
6. Назначьте assignees при необходимости

Или используйте GitHub CLI (если доступен):
```bash
gh issue create --title "Issue Title" --body-file .github/issues/issue-file.md
```

## Список Issues

| Priority | Issue | Файл | Тип долга | Усилия |
|----------|-------|------|-----------|--------|
| **P1** | Audit and consolidate mixin proliferation (154 files) | `P1-mixin-proliferation-audit.md` | Architectural violation | Высокий |
| **P2** | Evaluate and consolidate factory class duplication (24 classes) | `P2-factory-duplication-evaluation.md` | Duplication | Средний |
| **P3** | Reduce first-party imports for domain/composite/config.py (81 importers) | `P3-composite-config-import-reduction.md` | Compatibility debt | Средний |
| **P4** | Resolve TEMPORAL TODO marker in publication_fields.py:260 | `P4-resolve-todo-marker-publication-fields.md` | Code quality | Низкий |
| **P5** | Metrics cardinality audit and high-cardinality label review | `P5-metrics-cardinality-audit.md` | Observability gap | Средний |
| **P6** | Verify ADR-003 and ADR-008 archive completeness | `P6-adr-archive-verification.md` | Documentation | Низкий |
| **P7** | Continue hotspot ratchet for application/core/ (174 files, 21611 LOC) | `P7-application-core-hotspot-ratchet.md` | Hotspot management | Высокий |
| **P8** | Continue hotspot ratchet for bootstrap/runtime/ (44 files, 5758 LOC) | `P8-bootstrap-runtime-hotspot-ratchet.md` | Hotspot management | Средний |

## Рекомендуемый порядок выполнения

### Phase 1: Quick Wins (Неделя 1-2)
1. **P4** - Resolve TODO marker (низкие усилия, быстрый результат)
2. **P6** - ADR archive verification (низкие усилия, governance improvement)

### Phase 2: Governance (Неделя 2-4)
3. **P5** - Metrics cardinality audit (создать prevention mechanism)
4. **P3** - Composite config import reduction (targeted facades)

### Phase 3: Structural (Неделя 4-8)
5. **P2** - Factory duplication evaluation (средние усилия, medium risk)
6. **P8** - Bootstrap runtime hotspot ratchet (меньший hotspot)

### Phase 4: Major (Неделя 8+)
7. **P1** - Mixin proliferation audit (высокие усилия, major impact)
8. **P7** - Application core hotspot ratchet (крупный hotspot, high effort)

## Labels для использования

Все issues используют следующие labels (определены в frontmatter каждого файла):

### Priority Labels
- `priority/P1` - Критический приоритет
- `priority/P2` - Высокий приоритет
- `priority/P3` - Средний приоритет
- `priority/P4` - Низкий приоритет
- `priority/P5` - Очень низкий приоритет
- `priority/P6` - Минимальный приоритет
- `priority/P7` - Долгосрочный
- `priority/P8` - Долгосрочный низкий приоритет

### Type Labels
- `technical-debt` - Технический долг
- `architecture` - Архитектурные изменения
- `duplication` - Устранение дублирования
- `compatibility` - Compatibility layer
- `code-quality` - Качество кода
- `observability` - Observability и метрики
- `documentation` - Документация
- `hotspot` - Hotspot reduction

### Additional Labels
- `enhancement` - Улучшение (не bug fix)
- `bug` - Ошибка (для P4)

## Контекст

Все issues основаны на полном аудите технического долга BioETL, который выявил:

✅ **Strengths**:
- Transition compatibility debt полностью удален
- Config drift под полным контролем
- Dead code полностью классифицирован
- Test coverage gaps отсутствуют
- ADR governance активен

⚠️ **Areas for improvement**:
- Mixin proliferation (154 files)
- Factory duplication (24 classes)
- Hotspot growth (application/core/, bootstrap/runtime/)
- Missing enforcement для mixins, factories, config imports

**Overall Assessment**: Low technical debt с хорошо управляемым compatibility layer.

## Связанные артефакты

- **Technical Debt Audit**: Полный отчет аудита
- **Debt Scorecard**: `configs/quality/debt_scorecard.yaml`
- **Compatibility Facade Inventory**: `configs/quality/compatibility_facade_inventory.yaml`
- **Dead Code Inventory**: `reports/quality/dead-code-inventory.md`