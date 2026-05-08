Проведи полный observability-аудит для заданного workflow и pipeline и проверь наличие уже известных дефектов selector/query/rule semantics, которые ранее проявлялись на `chembl_assay`.

  Входные параметры:
  - <WORKFLOW_NAME>: chembl_assay
  - <LIMIT>: 10000

  Задача:
  1. Запусти:
     `./.venv-win/Scripts/python.exe -m bioetl workflow run <WORKFLOW_NAME> --limit <LIMIT>`

  2. После завершения обязательно зафиксируй:
  - workflow_run_id
  - manifest_id
  - pipeline_run_id
  - итоговый status
  - runtime flags:
    - metrics backend
    - audit_enabled / audit implementation
    - tracing_enabled / tracer_type
    - dq_monitor_enabled
    - preflight_status
    - run_manifest_enabled
    - run_ledger_enabled

  3. Проверь заполнение и поведение панелей в дашбордах:
  - `0. Control Plane`
  - `1. Overview`
  - `2. Runtime`
  - `3. Provider Health`
  - `4. Data Quality`
  - `5. Workflow`
  - `Silver Reject Explorer`
  - `Explore Logs`
  - `Explore Traces`

  4. Для каждой панели выстави один из статусов:
  - `OK`
  - `Expected Empty`
  - `Defect`
  - `Not Verifiable`

  5. Не считать ошибкой панели, которые пусты по дизайну из-за:
  - `audit_enabled=false`
  - `tracing_enabled=false` / `NoOpTracing`
  - `dq_monitor_enabled=false`
  - отсутствия failures
  - отсутствия rejects/quarantine
  - отсутствия provider incidents
  - denominator-gated semantics, где `UNKNOWN` корректен при недостатке telemetry/sample volume

  6. Обязательно отдельно проверь наличие следующих классов ошибок, которые уже встречались ранее:

  A. `Control Plane` selector alias gap
  Проверь, что при выборе `workflow_<pipeline>` панели:
  - `Monitor: Replay Safety State`
  - `Monitor: Manifest / Ledger Integrity`
  - `Inspect: Telemetry Missing`
  не уходят в `UNKNOWN` только из-за selector scope mismatch.
  Если `pipeline=<PIPELINE_NAME>` показывает `OK`, а `workflow_<PIPELINE_NAME>` показывает `UNKNOWN`, это дефект query-layer normalization.

  B. `Overview` selector alias gap
  Проверь, что при выборе `workflow_<pipeline>` не уходят в `No data`:
  - `System Status`
  - `Next Action`
  - `L0 Inputs`
  - `Runtime Blockers`
  - `DQ Status`
  - `Gold Lifecycle`
  - `Control Plane`
  - `Workflow Selected`
  Если эти панели имеют значения для entity pipeline, но пусты для `workflow_<pipeline>`, это дефект selector/query contract.

  C. `Overview` workflow summary rule gap
  Проверь, что:
  - `Workflow Selected`
  - `Workflow Global`
  не имеют `Status=UNKNOWN` после успешного workflow run при наличии workflow evidence.
  Если `System Status` определяется по другим сигналам, а workflow-panels остаются `UNKNOWN`, это дефект workflow summary rules.

  D. `Runtime` selector alias gap
  Проверь, что при выборе `workflow_<pipeline>` корректно ведут себя:
  - `Monitor Runtime Current Status`
  - `Inspect Top Runtime Blockers`
  - `Monitor Runtime Blockers`
  - `Monitor Runtime Error Rate`
  - `Monitor Worst Stage Lag`
  - `Inspect Active Runtime Blocker Detail`
  Важно:
  - если после нормального alias resolution blocker tables пусты и status=OK, это допустимо
  - если `Monitor Runtime Error Rate = UNKNOWN` сохраняется из-за denominator `<20` или отсутствия samples, это не дефект
  - если `UNKNOWN`/`No data` возникает из-за unsupported selector scope, это дефект

  E. Runtime false warning / no-terminal-run rule gap
  Проверь, что после успешного run:
  - `bioetl_runtime_current_status{pipeline="<PIPELINE_NAME>",run_type="backfill"}` не уходит в `WARN/CRIT` без реальной причины
  - `bioetl_runtime_current_blocker_reason > 0` не пуст при non-zero current status
  Если status non-zero без bounded current reason, это дефект rule semantics.

  F. `Data Quality` disabled-monitor semantics
  Если `dq_monitor_enabled=false`, проверь, что DQ surface не выглядит как unconditional green state при наличии disabled-monitor evidence.
  Если expected contract проекта подразумевает warning semantics, а panel показывает misleading `OK`, зафиксируй дефект.

  G. `Explore Logs` ingestion gap
  Проверь:
  - есть ли свежие записи запуска в локальном `reports/logs/bioetl.log`
  - возвращает ли Loki baseline query `{job="bioetl"}` записи по этому run
  Если локальный log существует, а Loki пуст, это дефект log shipping / ingestion / label contract.

  H. `Explore Traces` optional semantics
  Если запуск шел без tracing:
  - не считать пустой `Explore Traces` дефектом
  - но проверить, что UI/tooltip/contract явно сообщает, что traces доступны только для traced runs
  Если traced run required, но UI подает traces как always-available without warning, это дефект UX contract.

  7. Для каждой проблемной панели обязательно укажи:
  - dashboard
  - panel
  - datasource
  - точный query
  - что вернул backend
  - это `Defect` или `Expected Empty`
  - корневую причину
  - рекомендуемое исправление

  8. В конце дай два блока:
  - `Полный статус панелей`
  - `Severity-ordered report по реальным дефектам`

  9. Если реальные дефекты найдены:
  - подготовь remediation plan
  - сгруппируй по классам:
    - selector/query-layer normalization
    - recording rules
    - telemetry ingestion
    - UX/contract wording
    - optional surface semantics
  - для каждого пункта укажи:
    - root cause
    - safest fix
    - affected files
    - verification steps

  10. Если реальных дефектов не найдено:
  - явно напиши, что список ранее известных ошибок для этого workflow/pipeline не воспроизвелся
  - перечисли, какие empty/unknown states были признаны корректными по дизайну

  Формат ответа:
  - краткое summary запуска
  - таблица/список по дашбордам и панелям
  - затем отдельный severity-ordered defect report
  - затем remediation plan только если defects действительно есть
