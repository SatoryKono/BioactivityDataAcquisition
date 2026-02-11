# Architecture Audit Report

Date: 2026-02-11
Scope: `configs/pipelines/**`, `configs/dq/**`, `configs/filter/**`, `scripts/validate_pipeline_configs.py`, `scripts/config_gap_analysis.py`, `src/bioetl/infrastructure/config_loader.py`

## Executive Summary

- Total findings: 4
- Critical (MUST): 0
- Moderate (SHOULD): 4
- Informational (MAY): 2

Ключевой вывод: фактическая конфигурационная модель в целом согласована с ADR-029 (convention-based defaults) и ADR-026 (composite pipelines), но текущие скрипты аудита/валидации дают систематические ложноположительные сигналы и требуют приведения к текущей архитектуре.

## Moderate Findings

## [SHOULD] `validate_pipeline_configs.py` применяет только стандартную схему к composite-конфигам

**Location**: `scripts/validate_pipeline_configs.py:96-113`

**Rule Violated**: Архитектурная консистентность инструментов валидации (ADR-026 + ADR-025 совместно).

**Evidence**:

```python
configs_dir = Path("configs/pipelines")
schema_path = configs_dir / "_schema.json"
...
valid, error_msg = validate_config(config_path, schema)
if not valid:
    errors.append(f"{config_path}: {error_msg}")
```

Команда верификации:

```bash
.venv/bin/python scripts/validate_pipeline_configs.py
```

Возвращает ошибки по composite-конфигах вида `'pipeline_name' is a required property`, хотя composite-конфиги валидируются отдельной схемой `configs/pipelines/_composite_schema.json`.

**Impact**: CI/локальная проверка конфигов шумит ошибками и маскирует реальные дефекты.

**Recommendation**:

```python
if "/composite/" in str(config_path):
    schema = load_schema(configs_dir / "_composite_schema.json")
else:
    schema = load_schema(configs_dir / "_schema.json")
```

______________________________________________________________________

## [SHOULD] `validate_pipeline_configs.py` не учитывает доменный alias entity (`crossref/work` ↔ `publication`)

**Location**: `scripts/validate_pipeline_configs.py:56-70`, `configs/pipelines/crossref/publication.yaml:46-48`

**Rule Violated**: Корректность доменного нейминга и проверок (glossary/конвенции entity aliases).

**Evidence**:

```python
expected_suffix = f"{provider}/{entity}"
if path and not path.endswith(expected_suffix):
    warnings.append(...)
```

```yaml
# Explicit path needed because entity_type is 'work' (CrossRef API term)
# but filter file uses project entity name 'publication'.
filter_config_file: ../../filter/entities/crossref/publication.yaml
```

**Impact**: ложные предупреждения по путям `.../crossref/publication`, которые в проекте допустимы как internal entity alias.

**Recommendation**:

```python
ENTITY_ALIASES = {("crossref", "work"): "publication"}
expected_entity = ENTITY_ALIASES.get((provider, entity), entity)
expected_suffix = f"{provider}/{expected_entity}"
```

______________________________________________________________________

## [SHOULD] `config_gap_analysis.py` противоречит ADR-029, считая `sink.bronze` обязательным

**Location**: `scripts/config_gap_analysis.py:82-85`

**Rule Violated**: ADR-029 (sink-пути и секции могут вычисляться по convention).

**Evidence**:

```python
# Check bronze sink
if "bronze" not in sink:
    gaps.medium.append("Missing sink.bronze section")
```

При этом в загрузчике конфигов есть автозаполнение:

```python
sink = config.setdefault("sink", {})
for layer_name in ("bronze", "silver", "gold"):
    layer = sink.setdefault(layer_name, {})
```

**Impact**: отчёт о gap'ах создаёт SHOULD-нарушения там, где поведение штатно обеспечивается кодом загрузчика.

**Recommendation**:

```python
# Не помечать как medium, если sink.bronze отсутствует
# и включён ADR-029 convention defaults
if "bronze" not in sink:
    gaps.low.append("sink.bronze omitted (allowed by ADR-029 conventions)")
```

______________________________________________________________________

## [SHOULD] Несогласованность правил между `validate_pipeline_configs.py` и runtime-loader

**Location**: `scripts/validate_pipeline_configs.py:75-84`, `src/bioetl/infrastructure/config_loader.py:151-209`

**Rule Violated**: Единый источник правды для config-contract (tooling drift).

**Evidence**:

- Валидатор требует/проверяет наличие `sort_by` статически.
- Runtime-loader автоматически проставляет `sort_by.columns` на базе `primary_keys`.

```python
# validator
if "sort_by" not in sink:
    warnings.append(...)
```

```python
# runtime
sort_by = layer.setdefault("sort_by", {})
sort_by.setdefault("columns", list(primary_keys))
```

**Impact**: валидация и рантайм по-разному трактуют корректность одного и того же конфига.

**Recommendation**:

- Вынести policy-функции defaults/aliases в общий модуль.
- Переиспользовать их в обоих скриптах.

## Informational Findings

1. Composite-конфиги архитектурно отделены и имеют собственную схему (`_composite_schema.json`), что соответствует ADR-026.
1. В `crossref/publication.yaml` явно документирована доменная трансляция `work`↔`publication`, что снижает риск silent-errors при поддержке.

## Positive Observations

- Конфиги стандартных pipeline содержат типовые поля (`pipeline_name`, `provider`, `entity_type`, `primary_keys`, `silver_table`, `gold_table`).
- Runtime-конфигуратор реализует convention-based defaults для file references и sink paths, уменьшая дублирование.
- Архитектурные тесты импортных границ проходят успешно (`tests/test_architecture.py`).

## Remediation Plan

### Phase 1 — Stabilize validation tooling (1-2 дня)

1. Обновить `scripts/validate_pipeline_configs.py`:
   - schema switch: standard/composite;
   - alias-aware path hierarchy checks;
   - добавить `--mode runtime-parity` для учёта ADR-029 defaults.
1. Добавить smoke-тесты скрипта на 3 сценария:
   - standard config;
   - composite config;
   - crossref work/publication alias.

### Phase 2 — Align gap analysis with ADR-029 (1 день)

1. Переклассифицировать отсутствие `sink.bronze`/`sink.gold` как допустимое при convention defaults.
1. Добавить в отчёт явные поля:
   - `is_convention_resolved`;
   - `requires_explicit_override`.

### Phase 3 — Single source of truth for config policies (2-3 дня)

1. Выделить модуль policy:
   - `resolve_expected_entity(provider, entity_type)`;
   - `apply_sink_defaults(config)`;
   - `validate_required_contract(config, mode)`.
1. Подключить модуль в:
   - `validate_pipeline_configs.py`;
   - `config_gap_analysis.py`;
   - (опционально) pre-commit hook.

### Phase 4 — CI hardening (0.5 дня)

1. Добавить CI step:
   - `validate_pipeline_configs.py --strict --mode runtime-parity`.
1. Отдельный job для composite-schema regressions.

## Verification Log

```bash
find configs -maxdepth 3 -type f | sort
.venv/bin/python scripts/validate_pipeline_configs.py
.venv/bin/python scripts/config_gap_analysis.py
.venv/bin/pytest tests/test_architecture.py -q
nl -ba scripts/validate_pipeline_configs.py | sed -n '1,260p'
nl -ba scripts/config_gap_analysis.py | sed -n '1,280p'
nl -ba configs/pipelines/_schema.json | sed -n '1,220p'
nl -ba configs/pipelines/_composite_schema.json | sed -n '1,220p'
nl -ba configs/pipelines/composite/publication.yaml | sed -n '1,220p'
nl -ba configs/pipelines/crossref/publication.yaml | sed -n '1,220p'
nl -ba src/bioetl/infrastructure/config_loader.py | sed -n '1,260p'
```
