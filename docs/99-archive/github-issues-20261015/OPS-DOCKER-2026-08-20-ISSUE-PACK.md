# Docker Desktop local-stack residuals — 2026-08-20

**Wave code:** OPS-DOCKER-20260820
**Date:** 2026-08-20
**Checkout:** `E:\github\BioactivityDataAcquisition`
**ADR:** ADR-010 (Docker optional, local-only)

Live recovery of `main` / `monitoring` / `neo4j` from a foreign
`BioactivityDataAcquisition2` origin. Path-normalization for Windows vs
`/mnt/e` `PROJECT_ORIGIN` is already on `origin/main`
(`normalize_runtime_path` remaps after relative join). These issues own the
**remaining** defects. Do not treat deleting the second clone as sufficient.

## Constraints (all children)

- Docker remains optional (ADR-010). Default CI must not require a live engine.
- Do not create, edit, rename, move, overwrite, or delete `.env` / `.env.*`.
- Do not increase technical-debt budgets, exemptions, or thresholds.
- Do not use `docker compose down -v`, prune, or volume deletion as the happy path.
- No secrets, workstation passwords, or `.env` values in issue text or tests.

## Issue map

| ID | GitHub | Title | Priority |
| --- | --- | --- | --- |
| Parent | [#9177](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9177) | Coordinate 2026-08-20 Docker Desktop residuals | P1 |
| A | [#9179](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9179) | Re-seed Neo4j auth on `runtime_manager start\|recover` | P1 |
| B | [#9180](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9180) | Stop using slow `/health/ready` as the Docker healthcheck | P1 |
| C | [#9178](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9178) | Fail closed when a second clone steals global Compose names | P2 |
| D | [#9181](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9181) | Fix Windows-false Docker unit tests (chmod + report-root override) | P2 |
