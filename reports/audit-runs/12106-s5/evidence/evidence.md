# Evidence - Wave D (Gold Crash/Restart)

## Строка 10b (Crash during postwrite collaborator gate) - VERIFIED

`NoOpMetadataWriter` выходит из `_write_gold_metadata` до collaborator-а.
Поэтому probe ставит отдельный metadata writer и coordinator.

`create_gold_metadata_bundle` вызывается из `_prepare_gold_metadata_write`
после `_dispatch_write`. Первый вызов (v1) возвращает bundle, второй (v2)
делает `os.kill(os.getpid(), signal.SIGKILL)`. Родительский процесс читает
обе таблицы: `chembl.activity__v1_0_0` хранит `legacy_value`,
`chembl.activity__v2_0_0` хранит `value`. Код выхода дочернего процесса
равен `-SIGKILL`.

## Строка 11a (crash before commit) - VERIFIED

Дочерний процесс подменяет `_dispatch_write` и завершается SIGKILL до
`write_deltalake`. Каталогов `activity__v1_0_0` и `activity__v2_0_0` нет.

## Строки 8, 9, 10, 11b, 11c - NOT_VERIFIABLE

Физический commit Gold — синхронный `module.write_deltalake(...)` в
`_write_prepared_simple_delta`. В этой функции нет `await`/`yield`, поэтому
SIGKILL нельзя поставить внутрь native commit (строки 8, 9, 11b) и между
возвратом `write_deltalake` и возвратом helper-а (строка 11c).

`_write_single_target_impl` вызывает `_post_write_gold` сразу после
`COMMITTED_POSTWRITE_PENDING`. Отдельного pre-entry gate в этом шве нет
(строка 10). Это не power-loss и не доказательство всей durability Gold.
