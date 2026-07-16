______________________________________________________________________

Version: 1.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only optional Neo4j memory backend.
  Last verified: '2026-07-16'

______________________________________________________________________

# Neo4j backend recovery — quick start

## Trigger

Use this runbook when the optional Neo4j memory backend is unavailable or its
HTTP/Bolt readiness fails.

## Impact

Priority P2. Neo4j is not a required BioETL pipeline dependency; failure
reduces auxiliary memory retrieval only.

## Preconditions

- Work from the canonical Linux filesystem runtime origin.
- Supply required Neo4j values through the current process environment; do not
  create or edit `.env`.
- Preserve `bioetl-neo4j_neo4j_data`, its legacy source volume and verified
  backups. Recovery never uses volume deletion or prune.

## Procedure

1. Run the read-only contract and host gate:

   ```bash
   python scripts/ops/runtime/docker/runtime_manager.py check --stack neo4j
   ```

2. If Docker Desktop/WSL is unavailable, capture bounded evidence first:

   ```powershell
   .\scripts\ops\runtime\docker\restart-docker.ps1 `
     -TimeoutSeconds 180 `
     -ReportPath reports/quality/docker-desktop-recovery.json
   ```

3. Diagnose, recover and verify readiness through the single lifecycle owner:

   ```bash
   python scripts/ops/runtime/docker/runtime_manager.py diagnose --stack neo4j
   python scripts/ops/runtime/docker/runtime_manager.py recover --stack neo4j --timeout 180
   python scripts/ops/runtime/docker/runtime_manager.py status --stack neo4j
   ```

4. Run the backend-specific protocol check when configured:

   ```bash
   bash scripts/ai/mcp/check_neo4j_memory.sh
   ```

Do not replace readiness polling with fixed sleeps or direct restart loops.
`status` must report the required service healthy; a merely running container
is not success.

## Escalation

If the same bounded recovery fails three times, preserve the incident report,
manager diagnostics and recent bounded logs, then escalate. Do not remove the
container or volume as an automatic next step.

## Verification

- manager preflight has no errors;
- `status --stack neo4j` succeeds;
- HTTP 7474 and Bolt 7687 protocol checks succeed;
- volume identity before/after is unchanged;
- no new restart, OOM, unhealthy or image-identity finding exists.

## Rollback/Recovery

Stop only through `runtime_manager.py stop --stack neo4j`. Restore a target
volume only from a verified backup while retaining the legacy source. Never use
`down -v`, prune, VHDX deletion or an unbounded Docker Desktop restart.

## Post-incident

Record the failing check, bounded recovery actions, evidence paths, volume
identity, operator and follow-up owner.

## Compliance

Neo4j remains optional under ADR-010. Recovery does not store credentials in
reports, mutate `.env` or delete protected volumes.

## References

- `docs/DOCKER_SETUP.md`
- `docs/05-operations/runbooks/docker-compose-project-migration.md`
- `docs/05-operations/runbooks/docker-stability.md`
