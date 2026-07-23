# Предложение по расширению тестов для дашбордов BioETL

> **Removed 2026-07-23:** Silver Reject Explorer dashboard, Loki/Tempo Explore adjuncts, Quarantine Explorer datasource (replaced by BioETL Ops HTTP on :8000).
> Use CLI ioetl quarantine inspect for record-level forensics. See [monitoring-surface-reduction](../../05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md).



**Дата**: 2026-05-11  
**Источник**: dashboard-checklist-per-dashboard.md, существующие тесты  
**Версия**: 1.0.0

---

## Классификация проверок: автоматизируемые vs ручные

### Полностью автоматизируемые (MUST)

Эти проверки можно и должно автоматизировать как интеграционные тесты:

**Навигация:**
- ✅ Проверка наличия required top-level links (уже есть)
- ✅ Проверка отсутствия дублирующих ссылок (уже есть)
- ✅ Проверка времени handoff tokens (уже есть)
- ✅ Проверка forbidden vars в ссылках (уже есть)
- ✅ Проверка cross-scope markers (частично есть)
- ✅ Проверка required panel links (уже есть)
- ✅ Проверка KPI ownership (уже есть)
- ❌ Проверка что все ссылки открываются в том же окне (`targetBlank: false`) — НОВЫЙ ТЕСТ
- ❌ Проверка что текущий дашборд disabled в navigation — НОВЫЙ ТЕСТ

**Переменные и селекторы:**
- ✅ Проверка non-empty descriptions (уже есть)
- ✅ Проверка соответствия selector contract (уже есть)
- ✅ Проверка отсутствия forensic vars в non-explorer dashboards (уже есть)
- ✅ Проверка defaults по контракту (уже есть)
- ❌ Проверка что скрытые переменные justified — НОВЫЙ ТЕСТ (требует ревью описаний)
- ❌ Проверка dependency chains — НОВЫЙ ТЕСТ

**Дизайн-система:**
- ✅ Проверка layout overlap (уже есть)
- ✅ Проверка root gaps (уже есть)
- ✅ Проверка first-screen position (уже есть)
- ✅ Проверка recording rules (уже есть)
- ✅ Проверка status value mapping — CURRENT (dashboard contracts)
- ✅ Проверка thresholds configuration — CURRENT (full panel-contract inventory)
- ✅ Проверка panel-type visualization standards — CURRENT (dashboard contracts)
- ✅ Проверка заголовков по шаблону — CURRENT (panel title inventory)
- ✅ Проверка описаний панелей — CURRENT (full panel-contract inventory)

**JSON инварианты:**
- ✅ Проверка timezone/style/editable/graphTooltip (частично в layout tests)
- ❌ Проверка tags includes bioetl — НОВЫЙ ТЕСТ
- ❌ Проверка time.from/refresh по уровню дашборда — НОВЫЙ ТЕСТ

**Данные и метрики:**
- ✅ Проверка отсутствия `or vector(0)` в current-status panels (уже есть)
- ✅ Проверка units/decimals consistency — CURRENT (full panel-contract inventory)
- ✅ Проверка no-data/UNKNOWN policy — CURRENT (HTTP semantics + dashboard contracts)
- ✅ Проверка что range panels используют `$__range` — CURRENT (dashboard contracts)
- ✅ Проверка что current-status panels НЕ используют `$__range` — CURRENT

**Actionable links:**
- ✅ Проверка CTA links (частично есть)
- ✅ Проверка что critical panels имеют dataLinks — CURRENT (actionable-link contracts)
- ✅ Проверка runbook link format — CURRENT (full panel-contract inventory)

### Полностью ручные (SHOULD)

Эти проверки требуют человеческого суждения и не должны быть автоматизированы:

- Оценка UX/дизайна (визуальная эстетика)
- Оценка эффективности first-screen для operator triage
- Оценка качества описаний (смысловая полнота, не формат)
- Оценка правильности runbook references (содержание, не формат)
- Оценка адекватности threshold values (бизнес-логика)
- Оценка необходимости trust markers (контекстуальное решение)
- Оценка правильности KPI mirrors (смысловая корректность)

### Полуавтоматизируемые (MAY)

Эти проверки можно частично автоматизировать с ручным подтверждением:

- Проверка что critical signal не живёт в collapsed row — можно проверить position, но смысл требует ручной оценки
- Проверка collapsed row titles по incident scenario — можно проверить формат, но смысл требует ручной оценки
- Проверка что description объясняет OK/WARN/CRIT/UNKNOWN — можно проверить наличие токенов, но качество требует ручной оценки

---

## Предложение по расширению тестов

### Общие новые тесты

#### 1. test_dashboard_json_metadata_contract.py

```python
def test_all_dashboards_have_bioetl_tag():
    """Все shipped dashboards должны иметь tag 'bioetl'."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        tags = dashboard.get("tags", [])
        assert isinstance(tags, list)
        assert "bioetl" in tags, f"{dashboard_path.name} must have tag 'bioetl'"

def test_dashboard_time_refresh_by_level():
    """L0/L1 dashboards: 12h/30s, L2 forensic: 24h/1m."""
    expectations = {
        "bioetl-overview-v2.json": ("now-12h", "30s"),
        "bioetl-runtime.json": ("now-12h", "30s"),
        "bioetl-control-plane-v1.json": ("now-12h", "30s"),
        "bioetl-provider-health-v2.json": ("now-12h", "30s"),
        "bioetl-dq-v2.json": ("now-12h", "30s"),
        "bioetl-workflow-overview.json": ("now-12h", "30s"),
        "CLI quarantine inspect.json": ("now-24h", "1m"),
    }
    for dashboard_name, (expected_time, expected_refresh) in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        time_obj = dashboard.get("time")
        assert isinstance(time_obj, dict)
        assert time_obj.get("from") == expected_time
        refresh_obj = dashboard.get("refresh")
        assert refresh_obj is not None
        if isinstance(refresh_obj, str):
            assert refresh_obj == expected_refresh
        elif isinstance(refresh_obj, dict):
            assert refresh_obj.get("interval") == expected_refresh
```

#### 2. test_dashboard_visual_semantics.py

```python
def test_status_panels_have_correct_value_mapping():
    """Current-status stat panels должны иметь explicit value mapping."""
    status_dashboards = [
        "bioetl-runtime.json",
        "bioetl-provider-health-v2.json",
        "bioetl-dq-v2.json",
    ]
    for dashboard_name in status_dashboards:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            if "Status" in title or "Severity Matrix" in title:
                options = panel.get("options", {})
                assert options.get("colorMode") == "background"
                mappings = options.get("mappings", [])
                assert len(mappings) >= 3  # OK, WARN, CRIT
                mapping_values = {m.get("value") for m in mappings}
                assert 0 in mapping_values  # OK
                assert 1 in mapping_values  # WARN
                assert 2 in mapping_values  # CRIT

def test_thresholds_configuration():
    """Status panels должны иметь правильную thresholds конфигурацию."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            field_config = panel.get("fieldConfig", {})
            defaults = field_config.get("defaults", {})
            if defaults.get("color", {}).get("mode") == "thresholds":
                thresholds = defaults.get("thresholds", {})
                assert thresholds.get("mode") == "absolute"
                steps = thresholds.get("steps", [])
                assert len(steps) >= 2
                assert steps[0].get("value") is None  # green
                assert steps[0].get("color") in ("green", "#73BF69")
                if len(steps) >= 2:
                    assert steps[1].get("value") == 1  # orange
                if len(steps) >= 3:
                    assert steps[2].get("value") == 2  # red
```

#### 3. test_dashboard_panel_titles.py

```python
def test_panel_titles_follow_action_first_pattern():
    """Заголовки панелей должны начинаться с action verb."""
    action_verbs = {"Monitor", "Inspect", "Track", "Compare", "Review"}
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            if not title:
                continue
            # Пропускаем navigation/bus панели
            if "Navigation" in title or "Scope" in title:
                continue
            first_word = title.split()[0]
            assert first_word in action_verbs, (
                f"{dashboard_path.name}:{title} must start with action verb, "
                f"got {first_word!r}"
            )

def test_range_panels_include_window_in_title_or_description():
    """Range panels должны упоминать selected-range в title или description."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            description = panel.get("description", "")
            # Проверяем использует ли panel $__range
            uses_range = any(
                "$__range" in str(target.get("expr", ""))
                for target in panel.get("targets", [])
            )
            if uses_range:
                combined = f"{title} {description}".lower()
                assert "selected-range" in combined or "range" in combined, (
                    f"{dashboard_path.name}:{title} must mention selected-range "
                    "in title or description when using $__range"
                )
```

#### 4. test_dashboard_units_decimals.py

```python
def test_event_counters_have_correct_units_decimals():
    """Event counters должны иметь unit=short, decimals=0."""
    event_counter_keywords = {"Missing", "Failures", "Incompatibilities", "Events"}
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            if any(kw in title for kw in event_counter_keywords):
                field_config = panel.get("fieldConfig", {})
                defaults = field_config.get("defaults", {})
                assert defaults.get("unit") == "short", (
                    f"{dashboard_path.name}:{title} must have unit=short"
                )
                assert defaults.get("decimals") == 0, (
                    f"{dashboard_path.name}:{title} must have decimals=0"
                )

def test_timestamp_kpi_has_datetimeasiso_unit():
    """Timestamp KPI должен иметь unit=dateTimeAsIso."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            if "Timestamp" in title:
                field_config = panel.get("fieldConfig", {})
                defaults = field_config.get("defaults", {})
                assert defaults.get("unit") == "dateTimeAsIso", (
                    f"{dashboard_path.name}:{title} must have unit=dateTimeAsIso"
                )
```

#### 5. test_dashboard_critical_panels_have_actionable_links.py

```python
def test_p1_p2_panels_have_data_links():
    """P1/P2 operator panels должны иметь минимум один dataLink."""
    # Определение P1/P2 панелей по title/role
    p1_p2_patterns = [
        "Status",
        "Severity Matrix",
        "Blockers",
        "Top Causes",
        "Current Status",
    ]
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            if any(pattern in title for pattern in p1_p2_patterns):
                options = panel.get("options", {})
                links = options.get("dataLinks", [])
                assert len(links) >= 1, (
                    f"{dashboard_path.name}:{title} must have at least one dataLink"
                )

def test_runbook_links_follow_canonical_format():
    """Runbook links должны использовать canonical GitHub blob pattern."""
    canonical_prefix = "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/05-operations/runbooks/"
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            for link in _iter_panel_data_links(panel):
                url = link.get("url", "")
                title = link.get("title", "")
                if "runbook" in title.lower():
                    assert url.startswith(canonical_prefix), (
                        f"{dashboard_path.name}:{title} runbook link must use "
                        f"canonical GitHub blob pattern, got {url!r}"
                    )
```

#### 6. test_dashboard_variable_dependency_chains.py

```python
def test_variable_dependencies_match_selector_contract():
    """Dependency chains должны соответствовать selector contract."""
    expectations = {
        "bioetl-runtime.json": {
            "run_type": ["pipeline"],  # зависит от pipeline
            "stage": ["pipeline", "run_type"],  # зависит от pipeline и run_type
        },
        "bioetl-dq-v2.json": {
            "run_type": ["pipeline"],
            "stage": ["pipeline", "run_type"],
        },
    }
    for dashboard_name, dependencies in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        variables = {
            v.get("name"): v
            for v in dashboard.get("templating", {}).get("list", [])
            if v.get("name")
        }
        for var_name, expected_deps in dependencies.items():
            var = variables.get(var_name)
            assert var is not None, f"{dashboard_name} missing variable {var_name}"
            # Grafana не хранит dependency chains явно в JSON
            # Это проверка требует анализа query sources в selector contract
            # Можно проверить что query source использует правильные variables
```

---

### Специфические тесты для каждого дашборда

#### bioetl-overview-v2

```python
# test_grafana_overview_config.py (существующий, расширить)

def test_overview_first_screen_tier_1_panels():
    """Tier 1 panels должны быть на первом экране."""
    tier_1_panels = [
        "System Status",
        "First Action",
        "L0 Inputs",
    ]
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    for panel_title in tier_1_panels:
        panel = panels.get(panel_title)
        assert panel is not None
        assert panel.get("gridPos", {}).get("y", 999) <= 10

def test_overview_normalizes_workflow_pipeline():
    """Overview должен нормализовать workflow_<pipeline> в entity pipeline."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    # Проверить что queries используют entity pipeline, не workflow_<pipeline>
    # Это требует анализа PromQL expressions
```

#### bioetl-control-plane-v1

```python
# test_grafana_control_plane_config.py (НОВЫЙ файл)

def test_control_plane_global_diagnostics_block_exists():
    """Global diagnostics block должен быть отдельным."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    # Проверить наличие Global diagnostics panels
    # и что они не фильтруются по $pipeline/$run_type

def test_control_plane_first_screen_trust_summary():
    """First screen должен начинаться с answer-first trust cards."""
    trust_summary_panels = [
        "Monitor: Replay Safety State",
        "Inspect: Checkpoint Freshness Gap",
        "Monitor: Manifest / Ledger Integrity",
        "Inspect: Telemetry Missing",
    ]
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    for panel_title in trust_summary_panels:
        panel = panels.get(panel_title)
        assert panel is not None
        assert panel.get("gridPos", {}).get("y", 999) <= 12
```

#### bioetl-runtime

```python
# test_pipeline_runtime_dashboard.py (существующий, расширить)

def test_runtime_first_action_cta_contract():
    """Panel 9991 должна иметь 4 CTA."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = _find_panel_by_id(dashboard, 9991)
    assert panel is not None
    assert panel.get("title") == "First Action"
    options = panel.get("options", {})
    links = options.get("dataLinks", [])
    assert len(links) == 4
    link_titles = {link.get("title") for link in links}
    expected_ctas = {
        "Review current status",
        "Review range evidence",
        "Inspect top blockers",
        "Inspect active blocker",
    }
    assert link_titles == expected_ctas

def test_runtime_tracing_only_log_hygiene_collapsed():
    """Loki log-hygiene panels должны быть в collapsed row."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    # Проверить что panels с Loki queries находятся в collapsed row
    # Это требует анализа row structure
```

#### bioetl-provider-health-v2

```python
# test_grafana_provider_health_config.py (существующий, расширить)

def test_provider_health_first_action_cta_contract():
    """Panel 9002 должна иметь 3 CTA."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-provider-health-v2.json"))
    panel = _find_panel_by_id(dashboard, 9002)
    assert panel is not None
    assert panel.get("title") == "First Action"
    options = panel.get("options", {})
    links = options.get("dataLinks", [])
    assert len(links) == 3
    link_titles = {link.get("title") for link in links}
    expected_ctas = {
        "Review severity matrix",
        "Inspect critical providers",
        "Inspect provider top causes",
    }
    assert link_titles == expected_ctas

def test_provider_health_context_mapping_contract():
    """Переходы должны сохранять pipeline_context."""
    # Проверить что links из pipeline-scoped dashboards
    # включают var-pipeline_context=$pipeline
```

#### bioetl-dq-v2

```python
# test_grafana_dq_config.py (НОВЫЙ файл)

def test_dq_first_action_cta_contract():
    """Panel 9103 должна иметь 3 CTA."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = _find_panel_by_id(dashboard, 9103)
    assert panel is not None
    assert panel.get("title") == "Review: First Action"
    options = panel.get("options", {})
    links = options.get("dataLinks", [])
    assert len(links) == 3
    link_titles = {link.get("title") for link in links}
    expected_ctas = {
        "Review current status",
        "Inspect current reasons",
        "Open Silver Reject Explorer",
    }
    assert link_titles == expected_ctas

def test_dq_silver_reject_link_exists():
    """Panel 9102 должна иметь link к Silver Reject Explorer."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = _find_panel_by_id(dashboard, 9102)
    assert panel is not None
    options = panel.get("options", {})
    links = options.get("dataLinks", [])
    assert any(
        "Silver Reject Explorer" in link.get("title", "")
        for link in links
    )
```

#### bioetl-workflow-overview

```python
# test_grafana_workflow_dashboard_json_valid.py (существующий, расширить)

def test_workflow_overview_first_action_links():
    """Panel 9 должна иметь 5 CTA."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-workflow-overview.json"))
    panel = _find_panel_by_id(dashboard, 9)
    assert panel is not None
    assert panel.get("title") == "First Action"
    options = panel.get("options", {})
    links = options.get("dataLinks", [])
    assert len(links) == 5
    expected_targets = [
        "bioetl-runtime",
        "bioetl-dq-v2",
        "bioetl-provider-health-v2",
        "bioetl-control-plane-v1",
        "bioetl-overview-v2",
    ]
    for link in links:
        url = link.get("url", "")
        assert any(target in url for target in expected_targets)

def test_workflow_overview_no_visible_pipeline_run_type_selectors():
    """Workflow overview не должен иметь visible pipeline/run_type selectors."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-workflow-overview.json"))
    variables = {
        v.get("name"): v
        for v in dashboard.get("templating", {}).get("list", [])
        if v.get("name")
    }
    assert "pipeline" not in variables
    assert "run_type" not in variables
```

#### CLI quarantine inspect

```python
# test_grafana_silver_reject_config.py (существующий, расширить)

def test_silver_reject_first_action_cta_contract():
    """Panel 10 должна иметь 2 CTA."""
    dashboard = load_dashboard(Path("grafana/dashboards/CLI quarantine inspect.json"))
    panel = _find_panel_by_id(dashboard, 10)
    assert panel is not None
    assert panel.get("title") == "Review: First Action / No-Data Semantics"
    options = panel.get("options", {})
    links = options.get("dataLinks", [])
    assert len(links) == 2
    link_titles = {link.get("title") for link in links}
    expected_ctas = {
        "Review total rejects",
        "Review scoped summary",
    }
    assert link_titles == expected_ctas

def test_silver_reject_requires_single_select_pipeline():
    """Pipeline selector должен быть single-select."""
    dashboard = load_dashboard(Path("grafana/dashboards/CLI quarantine inspect.json"))
    variables = {
        v.get("name"): v
        for v in dashboard.get("templating", {}).get("list", [])
        if v.get("name")
    }
    pipeline = variables.get("pipeline")
    assert pipeline is not None
    assert pipeline.get("multi") is False
    assert pipeline.get("includeAll") is False

def test_silver_reject_payload_hash_is_textbox():
    """payload_hash должен быть textbox."""
    dashboard = load_dashboard(Path("grafana/dashboards/CLI quarantine inspect.json"))
    variables = {
        v.get("name"): v
        for v in dashboard.get("templating", {}).get("list", [])
        if v.get("name")
    }
    payload_hash = variables.get("payload_hash")
    assert payload_hash is not None
    assert payload_hash.get("type") == "textbox"
    assert payload_hash.get("current", {}).get("value") == ""
```

---

## Приоритизация реализации

### High Priority (неделя 1-2)

1. **test_dashboard_json_metadata_contract.py**
   - Проверка tags, time.from, refresh
   - Простая реализация, высокая ценность

2. **test_dashboard_visual_semantics.py**
   - Проверка value mapping, thresholds
   - Критично для status semantics

3. **test_dashboard_critical_panels_have_actionable_links.py**
   - Проверка dataLinks для critical panels
   - Важно для operator UX

4. **Специфические CTA contract тесты**
   - bioetl-runtime (panel 9991)
   - bioetl-provider-health-v2 (panel 9002)
   - bioetl-dq-v2 (panel 9103)
   - CLI quarantine inspect (panel 10)
   - bioetl-workflow-overview (panel 9)

### Medium Priority (неделя 3-4)

5. **test_dashboard_panel_titles.py**
   - Проверка action-first pattern
   - Проверка selected-range wording

6. **test_dashboard_units_decimals.py**
   - Проверка consistency
   - Важно для data quality

7. **Специфические layout тесты**
   - bioetl-control-plane-v1 global diagnostics
   - bioetl-runtime tracing-only collapsed

### Low Priority (неделя 5+)

8. **test_dashboard_variable_dependency_chains**
   - Сложная реализация
   - Меньшая критичность

9. **test_dashboard_range_panels_use_range**
   - Проверка что range panels используют $__range
   - Меньшая критичность

---

## Интеграционные тесты vs Unit тесты

### Интеграционные тесты (pytest.mark.integration)
- Чтение реальных JSON дашбордов
- Проверка контрактов с YAML files
- Время выполнения: 5-10 секунд
- Запуск в CI pipeline

### Unit тесты для QA скриптов
- Тестирование `scripts/engineering/qa/*`
- Проверка output format
- Время выполнения: <1 секунда
- Запуск в CI pipeline

---

## Обновление существующих тестов

### test_grafana_dashboard_links.py
- Добавить проверку `targetBlank: false`
- Добавить проверку что текущий дашборд disabled
- Расширить cross-scope markers проверку

### test_grafana_dashboard_first_screen_contract.py
- Добавить проверку Tier 1/2/3/4 structure для всех dashboards
- Добавить проверку что critical signal не в collapsed row

### test_grafana_variable_reference.py
- Добавить проверку dependency chains
- Добавить проверку что hidden variables justified

---

## Документация тестов

Для каждого нового тестового файла добавить:

1. Docstring с объяснением цели теста
2. Комментарии к сложным assertions
3. Ссылки на соответствующие разделы documentation
4. Примеры failure messages

---

## Мониторинг покрытия тестами

После реализации новых тестов:

1. Запустить `pytest tests/integration/test_grafana_*.py --cov=tests/integration/_grafana_test_support`
2. Обновить dashboard-checklist-per-dashboard.md с пометками `[TESTED]`
3. Обновить dashboard-audit-checklist.md с ссылками на соответствующие тесты
4. Создать matrix: проверка → тестовый файл → функция

---

## Заключение

Предложенные тесты покрывают:
- **~60%** полностью автоматизируемых проверок из чек-листа
- **~30%** полуавтоматизируемых проверок (формат + ручная оценка)
- **~10%** полностью ручных проверок (UX/смысл)

Фокус на:
- JSON metadata и визуальной семантике
- CTA contract для critical panels
- Layout и first-screen structure
- Units/decimals consistency

Это обеспечит:
- Регрессионную защиту для критических требований
- Автоматизированную валидацию контрактов
- Быстрый feedback при изменениях дашбордов
