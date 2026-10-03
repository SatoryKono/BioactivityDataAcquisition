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

The checked Actions integration is also supplied as workflow-canvas-acceptance.patch.
It is not active until applied by a workflow-authorized publisher; existing local
credentials were insufficient. Its absence is an acceptance blocker.
