"""Tests for unified HTTP error handler."""

from unittest.mock import Mock

from bioetl.domain.errors import ClientRateLimitError
from bioetl.domain.ports.resilience import ErrorCategory, RequestContext
from bioetl.infrastructure.clients.base.http_error_handler import DefaultHttpErrorHandler
from bioetl.infrastructure.errors import ApiUnexpectedStatusError


class TestErrorCategory:
    """Test ErrorCategory enum."""

    def test_error_categories_exist(self):
        """Test that all expected categories exist."""
        assert ErrorCategory.RATE_LIMIT.value == "rate_limit"
        assert ErrorCategory.SERVER_ERROR.value == "server_error"
        assert ErrorCategory.CLIENT_ERROR.value == "client_error"
        assert ErrorCategory.SUCCESS.value == "success"
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestDefaultHttpErrorHandler:
    """Test DefaultHttpErrorHandler implementation."""

    def test_classify_error_success(self):
        """Test classification of successful status codes."""
        handler = DefaultHttpErrorHandler()

        assert handler.classifier.classify(200) == ErrorCategory.SUCCESS
        assert handler.classifier.classify(201) == ErrorCategory.SUCCESS
        assert handler.classifier.classify(204) == ErrorCategory.SUCCESS
        assert handler.classifier.classify(301) == ErrorCategory.SUCCESS
        assert handler.classifier.classify(302) == ErrorCategory.SUCCESS

    def test_classify_error_rate_limit(self):
        """Test classification of rate limit status code."""
        handler = DefaultHttpErrorHandler()

        assert handler.classifier.classify(429) == ErrorCategory.RATE_LIMIT

    def test_classify_error_server_errors(self):
        """Test classification of 5xx server errors."""
        handler = DefaultHttpErrorHandler()

        assert handler.classifier.classify(500) == ErrorCategory.SERVER_ERROR
        assert handler.classifier.classify(502) == ErrorCategory.SERVER_ERROR
        assert handler.classifier.classify(503) == ErrorCategory.SERVER_ERROR
        assert handler.classifier.classify(504) == ErrorCategory.SERVER_ERROR

    def test_classify_error_client_errors(self):
        """Test classification of 4xx client errors."""
        handler = DefaultHttpErrorHandler()

        assert handler.classifier.classify(400) == ErrorCategory.CLIENT_ERROR
        assert handler.classifier.classify(401) == ErrorCategory.CLIENT_ERROR
        assert handler.classifier.classify(403) == ErrorCategory.CLIENT_ERROR
        assert handler.classifier.classify(404) == ErrorCategory.CLIENT_ERROR
        assert handler.classifier.classify(422) == ErrorCategory.CLIENT_ERROR

    def test_classify_error_unknown(self):
        """Test classification of unknown status codes."""
        handler = DefaultHttpErrorHandler()

        assert handler.classifier.classify(100) == ErrorCategory.UNKNOWN
        assert handler.classifier.classify(600) == ErrorCategory.UNKNOWN

    def test_handle_success_response(self):
        """Test that successful responses return None."""
        handler = DefaultHttpErrorHandler()
        response = Mock(status_code=200)
        context = RequestContext(
            provider="test",
            endpoint="https://api.example.com/data",
            status_code=200,
        )

        error = handler.handle(response, context)

        assert error is None

    def test_handle_rate_limit_error(self):
        """Test handling of rate limit error (429)."""
        handler = DefaultHttpErrorHandler()
        response = Mock(status_code=429)
        context = RequestContext(
            provider="test",
            endpoint="https://api.example.com/data",
            status_code=429,
        )

        error = handler.handle(response, context)

        assert isinstance(error, ClientRateLimitError)
        assert error.status_code == 429
        assert error.provider == "test"
        assert error.endpoint == "https://api.example.com/data"

    def test_handle_server_error(self):
        """Test handling of server errors (5xx)."""
        handler = DefaultHttpErrorHandler()
        response = Mock(status_code=500)
        context = RequestContext(
            provider="test",
            endpoint="https://api.example.com/data",
            status_code=500,
        )

        error = handler.handle(response, context)

        assert isinstance(error, ApiUnexpectedStatusError)
        assert error.status_code == 500
        assert error.provider == "test"
        assert "Server error" in str(error)

    def test_handle_client_error(self):
        """Test handling of client errors (4xx)."""
        handler = DefaultHttpErrorHandler()
        response = Mock(status_code=404)
        context = RequestContext(
            provider="test",
            endpoint="https://api.example.com/data",
            status_code=404,
        )

        error = handler.handle(response, context)

        assert isinstance(error, ApiUnexpectedStatusError)
        assert error.status_code == 404
        assert error.provider == "test"
        assert "Client error" in str(error)

    def test_handle_with_logger(self):
        """Test that errors are logged when logger is provided."""
        logger = Mock()
        handler = DefaultHttpErrorHandler(logger)
        response = Mock(status_code=500)
        context = RequestContext(
            provider="test",
            endpoint="https://api.example.com/data",
            status_code=500,
            method="GET",
        )

        error = handler.handle(response, context)

        assert isinstance(error, ApiUnexpectedStatusError)
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert call_args[0][0] == "server_error"

    def test_handle_status_code_from_response(self):
        """Test that status code is extracted from response if not in context."""
        handler = DefaultHttpErrorHandler()
        response = Mock(status_code=404)
        context = RequestContext(
            provider="test",
            endpoint="https://api.example.com/data",
            status_code=None,  # Not provided in context
        )

        error = handler.handle(response, context)

        assert isinstance(error, ApiUnexpectedStatusError)
        assert error.status_code == 404

    def test_handle_none_status_code(self):
        """Test handling when status code is None."""
        handler = DefaultHttpErrorHandler()
        response = Mock(spec=[])  # No status_code attribute
        context = RequestContext(
            provider="test",
            endpoint="https://api.example.com/data",
            status_code=None,
        )

        error = handler.handle(response, context)

        assert error is None

    def test_client_error_details(self):
        """Test that client error details are human-readable."""
        handler = DefaultHttpErrorHandler()

        assert handler._get_client_error_detail(400) == "Bad Request"
        assert handler._get_client_error_detail(401) == "Unauthorized"
        assert handler._get_client_error_detail(403) == "Forbidden"
        assert handler._get_client_error_detail(404) == "Not Found"
        assert handler._get_client_error_detail(429) == "Too Many Requests"
        assert handler._get_client_error_detail(999) == "Unknown Client Error"
