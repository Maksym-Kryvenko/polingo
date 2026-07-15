from typing import Any, Optional

import httpx

from mcp_server.config import CONNECT_TIMEOUT_S, MAX_RETRIES, backend_url


class BackendClient:
    """Thin async wrapper over the Polingo HTTP API. Never raises on transport
    failure — returns {"ok": bool, ...} so MCP tools can surface a reason."""

    def __init__(self, base_url: Optional[str] = None, transport=None):
        self._base_url = (base_url or backend_url()).rstrip("/")
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            # connect timeout is the one that matters for "backend down"; give reads
            # more headroom since LLM-backed adds can be slow.
            timeout=httpx.Timeout(30.0, connect=CONNECT_TIMEOUT_S),
            transport=self._transport,
        )

    async def _request(self, method: str, path: str, **kw) -> dict[str, Any]:
        last_exc = None
        for _ in range(MAX_RETRIES + 1):
            try:
                async with self._client() as c:
                    resp = await c.request(method, path, **kw)
                if resp.status_code >= 400:
                    return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                            "hint": f"backend at {self._base_url} rejected {method} {path}"}
                return {"ok": True, "data": resp.json()}
            except httpx.HTTPError as exc:
                last_exc = exc
        return {"ok": False, "error": str(last_exc),
                "hint": f"is the backend running at {self._base_url}?"}

    async def check_word(self, text: str) -> dict[str, Any]:
        return await self._request("POST", "/words/check", json={"text": text})

    async def add_words_bulk(self, text: str) -> dict[str, Any]:
        return await self._request("POST", "/words/check/bulk", json={"text": text})

    async def list_session_words(self) -> dict[str, Any]:
        return await self._request("GET", "/session/words/all")

    async def get_stats(self) -> dict[str, Any]:
        return await self._request("GET", "/stats")
