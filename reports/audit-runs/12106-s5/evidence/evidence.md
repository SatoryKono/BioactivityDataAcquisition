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

`_write_prepared_simple_delta` вызывает `module.write_deltalake(...)` и не
содержит `await`/`yield`. Это проверка Python-границы, а не crash внутри
native commit. Отсутствие yield не исключает `SIGKILL` во время
`write_deltalake`, поэтому сбой внутри native commit (строки 8, 9, 11b)
остаётся `NOT_VERIFIABLE`. После вызова в helper нет отдельного Python-шва
для детерминированного барьера (строка 11c).

`_write_single_target_impl` вызывает `_post_write_gold` сразу после
`COMMITTED_POSTWRITE_PENDING`. Отдельного pre-entry gate в этом шве нет
(строка 10). Это не power-loss и не доказательство всей durability Gold.
