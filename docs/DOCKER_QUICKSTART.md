# Docker quick start

> BIOETL_DOCKER_HELPER_ADR010_ADJUNCT — Local-Only Docker helpers governed by ADR-010.
> Contract: `configs/quality/docker_helper_contracts.yaml`

Docker — optional local adjunct. Выполняйте команды из Linux filesystem mirror,
не из `/mnt/*` или `/tmp`, и не создавайте/не изменяйте `.env`.

## Main stack

После передачи обязательных environment values в текущий процесс:

```bash
python scripts/ops/runtime/docker/runtime_manager.py check --stack main
python scripts/ops/runtime/docker/runtime_manager.py start --stack main --timeout 180
python scripts/ops/runtime/docker/runtime_manager.py status --stack main
```

## Monitoring stack

```bash
python scripts/ops/runtime/docker/runtime_manager.py check --stack monitoring
python scripts/ops/runtime/docker/runtime_manager.py start --stack monitoring --timeout 180
python scripts/ops/runtime/docker/runtime_manager.py status --stack monitoring
```

Manager сам создаёт отсутствующую contracted external network и отклоняет
конфликтующий owner. Не запускайте параллельный raw Compose проект из другого
origin.

## Logs, diagnostics, recovery, stop

```bash
python scripts/ops/runtime/docker/runtime_manager.py logs --stack main --tail 100
python scripts/ops/runtime/docker/runtime_manager.py diagnose --stack main
python scripts/ops/runtime/docker/runtime_manager.py recover --stack main --timeout 180
python scripts/ops/runtime/docker/runtime_manager.py stop --stack main --timeout 60
```

Для Desktop/WSL recovery используйте evidence-first wrapper:

```powershell
.\scripts\ops\runtime\docker\restart-docker.ps1 -TimeoutSeconds 180
```

Запрещённые routine recovery действия: `down -v`, volume/system prune, удаление
VHDX/data root, force-kill без двухфакторного last-resort подтверждения и
`wsl --shutdown`.

Подробнее: `docs/DOCKER_SETUP.md` и
`docs/05-operations/runbooks/docker-stability.md`.
