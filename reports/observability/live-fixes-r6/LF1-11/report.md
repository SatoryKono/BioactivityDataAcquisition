# LF1-11 Execution Report

## Overview
Этот отчет фиксирует статус выполнения живого запуска для проверки манифестов. Выполнение против локального compose-стека не удалось из-за ошибки старта инфраструктуры.

## Execution Details
- **Command:** `docker compose up -d`
- **Exit Code:** 1
- **Error:** `failed to solve: mount source: "overlay", target: "/var/lib/docker/buildkit/containerd-overlayfs/cachemounts/buildkit2484742094", fstype: overlay, flags: 0, data: "workdir=/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/22/work,upperdir=/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/22/fs,lowerdir=/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/14/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/13/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/12/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/11/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/10/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/9/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/8/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/7/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/6/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/5/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/4/fs,index=off,redirect_dir=off", err: invalid argument`
- **Source SHA (base):** `ba13e94f23ff267ac940cc6d8fc9bf35bbc8be06`
- **Deploy SHA (HEAD):** NOT_VERIFIABLE (Среда compose не поднялась)
- **Execution UTC:** 2026-11-08 21:37:14 UTC
- **Run ID:** NOT_RUN
- **Manifest ID:** NOT_RUN
- **Status:** BLOCKED

## Actual vs Expected
- **Expected:** Локальный compose-стек поднимается успешно, выполняется pipeline `chembl_activity`, и манифест записывается в `data/output/control/run_manifest`.
- **Actual:** Compose-стек не поднялся (exit code 1) из-за ошибки в Docker-слоях, запуск BLOCKED.

## Dependencies
- **LF1-10 / #12806:** Живая часть будет выполнена после приёмки LF1-10. На момент отчета compose падает, проверить живую часть невозможно.
- **LF1-05 / #12801:** BLOCKED / NOT_VERIFIABLE (Живая приёмка отклонена, живая среда недоступна).
- **LF1-09 / #12805:** REJECTED. Поставка НЕ РАЗРЕШЕНА, контрольный запуск (ETL/downstream) НЕ РАЗРЕШЁН.

## Artifacts
Запуск не производился из-за ошибки среды. Исторические артефакты остаются в каталоге, но новые не сгенерированы.
