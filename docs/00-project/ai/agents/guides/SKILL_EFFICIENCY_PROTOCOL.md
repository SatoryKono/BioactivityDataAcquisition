______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-11-12'

______________________________________________________________________

# Протокол оценки эффективности skills

Это методика измерений, а не новый bootstrap или разрешение запускать агентов.
Codex, Junie и Devin сравниваются как равноправные runtime. OpenCode остаётся
подчинённой отключённой поверхностью; результаты основных runtime на него не
переносятся. Приоритет и guardrails определяет [AGENTS.md](../../../../../AGENTS.md).

## Что уже измерено

[Снимок baseline/after](../../../../reports/generated/skill-efficiency-source-comparison.json)
содержит только метаданные выбранных tracked текстовых источников из Git.
Baseline `b283d1759fbaedfb1efe731307ccbd0c8024eaa8` зафиксирован перед #13028;
after `ffbc484dae248889de8e6aa3fc1ed512d209fdb1` — merge, закрывший #13032.
Оба снимка воспроизводятся из неизменяемых объектов, а не из текущего worktree.
Ранний baseline охватывал 171 файл runtime; одинаковая расширенная область
сравнения добавляет семь общих источников к обеим сторонам.

| Группа | Файлов baseline/after | Байт LF baseline | Байт LF after | Строк baseline/after |
| --- | --- | --- | --- | --- |
| Codex | 64 / 64 | 124032 | 127530 | 3132 / 3176 |
| Junie | 59 / 59 | 120880 | 124102 | 3146 / 3192 |
| Devin | 48 / 48 | 210589 | 218607 | 5270 / 5357 |
| Общие источники | 7 / 7 | 64609 | 75707 | 1310 / 1476 |

В области снимка изменились 34 файла. Рост объёма исходников не доказывает рост
загруженного контекста, а сокращение не доказывало бы экономию токенов.
В интервал входят и параллельные изменения проекта: причинный эффект только
этой серии по этим данным установить нельзя. Обязательные зеркала учитываются
отдельно и сохраняются; сумма трёх runtime не является контекстом одной сессии.

Фактические загрузки, повторные чтения, tool calls, время, tokens, корректность
маршрута, пропуски проверок и качество живых задач: **NOT_MEASURED**.
Исторический живой baseline восстановить из размеров файлов невозможно.

## Пригодность существующих инструментов и данных

| Источник | Что действительно даёт | Ограничение |
| --- | --- | --- |
| [efficiency_baseline.py](../../../../../scripts/ai/codex/efficiency_baseline.py), обычный режим | Длительность фиксированных launcher/MCP probes | Не читает трассу реальной задачи; обычный режим запускает команды, для этой методики не используется |
| Тот же инструмент, `--instruction-refs` | LF-normalized bytes, lines, digests, список изменённых источников | Только локальные объекты Git; не prompt, не token proxy, не частота выбора |
| [profile_benchmark.py](../../../../../scripts/ai/codex/profile_benchmark.py) | Ответы моделей на фиксированные синтетические fixtures | Задания запрещают чтение файлов/tools; не проверяют выбор или совместное применение project skills; здесь не запускается |
| [.devin/agent-metrics.json](../../../../../.devin/agent-metrics.json) и [collector](../../../../../.devin/scripts/collect_agent_metrics.py) | Агрегаты, обновляемые явными вызовами record methods | Нет связанных run ID, instruction/tree SHA, модели, сопоставимых условий и полноты сбора; репрезентативность не установлена, нулевые значения не доказывают неиспользование |

Пользовательские транскрипты и machine-local history не собирались. Статическая
проверка контракта не подтверждает native loading. Отдельные уровни доказательств
описаны в [AI rule loading evidence](../../../../05-operations/runbooks/ai-rules-loading.md).

## Воспроизведение статического сравнения

Из полного существующего checkout, с локально доступными обоими commit:

```text
python -B scripts/ai/codex/efficiency_baseline.py --instruction-refs b283d1759fbaedfb1efe731307ccbd0c8024eaa8 ffbc484dae248889de8e6aa3fc1ed512d209fdb1 --output reports/quality/skill-efficiency-source-comparison.json
```

На Windows выбирайте установленный `.venv-win/Scripts/python.exe`.
Не опускайте `--instruction-refs`: без него сохранён прежний launcher-probe режим.
При недоступном объекте команда завершится ошибкой без fetch, checkout или fallback
к probes. Сеть/lazy fetch и replacement objects отключены. Нужные исторические
объекты подготавливает оператор отдельно; команда не создаёт worktree.

Область: `.codex/{agents,skills}/`, `.junie/{agents,skills}/`,
`.devin/{agents,skills}/` с суффиксами `.md/.toml/.json/.yaml/.yml` и семь точных
общих путей из `scope.shared_paths` отчёта. Учитываются только regular blobs;
symlink, изображения, другие расширения и `.env*` исключаются до чтения blobs.
CRLF преобразуется в LF, lines — число `splitlines()`, SHA-256 берётся от LF bytes.
Нет даты генерации или host paths, поэтому повтор одинаковых refs воспроизводим.
`generator_sha256_lf` связывает результат с кодом генератора; изменение генератора
требует повторного получения снимка. Снимок не должен автоматически следовать main.

## Набор сопоставимых задач для будущих живых запусков

Единый fixture commit для обеих instruction variants — after SHA выше.
Инструкции baseline/after меняются отдельно от кода, данных и seed patch.
Подготовка variants требует отдельного согласованного scope; не исполняйте старые
инструкции с ослабленными guardrails. Текущие защитные правила действуют в обеих
группах и отражаются в manifest. Такой защищённый replay не равен исторической сессии.

| ID | Фиксированный запрос / вход | Ожидаемый маршрут и результат |
| --- | --- | --- |
| D1 docs V1 | Уточнить в governed worktree section `.github/CONTRIBUTING.md`, что validate-only не создаёт дерево; остальные правила сохранить | py-doc-bot; локальная правка документа, применимые docs checks, без безусловного full package |
| F1 focused fix | В копии fixture заменить единственную проверку ref в `_revision` на `if not ref:`; восстановить отказ для options/expressions до Git | py-debug-bot и py-test-bot по необходимости; негативные tests в `test_create_worktree.py`, без создания дерева или env |
| C1 CI diagnosis | Вход: `active script count exceeds lifecycle.active_script_count_max (335 > 334)`; read-only диагноз и минимальный план | py-debug-bot; найти inventory/catalog/entrypoint owners, не повышать лимит и не маскировать активный CLI ложной классификацией |
| G1 config contract | В копии lifecycle registry заменить decision helper на `unknown_fixture_status`; исправить только нарушенный контракт | py-config-bot + применимые проверки; вернуть обоснованный shared-helper boundary, сохранить бюджеты |
| A1 audit | В копии profile добавить отсутствующий allowed skill `missing_fixture_skill`; провести read-only аудит разрешимости | py-audit-bot; finding с файлом/строкой, обязательную post-change policy не объявлять необязательной |
| R1 research | По локальным источникам объяснить ownership HTTP adapters и composition wiring; дать evidence и неизвестные | research-workflow; поэтапный evidence trail, file/line ссылки, без внешнего поиска или неподтверждённых выводов |

Оператор сохраняет точные prompt bytes, seed patch и их digests **до** запуска;
проверяет единственность места замены и исходное состояние fixture. Seed F1/G1/A1
должен воспроизводить ожидаемый дефект локальной проверкой до model turn. Здесь
seeds и живые задачи не запускались: статус live qualification — NOT_MEASURED.
Не переносите намеренные дефекты fixture в main. Применимость нескольких skills
оценивается по обоснованной передаче ответственности, а не по числу вызовов.

## Условия сравнения и порядок

1. Зафиксировать case/prompt/seed digests, fixture/tree SHA, instruction SHA,
   обязательные overlay digests, зависимости, platform/shell и версию клиента.
   Отдельно квалифицировать native presence/discovery/body rendering/execution;
   неизвестное обозначить NOT_PROVEN, не заменять runtime чужим профилем.
2. Согласовать бюджет живых запусков отдельно. Не использовать реальные секреты,
   provider data или внешние evaluators. Новое дерево разрешено только по
   действующему D:/github/helper правилу; `.env*` требует per-task согласия.
3. Разделить runtime, точную модель/provider version, reasoning settings, cold/warm
   session и cache conditions. Запустить одинаковые cases в обеих группах, чередуя
   порядок baseline/after. Между cases восстанавливать sealed fixture; сохранять
   незавершённую работу до восстановления. Не переиспользовать контекст между cases.
4. Повторы и лимиты задаёт manifest заранее. Один запуск — наблюдение, не частота
   использования. Для небольшого набора показывать индивидуальные результаты,
   медиану/диапазон внутри сопоставимых групп и missing data. Не заявлять значимость
   или переносимость без достаточного дизайна и данных; не объединять разные модели.
5. Сначала оценить качество и guardrails, затем эффективность. Ошибочные/blocked
   запуски не удалять: учитывать отдельно, не выдавать ранний отказ за ускорение.
   Локальные tests, native observations и CI конкретного head отражать раздельно.

## Метрики и источники

| Метрика | Источник и определение | Если недоступно |
| --- | --- | --- |
| Loaded sources | Наблюдаемые body digests в prompt rendering либо подтверждённые file-read events; reference/catalog listing не считается загрузкой | NOT_MEASURED, либо частичное покрытие с указанием метода |
| Repeated reads | Число повторных чтений одного source digest и пересекающихся диапазонов в одном run; отдельная reviewer-разметка justified/redundant/unknown | NOT_MEASURED; повтор сам по себе не означает лишнюю работу |
| Tool calls | Bounded structured call events по категориям, включая ошибки; внутренние невидимые calls не угадываются | NOT_MEASURED, доступная часть помечается partial |
| Time | Monotonic start/stop целой задачи; отдельно startup, tool wait и CI wait, если наблюдаемы | NOT_MEASURED, не заменять временем Git snapshot |
| Tokens | Только фактические provider usage fields с units и provenance; input/output/cache раздельно | NOT_MEASURED; запрещены bytes/4 и другие оценки из размера файлов |
| Route correctness | Независимый reviewer сопоставляет case, выбранные роли/skills и текущие triggers | NOT_MEASURED; наличие файла не является выбором skill |
| Skipped checks | Required checks по реальному impact и журнал executed/skipped/blocked с причиной и follow-up | NOT_MEASURED; SKIP/blocked не равны PASS |
| Task quality | Acceptance проверки case плюс независимая проверка evidence, scope и отсутствия регрессии | NOT_MEASURED; самооценка модели не заменяет проверку |

Минимальная запись run: protocol/case/run ID, fixture/instruction/overlay digests,
runtime/client/model/settings, environment/cache group, seed digest, outcome,
availability/source для каждой метрики, sanitized evidence IDs и rubric verdict.
Неизвестные поля остаются NOT_MEASURED; отсутствующие events не превращаются в нули.

## Качество, приватность и stop conditions

Критерий отсутствия регрессии: обе группы выполняют acceptance каждого case;
нет новых необъяснённых required-check skips, неподтверждённых claims или
неразрешимых маршрутов; reviewer подтверждает корректность evidence и результата.
Любое нарушение env/worktree/budget/full-tree/parity правил блокирует положительный
вывод независимо от времени или tokens. Нативные permissions и обязательные
runtime mirrors сохраняются; OpenCode и сервисы не активируются.

Сборщик должен использовать allowlist полей и bounded events, а не полный
транскрипт. До сохранения исключить prompts/body text, `.env*`, credentials,
headers, endpoints, абсолютные host paths, персональные идентификаторы и сырые
tool arguments/results. Для источников достаточно repo-relative ID, digest,
диапазона и количества. Publication требует ручной проверки обезличивания;
сомнительную запись исключить с причиной, не редактировать метрики задним числом.

Неполные/несопоставимые данные, неизвестная модель/loader capability или нарушение
guardrail означают INCONCLUSIVE/BLOCKED, а не доказанную экономию. Методика не
меняет runtime поведение; живой сбор, instrumentation и external evaluation —
отдельная работа, которая не запускается этой командой или CI автоматически.
