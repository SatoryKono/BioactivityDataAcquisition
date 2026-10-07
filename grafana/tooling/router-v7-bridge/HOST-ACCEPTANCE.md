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

Each plugin matrix job verifies its bundle and uploads the complete dist tree.
The host job downloads those exact outputs, builds Dockerfile.host with the
newly compiled frontend, and records the produced image-config digest. It pulls
the registry digest from host-image.json and requires matching frontend/plugin
bytes, filenames, owners, modes, symlink targets and runtime configuration.
Registry-manifest and image-config digests identify different objects; receipt
fields keep them separate. Creation timestamps are excluded from artifact parity.
Any artifact/configuration mismatch blocks delivery. CI preserves build metadata
and the parity receipt; an absent receipt does not establish acceptance.

Dockerfile.host packages the compiled frontend and both owned plugins against
the pinned official 13.2.3 base. Plugins use Grafana's bundled-plugin directory;
the managed data volume therefore cannot mask them. host-image.json binds the
delivered digest to patch, lock and bundle hashes. The default monitoring compose
selects the managed JSON-dashboard variant and does not install or enable the
Scenes shadow app. This pin must not be deployed until the exact delivery commit
passes required CI and Proof-or-Stop gates. Explicitly layer compose.acceptance.yml on a separate acceptance host and
database to select the candidate and allow the two owned unsigned plugins.
Enable Scenes manually for shadow review; this does not authorize a cutover.
The acceptance-only runtime-probe is never shipped in the image.

`Dockerfile.managed` derives the JSON-dashboard host from the same immutable
candidate, removing the Scenes package. `managed-image.json` binds this variant
to its parent and recipe. `compose.managed-acceptance.yml` selects it for an
isolated database. The default compose uses this same managed image with only
SelectorShell permitted as an unsigned plugin; the temporary probe is excluded.
An isolated acceptance receipt does not establish default-host delivery. Preserve
a fresh database backup before deployment and repeat browser acceptance on the
default host after deployment before closing #11888, #11889 or #11895.
`python -m scripts.ops verify-router-managed-image` checks the trusted parent layer prefix and compares
every exported filesystem record against exactly the parent minus Scenes.
The registry image and independently rebuilt image must both match, including
backend, libraries, frontend, SelectorShell, owners, modes and symlink targets.
Host Python reads the tar streams without extracting paths or running image
executables. Only timestamps are excluded. CircleCI preserves the resulting
receipt; this image parity check does not itself establish browser acceptance.

The active CircleCI Docker gate also rebuilds both locked plugin graphs and
compares every resulting file with the parent image's exported plugin trees.
This includes source maps, metadata and other assets; missing, extra or changed
files block delivery even when module.js and plugin.json hashes match. Release
plugin artifacts must reproduce the CI build tree. A local build in a different
working directory is diagnostic evidence until the complete file comparison
passes, because webpack source-map metadata can depend on that directory.

The runtime-probe plugin executes navigation and hydration fixtures through
Grafana's shared react-router external. Install it only on the acceptance host,
run its explicit button, preserve the rendered receipt and remove it afterward.
Its temporary hydration data and harmless constructor are restored in finally.
Pinned Grafana 13.2.3 already maps react-dom/client in
public/app/features/plugins/loader/sharedDependencies.ts. The host workflow
verifies that mapping before compiling. Node probe tests verify fixture behavior;
they do not replace the real host's module-loading/browser acceptance.

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

For the JSON-dashboard variant, use `compose.managed-acceptance.yml` in place of
`compose.acceptance.yml`, and `compose.managed-probe.yml` in place of
`compose.probe.yml`. This temporary allowlist contains only SelectorShell and
the probe. After capture, recreate with the managed acceptance layer alone;
Scenes remains absent and the probe mount and permission are removed.
