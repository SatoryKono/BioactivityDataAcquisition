# Docker Helper Credential History Audit

Date: 2026-05-21
Issue: #4442
Scope: `docker-compose.redis.yml`, `docker-compose.minio.yml`,
`docker-compose.sonarqube.yml`, `.env.example`,
`configs/quality/docker_helper_contracts.yaml`

## Evidence Commands

```bash
git -c filter.lfs.process= -c filter.lfs.required=false log --all --format='%H %s' -S 'bioetl_redis_secure' -- docker-compose.redis.yml .env.example docker-compose.sonarqube.yml docker-compose.minio.yml
git -c filter.lfs.process= -c filter.lfs.required=false log --all --format='%H %s' -S 'minioadmin_secure' -- docker-compose.redis.yml docker-compose.minio.yml docker-compose.sonarqube.yml .env.example
git -c filter.lfs.process= -c filter.lfs.required=false log --all --format='%H %s' -S 'sonarqube_secure' -- docker-compose.redis.yml docker-compose.minio.yml docker-compose.sonarqube.yml .env.example
git -c filter.lfs.process= -c filter.lfs.required=false log --all --format='%H %s' -S 'sonarqube_system' -- docker-compose.redis.yml docker-compose.minio.yml docker-compose.sonarqube.yml .env.example
git -c filter.lfs.process= -c filter.lfs.required=false grep -n -E 'bioetl_redis_secure|minioadmin_secure|sonarqube_secure|sonarqube_system' HEAD -- docker-compose.redis.yml docker-compose.minio.yml docker-compose.sonarqube.yml .env.example
git -c filter.lfs.process= -c filter.lfs.required=false grep -n -E 'bioetl_redis_secure|minioadmin_secure|sonarqube_secure|sonarqube_system' 34e0512c9edbcb710c9a34b799994ea415346c0c -- docker-compose.redis.yml docker-compose.minio.yml docker-compose.sonarqube.yml .env.example
```

## Findings

- Historical default credential tokens were present in commit
  `34e0512c9edbcb710c9a34b799994ea415346c0c` in Docker helper compose
  defaults and `.env.example`.
- Commit `aab278b1f2ee546f7388152529829688381dd140` removed those defaults,
  introduced required environment expansion, and added
  `configs/quality/docker_helper_contracts.yaml`.
- Current `HEAD` has no direct matches for the retired default tokens in
  `docker-compose.redis.yml`, `docker-compose.minio.yml`,
  `docker-compose.sonarqube.yml`, or `.env.example`.
- Current `configs/quality/docker_helper_contracts.yaml` intentionally lists
  the retired tokens under `forbidden_default_tokens`; those references are
  governance evidence, not live defaults.

## Historical Matches

Commit `34e0512c9edbcb710c9a34b799994ea415346c0c` contained these retired
default-token surfaces:

- `.env.example`: `REDIS_PASSWORD`, `MINIO_ROOT_PASSWORD`,
  `SONARQUBE_DB_PASSWORD`, `SONARQUBE_SYSTEM_PASSWORD`.
- `docker-compose.minio.yml`: `MINIO_ROOT_PASSWORD` fallback default.
- `docker-compose.redis.yml`: Redis server, healthcheck, and exporter fallback
  defaults.
- `docker-compose.sonarqube.yml`: database and system-passcode fallback
  defaults.

## Current State

Current Docker helper files require explicit local environment values and bind
service ports to localhost. The history scan confirms the removed defaults
remain discoverable in git history, so any environment that treated those
values as real local credentials must rotate them before using the helper
stacks again.

## Recommendation

- Keep the current fail-closed compose behavior and forbidden-token governance
  contract.
- Treat the historical tokens as public and unusable.
- Do not rewrite repository history unless repository owners explicitly decide
  that removing the public history is worth the coordination cost.
