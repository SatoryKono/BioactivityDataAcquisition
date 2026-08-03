 Проведи observability-аудит не только по backend-запросам, но и по реальному Grafana UX, чтобы ловить не только rule/query defects, но и browser/client/datasource/layout проблемы.

  Вход:
  - workflow: chembl_target
  - limit: 10000

  Обязательный сценарий:

  1. Запусти:
     `./.venv-win/Scripts/python.exe -m bioetl workflow run <WORKFLOW_NAME> --limit <LIMIT>`

  2. Зафиксируй:
  - workflow_run_id
  - workflow manifest_id
  - pipeline_run_id
  - pipeline manifest_id
  - итоговый status
  - metrics backend
  - audit_enabled / audit implementation
  - tracing_enabled / tracer_type
  - dq_monitor_enabled
  - preflight_status
  - run_manifest_enabled
  - run_ledger_enabled

  3. Проверь все shipped observability surfaces:
  - `0. Control Plane`
  - `1. Overview`
  - `2. Runtime`
  - `3. Provider Health`
  - `4. Data Quality`
  - `5. Workflow`
  - `Silver Reject Explorer`
  - `Explore Logs`
  - `Explore Traces`

  4. Для каждой панели в каждом дашборде выведи:
  - dashboard
  - panel
  - datasource
  - panel type
  - exact query / URL / datasource target
  - backend result
  - browser/UI result
  - статус:
    - `OK`
    - `Expected Empty`
    - `Defect`
    - `Not Verifiable`

  5. Обязательно разделяй 4 класса проблем:
  - `Backend defect`
  - `Dashboard query defect`
  - `Grafana/UI rendering defect`
  - `Operational datasource/backend availability defect`

  6. Не ограничивайся backend audit. Для каждого Prometheus-панеля сделай 3 проверки:
  - exact shipped query from dashboard JSON
  - Prometheus API parse/result check for that exact query
  - actual Grafana panel render state in UI

  7. Для каждого Loki/Tempo/Infinity/custom datasource panel:
  - проверь exact datasource target/URL
  - проверь backend endpoint вручную
  - проверь actual Grafana render state
  - если datasource custom, отдельно проверь, что backend реально поднят и reachable из Grafana container/network, а не только с localhost

  8. Обязательно отдельно проверь browser-level defects:
  - `bad data`
  - `query error`
  - `panel error`
  - `No data`
  - unexpected `UNKNOWN`
  - scrollbars inside panels
  - clipped text
  - panel height misalignment
  - empty whitespace due bad grid sizing
  - rows/panels that do not fit first screen
  - table panels with unnecessary scrolling
  - stat/text/table panels that are visibly inconsistent in height

  9. Обязательно отдельно проверь already-known defect classes:
  A. `workflow_<pipeline>` alias mismatch in `Control Plane`
  B. `workflow_<pipeline>` alias mismatch in `Overview`
  C. workflow summary `UNKNOWN` drift in `Overview`
  D. `workflow_<pipeline>` alias mismatch in `Runtime`
  E. runtime false warning / missing current reason
  F. DQ disabled-monitor misleading green state
  G. Loki ingestion gap
  H. traces optional semantics wording
  I. invalid PromQL / parse-error panels
  J. provider cause panel showing synthetic/misleading degraded cause
  K. custom datasource panels failing because backend is unreachable
  L. browser layout defects not visible from backend queries

  10. Для `Silver Reject Explorer` обязательно проверь:
  - datasource provisioning
  - Grafana datasource UID/name
  - backend URL
  - endpoint health:
    - `/ops/quarantine/filter-options`
    - `/ops/quarantine/filtered-stats`
    - `/ops/quarantine/filtered-records`
    - `/ops/quarantine/filtered-record/{payload_hash}`
  - reachability:
    - from host
    - from Grafana container/network
  - actual panel render result in UI
  - отличай:
    - true empty forensic state
    - datasource error
    - backend timeout
    - bad payload schema
    - broken panel transform

  11. Для `Runtime` и `Provider Health` обязательно проверь exact shipped queries на parse validity через Prometheus API.
  Если exact dashboard expression не парсится, это `Defect`, даже если backend metrics сами по себе корректны.

  12. Для каждой проблемной панели укажи:
  - dashboard / panel
  - datasource
  - exact query or URL
  - backend response
  - UI/render result
  - defect class
  - root cause
  - safest fix
  - affected files
  - severity

  13. В конце выведи 4 блока:
  - `Run Summary`
  - `Full Panel Status`
  - `Severity-Ordered Defects`
  - `Remediation Plan`

  14. Если делаешь remediation:
  - сначала правь shipped dashboard JSON / rules / datasource contract
  - затем sync docs mirrors
  - затем rerun targeted tests
  - затем повтори live backend check
  - затем повтори browser-level smoke

  15. Никогда не пиши “ошибок нет”, если:
  - не был выполнен browser-level Grafana smoke
  - не были проверены exact panel queries against datasource API
  - не была проверена custom datasource availability
  - не был проверен layout/scroll/height behavior
