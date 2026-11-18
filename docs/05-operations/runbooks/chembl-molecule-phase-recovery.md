______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-11-18'

______________________________________________________________________

# Восстановление фаз ChEMBL Molecule из Bronze

## Trigger

В ранее обработанном `chembl_molecule` исходный `max_phase` заполнен, но
Silver содержит NULL или усечённое значение; Gold исключён по
`column_filter_mismatch:potential_duplicate`.

## Impact

Исправления #13197 и #13198 сохраняют reviewed `max_phase`, включая `0.5`,
и удаляют ошибочное условие `potential_duplicate` из Gold eligibility.
Уже записанные NULL-фазы требуют повторной обработки. Контракт Gold остаётся
строгим, source-profile extraction params, hash algorithm и список hash-полей
не меняются. Исправленные значения меняют `content_hash`; изменившийся фильтр
меняет effective-config digest и допустимый Gold cohort.

## Preconditions

Использовать проверенный commit с исправлениями и прошедшими локальными
transformer, Gold/SCD2 и config tests. Для исходного batch должны быть доступны
Bronze, прежние отчёты и право создать отдельные выходные каталоги.

1. Зафиксировать точный commit, merged config, SHA-256 и список исходных
   `*.jsonl.zst`, число записей и уникальных `molecule_id`, распределение фаз.
   Сохранить прежние Silver, Gold, checkpoints, manifests и отчёты.
2. Задать в окружении дочернего процесса новые абсолютные `BIOETL_DATA_DIR`,
   `BIOETL_REPORT_ROOT`, `BIOETL_ARCHIVE_ROOT`. Проверить resolved paths и
   вычисленные Settings: назначения не должны совпадать с исходными или
   общими таблицами. `.env` не изменять. Для локального отдельного report root
   допустимо явно задать `BIOETL_ENFORCE_REPORT_ROOT_MARKER=false` в том же
   процессе; DQ policy и Gold validation остаются строгими.
3. Проверить preview через `--dry-run` в отдельном preview root. Основной
   backfill запускать в другом новом root: backfill очищает назначения.

## Procedure

Пример для сохранённого batch от 18 ноября 2026 года; заменить пути на
проверенные абсолютные каталоги. На Windows использовать
`.venv-win/Scripts/python.exe` вместо `python`.

```text
python -m bioetl run --pipeline chembl_molecule --run-type backfill --limit 1000 --use-cached-bronze --cached-bronze-path <absolute-original-molecule-bronze-dir> --cached-bronze-date 2026-11-18 --no-exact-replay --required-persistence-profile degraded_observable --no-ensure-observability-backend
```

Cached source читает сжатый Bronze без обращения к provider API. Это ordinary
cached processing исправленным кодом: новые run ID, manifest и effective-config
anchors со ссылкой на исходный batch. Явный persistence profile фиксируется
в отчёте; он не отключает DQ или строгую Gold validation. Strict exact replay
предназначен для воспроизведения закреплённого результата и не описывает
восстановление новым кодом. Resume продолжает прежний запуск/checkpoint;
для этого восстановления его не использовать.

## Verification

- Сверить SHA-256 исходника до и после обработки; сопоставить Bronze, actual
  Silver Delta и current Gold Delta по `molecule_id`, проверить `entity_id`.
  При чтении Delta учитывать partition columns, включая `molecule_type`.
- Проверить точные фазы, nullable policy и полный strict Gold contract без
  служебных колонок SCD2. Сопоставить каждый reject с reason code, проверить
  баланс всех стадий и отсутствие необъяснённых потерь.
- Для исторического снимка из 1000 записей требуется: Silver=1000,
  заполненные фазы=1000, Gold current=1000, `0.5`=3; дробные IDs:
  `CHEMBL14830`, `CHEMBL23194`, `CHEMBL31184`.
- Повторить тот же cached input в режиме `incremental` в принятом новом root.
  Сопоставить entity IDs, normalized content hashes, число current rows,
  SCD2 versions и даты начала версий. Повторный backfill с очисткой не
  доказывает идемпотентность SCD2 merge.
- Проверить перечень downstream outputs, включая `composite_molecule`.
  Восстановленные и ещё открытые области перечислить явно; результат одного
  снимка не означает восстановление всей базы.
- Отдельно запустить `python -m bioetl workflow run chembl_molecule --limit 1000`
  с ещё одним новым data/report/archive root. Оценивать фактический новый
  cohort; не предполагать равенство исторической API-выборке. Сохранить
  HTTP/retry ошибки, exit status, отчёты и monitoring evidence.

## Rollback/Recovery

До приёмки не переключать consumers на новые outputs. При ошибке сохранить
диагностические outputs и исходные данные, устранить причину с regression
proof и повторить в новом root. Для отката потребитель использует прежнее
назначение; не заменять и не удалять оригиналы. Локальные проверки привязать
к точному SHA отдельно от remote CI.

## Источники контракта

- [Provider reference](../../04-reference/providers/chembl/molecule.md)
- [Molecule schema](../../04-reference/schemas/domain/chembl/molecule-schema.md)
- [Gold contract](../../04-reference/contracts/gold/chembl_molecule_v1.0.json)

## Post-incident

Сохранить команды, exit codes, новый run/manifest ID, effective-config digest,
контрольные суммы, сравнение фаз и Gold, перечень downstream datasets.
Закрывать назначенные задачи только по проверенным критериям; результаты
локального запуска и CI на текущем SHA указывать раздельно.

## Compliance

Оригиналы и `.env` сохраняются. DQ и strict Gold validation обязательны;
исходная выборка ChEMBL и hash policy не расширяются. Перезапуск сервисов
и переключение consumers не являются частью этой процедуры восстановления.
