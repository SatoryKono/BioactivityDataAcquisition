  Задача: провести end-to-end верификацию observability для всех declarative workflow и всех pipeline в проекте, затем при необходимости подготовить и реализовать исправления.

  Работай строго по этапам. Не пропускай этапы и не смешивай результаты.
  Не считай задачу завершённой, пока не выполнены все применимые этапы.

  --------------------------------------------------
  ЭТАП 0. Инвентаризация coverage scope
  --------------------------------------------------

  1. Сначала найди полный scope проверки:
     - все declarative workflow, доступные в проекте
     - все pipeline, доступные в проекте
     - отдельно выдели:
       - pipeline, которые уже покрываются workflow
       - standalone pipeline, которые не покрываются ни одним workflow

  2. Используй только реальный project state:
     - workflow configs
     - pipeline registry / composition / CLI surfaces
     - shipped dashboards
     - monitoring docs и runtime contracts

  3. По итогам Этапа 0 обязательно выведи:
     - список всех найденных workflow
     - список всех найденных pipeline
     - mapping:
       - `workflow -> какие pipeline он запускает`
     - список standalone pipeline, если они есть
     - список items, которые не удалось надёжно классифицировать, с пометкой `Not Verifiable`

  4. Не переходи к Этапу 1, пока не определён полный scope проверки.

  --------------------------------------------------
  ЭТАП 1. Прогон workflow/pipeline и аудит dashboard surfaces
  --------------------------------------------------

  Выполняй Этап 1 для каждого найденного workflow и для каждого standalone pipeline.

  ### 1A. Для каждого workflow

  1. Запусти workflow bounded-run командой вида:

     ./.venv-win/Scripts/python.exe -m bioetl workflow run <workflow_name> --limit 1000

     Если для конкретного workflow canonical command отличается, используй реальную project-supported команду и явно зафиксируй это.

  2. После завершения каждого workflow run обязательно зафиксируй:
     - `workflow_name`
     - `workflow_run_id`
     - `manifest_id`
     - все соответствующие `pipeline_run_id`
     - итоговый статус workflow
     - какие pipeline шаги реально исполнялись
     - ключевые runtime flags:
       - `metrics_enabled`
       - `audit_enabled`
       - `tracing_enabled`
       - `dq_monitor_enabled`

  3. Затем проверь заполнение и корректность всех релевантных panels/surfaces в контексте этого workflow run:
     - `0. Control Plane`
     - `1. Overview`
     - `2. Runtime`
     - `3. Provider Health`
     - `4. Data Quality`
     - `5. Workflow`
     - `Silver Reject Explorer`
     - `Explore Logs`
     - `Explore Traces`

  4. Проверяй панели не абстрактно, а в конкретном run context:
     - с правильными `workflow`
     - `pipeline`
     - `run_type`
     - `provider`
     - `stage`
     - и прочими relevant variables

  ### 1B. Для каждого standalone pipeline

  1. Запусти bounded-run командой через canonical pipeline CLI surface проекта, например:

     ./.venv-win/Scripts/python.exe -m bioetl run <pipeline_name> --limit 1000

     Если в проекте для pipeline используется другая canonical команда, используй её и явно зафиксируй это.

  2. После завершения каждого pipeline run обязательно зафиксируй:
     - `pipeline_name`
     - `pipeline_run_id`
     - связанный `manifest_id`, если есть
     - связанный `workflow_run_id`, если run всё же был workflow-managed
     - итоговый статус pipeline run
     - ключевые runtime flags:
       - `metrics_enabled`
       - `audit_enabled`
       - `tracing_enabled`
       - `dq_monitor_enabled`

  3. Затем проверь заполнение и корректность всех релевантных panels/surfaces в контексте этого pipeline run:
     - `0. Control Plane`
     - `1. Overview`
     - `2. Runtime`
     - `3. Provider Health`
     - `4. Data Quality`
     - `5. Workflow`
     - `Silver Reject Explorer`
     - `Explore Logs`
     - `Explore Traces`

  4. Для standalone pipeline отдельно учитывай, что:
     - `5. Workflow` может быть `Expected Empty` или `Not Verifiable`, если этот pipeline не работает через workflow layer
     - но это должно быть подтверждено runtime contract и backend evidence

  ### 1C. Классификация panel status

  Для каждой панели выстави ровно один статус:
  - `OK`
  - `Expected Empty`
  - `Defect`
  - `Not Verifiable`

  Используй такие правила классификации:
  - `OK`:
    панель заполнена и поведение соответствует ожидаемому контракту.
  - `Expected Empty`:
    панель пуста по дизайну или по runtime context, например из-за:
    - `audit_enabled=false`
    - `tracing_enabled=false`
    - `dq_monitor_enabled=false`
    - отсутствия failures
    - отсутствия rejects
    - отсутствия provider incidents
    - отсутствия логов/трейсов для данного запуска
    - отсутствия workflow context для standalone pipeline
  - `Defect`:
    панель должна была показать данные или корректный empty-state, но этого не произошло.
  - `Not Verifiable`:
    панель невозможно проверить надёжно из текущей среды, и причина должна быть явно указана.

  ### 1D. Evidence requirements

  Для каждой панели со статусом `Defect` или `Not Verifiable` укажи:
  - `scope_type`: `workflow` или `pipeline`
  - `scope_name`
  - `dashboard`
  - `panel`
  - `status`
  - `datasource`:
    `Prometheus`, `Loki`, `Tempo`, `Quarantine Explorer` или другое
  - фактический query / expression / request
  - что именно вернул backend
  - ожидаемое поведение
  - корневую причину
  - рекомендуемое исправление

  Для `Explore Logs` и `Explore Traces` отдельно различай:
  - feature disabled
  - no telemetry for this run
  - broken query / broken link / broken label propagation
  - environment limitation

  ### 1E. Итог Этапа 1

  В конце Этапа 1 выведи:
  - краткую сводку по всем workflow run и всем standalone pipeline run
  - coverage summary:
    - сколько workflow проверено
    - сколько pipeline проверено
    - какие pipeline были покрыты только через workflow
    - какие проверялись standalone
  - таблицу или список всех проверенных панелей с их статусами
  - severity-ordered report только по реальным `Defect`
  - отдельный список `Not Verifiable`, если такие есть

  --------------------------------------------------
  ЭТАП 2. План исправления
  --------------------------------------------------

  Выполняй Этап 2 только если на Этапе 1 найден хотя бы один `Defect`.

  1. Подготовь план исправления дефектов.
  2. План должен быть:
     - упорядочен по severity и dependencies
     - привязан к конкретным:
       - файлам
       - dashboard panels
       - queries
       - datasource contracts
       - workflow/pipeline scopes
     - разделён на:
       - root-cause fixes
       - test coverage
       - docs / dashboard contract sync

  3. Затем проведи аудит собственного плана:
     - нет ли лишних изменений
     - не лечит ли план симптомы вместо причины
     - не сломает ли он expected-empty behavior
     - не создаст ли divergence между workflow-driven и standalone pipeline behavior
     - покрывает ли он verification after fix

  4. По итогам аудита подготовь обновлённый финальный план.

  В конце Этапа 2 выведи:
  - исходный план
  - замечания аудита
  - обновлённый финальный план

  --------------------------------------------------
  ЭТАП 3. Реализация исправлений
  --------------------------------------------------

  Выполняй Этап 3 только если:
  - на Этапе 1 найден хотя бы один `Defect`
  - на Этапе 2 подготовлен финальный план исправления

  1. Полностью реализуй изменения из финального плана.
  2. После реализации снова вернись к Этапу 1 и повтори проверку:
     - для затронутых workflow
     - для затронутых pipeline
     - для всех affected dashboards/surfaces
  3. Повторяй цикл до тех пор, пока:
     - все реальные дефекты не будут исправлены, или
     - не останется только `Expected Empty` / `Not Verifiable`

  --------------------------------------------------
  УСЛОВИЯ ЗАВЕРШЕНИЯ
  --------------------------------------------------

  Если на Этапе 1:
  - не найдено ни одного `Defect`,
  или
  если Этап 2 / Этап 3 неприменимы,
  то выведи краткий финальный отчёт и завершай задачу.

  Финальный отчёт должен содержать:
  - coverage summary по всем workflow и pipeline
  - итоговый статус каждого workflow run
  - итоговый статус каждого standalone pipeline run
  - список реальных дефектов
  - что было исправлено
  - что осталось `Expected Empty`
  - что осталось `Not Verifiable`
  - общий итог:
    - `No Defects`
    - `Defects Fixed`
    - `Defects Remaining`

  --------------------------------------------------
  ФОРМАТ РАБОТЫ
  --------------------------------------------------

  Требования к ответу:
  - не скрывай промежуточные выводы
  - не помечай панель как дефект без указания backend evidence
  - не предлагай исправление без объяснения root cause
  - не считать пустые панели ошибкой, если это соответствует runtime flags или expected no-event conditions
  - если среда не позволяет проверить что-то напрямую, явно это фиксируй как `Not Verifiable`
  - не ограничивайся одним workflow или одним pipeline, пока не доказано, что остальные уже покрыты или неприменимы
  - не считать pipeline покрытым, если он не был либо реально запущен, либо надёжно покрыт workflow run с явным evidence
