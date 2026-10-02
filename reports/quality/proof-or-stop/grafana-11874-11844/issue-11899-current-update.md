Первоначальное расхождение зафиксировано полным `f042bfb-r2` producer: `config_root.py` измерен в 90%, исторический baseline был 97.5%. Исходный failed guard и raw candidate сохранены в предыдущем immutable evidence.

Последующий полный canonical **R11** на `f9d20f27b43bc9cdc2b2dbd2d23aafce6fa94854`, source SHA-256 `5115449e8c670f5393a58c7009693f666f0eff818fbaa80e0e9ea63f9827ae0f`, независимо проверен: 17 groups, 32 256 PASS, 181 SKIP, 0 failures/errors; line 99.69%, branch 94.32%. Его raw candidate измеряет `config_root.py` в **97.5%**. Принятый параллельный historical inventory сохраняет **100%** для этого модуля; canonical monotonic adoption не утверждает, что 100% измерены новым R11.

Всего у R11 candidate есть 69 строк ниже исторически принятых per-module значений. Они явно перечислены в ledger. Inventory содержит все 2548 текущих модулей, guards проходят без увеличения budget/threshold; отдельный direct measured candidate regression guard возвращает failure и сохранён.

[Current measured candidate, retained-row ledger и независимый R11 receipt](https://github.com/SatoryKono/BioactivityDataAcquisition/tree/06fdb533aaa69456d1480f902cc149a02a21385f/reports/quality/proof-or-stop/grafana-11874-11844).

Задача остаётся открытой: установить причину разницы test selection/execution/provenance, добавить содержательные проверки недостающих branches при необходимости и подтвердить новое измерение полным canonical producer. Не снижать исторический baseline и не выдавать retained historical rows за новые measurements. CI остаётся BLOCKED_EXTERNAL_PERMANENT.
