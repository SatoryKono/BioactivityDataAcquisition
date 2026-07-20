# Настройка PyCharm для разработки BioETL

Целевая рабочая среда: **PyCharm 2026.1.4 stable**, **Python 3.13.7** и
Windows. Правила качества принадлежат репозиторию (`pyproject.toml`,
`.editorconfig`, `.gitattributes`, scripts и CI); PyCharm только исполняет их.

## 1. Подготовка окружения

BioETL использует `uv` и отдельные окружения для Windows и WSL. Для PyCharm,
запущенного в Windows, подготовьте `.venv-win` поддерживаемым wrapper-ом:

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1
```

Затем выберите interpreter:

```text
$PROJECT_DIR$\.venv-win\Scripts\python.exe
```

Окружение не наследует global site-packages, а проект устанавливается editable.
Проверка:

```powershell
.\.venv-win\Scripts\python.exe --version
.\.venv-win\Scripts\python.exe -c "import bioetl; print(bioetl.__file__)"
```

Ожидаемая версия Python — `3.13.7`. Не добавляйте `PYTHONPATH`: shared run
configurations отключают `ADD_CONTENT_ROOTS` и `ADD_SOURCE_ROOTS` и полагаются
на editable install. WSL-команды используют отдельное Linux-окружение и не
должны переиспользовать `.venv-win`.

## 2. Project Structure и производительность

В **Settings > Project > Project Structure** задайте:

| Путь | Категория |
| --- | --- |
| `src` | Sources Root |
| `tests` | Test Sources Root |
| `.venv`, `.venv-win`, `.venv-wsl` | Excluded |
| generated `data/*`, `output`, `artifacts`, `reports` | Excluded |
| `logs`, `profiles`, `tmp`, caches, `htmlcov` | Excluded |
| `tests/fixtures` | не исключать |

Локальный `.idea/*.iml` не публикуется, потому что PyCharm может добавлять туда
machine-specific roots. Для active checkout держите один canonical clone;
другие ветки открывайте через отдельные Git worktree и отдельные окна IDE.

Для машины с 32 GB RAM стартовый IDE heap — `4096 MB`. Меняйте только `-Xmx`
через **Settings > Memory Usage**, включите **Show Memory Indicator** и
проверяйте результат после перезапуска. Не добавляйте custom GC/code-cache
flags без диагностики.

## 3. Ruff, форматирование и inspections

Ruff — единственный владелец lint, formatting и import optimization:

1. **Settings > Python > Tools > Ruff**: Enable, Interpreter mode,
   Inspections, Formatting и Import optimizer — включены.
2. **Settings > Python > Tools > Black**: выключен.
3. **Tools > Actions on Save**: Ruff formatting/import optimization включайте
   для изменяемого кода; встроенный Python formatter не назначайте вторым
   автоматическим formatter-ом.
4. Project inspection profile отключает дублирующую `PyPep8Inspection`, но
   сохраняет semantic Python inspections. Ruff diagnostics остаются включены.

Ширина форматирования — фактическое значение BioETL `88` из
`pyproject.toml`; `.editorconfig` и project code style показывают тот же right
margin. Универсальный пример `100` из исходного плана здесь не применяется,
потому что он расходился бы с formatter-ом репозитория.

## 4. Типизация

`mypy` — единственный основной type checker. Используйте shared configuration
`mypy-full`, которая выполняет:

```powershell
.\.venv-win\Scripts\python.exe -m mypy src tests
```

Строгость и Python compatibility level читаются из `pyproject.toml`. Не
запускайте `mypy --strict $FilePath$`: проверка одного файла теряет
межмодульный контекст. Mypy plugin, Pyright, basedpyright, Pyrefly и `ty` не
включаются как параллельные real-time checkers; их наличие в dev dependencies
не делает их IDE quality gate.

## 5. Shared run/debug configurations

В репозитории публикуются только переносимые configurations:

| Имя | Назначение |
| --- | --- |
| `pytest-fast` | `tests/unit`, без coverage/network/slow/integration |
| `pytest-full` | полный локальный suite, включая slow, но без network/benchmark |
| `pytest-coverage` | отдельный coverage run, threshold `85`, XML + terminal report |
| `pytest-debug-current-file` | текущий test file с `--no-cov -s`, без xdist |
| `ruff-check` | `ruff check src tests` |
| `ruff-format-check` | `ruff format --check src tests` |
| `mypy-full` | `mypy src tests` с project config |
| `quality-gate` | `python -m scripts.engineering.ci quality-gate` |
| `BioETL smoke (offline fixture)` | `chembl_activity` на трёх tracked Bronze records, без API |

Все configurations используют project interpreter, working directory
`$PROJECT_DIR$`, package/module entry points и не содержат secrets или
абсолютных пользовательских путей. Coverage не включён в fast/debug.

Для CLI-проверки тех же поверхностей используйте поддерживаемые Windows
wrappers:

```powershell
.\scripts\engineering\dev\run_pytest.ps1 tests\unit --narrow --timeout=120 --lf
.\scripts\engineering\dev\run_mypy.ps1
.\.venv-win\Scripts\python.exe -m ruff check src tests
.\.venv-win\Scripts\python.exe -m ruff format --check src tests
.\.venv-win\Scripts\python.exe -m scripts.engineering.ci quality-gate
```

## 6. Debugger и smoke safety

- Используйте локальный PyCharm debugger и `pytest-debug-current-file`.
- Coverage и xdist в debug configuration отключены.
- Attach to subprocess, gevent и remote debugging включайте только для
  подтверждённого сценария.
- Shared smoke configuration читает
  `tests/fixtures/bronze/chembl/activity/` и отключает health/backend servers;
  она не обращается к production API. Для работы в обычном dirty dev tree
  configuration явно использует `degraded_observable`; replay-ready проверяется
  отдельными reproducibility tests и clean-clone gate.
- Live API runs остаются локальными и должны явно называться `Live`; их нельзя
  публиковать с credentials или включать в общий quality gate.

## 7. AI plugins

Для inline completion используется один provider — GitHub Copilot. Windsurf /
Codeium и DeepSeek inline completion должны быть выключены; Claude/Google AI
plugins также не должны конкурировать за inline UI. Один отдельный ручной
chat/agent integration допустим, если он не включает inline completion и его
политика передачи project context проверена.

## 8. Что хранится в Git

Root `.gitignore` использует точный allowlist. Публикуются:

- `.idea/runConfigurations/` — только перечисленные выше configurations;
- `.idea/codeStyles/`;
- `.idea/inspectionProfiles/`;
- `.idea/pyLspTools.xml`.

Не публикуются `workspace.xml`, `.iml`, shelves, Local History, data sources,
plugin state, MCP/AI tokens и локальные SDK paths. Любые `.env`/`.env.*`
остаются secret-bearing machine-local files и не изменяются этим workflow.

## 9. Приёмка

После clean clone проверьте:

1. PyCharm stable и Python соответствуют целевым версиям.
2. `import bioetl` работает без `PYTHONPATH`.
3. Ruff форматирует файл один раз, а style warnings не дублируются.
4. `pytest-fast`, `pytest-debug-current-file`, `mypy-full` и offline smoke
   запускаются из `.venv-win`.
5. `git status` не показывает `workspace.xml`, `.iml`, shelves, secrets или
   абсолютные paths.
6. После фоновых задач CPU возвращается к низкому уровню; heap и durations
   фиксируются фактическими значениями, без неподтверждённых процентов.
