# Evidence - Wave D (Gold Crash/Restart)

## Строка 10b (Crash during postwrite collaborator gate) - VERIFIED
**Метод проверки:**
Использован harness (child_runner). Мок `MetadataWriter` при вызове `record_write_outcome` (после коммита в дельту) выполняет `os.kill(os.getpid(), signal.SIGKILL)`.
**Результат:**
Доказано, что `chembl.activity__v1_0_0` и `chembl.activity__v2_0_0` (dual-write targets) успешно читаются после аварийного завершения дочернего процесса.

## Строки 8, 9, 10, 11a, 11b, 11c - NOT_VERIFIABLE
**Ограничения GoldWriter:**
При анализе `src/bioetl/infrastructure/storage/gold/writer_implementation.py` обнаружено, что механизм физической записи Gold-слоя делегируется `deltalake` без предоставления синхронных pre-entry или commit барьеров (отсутствуют hook-и до dispatch и до фиксации лога Delta). Это означает, что невозможно точно прервать процесс *во время* физического коммита (строка 8, 9, 11b) или *непосредственно перед* коммитом внутри writer'а (строки 11a).
- В SilverWriter такие барьеры присутствуют (`SilverOutcomeBoundary` / `SilverCrashGates`), но в `GoldOutcomeBoundary` и `_write_single_target_impl` эти швы (pre-entry gate) не реализованы.
Таким образом, проверка точного crash/restart поведения на границах коммита для Gold недоступна.
