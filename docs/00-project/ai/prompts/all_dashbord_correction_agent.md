
• Задача: провести end-to-end верификацию observability для всех workflow и всех pipeline в проекте, затем при необходимости подготовить и реализовать исправления.

  Работай как инженер-аудитор и исполнитель исправлений.
  Не пропускай этапы.
  Не смешивай результаты этапов.
  Не завершай задачу, пока не выполнены все применимые этапы.

  ==================================================
  ОБЩИЕ ПРАВИЛА
  ==================================================

  1. Проверка должна покрывать:
     - все declarative workflow в проекте
     - все pipeline в проекте
     - отдельно:
       - pipeline, запускаемые через workflow
       - standalone pipeline, не покрытые workflow

  2. Любой вывод должен опираться на evidence из:
     - runtime command outputs
     - Prometheus / Loki / Tempo / Quarantine Explorer responses
     - dashboard JSON
     - project code / contracts / docs
     - generated run artifacts

  3. Не помечай panel как `Defect`, если нет backend evidence.

  4. Не считай panel ошибкой, если её пустота объясняется:
     - feature disabled
     - expected no-event condition
     - отсутствием релевантного workflow/pipeline context
     - документированным empty-state contract

  5. Для каждого запуска фиксируй абсолютные идентификаторы run artifacts, а не только summary.

  6. Если среда не позволяет что-то проверить надёжно, используй только статус `Not Verifiable` и явно объясняй причину.

  7. Если находишь `Defect`, после анализа подготовь и реализуй fix, затем повтори верификацию затронутого scope.

  ==================================================
  ЭТАП 0. SCOPE DISCOVERY
  ==================================================

  Цель: определить полный scope проверки до любых run и dashboard verdicts.

  Сделай:
  1. Найди все workflow.
  2. Найди все pipeline.
  3. Построй mapping:
     - `workflow -> steps -> pipelines`
  4. Выдели standalone pipeline.
  5. Определи canonical run command:
     - для workflow
     - для standalone pipeline
  6. Определи, какие dashboard surfaces применимы:
     - к workflow runs
     - к standalone pipeline runs

  Не переходи к Этапу 1, пока не сформирован полный inventory.

  ==================================================
  ЭТАП 1. EXECUTION + DASHBOARD AUDIT
  ==================================================

  Выполни проверку для каждого workflow и каждого standalone pipeline.

  ----------------------------------
  1A. Workflow runs
  ----------------------------------

  Для каждого workflow:
  1. Запусти bounded run.
     Базовый шаблон:
     `./.venv-win/Scripts/python.exe -m bioetl workflow run <workflow_name> --limit 1000`
  2. Если workflow требует другой canonical command, используй её и явно зафиксируй это.
  3. После завершения зафиксируй:
     - `workflow_name`
     - `workflow_run_id`
     - `manifest_id`
     - `pipeline_run_ids`
     - `executed_steps`
     - `final_status`
     - `metrics_enabled`
     - `audit_enabled`
     - `tracing_enabled`
     - `dq_monitor_enabled`

  ----------------------------------
  1B. Standalone pipeline runs
  ----------------------------------

  Для каждого standalone pipeline:
  1. Запусти bounded run через canonical project-supported command.
  2. После завершения зафиксируй:
     - `pipeline_name`
     - `pipeline_run_id`
     - `manifest_id` если есть
     - `workflow_run_id` если внезапно run оказался workflow-managed
     - `final_status`
     - `metrics_enabled`
     - `audit_enabled`
     - `tracing_enabled`
     - `dq_monitor_enabled`

  ----------------------------------
  1C. Dashboard / surface verification
  ----------------------------------

  Для каждого run проверь следующие surfaces:
  - `0. Control Plane`
  - `1. Overview`
  - `2. Runtime`
  - `3. Provider Health`
  - `4. Data Quality`
  - `5. Workflow`
  - `Silver Reject Explorer`
  - `Explore Logs`
  - `Explore Traces`

  Для каждой панели назначь ровно один статус:
  - `OK`
  - `Expected Empty`
  - `Defect`
  - `Not Verifiable`

  Критерии:
  - `OK`:
    panel заполнена или корректно показывает expected state.
  - `Expected Empty`:
    panel пуста по контракту или по runtime context.
  - `Defect`:
    panel должна была показать данные или корректный empty-state, но этого не произошло.
  - `Not Verifiable`:
    нет надёжной возможности проверить panel из текущей среды.

  Для `Explore Logs` и `Explore Traces` отдельно классифицируй причину:
  - `feature_disabled`
  - `no_telemetry_for_run`
  - `broken_query_or_link`
  - `broken_label_propagation`
  - `environment_limitation`

  ----------------------------------
  1D. Defect evidence
  ----------------------------------

  Для каждой панели со статусом `Defect` или `Not Verifiable` зафиксируй:
  - `scope_type`: `workflow` или `pipeline`
  - `scope_name`
  - `run_ids`
  - `dashboard`
  - `panel`
  - `status`
  - `datasource`
  - `query_or_request`
  - `backend_response`
  - `expected_behavior`
  - `root_cause`
  - `recommended_fix`

  ==================================================
  ЭТАП 2. FIX PLAN
  ==================================================

  Выполняй только если найден хотя бы один `Defect`.

  1. Подготовь initial fix plan.
  2. Для каждого defect укажи:
     - severity
     - impacted files
     - impacted dashboards
     - impacted datasource contract
     - root-cause fix
     - test additions
     - docs/contract sync
  3. Проведи self-audit плана:
     - не лечит ли он симптом вместо причины
     - не ломает ли expected-empty semantics
     - не вносит ли лишние изменения
     - покрывает ли verification after fix
  4. Сформируй final fix plan.

  ==================================================
  ЭТАП 3. IMPLEMENTATION
  ==================================================

  Выполняй только если:
  - на Этапе 1 есть `Defect`
  - на Этапе 2 есть final fix plan

  1. Реализуй fixes полностью.
  2. Прогони targeted verification.
  3. Повтори Этап 1 для затронутых workflow/pipeline/surfaces.
  4. Продолжай цикл до состояния:
     - либо `Defect` больше нет
     - либо остаются только `Expected Empty` и/или `Not Verifiable`

  ==================================================
  ЖЁСТКИЙ ФОРМАТ ОТЧЁТА
  ==================================================

  Используй следующий шаблон без пропусков.

  ############################
  # STAGE 0 REPORT
  ############################

  ## Workflow Inventory
  - <workflow_name>: <short description or step summary>

  ## Pipeline Inventory
  - <pipeline_name>: covered_by=<workflow_name|standalone|multiple>

  ## Workflow -> Pipeline Mapping
  - <workflow_name>:
    - <step_id> -> <pipeline_name>

  ## Standalone Pipelines
  - <pipeline_name>
  - <pipeline_name>

  ## Canonical Run Commands
  - workflow:
    - <workflow_name>: `<command>`
  - pipeline:
    - <pipeline_name>: `<command>`

  ## Stage 0 Gaps
  - <item>: `Not Verifiable` - <reason>

  ############################
  # STAGE 1 REPORT
  ############################

  ## Run Summary
  - scope_type=`workflow` scope_name=`<name>` final_status=`<status>` workflow_run_id=`<id>` manifest_id=`<id>` pipeline_run_ids=`<ids>`
  - scope_type=`pipeline` scope_name=`<name>` final_status=`<status>` pipeline_run_id=`<id>` manifest_id=`<id|n/a>`

  ## Runtime Flags
  - scope_name=`<name>` metrics_enabled=`<bool>` audit_enabled=`<bool>` tracing_enabled=`<bool>` dq_monitor_enabled=`<bool>`

  ## Panel Status Matrix
  - scope_name=`<name>` dashboard=`<dashboard>` panel=`<panel>` status=`OK|Expected Empty|Defect|Not Verifiable`
  - scope_name=`<name>` dashboard=`<dashboard>` panel=`<panel>` status=`...`

  ## Defects
  - severity=`Critical|High|Medium|Low`
    scope_type=`workflow|pipeline`
    scope_name=`<name>`
    dashboard=`<dashboard>`
    panel=`<panel>`
    datasource=`<Prometheus|Loki|Tempo|Quarantine Explorer|...>`
    query_or_request=`<exact query or request>`
    backend_response=`<actual result>`
    expected_behavior=`<expected>`
    root_cause=`<root cause>`
    recommended_fix=`<fix>`

  ## Not Verifiable
  - scope_type=`workflow|pipeline`
    scope_name=`<name>`
    dashboard=`<dashboard>`
    panel=`<panel or surface>`
    reason=`<reason>`

  ## Stage 1 Verdict
  - total_workflows_checked=`<n>`
  - total_pipelines_checked=`<n>`
  - total_panels_checked=`<n>`
  - defects_found=`<n>`
  - not_verifiable=`<n>`

  ############################
  # STAGE 2 REPORT
  ############################

  ## Initial Fix Plan
  - defect=`<short name>` severity=`<severity>` files=`<files>` action=`<action>`

  ## Plan Audit
  - issue=`<problem in plan>`
  - issue=`<problem in plan>`

  ## Final Fix Plan
  - order=`1` defect=`<name>` root_cause_fix=`<fix>` tests=`<tests>` docs_sync=`<docs>`
  - order=`2` defect=`<name>` root_cause_fix=`<fix>` tests=`<tests>` docs_sync=`<docs>`

  ############################
  # STAGE 3 REPORT
  ############################

  ## Implemented Changes
  - file=`<path>` change=`<summary>`
  - file=`<path>` change=`<summary>`

  ## Verification After Fix
  - command=`<command>` result=`<result>`
  - command=`<command>` result=`<result>`

  ## Re-Audit Results
  - scope_name=`<name>` dashboard=`<dashboard>` panel=`<panel>` status=`<status>`

  ############################
  # FINAL REPORT
  ############################

  ## Coverage Summary
  - workflows_total=`<n>`
  - workflows_checked=`<n>`
  - pipelines_total=`<n>`
  - pipelines_checked=`<n>`

  ## Final Defects
  - <defect summary>
  - or `none`

  ## Expected Empty
  - <summary list>

  ## Not Verifiable
  - <summary list>

  ## Overall Outcome
  - `No Defects`
  - `Defects Fixed`
  - `Defects Remaining`

  ==================================================
  ЗАВЕРШАЮЩЕЕ ПРАВИЛО
  ==================================================

  Если на Этапе 1 не найдено ни одного `Defect`, не придумывай Этап 2 и Этап 3.
  Если `Defect` есть, не останавливайся на диагностике — переходи к fix plan и реализации.
