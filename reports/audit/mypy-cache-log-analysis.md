# Анализ restore/hit логов mypy

## 1. Сводная таблица прогонов

| run_id | attempt | restore-hit | key | mypy-с | диагностики-хеш |
|--------|---------|-------------|-----|--------|-----------------|
| [42268383298](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42268383298) | 1 | YES | `facb0b5673c7` | 1.90 | `5005501428138591960` |
| [42262670607](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42262670607) | 1 | YES | `ef518a0f84c3` | 2.50 | `5005501428138591960` |
| [42258320278](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42258320278) | 1 | YES | `35bba54760b3` | 1.19 | `5005501428138591960` |
| [42255690985](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42255690985) | 1 | YES | `4af92fe06aba` | 3.18 | `5005501428138591960` |
| [42249828912](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42249828912) | 1 | YES | `22ee9243046d` | 3.12 | `5005501428138591960` |
| [42214305225](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42214305225) | 1 | YES | `21d25885c862` | 1.48 | `5005501428138591960` |
| [42189454943](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42189454943) | 1 | YES | `a4d7a31fccdc` | 1.75 | `5005501428138591960` |
| [42181874267](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42181874267) | 1 | YES | `f240ba1e5e54` | 1.94 | `5005501428138591960` |
| [42179584169](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42179584169) | 1 | YES | `874da0fd3843` | 1.58 | `5005501428138591960` |
| [42177262318](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42177262318) | 1 | YES | `2ad61c18314f` | 1.61 | `5005501428138591960` |
| [42175536415](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42175536415) | 1 | YES | `045e55bcbb6f` | 1.96 | `5005501428138591960` |
| [42173253283](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42173253283) | 1 | YES | `f19354df58af` | 1.09 | `5005501428138591960` |
| [42171289936](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42171289936) | 1 | YES | `777f88e4d945` | 2.21 | `5005501428138591960` |
| [42111299168](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42111299168) | 1 | YES | `20bc18f2c1f5` | 1.17 | `5005501428138591960` |
| [42083330972](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42083330972) | 1 | YES | `fc55be414ca7` | 2.00 | `5005501428138591960` |
| [42070040059](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42070040059) | 1 | YES | `ed297e0edf7a` | 1.97 | `5005501428138591960` |
| [42061320681](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42061320681) | 1 | YES | `10247db6ab6e` | 2.11 | `5005501428138591960` |
| [42055026296](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42055026296) | 1 | YES | `ca28e76f8b39` | 1.82 | `5005501428138591960` |
| [42050863486](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42050863486) | 1 | YES | `f78f2edfd0c0` | 2.94 | `5005501428138591960` |

## 2. Цитаты журналов (Evidence)

### [Run 42268383298](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42268383298)
```text
2026-11-06T18:11:47.4085735Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-facb0b5673c7cec55b6f4efb230f531618e9b56e
```

### [Run 42262670607](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42262670607)
```text
2026-11-06T17:33:55.9337669Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-ef518a0f84c3626fd43acb6c5198d74320efe21e
```

### [Run 42258320278](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42258320278)
```text
2026-11-06T17:05:37.5546530Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-35bba54760b39421b79f63186c79833498fe758d
```

### [Run 42255690985](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42255690985)
```text
2026-11-06T16:48:27.2331693Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-4af92fe06abad38388108c4b8f80b9f57a95d436
```

### [Run 42249828912](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42249828912)
```text
2026-11-06T16:10:48.4248609Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-22ee9243046df1b1f41350de8fdf56802dd96f94
```

### [Run 42214305225](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42214305225)
```text
2026-11-06T12:00:30.0783100Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-21d25885c8622fc241fbca51ce37eb0310dff6e9
```

### [Run 42189454943](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42189454943)
```text
2026-11-06T08:42:00.4530980Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-a4d7a31fccdccf4cac83b6b196cb3115f16e8080
```

### [Run 42181874267](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42181874267)
```text
2026-11-06T07:36:00.4279606Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-f240ba1e5e540ae933b3ceadabc95bb51b30bb67
```

### [Run 42179584169](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42179584169)
```text
2026-11-06T07:15:11.1627586Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-874da0fd3843d78895d0dd46a8c3b57dbf6788d8
```

### [Run 42177262318](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42177262318)
```text
2026-11-06T06:53:46.2951100Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-2ad61c18314f262693a5c782612f9adad5cb074d
```

### [Run 42175536415](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42175536415)
```text
2026-11-06T06:37:20.0776444Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-045e55bcbb6f8fbefccd5457d77bb503a985420f
```

### [Run 42173253283](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42173253283)
```text
2026-11-06T06:15:42.0270187Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-f19354df58afe8f69182d23bb0fe21bc7cec4588
```

### [Run 42171289936](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42171289936)
```text
2026-11-06T05:56:22.1137804Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-777f88e4d9454d359aec2924f578c5600d304060
```

### [Run 42111299168](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42111299168)
```text
2026-11-05T21:18:11.3193593Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-20bc18f2c1f5ff23b23d732d4c9aa703fddeb8b7
```

### [Run 42083330972](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42083330972)
```text
2026-11-05T18:21:26.7545174Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-fc55be414ca7627d7e988b147cf502de2c987fa6
```

### [Run 42070040059](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42070040059)
```text
2026-11-05T16:59:42.3784861Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-ed297e0edf7ae487a1b2768b92417881b24b94ab
```

### [Run 42061320681](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42061320681)
```text
2026-11-05T16:07:15.5466870Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-10247db6ab6edb7ee5bdcf14807e70639e652c47
```

### [Run 42055026296](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42055026296)
```text
2026-11-05T15:27:21.8765734Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-ca28e76f8b39d114c537351aad1d27c53b40e8cc
```

### [Run 42050863486](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42050863486)
```text
2026-11-05T15:02:54.8727395Z Cache hit for restore-key: Linux-X64-python-/opt/hostedtoolcache/Python/3.12.16/x64-mypy-91612c9d2d46ce7c029a3379c358f1068c63a877f58defa7a89b287491da34f0-f78f2edfd0c0052fafdfc5acc009f4164c4ae115
```

## 3. Выводы

### Установлено
- **Длительность hit-прогонов**: В проанализированных запусках среднее время выполнения mypy при попадании в кеш (hit=19) составило 1.97 с. Для промахов/отсутствия кеша (miss=0) нет наблюдений, поэтому средняя длительность miss не определена. В логах мы видим, что restore-keys работает: `Cache hit for restore-key: ...` восстанавливает кеш даже когда точного ключа с SHA нет.
- **Поведение кеша**: Восстановление по `restore-keys` без точного SHA работает и находит ближайший префикс. Почти все последние прогоны успешно восстанавливают кеш (restore-hit: YES), так как работает префикс `Linux-X64-python-3.12-mypy-<hash>-`.

### Не установлено
- **Сравнение hit/miss и корреляция hit ↔ длительность**: Недоступны по этой выборке: все 19 наблюдений имеют `restore_hit: "YES"`, наблюдений miss нет. Нулевая численность группы miss не означает нулевую длительность.
- **Причинность**: Без контролируемого эксперимента (warm vs cold на одном и том же коммите) нельзя достоверно утверждать, что именно кеш экономит Х секунд, так как размер кодовой базы и сложность типов могут меняться.
