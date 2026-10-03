# Host acceptance for Router 7 and Canvas query errors

The host is a private migration candidate, not an official upstream security backport.
Apply these patches, in order, to pristine Grafana commit
6193dc03311b631b9727b560d24369e683dc396e (v13.2.3):

1. grafana-v13.2.3.patch
2. grafana-canvas-query-error.patch
3. grafana-router-jest-esm.patch

Use git apply --check before each application. Verify the packed bridge and the
host bridge index.mjs/index.d.ts against the repository sources. Install the
upstream graph with the pinned Yarn release and --immutable --mode=skip-build.
Run the Canvas integration suite with NODE_ENV=test and
--testNamePattern="query error" before
the production frontend/Swagger build. The Jest transformer uses the existing
TypeScript compiler to execute the real bridge ESM code; it does not mock away
the bridge or suppress failed tests.

The Canvas patch preserves failed query semantics by rendering QUERY ERROR with
the datasource message instead of missing fields or stale success. Recovery must
restore the scene. Stock Grafana does not include this behavior.

Record source SHA, upstream SHA, patch hashes, bridge/lock hashes, build exits,
test counts, frontend/plugin bundle hashes, image digest and SBOM. Production
build success alone does not establish runtime acceptance.

On a separate Grafana database, verify all six Scene routes, navigation/history,
dashboard variables, selector cancellation, malicious internal-navigation vectors
and the bounded SSR applicability assessment. For panels 9482/3010, test no run,
missing tree/report, a real saved run, HTTP query failure and recovery at normal
and narrow viewports. HTTP failures must retain datasource errors and never turn
into invented successful data.

Before rollout, preserve the current image/plugin artifacts and back up Grafana
data. Upgrade the complete host/plugin set only after required acceptance/proof
gates pass. Recheck source/runtime parity and npm audit/SBOM/Dependabot after
merge. Rollback restores the prior database and the complete previous artifact
set; the previous router/UI defects remain residual risks after rollback.

Current blockers are tracked in #11888, #11889 and #11895. A billing-blocked CI run,
unpatched braces advisory, or failed governance gate is not successful acceptance.
Do not change .env, raise budgets, or suppress advisories to make the candidate pass.

The Actions integration applies all three patches and runs the focused Canvas
failure/recovery tests before the production build. The historical proposed
change remains in workflow-canvas-acceptance.patch for provenance.

Dockerfile.host packages the compiled frontend and both owned plugins against
the pinned official 13.2.3 base. Plugins use Grafana's bundled-plugin directory;
the managed data volume therefore cannot mask them. host-image.json binds the
delivered digest to patch, lock and bundle hashes. The default monitoring compose
retains the accepted 12.2.5 image and does not install or enable the Scenes shadow
app. Explicitly layer compose.acceptance.yml on a separate acceptance host and
database to select the candidate and allow the two owned unsigned plugins.
Enable Scenes manually for shadow review; this does not authorize a cutover.
The acceptance-only runtime-probe is never shipped in the image.

The runtime-probe plugin executes navigation and hydration fixtures through
Grafana's shared react-router external. Install it only on the acceptance host,
run its explicit button, preserve the rendered receipt and remove it afterward.
Its temporary hydration data and harmless constructor are restored in finally.

On the already prepared separate acceptance host, restart Grafana with the
temporary probe mount and exact unsigned-ID override (run from the repo root):

```bash
docker compose -f docker-compose.monitoring.yml -f grafana/tooling/router-v7-bridge/compose.acceptance.yml -f grafana/tooling/router-v7-bridge/compose.probe.yml up -d --no-deps --force-recreate grafana
```

Create an acceptance-only panel of type `bioetl-router-security-probe`, run
`Run host security acceptance`, and preserve its rendered receipt. Remove that
panel/dashboard, then recreate Grafana without the probe layer:

```bash
docker compose -f docker-compose.monitoring.yml -f grafana/tooling/router-v7-bridge/compose.acceptance.yml up -d --no-deps --force-recreate grafana
```

This removes both the probe mount and its unsigned allowlist entry. Do not add
the probe to `.env` or the default compose. Keep the candidate opt-in isolated
until acceptance, SBOM, backup/rollback and proof gates admit managed rollout.
