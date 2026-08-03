#!/usr/bin/env python3
"""Validate GitHub Actions references against runtime policy allowlist."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = ROOT / ".github/workflows"
COMPOSITE_ACTIONS_DIR = ROOT / ".github/actions"

ALLOWED_USES: dict[str, set[str]] = {
    "actions/checkout": {"de0fac2e4500dabe0009e67214ff5f5447ce83dd"},  # v6.0.2
    "actions/setup-python": {"a309ff8b426b58ec0e2a45f0f869d46889d02405"},  # v6.2.0
    "actions/cache": {"27d5ce7f107fe9357f9df03efb73ab90386fccae"},  # v5.0.5
    "actions/cache/restore": {"27d5ce7f107fe9357f9df03efb73ab90386fccae"},
    "actions/cache/save": {"27d5ce7f107fe9357f9df03efb73ab90386fccae"},
    "actions/upload-artifact": {"043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"},  # v7.0.1
    "actions/setup-node": {"48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e"},  # v6.4.0
    "actions/download-artifact": {"3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"},  # v8.0.1
    "actions/github-script": {"f28e40c7f34bde8b3046d885e986cb6290c5673b"},  # v7
    "actions/labeler": {"8558fd74291d67161a8a78ce36a881fa63b766a9"},  # v5
    "actions/stale": {"5bef64f19d7facfb25b37b414482c7164d639639"},  # v9
    "astral-sh/setup-uv": {
        "37802adc94f370d6bfd71619e3f0bf239e1f3b78",  # v7
        "94527f2e458b27549849d47d273a16bec83a01e9",  # v7
        "cda7432b7ae1feb69168d44b610cb8e3cdbd09b0",  # v1
    },
    "SonarSource/sonarqube-scan-action": {
        "fd88b7d7ccbaefd23d8f36f73b59db7a3d246602",
    },
    "aquasecurity/trivy-action": {"57a97c7e7821a5776cebc9bb87c984fa69cba8f1"},
    "docker/build-push-action": {"ca052bb54ab0790a636c9b5f226502c73d547a25"},
    "docker/login-action": {"c94ce9fb468520275223c153574b00df6fe4bcc9"},
    "docker/setup-buildx-action": {"4d04d5d9486b7bd6fa91e7baf45bbb4f8b9deedd"},
    "github/codeql-action/upload-sarif": {
        "8dca8a82e2fa1a2c8908956f711300f9c4a4f4f6",
    },
    "hadolint/hadolint-action": {"2332a7b74a6de0dda2e2221d575162eba76ba5e5"},
    "pypa/gh-action-pypi-publish": {
        "cef221092ed1bacb1cc03d23a2d87d1d172e277b",
    },
    "softprops/action-gh-release": {"3bb12739c298aeb8a4eeaf626c5b8d85266b0e65"},
    "wagoid/commitlint-github-action": {
        "f133a0d95090ef2609192b4a21f54e20af819ea9",
    },
}

ALLOWED_DOCKER_IMAGES: dict[str, set[str]] = {
    "docker://codiumai/pr-agent": {
        "sha256:a5741a479f21d20a9bbeca7847a720f92ac6f427e8dc0920fefa039ecafd5e6f"
    },
}

USES_PATTERN = re.compile(r"^\s*uses:\s*([^\s#]+)")
FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
FULL_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


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


def _report_violations(violations: list[str]) -> int:
    if not violations:
        print("GitHub Actions runtime policy check passed.")
        return 0
    sys.stderr.write("GitHub Actions runtime policy violations found:\n")
    for violation in violations:
        sys.stderr.write(f"- {violation}\n")
    return 1


def main() -> int:
    return _report_violations(_collect_uses_violations())


if __name__ == "__main__":
    raise SystemExit(main())
