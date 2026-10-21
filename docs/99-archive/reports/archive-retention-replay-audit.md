### Матрица аудита: Archive, Retention, Replay (Policy → Apply → Read, Concurrency, Restore)

| Поверхность хранения | Звено цепочки (Тема) | Чем доказано (Файл и тест) | Вывод/Обоснование (статус) |
| --- | --- | --- | --- |
| **Control Plane** (FileArchiveStore / Manifests, Ledgers) | **Policy → Apply** (Применение Lifecycle Policy) | `test_file_artifact_lifecycle_store.py::test_lifecycle_apply_deletes_only_expired_unprotected_files` | Успешно. Политика корректно вычисляет просроченные незащищенные артефакты и применяет удаление, сохраняя `retained_manifest`. |
| **Control Plane** (FileArchiveStore) | **Read / Restore** (Чтение и восстановление из архива) | `test_archive_restores_without_changing_source_and_rejects_overwrite` (unit)<br>`test_public_verify_cannot_read_archive_without_original_sources` (integration) | Успешно. Файлы восстанавливаются без повреждения исходных данных. Отклоняется перезапись. Публичная проверка архива корректно работает. |
| **Control Plane** (FileArchiveStore) | **Concurrency** (Параллельные операции) | `test_archive_parallel_reads_keep_checksum_validation` | Успешно. Параллельные чтения бандлов при `verify_entry` используют барьеры и сохраняют консистентность чексумм. |
| **Composite Replay Inputs** (CompositeReplayBundle) | **Concurrency** | `test_composite_replay_inputs.py::test_parallel_reads_freeze_one_version_and_block_premature_seal` | Успешно. Асинхронные/параллельные чтения фиксируют единственную версию (`freeze`) и блокируют преждевременный `seal()`. |
| **Delta Tables (Silver/Gold)** (Maintenance Archive / RetentionDedup) | **Policy → Apply** (Очистка и дедупликация) | `test_retention_dedup_primary_keys.py` | Успешно. Дедупликация и retention delta таблиц (Vacuum) работают на уровне инфраструктуры. Политика RetentionPolicy применяется корректно. |

Пробелов в покрытии не найдено, все затронутые звенья цепочки полностью покрыты существующими тестами.
Дополнительные проверки писать не требуется, так как существующий код (включая unit/integration/architecture слои) уже реализует проверки retention/archive/replay и concurrency/restore на всех поверхностях хранения.
