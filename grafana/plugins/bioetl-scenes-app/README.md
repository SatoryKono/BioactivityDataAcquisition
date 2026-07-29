# BioETL Scenes app

Optional, read-only presentation adapter governed by ADR-053.

The app exposes six task-oriented routes while the seven provisioned dashboard
UIDs remain the authoritative fallback and rollback surface. It has no backend,
write action, custom datasource, or BioETL core dependency.

## Build

```bash
npm ci
npm run typecheck
npm run test:ci
npm run build
```

The pinned lockfile and Grafana/Scenes dependency policy make the `dist/`
artifact reproducible. The package is not mounted or enabled by the default
monitoring compose surface during shadow rollout.

## Disable and rollback

Disable or remove `bioetl-scenes-app` from Grafana. The seven JSON dashboards
under `grafana/dashboards/` continue to be provisioned and reachable; no data
or control-plane migration is involved.
