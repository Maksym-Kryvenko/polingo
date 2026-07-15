# Polingo MCP server (Plan 5)

Standalone FastMCP (stdio) server exposing word-management tools to an MCP host
(e.g. Claude Code). Calls the Polingo HTTP API; does NOT import backend models.

## Run
    python -m pip install -r requirements.txt
    MCP_BACKEND_URL=http://localhost:8000/api python -m mcp_server.server

## Tools
add_word · add_words_bulk · list_session_words · get_stats

## Errors
If the backend is unreachable, tools return a structured message explaining why
(stdio cannot carry HTTP status codes). Connect timeout 5s, 1 retry.

## Claude Code registration (example)
    claude mcp add polingo -- python -m mcp_server.server
