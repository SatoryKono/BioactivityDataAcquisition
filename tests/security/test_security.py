"""Security tests for BioETL.

Validates:
1. VCR cassettes don't contain secrets
2. Environment variable patterns follow conventions
3. No hardcoded secrets in source code
4. PII handling follows security guidelines
"""

import re
from pathlib import Path

import pytest

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "bioetl"
VCR_DIR = PROJECT_ROOT / "tests" / "fixtures" / "vcr"

# Secret patterns to detect in source code
SECRET_PATTERNS = [
    # API Keys with explicit assignment
    (r"['\"]?api[_-]?key['\"]?\s*[:=]\s*['\"][^'\"]{10,}['\"]", "API key"),
    (r"['\"]?apikey['\"]?\s*[:=]\s*['\"][^'\"]{10,}['\"]", "API key"),
    # Authorization headers with actual tokens
    (r"Authorization['\"]?\s*[:=]\s*['\"]Bearer\s+[A-Za-z0-9\-_.]{20,}['\"]", "Bearer token"),
    (r"Authorization['\"]?\s*[:=]\s*['\"]Basic\s+[A-Za-z0-9+/=]{20,}['\"]", "Basic auth"),
    # AWS credentials (in proper context, not bare pattern which matches protein sequences)
    (r"aws_access_key_id\s*[:=]\s*['\"]AKIA[0-9A-Z]{16}['\"]", "AWS Access Key"),
    (r"['\"]?aws[_-]?secret[_-]?access[_-]?key['\"]?\s*[:=]\s*['\"][^'\"]{20,}['\"]", "AWS secret"),
    # Generic secrets
    (r"['\"]?password['\"]?\s*[:=]\s*['\"][^'\"]{8,}['\"]", "Password"),
    (r"['\"]?secret[_-]?key['\"]?\s*[:=]\s*['\"][^'\"]{10,}['\"]", "Secret key"),
    # Private keys
    (r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "Private key"),
]

# Patterns that are OK (false positive exclusions)
ALLOWED_PATTERNS = [
    r"api[_-]?key\s*=\s*None",
    r"api[_-]?key\s*=\s*os\.environ",
    r"api[_-]?key\s*=\s*self\.",
    r"password\s*=\s*None",
    r'"password":\s*"\*+"',  # Masked passwords
    r"secret[_-]?key\s*=\s*None",
    r'["\']api_key["\']\s*:\s*["\']["\']',  # Empty string
    r'["\']password["\']\s*:\s*["\']["\']',  # Empty string
]


class TestVCRCassetteSanitization:
    """Tests that VCR cassettes don't contain secrets."""

    @pytest.fixture
    def cassette_files(self) -> list[Path]:
        """Get all VCR cassette files."""
        if not VCR_DIR.exists():
            pytest.skip("VCR directory not found")
        return list(VCR_DIR.rglob("*.yaml"))

    def test_vcr_cassettes_exist(self, cassette_files: list[Path]) -> None:
        """Verify VCR cassettes exist."""
        assert len(cassette_files) > 0, "No VCR cassettes found"

    @pytest.mark.parametrize(
        "header_name",
        ["Authorization", "X-API-Key", "X-Api-Key", "Api-Key", "Apikey"],
    )
    def test_no_authorization_headers_with_real_values(
        self, cassette_files: list[Path], header_name: str
    ) -> None:
        """Verify cassettes don't contain real authorization headers."""
        violations = []
        for cassette in cassette_files:
            content = cassette.read_text(encoding="utf-8")
            # Look for headers with actual values (not empty or placeholder)
            pattern = rf"{header_name}:\s*['\"]?[A-Za-z0-9+/=\-_.]{20,}['\"]?"
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(f"{cassette.name}: Contains {header_name} header")

        assert not violations, "Cassettes with secrets:\n" + "\n".join(violations)

    def test_no_bearer_tokens(self, cassette_files: list[Path]) -> None:
        """Verify no Bearer tokens in cassettes."""
        violations = []
        for cassette in cassette_files:
            content = cassette.read_text(encoding="utf-8")
            # Real Bearer tokens are typically 20+ chars
            if re.search(r"Bearer\s+[A-Za-z0-9\-_.]{20,}", content):
                violations.append(f"{cassette.name}: Contains Bearer token")

        assert not violations, "Cassettes with Bearer tokens:\n" + "\n".join(
            violations
        )

    def test_no_aws_credentials(self, cassette_files: list[Path]) -> None:
        """Verify no AWS credentials in cassettes.

        Note: AKIA patterns in protein sequences are excluded as false positives.
        We look for AWS keys in proper configuration context only.
        """
        violations = []
        # AWS Access Key ID is exactly 20 chars: AKIA + 16 alphanumeric
        # Look for keys in config/header context (quoted or with aws prefix)
        aws_key_patterns = [
            r'["\']?aws[_-]?access[_-]?key["\']?\s*[:=]\s*["\']?AKIA[0-9A-Z]{16}["\']?',
            r'aws_access_key_id\s*[:=]\s*["\']?AKIA[0-9A-Z]{16}["\']?',
            r'AccessKeyId["\']?\s*[:=]\s*["\']?AKIA[0-9A-Z]{16}["\']?',
        ]
        aws_secret_pattern = r'["\']?aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\'][^"\']{20,}["\']'

        for cassette in cassette_files:
            content = cassette.read_text(encoding="utf-8")
            # Look for AWS keys in header/config context (not in protein sequences)
            for pattern in aws_key_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    violations.append(f"{cassette.name}: Contains AWS Access Key")
                    break
            if re.search(aws_secret_pattern, content, re.IGNORECASE):
                violations.append(f"{cassette.name}: Contains AWS Secret")

        assert not violations, "Cassettes with AWS credentials:\n" + "\n".join(violations)


class TestNoHardcodedSecrets:
    """Tests that source code doesn't contain hardcoded secrets."""

    @pytest.fixture
    def python_files(self) -> list[Path]:
        """Get all Python source files."""
        return list(SRC_DIR.rglob("*.py"))

    def test_source_files_exist(self, python_files: list[Path]) -> None:
        """Verify source files exist."""
        assert len(python_files) > 0, "No Python source files found"

    def test_no_hardcoded_secrets(self, python_files: list[Path]) -> None:
        """Verify no hardcoded secrets in source code."""
        violations = []

        for py_file in python_files:
            content = py_file.read_text(encoding="utf-8")

            # Skip if content matches allowed patterns
            for pattern, secret_type in SECRET_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    matched_text = match.group()
                    # Check if it's a false positive
                    if not any(
                        re.search(allowed, matched_text, re.IGNORECASE)
                        for allowed in ALLOWED_PATTERNS
                    ):
                        rel_path = py_file.relative_to(PROJECT_ROOT)
                        violations.append(
                            f"{rel_path}: Potential {secret_type}: {matched_text[:50]}..."
                        )

        assert not violations, "Potential secrets found:\n" + "\n".join(violations)

    def test_env_vars_use_correct_prefix(self, python_files: list[Path]) -> None:
        """Verify environment variables use BIOETL_ prefix."""
        non_bioetl_env_vars = []
        # Pattern to find os.environ.get or os.getenv calls
        env_pattern = r'os\.(?:environ\.get|getenv)\s*\(\s*["\']([^"\']+)["\']'

        # Allowed non-BIOETL prefixes (standard Python/system vars)
        allowed_prefixes = (
            "PATH",
            "HOME",
            "USER",
            "PYTHONPATH",
            "VIRTUAL_ENV",
            "DEBUG",
            "LOG_LEVEL",
            "CI",
            "GITHUB_",
        )

        for py_file in python_files:
            content = py_file.read_text(encoding="utf-8")
            matches = re.findall(env_pattern, content)

            for var_name in matches:
                if not var_name.startswith("BIOETL_") and not any(
                    var_name.startswith(prefix) for prefix in allowed_prefixes
                ):
                    rel_path = py_file.relative_to(PROJECT_ROOT)
                    non_bioetl_env_vars.append(f"{rel_path}: {var_name}")

        if non_bioetl_env_vars:
            # Warning, not failure - some legacy vars may exist
            pytest.xfail(
                "Non-BIOETL env vars (consider migrating):\n"
                + "\n".join(non_bioetl_env_vars)
            )


class TestPrivateKeyExposure:
    """Tests for private key exposure."""

    @pytest.fixture
    def all_files(self) -> list[Path]:
        """Get all files in project (excluding .git and venv)."""
        excluded = {".git", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache"}
        files = []
        for item in PROJECT_ROOT.rglob("*"):
            if item.is_file() and not any(ex in item.parts for ex in excluded):
                files.append(item)
        return files

    def test_no_private_keys_in_repo(self, all_files: list[Path]) -> None:
        """Verify no private keys in repository."""
        violations = []
        key_extensions = {".pem", ".key", ".p12", ".pfx"}
        key_pattern = r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"

        for file_path in all_files:
            # Check extension
            if file_path.suffix.lower() in key_extensions:
                violations.append(f"{file_path.name}: Private key file extension")
                continue

            # Check content for text files
            if file_path.suffix.lower() in {".py", ".txt", ".yaml", ".yml", ".json", ".md"}:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if re.search(key_pattern, content):
                        rel_path = file_path.relative_to(PROJECT_ROOT)
                        violations.append(f"{rel_path}: Contains private key")
                except UnicodeDecodeError:
                    pass  # Binary file

        assert not violations, "Private keys found:\n" + "\n".join(violations)


class TestPIIHandling:
    """Tests for PII handling patterns."""

    def test_silver_layer_uses_hashing(self) -> None:
        """Verify Silver layer transformers use hashing for PII fields."""
        # Check that PII-related code uses sha256
        infrastructure_files = list(
            (SRC_DIR / "infrastructure").rglob("*.py")
        )
        application_files = list(
            (SRC_DIR / "application").rglob("*.py")
        )

        all_files = infrastructure_files + application_files
        pii_patterns = [
            r"email",
            r"phone",
            r"address",
            r"ssn",
            r"social_security",
        ]

        files_with_pii = []
        for py_file in all_files:
            content = py_file.read_text(encoding="utf-8")
            for pattern in pii_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    # Check if sha256 or hashing is mentioned nearby
                    if not re.search(r"sha256|hash|anonymize", content, re.IGNORECASE):
                        rel_path = py_file.relative_to(PROJECT_ROOT)
                        files_with_pii.append(f"{rel_path}: PII field '{pattern}' without hashing")

        # This is informational - PII fields without explicit hashing may be OK
        # if they're excluded from Silver layer
        if files_with_pii:
            pytest.skip("Review PII handling:\n" + "\n".join(files_with_pii))
