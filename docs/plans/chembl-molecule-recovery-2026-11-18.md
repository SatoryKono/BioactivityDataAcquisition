# ChEMBL Molecule: исправление фаз и восстановление Gold

Status: proposed
Class: implementation_plan
Owner: BioETL Team
Last verified: 2026-11-18
Lifecycle: supporting_context

План исправляет потерю `max_phase` и ошибочный допуск в Gold, добавляет
регрессионную защиту и отдельное восстановление сохранённого Bronze.
Это план реализации: изменение этого документа не означает выполнения
исправлений или приёмки данных.

База аудита: `8efd52d62f9cc1a23e75d9808355e35b7692616a`.
Риск реализации — **V3**: меняются нормализованные значения, `content_hash`
и состав Gold. Порядок: RF-001 → RF-002 → RF-003/RF-004 → RF-005 →
RF-006 → RF-007 → RF-008A → RF-008B.

План подчинён [RULES](../00-project/RULES.md),
[ADR-050](../02-architecture/decisions/ADR-050-silver-structural-gold-semantic-filter-boundary.md)
и [процедуре backfill/rebuild](../05-operations/runbooks/backfill-rebuild.md).
Он не меняет нормативные контракты.

## RF-001 — исходное состояние и границы восстановления

Перед реализацией повторно зафиксировать HEAD, рабочую ветку, фактические
изменения, effective-config digest, исходный manifest и контрольные суммы
Bronze/Silver. Параллельные изменения Grafana сохранить. Реализацию вести
в отдельной ветке; новое дерево создавать только штатным helper внутри
`D:/github`, соблюдая корневые ограничения на `.env.*`.

Проверенный исходный Bronze:

```text
data/workflows-limit1000-20261118T042057Z/chembl_molecule/output/bronze/chembl/molecule
```

| Показатель проверенного снимка | Исходное состояние | Цель исправленной обработки |
| --- | ---: | --- |
| Bronze: записи / уникальные molecule ID | 1000 / 1000 | Снимок и набор ID сохранены |
| Silver: строки | 1000 | 1000 |
| Bronze: заполненный `max_phase` | 1000 | Соответствующие значения сохранены |
| Silver: заполненный `max_phase` | 0 | 1000 |
| Значения `0.5` | Bronze: 3; Silver: 0 | Silver и Gold: 3 |
| Gold Delta-таблица | Не создана | 1000 строк при прохождении строгого контракта |
| Оставшиеся три Gold-фильтра | Проходят 1000 записей | Поведение сохранено |
| Поле `potential_duplicate` в Bronze | Отсутствует у всех 1000 записей | Искусственное значение не добавляется |

Составить перечень затронутых запусков, downstream-таблиц и потребителей.
Исправление этого снимка не считать восстановлением всех downstream-данных;
для отложенных пересчётов явно сохранить статус и следующий шаг.

Для восстановления, live-диагностики и строгой обработки нового снимка
подготовить **разные** новые корни данных, отчётов и архивов. В каждом
дочернем процессе задать `BIOETL_DATA_DIR`, `BIOETL_REPORT_ROOT` и
`BIOETL_ARCHIVE_ROOT`, не изменяя `.env` и постоянное окружение.
Проверить физические разрешённые пути таблиц, CSV, checkpoint, quarantine,
control-plane, отчётов и архивов; они не должны пересекаться с оригиналами.

**Готовность:** определён точный набор входных файлов и их digest;
исходные и новые выходные пути разделены, контекст запуска проверен.

## RF-002 — тесты, воспроизводящие дефекты

Добавить тесты полного пути извлечения бизнес-полей и нормализации Molecule,
например `tests/unit/application/pipelines/chembl/test_molecule_transformer_contract.py`.

| Исходный `max_phase` | Результат |
| --- | --- |
| `"4.0"` | `4` |
| `"-1.0"` | `-1` |
| `"0.5"` | `0.5` |
| `0.5` | `0.5` |
| `None` | `None` |
| `1.5`, `4.9`, `5` | `INVALID_DATA:max_phase` |

Проверить не только доменный normalizer: дефект находится до него, в
извлечении трансформера. Для записи с корректным ID и недопустимой фазой
проверить DQ/quarantine reason; отдельно сохранить проверку действительно
отсутствующего ID. Причины не должны подменять друг друга.

В [тестах загрузчика фильтров](../../tests/unit/infrastructure/config/test_filter_config_loader.py)
проверить реальную объединённую конфигурацию Molecule: допуск корректной записи
без `potential_duplicate`, сохранение ограничений `molecule_type`,
`structure_type`, `inorganic_flag` и наличие полей фильтра в доступной проекции.

**Готовность:** новые regression cases воспроизводят дефекты исходного кода;
существующее golden-ожидание `0.5` не переписано под ошибочный результат.

## RF-003 — сохранить исходную фазу до нормализации

В [трансформере](../../src/bioetl/application/pipelines/chembl/molecule_transformer.py)
перенести `max_phase` из `int_fields` в `simple_fields`.
Преобразование и проверку допустимых кодов оставить существующему
[normalize_molecule_max_phase](../../src/bioetl/domain/normalization/profiles/chembl_molecule.py).
Общую `safe_int` не менять.

**Готовность:** случаи RF-002 проходят через production-путь; дробная фаза
сохранена, недопустимые числа отклонены до записи с правильным reason code.

## RF-004 — исправить Gold-допуск

В [конфигурации Molecule](../../configs/entities/chembl/molecule.yaml) удалить
только условие `gold_filters.columns.potential_duplicate=0`. Сохранить:

- `molecule_type=Small molecule`, `structure_type=MOL`, `inorganic_flag=0`;
- обязательный `molecule_id`;
- extraction parameters, source-profile version и hash-политику;
- строгую Gold-валидацию и действующую DQ-политику.

Зафиксировать новый effective-config digest и причину изменения допуска.
Отсутствующему полю не назначать фиктивный ноль.

**Готовность:** 1000 записей снимка проходят оставшиеся фильтры;
отрицательные примеры по действующим ограничениям по-прежнему исключаются.

## RF-005 — полный цикл, хэши и история SCD2

Расширить [E2E Molecule](../../tests/e2e/test_chembl_molecule_e2e.py): читать
фактическую Gold Delta-таблицу, сверять ID/число допустимых записей, фазы
Bronze/Silver/Gold, строгий контракт и причины отрицательных исключений.
Использовать локальные fixtures/VCR без API; обязательный regression test
не считать пройденным при skip или ослабленной проверке.

Проверить сохранность `molecule_id` и `entity_id`, пересчёт `content_hash`
по исправленным значениям и неизменность алгоритма/набора hash-полей.
Существующие normalization/hash golden-тесты должны сохранять свой контракт.

Для идемпотентности выполнить **две записи в одну и ту же тестовую таблицу**:

1. Первый запуск создаёт исправленные данные и фиксирует полный снимок Gold,
   включая текущие и исторические строки, `_version`, `_valid_from`, `_valid_to`.
2. Второй запуск получает тот же Bronze и ту же исправленную конфигурацию,
   но новый `run_id` и более поздний occurrence timestamp. Использовать
   `incremental`, без очистки таблиц и без перенаправления в новый каталог.
3. Сверить бизнес-значения, идентификаторы, хэши и **всю** историю SCD2:
   числа текущих/исторических строк и значения version/validity-полей
   остаются прежними. Одной текущей строки на ключ недостаточно.

Повторный `backfill` не использовать как доказательство идемпотентности:
он очищает Silver и Gold. Число технических Delta commits само по себе
не подменяет проверку логических строк и истории.

В [интеграции composite Molecule](../../tests/integration/composite/test_molecule_pipeline.py)
проверить дробную фазу seed и сохранность join keys.

**Готовность:** подтверждены реальная запись Gold, стабильные хэши и отсутствие
новых SCD2-версий для неизменившегося input без предварительной очистки.

## RF-006 — документация, generated artifacts и проверки

Обновить [справочник Molecule](../04-reference/providers/chembl/molecule.md),
`CHANGELOG.md` и инструкцию восстановления ранее обработанных данных.
Использовать штатные генераторы:

```powershell
.\.venv-win\Scripts\python.exe -m scripts.docs passports generate
.\.venv-win\Scripts\python.exe -m scripts.docs passports check
.\.venv-win\Scripts\python.exe -m scripts.engineering.qa report-module-coverage --allow-missing-coverage-xml
```

Выполнить targeted Ruff, RF-002/RF-005, существующие normalization/golden/hash
тесты, тесты extraction parameters и загрузчика фильтров. Дополнительно:

```powershell
.\.venv-win\Scripts\python.exe -m scripts.schema validate-configs --strict
.\.venv-win\Scripts\python.exe -m pytest tests/architecture/test_module_coverage_inventory_freshness.py
.\.venv-win\Scripts\python.exe -m scripts.docs check-links
.\.venv-win\Scripts\python.exe -m scripts.docs check-drift --runtime-mirrors --freshness
```

После изменений локальных Markdown-ссылок или служебных заголовков обновить
documentation cleanup inventory владельцем и выполнить его `--check`.
Runtime-зеркала синхронизировать только при изменении соответствующих
runtime-инструкций. До восстановления закрепить точную версию исправленного
кода и config; не выдавать один SHA за описание неучтённого dirty diff.

**Готовность:** обязательные проверки проходят без ослабления контрактов;
generated artifacts получены генераторами. Локальные результаты и CI
на конкретном SHA отражены отдельно.

## RF-007 — восстановление исторического Bronze

Использовать `CachedBronzeDataSource` и входной каталог RF-001. Команды ниже
выполняются только в подготовленном дочернем окружении восстановления
с новыми data/report/archive roots. Никакие команды в этом плане ещё не выполнены.

```powershell
$bronze = 'D:/github/BioactivityDataAcquisition/data/workflows-limit1000-20261118T042057Z/chembl_molecule/output/bronze/chembl/molecule'
$restoreArgs = @(
  '-m', 'bioetl', 'run', '--pipeline', 'chembl_molecule',
  '--run-type', 'backfill', '--limit', '1000',
  '--use-cached-bronze', '--cached-bronze-path', $bronze,
  '--cached-bronze-date', '2026-11-18',
  '--no-exact-replay', '--no-ensure-observability-backend'
)

# Сначала preview очистки; это ещё не обработка данных.
& .\.venv-win\Scripts\python.exe @restoreArgs --dry-run
```

Проверить preview, фактические физические пути и отсутствие общих выходов
с оригиналами. При несовпадении остановиться. Только после подтверждённого
preflight выполнить утверждённый запуск без интерактивного запроса:

```powershell
& .\.venv-win\Scripts\python.exe @restoreArgs --yes
```

`--yes` не является обходом preflight или разрешением очищать исходные данные.
Сохранить exit code, новый manifest/effective-config, ссылки на исходный
run/manifest, набор и digest прочитанных Bronze batches. Это новая обработка
исправленным кодом, не exact replay ошибочного запуска.

**Готовность:** значения всех 1000 фаз восстановлены, включая три `0.5`;
наборы ID и funnel согласованы; Gold проходит строгий контракт и содержит
ожидаемые строки; исходные контрольные суммы не изменились. Необъяснённые
исключения или новые ошибки Gold оставляют результат неприёмочным до разбора
и регрессионной защиты.

## RF-008A — отдельная live-диагностика и новый Bronze

Не использовать прежнюю команду `workflow run chembl_molecule --limit 1000`
как готовый live-рецепт: её default `replay_ready` требует cached-Bronze и
отклоняет такой запуск в preflight.

Для получения нового API-снимка использовать отдельный диагностический запуск
на исправленной версии, с явно выбранным `degraded_observable` и собственными
новыми data/report/archive roots:

```powershell
.\.venv-win\Scripts\python.exe -m bioetl run `
  --pipeline chembl_molecule --run-type incremental --limit 1000 `
  --required-persistence-profile degraded_observable `
  --no-cached-bronze --no-exact-replay `
  --no-ensure-observability-backend
```

Этот режим — отдельная явная диагностика. Не изменять глобальный persistence
default, strict family policy, `.env` или основной workflow ради её запуска.
Если действующий контекст запрещает диагностический профиль, сохранить отказ
и отдельно определить поддерживаемый способ capture; не обходить проверку.

Зафиксировать manifest, exit code, дату/состав/digest нового Bronze, фактический
DQ и пределы диагностики. Для нового API-снимка проверять фактическую допустимость,
а не требовать исторических 1000 допущенных записей или ровно трёх `0.5`.
Результат RF-008A **не заменяет строгую приёмку**.

## RF-008B — строгая обработка нового снимка и closeout

После успешного RF-008A проверить и сохранить новый Bronze как неизменяемый
вход. В третьем отдельном выходном окружении выполнить workflow с явно заданным
`replay_ready` и cached-Bronze. `$newBronze` и `$newBronzeDate` берутся из
проверенного manifest RF-008A:

```powershell
.\.venv-win\Scripts\python.exe -m bioetl workflow run chembl_molecule `
  --limit 1000 --required-persistence-profile replay_ready `
  --use-cached-bronze --cached-bronze-path $newBronze `
  --cached-bronze-date $newBronzeDate --no-exact-replay `
  --no-ensure-observability-backend
```

Проверить реальный exit/status, Gold Delta, фазы, ID, DQ/funnel и manifest
строгого запуска. Диагностический результат A и строгий результат B отражать
раздельно. Мониторинг связывать с соответствующими run/manifest ID;
зелёный dashboard или успешный старт не подменяют проверку данных.

Итоговый отчёт включает исходные AUD-001/AUD-002/AUD-003, SHA реализации,
config digest, run/manifest IDs, результаты тестов, сверку исторического и
нового снимков, downstream-статусы, локальные checks и CI на этом SHA.
Выполнить обязательный [Proof-or-Stop closeout](../04-reference/contracts/proof-or-stop-evidence.md).
`NOT_TESTED`, `DEGRADED` и отсутствующие receipts не объявлять строгим PASS.

**Откат:** результаты сохраняются отдельно; до приёмки потребители не
переключаются. При отказе сохранить оригинальные Bronze/Silver, отчёты и
результаты диагностики. Не перезаписывать принятые таблицы поверх более новых
операций. Возврат потребителей выполнять только по проверенному manifest.

Бюджеты долга не увеличиваются. Формальное состояние долга считать
`unchanged`, пока измерения не подтвердят улучшение; наличие новых тестов
само по себе не доказывает снижение долговых метрик.

## Статус этой редакции

Документ учитывает замечания аудита к RF-005, RF-007 и RF-008. Исправления кода,
обработка данных, live API, CI и приёмка pipeline ещё не выполнены.
