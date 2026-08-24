#!/usr/bin/env python3
"""Validate GitHub Actions references against runtime policy allowlist."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = ROOT / ".github/workflows"
COMPOSITE_ACTIONS_DIR = ROOT / ".github/actions"
REMOTE_ARTIFACTS_FILE = ROOT / "configs/quality/github_actions_remote_artifacts.yaml"

ALLOWED_USES: dict[str, set[str]] = {
    "actions/checkout": {
        "de0fac2e4500dabe0009e67214ff5f5447ce83dd",  # v6.0.2
        "3d3c42e5aac5ba805825da76410c181273ba90b1",  # v7.0.1
    },
    "actions/setup-python": {
        "a309ff8b426b58ec0e2a45f0f869d46889d02405",  # v6.2.0
        "5fda3b95a4ea91299a34e894583c3862153e4b97",  # v7.0.0
    },
    "actions/cache": {"27d5ce7f107fe9357f9df03efb73ab90386fccae"},  # v5.0.5
    "actions/cache/restore": {"27d5ce7f107fe9357f9df03efb73ab90386fccae"},
    "actions/cache/save": {"27d5ce7f107fe9357f9df03efb73ab90386fccae"},
    "actions/upload-artifact": {"043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"},  # v7.0.1
    "actions/setup-node": {
        "48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e",  # v6.4.0
        "249970729cb0ef3589644e2896645e5dc5ba9c38",  # v6.5.0
    },
    "actions/download-artifact": {"3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"},  # v8.0.1
    "actions/github-script": {"f28e40c7f34bde8b3046d885e986cb6290c5673b"},  # v7
    "actions/labeler": {"8558fd74291d67161a8a78ce36a881fa63b766a9"},  # v5
    "actions/stale": {"5bef64f19d7facfb25b37b414482c7164d639639"},  # v9
    "actions/dependency-review-action": {
        "a1d282b36b6f3519aa1f3fc636f609c47dddb294",  # v5.0.0
    },
    "astral-sh/setup-uv": {
        "37802adc94f370d6bfd71619e3f0bf239e1f3b78",  # v7 (canonical; composite setup-python-uv)
        "20cfd1bf945f4377ade1205e4dbc17946fc9a30d",  # v10.0.1
    },
    "SonarSource/sonarqube-scan-action": {
        "fd88b7d7ccbaefd23d8f36f73b59db7a3d246602",
    },
    "anchore/sbom-action": {
        "e22c389904149dbc22b58101806040fa8d37a610",  # v0.24.0
    },
    "aquasecurity/trivy-action": {
        "57a97c7e7821a5776cebc9bb87c984fa69cba8f1",  # v0.35.0
        "ed142fd0673e97e23eac54620cfb913e5ce36c25",  # v0.36.0
    },
    "docker/build-push-action": {"ca052bb54ab0790a636c9b5f226502c73d547a25"},
    "docker/login-action": {"dbcb813823bdd20940b903addbd779551569679f"},
    "docker/setup-buildx-action": {"bb05f3f5519dd87d3ba754cc423b652a5edd6d2c"},
    "gitleaks/gitleaks-action": {
        "e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e",  # v3.0.0
    },
    "github/codeql-action/init": {
        "db488ddef3bf6cb639b32c2e9a7c0a7ea8271d28",  # v4.37.8
    },
    "github/codeql-action/analyze": {
        "db488ddef3bf6cb639b32c2e9a7c0a7ea8271d28",  # v4.37.8
    },
    "github/codeql-action/upload-sarif": {
        "8dca8a82e2fa1a2c8908956f711300f9c4a4f4f6",  # v2 (docker.yml Trivy)
        "db488ddef3bf6cb639b32c2e9a7c0a7ea8271d28",  # v4.37.8
    },
    "google/osv-scanner-action/osv-scanner-action": {
        "6e4298ebc4db23e847df9b2e2de2939d6f066c67",  # v2.5.1
    },
    "hadolint/hadolint-action": {"2a66e89f53d0771bb131a7fa31f3136336094aa6"},
    "ossf/scorecard-action": {
        "2d1146689b8cda280b9bc96326124645441f03bc",  # v2.4.4
    },
    "pypa/gh-action-pypi-publish": {
        "dc37677b2e1c63e2034f94d8a5b11f265b73ba33",
    },
    "softprops/action-gh-release": {"3d0d9888cb7fd7b750713d6e236d1fcb99157228"},
    "wagoid/commitlint-github-action": {
        "f133a0d95090ef2609192b4a21f54e20af819ea9",
    },
    "zizmorcore/zizmor-action": {
        "3dc1ecc9bcb9e94e9b2c709687979e1298497054",  # v0.6.2
    },
}

ALLOWED_DOCKER_IMAGES: dict[str, set[str]] = {
    "docker://codiumai/pr-agent": {
        "sha256:a5741a479f21d20a9bbeca7847a720f92ac6f427e8dc0920fefa039ecafd5e6f"
    },
}

USES_PATTERN = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")
FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
FULL_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PIPE_TO_SHELL_PATTERN = re.compile(
    r"(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba)?sh\b",
    re.IGNORECASE,
)
REMOTE_SCRIPT_URL_PATTERN = re.compile(
    r"https?://[^\s\"']+\.(?:sh|ps1)\b",
    re.IGNORECASE,
)


def iter_yaml_files() -> list[Path]:
    return [
        *sorted(WORKFLOWS_DIR.glob("*.yml")),
        *sorted(WORKFLOWS_DIR.glob("*.yaml")),
        *sorted(COMPOSITE_ACTIONS_DIR.rglob("action.yml")),
        *sorted(COMPOSITE_ACTIONS_DIR.rglob("action.yaml")),
    ]


def _parsed_uses_reference(line: str) -> tuple[str, str] | None:
    match = USES_PATTERN.match(line)
    if match is None:
        return None
    uses_ref = match.group(1)
    if uses_ref.startswith(("./", "../")):
        return None
    return uses_ref, uses_ref.partition("@")[0]


def _validate_allowed_uses_ref(uses_ref: str, action: str) -> str | None:
    if "@" not in uses_ref:
        return f"external action {uses_ref} must include an immutable ref"
    _, _, ref = uses_ref.partition("@")
    if action.startswith("docker://"):
        if not FULL_SHA256_DIGEST_PATTERN.fullmatch(ref):
            return f"Docker image {uses_ref} must be pinned by full sha256 digest"
        allowed_refs = ALLOWED_DOCKER_IMAGES.get(action)
        if allowed_refs is None:
            return f"unrecognized Docker image {action}; add an approved digest"
        if ref in allowed_refs:
            return None
        return f"disallowed {uses_ref}; expected one of {sorted(allowed_refs)}"
    if not FULL_SHA_PATTERN.fullmatch(ref):
        return f"external action {uses_ref} must be pinned by full 40-character SHA"
    allowed_refs = ALLOWED_USES.get(action)
    if allowed_refs is None:
        return f"unrecognized external action {action}; add an approved SHA to ALLOWED_USES"
    if ref in allowed_refs:
        return None
    return f"disallowed {uses_ref}; expected one of {sorted(allowed_refs)}"


def _uses_violations_in_file(file_path: Path) -> list[str]:
    violations: list[str] = []
    rel_path = file_path.relative_to(ROOT)
    for line_no, line in enumerate(
        file_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        parsed = _parsed_uses_reference(line)
        if parsed is None:
            continue
        uses_ref, action = parsed
        violation = _validate_allowed_uses_ref(uses_ref, action)
        if violation is None:
            continue
        violations.append(f"{rel_path}:{line_no}: {violation}")
    return violations


def _collect_uses_violations() -> list[str]:
    violations: list[str] = []
    for file_path in iter_yaml_files():
        violations.extend(_uses_violations_in_file(file_path))
    return violations


def load_remote_artifacts_policy(path: Path | None = None) -> dict[str, Any]:
    """Load repository-controlled remote executable pins."""
    policy_path = path or REMOTE_ARTIFACTS_FILE
    payload = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise RuntimeError(f"Remote artifacts policy must be a mapping: {policy_path}")
    return payload


def _allowed_remote_artifacts(
    policy: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    payload = policy if policy is not None else load_remote_artifacts_policy()
    raw_artifacts = payload.get("artifacts", [])
    if not isinstance(raw_artifacts, list):
        raise RuntimeError("github_actions_remote_artifacts.artifacts must be a list")
    artifacts: list[dict[str, str]] = []
    for entry in raw_artifacts:
        if not isinstance(entry, dict):
            raise RuntimeError("remote artifact entries must be mappings")
        url = entry.get("url")
        digest = entry.get("sha256")
        if not isinstance(url, str) or not url:
            raise RuntimeError("remote artifact url must be a non-empty string")
        if not isinstance(digest, str) or not SHA256_HEX_PATTERN.fullmatch(digest):
            raise RuntimeError(f"remote artifact sha256 must be 64 hex chars: {url}")
        artifacts.append({"url": url, "sha256": digest.lower()})
    return artifacts


def _forbidden_url_substrings(policy: dict[str, Any] | None = None) -> tuple[str, ...]:
    payload = policy if policy is not None else load_remote_artifacts_policy()
    raw = payload.get("forbidden_url_substrings", [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise RuntimeError(
            "github_actions_remote_artifacts.forbidden_url_substrings must be a list of strings"
        )
    return tuple(raw)


def remote_download_violations_in_text(
    text: str,
    *,
    rel_path: str,
    policy: dict[str, Any] | None = None,
) -> list[str]:
    """Return integrity violations for remote executable downloads in a workflow."""
    payload = policy if policy is not None else load_remote_artifacts_policy()
    violations: list[str] = []
    lowered = text.lower()
    for needle in _forbidden_url_substrings(payload):
        if needle.lower() in lowered:
            violations.append(
                f"{rel_path}: forbidden mutable installer URL substring {needle!r}"
            )
    if PIPE_TO_SHELL_PATTERN.search(text):
        violations.append(
            f"{rel_path}: pipe-to-shell remote download is forbidden; pin and checksum the artifact"
        )
    allowed = _allowed_remote_artifacts(payload)
    allowed_urls = {item["url"] for item in allowed}
    for match in REMOTE_SCRIPT_URL_PATTERN.finditer(text):
        url = match.group(0)
        if url not in allowed_urls:
            violations.append(
                f"{rel_path}: unpinned remote script download {url}; add integrity metadata"
            )
    for artifact in allowed:
        if artifact["url"] not in text:
            continue
        if artifact["sha256"] not in lowered:
            violations.append(
                f"{rel_path}: remote artifact {artifact['url']} is missing pinned sha256 "
                f"{artifact['sha256']}"
            )
    return violations


def _collect_remote_download_violations() -> list[str]:
    policy = load_remote_artifacts_policy()
    violations: list[str] = []
    for file_path in iter_yaml_files():
        rel_path = file_path.relative_to(ROOT).as_posix()
        text = file_path.read_text(encoding="utf-8")
        violations.extend(
            remote_download_violations_in_text(text, rel_path=rel_path, policy=policy)
        )
    return violations


def _report_violations(violations: list[str]) -> int:
    if not violations:
        print("GitHub Actions runtime policy check passed.")
        return 0
    sys.stderr.write("GitHub Actions runtime policy violations found:\n")
    for violation in violations:
        sys.stderr.write(f"- {violation}\n")
    return 1


def main() -> int:
    return _report_violations(
        [*_collect_uses_violations(), *_collect_remote_download_violations()]
    )


if __name__ == "__main__":
    raise SystemExit(main())
