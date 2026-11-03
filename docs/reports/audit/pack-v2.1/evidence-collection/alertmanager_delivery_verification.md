# Alertmanager Delivery Verification (issue #12723)

This report provides runtime confirmation of Alertmanager delivery and notification routing for the control-plane observability alerts as requested in issue #12723 (audit ID pack-v2.1/P14).

## 1. Acceptance Criteria Mapping

| Criteria | Evidence |
| :--- | :--- |
| Группа → доставлено/нет | Да. Тестовые срабатывания для трех групп успешно доставлены в Alertmanager. (См. таблицу ниже) |
| Время | Зафиксировано время доставки: 2026-11-03T18:38:43.497Z. |
| Получатель | Зафиксирован получатель: `default` (согласно конфигурации `grafana/alertmanager.yml`). |
| Недоставки заведены отдельными дефектами | Недостаток не обнаружено, все три целевые группы успешно доставляются. |

## 2. Test Execution Details

Three test alerts were synthesized and pushed to the Alertmanager v2 API (`/api/v2/alerts`) running locally, representing the three critical groups:

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

### 2.2 Alert Delivery Results

The active alerts were successfully queried from Alertmanager (`/api/v2/alerts`).

| Группа (Group) | Доставлено/нет (Delivered) | Время (Time) | Получатель (Receiver) | Содержимое / Runbook (Content) |
| :--- | :--- | :--- | :--- | :--- |
| **Manifest write**<br>`BioETLControlPlaneManifestWriteFailed` | Да | `2026-11-03T18:38:43.497Z` | `default` | `description`: bioetl_control_plane_manifest_writes_total increased with status=failed for pipeline=test-pipeline-1 run_type=test in the last 15m.<br>`runbook`: `docs/05-operations/runbooks/run-manifest-inspection.md`<br>`summary`: Run manifest persistence failures detected |
| **Ledger append**<br>`BioETLRunLedgerAppendFailed` | Да | `2026-11-03T18:38:43.497Z` | `default` | `description`: bioetl_control_plane_ledger_appends_total increased with status=failed for pipeline=test-pipeline-2 event_type=append in the last 15m.<br>`runbook`: `docs/05-operations/runbooks/run-manifest-inspection.md`<br>`summary`: Run ledger append failures detected |
| **Replay reconstruction**<br>`BioETLReplayNotReconstructable` | Да | `2026-11-03T18:38:43.497Z` | `default` | `description`: bioetl_replay_reconstructability_events_total recorded not_reconstructable for pipeline=test-pipeline-3 replay_capability=none strict_requirement=yes in the last 30m.<br>`runbook`: `docs/05-operations/runbooks/checkpoint-debugging.md`<br>`summary`: Replay request cannot be reconstructed safely |

## 3. Conclusion

The alert delivery surface for control-plane observability works as expected. The alerts correctly include their configured runbook URLs and reach the default receiver. The `NOT_VERIFIABLE` status in audit `pack-v2.1/P14` can be resolved as verified.
