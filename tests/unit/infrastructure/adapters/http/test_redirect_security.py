"""Redirect destinations must never be contacted implicitly."""

import httpx
import pytest
from bioetl.infrastructure.adapters.http.request_timing import _dispatch_http_request

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize(
    "target",
    [
        "http://127.0.0.1/internal",
        "http://[::1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/",
        "https://other.example/",
    ],
)
async def test_redirect_is_not_followed_even_with_unsafe_injected_client(
    stream, target
):
    seen = []

    def respond(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"Location": target})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), follow_redirects=True
    ) as client:
        response = await _dispatch_http_request(
            client,
            "GET",
            "https://provider.example/works",
            {},
            is_stream=stream,
            request_timeout=1,
        )
        assert response.status_code == 302
        await response.aclose()
    assert seen == ["https://provider.example/works"]


@pytest.mark.asyncio
async def test_request_cannot_opt_out_of_redirect_policy():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: pytest.fail("must not send"))
    ) as client:
        with pytest.raises(ValueError, match="Automatic redirects are forbidden"):
            await _dispatch_http_request(
                client,
                "GET",
                "https://provider.example",
                {"follow_redirects": True},
                is_stream=False,
                request_timeout=1,
            )
