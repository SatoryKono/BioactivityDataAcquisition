# Docker security baseline

Use this runbook to reproduce the RF-001 image baseline without changing the
runtime image. Generated files stay under `reports/security/`, are ignored by
Git, and are attached by `docker.yml` as the bounded
`bioetl-security-baseline-<sha>` workflow artifact.

## Identity

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

The Dockerfile pins both stages to the same immutable Python image digest. Do
not substitute a mutable tag when collecting closure evidence.

## Runtime versions

```powershell
docker run --rm --entrypoint python "bioetl:$baselineSha" --version
docker run --rm --entrypoint python "bioetl:$baselineSha" -c `
  'import importlib.util; print("pip=" + ("absent" if importlib.util.find_spec("pip") is None else "present"))'
docker run --rm --entrypoint uv "bioetl-builder:$baselineSha" `
  pip freeze --python /app/.venv/bin/python
```

The CI artifact additionally records the final image ID, source SHA, runtime
Python version, runtime `pip` presence, installed packages, Trivy version/DB metadata, and the
GitHub Trivy alert snapshot used to populate `alert_number` where an existing
alert identity is available. The current least-privilege runtime image has no
`pip` module; package inventory is read through `importlib.metadata` instead.

## Trivy reproduction

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
last command is the enforcement boundary and must remain blocking. RF-001 may
therefore expose a known red gate; RF-002 owns removal of those findings.

The SBOM is generated in the same `docker-build` job from the same local image
reference as the Trivy scan. On `main`, that exact image is exported after the
blocking gate, transferred as an OCI archive, loaded without rebuilding, and
published only after its local and registry config digests match the scanned
image ID.

## Output contract

The workflow artifact contains:

- `trivy-results.sarif` and `trivy-results.json`;
- `trivy-base-results.json` for the exact pinned Debian base digest;
- `bioetl.spdx.json`;
- `trivy-alerts.csv` with
  `alert_number,CVE,package,installed,fixed,layer,status`;
- Trivy/GitHub metadata and runtime provenance files.
- `baseline.sha256`, covering every required baseline file.

These files are CI outputs, not tracked repository evidence. Closure claims
must cite the workflow URL, source SHA, image ID/digest, and artifact name.
