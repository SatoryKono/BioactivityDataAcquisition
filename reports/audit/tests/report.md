# Аудит тестовой системы — 20260825T164939Z-tests-cycle-80651be4d1

## Scope и метод

Аудит выполнен для `tests/`, связанных quality-артефактов, `pyproject.toml`, `configs/quality/test_matrix.yaml` и Windows runner `scripts/engineering/dev/run_pytest.ps1`. В качестве ограниченного доказательного прогона выбрана каноническая lane `unit-fast`: полный `tests/` не запускался, поскольку пользователь не задал явные `LANE=full` или `SCOPE=all`, а workflow запрещает начинать с неограниченного тяжёлого прогона.

| Параметр | Значение |
| --- | --- |
| Branch | `audit/grok-tests-cycle-20260825` |
| Base SHA | `e736cc1578` |
| Previous audit | `20260820T081148Z-tests-cycle-16c9a2b6e6` |
| Runtime | Windows, Python 3.13.7, pytest 9.1.1 |
| Test files / functions | 2,367 / 24,972 |
| CI workflow files | 46 |
| Skip/xfail occurrences | 305 |
| Governance and residual snapshots | present |

## Подтверждённый finding

| ID | Severity | Class | State | Evidence |
| --- | --- | --- | --- | --- |
| `FAIL-COVERAGE-INVENTORY-FRESHNESS` | High / P1 | `fixture` | `PROVEN`, `BLOCKED` | Freshness guard сравнил committed SHA `52f9…` с current SHA `9fd9…`; live scorecard: 7.41; unit-fast остановлена на assertion scorecard floor. |

Текущий `module-coverage-inventory.json` содержит **74 unmeasured modules**. Поэтому `build_architecture_quality_scorecard()` даёт 7.41 вместо порога 8.0, хотя материализованный scorecard остаётся на устаревшем 9.41. Расхождение выводит из строя `tests/unit/infrastructure/quality/test_architecture_quality_scorecard.py::test_architecture_quality_scorecard_has_stable_weighted_shape`.

> Это не flaky finding: воспроизведён и через targeted freshness guard, и через изолированное вычисление live scorecard.

## Проверенные контуры

| Контур | Результат |
| --- | --- |
| Canonical test lanes | Матрица задаёт serial `unit-fast`, а coverage truth — только `coverage-verify`. |
| Изоляция сети | Выбранная lane исключает `slow`, `benchmark`, `memory`, `repo_backed`, `subprocess_backed`, `fs_contract`; unit baseline не требует live network. |
| Skip/xfail | Обнаружены 305 occurrences; в baseline присутствуют платформенные skips (symlink privilege, Windows threading) и необязательный `openpyxl`; не классифицированы как remediation. |
| Coverage truth | Нельзя считать актуальным: freshness guard failed. |
| GitHub deduplication | Open issues по запросу `coverage inventory freshness scorecard` не найдены. Issue не создавалась, так как `ALLOW_ISSUE_WRITE=false`. |

## Remediation и проверка

Необходим полный канонический `coverage-verify` на чистом `src/bioetl` для создания согласованного `reports/coverage/coverage.xml`; затем допустима генерация `reports/quality/module-coverage-inventory.json` из этого XML. После этого должны быть повторно запущены freshness guard, scorecard test и unit-fast lane. Обновление inventory без нового coverage XML не создаёт coverage truth и поэтому не является допустимым обходом.

## Surface score

**1/3.** Имеется серьёзная воспроизводимая ошибка quality-gate, затрагивающая основной быстрый feedback lane. Критических data-loss, secret или layer-boundary finding не обнаружено в выполненном scope.

## Артефакты

- `reports/audit/tests/findings.json`
- `reports/audit/test-cycle/20260825T164939Z-80651be4d1-test/cycle-1/baseline.log`
- `reports/audit/test-cycle/20260825T164939Z-80651be4d1-test/cycle-1/coverage-freshness.log`
- `reports/audit/test-cycle/20260825T164939Z-80651be4d1-test/cycle-1/scorecard-live-metrics.json`
- `reports/audit-runs/20260825T164939Z-tests-cycle-80651be4d1/github-issue-search.json`
