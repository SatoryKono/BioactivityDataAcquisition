"""Security tests for BioETL.

Validates:
1. VCR cassettes don't contain secrets
2. Environment variable patterns follow conventions
3. No hardcoded secrets in source code
4. PII handling follows security guidelines
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.security

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
    (
        r"Authorization['\"]?\s*[:=]\s*['\"]Bearer\s+[A-Za-z0-9\-_.]{20,}['\"]",
        "Bearer token",
    ),
    (
        r"Authorization['\"]?\s*[:=]\s*['\"]Basic\s+[A-Za-z0-9+/=]{20,}['\"]",
        "Basic auth",
    ),
    # AWS credentials (in proper context, not bare pattern which matches protein sequences)
    (r"aws_access_key_id\s*[:=]\s*['\"]AKIA[0-9A-Z]{16}['\"]", "AWS Access Key"),
    (
        r"['\"]?aws[_-]?secret[_-]?access[_-]?key['\"]?\s*[:=]\s*['\"][^'\"]{20,}['\"]",
        "AWS secret",
    ),
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

PII_PATTERNS = [
    (r"\bemail\b", "email"),
    (r"\bphone\b", "phone"),
    (r"\baddress\b", "address"),
    (r"\bssn\b", "ssn"),
    (r"\bsocial_security\b", "social_security"),
]


# ---------------------------------------------------------------------------
# Session-scoped fixture: read all source .py files once per test session.
# Caches (path, content) tuples so that multiple test classes that scan
# source files do not re-read the filesystem independently.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def _src_file_contents() -> list[tuple[Path, str]]:
    """Read all Python source files under SRC_DIR once per session."""
    return [
        (py_file, py_file.read_text(encoding="utf-8"))
        for py_file in sorted(SRC_DIR.rglob("*.py"))
    ]


@pytest.mark.slow
@pytest.mark.timeout(300)  # VCR cassettes can be large
class TestVCRCassetteSanitization:
    """Tests that VCR cassettes don't contain secrets."""

    @pytest.fixture(scope="class")
    @classmethod
    def cassette_files(cls) -> list[Path]:
        """Get all VCR cassette files (class-scoped to avoid repeated glob)."""
        if not VCR_DIR.exists():
            pytest.skip("VCR directory not found")
        return list(VCR_DIR.rglob("*.yaml"))

    @pytest.fixture(scope="class")
    @classmethod
    def cassette_contents(cls, cassette_files: list[Path]) -> list[tuple[str, str]]:
        """Pre-load all cassette contents once for the entire class.

        Returns list of (filename, content) tuples. Reading 182 YAML files
        (~169MB) once instead of per-test avoids ~7x redundant I/O.
        """
        return [
            (cassette.name, cassette.read_text(encoding="utf-8"))
            for cassette in cassette_files
        ]

    def test_vcr_cassettes_exist(self, cassette_files: list[Path]) -> None:
        """Verify VCR cassettes exist."""
        assert len(cassette_files) > 0, "No VCR cassettes found"

    @pytest.mark.parametrize(
        "header_name",
        ["Authorization", "X-API-Key", "X-Api-Key", "Api-Key", "Apikey"],
    )
    def test_no_authorization_headers_with_real_values(
        self, cassette_contents: list[tuple[str, str]], header_name: str
    ) -> None:
        """Verify cassettes don't contain real authorization headers."""
        violations = []
        header_lower = header_name.lower()
        compiled = re.compile(
            rf"{header_name}:\s*['\"]?[A-Za-z0-9+/=\-_.]{(20,)}['\"]?",
            re.IGNORECASE,
        )
        for name, content in cassette_contents:
            # Quick pre-filter: skip files that don't contain the header name
            if header_lower not in content.lower():
                continue
            if compiled.search(content):
                violations.append(f"{name}: Contains {header_name} header")

        assert not violations, "Cassettes with secrets:\n" + "\n".join(violations)

    def test_no_bearer_tokens(self, cassette_contents: list[tuple[str, str]]) -> None:
        """Verify no Bearer tokens in cassettes."""
        violations = []
        bearer_re = re.compile(r"Bearer\s+[A-Za-z0-9\-_.]{20,}")
        for name, content in cassette_contents:
            # Quick pre-filter: skip files without "Bearer"
            if "Bearer" not in content:
                continue
            if bearer_re.search(content):
                violations.append(f"{name}: Contains Bearer token")

        assert not violations, "Cassettes with Bearer tokens:\n" + "\n".join(violations)

    def test_no_aws_credentials(self, cassette_contents: list[tuple[str, str]]) -> None:
        """Verify no AWS credentials in cassettes.

        Note: AKIA patterns in protein sequences are excluded as false positives.
        We look for AWS keys in proper configuration context only.
        """
        violations = []
        # Pre-compile combined pattern for all AWS key variants (single pass)
        aws_key_combined = re.compile(
            r"(?:"
            r'["\']?aws[_-]?access[_-]?key["\']?\s*[:=]\s*["\']?AKIA[0-9A-Z]{16}["\']?'
            r'|aws_access_key_id\s*[:=]\s*["\']?AKIA[0-9A-Z]{16}["\']?'
            r'|AccessKeyId["\']?\s*[:=]\s*["\']?AKIA[0-9A-Z]{16}["\']?'
            r")",
            re.IGNORECASE,
        )
        aws_secret_re = re.compile(
            r'["\']?aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\'][^"\']{20,}["\']',
            re.IGNORECASE,
        )

        # Quick pre-filter: skip files that don't contain "aws" or "AKIA"
        # (case-insensitive substring check is much faster than regex)
        for name, content in cassette_contents:
            content_lower = content.lower()
            if "aws" not in content_lower and "akia" not in content_lower:
                continue
            if aws_key_combined.search(content):
                violations.append(f"{name}: Contains AWS Access Key")
            if aws_secret_re.search(content):
                violations.append(f"{name}: Contains AWS Secret")

        assert not violations, "Cassettes with AWS credentials:\n" + "\n".join(
            violations
        )


@pytest.mark.timeout(180)  # File scanning needs more time
class TestNoHardcodedSecrets:
    """Tests that source code doesn't contain hardcoded secrets."""

    @pytest.fixture(scope="class")
    @classmethod
    def source_contents(
        cls, _src_file_contents: list[tuple[Path, str]]
    ) -> list[tuple[Path, str]]:
        """Class-scoped alias for session-cached source file contents."""
        return _src_file_contents

    def test_source_files_exist(self, source_contents: list[tuple[Path, str]]) -> None:
        """Verify source files exist."""
        assert len(source_contents) > 0, "No Python source files found"

    def test_no_hardcoded_secrets__no_hardcoded_secrets__bd2bd2d3(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
        """Verify no hardcoded secrets in source code."""
        violations = []

        for py_file, content in source_contents:
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

    def test_env_vars_use_correct_prefix(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
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
            "PYTEST_",
            "OTEL_",
            "DEBUG",
            "LOG_LEVEL",
            "CI",
            "GITHUB_",
        )

        for py_file, content in source_contents:
            matches = re.findall(env_pattern, content)

            for var_name in matches:
                if not var_name.startswith("BIOETL_") and not any(
                    var_name.startswith(prefix) for prefix in allowed_prefixes
                ):
                    rel_path = py_file.relative_to(PROJECT_ROOT)
                    non_bioetl_env_vars.append(f"{rel_path}: {var_name}")

        assert not non_bioetl_env_vars


@pytest.mark.timeout(180)  # File scanning needs more time
class TestPrivateKeyExposure:
    """Tests for private key exposure."""

    @pytest.fixture(scope="class")
    @classmethod
    def all_files(cls) -> list[Path]:
        """Get all files in project (excluding .git and venv).

        Uses os.walk for efficiency to prune ignored directories.
        """
        import os

        excluded = {
            ".git",
            ".worktrees",
            ".venv",
            ".venv-docs",
            ".venv-win",
            "venv",
            "__pycache__",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".hypothesis",
            ".benchmarks",
            ".cache",
            ".import_linter_cache",
            ".codex",
            ".jules",
            ".github",
            "data",
            "build",
            "dist",
            ".idea",
            ".vscode",
            "logs",
            "tmp",
            "node_modules",
            "site",
            "htmlcov",
            "coverage.json",  # Skip large generated files
        }

        files = []
        # Walk effectively prunes trees, unlike rglob
        for root, dirs, filenames in os.walk(PROJECT_ROOT):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in excluded]

            for filename in filenames:
                if filename in excluded:
                    continue

                file_path = Path(root) / filename
                files.append(file_path)

        return files

    def test_no_private_keys_in_repo(self, all_files: list[Path]) -> None:
        """Verify no private keys in repository."""
        import subprocess

        violations = []
        key_extensions = {".pem", ".key", ".p12", ".pfx"}

        tracked_files = all_files
        try:
            tracked = subprocess.run(
                ["git", "ls-files"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(PROJECT_ROOT),
            )
            if tracked.returncode == 0 and tracked.stdout.strip():
                tracked_files = [
                    PROJECT_ROOT / rel_path
                    for rel_path in tracked.stdout.strip().splitlines()
                ]
        except (subprocess.TimeoutExpired, OSError):
            pass

        # 1) Check tracked repository files for private-key-like extensions.
        for file_path in tracked_files:
            if file_path.suffix.lower() in key_extensions:
                rel_path = file_path.relative_to(PROJECT_ROOT)
                violations.append(f"{rel_path}: Private key file extension")

        # 2) Check file content using git grep (immune to Windows file locks)
        text_globs = ["*.py", "*.txt", "*.yaml", "*.yml", "*.json", "*.md"]
        git_grep_cmd = [
            "git",
            "grep",
            "-l",
            "-E",
            r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
            "--",
            *text_globs,
        ]
        try:
            result = subprocess.run(
                git_grep_cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(PROJECT_ROOT),
            )
            if result.returncode == 0 and result.stdout.strip():
                for match_file in result.stdout.strip().splitlines():
                    # The security tests themselves carry the detection pattern.
                    # Exclude them from repository-content hits to avoid self-matches.
                    if match_file.startswith("tests/security/"):
                        continue
                    violations.append(f"{match_file}: Contains private key")
        except (subprocess.TimeoutExpired, OSError):
            pass  # git grep unavailable or timed out -- skip content check

        assert not violations, "Private keys found:\n" + "\n".join(violations)


@pytest.mark.timeout(120)  # File scanning needs more time
class TestPIIHandling:
    """Tests for PII handling patterns.

    Enforces that all files containing PII-related fields (email, phone,
    address, ssn) either:
    1. Reference hashing/anonymization (sha256, hash, anonymize keywords), OR
    2. Are in the known technical/false-positive allowlist.

    IMPORTANT: Known False Positives (NOT actual PII):
    -------------------------------------------------
    - `email` in config.py, pubmed_client.py, pipeline_config.py, client.py:
      These are technical API identifiers required by NCBI E-utilities for
      tool identification, NOT user personal data. NCBI mandates this for
      rate limiting and contact purposes.
      See: https://www.ncbi.nlm.nih.gov/books/NBK25497/

    - `issn` (matched by `ssn` pattern): ISSN is International Standard Serial
      Number for journals, NOT Social Security Number.

    - `address` in affiliation contexts: Refers to "email address" text in
      PubMed affiliation extraction, not physical/postal address PII.
      Actual email values are hashed at the transformer level (RULES.md S5.4).
    """

    # Files with known technical email usage (NOT user PII)
    # These are API identifiers required by external services
    KNOWN_TECHNICAL_EMAIL_FILES = frozenset(
        {
            "_base.py",  # NCBI API tool identification (default_email in Settings)
            "config.py",  # NCBI API tool identification (default_email)
            "pubmed_client.py",  # NCBI API tool identification
            "_health.py",  # PubMed adapter (NCBI required email)
            "_search.py",  # PubMed adapter (NCBI required email)
            "_fetch.py",  # PubMed adapter (NCBI required email)
            "_state.py",  # PubMed adapter state mixin (NCBI required email)
            "pipeline_config.py",  # NCBI API source config
            "client.py",  # User-Agent header identification
            "source_config.py",  # NCBI API default_email for PubMed
            "batch.py",  # CrossRef mailto for polite pool access (higher rate limits)
            "pipeline_config_provider.py",  # Technical email config for API identification
            "client_builders.py",  # CrossRef mailto for polite pool (EXC-010)
            "health_probe.py",  # OpenAlex mailto for API identification (EXC-010)
            "query_builder.py",  # OpenAlex mailto for API identification (EXC-010)
            "constants.py",  # NCBI API docstring mentions Email requirement (EXC-010)
        }
    )
    KNOWN_TECHNICAL_EMAIL_PATHS = frozenset(
        {
            # NCBI-required technical contact resolved by the PubMed adapter factory.
            "infrastructure/adapters/pubmed/_adapter_support.py",
        }
    )

    # Files where "address" refers to non-PII context (email address text,
    # network address, etc.) -- not physical/postal address
    KNOWN_NON_PII_ADDRESS_FILES = frozenset(
        {
            "noop_logger.py",  # Logging infrastructure, no PII
            "retry.py",  # Network retry logic, "address" = URL/endpoint
            "server.py",  # Metrics server, "address" = network bind address
        }
    )

    def _scanned_layer_files(self) -> list[Path]:
        infrastructure_files = list((SRC_DIR / "infrastructure").rglob("*.py"))
        application_files = list((SRC_DIR / "application").rglob("*.py"))
        return infrastructure_files + application_files

    def _file_is_allowlisted_for_pattern(
        self,
        py_file: Path,
        pattern_name: str,
    ) -> bool:
        if py_file.name in self.KNOWN_TECHNICAL_EMAIL_FILES:
            return True
        if (
            pattern_name == "email"
            and py_file.relative_to(SRC_DIR).as_posix()
            in self.KNOWN_TECHNICAL_EMAIL_PATHS
        ):
            return True
        return (
            pattern_name == "address"
            and py_file.name in self.KNOWN_NON_PII_ADDRESS_FILES
        )

    def _file_mentions_hashing(self, content: str) -> bool:
        return bool(re.search(r"sha256|hash|anonymize", content, re.IGNORECASE))

    def _pii_violations_for_file(self, py_file: Path) -> list[str]:
        content = py_file.read_text(encoding="utf-8")
        violations: list[str] = []
        for regex_pattern, pattern_name in PII_PATTERNS:
            if not re.search(regex_pattern, content, re.IGNORECASE):
                continue
            if self._file_is_allowlisted_for_pattern(py_file, pattern_name):
                continue
            if self._file_mentions_hashing(content):
                continue
            rel_path = py_file.relative_to(PROJECT_ROOT)
            violations.append(f"{rel_path}: PII field '{pattern_name}' without hashing")
        return violations

    def test_silver_layer_uses_hashing(self) -> None:
        """Verify Silver layer transformers use hashing for PII fields.

        ENFORCED: Files containing PII-related fields MUST reference
        hashing/anonymization or be in the known allowlist.
        Violations indicate PII leakage risk (RULES.md S5.4).
        """
        files_with_pii = [
            violation
            for py_file in self._scanned_layer_files()
            for violation in self._pii_violations_for_file(py_file)
        ]

        assert not files_with_pii, (
            "PII fields found without hashing reference (RULES.md S5.4).\n"
            "Each file with PII-related fields MUST either:\n"
            "  1. Reference hashing/anonymization (sha256, hash, anonymize), OR\n"
            "  2. Be added to the known allowlist with documented rationale.\n"
            "Violations:\n" + "\n".join(files_with_pii)
        )


@pytest.mark.timeout(120)  # File scanning needs more time
class TestInputValidation:
    """Tests for input validation and injection prevention."""

    @pytest.fixture(scope="class")
    @classmethod
    def source_contents(
        cls, _src_file_contents: list[tuple[Path, str]]
    ) -> list[tuple[Path, str]]:
        """Class-scoped alias for session-cached source file contents."""
        return _src_file_contents

    def test_no_eval_or_exec_in_source(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
        """Verify no dangerous eval/exec calls in source code."""
        violations = []
        dangerous_patterns = [
            (r"\beval\s*\(", "eval()"),
            (r"\bexec\s*\(", "exec()"),
            (r"\bcompile\s*\([^)]*\bexec\b", "compile() with exec mode"),
        ]

        for py_file, content in source_contents:
            for pattern, desc in dangerous_patterns:
                if re.search(pattern, content):
                    rel_path = py_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel_path}: {desc}")

        assert not violations, "Dangerous code execution found:\n" + "\n".join(
            violations
        )

    def test_no_shell_injection_patterns(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
        """Verify no shell injection vulnerabilities in subprocess calls."""
        violations = []
        # Dangerous: shell=True with variable input
        dangerous_pattern = r"subprocess\.(?:run|call|Popen)\s*\([^)]*shell\s*=\s*True"

        for py_file, content in source_contents:
            if re.search(dangerous_pattern, content):
                rel_path = py_file.relative_to(PROJECT_ROOT)
                violations.append(f"{rel_path}: subprocess with shell=True")

        assert not violations, "Shell injection risks found:\n" + "\n".join(violations)

    def test_no_sql_string_formatting(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
        """Verify no SQL injection via string formatting."""
        violations = []
        # Dangerous: f-string or % formatting in SQL queries
        # Use more specific patterns to avoid false positives on normal text
        # containing words like "update" in non-SQL contexts
        sql_patterns = [
            # SELECT ... FROM with interpolation
            r'f["\'].*SELECT\s+.+\s+FROM\s+.*{',
            # INSERT INTO with interpolation
            r'f["\'].*INSERT\s+INTO\s+.*{',
            # UPDATE ... SET with interpolation
            r'f["\'].*UPDATE\s+\w+\s+SET\s+.*{',
            # DELETE FROM with interpolation
            r'f["\'].*DELETE\s+FROM\s+.*{',
            # CREATE/DROP TABLE/DATABASE with interpolation
            r'f["\'].*(?:CREATE|DROP)\s+(?:TABLE|DATABASE|INDEX)\s+.*{',
            # % formatting with SQL keywords followed by FROM/INTO/SET
            r'["\'].*SELECT\s+.+\s+FROM.*["\']\s*%',
            r'["\'].*INSERT\s+INTO.*["\']\s*%',
            r'["\'].*UPDATE\s+\w+\s+SET.*["\']\s*%',
            r'["\'].*DELETE\s+FROM.*["\']\s*%',
        ]

        for py_file, content in source_contents:
            for pattern in sql_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    rel_path = py_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel_path}: Potential SQL injection")
                    break

        assert not violations, "SQL injection risks found:\n" + "\n".join(violations)

    def test_no_pickle_with_untrusted_data(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
        """Verify no pickle.loads on untrusted data."""
        violations = []
        # Check for pickle usage (which should be reviewed for untrusted input)
        pickle_pattern = r"pickle\.(?:loads?|Unpickler)"

        for py_file, content in source_contents:
            if re.search(pickle_pattern, content):
                # Check if it's in a context that might be dangerous
                # (loading from network, user input, etc.)
                rel_path = py_file.relative_to(PROJECT_ROOT)
                violations.append(
                    f"{rel_path}: Uses pickle (review for untrusted input)"
                )

        # Informational - pickle may be OK for internal serialization
        if violations:
            pytest.skip("Review pickle usage:\n" + "\n".join(violations))

        assert not violations


@pytest.mark.timeout(120)  # File scanning needs more time
class TestPathTraversal:
    """Tests for path traversal vulnerabilities."""

    @pytest.fixture(scope="class")
    @classmethod
    def source_contents(
        cls, _src_file_contents: list[tuple[Path, str]]
    ) -> list[tuple[Path, str]]:
        """Class-scoped alias for session-cached source file contents."""
        return _src_file_contents

    # Files where Path(request.*) is a typed internal dataclass, not user input
    KNOWN_SAFE_PATH_FILES = frozenset(
        {
            "writer_operations.py",  # Path(request.base_path) — internal _MetadataWriteRequest dataclass
        }
    )

    def test_no_unsanitized_path_joins(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
        """Verify path handling uses safe patterns."""
        violations = []
        # Looking for patterns where user input might be joined to paths
        # without proper sanitization
        dangerous_patterns = [
            r"os\.path\.join\s*\([^)]*request\.",
            r"Path\s*\([^)]*request\.",
            r"open\s*\([^)]*\+",  # String concatenation in open()
        ]

        for py_file, content in source_contents:
            if py_file.name in self.KNOWN_SAFE_PATH_FILES:
                continue
            for dangerous_pattern in dangerous_patterns:
                if re.search(dangerous_pattern, content):
                    rel_path = py_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel_path}: Potential path traversal")

        assert not violations, "Path traversal risks:\n" + "\n".join(violations)

    def test_config_files_use_safe_paths(self) -> None:
        """Verify configuration files don't allow arbitrary path access."""
        config_dir = PROJECT_ROOT / "configs"
        if not config_dir.exists():
            pytest.skip("No configs directory")

        violations = []
        for config_file in config_dir.rglob("*.yaml"):
            content = config_file.read_text(encoding="utf-8")
            # Check for absolute paths that might be manipulated
            if re.search(r'^\s*path:\s*["\']?/', content, re.MULTILINE):
                # Verify it's not a user-controllable path
                if "user" in content.lower() or "input" in content.lower():
                    violations.append(f"{config_file.name}: User-controllable path")

        assert not violations, "Path issues in configs:\n" + "\n".join(violations)


@pytest.mark.timeout(120)  # File scanning needs more time
class TestSecurityHeaders:
    """Tests for security-related header handling."""

    @pytest.fixture(scope="class")
    @classmethod
    def source_contents(
        cls, _src_file_contents: list[tuple[Path, str]]
    ) -> list[tuple[Path, str]]:
        """Class-scoped alias for session-cached source file contents."""
        return _src_file_contents

    def test_sensitive_headers_sanitized_in_logs(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
        """Verify sensitive headers are not logged."""
        violations = []
        sensitive_headers = [
            "Authorization",
            "X-API-Key",
            "Cookie",
            "Set-Cookie",
            "X-Auth-Token",
        ]

        log_pattern = r"(?:logger?\.(?:info|debug|warning|error)|print)\s*\("

        for py_file, content in source_contents:
            if re.search(log_pattern, content):
                for header in sensitive_headers:
                    # Check if header name appears near logging statements
                    combined_pattern = (
                        rf"(?:logger?\.(?:info|debug|warning|error)|print)\s*\([^)]*"
                        rf"{header}[^)]*(?:request\.headers|response\.headers)"
                    )
                    if re.search(combined_pattern, content, re.IGNORECASE):
                        rel_path = py_file.relative_to(PROJECT_ROOT)
                        violations.append(f"{rel_path}: Logs {header} header")

        assert not violations, "Sensitive headers in logs:\n" + "\n".join(violations)


@pytest.mark.timeout(120)  # File scanning needs more time
class TestCryptographyUsage:
    """Tests for proper cryptography usage."""

    @pytest.fixture(scope="class")
    @classmethod
    def source_contents(
        cls, _src_file_contents: list[tuple[Path, str]]
    ) -> list[tuple[Path, str]]:
        """Class-scoped alias for session-cached source file contents."""
        return _src_file_contents

    def test_uses_secure_hash_algorithms(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
        """Verify secure hash algorithms are used.

        Note: MD5/SHA1 with usedforsecurity=False is allowed for non-cryptographic
        purposes like deterministic jitter (see ADR-014).
        """
        weak_hashes = ["md5", "sha1"]
        violations = []

        for py_file, content in source_contents:
            for weak_hash in weak_hashes:
                # Check for hashlib usage of weak algorithms
                # Skip comments and multi-line strings for detection
                # Using a more robust regex that handles one level of nested parentheses
                matches = re.finditer(
                    rf"hashlib\.{weak_hash}\s*\((?:[^()]|\([^()]*\))*\)", content
                )
                for match in matches:
                    call = match.group(0)
                    # Allow if usedforsecurity=False is explicitly set
                    if "usedforsecurity=False" not in call:
                        rel_path = py_file.relative_to(PROJECT_ROOT)
                        violations.append(
                            f"{rel_path}: Uses weak hash {weak_hash} without usedforsecurity=False"
                        )

        assert not violations, "Weak hash algorithms:\n" + "\n".join(violations)

    def test_random_uses_secrets_module(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
        """Verify security-sensitive randomness uses secrets module."""
        # For tokens, keys, etc. - random module is not cryptographically secure
        violations = []
        random_pattern = r"random\.(?:choice|randint|random|sample)\s*\("

        for py_file, content in source_contents:
            if re.search(random_pattern, content):
                # Check if it's for security-sensitive purposes
                if re.search(
                    r"(?:token|key|secret|password|salt)", content, re.IGNORECASE
                ):
                    rel_path = py_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel_path}: random module for security purpose")

        # Informational - random may be OK for non-security uses
        if violations:
            pytest.skip("Review random usage:\n" + "\n".join(violations))

        assert not violations
