# Observability sequential run — executive summary

**Run:** `20260821T1503Z-obs-seq-b38cf2d489`  
**BASE:** `origin/main` `b38cf2d489`  
**Branch:** `fix/observability-seq-b38cf2d489`  
**surface_score:** **2** (acceptable) — legend: 0 unacceptable, 1 weak, 2 acceptable, 3 good.

grafana-six не запускался. `docker-compose.monitoring.yml` не стартовали (стек уже был up). `.env` не трогали. В `main` не коммитили.

## Top gaps

1. **P1 #9342** — `9104` null mapping orange on origin/main (gate FAIL). Исправлено на ветке (`gray`).
2. **P1 #9343** — DQ `9103` authored 15px. Исправлено на ветке (`16px`).
3. **P1 #9340** — nav `1000` Dark 200% overflow (чужой live cycle). Не дублировали.

## Inventory formula

YAML `panel_count` = leaf+row = `--check`. Исторический CONTRADICTION на этом SHA **не** воспроизводится.

## Cards

0–8 executed; 9 sweep. Closeout всех P1 этого прогона: **BLOCKED** до merge в origin/main.
