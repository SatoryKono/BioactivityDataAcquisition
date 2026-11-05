# Alertmanager Delivery Verification (issue #12723)

Этот отчёт фиксирует неполную пробу для issue #12723 (audit ID pack-v2.1/P14). Он не подтверждает вычисление правил Prometheus, передачу оповещений из Prometheus в Alertmanager и доставку уведомлений получателю.

## 1. Acceptance Criteria Mapping

| Criteria | Evidence |
| :--- | :--- |
| Группа → доставлено/нет | Нет для уведомления. Три синтетических алерта приняты `POST /api/v2/alerts` и видны в `GET /api/v2/alerts`. Маршрут Prometheus → Alertmanager не упражнён. |
| Время | В отчёте указано `2026-11-03T18:38:43.497Z`. Первичный ответ API не сохранён, поэтому происхождение метки не подтверждено. |
| Получатель | Имя маршрута `default` есть в `grafana/alertmanager.yml`. Интеграций (webhook, почта или иной sink) нет, отправка уведомления не подтверждена. |
| Недоставки заведены отдельными дефектами | Заведён дефект `P14-OBS-003`: маршрут Prometheus → Alertmanager не упражнён, получатель `default` без интеграций, происхождение timestamp не зафиксировано. |

## 2. Test Execution Details

Three synthetic alerts were posted to the local Alertmanager v2 API (`POST /api/v2/alerts`). This bypasses Prometheus rule evaluation and the Prometheus → Alertmanager forwarding configured in `grafana/prometheus.yml`.

1. **Manifest Write:** `BioETLControlPlaneManifestWriteFailed`
2. **Ledger Append:** `BioETLRunLedgerAppendFailed`
3. **Replay Reconstruction:** `BioETLReplayNotReconstructable`

### 2.1 Configuration

*   **Alertmanager config** (`grafana/alertmanager.yml`):
    ```yaml
    global:
      resolve_timeout: 5m
    route:
      receiver: 'default'
    receivers:
      - name: 'default'
    ```

У получателя `default` нет канала доставки. `GET /api/v2/alerts` показывает только активные алерты, не отправленное уведомление.

### 2.2 API accept results

Активные алерты прочитаны из `GET /api/v2/alerts`. Колонка ниже — приём API, не доставка уведомления. Значения `runbook` — относительные пути репозитория; разрешение ссылок не проверялось.

| Группа (Group) | Принято API / уведомление | Время (Time) | Получатель (Receiver) | Содержимое / Runbook (Content) |
| :--- | :--- | :--- | :--- | :--- |
| **Manifest write**<br>`BioETLControlPlaneManifestWriteFailed` | Принято API; уведомление не проверено | `2026-11-03T18:38:43.497Z` (происхождение не сохранено) | имя `default`; интеграций нет | `description`: bioetl_control_plane_manifest_writes_total increased with status=failed for pipeline=test-pipeline-1 run_type=test in the last 15m.<br>`runbook`: относительный путь `docs/05-operations/runbooks/run-manifest-inspection.md`<br>`summary`: Run manifest persistence failures detected |
| **Ledger append**<br>`BioETLRunLedgerAppendFailed` | Принято API; уведомление не проверено | `2026-11-03T18:38:43.497Z` (происхождение не сохранено) | имя `default`; интеграций нет | `description`: bioetl_control_plane_ledger_appends_total increased with status=failed for pipeline=test-pipeline-2 event_type=append in the last 15m.<br>`runbook`: относительный путь `docs/05-operations/runbooks/run-manifest-inspection.md`<br>`summary`: Run ledger append failures detected |
| **Replay reconstruction**<br>`BioETLReplayNotReconstructable` | Принято API; уведомление не проверено | `2026-11-03T18:38:43.497Z` (происхождение не сохранено) | имя `default`; интеграций нет | `description`: bioetl_replay_reconstructability_events_total recorded not_reconstructable for pipeline=test-pipeline-3 replay_capability=none strict_requirement=yes in the last 30m.<br>`runbook`: относительный путь `docs/05-operations/runbooks/checkpoint-debugging.md`<br>`summary`: Replay request cannot be reconstructed safely |

## 3. Conclusion

Полный маршрут от вычисления правил в Prometheus до доставки уведомления получателю с настроенной интеграцией не подтверждён. `runbook` в annotations — относительные пути, не проверенные URL. Происхождение timestamp не зафиксировано первичным ответом API. Статус `NOT_VERIFIABLE` в отчёте P14 сохранён, дефект `P14-OBS-003` заведён.
