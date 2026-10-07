#!/usr/bin/env bash
# Publish only the same-workflow scanned image after the protected approval job.
set -euo pipefail
set +x
unset PYTHONOPTIMIZE
[[ "${CIRCLECI:-}" = true ]]
[[ "${CIRCLE_PROJECT_USERNAME:-}" = SatoryKono ]]
[[ "${CIRCLE_PROJECT_REPONAME:-}" = BioactivityDataAcquisition ]]
: "${CIRCLE_SHA1:?Missing source SHA}"
: "${CIRCLE_BRANCH:?Missing source branch}"
: "${CIRCLE_WORKFLOW_ID:?Missing workflow identity}"
: "${GHCR_USER:?Missing registry user}"
: "${GHCR_TOKEN:?Missing registry credential}"
[[ "$CIRCLE_BRANCH" = main ]]
[[ "$CIRCLE_SHA1" =~ ^[0-9a-f]{40}$ ]]
[[ "$(git rev-parse HEAD)" = "$CIRCLE_SHA1" ]]
repo_root="$(git rev-parse --show-toplevel)"
export PATH="$repo_root/.venv/bin:$PATH"
export PYTHONPATH="$repo_root/src:$repo_root"
artifact_root="${SCANNED_IMAGE_DIRECTORY:?Missing security workspace}"
cd "$artifact_root"
python3 - <<'MANIFEST'
import re
from pathlib import Path

required = {
    'bioetl-image-id.txt', 'bioetl-image-provenance.txt', 'bioetl-pip-freeze.txt',
    'bioetl.spdx.json', 'docker-build-metadata.json', 'github-trivy-alerts.json',
    'trivy-alerts.csv', 'trivy-base-results.json', 'trivy-fixability-audit.json',
    'trivy-results.json', 'trivy-results.sarif', 'trivy-version.json',
}
for manifest, names in [('baseline.sha256', required), ('scanned-image.sha256', {'bioetl-scanned-image.tar.zst'})]:
    lines = Path(manifest).read_text(encoding='utf-8').splitlines()
    entries = [re.fullmatch(r'([0-9a-f]{64})  ([a-zA-Z0-9_.-]+)', line) for line in lines]
    assert all(entries), 'Malformed checksum manifest'
    assert len(entries) == len(names) and {entry[2] for entry in entries} == names
    assert all(Path(name).is_file() and not Path(name).is_symlink() for name in names)
MANIFEST
sha256sum --check baseline.sha256
sha256sum --check scanned-image.sha256
python3 - <<'VERIFY'
import json, os, re
from pathlib import Path
metadata = json.loads(Path('docker-build-metadata.json').read_text(encoding='utf-8'))
assert metadata['producer'] == 'circleci'
assert metadata['source_sha'] == os.environ['CIRCLE_SHA1']
assert metadata['run_attempt'] == os.environ['CIRCLE_WORKFLOW_ID']
assert metadata['image_ref'] == 'bioetl:' + os.environ['CIRCLE_SHA1']
assert str(metadata['run_id']).isdigit()
assert re.fullmatch(r'sha256:[0-9a-f]{64}', metadata['image_id'])
assert Path('bioetl-image-id.txt').read_text(encoding='utf-8').strip() == metadata['image_id']
scan = json.loads(Path('trivy-results.json').read_text(encoding='utf-8'))
assert scan['Metadata']['ImageID'] == metadata['image_id'], 'Scan/image identity mismatch'
from scripts.engineering.qa.docker_stability_campaign.trivy_baseline import build_fixability_audit, is_strict_blocking_finding
audit = build_fixability_audit(scan)
assert not any(is_strict_blocking_finding(row) for row in audit['all_findings'])
VERIFY
check_current_main() {
  python3 - <<'CURRENT'
import json, os, urllib.request
url = 'https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/git/ref/heads/main'
request = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json'})
with urllib.request.urlopen(request, timeout=30) as response:
    current = json.load(response)['object']['sha']
if current != os.environ['CIRCLE_SHA1']:
    raise SystemExit('Publication rejected: source is no longer current main')
CURRENT
}
check_current_main
# Confirm the server-side approval and successful producer in this workflow.
# This public project exposes read-only workflow/job metadata without credentials.
# An HTTP/auth failure aborts publication; there is no approval-check fallback.
python3 - <<'APPROVAL'
import json, os, urllib.request
from pathlib import Path

url = 'https://circleci.com/api/v2/workflow/' + os.environ['CIRCLE_WORKFLOW_ID'] + '/job'
with urllib.request.urlopen(url, timeout=30) as response:
    payload = json.load(response)
assert not payload.get('next_page_token'), 'Unexpected workflow pagination'
jobs = payload['items']
approval = [job for job in jobs if job['name'] == 'docker-publish-approval']
assert len(approval) == 1 and approval[0]['status'] == 'success' and approval[0].get('approved_by')
metadata = json.loads(Path('docker-build-metadata.json').read_text(encoding='utf-8'))
producer = [job for job in jobs if job['name'] == 'docker-security-baseline']
assert len(producer) == 1 and producer[0]['status'] == 'success'
assert str(producer[0]['job_number']) == str(metadata['run_id'])
Path('approval.json').write_text(json.dumps({'workflow_id': os.environ['CIRCLE_WORKFLOW_ID'], 'approval_job_id': approval[0]['id'], 'approved_by': approval[0]['approved_by'], 'producer_job_number': producer[0]['job_number']}, sort_keys=True) + '\n', encoding='utf-8')
APPROVAL
# Use the job-injected Environment CLI, not the separately installed local CLI.
# Obtain the signing credential before any registry write; never print it.
SIGSTORE_ID_TOKEN="$(circleci run oidc get --claims '{"aud":"sigstore"}')"
[[ -n "$SIGSTORE_ID_TOKEN" ]]
export SIGSTORE_ID_TOKEN
zstd --decompress --stdout bioetl-scanned-image.tar.zst | docker load
image_ref="bioetl:${CIRCLE_SHA1}"
expected_id="$(cat bioetl-image-id.txt)"
[[ "$(docker image inspect "$image_ref" --format '{{.Id}}')" = "$expected_id" ]]
image_base='ghcr.io/satorykono/bioactivitydataacquisition'
sha_ref="$image_base:$CIRCLE_SHA1"
# Isolated config prevents credentials leaking into persisted security artifacts.
DOCKER_CONFIG="$(mktemp -d)"
export DOCKER_CONFIG
cleanup() { docker logout ghcr.io >/dev/null 2>&1 || true; rm -rf "$DOCKER_CONFIG"; }
trap cleanup EXIT
printf '%s' "$GHCR_TOKEN" | docker login ghcr.io --username "$GHCR_USER" --password-stdin
# A source-SHA tag is immutable: reject a different existing image.
if docker manifest inspect "$sha_ref" > existing-manifest.json 2> existing-manifest-error.log; then
  python3 - <<'EXISTING'
import json
from pathlib import Path
manifest = json.loads(Path('existing-manifest.json').read_text(encoding='utf-8'))
assert manifest['config']['digest'] == Path('bioetl-image-id.txt').read_text(encoding='utf-8').strip(), 'SHA tag already binds a different image'
EXISTING
else
  grep -Eq 'manifest unknown|no such manifest' existing-manifest-error.log
fi
docker tag "$image_ref" "$sha_ref"
docker push "$sha_ref" | tee image-sha-push.log
IMAGE_DIGEST="$(python3 - <<'DIGEST'
import re
from pathlib import Path
matches = re.findall(r'digest: (sha256:[0-9a-f]{64})', Path('image-sha-push.log').read_text(encoding='utf-8'))
assert len(matches) == 1, 'Expected one registry manifest digest'
print(matches[0])
DIGEST
)"
export IMAGE_DIGEST
docker manifest inspect "$image_base@$IMAGE_DIGEST" > published-manifest.json
python3 - <<'IMAGE'
import json
from pathlib import Path
manifest = json.loads(Path('published-manifest.json').read_text(encoding='utf-8'))
assert manifest['config']['digest'] == Path('bioetl-image-id.txt').read_text(encoding='utf-8').strip()
IMAGE
# Cosign is checksum-pinned in job setup; the Environment CLI is supplied by CircleCI.
export CIRCLE_ORGANIZATION_ID="${CIRCLE_ORGANIZATION_ID:?Missing OIDC issuer identity}"
export CIRCLE_PROJECT_ID="${CIRCLE_PROJECT_ID:?Missing OIDC project identity}"
export PIPELINE_DEFINITION_ID="${PIPELINE_DEFINITION_ID:?Missing OIDC pipeline identity}"
python3 - <<'PROVENANCE'
import json, os
from pathlib import Path
metadata = json.loads(Path('docker-build-metadata.json').read_text(encoding='utf-8'))
predicate = {
    'buildDefinition': {
        'buildType': 'https://github.com/SatoryKono/BioactivityDataAcquisition/blob/' + os.environ['CIRCLE_SHA1'] + '/.circleci/config.yml',
        'externalParameters': {'source': 'https://github.com/SatoryKono/BioactivityDataAcquisition', 'revision': os.environ['CIRCLE_SHA1'], 'dockerfile': 'Dockerfile.bioetl'},
        'internalParameters': {},
        'resolvedDependencies': [{'uri': 'git+https://github.com/SatoryKono/BioactivityDataAcquisition', 'digest': {'gitCommit': os.environ['CIRCLE_SHA1']}}],
    },
    'runDetails': {
        'builder': {'id': 'https://circleci.com/api/v2/projects/' + os.environ['CIRCLE_PROJECT_ID'] + '/pipeline-definitions/' + os.environ['PIPELINE_DEFINITION_ID']},
        'metadata': {'invocationId': 'https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/' + metadata['run_id']},
    },
}
Path('provenance.json').write_text(json.dumps(predicate, sort_keys=True) + '\n', encoding='utf-8')
PROVENANCE
cosign attest --yes --use-signing-config=false --oidc-issuer "https://oidc.circleci.com/org/$CIRCLE_ORGANIZATION_ID" --type slsaprovenance1 --predicate provenance.json "$image_base@$IMAGE_DIGEST"
cosign attest --yes --use-signing-config=false --oidc-issuer "https://oidc.circleci.com/org/$CIRCLE_ORGANIZATION_ID" --type spdxjson --predicate bioetl.spdx.json "$image_base@$IMAGE_DIGEST"
unset SIGSTORE_ID_TOKEN
identity="https://circleci.com/api/v2/projects/$CIRCLE_PROJECT_ID/pipeline-definitions/$PIPELINE_DEFINITION_ID"
issuer="https://oidc.circleci.com/org/$CIRCLE_ORGANIZATION_ID"
cosign verify-attestation --certificate-identity "$identity" --certificate-oidc-issuer "$issuer" --type slsaprovenance1 "$image_base@$IMAGE_DIGEST" > provenance-verification.json
cosign verify-attestation --certificate-identity "$identity" --certificate-oidc-issuer "$issuer" --type spdxjson "$image_base@$IMAGE_DIGEST" > sbom-verification.json
python3 - <<'CLAIMS'
import base64, json, os
from pathlib import Path

def envelopes(path):
    remaining = Path(path).read_text(encoding='utf-8').strip()
    decoder = json.JSONDecoder()
    while remaining:
        value, end = decoder.raw_decode(remaining)
        yield from value if isinstance(value, list) else [value]
        remaining = remaining[end:].strip()

for verified, predicate_file in [('provenance-verification.json', 'provenance.json'), ('sbom-verification.json', 'bioetl.spdx.json')]:
    expected = json.loads(Path(predicate_file).read_text(encoding='utf-8'))
    matched = False
    for envelope in envelopes(verified):
        statement = json.loads(base64.b64decode(envelope['payload'], validate=True))
        bound = any(subject.get('digest', {}).get('sha256') == os.environ['IMAGE_DIGEST'].removeprefix('sha256:') for subject in statement.get('subject', []))
        matched |= bound and statement.get('predicate') == expected
    assert matched, 'No verified attestation binds the expected predicate and image digest'
CLAIMS
# Promote the mutable main tag only after security, approval and attestation.
check_current_main
docker tag "$image_ref" "$image_base:main"
docker push "$image_base:main" | tee image-main-push.log
python3 - <<'FINAL'
import json, os, re
from pathlib import Path
matches = re.findall(r'digest: (sha256:[0-9a-f]{64})', Path('image-main-push.log').read_text(encoding='utf-8'))
assert matches == [os.environ['IMAGE_DIGEST']]
Path('publication.json').write_text(json.dumps({'source_sha': os.environ['CIRCLE_SHA1'], 'image_digest': os.environ['IMAGE_DIGEST'], 'workflow_id': os.environ['CIRCLE_WORKFLOW_ID'], 'provenance_verified': True, 'sbom_verified': True}, sort_keys=True) + '\n', encoding='utf-8')
FINAL
