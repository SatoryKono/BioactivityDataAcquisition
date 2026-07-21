# Настройка PyCharm для разработки BioETL

Целевая рабочая среда: **PyCharm 2026.1.4 stable**, **Python 3.13.7** и
Windows. Правила качества принадлежат репозиторию (`pyproject.toml`,
`.editorconfig`, `.gitattributes`, scripts и CI); PyCharm только исполняет их.

## 0. Фиксация исходного состояния

Перед любыми изменениями зафиксируйте базу для обратной трассировки:

На этом baseline верно зафиксированы три наблюдения:
1. В IDE ограниченный effective heap является частой причиной нестабильного опыта.
2. Ранее отсутствовала единая integration точка для toolchain (`ruff`/`mypy`/`pytest`) в конфигурации проекта и CI.
3. Был избыток AI-плагинов, что добавляло фоновую нагрузку и конфликты inline completion.

1. Версии: `PyCharm`, Python interpreter, `bioetl`, `ruff`, `mypy`.
2. Список включённых plugins, отдельно выделив AI inline-completion:
   - какие плагины активны;
   - какой из них inline provider;
   - какие плагин-пакеты выполняют анализ/форматирование.
3. Текущие run/debug-конфигурации и их аргументы.
4. Текущие статусы инспекций (`PyPep8Inspection`, `Ruff`, `Mypy`).
5. Базовые диагностические снимки:
   - `Help | Diagnostic Tools | Activity Monitor` (за 3–5 минут после старта).
   - `Settings | Memory Usage` (`Show Memory Indicator` + текущий `-Xmx` через UI).
6. Физическая RAM системы (например, из Task Manager/параметров Windows) для выбора
   стартового `-Xmx`.
7. Размер репозитория и число файлов (включая включённые в проект каталоги и исключённые
   из анализа), чтобы обосновать исключения и ожидаемую стоимость индексирования.
8. Длительность `Project | Loading/Background Analysis` (project analysis): время
   до первого idle по `Activity Monitor` до/после изменений настроек.
9. Память/heap в двух точках:
   - `heap` сразу после открытия проекта;
   - `heap` через 30–60 минут рабочей сессии без тяжёлых операций.
10. Idle CPU: фиксируйте длительность до устойчивого состояния «низкой нагрузки»
    после старта и после периода работы.
11. Время запуска ключевых проверок: `pytest-fast`, `mypy-full`, `ruff-check` (измерить хотя бы
    один cold и один warmed запуск каждого, чтобы видеть эффект кэша).

Сохраните baseline в комментарий в `# pycharm-setup` (или личную заметку по проекту),
чтобы можно было сравнить эффект после изменения профиля.
При внесении изменений соблюдайте правило: **меняйте только одну группу настроек за раз**.
Иначе невозможно установить причинно-следственный эффект конкретного шага.

### 0.1. Основная рабочая IDE

Для основной разработки используйте только **PyCharm 2026.1.4 (Stable)**.

- Установите/обновите stable через JetBrains Toolbox (рекомендуется) или установщик
  с [официальной страницы Other versions](https://www.jetbrains.com/pycharm/download/other/).
- При необходимости держите EAP 2026.2 только в отдельной установке/профиле (через
  Toolbox), не используйте его для ежедневной работы с BioETL.
- Экспортируйте IDE settings или включите `Settings Repository`/`Backup and Sync`
  (не одновременно): это нужно для восстановления после переустановки.
  При этом `secrets` и локальные paths не входят в полезный экспорт.
- Проверка состояния: `Help | About` → версия должна быть `PyCharm 2026.1.4`.

## 1. Нормализовать проект и окружение

### 1.1 Подготовка окружения

BioETL использует `uv` и отдельные окружения для Windows и WSL. Для PyCharm,
запущенного в Windows, подготовьте `.venv-win` поддерживаемым wrapper-ом:

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1
```

Затем выберите interpreter:

```text
$PROJECT_DIR$\.venv-win\Scripts\python.exe
```

Окружение проекта отдельное, **без наследования global site-packages**, и проект
устанавливается editable.
Проверка:

```powershell
.\.venv-win\Scripts\python.exe --version
.\.venv-win\Scripts\python.exe -c "import bioetl; print(bioetl.__file__)"
```

Ожидаемая версия Python — `3.13.7`. Не добавляйте `PYTHONPATH`: shared run
configurations отключают `ADD_CONTENT_ROOTS` и `ADD_SOURCE_ROOTS` и полагаются
на editable install. WSL-команды используют отдельное Linux-окружение и не
должны переиспользовать `.venv-win`.

Dev tools (`ruff`, `mypy`, `pytest`, `black` при необходимости) устанавливайте через
текущий dependency manager (`uv`) и фиксируйте в `pyproject.toml` + `uv.lock`.
Не используйте глобальные установки tooling через системный pip.

### 1.2 Канонический repository clone

Оставьте **один канонический clone** проекта для основной работы.
Дополнительные ветки или эксперименты открывайте в отдельных Git worktree:
`git worktree add ...`. Не открывайте несколько независимых full-копий одного и
того же checkout как разные проекты в одном рабочем процессе — это повышает
дублирование индексации и конфликтов конфигурации.

### 1.3 Архивные копии вне active content root

Архивные копии/legacy-копии (`backup`, `old-*`, `archive*`, старые
`BioactivityDataAcquisition*`-клонии) выносите вне active `Project content root`
или явно mark as Excluded, чтобы они не индексировались и не влияли на search/indexing.  
Активный project root не должен содержать архивные копии и крупные generated datasets.

## 2. Настроить производительность IDE

### 2.1 CLI и tests из clean environment

- Проверка для Windows: `scripts`, `CLI` и `pytest` запускаются из проектного
  environment (`.venv-win`) без ручного `PYTHONPATH`.
- Окна запуска:
  - `.\.venv-win\Scripts\python.exe`
  - конфигурации `Run/Debug`/скрипты CI.
- Валидация: убедиться в конфигурациях, что нет `PYTHONPATH=$PROJECT_DIR$/src` и
  аналогичных ручных переопределений.
- Включите:
  - **Settings | Memory Usage | Show Memory Indicator**.
  - визуальный контроль загрузки памяти через встроенный индикатор после перезапуска.

### 2.2 Project Structure и производительность

В **Settings > Project > Project Structure** задайте:

| Путь | Категория |
| --- | --- |
| `src` | Sources Root (обязательно) |
| `tests` | Test Sources Root (обязательно) |
| `.venv`, `.venv-win`, `.venv-wsl` | Excluded |
| `data`, `output`, `logs`, `profiles`, `profile`, `cache`, `tmp`, `venv` | Excluded |
| generated `data/*`, `artifacts`, `reports`, `htmlcov`, `.venv-win`, `.venv-wsl` | Excluded |
| `tests/fixtures` | не исключать |

Локальный `.idea/` целиком не публикуется, потому что PyCharm добавляет туда
machine-specific roots и runtime state. Для active checkout держите один canonical clone;
другие ветки открывайте через отдельные Git worktree и отдельные окна IDE.

### 2.2.1 Нормализация корневых каталогов

- `src` — обязательный единственный `Sources Root` для Python-кода проекта.
- `tests` — обязательный `Test Sources Root` для корректной работы тестирования.
- Не добавляйте другие активные каталоги с исходным кодом как Sources Root поверх `src`
  без архитектурной необходимости (иначе рост индексинга и дублирование кэша).

### 2.3 Настройка JVM heap

- Выберите `-Xmx` по измерениям (замеры memory pressure/heap churn при типичных нагрузках):
  - 8 GB RAM: старт 2–2.5 GB,
  - 16 GB RAM: старт 3 GB,
  - 32 GB+ RAM: старт 4 GB,
  - далее поднимайте только при повторяющихся warning’ах по memory pressure.
- Важно: `-Xmx` управляет только JVM памяти PyCharm, но не решает OOM в Python-процессах ETL.
  Для ETL используйте отдельную диагностику Python-процессов и настройку алгоритма
  (`batch size`, параллелизм, типы данных, лимиты окружения).
- `custom GC flags` отсутствуют: не добавляйте дополнительные JVM flags (`-XX`)
  без подтверждённой диагностики memory pressure/GC.

### 2.4 Локальные диски для производительности

- Проверьте, что project root, `.venv`/`.venv-win`, и каталоги PyCharm System/Cache
  (IDE settings) находятся на локальном SSD, а не на network/cloud-synced path.
- Для Windows это проверяется через path-реестр/ссылки в интерпретаторе и IDE settings.

### 2.5 Windows Defender и security policy (по согласованию)

- На Windows рассматривайте Microsoft Defender exclusion только для доверенного
  project directory и только после проверки/разрешения локальной security policy.
- Не добавляйте исключения для кешей/venv/проекта без формального согласования.

### 2.6 Этап 2: критерии и методика контроля производительности

- При нагрузочном тесте используйте `Help | Diagnostic Tools | Activity Monitor`
  для оценки эффекта; не отключайте встроенные функции IDE «наугад».
- Критерии завершения этапа:
  - нет `low-memory warning`;
  - IDE не уходит в устойчивый swap;
  - после завершения background tasks `idle CPU` быстро возвращается в низкий диапазон;
  - typing/navigation latency измерено как метрика и не имеет регресса по сравнению с baseline.
  - все заявленные улучшения подтверждены измерениями (время запуска, latency, heap/GC),
    а не только непроверенными процентами.
  - для ETL дополнительно фиксируйте метрики Python-процессов на одинаковом входе (RSS/USS,
    пики памяти на этапе transform/write), чтобы не смешивать ETL OOM с IDE heap.

## 3. Сделать pyproject.toml источником истины

Локальные настройки IDE не должны быть основным источником правил качества:
`pyproject.toml` — первичный источник для formatter/linter/type checker/pytest опций.

### 3.1 Рекомендуемый стартовый минимальный конфиг (новый проект)

Для нового проекта стартовый профиль:

```toml
[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I"]

[tool.mypy]
python_version = "3.13"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"
```

Это стартовая заготовка, а не финальная политика BioETL. Наборы `B`, `UP`, `SIM`, `RUF`,
исключения, per-module overrides и coverage threshold добавляются только после анализа
текущей базы ошибок в репозитории. Coverage threshold и pytest coverage-аргументы
выполняются только в `pytest-coverage`, а не глобально для остальных pytest-конфигураций.

Принцип целостности: `Ruff`, `mypy`, `pytest` используют конфигурацию
репозитория (pyproject/lock/scripts, а где применимо — `configs`) и должны
идентично совпадать с параметрами в CI.

## 4. Подключить инструменты в PyCharm

### 4.0. Чек-лист по устранению глобального coverage

- `pyproject.toml` не должен задавать `--cov` как глобальный default в `addopts`.
- Не добавляйте `--cov` в `Tools | Python Integrated Tools | Testing` как общий дефолт.
- `pytest-fast`, `pytest-full`, `pytest-debug` запускаются без coverage.
- `pytest-coverage` — единственная pytest конфигурация для флага `--cov*`, `--cov-report*` и порогов покрытия.

1. Подключите и настройте инструменты через UI PyCharm (без ручного редактирования XML), затем сохраните `run/debug` конфигурации как shared project files и только после этого продолжайте настройку следующей группы.

### 4.1 Ruff, форматирование и inspections

Ruff — единственный владелец lint, formatting и import optimization:
добавьте ровно один formatter и ровно один import optimizer, чтобы не было
дублирования форматирования/импортных автофиксов:

Важно: в PyCharm 2026.1 не используйте `External Tools` как основной путь
для `ruff`/`black`/`pytest`/`mypy` — эти инструменты выполняются через
штатную IDE-интеграцию (Tools/Actions on Save + Run/Debug + `pyproject.toml`/CI).
Дополнительно: не допускайте одновременного активного Ruff Format и Black formatter.
Выберите один из них и зафиксируйте политику в `pyproject.toml`, `.editorconfig`
и project/shared IDE-конфигурациях.

1. **Settings > Python > Tools > Ruff**: Enable, Interpreter mode,
   Inspections, Formatting и Import optimizer — включены.
2. **Settings > Python > Tools > Black**: выключен, если активен Ruff formatter
   (или включён только в ручном режиме, когда Black избран как единственный formatter).
3. **Tools > Actions on Save**: включите ровно один formatter и ровно один
   import optimizer (в режиме Auto/On save по выбору команды), без второго
   formatter/import optimizer в цепочке.
4. Project inspection profile отключает дублирующую `PyPep8Inspection`, но
   сохраняет semantic Python inspections. Ruff diagnostics остаются включены.
5. Нельзя включать одновременно Ruff Format и Black как форматтеры для одного и того же
   проекта; в каждой среде выбирается ровно один formatter-source-of-truth.
6. Не используйте `mypy --strict $FilePath$` как основной quality gate; этот режим
   оставляйте только как локальную/editorial диагностику, а основной контроль типа
   выполняйте через `mypy-full` (project target / CI-equivalent).

Ширина форматирования — фактическое значение BioETL `88` из
`pyproject.toml`; `.editorconfig` и project code style показывают тот же right
margin. Универсальный пример `100` из исходного плана здесь не применяется,
потому что он расходился бы с formatter-ом репозитория.

### 4.1.1 Форматтер-политика (выберите один вариант)

Для текущего плана по умолчанию:

1. Ruff format активен.
2. Black отключён в PyCharm и не используется для форматирования в Actions on Save.
3. На уровне `pyproject.toml` фиксировать `format`-политику только через `ruff`.

Альтернативный вариант (если переход на Ruff невозможен):

1. Ruff format disabled (formatter только в lint/import roles).
2. Black включён как единственный formatter с управлением через PyCharm/CLI.
3. В репозитории и CI нельзя оставлять конфликтующие formatter-инструкции.

### 4.2 Типизация

`mypy` — единственный основной type checker (все остальные типа-чекеры не
используются как параллельные gates):

1. Используйте shared configuration `mypy-full`, которая выполняет:

```powershell
.\.venv-win\Scripts\python.exe -m mypy src tests
```

Строгость и Python compatibility level читаются из `pyproject.toml`. Не
запускайте `mypy --strict $FilePath$`: проверка одного файла теряет
межмодульный контекст. Mypy plugin, Pyright, basedpyright, Pyrefly и `ty` не
включаются как параллельные real-time checkers; их наличие в dev dependencies
не делает их IDE quality gate.

### 4.3 Shared run/debug configurations

В `configs/ide/pycharm/runConfigurations/` публикуются только переносимые
configuration templates:

| Имя | Назначение |
| --- | --- |
| `pytest-fast` | unit/smoke набор: быстрый локальный прогон `tests/unit` без `coverage` |
| `pytest-full` | весь локальный набор `tests` без `network` и `benchmark` |
| `pytest-coverage` | отдельный прогон coverage: `--cov=bioetl`, отчёты `term-missing` и `xml`, порог `85` |
| `pytest-debug` | текущий файл теста без `coverage` (обязательное `--no-cov` при необходимости), с `-s`, без `xdist` |
| `ruff-check` | `ruff check src tests` |
| `ruff-format-check` | `ruff format --check src tests` |
| `mypy-full` | `mypy src tests` с project config |
| `quality-gate` | `python -m scripts.engineering.ci quality-gate` |
| `BioETL smoke (offline fixture)` | `chembl_activity` на трёх tracked Bronze records, без API |

Все configurations используют project interpreter, working directory
`$PROJECT_DIR$`, package/module entry points и не содержат secrets или
абсолютных пользовательских путей. Coverage не включён в fast/debug и не является
глобальным дефолтом в `Run/Debug`/`On Save` для pytest.
Каждая configuration должна запускаться после `clean clone` без ручного `PYTHONPATH`
и без user-specific path overrides.

Для CLI-проверки тех же поверхностей используйте поддерживаемые Windows
wrappers:

```powershell
.\scripts\engineering\dev\run_pytest.ps1 tests\unit --narrow --timeout=120 --lf
.\scripts\engineering\dev\run_mypy.ps1
.\.venv-win\Scripts\python.exe -m ruff check src tests
.\.venv-win\Scripts\python.exe -m ruff format --check src tests
.\.venv-win\Scripts\python.exe -m scripts.engineering.ci quality-gate
```

### 4.4 Debugger и smoke safety

- Используйте локальный PyCharm debugger и `pytest-debug`.
- Coverage в обычных debug-сценариях отключена по умолчанию: в debug конфигурациях `pytest-debug` и локального pipeline-debug не должно быть `--cov`/coverage hooks.
- Coverage и xdist в debug configuration отключены.
- В PyCharm для Python нет отдельного режима `GDB-compatible` как глобальной debugger-настройки; используйте реальные режимы: локальный debug через `debugpy`, fallback на `pydevd` по необходимости и Remote Debug/Attach только по факту удалённого запуска.
- Attach to subprocess, gevent и remote debugging включайте только для
  подтверждённого сценария.
  - Remote debugging настраивайте только при фактическом удалённом execution.
  - Для локального debug на Python 3.13 сначала используйте `debugpy`; если есть
    несовместимость в конкретном сценарии, возвращайтесь к `pydevd`.
  - Профилирование запускайте через `Run | Profile` только для конкретного
  воспроизводимого сценария и репрезентативного входного набора; профилирование
  создаёт overhead и не включается глобально для всех ETL-процессов.
- Shared smoke configuration читает
  `tests/fixtures/bronze/chembl/activity/` и отключает health/backend servers;
  она не обращается к production API. Для работы в обычном dirty dev tree
  configuration явно использует `degraded_observable`; replay-ready проверяется
  отдельными reproducibility tests и clean-clone gate.
- Live API runs остаются локальными и должны явно называться `Live`; их нельзя
  публиковать с credentials или включать в общий quality gate.

### 4.5 AI plugins

Для inline completion активен ровно один provider (в baseline — GitHub Copilot).
Windsurf /
Codeium и DeepSeek inline completion должны быть выключены; Claude/Google AI
plugins также не должны конкурировать за inline UI. Один отдельный ручной
chat/agent integration допустим, если он не включает inline completion и его
политика передачи project context проверена.

## 5. Разделить test configurations

Создайте через `Run | Edit Configurations...` отдельные project-level конфигурации и сохраните их как `shared` (project files):

1. `pytest-fast` — scope `tests/unit`, без coverage.
2. `pytest-full` — scope `tests`, исключения `network` и `benchmark`, без coverage.
3. `pytest-coverage` — полный target + `--cov=bioetl` + `--cov-report=term-missing` + `--cov-report=xml` (или проектные эквиваленты), с coverage threshold по CI (по-умолчанию `85`).
4. `pytest-debug` — текущий test file/local smoke, **без coverage** (`--no-cov`), с `-s`, без `xdist`.
5. `mypy-full` — полный target проекта (`src tests` или CI-эквивалент), без запуска на Save.
6. `quality-gate` — repository-level скрипт/CI command, который последовательно вызывает Ruff, mypy и tests.

Не запускайте полный `mypy` и полный `pytest` на каждом `Save`; привяжите их только к ручным конфигурациям.
`pytest` с `--cov` не включайте как глобальный default; coverage-опции должны выполняться
только в `pytest-coverage`/профильных скриптах.
Не дублируйте одинаковые параметры проверки между UI-конфигурациями, `pyproject.toml` и CI без явной необходимости — источник истины должен оставаться единым (в первую очередь `pyproject.toml` + CI-скрипты).
Проверочный критерий переноса: после `clean clone` import и запуск `pytest-fast`/`mypy-full` работают из project files и project interpreter без добавления `PYTHONPATH` в run/debug конфигурациях.

## 6. Создать переносимые run/debug configurations для pipeline configuration

Для задач пайплайна используйте только переносимые шаблоны конфигураций:

- pipeline конфигурации живут в `configs/ide/pycharm/runConfigurations/`;
- каждая конфигурация хранится как project file (shared) и не содержит локальных путей или secrets;
- конфигурации воспроизводимы на clean clone: запуск не требует ручного `PYTHONPATH` или абсолютных путей на машине.
- Secrets/credentials не хранятся в `.idea/`; для исполнения pipeline-скриптов секреты берутся только из
  локального безопасного механизма (не через run/debug XML).
- запуск выполняется через `quality-gate` или точечные конфигурации (`pytest-*`, `mypy-full`), а не через ad-hoc XML в локальном `.idea/`.
- Для переносимости и воспроизводимости каждый pipeline-конфиг должен задавать:
  - `Target`: `module name` или официальный `console script` (не локальные абсолютные пути);
  - `Working directory`: `$PROJECT_DIR$`;
  - `Interpreter`: project interpreter (`.venv-win` на Windows);
  - `Parameters`: только dev/smoke config и безопасные defaults;
  - `Environment`: локальный `.env` (secrets не коммитить), переменные не указывать inline в XML/конфиге.
  - `Store as project file`: включено.
  - `Run target`: небольшой детерминированный fixture dataset для smoke-проверок pipeline.

1. Дополнительно, если команда явно разрешает запуск production-like сценария с
   рабочей станции, создайте отдельную configuration для полного `production-like`
   прогонки, чтобы не смешивать её с smoke/debug путями.

## 7. Исправить templates и scaffolding

1. Создать группу `BioETL` и привязать к ней шаблоны/скрипты проекта (run/debug, file templates, скелетные шаблоны конфигураций), чтобы исключить разнобой между командами.
2. В live templates использовать синтаксис `$VARIABLE$` и `$END$`.
3. Оставить live templates только для коротких проверенных `API` calls, чтобы не зацементировать архитектуру в шаблоне.
4. Полный pipeline вынести в project file template или generator, где детерминизм реализован через библиотечные primitives и проверенный код.
5. Проверить правильный синтаксис templates (live templates, file templates, скрипты скелета).
6. Каждый template должен опираться на существующие API проекта/пакета/порты, а не вводить несуществующие вызовы.
7. Каждый template должен импортировать существующие symbols из проектной базы/портов/сервисов и не вводить недекларированные импорты.
8. Каждый template должен иметь typed signatures (аннотации типов).
9. В обязательной бизнес-логике шаблонов не использовать `pass`; обязательные методы должны явно декларировать поведение (например, `NotImplementedError` или конкретную реализацию). Snippet/template не заменяет реализацию или deterministic control-flow.
10. Не создавать wall-clock time внутри transformation; время должно приходить из context/параметров/clock provider.
11. Каждая используемая в шаблонах логика должна опираться только на library primitives, которые покрыты tests.
12. Экспортировать templates или хранить project templates в VCS.
13. Признак приёмки секции templates: детерминизм (сортировки/hashing/retry/clocking) подтверждается только кодом и тестами, не snippets.

## 8. Закрепить детерминизм в коде и тестах

1. Создать единый RunContext с полями: `run_id`, `started_at`, `seed`, `source_version`, `config_hash`.
2. Передавать `RunContext` в pipeline, logger и output metadata.
3. Реализовать канонизацию `schema`, `dtypes`, порядка колонок, `timezone` и `nulls` перед экспортом и валидацией.
4. Реализовать стабильную сортировку с полным tie-breaker key.
5. Вычислять hash из канонического набора значений (canonicalized values), а не из случайного dataframe representation.
6. Добавить `atomic write` primitive и тестировать поведение при сбое/интеррупте.
7. Добавить reproducibility test: два запуска с одинаковым input/config/context дают одинаковые output hashes.
8. Повторный pipeline run (smoke или production-like) обязателен: второй прогон должен матчиться по output hash/метаданным с первым.

Важно: детерминизм устанавливается контрактами кода (canonicity, atomic write, сортировка, hash), а не snippet-логикой.

## 9. Упростить AI-слой

1. Оставить ровно один inline completion provider.
2. Остальные AI-плагины отключить как inline completion, либо перевести только в ручной chat/agent режим.
3. Проверить duplicate shortcuts между AI-инструментами и автоматическую индексацию контекста; устранить конфликты вручную.
4. Сравнить оставшиеся AI-плагины/варианты на одинаковом наборе BioETL-задач по latency, accuracy/acceptance, rate ошибок, нагрузке и выбору provider закрепить выбором.
5. После выбора удалить или отключить проигравшие плагины, чтобы убрать лишнюю фоновую нагрузку и конфликтующие UI-механизмы.
6.

## 10. Настроить Git и совместное использование IDE settings

1. Добавить `.editorconfig`:

```editorconfig
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4
max_line_length = 100
```

2. Добавить `.gitattributes`:

```gitattributes
* text=auto
*.py text eol=lf
*.toml text eol=lf
*.yaml text eol=lf
*.yml text eol=lf
*.json text eol=lf
*.md text eol=lf
*.bat text eol=crlf
```

3. Добавить минимальный `.gitignore`:

```gitignore
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
.coverage.*
coverage.xml
htmlcov/
build/
dist/
*.egg-info/

# Project-specific generated data and reports
/data/raw/
/data/interim/
/data/processed/
/output/
logs/
profiles/

# Local environment and secrets
.env
.env.local

# Игнорировать локальный `.idea/` целиком. Общие templates репозитория живут в
# `configs/ide/pycharm/`, а не в `.idea/`.
.idea/
```

4. Адаптировать список data directories под проект: не игнорировать fixtures и small reference datasets, если они участвуют в `tests`.
5.

## 11. Профилирование и итоговая проверка

1. IDE performance: использовать `Help | Diagnostic Tools | Activity Monitor` + `Settings | Memory Usage | Show Memory Indicator`.
2. Прогонять профилирование на выбранной `run configuration` с фиксированным input (`run`-time profile [12]) и анализировать hotspot'ы.
3. Не профилировать production API calls без явного контроля rate limits и side effects (безопасный стенд или replay-режим только).
4. Сравнить показатели профилирования/производительности с baseline (до изменений).
5. Зафиксировать конечную конфигурацию в `docs/development/pycharm.md` (или зеркально в актуальной локальной runtime-структуре, если путь отличается).
6. stable PyCharm используется для основной работы, EAP изолирован.

## 12. Что хранится в Git

Root `.gitignore` полностью игнорирует локальный `.idea/`. В Git публикуются
переносимые templates с той же относительной структурой:

- `configs/ide/pycharm/runConfigurations/` — только перечисленные выше
  configurations;
- `configs/ide/pycharm/codeStyles/`;
- `configs/ide/pycharm/inspectionProfiles/`;
- `configs/ide/pycharm/pyLspTools.xml`.

После clean clone скопируйте templates в локальный `.idea/`:

```powershell
New-Item -ItemType Directory -Force .\.idea | Out-Null
Copy-Item -Recurse -Force .\configs\ide\pycharm\* .\.idea\
```

или в Bash/WSL:

```bash
mkdir -p .idea
cp -R configs/ide/pycharm/. .idea/
```

Не публикуются `workspace.xml`, `.iml`, shelves, Local History, data sources,
plugin state, MCP/AI tokens и локальные SDK paths; `.idea` в tracked shared templates
не содержит secrets/credentials. Любые `.env`/`.env.*` остаются secret-bearing
machine-local files и не изменяются этим workflow.

## 13. Приёмка

Критерии приёмки:
План считается внедрённым, когда выполнены все условия:

1. PyCharm stable и Python соответствуют целевым версиям.
2. `import bioetl` работает без `PYTHONPATH`.
3. Ruff форматирует файл один раз, а style warnings не дублируются.
4. `pytest-fast`, `pytest-debug`, `mypy-full` и offline smoke
   запускаются из `.venv-win`.
5. `git status` не показывает `workspace.xml`, `.iml`, shelves, secrets или
   абсолютные paths; `.idea/` не содержит secrets/credentials.
6. Повторный pipeline run проходит reproducibility test: при одинаковом input/config/context
   второй прогон даёт те же output hashes.
7. `Settings | Data Sharing`/Usage statistics: включение/выключение является
  настройкой privacy (в стабильном релизе JetBrains телеметрия по умолчанию
  отключена, в EAP включена), а не инструментом заметной оптимизации
  производительности IDE; сторонние плагины могут иметь собственные сборы данных.
8. Под нагрузкой используйте `Help | Diagnostic Tools | Activity Monitor`;
   после фоновых задач CPU возвращается к низкому уровню; heap и durations
   фиксируются фактическими значениями.
9. Все заявленные улучшения подтверждаются измерениями и сравнением с baseline
   (время запуска/операции, latency/p95, heap/GC), а не непроверяемыми процентами.
10. CLI/тестовые run-конфигурации используют проектный интерпретатор (`.venv-win`)
   без ручного `PYTHONPATH`.
11. Активен ровно один inline AI provider; конфликты inline completion/plugins отсутствуют.
12. В интерфейсе PyCharm включён **Settings | Memory Usage | Show Memory Indicator**.
13. `-Xmx` выбран по RAM и изменялся только через UI `Memory Usage`; остальные JVM flags (`-XX:*`) не добавлялись без диагностики.
14. `pyproject.toml` и `uv.lock` соответствуют установленным dev tools; в окружении
   нет глобальных `pip install`-инстансов для `ruff/mypy/pytest`.
15. Проект, `.venv-win` и пути IDE system/cache используются на локальном SSD и
   не находятся на cloud/network sync path.
16. Для Windows Microsoft Defender exclusion для project directory разрешён только для
   доверенного каталога и только при наличии разрешения security policy.
17. В процессе работы пайплайна и локальной разработки не используются устаревшие
    `External Tools` для `ruff`/`black`/`pytest`/`mypy` как основной путь; используются
    нативные интеграции PyCharm и project/CI конфигурации.
18. Форматтерный пайплайн единый: нельзя одновременно включать Ruff format и Black как
    активные formatter-источники для одного проектного потока (On Save/Actions/CI).
19. Основной mypy-gate выполняется только через full project scope (`mypy-full`);
   `mypy --strict $FilePath$` не рассматривается как заменяющий его.
20. `coverage` не используется как глобальный дефолт для pytest в IDE и проектных Run/On Save-конфигурациях; отдельная конфигурация `pytest-coverage` — единственный источник отчётов и порогов покрытия.
