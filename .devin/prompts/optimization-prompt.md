# Devin Optimization Prompt - Улучшенный промт для повышения эффективности

## Контекст
Ты работаешь с проектом BioETL и используешь Devin CLI с кастомными subagent profiles. Текущая конфигурация включает 9 profiles, 14 skills, 18 MCP servers и 7 documented workflows.

## Задача
Проанализируй текущую конфигурацию Devin и предложи конкретные, actionable улучшения для повышения эффективности и удобства работы, учитывая:

1. Текущую структуру `.devin/` (agents, skills, workflows, config)
2. Существующую документацию (DEVIN-SETUP-GUIDE.md, ORCHESTRATION.md, DEVIN-RUNTIME.md)
3. Установленные guardrails и governance policies
4. Канонические источники из docs/00-project/
5. Memory workflow из src/memory/DAILY_WORKFLOW.md

## Формат ответа

### 1. Краткий анализ текущего состояния (максимум 5 пунктов)
- Что работает хорошо
- Основные проблемы
- Текущая эффективность (оценка 1-10)

### 2. Приоритетные улучшения (с конкретными действиями)

#### Приоритет 1: Quick Wins (высокий эффект, низкие усилия)
- **Проблема:** [краткое описание]
- **Решение:** [конкретное действие с кодом/командами]
- **Ожидаемый эффект:** [количественная оценка]
- **Риски:** [минимальные риски]

#### Приоритет 2: Workflow Optimization (средний эффект, средние усилия)
- [аналогично]

#### Приоритет 3: Configuration Optimization (средний эффект, высокие усилия)
- [аналогично]

### 3. Конкретные примеры улучшений

Для каждого улучшения предоставь:
- **До:** [текущий подход]
- **После:** [улучшенный подход]
- **Код/конфиг:** [конкретные изменения]
- **Команды:** [как использовать]

### 4. План внедрения

Разбей на фазы с конкретными сроками:
- **Фаза 1 (неделя 1):** [конкретные задачи]
- **Фаза 2 (неделя 2-3):** [конкретные задачи]
- **Фаза 3 (неделя 4+):** [конкретные задачи]

### 5. Ожидаемые результаты

Количественные метрики:
- Сокращение времени на рутинные задачи: [X%]
- Упрощение обучения новых пользователей: [X%]
- Снижение количества ошибок: [X%]

## Ограничения и guardrails

1. **НЕ нарушать** существующие governance policies
2. **НЕ увеличивать** бюджеты тех. долга (запрещено)
3. **НЕ нарушать** архитектурные границы
4. **НЕ создавать** root-level scratch files
5. **Соблюдать** каноническую precedence из AGENTS.md
6. **Использовать** memory workflow из src/memory/DAILY_WORKFLOW.md
7. **Следовать** POST_CHANGE_VALIDATION.md для любых изменений

## Специфические требования для BioETL

1. Учитывай существующие py-* profiles (py-audit-bot, py-config-bot, py-debug-bot, py-doc-bot, py-plan-bot, py-test-bot)
2. Используй существующие skills (new-pipeline, observability-dashboard, observability-prometheus, technical-designer-mermaid, vcr-record, verify-architecture)
3. Следуй ORCHESTRATION.md workflow patterns
4. Учитывай MCP server конфигурацию (18 servers)
5. Используй Makefile targets (devin, devin-check, devin-mcp-start)

## Пример хорошего ответа

### Приоритет 1: Quick Wins

**Проблема:** Для простого bug fix требуется полный 8-шаговый workflow, что занимает ~30 минут.

**Решение:** Добавить quick-fix shortcut в Makefile:

```makefile
devin-fix-bug:
	@echo "Quick bug fix workflow (5 steps vs 8)"
	@$(DEVIN) $(DEVIN_ARGS) --prompt "Run py-test-bot baseline on current scope, orchestrator fix, py-test-bot final, py-doc-bot docstring only, py-audit-bot targeted"

# Использование:
# make devin-fix-bug
```

**Ожидаемый эффект:** Сокращение времени на простые bug fixes с 30 до 12 минут (60% быстрее)

**Риски:** Минимальные - только добавление shortcut, не меняет существующую логику

### Приоритет 2: Workflow Optimization

**Проблема:** Выбор правильного profile требует чтения ORCHESTRATION.md (~10 минут).

**Решение:** Добавить интерактивный profile selector:

```makefile
devin-select-profile:
	@echo "Select profile based on task type:"
	@echo "  1) Bug fix              → py-debug-bot"
	@echo "  2) Feature addition     → py-plan-bot → orchestrator"
	@echo "  3) Config change        → py-config-bot"
	@echo "  4) Documentation        → py-doc-bot"
	@echo "  5) Testing              → py-test-bot"
	@echo "  6) Audit                → py-audit-bot"
	@read -p "Select profile (1-6): " profile
	@$(DEVIN) --prompt "Use profile $$profile for current task"
```

**Ожидаемый эффект:** Сокращение времени на выбор profile с 10 до 2 минут (80% быстрее)

**Риски:** Минимальные - только helper command

## Дополнительные указания

1. **Будь конкретным:** Используй реальные команды, файлы, пути из проекта
2. **Будь прагматичным:** Предлагай решения, которые можно внедрить быстро
3. **Будь реалистичным:** Оценивай усилия и риски честно
4. **Будь последовательным:** Улучшения должны быть совместимы с существующей системой
5. **Будь measurable:** Предоставляй количественные оценки эффекта

## Проверка качества

Перед отправкой ответа проверь:
- [ ] Все предложения совместимы с AGENTS.md guardrails
- [ ] Все предложения учитывают существующую структуру .devin/
- [ ] Все предложения имеют конкретные код/команды
- [ ] Все предложения имеют количественные оценки эффекта
- [ ] Все предложения имеют оценку рисков
- [ ] План внедрения разбит на фазы с конкретными сроками
- [ ] Ответ на русском (технические термины в оригинале)
- [ ] Не предлагаются изменения, которые увеличивают тех. долг