---
Status: proposed
Date: 2026-06-17
---

# MCP server: standalone FastMCP over the REST API

> **Status note:** Target design. No MCP/FastMCP code or dependency exists in the repo yet.

Claude Code integration will be a separate FastMCP process speaking **stdio**, which calls the FastAPI backend over HTTP. It will not import the models or touch SQLite directly, and it will not be mounted inside the FastAPI app.

We chose this so the backend stays a pure REST core reusable by both the web UI and MCP, with all business logic (validation, dedup, form-gen enqueue) living in one place rather than duplicated in an MCP adapter.

## Considered options

- **In-process MCP mounted inside FastAPI (HTTP/SSE)** — rejected: couples the MCP surface to the web server's lifecycle and request stack.
- **MCP process talking directly to SQLite** — rejected: duplicates business logic (validation, dedup, form-gen enqueue) and risks divergence from the web UI.

## Consequences

- **The real distinction from in-process is process isolation, not "a reachable port."** The standalone process still reaches the backend at `localhost:8000`; the benefit is that the MCP adapter restarts/fails independently of the web server. (Earlier framing of this as "avoids exposing a port" was wrong — stdio avoids the MCP server *itself* needing a port, but it still calls the HTTP backend.)
- **Backend-unreachable behaviour must be specified.** stdio can only return text to Claude Code, so HTTP status codes are lost unless mapped. Open decisions to pin down in implementation: connect timeout + retry policy; startup-order contract (a health check that fails fast if the backend is down); and a structured error passthrough so Claude sees *why* an add failed, not a generic error.
- If the backend runs in a container and the MCP server on the host (or vice-versa), the base URL must account for `host.docker.internal` vs `localhost`.
- An extra network hop and a second process to run/manage.
