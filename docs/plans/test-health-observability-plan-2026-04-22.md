# Test Health Observability Plan

*Status: Working planning artifact (non-normative)*
*Created: 2026-04-22*
*Scope: measurable pytest lane execution, run summaries, history, and CI test-health reporting*

## Цель

Сделать тесты управляемыми не только по green/red, а по измеримым данным:

- сколько запусков было;
- какие suites запускались;
- сколько было падений, ошибок и skip;
- какие тесты нестабильны;
- где накапливается тестовый долг.

## Текущее состояние

В проекте уже есть хорошая база:

- `pytest-xdist`;
- `pytest-timeout`;
- `pytest-cov`;
- `pytest-vcr`;
- markers в `pytest.ini` / `pyproject.toml`;
- `configs/quality/test_matrix.yaml`;
- `configs/quality/test_health_reporting.yaml`;
- поддерживаемый sharded runner:
  `scripts/engineering/dev/run_pytest_sharded.sh`.

Поэтому не нужно начинать с нового фреймворка. Нужно добавить единый сбор
фактов и отчетность поверх существующей pytest-инфраструктуры.

Базовый локальный способ запуска для больших прогонов должен оставаться тем,
который уже используется в проекте:

```powershell
$env:PYTHONPATH="src"
bash scripts/engineering/dev/run_pytest_sharded.sh --stream --keep-coverage-files --coverage-dir .coverage-sharded -- -vv --cov-report=html
```

В Bash-окружении эквивалент:

```bash
PYTHONPATH=src bash scripts/engineering/dev/run_pytest_sharded.sh --stream --keep-coverage-files --coverage-dir .coverage-sharded -- -vv --cov-report=html
```

Все новые test-health команды должны уметь работать поверх
`run_pytest_sharded.sh` и его опций, а не заменять его новым независимым
раннером.

## Состояние реализации на 2026-04-22

- Этап 1 выполнен: canonical lanes живут в
  `configs/quality/test_matrix.yaml` под `test_lanes.lanes`, включая runner
  backend metadata и единственный `coverage-verify` repo-wide coverage gate.
- Этап 2 начат: `scripts/engineering/qa/test_health.py` агрегирует один или
  несколько pytest JUnit XML файлов в
  `reports/quality/test-runs/{run_id}.json`.
- Этап 3 начат: `python -m scripts.engineering.qa run-tests --suite ...`
  делегирует выполнение существующим `run_pytest.sh` /
  `run_pytest_sharded.sh`, добавляет JUnit artifacts и пишет JSON summary.
- Для мягкой CI-миграции добавлен `summarize-junit`, который агрегирует уже
  существующие JUnit XML jobs в тот же JSON summary format.
- Этап 4 начат минимально: `python -m scripts.engineering.qa test-health --last 30` читает JSON summaries и показывает run/failure/skip rollup, top
  failing nodeids, flaky candidates и новые падения. Эта же команда может
  принять `--suite ... --junit-glob ...` и сначала агрегировать JUnit XML в JSON
  summary, чтобы прямые `run_pytest_sharded.sh --junit-dir ...` запуски сразу
  попадали в rollup.
- Этап 5 начат: aggregator пишет эвристическую `classification` для failures
  по `phase`, `message` и `file`; правила живут в
  `configs/quality/test_health_classifiers.yaml` и могут быть переопределены
  через `--classifier-config`.
- Этап 6 начат: `test-health --markdown-out ...` может писать combined
  Markdown rollup, а `--github-step-summary` добавляет его в
  `$GITHUB_STEP_SUMMARY`. `.github/workflows/tests.yml` теперь собирает
  test-health summaries из существующих JUnit artifacts в `duration-telemetry`;
  PR reporting остается следующим шагом.

## Этап 1. Зафиксировать тестовые lanes

Ввести именованные lanes, чтобы каждый запуск был сравнимым:

- `unit-fast`: `tests/unit`, без `slow`, `benchmark`, `memory`;
- `integration-replay`: integration + VCR/replay, без live network;
- `contracts`: schema/contracts/snapshots;
- `architecture`: layer/contracts/governance checks;
- `e2e`: медленный lane, отдельно;
- `memory`: Neo4j/MCP lane, отдельно от coverage;
- `coverage-verify`: единственный lane, который применяет repo-wide coverage gate.

Результат: каждый CI/local запуск имеет `suite_name`, а не просто произвольную
команду `pytest`.

Для sharded запусков `suite_name` остается логическим именем всего запуска, а
отдельные shards должны фиксироваться как детализация внутри того же `run_id`.

## Этап 2. Единый формат результата

Использовать нативный pytest JUnit XML как источник истины. Для обычного
pytest-запуска это один XML:

```bash
python3 -m pytest ... --junitxml=reports/quality/test-runs/junit/{run_id}.xml
```

Для sharded запуска это набор XML-файлов под одним `run_id`, например:

```text
reports/quality/test-runs/junit/{run_id}/{shard_name}.xml
```

Поверх JUnit XML добавить небольшой агрегатор, который пишет JSON:

```text
reports/quality/test-runs/{run_id}.json
```

Минимальная схема:

```json
{
  "run_id": "...",
  "suite": "unit-fast",
  "shards": ["S1-domain-core", "S2-comp-iface"],
  "started_at": "...",
  "duration_seconds": 123.4,
  "command": "...",
  "git_sha": "...",
  "ci_job": "...",
  "counts": {
    "collected": 1000,
    "passed": 980,
    "failed": 3,
    "errors": 1,
    "skipped": 14,
    "xfailed": 2,
    "xpassed": 0
  },
  "failures": [
    {
      "nodeid": "tests/...",
      "file": "tests/...",
      "phase": "call",
      "message": "AssertionError..."
    }
  ]
}
```

Важно: `failed` и `errors` считать отдельно. Ошибка fixture/import/setup не
равна обычному assertion failure.

Aggregator должен поддерживать оба режима:

- один JUnit XML для нешардированного запуска;
- несколько JUnit XML файлов для `run_pytest_sharded.sh`, объединенных в один
  `run_id` и один logical `suite`.

## Этап 3. Wrapper для запуска

Добавить один CLI-wrapper:

```bash
python -m scripts.engineering.qa run-tests --suite unit-fast
python -m scripts.engineering.qa run-tests --suite contracts
```

Wrapper не должен становиться новым главным pytest runner. Его роль:
оркестрировать test-health metadata и делегировать выполнение существующему
поддерживаемому runner-у. Для больших локальных/CI прогонов canonical backend:

```bash
PYTHONPATH=src bash scripts/engineering/dev/run_pytest_sharded.sh <runner-options> -- <pytest-options>
```

PowerShell пример:

```powershell
$env:PYTHONPATH="src"
bash scripts/engineering/dev/run_pytest_sharded.sh --stream --keep-coverage-files --coverage-dir .coverage-sharded -- -vv --cov-report=html
```

Wrapper должен:

- выбрать pytest args по suite;
- выбрать backend runner по suite (`run_pytest_sharded.sh` для shardable lanes,
  прямой pytest только для узких lanes, где это явно проще);
- создать `run_id`;
- включить `--junitxml` или shard-aware JUnit output directory;
- после pytest запустить aggregator;
- вернуть тот же exit code, что pytest;
- не скрывать stdout/stderr pytest;
- принимать и пробрасывать опции sharded runner-а (`--stream`,
  `--keep-coverage-files`, `--coverage-dir`, `--wave`, `--shard`) и pytest args
  после `--`.

Это даст стабильный сбор статистики без изменения тестов.

## Этап 4. История и подсчет падений

Добавить rollup-команду:

```bash
python -m scripts.engineering.qa test-health --last 30
```

Она читает `reports/quality/test-runs/*.json` и строит:

- количество запусков по suite;
- pass rate по suite;
- top failing nodeids;
- новые падения против предыдущего green baseline;
- flaky candidates: тесты, которые и падали, и проходили за последние N запусков;
- infrastructure failures: setup/import/vcr/env errors;
- skip trend.

Отдельно считать:

- `run_count`: сколько раз suite запускался;
- `failure_count`: сколько запусков suite завершились non-green;
- `test_failure_count`: сколько отдельных test cases упало;
- `unique_failing_tests`: сколько уникальных nodeid падало.

## Этап 5. Классификация падений

Добавить простую классификацию без ML:

- `assertion`: обычный regression;
- `setup_error`: fixture/import/config;
- `vcr_error`: cassette/plugin/network replay;
- `timeout`: `pytest-timeout`;
- `snapshot_drift`: snapshot/artifact mismatch;
- `environment`: Docker/Neo4j/API/env var;
- `collection`: pytest collection/import failure.

Классификация должна быть эвристической и переопределяемой. Сначала достаточно
regex по `message`, `phase`, `file`.

## Этап 6. CI интеграция

В CI для каждого lane сохранять artifacts:

- JUnit XML;
- JSON run summary;
- combined rollup markdown.

PR comment или job summary должен показывать краткую сводку:

```text
unit-fast: 982 passed, 2 failed, 11 skipped, 82.4s
contracts: 240 passed, 1 failed, 65 skipped, 21.3s
Top failures:
- tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py::...
```

Merge-blocking остается обычный pytest exit code + quality gate. Health classes
из `test_health_reporting.yaml` остаются informational.

## Этап 7. Политики улучшения тестов

После появления статистики улучшать тесты по очереди:

1. Сначала fixing setup/collection/VCR errors, потому что они портят доверие к
   результатам.
1. Потом snapshot/artifact drift, потому что это часто governance debt.
1. Потом flaky tests по top frequency.
1. Потом слишком медленные tests и serial bottlenecks.
1. Потом coverage gaps по `configs/quality/test_matrix.yaml`.

## Критерии готовности

- Любой pytest lane создает JUnit XML и JSON summary.
- Можно ответить на вопросы: "сколько запусков было за неделю?", "какой suite
  чаще падает?", "какие 10 тестов падают чаще всего?".
- CI показывает краткий test health summary.
- История не блокирует merge сама по себе, но делает regressions видимыми.
- Существующие pytest markers и `test_matrix.yaml` не дублируются, а
  используются как источник классификации.
