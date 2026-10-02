# BioETL Scenes app

Optional, read-only presentation adapter governed by ADR-053.

The app exposes six task-oriented routes while the five provisioned dashboard
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

Disable or remove `bioetl-scenes-app` from Grafana. The five JSON dashboards
under `grafana/dashboards/` continue to be provisioned and reachable; no data
or control-plane migration is involved.

ADR-053 approved this five-UID cutover on 2026-10-02. Pipeline Flow opens
Incident fleet diagnostics; Dependency Health opens saved Overview provider
evidence. Historical seven-UID capture ledgers do not prove current parity.


## Router migration candidate

The current lockfile consumes the private BioETL Router 7 bridge archive.
Deploy this artifact only with the matching patched Grafana 13.2.3 frontend
whose shared router export is Router 7.18.4. A stock host version number alone
is insufficient: an older shared Router 6 context is incompatible with the
Scenes Router 7 dependency. The integration patch and archive are maintained
in `grafana/tooling/router-v7-bridge/`.

This is a migration candidate for #11888 and #11889. The shared Grafana rollout
remains pending exact-SHA CI and runtime acceptance. Preserve the previous host
image, plugin artifacts, manifests, lockfiles, and Grafana data backup for rollback.
