from mcp.server.fastmcp import FastMCP

from mcp_server.backend import BackendClient

mcp = FastMCP("polingo")
_default_backend = BackendClient()


async def add_word_tool(text: str, backend=None) -> str:
    backend = backend or _default_backend
    r = await backend.check_word(text)
    if not r["ok"]:
        return f"Could not add '{text}': {r['error']} ({r['hint']})"
    d = r["data"]
    word = (d.get("word") or {}).get("polish", text)
    if d.get("created"):
        return f"Added new word '{word}'."
    if d.get("found"):
        return f"'{word}' already exists (matched {d.get('matched_field')})."
    return f"'{text}' could not be resolved."


async def add_words_bulk_tool(text: str, backend=None) -> str:
    backend = backend or _default_backend
    r = await backend.add_words_bulk(text)
    if not r["ok"]:
        return f"Bulk add failed: {r['error']} ({r['hint']})"
    d = r["data"]
    return (f"Added {d.get('added_count', 0)}, "
            f"{d.get('duplicate_count', 0)} duplicates, {d.get('failed_count', 0)} failed.")


async def list_session_words_tool(backend=None) -> str:
    backend = backend or _default_backend
    r = await backend.list_session_words()
    if not r["ok"]:
        return f"Could not list words: {r['error']} ({r['hint']})"
    words = r["data"].get("words", [])
    return f"{len(words)} words in session: " + ", ".join(w["polish"] for w in words[:50])


async def get_stats_tool(backend=None) -> str:
    backend = backend or _default_backend
    r = await backend.get_stats()
    if not r["ok"]:
        return f"Could not get stats: {r['error']} ({r['hint']})"
    d = r["data"]
    return (f"Today {d['today_percentage']}% (trend {d['trend']}), "
            f"overall {d['overall_percentage']}%, {d['available_words']} words available.")


# Register with FastMCP (thin wrappers so tests can call the *_tool fns directly)
@mcp.tool()
async def add_word(text: str) -> str:
    """Add a single Polish word (or phrase) to the learner's vocabulary."""
    return await add_word_tool(text)


@mcp.tool()
async def add_words_bulk(text: str) -> str:
    """Add multiple comma-separated words at once."""
    return await add_words_bulk_tool(text)


@mcp.tool()
async def list_session_words() -> str:
    """List the words currently in the learner's session."""
    return await list_session_words_tool()


@mcp.tool()
async def get_stats() -> str:
    """Get the learner's current practice statistics."""
    return await get_stats_tool()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
