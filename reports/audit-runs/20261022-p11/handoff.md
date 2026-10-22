# P11 reproducibility audit handoff

Прогон `20261022-p11`. Стадия P11, concern: reproducibility и replay.
Код в этом прогоне не менялся. P20 не выполнялся.

## Ревизия

- Проверенный код: `ee83860e7902adcd5eebff163514df97a6c5f5f4` (`origin/main` на момент повторной проверки).
- Дерево этой ревизии совпадает с деревом до добавления handoff.
- Пустой коммит Jules: `6f33814261f159ad9567e066009e62fb9e8466bc`.
- Его дерево совпадает с родителем `626e2661761a713039d42dfd00b6893814b4fd20`.
- Слияние с `origin/main` не потребовало ручного разрешения конфликтов.
- Время проверки, UTC: `2026-10-22T07:30:00Z`.

## Почему CI был красным

PR не содержал ни одного изменённого файла. Классификатор `pr_gate` включает все path-scoped гейты с причиной `fail_closed_empty_diff`, а шаги Class lane их пропускают. Агрегатор затем видит `skipped` там, где нужен `success`.

Прогон: `39734948232`.

Пустой коммит оставлен в истории. Этот каталог делает diff непустым.

## Замечания ревью

У PR не было inline-замечаний CodeRabbit: первый комментарий только сообщает, что draft не ревьюился, а набор изменённых файлов был пуст. Этот handoff не повторяет две формулировки из текста PR.

- Имена `BYTE_EQUIVALENT`, `SEMANTIC_EQUIVALENT`, `OCCURRENCE_ONLY_DIFFERENT` и `NOT_EQUIVALENT` в `src/bioetl` отсутствуют. Сравнение артефактов использует ключи `raw_byte_equivalent`, `semantic_equivalent` и `occurrence_only`.
- `RunManifest` является frozen dataclass. Повторный `save` того же `manifest_id` с другим `execution_fingerprint` файл перезаписывает. Иммутабельность объекта не равна запрету повторной записи файла.
- `src/memory/ledger.py` — отдельный журнал мутаций памяти. Он не является run ledger control plane.

## Проверенные факты

| Факт | Значение |
| --- | --- |
| `RunManifest` | frozen dataclass |
| Повторный save другого fingerprint | записывает второй payload |
| `ReplayCapability` | `exact_replay_supported`, `resume_only`, `rebuild_only` |
| Ledger run | append JSONL в `FileRunLedgerStore.append` |
| Composite resume | checkpoint, затем suffix после `last_event_id` |
| Handoff P07, P08, P10 кампании `20261022` | отсутствуют |
| Двухпроходный replay | не выполнялся |
| `findings_sha256` | `3a0c89907dfead59f50184c71dcbd1f7b56a21eb0275eef6159c543e5ec4714f` |

`occurrence_only` не сводится к byte equivalence: ключ истинен только вместе с `semantic_equivalent` и непустым `occurrence_only_artifacts`, а `raw_byte_equivalent` считается отдельно.

`resolve_replay_capability` возвращает `exact_replay_supported` только при полном snapshot envelope. `require_input_snapshots` закрывает strict profile без snapshot.

## Findings

1. `AUDIT-20261022-P11-001` / `MANIFEST_FILE_REWRITE`. Статус `PROVEN`, вердикт `CONFIRMED`. На ревизии `1d1878e5d6c72b061b9bf01d93495923f3058541` два `FileRunManifestStore.save` с `manifest_id=manifest-same-id` и `execution_fingerprint` `fingerprint-a`, затем `fingerprint-b`, после `store.get` дали `{"replaced": true, "second_fingerprint": "fingerprint-b"}` (`2026-10-22T10:10:40Z`). Команда записана в `findings.json`. Повтор того же объекта тестом разрешён.
2. `AUDIT-20261022-P11-002` / `REPLAY_RUNTIME_UNVERIFIED`. Статус `NOT_PROVEN`, вердикт `NOT_VERIFIABLE`. Нет handoff P07, P08 и P10, runtime A/B не запускался.
3. `AUDIT-20261022-P11-003` / `HYBRID_REPLAY_MODEL`. Статус `PROVEN`, вердикт `DOWNGRADED`. Граница checkpoint и ledger записана в ADR-046. Это не дефект, требующий ledger-only resume.

Машиночитаемая копия: `reports/audit-runs/20261022-p11/findings.json`.
Манифест: `reports/audit-runs/20261022-p11/audit-manifest.json`.
Матрицы: `reports/audit-runs/20261022-p11/equivalence-matrix.csv`, `reports/audit-runs/20261022-p11/replay-eligibility-matrix.csv`.

## Вне объёма

- Исправление повторной записи манифеста.
- Исполнение P07, P08, P10 и P20.
- Изменение бюджетов технического долга.
- Журнал `src/memory`.

## Повтор

```text
# AUDIT-20261022-P11-001, result {"replaced": true, "second_fingerprint": "fingerprint-b"}
# command: reports/audit-runs/20261022-p11/findings.json evidence[0].command
rg -n "class RunManifest" src/bioetl/domain/control_plane/run_manifest.py
rg -n "def persist_manifest" src/bioetl/infrastructure/control_plane/_file_run_manifest_persistence.py
rg -n "list_entries_after" src/bioetl/application/composite/checkpoint/load_service.py
rg -n "BYTE_EQUIVALENT|SEMANTIC_EQUIVALENT|OCCURRENCE_ONLY_DIFFERENT|NOT_EQUIVALENT" src/bioetl
```
