import httpx
import pytest

from mcp_server.backend import BackendClient


@pytest.mark.asyncio
async def test_check_word_returns_parsed_json():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/words/check"
        return httpx.Response(200, json={"found": True, "word": {"id": 1}, "created": False})

    transport = httpx.MockTransport(handler)
    client = BackendClient(base_url="http://test/api", transport=transport)
    result = await client.check_word("kot")
    assert result["ok"] is True
    assert result["data"]["found"] is True


@pytest.mark.asyncio
async def test_unreachable_backend_returns_structured_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    transport = httpx.MockTransport(handler)
    client = BackendClient(base_url="http://test/api", transport=transport)
    result = await client.check_word("kot")
    assert result["ok"] is False
    assert "error" in result and "hint" in result
