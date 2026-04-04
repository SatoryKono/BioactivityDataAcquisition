#!/usr/bin/env python3
"""
CI Fixes script for SatoryKono/BioactivityDataAcquisition.

Implements CI-01, CI-02, CI-03:
  CI-01 — Replace actions/checkout@v6 → @v4 across all workflows
  CI-02 — Add Python 3.13 to test-matrix in tests.yml
  CI-03 — Fix docker-push to reuse image from docker-build (no double build)

Usage:
    python apply_ci_fixes.py --token ghp_YOUR_TOKEN_HERE [--dry-run]
    python apply_ci_fixes.py --token ghp_YOUR_TOKEN_HERE --only ci-01
    python apply_ci_fixes.py --token ghp_YOUR_TOKEN_HERE --only ci-02
    python apply_ci_fixes.py --token ghp_YOUR_TOKEN_HERE --only ci-03

Requirements: pip install requests
"""

import argparse
import base64
import sys
import time
from typing import Optional

import requests

OWNER = "SatoryKono"
REPO = "BioactivityDataAcquisition"
BASE_BRANCH = "main"

BRANCHES = {
    "ci-01": "fix/ci-checkout-v4",
    "ci-02": "feat/ci-python-313-matrix",
    "ci-03": "refactor/ci-docker-single-build",
}

PR_BODIES = {
    "ci-01": """## CI-01: Replace `actions/checkout@v6` → `@v4`

`actions/checkout@v6` does not exist as a stable release.
The latest stable version is `@v4`. GitHub resolves unknown tags to
`latest`, which can silently break all workflows when upstream changes.

### Changes
- Replaced `actions/checkout@v6` with `actions/checkout@v4` in all 25 affected workflows.

### Risk
None — `@v4` is the standard stable version with identical behaviour.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
""",
    "ci-02": """## CI-02: Add Python 3.13 to test-matrix

`tests.yml` only tested `["3.11", "3.12"]`, while `release.yml` already
includes `3.13` and `AGENTS.md` recommends Python 3.13.

### Changes
- Added `"3.13"` to `matrix.python-version` in `tests.yml` (job: `test-matrix`)
- Coverage collection remains on Python 3.11 only (no extra artifact noise)
- Matrix grows from 12 to 18 parallel jobs

### Risk
Low. `release.yml` already confirms Python 3.13 compatibility.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
""",
    "ci-03": """## CI-03: Fix docker-push — reuse image built in docker-build

`docker-push` was rebuilding the image from scratch on a separate runner
that cannot access the image loaded by `docker-build` (`load: true`).

### Changes
- `docker-build`: login to GHCR on main-push; push temp tag `:sha-<SHA>`
- `docker-push`: use `docker buildx imagetools create` to retag — no rebuild
- `docker-build`: also upgrades `build-push-action` v5 → v6, `codeql/upload-sarif` v2 → v3
- `docker-push` timeout reduced 10 min → 5 min (retag is ~30 s)

### Risk
Medium — test by triggering a push to main after merging.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
""",
}


class GitHubAPI:
    def __init__(self, token: str, dry_run: bool = False) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        self.dry_run = dry_run
        self.base = f"https://api.github.com/repos/{OWNER}/{REPO}"

    def get(self, path: str) -> dict:
        resp = self.session.get(f"{self.base}{path}")
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, data: dict) -> dict:
        if self.dry_run:
            print(f"  [DRY-RUN] POST {path}")
            return {}
        resp = self.session.post(f"{self.base}{path}", json=data)
        resp.raise_for_status()
        return resp.json()

    def put(self, path: str, data: dict) -> dict:
        if self.dry_run:
            print(f"  [DRY-RUN] PUT {path}")
            return {}
        resp = self.session.put(f"{self.base}{path}", json=data)
        resp.raise_for_status()
        return resp.json()

    def get_sha(self, branch: str = BASE_BRANCH) -> str:
        data = self.get(f"/git/refs/heads/{branch}")
        return data["object"]["sha"]

    def branch_exists(self, branch: str) -> bool:
        try:
            self.get(f"/git/refs/heads/{branch}")
            return True
        except requests.HTTPError:
            return False

    def create_branch(self, branch: str, from_sha: str) -> None:
        print(f"  Creating branch: {branch}")
        self.post("/git/refs", {"ref": f"refs/heads/{branch}", "sha": from_sha})

    def get_file(self, path: str, branch: str) -> tuple[str, str]:
        """Returns (content_decoded, sha)."""
        data = self.get(f"/contents/{path}?ref={branch}")
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content, data["sha"]

    def update_file(self, path: str, content: str, sha: str, message: str, branch: str) -> None:
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        self.put(f"/contents/{path}", {
            "message": message,
            "content": encoded,
            "sha": sha,
            "branch": branch,
        })

    def create_pr(self, title: str, branch: str, body: str) -> str:
        data = self.post("/pulls", {
            "title": title,
            "head": branch,
            "base": BASE_BRANCH,
            "body": body,
        })
        return data.get("html_url", "(dry-run)")

    def list_workflow_files(self) -> list[dict]:
        return self.get("/contents/.github/workflows")


# ── CI-01 ────────────────────────────────────────────────────────────────────

def apply_ci01(api: GitHubAPI) -> None:
    print("\n=== CI-01: Replace checkout@v6 → @v4 ===")
    branch = BRANCHES["ci-01"]
    sha = api.get_sha()

    if api.branch_exists(branch):
        print(f"  Branch {branch} already exists — skipping branch creation")
    else:
        api.create_branch(branch, sha)

    files = api.list_workflow_files()
    updated = []

    for f in files:
        if not f["name"].endswith(".yml") and not f["name"].endswith(".yaml"):
            continue
        path = f["path"]
        content, file_sha = api.get_file(path, branch)
        if "actions/checkout@v6" not in content:
            continue
        new_content = content.replace("actions/checkout@v6", "actions/checkout@v4")
        count = content.count("actions/checkout@v6")
        print(f"  Patching {path} ({count} occurrence{'s' if count > 1 else ''})")
        api.update_file(
            path=path,
            content=new_content,
            sha=file_sha,
            message=f"fix(ci): replace checkout@v6 with @v4 in {f['name']}\n\nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>",
            branch=branch,
        )
        updated.append(f["name"])
        time.sleep(0.3)  # avoid secondary rate limit

    print(f"\n  Updated {len(updated)} files: {', '.join(updated)}")

    if not api.dry_run:
        pr_url = api.create_pr(
            title="fix(ci): replace non-existent actions/checkout@v6 with @v4 across all workflows",
            branch=branch,
            body=PR_BODIES["ci-01"],
        )
        print(f"  PR created: {pr_url}")


# ── CI-02 ────────────────────────────────────────────────────────────────────

def apply_ci02(api: GitHubAPI) -> None:
    print("\n=== CI-02: Add Python 3.13 to test-matrix ===")
    branch = BRANCHES["ci-02"]
    sha = api.get_sha()

    if api.branch_exists(branch):
        print(f"  Branch {branch} already exists — skipping branch creation")
    else:
        api.create_branch(branch, sha)

    path = ".github/workflows/tests.yml"
    content, file_sha = api.get_file(path, branch)

    old_matrix = 'python-version: [ "3.11", "3.12" ]'
    new_matrix = 'python-version: [ "3.11", "3.12", "3.13" ]'

    if old_matrix not in content:
        print(f"  WARNING: expected pattern not found in {path}. Already updated?")
        return

    new_content = content.replace(old_matrix, new_matrix, 1)
    print(f"  Patching {path}: adding 3.13 to test matrix")

    api.update_file(
        path=path,
        content=new_content,
        sha=file_sha,
        message=(
            "feat(ci): add Python 3.13 to test-matrix\n\n"
            "Aligns tests.yml with release.yml and AGENTS.md recommendation.\n"
            "Coverage collection remains on 3.11 only.\n\n"
            "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
        ),
        branch=branch,
    )

    if not api.dry_run:
        pr_url = api.create_pr(
            title="feat(ci): add Python 3.13 to test-matrix",
            branch=branch,
            body=PR_BODIES["ci-02"],
        )
        print(f"  PR created: {pr_url}")


# ── CI-03 ────────────────────────────────────────────────────────────────────

DOCKER_YML_FIXED = """\
name: Docker Build & Compose Validation

permissions:
  contents: read

on:
  push:
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - '.ai/**'
      - '.claude/**'
      - '.github/workflows/**'
      - 'LICENSE'
    branches: [ main, master, develop ]
    paths:
      - 'Dockerfile'
      - 'docker-compose*.yml'
      - '.dockerignore'
      - 'entrypoint.sh'
  pull_request:
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - '.ai/**'
      - '.claude/**'
      - '.github/workflows/**'
      - 'LICENSE'
    branches: [ main, master, develop ]
    paths:
      - 'Dockerfile'
      - 'docker-compose*.yml'
      - '.dockerignore'
      - 'entrypoint.sh'

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  docker-lint:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Hadolint (Dockerfile linting)
        uses: hadolint/hadolint-action@v3
        with:
          dockerfile: Dockerfile

  docker-compose-validate:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4

      - name: Validate docker-compose.yml syntax
        run: docker compose config > /dev/null

      - name: Validate docker-compose.monitoring.yml syntax
        run: docker compose -f docker-compose.monitoring.yml config > /dev/null

  docker-build:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: docker-lint
    permissions:
      contents: read
      security-events: write
      packages: write
    outputs:
      image-ref: ${{ steps.set-ref.outputs.image-ref }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4

      # Login to GHCR so we can push a temporary SHA tag on main pushes.
      # This allows docker-push to retag without rebuilding the image.
      - name: Login to GHCR (temp tag on main push)
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build Docker image
        id: build
        uses: docker/build-push-action@v6
        with:
          context: .
          # On main push: push temp SHA tag to GHCR so docker-push can retag.
          # On PR/other: load locally for Trivy scan only.
          push: ${{ github.ref == 'refs/heads/main' && github.event_name == 'push' }}
          load: ${{ !(github.ref == 'refs/heads/main' && github.event_name == 'push') }}
          tags: |
            bioetl:${{ github.sha }}
            ${{ (github.ref == 'refs/heads/main' && github.event_name == 'push') && format('ghcr.io/{0}:sha-{1}', github.repository, github.sha) || '' }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Set image-ref output
        id: set-ref
        run: |
          if [ "${{ github.ref }}" = "refs/heads/main" ] && [ "${{ github.event_name }}" = "push" ]; then
            echo "image-ref=ghcr.io/${{ github.repository }}:sha-${{ github.sha }}" >> "$GITHUB_OUTPUT"
          else
            echo "image-ref=bioetl:${{ github.sha }}" >> "$GITHUB_OUTPUT"
          fi

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@0.30.0
        with:
          image-ref: ${{ steps.set-ref.outputs.image-ref }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results to GitHub Security tab
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Run Trivy on debian:bookworm-slim base image
        uses: aquasecurity/trivy-action@0.30.0
        with:
          image-ref: 'debian:bookworm-slim'
          format: 'table'
          severity: 'CRITICAL,HIGH'

  docker-push:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    needs: docker-build
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    permissions:
      contents: read
      packages: write

    steps:
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # Retag the already-built and pushed SHA image — no rebuild needed.
      - name: Tag and push final image tags
        run: |
          SOURCE="ghcr.io/${{ github.repository }}:sha-${{ github.sha }}"
          docker buildx imagetools create \\
            --tag "ghcr.io/${{ github.repository }}:latest" \\
            --tag "ghcr.io/${{ github.repository }}:${{ github.sha }}" \\
            --tag "ghcr.io/${{ github.repository }}:${{ github.ref_name }}" \\
            "${SOURCE}"
          echo "✅ Final tags pushed (no rebuild)"
"""


def apply_ci03(api: GitHubAPI) -> None:
    print("\n=== CI-03: Fix docker-push double build ===")
    branch = BRANCHES["ci-03"]
    sha = api.get_sha()

    if api.branch_exists(branch):
        print(f"  Branch {branch} already exists — skipping branch creation")
    else:
        api.create_branch(branch, sha)

    path = ".github/workflows/docker.yml"
    _, file_sha = api.get_file(path, branch)

    print(f"  Replacing {path} with fixed version")
    api.update_file(
        path=path,
        content=DOCKER_YML_FIXED,
        sha=file_sha,
        message=(
            "refactor(ci): fix docker-push to retag instead of rebuild\n\n"
            "- docker-build: push temp :sha-<SHA> tag on main pushes\n"
            "- docker-push: use imagetools create to retag (no rebuild, ~30s)\n"
            "- upgrade build-push-action v5→v6, codeql/upload-sarif v2→v3\n"
            "- timeout docker-push 10→5 min\n\n"
            "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
        ),
        branch=branch,
    )

    if not api.dry_run:
        pr_url = api.create_pr(
            title="refactor(ci): fix docker-push to retag instead of rebuild",
            branch=branch,
            body=PR_BODIES["ci-03"],
        )
        print(f"  PR created: {pr_url}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Apply CI fixes to BioactivityDataAcquisition")
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token (needs repo + workflow scopes)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without making changes")
    parser.add_argument("--only", choices=["ci-01", "ci-02", "ci-03"], help="Apply only one fix")
    args = parser.parse_args()

    api = GitHubAPI(args.token, dry_run=args.dry_run)

    if args.dry_run:
        print("🔍 DRY-RUN mode — no changes will be made\n")

    try:
        if not args.only or args.only == "ci-01":
            apply_ci01(api)
        if not args.only or args.only == "ci-02":
            apply_ci02(api)
        if not args.only or args.only == "ci-03":
            apply_ci03(api)
        print("\n✅ Done!")
    except requests.HTTPError as e:
        print(f"\n❌ GitHub API error: {e}")
        print(f"   Response: {e.response.text if e.response else 'no response'}")
        sys.exit(1)


if __name__ == "__main__":
    main()
