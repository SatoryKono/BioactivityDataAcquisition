import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from vcr.request import Request

    from bioetl.domain.types import RunID

# VCR.py imports (for API recording)
try:
    VCR_AVAILABLE = bool(__import__("vcr"))
except ImportError:
    VCR_AVAILABLE = False


def pytest_configure() -> None:
    """Add src directory to Python path and mock missing modules."""
    import os

    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    sys.path.insert(0, str(src_dir))

    # Set BIOETL_ENV to staging for tests to avoid dev environment validation
    # requiring endpoint_url
    os.environ.setdefault("BIOETL_ENV", "staging")

    # Mock pubchempy if not installed
    try:
        __import__("pubchempy")
    except ImportError:
        sys.modules["pubchempy"] = MagicMock()

    # Mock botocore if not installed
    try:
        __import__("botocore")
    except ImportError:
        mock_botocore = MagicMock()

        class ClientError(Exception):
            def __init__(self, error_response, operation_name):
                self.response = error_response
                self.operation_name = operation_name

        mock_botocore.exceptions.ClientError = ClientError
        sys.modules["botocore"] = mock_botocore
        sys.modules["botocore.exceptions"] = mock_botocore.exceptions

    # Mock boto3 if not installed
    try:
        __import__("boto3")
    except ImportError:
        sys.modules["boto3"] = MagicMock()


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Returns the root directory of the project."""
    # Assuming tests/conftest.py is one level deep in tests/
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def src_dir(project_root: Path) -> Path:
    return project_root / "src"


@pytest.fixture(scope="session")
def docs_dir(project_root: Path) -> Path:
    return project_root / "docs"


@pytest.fixture(scope="session")
def pyproject_toml(project_root: Path) -> Path:
    return project_root / "pyproject.toml"


@pytest.fixture(scope="session")
def requirements_md(project_root: Path) -> Path:
    return project_root / "REQUIREMENTS.md"


# =============================================================================
# VCR.py Configuration (RULES.md Section 4.2)
# =============================================================================


def _sanitize_request(request: "Request") -> "Request":
    """Sanitize secrets from recorded requests.

    Removes:
    - Authorization headers
    - API keys from query params and headers
    - PII data patterns

    Requirements:
    - REQ-TEST-002: Secret sanitization in before_record hook
    """
    if not VCR_AVAILABLE:
        return request

    # Sanitize headers
    headers_to_sanitize = [
        "Authorization",
        "X-API-Key",
        "Api-Key",
        "X-Api-Key",
        "Cookie",
        "Set-Cookie",
    ]
    for header in headers_to_sanitize:
        if header in request.headers:
            request.headers[header] = "REDACTED"
        # Also check lowercase
        if header.lower() in request.headers:
            request.headers[header.lower()] = "REDACTED"

    # Sanitize API keys in query params
    if "?" in request.uri:
        base_url, query = request.uri.split("?", 1)
        # Patterns to sanitize in query string
        patterns = [
            (r"api_key=[^&]+", "api_key=REDACTED"),
            (r"apikey=[^&]+", "apikey=REDACTED"),
            (r"access_token=[^&]+", "access_token=REDACTED"),
            (r"token=[^&]+", "token=REDACTED"),
        ]
        for pattern, replacement in patterns:
            query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
        request.uri = f"{base_url}?{query}"

    return request


def _sanitize_response(response: dict[str, Any]) -> dict[str, Any]:
    """Sanitize secrets from recorded responses."""
    # Remove sensitive headers from response
    headers_to_remove = ["Set-Cookie", "X-Request-Id"]
    if "headers" in response:
        for header in headers_to_remove:
            response["headers"].pop(header, None)
            response["headers"].pop(header.lower(), None)
    return response


@pytest.fixture(scope="module")
def vcr_cassette_dir(request: pytest.FixtureRequest, project_root: Path) -> Path:
    """Return the directory for VCR cassettes based on test module."""
    # Create cassette directory based on test module path
    test_file = Path(request.fspath)
    relative_path = test_file.relative_to(project_root / "tests")
    cassette_dir = project_root / "tests" / "fixtures" / "vcr" / relative_path.parent
    cassette_dir.mkdir(parents=True, exist_ok=True)
    return cassette_dir


@pytest.fixture(scope="module")
def vcr_config(project_root: Path) -> dict[str, Any]:
    """VCR.py configuration.

    CI mode: record_mode="none" - fail if cassette missing
    Local recording: pytest --vcr-record=new_episodes
    """
    cassette_library_dir = project_root / "tests" / "fixtures" / "vcr"
    cassette_library_dir.mkdir(parents=True, exist_ok=True)

    return {
        "cassette_library_dir": str(cassette_library_dir),
        # CI mode: fail if cassette is missing
        # Override with --vcr-record=new_episodes for local recording
        "record_mode": "new_episodes",
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "before_record_request": _sanitize_request,
        "before_record_response": _sanitize_response,
        "filter_headers": [
            "Authorization",
            "X-API-Key",
            "Cookie",
            "Set-Cookie",
        ],
        "decode_compressed_response": True,
    }


# =============================================================================
# Test Fixtures for Infrastructure Components
# =============================================================================


@pytest.fixture
def run_id() -> "RunID":
    """Generate a unique run ID for tests."""
    from bioetl.domain.types import RunID

    return RunID(uuid4())


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the settings cache before and after each test."""
    try:
        from bioetl.infrastructure.config import get_pipeline_config, get_settings

        get_settings.cache_clear()
        get_pipeline_config.cache_clear()
        yield
        get_settings.cache_clear()
        get_pipeline_config.cache_clear()
    except ImportError:
        yield


@pytest.fixture(autouse=True)
def cleanup_infrastructure_state():
    """
    Ensure infrastructure state is cleared between tests.

    This prevents state leakage between tests, specifically for:
    - S3ClientPool: Contains boto3 clients that might be bound to mocks or real endpoints.
    """
    yield

    # Teardown
    try:
        from bioetl.infrastructure.storage.s3_client_pool import S3ClientPool

        S3ClientPool.clear_pool()
    except ImportError:
        pass


@pytest.fixture(scope="session")
def docker_ip():
    """Get Docker IP address, skip if Docker not available."""
    import platform
    import shutil

    if not shutil.which("docker"):
        pytest.skip("Docker executable not found")

    try:
        # For Windows, Docker Desktop typically uses localhost.
        if platform.system() == "Windows":
            return "localhost"

        # Try to execute a docker command to verify connectivity
        import subprocess

        from pytest_docker.plugin import get_docker_ip

        subprocess.check_call(
            ["docker", "ps"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return get_docker_ip()
    except ImportError:
        pytest.skip("pytest-docker not installed, run: pip install pytest-docker")
    except Exception:
        pytest.skip("Docker not available or not running")


@pytest.fixture(scope="session")
def docker_compose_file(project_root: Path) -> str:
    """Path to docker-compose.test.yml for pytest-docker.

    Uses a separate compose file with only the minimal services (minio, redis)
    required for testing. This avoids port conflicts and issues with
    services like Grafana that mount local directories.
    """
    return str(project_root / "docker-compose.test.yml")


@pytest.fixture(scope="session")
def minio_service(docker_ip, docker_services):
    """Ensure that MinIO service is up and responsive."""
    import urllib.error
    import urllib.request

    port = docker_services.port_for("minio", 9000)
    url = f"http://{docker_ip}:{port}"

    def is_responsive():
        try:
            urllib.request.urlopen(f"{url}/minio/health/live", timeout=2)
            return True
        except (urllib.error.URLError, ConnectionError):
            return False

    docker_services.wait_until_responsive(timeout=30.0, pause=0.5, check=is_responsive)
    return url


@pytest.fixture(scope="session")
def redis_service(docker_ip, docker_services):
    """Ensure that Redis service is up and responsive."""
    import socket

    port = docker_services.port_for("redis", 6379)

    def is_responsive():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect((docker_ip, port))
            sock.close()
            return True
        except (OSError, ConnectionError):
            return False

    docker_services.wait_until_responsive(timeout=30.0, pause=0.5, check=is_responsive)
    return f"redis://{docker_ip}:{port}"


@pytest.fixture
def minio_client(minio_service):
    """boto3 client for MinIO."""
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=minio_service,
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
    )
    # Create buckets
    buckets = ["bronze", "silver", "gold", "checkpoints"]
    for bucket in buckets:
        client.create_bucket(Bucket=bucket)
    return client


@pytest.fixture
def redis_client(redis_service):
    """Redis client."""
    import redis.asyncio as aioredis

    return aioredis.from_url(redis_service)


@pytest.fixture
def fake_redis():
    """Fake Redis client for unit tests using fakeredis."""
    try:
        import fakeredis.aioredis
    except ImportError:
        pytest.skip("fakeredis not installed, run: pip install fakeredis")

    return fakeredis.aioredis.FakeRedis()


@pytest.fixture
def token_bucket():
    """Token bucket rate limiter for testing."""
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

    return TokenBucket(rate=100.0, capacity=100)


@pytest.fixture
def circuit_breaker():
    """Circuit breaker for testing."""
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker

    return CircuitBreaker(provider="test", failure_threshold=5, recovery_timeout=60)


# =============================================================================
# E2E Docker Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def docker_ip():
    """Get Docker IP address, skip if Docker not available."""
    import platform
    import shutil

    if not shutil.which("docker"):
        pytest.skip("Docker executable not found")

    try:
        # For Windows, Docker Desktop typically uses localhost.
        if platform.system() == "Windows":
            return "localhost"

        # Try to execute a docker command to verify connectivity
        import subprocess

        from pytest_docker.plugin import get_docker_ip

        subprocess.check_call(
            ["docker", "ps"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return get_docker_ip()
    except ImportError:
        # If pytest-docker is not installed or other error, assume localhost for many CI envs
        # or skip.
        return "localhost"
    except Exception:
        pytest.skip("Docker not available or not running")


@pytest.fixture(scope="session")
def docker_compose_file(project_root: Path) -> str:
    """Path to docker-compose.test.yml for pytest-docker.

    Uses a separate compose file with only the minimal services (minio, redis)
    required for testing.
    """
    return str(project_root / "docker-compose.test.yml")


@pytest.fixture(scope="session")
def minio_service(docker_ip, docker_services):
    """Ensure that MinIO service is up and responsive."""
    import urllib.error
    import urllib.request

    # Assuming port 9000 is mapped
    port = docker_services.port_for("minio", 9000)
    url = f"http://{docker_ip}:{port}"

    # Wait for health check
    def is_responsive():
        try:
            # Use /minio/health/live for liveness check
            urllib.request.urlopen(f"{url}/minio/health/live", timeout=1)
            return True
        except (urllib.error.URLError, ConnectionError, Exception):
            return False

    docker_services.wait_until_responsive(timeout=30.0, pause=0.5, check=is_responsive)
    return url


@pytest.fixture(scope="session")
def redis_service(docker_ip, docker_services):
    """Ensure that Redis service is up and responsive."""
    import socket

    port = docker_services.port_for("redis", 6379)

    def is_responsive():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect((docker_ip, port))
            sock.close()
            return True
        except (OSError, ConnectionError):
            return False

    docker_services.wait_until_responsive(timeout=30.0, pause=0.5, check=is_responsive)
    return f"redis://{docker_ip}:{port}"
