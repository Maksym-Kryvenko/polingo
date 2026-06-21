import pytest

from mcp_server.server import add_word_tool, get_stats_tool


class _FakeBackend:
    def __init__(self, result):
        self._result = result

    async def check_word(self, text):
        return self._result

    async def get_stats(self):
        return self._result


@pytest.mark.asyncio
async def test_add_word_tool_success_message():
    backend = _FakeBackend({"ok": True, "data": {"found": True, "created": True,
                                                 "word": {"polish": "kot"}}})
    msg = await add_word_tool("kot", backend=backend)
    assert "kot" in msg
    assert "added" in msg.lower() or "created" in msg.lower()


@pytest.mark.asyncio
async def test_add_word_tool_surfaces_backend_down():
    backend = _FakeBackend({"ok": False, "error": "refused", "hint": "is the backend running?"})
    msg = await add_word_tool("kot", backend=backend)
    assert "refused" in msg or "running" in msg


@pytest.mark.asyncio
async def test_get_stats_tool_formats_numbers():
    backend = _FakeBackend({"ok": True, "data": {"today_percentage": 80.0, "trend": 5.0,
                                                 "overall_percentage": 75.0, "available_words": 42}})
    msg = await get_stats_tool(backend=backend)
    assert "42" in msg
