______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only optional Docker adjunct (ADR-010).
  Last verified: '2026-09-05'

______________________________________________________________________

# Docker security baseline

## Trigger

Use this runbook to reproduce the current RF-001/RF-002 image baseline for
`Dockerfile.bioetl`, or when a security/CI claim needs the bounded
Trivy/SBOM evidence artifact from `docker.yml`.

## Impact

- Priority: P2.
- Missing or unreproducible baseline evidence blocks RF-001/RF-002 closure
  claims and supply-chain review.
- Generated files stay under `reports/security/`, are ignored by Git, and are
  attached by `docker.yml` as the bounded
  `bioetl-security-baseline-<sha>` workflow artifact.

## Preconditions

- Runtime profile: Local-Only optional Docker adjunct (ADR-010).
- Clean checkout of the exact commit being measured (`git status --short`
  empty for Dockerfile/image inputs).
- Docker daemon available; do not substitute mutable tags or unpinned package
  versions when collecting closure evidence.
- Do not create, edit, rename, move, or delete any `.env` file.

## Procedure

### Identity

Run from a clean checkout of the exact commit being measured:

```powershell
$baselineSha = git rev-parse HEAD
git status --short
docker build --pull --no-cache --target builder `
  -f Dockerfile.bioetl -t "bioetl-builder:$baselineSha" .
docker build --pull --no-cache `
  -f Dockerfile.bioetl -t "bioetl:$baselineSha" .
docker image inspect "bioetl:$baselineSha" --format '{{.Id}} {{json .RepoDigests}}'
```

The Dockerfile pins one immutable Wolfi base digest for its builder and runtime
root stages. Direct Wolfi packages pin Python `3.13.15-r6` and `uv 0.11.26-r0`;
the final scratch stage copies the audited runtime root and locked environment.

### Runtime versions

```powershell
docker run --rm --entrypoint python "bioetl:$baselineSha" --version
docker run --rm --entrypoint python "bioetl:$baselineSha" -c `
  'import importlib.util; print("pip=" + ("absent" if importlib.util.find_spec("pip") is None else "present"))'
docker run --rm --entrypoint uv "bioetl-builder:$baselineSha" `
  pip freeze --python /app/.venv/bin/python
```

The CI artifact additionally records the final image ID, source SHA, Wolfi base
and direct package identities, runtime Python version, runtime `pip` presence,
installed packages, Trivy version/DB metadata, and the GitHub Trivy alert
snapshot used to populate `alert_number` where an existing alert identity is
available. The current least-privilege runtime image has no `pip` module;
package inventory is read through `importlib.metadata` instead. The runtime is
shell-less, has no package manager, and runs as the Chainguard non-root account
`65532:65532`; Compose therefore invokes `bioetl` directly instead of using
`/bin/sh -c`. Its private `/tmp` is owned by the runtime account with mode
`0700`, preventing cross-user writes while preserving Python temporary-file
support.

### Trivy reproduction

The pinned workflow action installs Trivy `v0.70.0`. A local installation of
that exact version can reproduce both evidence formats:

```powershell
New-Item -ItemType Directory -Force reports/security | Out-Null
trivy image --severity CRITICAL,HIGH,MEDIUM,UNKNOWN --format json `
  --output reports/security/trivy-results.json "bioetl:$baselineSha"
trivy image --severity CRITICAL,HIGH,MEDIUM,UNKNOWN --format sarif `
  --output reports/security/trivy-results.sarif "bioetl:$baselineSha"
trivy image --severity CRITICAL,HIGH,MEDIUM --exit-code 1 `
  "bioetl:$baselineSha"
```

The first two commands are evidence collection and do not hide findings. The
last command is the enforcement boundary and must remain blocking. RF-002 moved
the supported Python 3.13 runtime to the pinned Wolfi/scratch image without
changing the governed data-stack versions; the expected strict-gate result is
zero findings and exit code `0`.

The SBOM is generated in the same `docker-build` job from the same local image
reference as the Trivy scan. On `main`, that exact image is exported after the
blocking gate, transferred as an OCI archive, loaded without rebuilding, and
published only after its local and registry config digests match the scanned
image ID.

### Output contract

The workflow artifact contains:

- `trivy-results.sarif` and `trivy-results.json`;
- `trivy-base-results.json` for the exact pinned distro base digest;
- `reports/security/bioetl.spdx.json`;
- `trivy-alerts.csv` with
  `alert_number,CVE,package,installed,fixed,layer,status`;
- Trivy/GitHub metadata and runtime provenance files.
- `baseline.sha256`, covering every required baseline file.

These files are CI outputs, not tracked repository evidence. Closure claims
must cite the workflow URL, source SHA, image ID/digest, and artifact name.

## Verification

- Local `docker image inspect` for `bioetl:<sha>` returns an image ID.
- Strict Trivy gate (`--exit-code 1` on CRITICAL,HIGH,MEDIUM) exits `0`.
- Closure notes cite workflow URL, source SHA, image ID/digest, and artifact
  name `bioetl-security-baseline-<sha>`.
- On `main` publish path, local and registry config digests match the scanned
  image ID.

## Rollback/Recovery

Do not publish or retag an image whose config digest does not match the
scanned local image ID. Discard local `bioetl:<sha>` / `bioetl-builder:<sha>`
tags from a failed measurement and rebuild from the same commit. Do not unpin
the Wolfi base digest or direct package versions to force a green scan.

## Post-incident

Record the source SHA, image ID/digest, Trivy version, artifact name, workflow
URL, and operator. File follow-up only against the measured commit; do not
treat `reports/security/` outputs as tracked evidence.

## Compliance

Docker remains optional under ADR-010. This runbook documents command names and
artifact filenames only; it MUST NOT record secret values, `.env` contents, or
registry credentials. Generated evidence stays in gitignored `reports/security/`.
